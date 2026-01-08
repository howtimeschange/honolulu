export interface Session {
  id: string;
  createdAt: string;
  status: 'active' | 'completed' | 'error';
  title?: string;
}

export interface Attachment {
  id: string;
  type: 'image' | 'document';
  filename: string;
  contentType: string;
  base64?: string;  // For images
  text?: string;    // For PDF documents (extracted text)
  pageCount?: number;  // For PDF documents
}

export interface Message {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: Date;
  subAgent?: string;
  toolCalls?: ToolCall[];
  attachments?: Attachment[];
}

export interface ToolCall {
  id: string;
  name: string;
  args: Record<string, unknown>;
  status: 'pending' | 'running' | 'completed' | 'error' | 'awaiting_confirmation';
  result?: string;
}

export interface SubAgentStatus {
  name: string;
  displayName: string;
  status: 'idle' | 'running' | 'completed';
  currentTask?: string;
}

export interface AgentMessage {
  type:
    | 'thinking'
    | 'text'
    | 'text_delta'  // Streaming text chunk
    | 'tool_call'
    | 'confirm_request'
    | 'tool_result'
    | 'done'
    | 'error'
    | 'permission_denied'
    | 'cancelled'
    | 'sub_agent_start'
    | 'sub_agent_progress'
    | 'sub_agent_done';
  content?: string;
  tool?: string;
  args?: Record<string, unknown>;
  id?: string;
  requires_confirmation?: boolean;
  reason?: string;
  agent?: string;
  task?: string;
  result?: string;
}

export interface FilePreview {
  path: string;
  content: string;
  language?: string;
}

export interface AppConfig {
  agentName: string;
  model: {
    provider: string;
    name: string;
  };
  routing: {
    enabled: boolean;
    strategy: string;
    providers: string[];
  };
}

export interface SubAgentInfo {
  name: string;
  display_name: string;
  description: string;
}
