# Contributing to xianyu-guanjia

Thanks for your interest in contributing! Here's how to get started.

## Development Setup

```bash
git clone https://github.com/brianzhibo-design/XIANYUGUANJIA.git
cd XIANYUGUANJIA
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Project Layout

```
src/
├── cli.py              # CLI entry point
├── core/               # Framework: config, logging, drissionpage client, crypto, cookie_grabber
├── modules/            # Business logic: listing, operations, messages, orders, analytics
├── dashboard_server.py # Python Dashboard API server
└── integrations/       # Third-party integrations (xianguanjia)
client/                 # React frontend (Vite + Tailwind)
tests/                  # Python test suite
```

## How to Contribute

### Bug Reports

Open an [issue](https://github.com/brianzhibo-design/XIANYUGUANJIA/issues/new?template=bug_report.md) with:
- What you expected
- What actually happened
- Steps to reproduce
- Logs (from `bash service.sh status` or terminal output)

### Feature Requests

Open an [issue](https://github.com/brianzhibo-design/XIANYUGUANJIA/issues/new?template=feature_request.md) describing the use case.

### Pull Requests

1. Fork the repo
2. Create a feature branch: `git checkout -b feat/my-feature`
3. Make your changes
4. Run linting: `ruff check src/`
5. Run tests: `python -m pytest tests/ -x`
6. Commit with a clear message: `git commit -m "feat: add price optimization"`
7. Push to your fork and open a PR

### Commit Convention

We follow [Conventional Commits](https://www.conventionalcommits.org/):

| Prefix | When to use |
|--------|-------------|
| `feat:` | New feature |
| `fix:` | Bug fix |
| `docs:` | Documentation only |
| `refactor:` | Code restructuring (no behavior change) |
| `test:` | Adding or updating tests |
| `chore:` | Build, CI, dependency updates |

## Versioning (版本号规范)

项目遵循 [Semantic Versioning 2.0.0](https://semver.org/lang/zh-CN/) (语义化版本)。

版本号格式：`MAJOR.MINOR.PATCH`

| 变更类型 | 版本位 | 何时递增 | 示例 |
|----------|--------|---------|------|
| **MAJOR** | 主版本 | 架构重构、破坏性变更、大规模重写 | 移除 Node.js 后端 → 8.0.0 |
| **MINOR** | 次版本 | 新增功能（向后兼容） | 新增大件快运品类 → 8.1.0 |
| **PATCH** | 修订号 | Bug 修复、小优化（向后兼容） | 修复报价计算 → 8.1.1 |

### 版本号存储位置（唯一真相源）

版本号定义在 `src/__init__.py` 的 `__version__` 变量中。修改版本时 **必须同步更新**：

1. `src/__init__.py` — `__version__ = "X.Y.Z"` (Python 后端读取)
2. `package.json` — `"version": "X.Y.Z"` (npm 元数据)

`scripts/build_release.sh` 会自动从 `src/__init__.py` 读取版本号生成发布包，无需手动改。

### 何时更新版本号

- 每次准备发布新 Release 前更新，不要在开发中频繁修改
- git tag 必须与 `__version__` 一致：`git tag v8.0.0`
- GitHub Release 标题格式：`v8.0.0`

### 禁止事项

- 不得回退版本号（如从 8.0.0 改回 1.0.0）
- 不得跳过版本号（如从 8.0.0 跳到 10.0.0）
- 不得使用非数字后缀（如 8.0.0-beta）除非团队明确约定

## Code Style

- Python 3.10+
- Type hints everywhere
- Use `async/await` for I/O operations
- `loguru` for logging (not `print`)
- Structured JSON output from CLI commands

## Need Help?

Open an issue or start a [discussion](https://github.com/brianzhibo-design/XIANYUGUANJIA/discussions).
