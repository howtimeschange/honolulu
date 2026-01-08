"""FastAPI application for Honolulu agent."""

import asyncio
import json
import uuid
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

import base64
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import yaml
from honolulu.agent import Agent, AgentEvent
from honolulu.config import Config, get_default_config, ProviderConfig as ConfigProviderConfig
from honolulu.models import ClaudeProvider, OpenAIProvider, ModelRouter, RoutingStrategy
from honolulu.tools import ToolManager, get_builtin_tools, MCPServerConfig, get_mcp_manager
from honolulu.permissions import PermissionController
from honolulu.agents import create_orchestrator


@dataclass
class SubAgentEvent:
    """Event from a sub-agent."""

    agent_name: str
    event_type: str  # "start", "progress", "done", "error"
    content: str


@dataclass
class Session:
    """Agent session."""

    id: str
    agent: Agent
    created_at: datetime
    status: str = "active"
    pending_confirmations: dict[str, asyncio.Future] = field(default_factory=dict)
    sub_agent_callback: Callable[[SubAgentEvent], None] | None = None


class ChatRequest(BaseModel):
    """Request to start a chat."""

    message: str
    session_id: str | None = None
    multi_agent: bool = False  # Enable multi-agent orchestration mode


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
model_router: ModelRouter | None = None  # Multi-model router if enabled


async def reload_config() -> dict[str, Any]:
    """Reload configuration from file and reinitialize providers.

    Returns:
        Dict with reload status and any warnings
    """
    global config, model_router

    config_path = Path("config/default.yaml")
    warnings = []

    try:
        # Load new config
        if config_path.exists():
            new_config = Config.load(config_path)
        else:
            new_config = get_default_config()

        new_config.expand_env_vars()

        # Reinitialize model router if routing is enabled
        new_router = None
        if new_config.routing.enabled and new_config.routing.providers:
            try:
                strategy = RoutingStrategy(new_config.routing.strategy)
                new_router = ModelRouter(
                    strategy=strategy,
                    fallback_enabled=new_config.routing.fallback_enabled,
                )

                for p in new_config.routing.providers:
                    provider = _create_provider(p)
                    new_router.register(
                        name=p.name,
                        provider=provider,
                        priority=p.priority,
                        cost_per_1k_input=p.cost_per_1k_input,
                        cost_per_1k_output=p.cost_per_1k_output,
                        capabilities=p.capabilities,
                        is_default=p.is_default,
                    )
                    print(f"[Hot Reload] Registered provider: {p.name} ({p.type}/{p.model})")

                print(f"[Hot Reload] Model router enabled with {len(new_config.routing.providers)} providers")
            except Exception as e:
                warnings.append(f"Failed to initialize model router: {e}")
                new_router = None

        # Update global state
        config = new_config
        model_router = new_router

        # Note: MCP servers cannot be hot-reloaded due to process management
        # They require a full server restart
        if new_config.mcp_servers:
            warnings.append("MCP server changes require server restart to take effect")

        return {
            "success": True,
            "warnings": warnings,
            "routing_enabled": new_config.routing.enabled,
            "provider_count": len(new_config.routing.providers) if new_config.routing.enabled else 0,
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "warnings": warnings,
        }


def _create_provider(provider_config):
    """Create a model provider from config."""
    if provider_config.type == "anthropic":
        return ClaudeProvider(
            api_key=provider_config.api_key,
            model=provider_config.model,
            base_url=provider_config.base_url,
        )
    elif provider_config.type == "openai":
        return OpenAIProvider(
            api_key=provider_config.api_key,
            model=provider_config.model,
            base_url=provider_config.base_url,
        )
    else:
        raise ValueError(f"Unknown provider type: {provider_config.type}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    global config, mcp_tools, model_router

    # Load config if file exists
    config_path = Path("config/default.yaml")
    if config_path.exists():
        config = Config.load(config_path)

    config.expand_env_vars()

    # Initialize model router if enabled
    if config.routing.enabled and config.routing.providers:
        try:
            strategy = RoutingStrategy(config.routing.strategy)
            model_router = ModelRouter(
                strategy=strategy,
                fallback_enabled=config.routing.fallback_enabled,
            )

            for p in config.routing.providers:
                provider = _create_provider(p)
                model_router.register(
                    name=p.name,
                    provider=provider,
                    priority=p.priority,
                    cost_per_1k_input=p.cost_per_1k_input,
                    cost_per_1k_output=p.cost_per_1k_output,
                    capabilities=p.capabilities,
                    is_default=p.is_default,
                )
                print(f"Registered provider: {p.name} ({p.type}/{p.model})")

            print(f"Model router enabled with {len(config.routing.providers)} providers, strategy: {config.routing.strategy}")
        except Exception as e:
            print(f"Warning: Failed to initialize model router: {e}")
            model_router = None

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


def create_agent(
    sub_agent_callback: Callable[[SubAgentEvent], None] | None = None,
    multi_agent_mode: bool = False,
) -> Agent:
    """Create a new agent instance.

    Args:
        sub_agent_callback: Callback for sub-agent events (only used in multi-agent mode)
        multi_agent_mode: Enable multi-agent orchestration mode
    """
    # Use router if available, otherwise create single provider
    if model_router is not None:
        model = model_router
    else:
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

    # In multi-agent mode, create orchestrator with delegation tools
    if multi_agent_mode:
        def on_sub_agent_event(agent_name: str, event_type: str, content: str) -> None:
            if sub_agent_callback:
                sub_agent_callback(SubAgentEvent(agent_name, event_type, content))

        orchestrator = create_orchestrator(
            model=model,
            tool_manager=tool_manager,
            on_sub_agent_event=on_sub_agent_event,
        )
        # Use orchestrator's system prompt
        return Agent(
            model=model,
            tool_manager=tool_manager,
            system_prompt=orchestrator.SYSTEM_PROMPT,
        )

    # Create standard agent
    return Agent(model=model, tool_manager=tool_manager)


def create_session(
    multi_agent_mode: bool = False,
    sub_agent_callback: Callable[[SubAgentEvent], None] | None = None,
) -> Session:
    """Create a new session.

    Args:
        multi_agent_mode: Enable multi-agent orchestration mode
        sub_agent_callback: Callback for sub-agent events
    """
    session_id = str(uuid.uuid4())

    # Create agent with multi-agent support
    agent = create_agent(
        sub_agent_callback=sub_agent_callback,
        multi_agent_mode=multi_agent_mode,
    )

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
        session = create_session(multi_agent_mode=request.multi_agent)

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
    result = {
        "agent_name": config.agent_name,
        "model": {
            "provider": config.model.provider,
            "name": config.model.name,
        },
        "permissions": {
            "mode": config.permissions.mode,
        },
        "routing": {
            "enabled": config.routing.enabled,
            "strategy": config.routing.strategy,
            "providers": [p.name for p in config.routing.providers],
        },
    }

    # Add active providers if router is enabled
    if model_router is not None:
        result["routing"]["active_providers"] = model_router.providers

    return result


# Pydantic models for config API
class ProviderConfigRequest(BaseModel):
    """Provider configuration request."""
    id: str
    name: str
    type: str  # "anthropic" | "openai"
    api_key: str
    base_url: str | None = None
    model: str
    is_default: bool = False


class MCPServerConfigRequest(BaseModel):
    """MCP server configuration request."""
    name: str
    command: str
    args: list[str] = []
    env: dict[str, str] = {}
    enabled: bool = True


class ConfigUpdateRequest(BaseModel):
    """Configuration update request."""
    providers: list[ProviderConfigRequest] | None = None
    mcp_servers: list[MCPServerConfigRequest] | None = None


@app.get("/api/config/providers")
async def get_providers():
    """Get configured model providers (with masked API keys)."""
    providers = []

    # Add main model config as a provider if routing is not enabled
    if not config.routing.enabled:
        providers.append({
            "id": "main",
            "name": "Main Provider",
            "type": config.model.provider,
            "api_key_set": bool(config.model.api_key and not config.model.api_key.startswith("${")),
            "api_key_env": config.model.api_key if config.model.api_key.startswith("${") else None,
            "base_url": config.model.base_url,
            "model": config.model.name,
            "is_default": True,
        })
    else:
        # Add routing providers
        for i, p in enumerate(config.routing.providers):
            providers.append({
                "id": f"provider_{i}",
                "name": p.name,
                "type": p.type,
                "api_key_set": bool(p.api_key and not p.api_key.startswith("${")),
                "api_key_env": p.api_key if p.api_key.startswith("${") else None,
                "base_url": p.base_url,
                "model": p.model,
                "is_default": p.is_default,
            })

    return {"providers": providers}


@app.get("/api/config/mcp")
async def get_mcp_servers():
    """Get configured MCP servers."""
    servers = []
    for mcp in config.mcp_servers:
        servers.append({
            "name": mcp.name,
            "command": mcp.command,
            "args": mcp.args,
            "env": {k: ("***" if "KEY" in k.upper() or "TOKEN" in k.upper() or "SECRET" in k.upper() else v) for k, v in mcp.env.items()},
            "enabled": True,
        })
    return {"servers": servers}


@app.post("/api/config/reload")
async def reload_config_endpoint():
    """Manually trigger configuration hot reload.

    This reloads provider configuration without server restart.
    MCP server changes still require a full restart.
    """
    result = await reload_config()

    if result.get("success"):
        return {
            "success": True,
            "message": "Configuration reloaded successfully",
            "routing_enabled": result.get("routing_enabled"),
            "provider_count": result.get("provider_count"),
            "warnings": result.get("warnings"),
        }
    else:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to reload config: {result.get('error', 'Unknown error')}",
        )


@app.put("/api/config")
async def update_config(request: ConfigUpdateRequest):
    """Update configuration and save to file.

    Note: Changes to providers require server restart to take full effect.
    MCP server changes also require restart.
    """
    global config, model_router

    config_path = Path("config/default.yaml")

    # Load existing config file
    if config_path.exists():
        with open(config_path) as f:
            config_data = yaml.safe_load(f) or {}
    else:
        config_data = {}

    changes_made = []

    # Update providers
    if request.providers is not None:
        if len(request.providers) == 0:
            # Clear routing, use default model
            config_data["routing"] = {"enabled": False}
            changes_made.append("providers cleared")
        elif len(request.providers) == 1:
            # Single provider - use as main model
            p = request.providers[0]
            config_data["model"] = {
                "provider": p.type,
                "name": p.model,
                "api_key": p.api_key if p.api_key else "${ANTHROPIC_API_KEY}" if p.type == "anthropic" else "${OPENAI_API_KEY}",
                "base_url": p.base_url,
                "max_tokens": 8192,
            }
            config_data["routing"] = {"enabled": False}
            changes_made.append("single provider configured")
        else:
            # Multiple providers - enable routing
            providers_config = []
            for i, p in enumerate(request.providers):
                providers_config.append({
                    "name": p.name,
                    "type": p.type,
                    "api_key": p.api_key if p.api_key else f"${{{p.type.upper()}_API_KEY}}",
                    "model": p.model,
                    "base_url": p.base_url,
                    "priority": 100 - i * 10,  # Descending priority
                    "is_default": p.is_default,
                })
            config_data["routing"] = {
                "enabled": True,
                "strategy": "quality-first",
                "fallback_enabled": True,
                "providers": providers_config,
            }
            changes_made.append(f"{len(request.providers)} providers configured with routing")

    # Update MCP servers
    if request.mcp_servers is not None:
        enabled_servers = [s for s in request.mcp_servers if s.enabled]
        if enabled_servers:
            config_data["mcp_servers"] = [
                {
                    "name": s.name,
                    "command": s.command,
                    "args": s.args,
                    "env": s.env,
                }
                for s in enabled_servers
            ]
            changes_made.append(f"{len(enabled_servers)} MCP servers configured")
        else:
            config_data.pop("mcp_servers", None)
            changes_made.append("MCP servers cleared")

    # Write back to file
    with open(config_path, "w") as f:
        yaml.dump(config_data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

    # Hot reload configuration for providers (MCP still requires restart)
    reload_result = await reload_config()

    mcp_changed = request.mcp_servers is not None
    restart_required = mcp_changed and not reload_result.get("success", False)

    warnings = reload_result.get("warnings", [])
    if not reload_result.get("success"):
        warnings.append(f"Hot reload failed: {reload_result.get('error', 'Unknown error')}")

    message_parts = [f"Configuration updated: {', '.join(changes_made)}"]
    if reload_result.get("success") and request.providers is not None:
        message_parts.append("Provider changes applied immediately")
    if mcp_changed:
        message_parts.append("MCP changes require server restart")

    return {
        "success": True,
        "message": ". ".join(message_parts) + ".",
        "changes": changes_made,
        "restart_required": restart_required,
        "hot_reload": reload_result,
        "warnings": warnings if warnings else None,
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
                # User sent a message, run the agent with streaming
                user_message = data["content"]
                attachments = data.get("attachments")  # Optional attachments

                # Use streaming method for real-time text output
                async for event in session.agent.run_streaming(user_message, attachments):
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


async def send_sub_agent_event(websocket: WebSocket, event: SubAgentEvent):
    """Send a sub-agent event to the WebSocket client."""
    await websocket.send_json({
        "type": f"sub_agent_{event.event_type}",  # sub_agent_start, sub_agent_progress, sub_agent_done, sub_agent_error
        "agent": event.agent_name,
        "content": event.content,
    })


@app.get("/api/agents")
async def list_agents():
    """List available sub-agents."""
    from honolulu.agents.sub_agents import CoderAgent, ResearcherAgent

    return {
        "agents": [
            {
                "name": CoderAgent.name,
                "display_name": CoderAgent.display_name,
                "description": CoderAgent.description,
            },
            {
                "name": ResearcherAgent.name,
                "display_name": ResearcherAgent.display_name,
                "description": ResearcherAgent.description,
            },
        ]
    }


# Supported file types
SUPPORTED_IMAGE_TYPES = {"image/png", "image/jpeg", "image/gif", "image/webp"}
SUPPORTED_DOCUMENT_TYPES = {"application/pdf"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB


@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...)):
    """Upload a file (image or PDF) for multimodal chat.

    Returns:
        For images: {id, filename, content_type, base64, type: "image"}
        For PDFs: {id, filename, content_type, text, page_count, type: "document"}
    """
    if not file.content_type:
        raise HTTPException(status_code=400, detail="Missing content type")

    # Check file type
    if file.content_type not in SUPPORTED_IMAGE_TYPES and file.content_type not in SUPPORTED_DOCUMENT_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {file.content_type}. Supported: images (png, jpg, gif, webp) and PDF"
        )

    # Read file content
    content = await file.read()

    # Check file size
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Maximum size: {MAX_FILE_SIZE // 1024 // 1024}MB"
        )

    file_id = str(uuid.uuid4())

    if file.content_type in SUPPORTED_IMAGE_TYPES:
        # Return base64-encoded image
        b64_content = base64.b64encode(content).decode("utf-8")
        return {
            "id": file_id,
            "filename": file.filename,
            "content_type": file.content_type,
            "base64": b64_content,
            "type": "image",
        }
    else:
        # PDF - extract text
        try:
            from honolulu.tools.pdf_extractor import extract_pdf_text, get_pdf_info

            text = extract_pdf_text(content)
            info = get_pdf_info(content)

            return {
                "id": file_id,
                "filename": file.filename,
                "content_type": file.content_type,
                "text": text,
                "page_count": info["page_count"],
                "type": "document",
            }
        except ImportError:
            raise HTTPException(
                status_code=500,
                detail="PDF processing not available. Install pymupdf: pip install pymupdf"
            )
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to process PDF: {str(e)}"
            )


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
