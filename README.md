# Honolulu v0.0.2

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Node.js 20+](https://img.shields.io/badge/node-20+-green.svg)](https://nodejs.org/)

基于 Claude 构建的通用 AI Agent 助手，类似于 Manus。

<img width="422" height="573" alt="截屏2026-01-07 15 21 03" src="https://github.com/user-attachments/assets/560e5f7a-8066-4f60-97a3-14106a33ffc3" />
<img width="405" height="485" alt="截屏2026-01-07 15 21 22" src="https://github.com/user-attachments/assets/bd3ff03a-fdd5-43ea-9f0f-7c1ba59f7040" />

**Powered by 易成 Kim**

## 功能特性

- **工具执行**：文件操作、Shell 命令、网络搜索和抓取
- **MCP 集成**：连接任意 MCP 服务器扩展能力
- **多模型路由**：智能路由到 Claude、GPT、通义千问等模型
- **记忆系统**：短期、工作和长期记忆，支持向量数据库
- **交互式权限**：敏感操作需要用户确认
- **代理支持**：支持 OneRouter、OpenRouter 等 API 代理

## 快速开始

### 一键安装

```bash
# 克隆仓库
git clone https://github.com/howtimeschange/honolulu.git
cd honolulu

# 安装所有依赖
./start.sh install

# 配置 API Key（创建 .env 文件）
cp .env.example .env
# 编辑 .env 填入你的 API Key

# 启动服务器
./start.sh
```

### 配置环境变量

在项目根目录创建 `.env` 文件：

```bash
# 直接使用 Anthropic API
ANTHROPIC_API_KEY=你的-anthropic-api-key

# 使用 OneRouter / OpenRouter 代理
ANTHROPIC_API_KEY=你的-onerouter-api-key
ANTHROPIC_BASE_URL=https://你的代理地址.com/api
```

### 开始使用

**终端 1 - 启动服务器：**
```bash
./start.sh
# 或
./start.sh server
```

**终端 2 - 启动 CLI：**
```bash
honolulu
# 或
./start.sh cli
```

### CLI 命令

```bash
honolulu                    # 交互模式
honolulu --help             # 查看帮助
honolulu -e "你好"           # 执行单条命令
honolulu -s http://ip:8420  # 连接远程服务器
```

## 项目架构

```
honolulu/
├── packages/
│   ├── core/                    # Python 后端
│   │   └── src/honolulu/
│   │       ├── agent.py         # Agent 主类
│   │       ├── models/          # 模型提供者 (Claude, OpenAI)
│   │       │   ├── claude.py    # Anthropic Claude
│   │       │   ├── openai_provider.py  # OpenAI 兼容接口
│   │       │   └── router.py    # 多模型路由
│   │       ├── tools/           # 工具实现
│   │       │   ├── builtin.py   # 文件、Bash、网络工具
│   │       │   └── mcp.py       # MCP 服务器集成
│   │       ├── memory/          # 记忆系统
│   │       │   ├── base.py      # 记忆管理器
│   │       │   └── vector_store.py  # ChromaDB 集成
│   │       ├── server/          # FastAPI 服务器
│   │       ├── permissions.py   # 权限控制器
│   │       └── config.py        # 配置管理
│   │
│   └── cli/                     # TypeScript CLI
│       └── src/
│           ├── index.ts         # CLI 入口
│           ├── client.ts        # API 客户端
│           └── ui/              # UI 组件
│
├── config/
│   └── default.yaml             # 配置文件
├── .env.example                 # 环境变量模板
├── .env                         # 你的环境变量（不会提交到 git）
└── start.sh                     # 快速启动脚本
```

## 配置说明

编辑 `config/default.yaml`：

```yaml
# 模型配置
model:
  provider: "anthropic"
  name: "claude-sonnet-4-20250514"
  api_key: "${ANTHROPIC_API_KEY}"
  base_url: "${ANTHROPIC_BASE_URL}"  # 可选：用于代理
  max_tokens: 8192

# 权限设置
permissions:
  mode: "interactive"  # auto | interactive | strict
  allowed_paths:
    - "${HOME}/projects/**"
  blocked_commands:
    - "rm -rf /"
    - "sudo"

# MCP 服务器（可选）
mcp_servers:
  - name: "filesystem"
    command: "npx"
    args: ["-y", "@anthropic/mcp-filesystem"]
```

## 内置工具

| 工具 | 描述 | 需要确认 |
|------|------|----------|
| `file_read` | 读取文件内容 | 否 |
| `file_write` | 写入/创建文件 | 是 |
| `file_list` | 列出目录内容 | 否 |
| `bash_exec` | 执行 Shell 命令 | 是 |
| `web_search` | 网络搜索 | 否 |
| `web_fetch` | 获取网页内容 | 否 |

## API 接口

### REST 端点

| 方法 | 端点 | 描述 |
|------|------|------|
| POST | `/api/chat` | 开始聊天会话 |
| GET | `/api/sessions` | 列出活跃会话 |
| DELETE | `/api/sessions/{id}` | 删除会话 |
| GET | `/api/tools` | 列出可用工具 |
| GET | `/docs` | Swagger UI 文档 |

### WebSocket

连接到 `/ws/{session_id}` 进行实时通信。

**服务器 → 客户端：**
- `thinking` - 正在处理
- `text` - 文本响应
- `tool_call` - 正在调用工具
- `confirm_request` - 需要确认
- `tool_result` - 执行结果
- `done` - 完成
- `error` - 发生错误

**客户端 → 服务器：**
- `message` - 用户消息
- `confirm_response` - 确认响应
- `cancel` - 取消操作

## 开发路线

- [x] 核心 Agent 及工具执行
- [x] 交互式权限系统
- [x] MCP 服务器集成
- [x] 多模型路由
- [x] 记忆系统（向量数据库）
- [x] OneRouter / 代理支持
- [ ] Web UI 界面
- [ ] 多 Agent 协作
- [ ] Docker 一键部署

## 参与贡献

欢迎贡献代码！请查看 [CONTRIBUTING.md](CONTRIBUTING.md) 了解详情。

## 开源协议

MIT License - 详见 [LICENSE](LICENSE) 文件
