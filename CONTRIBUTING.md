# Contributing to Honolulu

感谢你对 Honolulu 的兴趣！欢迎贡献代码、报告问题或提出建议。

## 开发环境设置

1. Fork 并克隆仓库

```bash
git clone https://github.com/YOUR_USERNAME/honolulu.git
cd honolulu
```

2. 安装依赖

```bash
# Python 后端
cd packages/core
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# TypeScript CLI
cd ../cli
npm install
```

3. 运行测试

```bash
# Python 测试
cd packages/core
pytest

# TypeScript 类型检查
cd packages/cli
npm run typecheck
```

## 提交 Pull Request

1. 创建新分支

```bash
git checkout -b feature/your-feature-name
```

2. 确保代码风格一致

```bash
# Python
cd packages/core
ruff check src/
ruff format src/

# TypeScript
cd packages/cli
npm run lint
```

3. 提交更改

```bash
git add .
git commit -m "feat: add your feature"
```

4. 推送并创建 PR

```bash
git push origin feature/your-feature-name
```

## Commit 规范

使用 [Conventional Commits](https://www.conventionalcommits.org/) 格式：

- `feat:` 新功能
- `fix:` Bug 修复
- `docs:` 文档更新
- `refactor:` 代码重构
- `test:` 测试相关
- `chore:` 构建/工具相关

## 报告问题

请在 [Issues](https://github.com/phodal/honolulu/issues) 中报告问题，包含：

1. 问题描述
2. 复现步骤
3. 期望行为
4. 实际行为
5. 环境信息（OS、Python 版本、Node 版本）

## 添加新工具

1. 在 `packages/core/src/honolulu/tools/` 创建新文件
2. 继承 `Tool` 基类
3. 实现 `execute` 方法
4. 在 `__init__.py` 中注册

示例：

```python
from honolulu.tools.base import Tool, ToolResult

class MyNewTool(Tool):
    name = "my_tool"
    description = "Description of what this tool does"
    parameters = {
        "type": "object",
        "properties": {
            "param1": {"type": "string", "description": "..."}
        },
        "required": ["param1"]
    }
    requires_confirmation = False  # 是否需要用户确认

    async def execute(self, param1: str, **kwargs) -> ToolResult:
        # 实现工具逻辑
        return ToolResult(success=True, output="result")
```

## 行为准则

- 尊重所有贡献者
- 保持友善和建设性的讨论
- 专注于代码和想法，而非个人

感谢你的贡献！🌋
