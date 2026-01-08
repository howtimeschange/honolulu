# Honolulu v0.1.0

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Node.js 20+](https://img.shields.io/badge/node-20+-green.svg)](https://nodejs.org/)

基于 Claude 构建的通用 AI Agent 助手，类似于 Manus。

<img width="422" height="573" alt="截屏2026-01-07 15 21 03" src="https://github.com/user-attachments/assets/560e5f7a-8066-4f60-97a3-14106a33ffc3" />
<img width="405" height="485" alt="截屏2026-01-07 15 21 22" src="https://github.com/user-attachments/assets/bd3ff03a-fdd5-43ea-9f0f-7c1ba59f7040" />

**Powered by 易成 Kim**

## 产品形态

Honolulu 提供多种交互方式，满足不同场景需求：

| 形态 | 状态 | 说明 |
|------|------|------|
| **Web UI** | ✅ 已实现 | 现代化浏览器界面，支持实时聊天、文件上传、可视化配置 |
| **CLI 命令行** | ✅ 已实现 | 终端交互模式，适合开发者和自动化场景 |
| **桌面客户端** | 🚧 规划中 | 原生桌面应用，打造用户电脑中的超级 AI 助手 |
| **移动端** | 📋 远期规划 | iOS/Android 应用，随时随地使用 AI 助手 |

## 功能特性

- **Web UI 界面**：现代化 React 界面，支持实时聊天、文件上传、工具调用可视化
- **CLI 命令行**：终端交互模式，适合开发者和脚本自动化
- **流式响应**：打字机效果实时显示 AI 回复
- **工具执行**：文件操作、Shell 命令、网络搜索和抓取
- **MCP 集成**：连接任意 MCP 服务器扩展能力，支持可视化配置
- **多模型路由**：智能路由到 Claude、GPT、通义千问等模型
- **配置热加载**：Provider 配置更改即时生效，无需重启
- **记忆系统**：短期、工作和长期记忆，支持向量数据库
- **交互式权限**：敏感操作需要用户确认
- **代理支持**：支持 OneRouter、OpenRouter 等 API 代理
- **多 Agent 协作**：支持 Orchestrator 模式调度多个专业子 Agent

## 快速开始

### 1. 安装

```bash
# 克隆仓库
git clone https://github.com/howtimeschange/honolulu.git
cd honolulu

# 一键安装所有依赖
./start.sh install
```

### 2. 配置 API Key

```bash
# 方式一：创建 .env 文件（推荐）
cp .env.example .env
# 编辑 .env 填入你的 API Key

# 方式二：直接设置环境变量
export ANTHROPIC_API_KEY='你的-api-key'
```

### 3. 启动使用

**方式一：一键启动（推荐）**
```bash
./start.sh dev
# 自动启动服务器 + Web UI，并打开浏览器
```

**方式二：Web UI 模式**
```bash
# 终端 1 - 启动后端服务器
./start.sh server

# 终端 2 - 启动 Web UI
./start.sh web

# 打开浏览器访问 http://localhost:5173
```

**方式三：CLI 命令行模式**
```bash
# 终端 1 - 启动后端服务器
./start.sh server

# 终端 2 - 启动 CLI
./start.sh cli
# 或直接运行
honolulu
```

### CLI 命令参考

```bash
honolulu                    # 交互模式
honolulu --help             # 查看帮助
honolulu -e "你好"           # 执行单条命令
honolulu -s http://ip:8420  # 连接远程服务器
```

### start.sh 命令参考

```bash
./start.sh install   # 安装所有依赖
./start.sh dev       # 一键启动服务器 + Web UI
./start.sh server    # 仅启动 API 服务器
./start.sh web       # 仅启动 Web UI
./start.sh cli       # 启动 CLI
./start.sh test      # 运行测试
./start.sh help      # 查看帮助
```

## 项目架构

```
honolulu/
├── packages/
│   ├── core/                    # Python 后端
│   │   └── src/honolulu/
│   │       ├── agent.py         # Agent 主类
│   │       ├── agents/          # 多 Agent 系统
│   │       │   ├── orchestrator.py  # 编排器
│   │       │   └── specialist.py    # 专业 Agent
│   │       ├── models/          # 模型提供者
│   │       │   ├── claude.py    # Anthropic Claude
│   │       │   ├── openai_provider.py  # OpenAI 兼容接口
│   │       │   └── router.py    # 多模型路由
│   │       ├── tools/           # 工具实现
│   │       │   ├── builtin.py   # 文件、Bash、网络工具
│   │       │   ├── mcp.py       # MCP 服务器集成
│   │       │   └── pdf_extractor.py  # PDF 文本提取
│   │       ├── memory/          # 记忆系统
│   │       │   ├── base.py      # 记忆管理器
│   │       │   └── vector_store.py  # ChromaDB 集成
│   │       ├── server/          # FastAPI 服务器
│   │       │   └── app.py       # API 端点
│   │       ├── permissions.py   # 权限控制器
│   │       └── config.py        # 配置管理
│   │
│   ├── web/                     # React Web UI
│   │   └── src/
│   │       ├── App.tsx          # 主应用
│   │       ├── components/      # UI 组件
│   │       │   ├── ChatPanel/   # 聊天面板
│   │       │   ├── Sidebar/     # 侧边栏
│   │       │   ├── WorkPanel/   # 工作面板
│   │       │   └── Settings/    # 设置面板
│   │       ├── hooks/           # React Hooks
│   │       └── utils/           # 工具函数
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

## Web UI 功能

### 聊天界面
- 实时流式响应（打字机效果）
- Markdown 渲染和代码高亮
- 文件上传支持（图片、PDF）
- 会话历史持久化

### 设置面板
- **Model Providers**：配置多个模型提供商（Anthropic、OpenAI 等）
  - 支持自定义 API Key 和 Base URL
  - 配置热加载，无需重启服务器
- **MCP Servers**：可视化配置 MCP 服务器
  - 预设模板（Filesystem、GitHub、Brave Search 等）
  - 环境变量配置

### 工作面板
- 工具调用历史和状态
- 文件预览
- 权限确认对话框

## 配置说明

### 环境变量

在项目根目录创建 `.env` 文件：

```bash
# 直接使用 Anthropic API
ANTHROPIC_API_KEY=你的-anthropic-api-key

# 使用 OneRouter / OpenRouter / GLM / Kimi 代理
ANTHROPIC_API_KEY=你的-第三方-api-key
ANTHROPIC_BASE_URL=https://你的代理地址.com/api

# 可选：OpenAI API（用于多模型路由）
OPENAI_API_KEY=你的-openai-api-key
```

### 配置文件

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

# 多模型路由（可选）
routing:
  enabled: false
  strategy: "quality-first"  # cost-optimized | quality-first | round-robin
  fallback_enabled: true
  providers:
    - name: "claude"
      type: "anthropic"
      api_key: "${ANTHROPIC_API_KEY}"
      model: "claude-sonnet-4-20250514"
      priority: 100
      is_default: true
    - name: "gpt4"
      type: "openai"
      api_key: "${OPENAI_API_KEY}"
      model: "gpt-4o"
      priority: 90
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
| `pdf_extract` | 提取 PDF 文本 | 否 |

## API 接口

### REST 端点

| 方法 | 端点 | 描述 |
|------|------|------|
| POST | `/api/chat` | 开始聊天会话 |
| GET | `/api/sessions` | 列出活跃会话 |
| DELETE | `/api/sessions/{id}` | 删除会话 |
| GET | `/api/tools` | 列出可用工具 |
| GET | `/api/config/providers` | 获取 Provider 配置 |
| GET | `/api/config/mcp` | 获取 MCP 配置 |
| PUT | `/api/config` | 更新配置（热加载） |
| POST | `/api/config/reload` | 手动触发配置重载 |
| GET | `/docs` | Swagger UI 文档 |

### WebSocket

连接到 `/ws/{session_id}` 进行实时通信。

**服务器 → 客户端：**
- `thinking` - 正在处理
- `text_delta` - 流式文本片段
- `text` - 完整文本响应
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

### 已完成
- [x] 核心 Agent 及工具执行
- [x] 交互式权限系统
- [x] MCP 服务器集成
- [x] 多模型路由
- [x] 记忆系统（向量数据库）
- [x] OneRouter / 代理支持
- [x] Web UI 界面
- [x] CLI 命令行界面
- [x] 流式响应 / 打字机效果
- [x] 文件上传（图片、PDF）
- [x] 设置面板（Provider / MCP 配置）
- [x] 配置热加载
- [x] 多 Agent 协作框架

### 进行中
- [ ] Agent 市场 / 插件系统
- [ ] Docker 一键部署

### 远期规划
- [ ] **桌面客户端**（Electron/Tauri）- 打造用户电脑中的超级 AI 助手
- [ ] 移动端适配（iOS/Android）
- [ ] 语音交互
- [ ] 屏幕共享与操作
- [ ] 本地知识库
- [ ] 自定义 Agent 工作流

## 愿景

Honolulu 的目标是成为用户电脑中的**超级 AI 助手**：

- **随时待命**：桌面客户端常驻后台，随时唤起
- **全能助手**：文件管理、代码开发、信息检索、日程管理...
- **隐私优先**：本地运行，数据不离开用户电脑
- **无限扩展**：通过 MCP 协议连接任意工具和服务

## 参与贡献

欢迎贡献代码！请查看 [CONTRIBUTING.md](CONTRIBUTING.md) 了解详情。

## 开源协议

MIT License - 详见 [LICENSE](LICENSE) 文件
