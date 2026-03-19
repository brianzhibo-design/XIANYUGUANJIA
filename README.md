<p align="center">
  <h1 align="center">闲鱼管家</h1>
  <p align="center">
    闲鱼自动化运营平台 — AI 智能客服 · 自动报价 · 订单履约 · 实时监控
  </p>
</p>

<p align="center">
  <a href="https://github.com/brianzhibo-design/XIANYUGUANJIA/actions/workflows/ci.yml"><img src="https://github.com/brianzhibo-design/XIANYUGUANJIA/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="https://github.com/brianzhibo-design/XIANYUGUANJIA/releases/latest"><img src="https://img.shields.io/github/v/release/brianzhibo-design/XIANYUGUANJIA?label=release" alt="Release"></a>
  <img src="https://img.shields.io/badge/python-3.12-blue" alt="Python">
  <img src="https://img.shields.io/badge/tests-1224-green" alt="Tests">
  <a href="./LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue" alt="License"></a>
</p>

---

## 核心特性

- **AI 智能客服** — 接入 DeepSeek/通义千问等大语言模型，根据商品信息自动报价、上下文感知回复，支持多轮对话
- **物流自动报价** — 全国快递实时比价（圆通/中通/申通/韵达/极兔/菜鸟），按重量、体积、线路智能选择最优方案
- **订单全链路履约** — 虚拟商品自动发卡密、实物订单自动提交物流单，状态跟踪闭环
- **多级 Cookie 保活** — 闲管家 IM 直读 → CookieCloud 同步 → 本地持久化 → Playwright 硬解滑块，四级降级策略
- **实时 Dashboard** — React + TailwindCSS 现代化仪表盘，状态监控、数据分析、配置热更新
- **一键在线更新** — Dashboard 内置版本检查、SHA256 校验、自动备份、失败回滚

---

## 架构

```
┌─────────────────────────────────────────────────────────────┐
│  React Dashboard (Vite + TailwindCSS)         :5173 / dist │
└──────────────────────┬──────────────────────────────────────┘
                       │ REST API
┌──────────────────────▼──────────────────────────────────────┐
│  Dashboard Server (BaseHTTPRequestHandler)           :8091  │
│  ├── routes/system.py    — 健康检查·版本·更新               │
│  ├── routes/config.py    — 配置 CRUD                        │
│  ├── routes/products.py  — 商品管理                         │
│  └── routes/orders.py    — 订单管理                         │
├─────────────────────────────────────────────────────────────┤
│  Core Modules                                               │
│  ├── messages/   — WebSocket 长连接·消息收发·AI 回复·去重    │
│  ├── quote/      — 快递比价·报价引擎·成本表                 │
│  ├── orders/     — 订单同步·价格执行·虚拟发货               │
│  ├── listing/    — 商品发布·批量改价·模板管理               │
│  ├── analytics/  — 数据统计·趋势分析                        │
│  └── compliance/ — 合规检查·敏感词过滤                      │
├─────────────────────────────────────────────────────────────┤
│  Integrations                                               │
│  ├── 闲鱼 WebSocket  — 实时消息通道                         │
│  ├── 闲管家开放平台   — 订单/发货/改价 API                   │
│  └── AI Provider     — DeepSeek / 通义千问 / OpenAI         │
└─────────────────────────────────────────────────────────────┘
```

---

## 快速开始

### 环境要求

- Python 3.10+（推荐 3.12）
- Node.js 18+（推荐 20）
- macOS / Linux / Windows

### 1. 克隆并初始化

```bash
git clone https://github.com/brianzhibo-design/XIANYUGUANJIA.git
cd XIANYUGUANJIA

python3 -m venv .venv
source .venv/bin/activate    # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2. 配置

```bash
cp .env.example .env
```

编辑 `.env`，填入以下必需项：

| 变量 | 说明 | 获取方式 |
|------|------|----------|
| `XIANYU_COOKIE_1` | 闲鱼登录 Cookie | 浏览器 F12 或 Dashboard 自动获取 |
| `AI_API_KEY` | AI 服务密钥 | [DeepSeek](https://platform.deepseek.com/) 等平台申请 |
| `AI_BASE_URL` | AI API 地址 | 如 `https://api.deepseek.com/v1` |
| `AI_MODEL` | 模型名称 | 如 `deepseek-chat` |
| `XGJ_APP_KEY` | 闲管家 AppKey | [闲管家开放平台](https://open.goofish.pro) 注册 |
| `XGJ_APP_SECRET` | 闲管家 AppSecret | 同上 |

### 3. 启动

```bash
# 后端
python -m src.main

# 前端（开发模式）
cd client && npm install && npm run dev
```

访问 `http://localhost:5173` 进入 Dashboard。

> **macOS 用户**：可直接运行 `bash scripts/macos/start.command` 一键启动。

---

## 项目结构

```
├── src/                          # Python 后端
│   ├── __init__.py               # 版本号 (SSOT)
│   ├── main.py                   # 入口
│   ├── cli.py                    # CLI 工具
│   ├── dashboard_server.py       # HTTP 服务器
│   ├── core/                     # 框架层: 配置·日志·加密·Cookie
│   ├── dashboard/                # Dashboard API 路由
│   ├── modules/                  # 业务模块
│   │   ├── messages/             #   消息: WS 通信·AI 回复·去重·工作流
│   │   ├── quote/                #   报价: 快递比价·成本表·报价引擎
│   │   ├── orders/               #   订单: 同步·改价·履约
│   │   ├── listing/              #   商品: 发布·模板·批量操作
│   │   ├── virtual_goods/        #   虚拟商品: 卡密发货·状态闭环
│   │   ├── analytics/            #   数据: 统计·趋势
│   │   └── compliance/           #   合规: 风控·敏感词
│   └── integrations/             # 第三方集成 (闲管家)
├── client/                       # React 前端 (Vite + TailwindCSS)
│   ├── src/
│   │   ├── pages/                #   页面
│   │   ├── components/           #   组件
│   │   └── api/                  #   API 客户端
│   └── dist/                     #   构建产物
├── tests/                        # 1224 个单元测试
├── config/                       # YAML 配置文件
├── scripts/                      # 运维脚本
│   ├── release.sh                #   一键发版
│   ├── bump_version.sh           #   版本号同步
│   ├── build_release.sh          #   构建离线安装包
│   ├── update.sh / update.bat    #   在线更新
│   └── macos/ / windows/         #   平台专用脚本
└── .github/workflows/            # CI/CD
    ├── ci.yml                    #   Lint + Test + Security
    └── release.yml               #   自动构建 + 发布 Release
```

---

## 开发

### 测试

```bash
# 运行全部测试
pytest tests/ -v --cov=src

# 运行指定模块测试
pytest tests/test_quote_engine.py -v

# 跳过慢测试
pytest tests/ -m "not slow"
```

### 代码规范

```bash
# Lint
ruff check src/

# 格式化
ruff format src/

# 类型检查
mypy src/
```

### 发版

```bash
# 一键发版（bump + build + commit + push + create release + upload asset）
bash scripts/release.sh 9.3.0
```

---

## 技术栈

| 层 | 技术 |
|----|------|
| 后端 | Python 3.12, asyncio, WebSocket, httpx |
| 前端 | React 18, TypeScript, Vite, TailwindCSS, Recharts |
| 数据 | SQLite (WAL mode), JSON 配置 |
| AI | DeepSeek / 通义千问 / OpenAI (兼容 OpenAI API 格式) |
| 自动化 | DrissionPage (CDP), Playwright (备用) |
| CI/CD | GitHub Actions, Ruff, pytest, Bandit, pip-audit |
| 部署 | macOS LaunchAgent / Windows 服务 / 手动部署 |

---

## 贡献

欢迎提交 PR。详见 [CONTRIBUTING.md](./CONTRIBUTING.md)。

提交前请确保：
1. `ruff check src/` 无报错
2. `pytest tests/ -v --cov=src` 全部通过

## License

[MIT](./LICENSE)
