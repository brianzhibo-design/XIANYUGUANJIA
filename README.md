<div align="center">

# 🦞 Xianyu OpenClaw — 闲鱼虚拟商品卖家自动化平台

[![CI](https://github.com/G3niusYukki/xianyu-openclaw/actions/workflows/ci.yml/badge.svg)](https://github.com/G3niusYukki/xianyu-openclaw/actions)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Node.js 18+](https://img.shields.io/badge/node.js-18+-green.svg)](https://nodejs.org/)
[![Coverage](https://img.shields.io/badge/coverage-95%25-brightgreen.svg)](tests/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**⚡ 从消息到履约，全流程自动化 · 从监控到告警，全链路可观测**

[English](#english) | [简体中文](#简介) | [快速开始](#-快速开始) | [文档](docs/)

</div>

---

## 📖 简介

**Xianyu OpenClaw（闲鱼管家）** 是专为闲鱼(Xianyu/Goofish)虚拟商品卖家设计的 **API-first 全自动化工作台**。

通过 WebSocket 直连闲鱼消息通道，结合 AI 实现智能回复、自动报价、商品管理和订单履约，帮助卖家实现 7×24 小时无人值守运营。

### 🎯 为什么创建这个项目？

闲鱼作为国内最大的二手交易平台，虚拟商品卖家面临以下痛点：

| 痛点 | 传统方案 | Xianyu OpenClaw 方案 |
|------|---------|---------------------|
| 消息回复不及时 | 人工盯盘，响应慢 | WebSocket 毫秒级接收 + AI 自动回复 |
| 报价效率低 | 手动计算，易出错 | 智能报价引擎，自动识别地址/重量/时效 |
| Cookie 频繁失效 | 手动更新，中断服务 | 后台自动刷新，无感知续期 |
| 多店铺管理困难 | 频繁切换账号 | 统一配置中心，支持多账号 |
| 异常无法及时感知 | 被动发现问题 | 多渠道告警（飞书/企微），关键事件不漏接 |

---

## 🎉 v2.0 重大更新

### 核心新功能

| 功能 | 描述 | 版本 |
|------|------|------|
| 🔐 **Cookie 静默自动刷新** | 后台守护线程每30分钟自动检查，失效时从浏览器静默获取新 Cookie | v2.0 |
| 📢 **多通道告警通知** | 支持飞书、企业微信 Webhook，覆盖售后、发货、人工接管等全场景 | v2.0 |
| 🎨 **可视化配置中心** | Cookie 配置页支持粘贴验证、AI 配置支持6家提供商引导 | v2.0 |
| 🔍 **API 可用性校验** | 实时健康检查面板，5大服务状态一目了然 | v2.0 |
| 💬 **双层消息去重** | 精确 hash + 内容 hash，防止重复回复 | v2.0 |
| 💰 **智能议价追踪** | 议价计数器辅助 AI 策略，自动识别讨价还价 | v2.0 |
| 🧹 **架构重构** | 清理 240+ 废弃文件，Python 后端统一化 | v2.0 |

---

## ✨ 核心功能

### 📨 消息自动化

```mermaid
graph LR
    A[买家消息] --> B[WebSocket 直连]
    B --> C[AI 意图识别]
    C --> D{意图类型}
    D -->|咨询| E[自动回复]
    D -->|议价| F[议价追踪]
    D -->|下单| G[订单处理]
    F --> H[AI 策略建议]
```

- **WebSocket 直连** — 毫秒级消息接收，无需轮询
- **AI 意图识别** — 自动识别咨询、议价、下单意图
- **双层去重** — 精确 hash + 内容 hash，防重复回复
- **议价追踪** — 智能计数器，辅助 AI 议价策略
- **合规护栏** — 禁词拦截、频率限制、审计日志

### 📦 商品自动化

- **AI 内容生成** — 标题、描述、标签一键生成
- **自动上架** — HTML模板 → 截图 → OSS → API发布
- **价格监控** — 自动调价、擦亮、上下架
- **多店铺管理** — 支持多账号切换和独立配置

### 🚚 订单自动化

- **自动发货** — 虚拟商品自动发卡密
- **物流同步** — 闲管家 API 对接，实时状态更新
- **售后处理** — 退款、退货自动识别和响应

### 📊 监控告警

- **Cookie 健康** — 自动检测、静默刷新、失效告警
- **服务状态** — 5大服务实时健康检查面板
- **多渠道告警** — 飞书/企业微信，关键事件不漏接
- **数据看板** — 曝光、转化、订单数据实时可视化

---

## 🏗️ 技术架构

### 系统架构图

```
┌─────────────────────────────────────────────────────────────────┐
│                     🎨 React 前端 (Vite)                        │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐           │
│  │ Dashboard│ │ 商品管理 │ │ 订单中心 │ │ 系统配置 │           │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘           │
└───────────────────────────┬─────────────────────────────────────┘
                            │ HTTP / WebSocket
┌───────────────────────────┴─────────────────────────────────────┐
│                   📦 Node.js 后端 (Express)                     │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐           │
│  │ 闲管家 API 代理│ │ 配置管理     │ │ Webhook 接收 │           │
│  └──────────────┘ └──────────────┘ └──────────────┘           │
└───────────────────────────┬─────────────────────────────────────┘
                            │
┌───────────────────────────┴─────────────────────────────────────┐
│                    🐍 Python 后端 (asyncio)                     │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐           │
│  │ WebSocket│ │ AI 服务  │ │ 报价引擎 │ │ 任务调度 │           │
│  │ 消息监听 │ │          │ │          │ │          │           │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘           │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐           │
│  │ Cookie   │ │ 告警通知 │ │ 数据分析 │ │ 合规中心 │           │
│  │ 自动刷新 │ │          │ │          │ │          │           │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘           │
└─────────────────────────────────────────────────────────────────┘
```

### 技术栈

| 层级 | 技术 | 说明 |
|------|------|------|
| **前端** | React 18 / Vite / TailwindCSS | 响应式管理面板，支持 PWA |
| **Node 后端** | Express / Joi | API 代理、配置校验、Webhook |
| **Python 后端** | Python 3.10+ / asyncio | 核心引擎：WebSocket、AI、调度 |
| **数据库** | SQLite / PostgreSQL | 开发用 SQLite，生产用 PostgreSQL |
| **消息队列** | 内存队列 + SQLite | 轻量级，无需额外依赖 |
| **AI 服务** | OpenAI 兼容 API | 支持 DeepSeek、阿里百炼、智谱等 |
| **通知** | HTTP Webhook | 飞书、企业微信、钉钉等 |

---

## 🚀 快速开始

### 环境要求

- Python 3.10+
- Node.js 18+
- Chrome 或 Edge 浏览器（Cookie 自动获取需要）
- 闲鱼账号 Cookie
- AI 服务 API Key

### 方式一：一键启动（推荐）

```bash
# 1. 克隆项目
git clone https://github.com/G3niusYukki/xianyu-openclaw.git
cd xianyu-openclaw

# 2. 一键启动（自动安装所有依赖）
# macOS / Linux
./start.sh

# Windows
start.bat
```

一键启动脚本会自动完成：Python 虚拟环境创建、pip 依赖安装、Playwright Chromium 浏览器下载（首次约 150MB）、Node.js 依赖安装、启动所有服务。

### 方式二：手动安装

```bash
# 1. 克隆项目
git clone https://github.com/G3niusYukki/xianyu-openclaw.git
cd xianyu-openclaw

# 2. 安装 Python 依赖
python3 -m venv .venv && source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# 3. 安装 Playwright Chromium 浏览器（Cookie 自动获取和消息服务需要）
playwright install chromium

# 4. 安装 Node.js 依赖
cd server && npm install && cd ..
cd client && npm install && cd ..

# 5. 配置环境变量
cp .env.example .env
# 编辑 .env，填入 Cookie 和 AI Key

# 6. 启动服务（需要3个终端窗口）

# 终端1 - Python 后端（必需，处理核心API）
python -m src.dashboard_server --port 8091

# 终端2 - Node.js 后端
npm run dev:server

# 终端3 - React 前端
npm run dev:client
```

访问地址：
- **前端面板**: http://localhost:5173
- **Python API**: http://localhost:8091
- **Node API**: http://localhost:3001

> **注意**：前端代理配置指向 Python 后端 8091 端口，必须先启动 Python 服务，否则前端页面无法正常工作。

### 方式三：Docker 一键部署

```bash
cp .env.example .env
# 编辑 .env 填入配置
docker compose up -d
```

---

## 📖 使用指南

### 首次配置

1. **系统配置** → 填入 AI 服务商信息（支持6家提供商引导）
2. **店铺管理** → 粘贴 Cookie，点击验证
3. **告警通知** → 配置飞书/企业微信 Webhook
4. **启动监控** → Cookie 自动刷新和消息监听将自动运行

### 核心工作流

```
买家消息 → WebSocket 接收 → AI 意图识别 → 自动回复/报价
                ↓
        议价意图 → 议价计数器 → AI 策略建议
                ↓
        下单意向 → 订单同步 → 自动发货
                ↓
        异常情况 → 多渠道告警 → 人工接管
```

---

## ⚙️ 配置说明

### 环境变量 (.env)

```bash
# 闲鱼 Cookie（必需）
XIANYU_COOKIE_1=your_cookie_here

# AI 配置（必需）
AI_PROVIDER=deepseek
AI_API_KEY=sk-...
AI_BASE_URL=https://api.deepseek.com/v1
AI_MODEL=deepseek-chat

# Cookie 自动刷新（可选）
COOKIE_AUTO_REFRESH=true
COOKIE_REFRESH_INTERVAL=30

# 端口配置（可选）
FRONTEND_PORT=5173
NODE_PORT=3001
PYTHON_PORT=8091
```

### 系统配置页面

v2.0 新增可视化配置：
- **AI 设置** - 6家提供商引导卡片，一键切换
- **Cookie 设置** - 粘贴验证、实时评级、获取指南
- **告警通知** - Webhook 配置、事件开关、测试发送
- **闲管家 API** - AppKey / Secret 管理

---

## 📊 监控告警

### 实时健康面板

Dashboard 集成 5 大服务状态：
- 🟢 Node 后端
- 🟢 Python 后端  
- 🟢 Cookie 健康
- 🟢 AI 服务
- 🟢 闲管家 API

### 告警场景

| 场景 | 级别 | 通知渠道 |
|------|------|----------|
| Cookie 过期 | P0 | 飞书 + 企业微信 |
| Cookie 自动刷新成功 | P1 | 飞书 |
| 售后介入 | P1 | 飞书 |
| 发货失败 | P1 | 飞书 |
| 人工接管 | P2 | 飞书 |

---

## 🗂️ 项目结构

```
xianyu-openclaw/
├── src/                          # Python 后端
│   ├── main.py                   # 主入口
│   ├── cli.py                    # CLI 工具
│   ├── dashboard_server.py       # Dashboard API
│   ├── core/                     # 核心模块
│   │   ├── cookie_health.py      # Cookie 健康检查
│   │   ├── cookie_grabber.py     # Cookie 自动刷新
│   │   ├── notify.py             # 通知模块
│   │   └── playwright_client.py  # 浏览器自动化
│   └── modules/                  # 业务模块
│       ├── messages/             # 消息（去重、议价、回复）
│       │   ├── service.py        # 消息服务
│       │   ├── reply_engine.py   # 回复引擎
│       │   └── bargain_tracker.py # 议价追踪
│       ├── listing/              # 商品（上架、模板、OSS）
│       │   ├── service.py        # 商品服务
│       │   ├── auto_publish.py   # 自动发布
│       │   └── image_generator.py # 图片生成
│       ├── orders/               # 订单（同步、发货）
│       │   ├── service.py        # 订单服务
│       │   └── xianguanjia.py    # 闲管家集成
│       ├── virtual_goods/        # 虚拟商品（卡密）
│       ├── quote/                # 报价引擎
│       │   ├── engine.py         # 报价核心
│       │   └── providers.py      # 报价数据源
│       └── accounts/             # 账号管理
├── server/                       # Node.js 后端
│   └── src/
│       ├── routes/
│       │   ├── xianguanjia.js    # 闲管家代理
│       │   └── config.js         # 配置管理
├── client/                       # React 前端
│   └── src/
│       ├── pages/                # 页面
│       │   ├── config/           # 系统配置
│       │   ├── accounts/         # 店铺管理
│       │   └── dashboard/        # 数据看板
│       └── components/           # 组件
│           ├── ApiStatusPanel.jsx    # 状态面板
│           └── SetupGuide.jsx        # 引导组件
├── tests/                        # 测试（覆盖率 95%）
├── config/                       # 配置模板
├── docs/                         # 文档
│   ├── PROJECT_PLAN.md           # 项目规划
│   ├── reviews/                  # 代码审查
│   └── xianguanjia-api.md        # 闲管家 API 文档
├── database/                     # 数据库迁移
├── docker-compose.yml            # Docker 编排
└── scripts/                      # 脚本工具
```

---

## 🛠️ 开发指南

```bash
# 开发模式（需要同时运行3个服务）
python -m src.dashboard_server --port 8091  # Python 后端（必需）
npm run dev:server                          # Node 后端
npm run dev:client                          # React 前端

# 或使用 Docker（推荐新手）
docker compose up -d
python -m src.cli doctor --strict

# 测试
pytest tests/ --cov=src --cov-report=html
ruff check src/
ruff format src/

# 构建
cd client && npm run build
```

---

## ❓ 常见问题

### Cookie 自动获取失败 / 无法打开浏览器窗口

**症状**：Dashboard 点击"自动获取 Cookie"显示"无法启动浏览器"或"所有获取方式均失败"。

**解决**：
1. 确认已安装 Playwright 浏览器：`playwright install chromium`
2. 确认本机已安装 Chrome 或 Edge 浏览器
3. 如需静默自动刷新（Level 1），需在本机 Chrome/Edge 中至少登录一次闲鱼

### Cookie 频繁失效 / WebSocket 断连

**症状**：消息监听中断，日志出现 `FAIL_SYS_USER_VALIDATE`。

**解决**：
1. 保持本机 Chrome/Edge 浏览器开启且闲鱼已登录，系统会自动从浏览器读取最新 Cookie
2. 确认 `COOKIE_AUTO_REFRESH=true` 已在 `.env` 中设置
3. 如无法保持浏览器登录，可在 Dashboard 手动粘贴 Cookie

### Windows 上 Playwright 安装失败

**症状**：`playwright install chromium` 报错或超时。

**解决**：
1. 确认网络可以访问 `cdn.playwright.dev`
2. 如网络受限，可设置代理：`set HTTPS_PROXY=http://proxy:port` 后重试
3. 使用一键启动脚本 `start.bat` 会自动处理安装

---

## 📝 更新日志

### v2.0.0 (2026-03-07)

**新增功能**
- 🔐 Cookie 静默自动刷新（rookiepy + Playwright）
- 📢 飞书/企业微信告警通知
- 🎨 可视化配置中心（Cookie、AI、告警）
- 🔍 API 可用性实时健康面板
- 💬 双层消息去重（精确 hash + 内容 hash）
- 💰 智能议价追踪计数器

**架构优化**
- 🧹 清理 src/lite/ 等 240+ 废弃文件
- 📦 新增 src/core/notify.py 通用通知模块
- 🔧 统一配置管理，支持前端可视化编辑
- 📊 测试覆盖率提升至 95%

**Bug 修复**
- 修复 CI lint 错误（ruff + bandit）
- 修复测试冲突（conversion_rate_placeholder）
- 修复 axios 导入重复问题

[查看完整更新日志](CHANGELOG.md)

---

## 🤝 参与贡献

欢迎贡献代码！请阅读 [CONTRIBUTING.md](CONTRIBUTING.md) 了解规范。

### 贡献流程

1. Fork 仓库
2. 创建功能分支 (`git checkout -b feature/amazing`)
3. 提交更改 (`git commit -m 'feat: add amazing'`)
4. 推送分支 (`git push origin feature/amazing`)
5. 创建 Pull Request

---

## 📄 许可证

[MIT](LICENSE) © 2026 G3niusYukki

---

## 💬 联系我们

- **GitHub Issues**: 功能建议和 Bug 报告
- **Email**: 详见 GitHub Profile

---

## ⚠️ 免责声明

本工具仅供学习研究使用，请遵守闲鱼平台规则和相关法律法规。使用者需自行承担使用风险。

---

## English

### Introduction

**Xianyu OpenClaw** is an API-first full-automation workbench designed for virtual goods sellers on Xianyu (Goofish), China's largest second-hand trading platform.

By connecting directly to Xianyu's message channel via WebSocket and combining AI for intelligent replies, automatic quoting, product management, and order fulfillment, it helps sellers achieve 7×24 hour unattended operation.

### Key Features

- **Message Automation** — WebSocket direct connection, AI intent recognition, double-layer deduplication
- **Product Automation** — AI content generation, automatic listing, price monitoring
- **Order Automation** — Automatic delivery for virtual goods, logistics sync, after-sales handling
- **Monitoring & Alerting** — Cookie health monitoring, multi-channel alerts (Lark/WeCom), real-time dashboard

### Quick Start

```bash
git clone https://github.com/G3niusYukki/xianyu-openclaw.git
cd xianyu-openclaw

# One-click start (recommended, auto-installs everything)
# macOS / Linux
./start.sh
# Windows
start.bat

# Or manual install:
python3 -m venv .venv && source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
playwright install chromium    # Required for cookie auto-grab
cd server && npm install && cd ../client && npm install && cd ..
cp .env.example .env
# Edit .env with your Cookie and AI Key
```

Access:
- Frontend: http://localhost:5173
- Python API: http://localhost:8091
- Node API: http://localhost:3001

---

<div align="center">

Made with ❤️ by G3niusYukki

</div>
