"""FastAPI application for Honolulu agent."""

import asyncio
import json
import uuid
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from honolulu.agent import Agent, AgentEvent
from honolulu.config import Config, get_default_config
from honolulu.models.claude import ClaudeProvider
from honolulu.tools import ToolManager, get_builtin_tools, MCPServerConfig, get_mcp_manager
from honolulu.permissions import PermissionController


@dataclass
class Session:
    """Agent session."""

    id: str
    agent: Agent
    created_at: datetime
    status: str = "active"
    pending_confirmations: dict[str, asyncio.Future] = field(default_factory=dict)


class ChatRequest(BaseModel):
    """Request to start a chat."""

    message: str
    session_id: str | None = None


class ChatResponse(BaseModel):
    """Response with session info."""

    session_id: str
    ws_url: str


class SessionInfo(BaseModel):
    """Session information."""

    id: str
    created_at: str
    status: str


# Global state
sessions: dict[str, Session] = {}
config: Config = get_default_config()
mcp_tools: list = []  # MCP tools discovered at startup


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    global config, mcp_tools

    # Load config if file exists
    config_path = Path("config/default.yaml")
    if config_path.exists():
        config = Config.load(config_path)

    config.expand_env_vars()

    # Initialize MCP servers if configured
    if config.mcp_servers:
        try:
            mcp_configs = [
                MCPServerConfig(
                    name=s.name,
                    command=s.command,
                    args=s.args,
                    env=s.env,
                )
                for s in config.mcp_servers
            ]
            mcp_manager = get_mcp_manager()
            await mcp_manager.initialize(mcp_configs)
            mcp_tools = mcp_manager.get_tools()
            print(f"Initialized {len(mcp_tools)} MCP tools from {len(config.mcp_servers)} servers")
        except Exception as e:
            print(f"Warning: Failed to initialize MCP servers: {e}")

    yield

    # Cleanup MCP connections
    try:
        mcp_manager = get_mcp_manager()
        await mcp_manager.close()
    except Exception:
        pass

    # Cleanup sessions
    sessions.clear()


app = FastAPI(
    title="Honolulu Agent API",
    description="API for the Honolulu AI agent assistant",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def create_agent() -> Agent:
    """Create a new agent instance."""
    # Create model provider
    model = ClaudeProvider(
        api_key=config.model.api_key,
        model=config.model.name,
        base_url=config.model.base_url,
    )

    # Create tool manager with built-in tools
    tool_manager = ToolManager()
    tool_manager.register_all(get_builtin_tools())

    # Register MCP tools if available
    if mcp_tools:
        tool_manager.register_all(mcp_tools)

    # Create agent
    return Agent(model=model, tool_manager=tool_manager)


def create_session() -> Session:
    """Create a new session."""
    session_id = str(uuid.uuid4())
    agent = create_agent()

    session = Session(
        id=session_id,
        agent=agent,
        created_at=datetime.now(),
    )

    sessions[session_id] = session
    return session


@app.post("/api/chat", response_model=ChatResponse)
async def start_chat(request: ChatRequest):
    """Start a new chat session or continue an existing one."""
    if request.session_id and request.session_id in sessions:
        session = sessions[request.session_id]
    else:
        session = create_session()

    return ChatResponse(
        session_id=session.id,
        ws_url=f"/ws/{session.id}",
    )


@app.get("/api/sessions", response_model=list[SessionInfo])
async def list_sessions():
    """List all active sessions."""
    return [
        SessionInfo(
            id=s.id,
            created_at=s.created_at.isoformat(),
            status=s.status,
        )
        for s in sessions.values()
    ]


@app.delete("/api/sessions/{session_id}")
async def delete_session(session_id: str):
    """Delete a session."""
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    del sessions[session_id]
    return {"ok": True}


@app.get("/api/tools")
async def list_tools():
    """List available tools."""
    agent = create_agent()
    return agent.tool_manager.get_tool_definitions()


@app.get("/api/config")
async def get_config():
    """Get current configuration (sanitized)."""
    return {
        "agent_name": config.agent_name,
        "model": {
            "provider": config.model.provider,
            "name": config.model.name,
        },
        "permissions": {
            "mode": config.permissions.mode,
        },
    }


@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """WebSocket endpoint for agent interaction."""
    await websocket.accept()

    if session_id not in sessions:
        await websocket.send_json({"type": "error", "message": "Session not found"})
        await websocket.close()
        return

    session = sessions[session_id]
    permission_controller = PermissionController(config.permissions)

    async def confirmation_callback(
        tool_call_id: str,
        tool_name: str,
        tool_args: dict,
    ) -> bool:
        """Handle confirmation requests."""
        # Check if permission controller blocks it
        allowed, reason = permission_controller.check_tool_permission(
            tool_name, tool_args
        )
        if not allowed:
            await websocket.send_json(
                {
                    "type": "permission_denied",
                    "tool_call_id": tool_call_id,
                    "reason": reason,
                }
            )
            return False

        # Create a future for the confirmation response
        future: asyncio.Future[bool] = asyncio.get_event_loop().create_future()
        session.pending_confirmations[tool_call_id] = future

        try:
            # Wait for confirmation (with timeout)
            result = await asyncio.wait_for(future, timeout=300.0)  # 5 minute timeout
            return result
        except asyncio.TimeoutError:
            return False
        finally:
            session.pending_confirmations.pop(tool_call_id, None)

    session.agent.confirm_callback = confirmation_callback

    try:
        while True:
            # Receive message from client
            data = await websocket.receive_json()

            if data["type"] == "message":
                # User sent a message, run the agent
                user_message = data["content"]

                async for event in session.agent.run(user_message):
                    await send_agent_event(websocket, event)

            elif data["type"] == "confirm_response":
                # User responded to a confirmation request
                tool_call_id = data["id"]
                action = data["action"]  # "allow", "deny", "allow_all"

                if tool_call_id in session.pending_confirmations:
                    future = session.pending_confirmations[tool_call_id]

                    if action == "allow":
                        future.set_result(True)
                    elif action == "allow_all":
                        # Allow this and future calls to this tool
                        tool_name = data.get("tool_name")
                        if tool_name:
                            session.agent.allow_tool_for_session(tool_name)
                        future.set_result(True)
                    else:  # deny
                        future.set_result(False)

            elif data["type"] == "cancel":
                # User wants to cancel the current operation
                # For now, just acknowledge
                await websocket.send_json({"type": "cancelled"})

    except WebSocketDisconnect:
        pass
    except Exception as e:
        await websocket.send_json({"type": "error", "message": str(e)})


async def send_agent_event(websocket: WebSocket, event: AgentEvent):
    """Send an agent event to the WebSocket client."""
    message: dict[str, Any] = {"type": event.type}

    if event.content is not None:
        message["content"] = event.content

    if event.tool_name:
        message["tool"] = event.tool_name

    if event.tool_args:
        message["args"] = event.tool_args

    if event.tool_call_id:
        message["id"] = event.tool_call_id

    if event.requires_confirmation:
        message["requires_confirmation"] = True

    await websocket.send_json(message)


def main():
    """Run the server."""
    import uvicorn

    uvicorn.run(
        "honolulu.server.app:app",
        host=config.server.host,
        port=config.server.port,
        reload=True,
    )


if __name__ == "__main__":
    main()
