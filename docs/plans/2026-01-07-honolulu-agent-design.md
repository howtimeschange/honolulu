# Honolulu - 通用 AI Agent 助手设计文档

## 概述

Honolulu 是一个基于 Claude Agent SDK 的通用 AI Agent 助手，类似 Manus。采用 Python 核心 + TypeScript CLI 的架构。

## MVP 范围

- **核心能力**: 工具执行（文件操作、代码执行、网络搜索、MCP 集成）
- **用户界面**: CLI + API Server
- **安全模式**: Interactive（敏感操作需确认）
- **模型**: 可配置，默认 Claude

## 整体架构

```
┌─────────────────────────────────────────────────────────────┐
│                    TypeScript CLI                            │
│              (交互式命令行界面，用户确认)                      │
└─────────────────────┬───────────────────────────────────────┘
                      │ HTTP/WebSocket
┌─────────────────────▼───────────────────────────────────────┐
│                  Python API Server                           │
│   ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│   │ FastAPI     │  │ WebSocket   │  │ 权限控制器   │        │
│   │ REST API    │  │ 实时流      │  │ Interactive │        │
│   └─────────────┘  └─────────────┘  └─────────────┘        │
└─────────────────────┬───────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────┐
│                   Agent Core (Python)                        │
│   ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│   │ Claude SDK  │  │ Tool Manager│  │ Context Mgr │        │
│   │ 模型抽象    │  │ 工具调度    │  │ 对话历史    │        │
│   └─────────────┘  └─────────────┘  └─────────────┘        │
└─────────────────────┬───────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────┐
│                      Tools Layer                             │
│   ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐             │
│   │ 文件   │ │ Bash   │ │ 网络   │ │  MCP   │             │
│   │ 操作   │ │ 执行   │ │ 搜索   │ │ 服务器 │             │
│   └────────┘ └────────┘ └────────┘ └────────┘             │
└─────────────────────────────────────────────────────────────┘
```

## 项目结构

```
honolulu/
├── packages/
│   ├── core/                    # Python 核心
│   │   ├── pyproject.toml
│   │   ├── src/
│   │   │   └── honolulu/
│   │   │       ├── __init__.py
│   │   │       ├── agent.py           # 主 Agent 类
│   │   │       ├── models/
│   │   │       │   ├── __init__.py
│   │   │       │   ├── base.py        # 模型抽象接口
│   │   │       │   └── claude.py      # Claude 实现
│   │   │       ├── tools/
│   │   │       │   ├── __init__.py
│   │   │       │   ├── base.py        # 工具基类
│   │   │       │   ├── file_ops.py    # 文件操作
│   │   │       │   ├── bash.py        # Bash 执行
│   │   │       │   ├── web_search.py  # 网络搜索
│   │   │       │   └── mcp.py         # MCP 客户端
│   │   │       ├── server/
│   │   │       │   ├── __init__.py
│   │   │       │   ├── app.py         # FastAPI 应用
│   │   │       │   └── websocket.py   # WebSocket 处理
│   │   │       └── permissions.py     # 权限控制
│   │   └── tests/
│   │
│   └── cli/                     # TypeScript CLI
│       ├── package.json
│       ├── tsconfig.json
│       └── src/
│           ├── index.ts         # 入口
│           ├── client.ts        # API 客户端
│           ├── ui/
│           │   ├── prompt.ts    # 用户交互
│           │   └── spinner.ts   # 加载动画
│           └── confirm.ts       # 确认对话框
│
├── config/
│   └── default.yaml             # 默认配置
├── docker-compose.yml
└── README.md
```

## 工具系统

### 内置工具 (MVP)

| 工具名 | 功能 | 需要确认 |
|--------|------|----------|
| `file_read` | 读取文件内容 | ❌ |
| `file_write` | 写入/创建文件 | ✅ |
| `file_list` | 列出目录内容 | ❌ |
| `bash_exec` | 执行 shell 命令 | ✅ |
| `web_search` | 网络搜索 | ❌ |
| `web_fetch` | 获取网页内容 | ❌ |
| `mcp_call` | 调用 MCP 服务器工具 | 根据工具类型 |

### 工具接口

```python
class Tool(ABC):
    name: str
    description: str
    parameters: dict          # JSON Schema
    requires_confirmation: bool

    @abstractmethod
    async def execute(self, params: dict) -> ToolResult:
        pass
```

## 配置文件

```yaml
# config/default.yaml

agent:
  name: "honolulu"

model:
  provider: "anthropic"
  name: "claude-sonnet-4-20250514"
  api_key: "${ANTHROPIC_API_KEY}"
  max_tokens: 8192

permissions:
  mode: "interactive"
  allowed_paths:
    - "${HOME}/projects/**"
    - "/tmp/**"
  blocked_paths:
    - "${HOME}/.ssh/**"
    - "${HOME}/.aws/**"
  allowed_commands:
    - "git"
    - "ls"
    - "cat"
    - "npm"
    - "python"
  blocked_commands:
    - "rm -rf /"
    - "sudo"
    - "chmod 777"

mcp_servers:
  - name: "filesystem"
    command: "npx"
    args: ["-y", "@anthropic/mcp-server-filesystem", "~/projects"]

  - name: "github"
    command: "npx"
    args: ["-y", "@anthropic/mcp-server-github"]
    env:
      GITHUB_TOKEN: "${GITHUB_TOKEN}"

server:
  host: "127.0.0.1"
  port: 8420
```

## API 设计

### REST API

```
POST /api/chat
  请求: { "message": "用户指令", "session_id": "xxx" }
  响应: { "session_id": "xxx", "ws_url": "/ws/{session_id}" }

GET /api/sessions
  响应: [{ "id": "xxx", "created_at": "...", "status": "active" }]

DELETE /api/sessions/{session_id}
  响应: { "ok": true }

GET /api/config
  响应: 当前配置（脱敏）

GET /api/tools
  响应: 可用工具列表
```

### WebSocket 消息

```typescript
// 服务器 → 客户端
{ type: "thinking", content: "正在分析任务..." }
{ type: "text", content: "我来帮你创建文件..." }
{ type: "tool_call", id: "tc_1", tool: "file_write", args: {...} }
{ type: "confirm_request", id: "cr_1", tool: "file_write", args: {...}, message: "创建文件 hello.py" }
{ type: "tool_result", id: "tc_1", result: {...} }
{ type: "done", summary: "已完成任务" }
{ type: "error", message: "..." }

// 客户端 → 服务器
{ type: "confirm_response", id: "cr_1", action: "allow" | "deny" | "allow_all" }
{ type: "cancel" }
```

## 工作流程

1. 用户通过 CLI 输入指令
2. CLI 发送请求到 API Server，建立 WebSocket 连接
3. Agent 调用 Claude 模型分析任务
4. 模型返回工具调用意图
5. 权限控制器检查是否需要确认
6. 如需确认，通过 WebSocket 推送确认请求到 CLI
7. 用户确认后，执行工具
8. 工具结果反馈给模型，继续 Agent 循环
9. 任务完成，返回最终结果

## 后续扩展

- 多模型智能路由
- 长短期记忆系统
- Web UI 界面
- 多 Agent 协作
