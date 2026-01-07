# 🌋 Honolulu - 通用AI助手

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Node.js 20+](https://img.shields.io/badge/node-20+-green.svg)](https://nodejs.org/)

A universal AI agent assistant built on Claude, similar to Manus.

**Powered by 易成Kim。**

## Architecture

- **Python Core** (`packages/core`): Agent logic, tool system, and API server
- **TypeScript CLI** (`packages/cli`): Interactive command-line interface

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 20+
- An Anthropic API key

### Installation

**Quick Setup (recommended):**

```bash
./scripts/setup.sh
```

**Manual Setup:**

1. **Set up the Python backend:**

```bash
cd packages/core
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

2. **Set up the TypeScript CLI:**

```bash
cd packages/cli
npm install
npm run build
```

3. **Configure your API key:**

```bash
export ANTHROPIC_API_KEY="your-api-key"
```

### Running

1. **Start the server:**

```bash
cd packages/core
source .venv/bin/activate
honolulu-server
```

2. **Run the CLI (in another terminal):**

```bash
cd packages/cli
npm start
```

Or use the single-command mode:

```bash
npm start -- -e "List all Python files in the current directory"
```

## Features

### Built-in Tools

| Tool | Description | Requires Confirmation |
|------|-------------|----------------------|
| `file_read` | Read file contents | No |
| `file_write` | Write/create files | Yes |
| `file_list` | List directory contents | No |
| `bash_exec` | Execute shell commands | Yes |
| `web_search` | Search the web | No |
| `web_fetch` | Fetch web page content | No |

### Permission Modes

- **auto**: All tool calls execute automatically
- **interactive** (default): Sensitive operations require confirmation
- **strict**: All tool calls require confirmation

### Confirmation Options

When a tool requires confirmation, you can:

- **Allow**: Execute this time only
- **Allow all**: Allow all future calls to this tool in the session
- **Deny**: Block this execution

## Configuration

Edit `config/default.yaml` to customize:

- Model settings (provider, model name, API key)
- Permission rules (allowed/blocked paths and commands)
- MCP server connections
- Server host and port

## Project Structure

```
honolulu/
├── packages/
│   ├── core/                    # Python backend
│   │   ├── src/honolulu/
│   │   │   ├── agent.py         # Main Agent class
│   │   │   ├── models/          # Model providers
│   │   │   ├── tools/           # Tool implementations
│   │   │   ├── server/          # FastAPI server
│   │   │   ├── permissions.py   # Permission controller
│   │   │   └── config.py        # Configuration
│   │   └── pyproject.toml
│   │
│   └── cli/                     # TypeScript frontend
│       ├── src/
│       │   ├── index.ts         # CLI entry point
│       │   ├── client.ts        # API client
│       │   └── ui/              # UI components
│       └── package.json
│
├── config/
│   └── default.yaml             # Default configuration
└── README.md
```

## API

### REST Endpoints

- `POST /api/chat` - Start a chat session
- `GET /api/sessions` - List active sessions
- `DELETE /api/sessions/{id}` - Delete a session
- `GET /api/tools` - List available tools
- `GET /api/config` - Get current configuration

### WebSocket Protocol

Connect to `/ws/{session_id}` for real-time communication.

**Server → Client messages:**
- `thinking` - Agent is processing
- `text` - Text response from agent
- `tool_call` - Tool is being called
- `confirm_request` - Confirmation needed
- `tool_result` - Tool execution result
- `done` - Task completed
- `error` - Error occurred

**Client → Server messages:**
- `message` - User message
- `confirm_response` - Response to confirmation request
- `cancel` - Cancel current operation

## Roadmap

- [ ] 多模型智能路由（Claude/GPT/Gemini/国产模型）
- [ ] 长短期记忆系统（向量数据库）
- [ ] MCP 服务器集成
- [ ] Web UI 界面
- [ ] 多 Agent 协作
- [ ] Docker 一键部署

## Contributing

欢迎贡献代码！请查看 [CONTRIBUTING.md](CONTRIBUTING.md) 了解详情。

## License

MIT License - 详见 [LICENSE](LICENSE) 文件
