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
  <img src="https://img.shields.io/badge/react-18-blue" alt="React">
  <a href="./LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue" alt="License"></a>
</p>

---

## 这是什么

闲鱼管家是一个为闲鱼卖家设计的**本地自动化运营工作台**，帮助你自动化处理日常运营中最繁琐的重复性工作。

它的设计理念是：**买来就能用，用了就离不开**。全程通过浏览器中的管理面板（Dashboard）操作，无需对接 API、写代码或折腾服务器。

---

## 核心功能

### AI 智能客服

买家发来消息后，系统自动识别意图并回复：

- **自动报价**：根据商品信息和买家收货地址，AI 自动计算最优快递方案并回复报价（支持圆通、中通、申通、韵达、极兔、德邦、顺丰、京东等）
- **上下文感知**：记住当前会话的商品信息，支持多轮对话，不会答非所问
- **意图分类**：自动识别买家意图（询价、议价、发货、查件、退款等），分流到对应处理流程
- **合规兜底**：内置敏感词过滤 + 发送前合规检查，避免账号风控
- **人工介入**：卖家在闲鱼手动发消息后，该会话自动暂停自动回复，避免人工和机器人话术冲突

### 物流自动报价引擎

- **实时比价**：聚合多家快递公司实时报价，按重量、体积、目的地智能排序
- **成本表管理**：支持 Excel 导入自定义成本价，加价比例和安全边距均可配置
- **地理解析**：自动识别买家收货地址的省市区，匹配对应快递线路
- **多级地址**：支持大件快运（同城/省内/跨省/偏远地区）和小件快递两套报价体系

### 订单全链路履约

- **虚拟商品自动发货**：买家付款后，自动发送卡密/兑换码，无需手动操作
- **实物订单自动发货**：支持闲管家开放平台 API 自动提交物流单
- **价格自动调整**：根据配置规则，在买家议价时自动执行降价操作
- **闲管家回调闭环**：支持闲管家订单推送，支付后自动同步订单状态

### 多账号管理

- 支持多闲鱼账号同时运营，每个账号独立 Cookie、独立配置
- 账号健康监控：自动检测 Cookie 有效性，过期前告警
- Cookie 自动刷新：内置四级降级策略（闲管家 IM → CookieCloud → 本地持久化 → Playwright 滑块验证）

### 商品管理与发布

- 商品发布：支持图片模板合成、批量发布
- 批量改价：根据策略自动调整商品价格
- 商品列表管理：上下架、编辑、同步状态

### 实时 Dashboard

- **状态监控**：Cookie 健康度、消息处理量、订单履约进度实时展示
- **数据分析**：成交趋势、客服效率、快递成本等运营数据图表
- **配置热更新**：所有配置修改实时生效，无需重启服务
- **一键更新**：内置版本检查 + SHA256 校验 + 自动备份 + 失败回滚

---

## 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│  React Dashboard (Vite + TailwindCSS)                       │
│  端口：5173（开发）/ 静态构建产物（生产）                    │
│  ─ 管理面板 UI / 消息沙盒 / 订单管理 / 数据分析 / 系统配置   │
└──────────────────────┬──────────────────────────────────────┘
                       │  REST API (JSON)
┌──────────────────────▼──────────────────────────────────────┐
│  Dashboard Server  (Python ThreadingHTTPServer)             │
│  端口：8091                                                  │
│  ├── routes/system.py    — 健康检查 / 版本 / 在线更新        │
│  ├── routes/config.py    — 系统配置 CRUD                     │
│  ├── routes/cookie.py   — Cookie 管理                       │
│  ├── routes/products.py — 商品管理                           │
│  ├── routes/orders.py  — 订单管理                           │
│  ├── routes/messages.py — 消息查询                          │
│  ├── routes/quote.py    — 报价查询                          │
│  └── routes/slider.py   — 滑块验证                          │
├─────────────────────────────────────────────────────────────┤
│  业务模块（src/modules/）                                    │
│  ├── messages/  — WebSocket 闲鱼长连接 / AI 回复 / 去重     │
│  ├── quote/     — 快递比价 / 成本表 / 报价引擎              │
│  ├── orders/    — 订单同步 / 改价 / 履约                    │
│  ├── listing/   — 商品发布 / 图片模板 / 批量操作             │
│  ├── virtual_goods/ — 虚拟商品 / 卡密发货                   │
│  ├── analytics/ — 数据统计 / 趋势分析 / 报表生成             │
│  ├── ticketing/ — 票务识别 / 智能应答                      │
│  ├── compliance/ — 敏感词过滤 / 合规检查                    │
│  └── accounts/  — 多账号管理 / 健康监控                      │
├─────────────────────────────────────────────────────────────┤
│  核心层（src/core/）                                         │
│  ├── config.py      — 配置加载（YAML / .env / Dashboard）    │
│  ├── crypto.py      — AES-256 Cookie 加密存储                │
│  ├── cookie_grabber.py — DrissionPage 浏览器自动化          │
│  ├── cookie_health.py — Cookie 健康度检测                   │
│  ├── logger.py      — loguru 日志                           │
│  └── error_handler.py — 统一错误处理                         │
├─────────────────────────────────────────────────────────────┤
│  第三方集成（src/integrations/xianguanjia/）                 │
│  ├── 闲管家开放平台 — 订单查询 / 改价 / 发货 API            │
│  ├── 闲鱼 WebSocket  — 实时消息通道                         │
│  └── AI Provider     — DeepSeek / 通义千问 / OpenAI 等       │
└─────────────────────────────────────────────────────────────┘
```

---

## 技术栈

| 层级 | 技术选型 |
|------|---------|
| 后端语言 | Python 3.12 |
| HTTP 服务器 | Python stdlib `ThreadingHTTPServer`（零依赖） |
| 异步通信 | `asyncio` + `httpx` + `websockets` |
| 数据验证 | Pydantic 2.5+ |
| 浏览器自动化 | DrissionPage（CDP 协议） + Playwright（备用） |
| 加密 | `cryptography`（Fernet / AES-256） |
| 数据库 | SQLite（WAL 模式） |
| 图片处理 | Pillow + OpenCV |
| AI 接入 | OpenAI 兼容接口（DeepSeek / 通义千问 / 智谱 / 火山方舟） |
| 前端框架 | React 18 + TypeScript 5 |
| 前端构建 | Vite 5 |
| 样式方案 | TailwindCSS 3.3 |
| 路由 | react-router-dom 6 |
| 图表 | Recharts |
| 代码规范 | Ruff（lint + format） |
| 测试 | pytest + pytest-asyncio + pytest-cov |
| 安全扫描 | Bandit + pip-audit |
| CI/CD | GitHub Actions |

---

## 项目结构

```
XIANYUGUANJIA/
├── src/                         # Python 后端（版本号：9.5.0）
│   ├── __init__.py              #   __version__ 唯一真相源
│   ├── main.py                  #   主入口（多模块协调启动）
│   ├── cli.py                   #   命令行工具
│   ├── dashboard_server.py      #   Dashboard HTTP 服务入口
│   ├── setup_wizard.py           #   首次启动配置向导
│   │
│   ├── core/                    #   框架核心层
│   │   ├── config.py            #     配置加载（优先级：.env > YAML > 默认值）
│   │   ├── config_models.py      #     Pydantic 配置模型
│   │   ├── crypto.py            #     Cookie AES-256 加密
│   │   ├── cookie_grabber.py    #     DrissionPage 自动获取 Cookie
│   │   ├── cookie_health.py     #     Cookie 健康度检测
│   │   ├── cookie_store.py      #     Cookie 持久化存储
│   │   ├── drissionpage_client.py #   浏览器客户端封装
│   │   ├── slider_solver.py     #     滑块验证码破解
│   │   ├── startup_checks.py    #     启动自检
│   │   ├── logger.py            #     loguru 日志封装
│   │   └── error_handler.py     #     统一错误类型
│   │
│   ├── dashboard/               #   Dashboard 服务层
│   │   ├── router.py            #     路由总入口
│   │   ├── repository.py       #     SQLite 数据仓储
│   │   ├── config_service.py    #     配置服务
│   │   └── routes/              #     分路由
│   │       ├── config.py
│   │       ├── cookie.py
│   │       ├── orders.py
│   │       ├── products.py
│   │       ├── messages.py
│   │       ├── quote.py
│   │       ├── slider.py
│   │       └── system.py
│   │
│   ├── modules/                 #   业务模块层
│   │   ├── messages/            #     消息模块（核心）
│   │   │   ├── service.py      #       消息服务（入口）
│   │   │   ├── reply_engine.py #       回复策略引擎（意图规则库）
│   │   │   ├── workflow.py     #       会话工作流
│   │   │   ├── quote_parser.py #       报价解析
│   │   │   ├── quote_composer.py #     报价回复组合
│   │   │   ├── ai_router.py    #       AI 意图路由
│   │   │   ├── dedup.py        #       消息去重
│   │   │   ├── safety_guard.py #       安全守卫
│   │   │   └── ws_live.py      #       WebSocket 长连接
│   │   │
│   │   ├── quote/              #     报价模块
│   │   │   ├── engine.py       #       报价计算引擎
│   │   │   ├── cost_table.py   #       成本表管理
│   │   │   ├── geo_resolver.py #       地址解析（省市区 → 快递线路）
│   │   │   ├── ledger.py       #       报价流水账
│   │   │   ├── route.py        #       路线选择
│   │   │   ├── providers.py    #       快递公司接入
│   │   │   └── models.py       #       数据模型
│   │   │
│   │   ├── orders/             #     订单模块
│   │   │   ├── service.py      #       订单服务
│   │   │   ├── sync.py         #       闲鱼订单同步
│   │   │   ├── store.py        #       订单本地存储
│   │   │   ├── price_execution.py #     自动改价执行
│   │   │   ├── xianguanjia.py  #       闲管家 API 封装
│   │   │   └── auto_price_poller.py #  价格轮询
│   │   │
│   │   ├── virtual_goods/      #     虚拟商品模块
│   │   │   ├── service.py      #       虚拟商品服务
│   │   │   ├── ingress.py      #       闲管家虚拟供货接入
│   │   │   ├── callbacks.py    #       回调处理
│   │   │   ├── scheduler.py    #       发货调度器
│   │   │   └── store.py       #       虚拟商品存储
│   │   │
│   │   ├── listing/            #     商品发布模块
│   │   │   ├── service.py      #       商品服务
│   │   │   ├── templates/     #       图片模板合成
│   │   │   │   ├── compositor.py #     模板合成器
│   │   │   │   ├── frames/     #       模板框架
│   │   │   │   └── layers/     #       文字/装饰图层
│   │   │   ├── image_generator.py #   图片生成
│   │   │   ├── oss_uploader.py #       阿里云 OSS 上传
│   │   │   └── scheduler.py    #       发布调度
│   │   │
│   │   ├── analytics/          #     数据分析模块
│   │   │   ├── service.py      #       分析服务
│   │   │   ├── report_generator.py #   报表生成
│   │   │   └── visualization.py #     可视化
│   │   │
│   │   ├── accounts/           #     多账号管理
│   │   │   ├── service.py      #       账号服务
│   │   │   ├── monitor.py     #       健康监控
│   │   │   └── scheduler.py   #       账号调度
│   │   │
│   │   ├── content/            #     AI 内容生成
│   │   ├── media/             #     媒体处理
│   │   ├── ticketing/         #     票务识别
│   │   ├── operations/        #     运营工具
│   │   ├── growth/            #     增长工具
│   │   ├── followup/          #     跟单
│   │   └── compliance/         #     合规检查
│   │
│   └── integrations/           #   第三方集成
│       └── xianguanjia/       #     闲管家开放平台
│           ├── open_platform_client.py
│           ├── virtual_supply_client.py
│           ├── signing.py      #       签名算法
│           └── errors.py       #       错误类型
│
├── client/                     # React 前端
│   ├── src/
│   │   ├── App.tsx             #     路由配置
│   │   ├── main.tsx            #     渲染入口
│   │   ├── api/               #     Axios API 客户端
│   │   │   ├── accounts.ts    #       账号 API
│   │   │   ├── config.ts      #       配置 API
│   │   │   ├── dashboard.ts   #       Dashboard API
│   │   │   ├── listing.ts     #       商品 API
│   │   │   └── xianguanjia.ts #       闲管家 API
│   │   ├── pages/             #     页面
│   │   │   ├── Dashboard.tsx  #       首页仪表盘
│   │   │   ├── Orders.tsx     #       订单管理
│   │   │   ├── accounts/      #       账号管理
│   │   │   ├── products/      #       商品管理
│   │   │   ├── messages/      #       消息沙盒
│   │   │   ├── analytics/      #       数据分析
│   │   │   └── config/        #       系统配置
│   │   └── components/         #     通用组件
│   │       ├── Navbar.tsx     #       导航栏
│   │       ├── SetupWizard.tsx #      首次配置向导
│   │       ├── IntentRulesManager.tsx # 意图规则管理
│   │       └── ...
│   └── dist/                  #     构建产物（部署用）
│
├── tests/                      # 单元测试（pytest）
├── config/                     # YAML 配置文件
│   ├── config.yaml             #   主配置（报价规则/快递参数/关键词）
│   ├── config.example.yaml     #   配置模板
│   ├── categories/             #   品类配置（快递/虚拟商品/票务）
│   └── templates/              #   消息回复模板
│
├── scripts/                    # 运维脚本
│   ├── start.sh / start.bat   #   一键启动（精简版）
│   ├── update.sh / update.bat #   在线更新
│   ├── release.sh             #   一键发版
│   ├── build_release.sh       #   构建离线安装包
│   ├── macos/                 #   macOS 专用（LaunchAgent / .command）
│   ├── windows/               #   Windows 专用（.bat 脚本）
│   ├── unix/                 #   Unix 辅助脚本
│   └── qa/                   #   质量检查脚本
│
├── data/                      # 运行时数据（自动生成，勿提交到 git）
│   ├── geo/city_province.json #   地理数据
│   └── *.db                   #   SQLite 数据库
│
├── database/migrations/       # 数据库迁移 SQL
├── docs/                      # 技术文档 / 设计文档 / Code Review 记录
├── examples/                  # Python 使用示例
├── .env.example              # 环境变量模板
├── pyproject.toml            # Python 项目配置
├── ruff.toml                 # Ruff 代码规范配置
├── pytest.ini                # pytest 配置
└── .github/workflows/        # CI/CD
    ├── ci.yml                #   Lint + Test + Security Scan
    └── release.yml           #   自动构建 + GitHub Release
```

---

## 快速开始

### 环境要求

| 依赖 | 版本 | 说明 |
|------|------|------|
| Python | 3.10+（推荐 3.12） | 后端运行时 |
| Node.js | 18+（推荐 20） | 前端构建工具 |
| Chrome / Edge | 任意版本 | Cookie 自动获取需要本地浏览器 |

### 步骤 1：克隆并安装依赖

```bash
git clone https://github.com/brianzhibo-design/XIANYUGUANJIA.git
cd XIANYUGUANJIA

# Python 依赖
python3 -m venv .venv
source .venv/bin/activate    # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# 前端依赖
cd client && npm install && cd ..
```

> **国内用户**：启动脚本会自动检测网络环境并切换阿里云/npm 镜像，无需手动配置。

### 步骤 2：配置

```bash
cp .env.example .env
```

编辑 `.env`，填入以下三项最小配置即可运行：

| 变量 | 说明 | 获取方式 |
|------|------|---------|
| `XIANYU_COOKIE_1` | 闲鱼登录 Cookie | 浏览器 F12 → Network → 复制请求头 Cookie |
| `AI_API_KEY` | AI 服务密钥 | [DeepSeek](https://platform.deepseek.com/) / [阿里百炼](https://bailian.console.aliyun.com/) 等平台申请 |
| `AI_BASE_URL` | AI API 地址 | 如 `https://api.deepseek.com/v1` |
| `AI_MODEL` | 模型名称 | 如 `deepseek-chat` |
| `XGJ_APP_KEY` | 闲管家 AppKey | [闲管家开放平台](https://open.goofish.pro) 注册应用获取 |
| `XGJ_APP_SECRET` | 闲管家 AppSecret | 同上 |

### 步骤 3：启动

```bash
# macOS / Linux（推荐）
bash start.sh

# Windows
start.bat

# macOS 用户可双击运行
bash scripts/macos/start.command
```

或分步启动：

```bash
# 后端（终端 1）
source .venv/bin/activate
python3 -m src.main

# 前端（终端 2）
cd client && npm run dev
```

访问 `http://localhost:5173` 进入管理面板。

### 步骤 4：获取闲鱼 Cookie

1. Chrome 打开 [goofish.com](https://www.goofish.com) 并登录
2. **F12** 打开开发者工具 → **Network** 标签
3. **F5** 刷新页面 → 点击任意请求 → 在 **Request Headers** 中找到 `Cookie:` 行
4. 全部复制粘贴到管理面板「账户管理」页面，或直接填入 `.env` 的 `XIANYU_COOKIE_1`

Cookie 有效期约 7-30 天，过期后通过管理面板手动更新，或启用 CookieCloud 自动同步。

---

## 配置说明

### 配置优先级

```
config.yaml 默认值  <  data/system_config.json（Dashboard 热配置）  <  .env / 环境变量
```

### config.yaml 主要配置项

```yaml
# 报价引擎
quote:
  preferred_couriers: [圆通, 中通, 申通, 韵达, 极兔]  # 优先快递公司
  markup_ratio: 0.15          # 基础加价比例 15%
  safety_margin: 2.0          # 安全边距 2 元

# AI 回复
ai:
  provider: deepseek
  model: deepseek-chat
  temperature: 0.7
  max_tokens: 1000

# 消息模块
messages:
  enabled: true
  auto_reply: true
  manual_mode_timeout: 600    # 人工介入后自动恢复时间（秒）
  first_reply_delay: 2        # 首条回复延迟（秒）
  inter_reply_delay: 3        # 两条消息间隔（秒）
```

---

## 部署方式

### macOS 桌面（推荐个人使用）

```bash
# 安装 LaunchAgent 开机自启动
bash scripts/macos/install_launchd.sh
```

### Linux 服务器

```bash
# 以后台服务方式运行
nohup python3 -m src.main > logs/app.log 2>&1 &
```

### Windows 服务器

直接运行 `start.bat`，或使用任务计划程序配置开机自启。

---

## 开发指南

### 代码规范

```bash
# 代码检查
ruff check src/

# 代码格式化
ruff format src/

# 类型检查
mypy src/
```

### 测试

```bash
# 运行全部测试
pytest tests/ -v --cov=src

# 跳过慢测试
pytest tests/ -m "not slow"

# 运行指定模块
pytest tests/test_quote_engine.py -v
```

### 发版流程

```bash
# 一键发版（自动 bump 版本 + 构建 + commit + push + 创建 Release）
bash scripts/release.sh 9.6.0
```

版本号存储在 `src/__init__.py` 的 `__version__`，发版脚本会自动同步到 `package.json`。

---

## 版本历史

详见 [CHANGELOG.md](./CHANGELOG.md)。

---

## 常见问题

**Q: 提示 "Cookie 格式异常"**
A: 确保复制的 Cookie 包含 `_tb_token_`、`cookie2`、`sgcookie` 等关键字段。可在 [goofish.com](https://www.goofish.com) 重新获取。

**Q: AI 回复不准确**
A: 在管理面板「系统配置 → AI 配置」中调整 `temperature` 和 `max_tokens`，或更新 `config/rules.yaml` 中的自定义回复规则。

**Q: 报价结果为空**
A: 检查买家收货地址是否完整，或在 `config/categories/express.yaml` 中确认对应线路的快递公司已配置。

**Q: 端口 5173 或 8091 被占用**
```bash
lsof -ti :5173 | xargs kill -9
lsof -ti :8091 | xargs kill -9
```

---

## 贡献

欢迎提交 Issue 和 Pull Request。提交前请确保：

1. `ruff check src/` 无报错
2. `pytest tests/ -x -q` 全部通过

详见 [CONTRIBUTING.md](./CONTRIBUTING.md)。

## License

[MIT](./LICENSE)
