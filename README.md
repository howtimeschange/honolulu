# Honolulu

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Node.js 20+](https://img.shields.io/badge/node-20+-green.svg)](https://nodejs.org/)

A universal AI agent assistant built on Claude, similar to Manus.
<img width="422" height="573" alt="截屏2026-01-07 15 21 03" src="https://github.com/user-attachments/assets/560e5f7a-8066-4f60-97a3-14106a33ffc3" />
<img width="405" height="485" alt="截屏2026-01-07 15 21 22" src="https://github.com/user-attachments/assets/bd3ff03a-fdd5-43ea-9f0f-7c1ba59f7040" />



**Powered by 易成 Kim**

## Features

- **Tool Execution**: File operations, shell commands, web search & fetch
- **MCP Integration**: Connect to any MCP server for extended capabilities
- **Multi-Model Routing**: Smart routing between Claude, GPT, Qwen and more
- **Memory System**: Short-term, working, and long-term memory with vector store
- **Interactive Permissions**: Sensitive operations require confirmation
- **OneRouter Support**: Use API proxies like OneRouter, OpenRouter

## Quick Start

### One-Command Setup

```bash
# Clone the repo
git clone https://github.com/howtimeschange/honolulu.git
cd honolulu

# Install everything
./start.sh install

# Configure your API key (create .env file)
cp .env.example .env
# Edit .env with your API key

# Start the server
./start.sh
```

### Configure Environment

Create a `.env` file in the project root:

```bash
# For Anthropic API (direct)
ANTHROPIC_API_KEY=your-anthropic-api-key

# For OneRouter / OpenRouter (proxy)
ANTHROPIC_API_KEY=your-onerouter-api-key
ANTHROPIC_BASE_URL=https://your-proxy.com/api
```

### Start Using

**Terminal 1 - Start Server:**
```bash
./start.sh
# or
./start.sh server
```

**Terminal 2 - Start CLI:**
```bash
honolulu
# or
./start.sh cli
```

### CLI Commands

```bash
honolulu                    # Interactive mode
honolulu --help             # Show help
honolulu -e "你好"           # Execute single command
honolulu -s http://ip:8420  # Connect to remote server
```

## Architecture

```
honolulu/
├── packages/
│   ├── core/                    # Python backend
│   │   └── src/honolulu/
│   │       ├── agent.py         # Main Agent class
│   │       ├── models/          # Model providers (Claude, OpenAI)
│   │       │   ├── claude.py    # Anthropic Claude
│   │       │   ├── openai_provider.py  # OpenAI compatible
│   │       │   └── router.py    # Multi-model routing
│   │       ├── tools/           # Tool implementations
│   │       │   ├── builtin.py   # File, bash, web tools
│   │       │   └── mcp.py       # MCP server integration
│   │       ├── memory/          # Memory system
│   │       │   ├── base.py      # Memory manager
│   │       │   └── vector_store.py  # ChromaDB integration
│   │       ├── server/          # FastAPI server
│   │       ├── permissions.py   # Permission controller
│   │       └── config.py        # Configuration
│   │
│   └── cli/                     # TypeScript CLI
│       └── src/
│           ├── index.ts         # CLI entry point
│           ├── client.ts        # API client
│           └── ui/              # UI components
│
├── config/
│   └── default.yaml             # Configuration file
├── .env.example                 # Environment template
├── .env                         # Your environment (git ignored)
└── start.sh                     # Quick start script
```

## Configuration

Edit `config/default.yaml`:

```yaml
# Model configuration
model:
  provider: "anthropic"
  name: "claude-sonnet-4-20250514"
  api_key: "${ANTHROPIC_API_KEY}"
  base_url: "${ANTHROPIC_BASE_URL}"  # Optional: for proxies
  max_tokens: 8192

# Permission settings
permissions:
  mode: "interactive"  # auto | interactive | strict
  allowed_paths:
    - "${HOME}/projects/**"
  blocked_commands:
    - "rm -rf /"
    - "sudo"

# MCP servers (optional)
mcp_servers:
  - name: "filesystem"
    command: "npx"
    args: ["-y", "@anthropic/mcp-filesystem"]
```

## Built-in Tools

| Tool | Description | Requires Confirmation |
|------|-------------|----------------------|
| `file_read` | Read file contents | No |
| `file_write` | Write/create files | Yes |
| `file_list` | List directory contents | No |
| `bash_exec` | Execute shell commands | Yes |
| `web_search` | Search the web | No |
| `web_fetch` | Fetch web page content | No |

## API Reference

### REST Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/chat` | Start chat session |
| GET | `/api/sessions` | List active sessions |
| DELETE | `/api/sessions/{id}` | Delete session |
| GET | `/api/tools` | List available tools |
| GET | `/docs` | Swagger UI |

### WebSocket

Connect to `/ws/{session_id}` for real-time communication.

**Server → Client:**
- `thinking` - Processing
- `text` - Text response
- `tool_call` - Tool being called
- `confirm_request` - Need confirmation
- `tool_result` - Execution result
- `done` - Completed
- `error` - Error occurred

**Client → Server:**
- `message` - User message
- `confirm_response` - Confirmation response
- `cancel` - Cancel operation

## Roadmap

- [x] Core agent with tool execution
- [x] Interactive permission system
- [x] MCP server integration
- [x] Multi-model routing
- [x] Memory system with vector store
- [x] OneRouter / proxy support
- [ ] Web UI interface
- [ ] Multi-agent collaboration
- [ ] Docker deployment

## Contributing

欢迎贡献代码！请查看 [CONTRIBUTING.md](CONTRIBUTING.md) 了解详情。

## License

MIT License - 详见 [LICENSE](LICENSE) 文件
