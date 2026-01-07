/**
 * API client for communicating with the Honolulu server.
 */

import WebSocket from "ws";

export interface ChatResponse {
  session_id: string;
  ws_url: string;
}

export interface AgentMessage {
  type:
    | "thinking"
    | "text"
    | "tool_call"
    | "confirm_request"
    | "tool_result"
    | "done"
    | "error"
    | "permission_denied"
    | "cancelled";
  content?: string;
  tool?: string;
  args?: Record<string, unknown>;
  id?: string;
  requires_confirmation?: boolean;
  reason?: string;
}

export interface ConfirmResponse {
  type: "confirm_response";
  id: string;
  action: "allow" | "deny" | "allow_all";
  tool_name?: string;
}

export class HonoluluClient {
  private baseUrl: string;
  private ws: WebSocket | null = null;
  private sessionId: string | null = null;

  constructor(baseUrl: string = "http://127.0.0.1:8420") {
    this.baseUrl = baseUrl;
  }

  /**
   * Start a new chat session.
   */
  async startChat(message: string): Promise<ChatResponse> {
    const response = await fetch(`${this.baseUrl}/api/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message, session_id: this.sessionId }),
    });

    if (!response.ok) {
      throw new Error(`Failed to start chat: ${response.statusText}`);
    }

    const data = (await response.json()) as ChatResponse;
    this.sessionId = data.session_id;
    return data;
  }

  /**
   * Connect to WebSocket for real-time communication.
   */
  connect(
    sessionId: string,
    onMessage: (msg: AgentMessage) => void,
    onError: (error: Error) => void,
    onClose: () => void
  ): void {
    const wsUrl = this.baseUrl.replace("http", "ws") + `/ws/${sessionId}`;
    this.ws = new WebSocket(wsUrl);

    this.ws.on("open", () => {
      // Connection established
    });

    this.ws.on("message", (data: WebSocket.Data) => {
      try {
        const msg = JSON.parse(data.toString()) as AgentMessage;
        onMessage(msg);
      } catch (e) {
        onError(new Error(`Failed to parse message: ${e}`));
      }
    });

    this.ws.on("error", (error) => {
      onError(error);
    });

    this.ws.on("close", () => {
      onClose();
    });
  }

  /**
   * Send a message through WebSocket.
   */
  sendMessage(content: string): void {
    if (!this.ws) {
      throw new Error("Not connected");
    }

    this.ws.send(
      JSON.stringify({
        type: "message",
        content,
      })
    );
  }

  /**
   * Send confirmation response.
   */
  sendConfirmResponse(
    id: string,
    action: "allow" | "deny" | "allow_all",
    toolName?: string
  ): void {
    if (!this.ws) {
      throw new Error("Not connected");
    }

    const response: ConfirmResponse = {
      type: "confirm_response",
      id,
      action,
    };

    if (toolName) {
      response.tool_name = toolName;
    }

    this.ws.send(JSON.stringify(response));
  }

  /**
   * Cancel current operation.
   */
  cancel(): void {
    if (!this.ws) {
      return;
    }

    this.ws.send(JSON.stringify({ type: "cancel" }));
  }

  /**
   * Close the connection.
   */
  close(): void {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }

  /**
   * Get available tools.
   */
  async getTools(): Promise<unknown[]> {
    const response = await fetch(`${this.baseUrl}/api/tools`);
    return (await response.json()) as unknown[];
  }

  /**
   * Get current configuration.
   */
  async getConfig(): Promise<Record<string, unknown>> {
    const response = await fetch(`${this.baseUrl}/api/config`);
    return (await response.json()) as Record<string, unknown>;
  }
}
