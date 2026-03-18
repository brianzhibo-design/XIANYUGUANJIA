<div align="center">

# 闲鱼管家

> **曾用名**：xianyu-openclaw（已于 v8.0.0 更名为 xianyu-guanjia）

[![Version](https://img.shields.io/badge/version-8.0.0-blue.svg)](CHANGELOG.md)
[![Python](https://img.shields.io/badge/python-3.10+-3776AB.svg?logo=python&logoColor=white)](https://www.python.org/downloads/)
[![React](https://img.shields.io/badge/react-18-61DAFB.svg?logo=react&logoColor=white)](https://react.dev/)
[![Platform](https://img.shields.io/badge/platform-macOS%20%7C%20Windows%20%7C%20Linux-lightgrey.svg)]()

### 闲鱼虚拟商品卖家 7×24 无人值守自动化工作台

WebSocket 直连消息通道 · AI 智能回复与报价 · 商品管理与订单履约 · 风控自愈与进程守护

</div>

<br/>

## 为什么选择闲鱼管家？

闲鱼虚拟商品卖家面临的核心痛点：

| 痛点 | 传统方式 | 闲鱼管家方案 |
|------|---------|-------------|
| 消息回复不及时，错过买家 | 人工盯盘，24h 在线 | WebSocket 毫秒级接收 + AI 自动回复 |
| 报价计算复杂，容易出错 | 查表、手算、易遗漏 | 地址解析 + 快递计费 + 时效匹配，自动生成报价 |
| Cookie 频繁失效，服务中断 | 手动更新，中断数小时 | 静默刷新 + CookieCloud 即时同步，无感知续期 |
| 商品上架繁琐 | 逐个编辑标题、描述、图片 | AI 生成内容 + 7 套视觉模板 + 一键批量发布 |
| 风控触发后无法自动恢复 | 等通知 → 手动过验证 → 重启 | 滑块自动验证 + Cookie 自动恢复 + 进程自愈 |
| 多店铺切换管理混乱 | 频繁登录切换 | 统一配置中心，多账号独立管理 |

---

## 核心功能

### 消息自动化

```
买家消息 ─→ WebSocket 实时接收 ─→ AI 意图识别 ─→ 自动回复 / 报价
                                       │
                                       ├─ 咨询意图 → 智能应答（30+ 意图规则）
                                       ├─ 议价意图 → 议价计数器 + AI 策略
                                       ├─ 下单意向 → 订单同步 → 自动发货
                                       └─ 售后/异常 → 告警通知 → 人工接管
```

- **WebSocket 直连** — 毫秒级消息接收，无轮询延迟
- **AI 意图识别** — 30+ 条意图规则，覆盖咨询、议价、下单、售后、系统通知
- **双层消息去重** — 精确 hash + 内容 hash，杜绝重复回复
- **议价追踪** — 智能计数器辅助 AI 策略，自动识别讨价还价轮次
- **合规护栏** — 禁词拦截、频率限制、敏感词动态替换、审计日志

### 商品自动化

- **AI 内容生成** — 标题、描述、SEO 标签一键生成
- **7 套视觉模板** — 统一渲染引擎，支持自定义字体 / 配色 / 背景
- **自动上架流程** — HTML 模板 → 截图 → OSS 上传 → API 发布，全链路自动化
- **批量管理** — 自动调价、定时擦亮、批量上下架

### 订单自动化

- **虚拟商品自动发货** — 自动发送卡密，买家付款后秒级完成
- **闲管家 API 对接** — 实物订单物流发货、改价、SKU 库存管理
- **售后智能响应** — 退款 / 退货自动识别，复杂问题自动转人工

### 报价引擎

- **地址智能解析** — 省市归一化、城市候选扩展、自治区适配
- **多数据源** — 支持 Excel 导入快递报价表 + API 实时查询
- **安全加价** — Dashboard 可配置加价比例，默认 0%（无额外加价）

### 风控自动恢复

```
RGV587 风控触发
    │
    ├─ 1-2 次 → 退避重试 + 读浏览器 Cookie → 自动重连
    │
                  └─ 3+ 次 → 发送告警通知
                  │
                  ├─ 自动方案：DrissionPage 过滑块（NC / 拼图）
                  │              ↓
                  │          Cookie 完整? → 自动重连
                  │              ↓ 否
                  └─ CookieCloud 同步 → 自动重连
```

- **滑块自动验证** — DrissionPage + OpenCV，支持 NC 滑块和拼图验证
- **CookieCloud 集成** — 浏览器扩展即时同步 Cookie，风控恢复秒级生效
- **Cookie 静默刷新** — 后台守护线程每 30 分钟自动检查，失效时静默获取

### 监控与告警

- **实时健康面板** — Cookie / AI 服务 / 闲管家 API / 后端状态一目了然
- **多渠道告警** — 飞书 / 企业微信 Webhook，覆盖以下场景：

| 场景 | 级别 | 说明 |
|------|------|------|
| Cookie 过期 | P0 | 立即通知，触发自动恢复 |
| 风控滑块触发 | P0 | 通知 + 自动过滑块 |
| Cookie 自动刷新成功 | P1 | 确认服务已恢复 |
| 滑块验证结果 | P1 | 成功/失败均通知 |
| 售后介入 | P1 | 提醒人工关注 |
| 发货失败 | P1 | 触发重试或人工处理 |

### 在线更新 & 部署

- **Dashboard 一键更新** — 检查更新 → 自动备份 → 下载 → 安装 → 重启，全程可视
- **离线安装包** — macOS / Windows / 通用三版本，含全部依赖，无需联网
- **桌面快捷方式** — macOS `.command` + LaunchAgent / Windows `.bat` + 开机启动
- **进程守护** — `supervisor.sh` 健康检查 + 自动重启，HTTP 挂死自愈

---

## 快速开始

### 环境要求

| 项目 | 要求 | 说明 |
|------|------|------|
| **Python** | 3.10+ | 后端运行环境 |
| **Node.js** | 18+ | 仅前端构建/开发需要，生产可选 |
| **操作系统** | macOS / Windows / Linux | 全平台支持 |
| **磁盘空间** | 约 1GB | 含 Python 依赖和前端构建产物 |

### 三项准备

开始之前，请准备好以下凭证：

<table>
<tr><th>必备项</th><th>用途</th><th>获取方式</th></tr>
<tr>
<td><b>闲鱼 Cookie</b></td>
<td>登录凭证，用于消息监听和 API 调用</td>
<td>
  打开 <a href="https://www.goofish.com">goofish.com</a> → 登录 → F12 → Network → 复制 Cookie<br/>
  <em>也可启动后在管理面板「账户管理」点击「自动获取」</em>
</td>
</tr>
<tr>
<td><b>AI API Key</b></td>
<td>自动回复和内容生成</td>
<td>
  推荐 <a href="https://platform.deepseek.com">DeepSeek</a>（性价比高）<br/>
  也支持通义千问、智谱、火山方舟、OpenAI 等
</td>
</tr>
<tr>
<td><b>闲管家凭证</b></td>
<td>订单同步、发货、改价</td>
<td>
  <a href="https://open.goofish.pro">闲管家开放平台</a> 注册 → 创建应用 → 获取 AppKey / AppSecret
</td>
</tr>
</table>

### 方式一：离线安装包（推荐新用户）

从 [Releases](https://github.com/brianzhibo-design/XIANYUGUANJIA/releases) 下载对应平台的安装包，已包含全部依赖，无需联网安装：

**macOS:**

```bash
tar xzf xianyu-openclaw-v8.0.0-macos-arm64.tar.gz
cd xianyu-openclaw-v8.0.0
bash quick-start.sh
```

**Windows:**

```
1. 解压 xianyu-openclaw-v8.0.0-windows-x64.zip
2. 双击 quick-start.bat
```

首次启动自动弹出 **SetupWizard 设置向导**，按步骤完成配置即可。

### 方式三：一键启动脚本（精简版）

```bash
./start.sh     # macOS / Linux — 自动检测端口、安装依赖、启动服务
start.bat      # Windows
```

脚本自动完成：环境检查 → 端口清理 → 依赖安装 → 配置创建 → 服务启动。

### 方式四：手动安装（开发者）

```bash
# 1. 创建虚拟环境
python3 -m venv .venv && source .venv/bin/activate

# 2. 安装后端依赖
pip install -r requirements.txt

# 3. 安装前端依赖并构建
cd client && npm install && npm run build && cd ..

# 4. 配置
cp config/config.example.yaml config/config.yaml
# 编辑 config/config.yaml 或复制 .env.example 为 .env

# 5. 启动（两个终端）
python -m src.dashboard_server --port 8091   # 终端 1: Python 后端
cd client && npx vite --host                 # 终端 2: React 前端（开发模式）
```

### 访问地址

| 服务 | 地址 | 说明 |
|------|------|------|
| **管理面板** | http://localhost:5173 | React Dashboard，所有操作入口 |
| **后端 API** | http://localhost:8091 | Python 后端，提供 REST API |

---

## 首次配置

首次启动会自动弹出全屏 **SetupWizard 设置向导**，引导完成以下步骤：

| 步骤 | 操作 | 说明 |
|------|------|------|
| 1 | **账户管理** → 粘贴 Cookie 或点击「自动获取」 | 系统自动验证 Cookie 有效性 |
| 2 | **系统配置 → AI** → 选择服务商，填入 API Key | 支持 DeepSeek / 通义千问 / 智谱 / 火山方舟 / OpenAI |
| 3 | **系统配置 → CookieCloud** → 填入 UUID 和密码 | 推荐，防止 Cookie 失效中断服务 |
| 4 | **消息 → 对话沙盒** → 测试自动回复 | 确认 AI 回复质量和报价准确性 |
| 5 | 开启自动回复 | 进入 7×24 无人值守模式 |

> 配置完成后可随时在「系统配置」页面修改。所有配置支持管理面板可视化编辑，无需手动改配置文件。

---

## 在线更新

Dashboard 顶部显示当前版本号和「检查更新」按钮：

| 步骤 | 动作 | 说明 |
|------|------|------|
| 1 | 点击「检查更新」 | 自动比对 GitHub Release 最新版本 |
| 2 | 发现新版本 → 点击「立即更新」 | 后台开始下载，Dashboard 实时显示进度 |
| 3 | 下载完成 → 自动安装 | 备份当前版本 → 解压覆盖 → 安装依赖 → 重启服务 |
| 4 | 服务重启 → 自动重连 | Dashboard 自动检测服务恢复，无需手动刷新 |

- 更新过程中 Dashboard 实时显示当前阶段（检查 → 下载 → 安装 → 重启 → 重连）
- 自动保留最近 3 个版本备份，可随时回滚
- 更新失败时自动回退，不影响现有服务

---

## 配置说明

### 环境变量（`.env`）

只需 **3 项必填** 即可运行，其余均有默认值：

```bash
# ── 必填 ──────────────────────────────────
XIANYU_COOKIE_1=你的闲鱼Cookie           # 登录凭证
AI_API_KEY=你的AI密钥                     # 自动回复
XGJ_APP_KEY=闲管家AppKey                  # 订单/发货
XGJ_APP_SECRET=闲管家AppSecret

# ── 可选（有默认值）────────────────────────
AI_PROVIDER=deepseek                      # deepseek / openai / qwen / zhipu
AI_BASE_URL=https://api.deepseek.com/v1
AI_MODEL=deepseek-chat
MESSAGES_ENABLED=true                     # 消息自动回复开关
COOKIE_AUTO_REFRESH=true                  # Cookie 自动刷新（每 30 分钟）
```

> 完整配置项见 [`.env.example`](.env.example)。大部分配置也可在管理面板「系统配置」中可视化设置。

### CookieCloud 配置（强烈推荐）

CookieCloud 是浏览器扩展，可将 Cookie 实时同步到服务端。风控恢复时，在浏览器中通过滑块验证后 Cookie 秒级生效：

1. 安装 [CookieCloud 浏览器扩展](https://github.com/nichenqin/CookieCloud)（Chrome / Edge）
2. 扩展设置中记录 **UUID** 和**加密密码**
3. 在管理面板「系统配置 → CookieCloud」中填入 UUID 和密码，保存
4. Cookie 失效时，浏览器登录闲鱼 → 点击 CookieCloud「同步」→ 服务自动恢复

### 风控滑块自动验证（可选）

在管理面板「系统配置 → 风控滑块自动验证」中开启：

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `enabled` | 是否启用 | `false` |
| `max_attempts` | 单次风控最大尝试次数 | `3` |
| `cooldown_seconds` | 两次尝试间冷却时间 | `60` |
| `headless` | 是否无头模式运行浏览器 | `false` |

> **注意**：自动过滑块存在账号封控风险，建议配合 CookieCloud 使用，优先通过手动验证恢复。

---

## 常见问题

<details>
<summary><b>Cookie 频繁失效 / WebSocket 断连</b></summary>

**症状**：消息监听中断，日志出现 `FAIL_SYS_USER_VALIDATE`。

**解决**：
1. 保持本机浏览器已登录闲鱼，系统会自动从浏览器读取最新 Cookie
2. 推荐安装 [CookieCloud](https://github.com/nichenqin/CookieCloud) 浏览器扩展，实现 Cookie 即时同步
3. 确认 `COOKIE_AUTO_REFRESH=true` 已在 `.env` 中设置
4. 如无法保持浏览器登录，可在 Dashboard「账户管理」手动粘贴 Cookie
</details>

<details>
<summary><b>RGV587 风控滑块触发</b></summary>

**症状**：日志出现 `RGV587`，WebSocket 断连，收到告警通知"闲鱼触发风控验证"。

**解决（按推荐顺序）**：
1. **CookieCloud 方案**（推荐） — 在浏览器中手动通过闲鱼滑块验证后，CookieCloud 自动同步最新 Cookie
2. **自动验证方案** — 在系统设置中开启「风控滑块自动验证」（有封号风险，谨慎使用）
3. **手动方案** — 在 Dashboard「账户管理」粘贴新 Cookie
</details>

<details>
<summary><b>CookieCloud 配置步骤</b></summary>

1. 安装 [CookieCloud](https://github.com/nichenqin/CookieCloud) 浏览器扩展（Chrome / Edge）
2. 扩展设置中选择"自托管"或使用公共服务
3. 记录 UUID 和加密密码
4. 在管理面板「系统配置 → CookieCloud」中填入 UUID 和密码，保存
5. 当 Cookie 失效时，在浏览器登录闲鱼后点击 CookieCloud 扩展的"同步"，系统自动获取最新 Cookie
</details>

<details>
<summary><b>macOS 桌面快捷方式无法启动</b></summary>

**症状**：双击 `闲鱼管家.command` 后终端闪退或无日志输出。

**解决**：
1. **重新生成桌面快捷方式**（推荐）：在项目目录运行 `bash scripts/macos/install-desktop.sh`，会生成带 PATH 补全的 .command 文件，双击即可正常显示日志
2. 确认 `start.sh` 有执行权限：`chmod +x start.sh`
3. 检查 Python 和 Node.js 是否在 PATH 中（Homebrew 安装的通常在 `/opt/homebrew/bin`）
4. 在终端中直接运行 `bash start.sh` 查看详细错误
</details>

<details>
<summary><b>Docker 部署后无法访问面板</b></summary>

**解决**：
1. 确认容器正常运行：`docker compose ps`
2. 检查端口映射：`docker compose logs`
3. 国内网络构建失败时使用：`MIRROR=china docker compose up -d --build`
</details>

---

## 技术架构

### 系统架构图

```
┌──────────────────────────────────────────────────────────────────┐
│                    React 前端 (Vite + TypeScript)                 │
│                                                                  │
│   ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐        │
│   │Dashboard │  │ 商品管理  │  │ 订单中心 │  │ 系统配置  │        │
│   │ 数据看板  │  │ 批量上架  │  │ 订单履约 │  │ AI/Cookie │        │
│   └──────────┘  └──────────┘  └──────────┘  └──────────┘        │
│   ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐        │
│   │ 账户管理  │  │ 消息中心  │  │ 数据分析 │  │ 更新管理  │        │
│   │ 多店铺   │  │ 对话沙盒  │  │ 转化漏斗 │  │ 版本检查  │        │
│   └──────────┘  └──────────┘  └──────────┘  └──────────┘        │
└──────────────────────────┬───────────────────────────────────────┘
                           │ HTTP REST API / WebSocket
┌──────────────────────────┴───────────────────────────────────────┐
│                    Python 后端 (asyncio)                          │
│                                                                  │
│   ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│   │  消息模块        │  │  商品模块        │  │  订单模块        │ │
│   │  · WebSocket监听 │  │  · AI内容生成    │  │  · 闲管家API    │ │
│   │  · AI意图识别    │  │  · 图片模板渲染  │  │  · 自动发货     │ │
│   │  · 双层去重      │  │  · OSS上传      │  │  · 物流同步     │ │
│   │  · 议价追踪      │  │  · 自动发布     │  │  · 售后处理     │ │
│   └─────────────────┘  └─────────────────┘  └─────────────────┘ │
│   ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│   │  报价模块        │  │  安全模块        │  │  系统模块        │ │
│   │  · 地址解析      │  │  · Cookie管理   │  │  · 配置管理     │ │
│   │  · 快递计费      │  │  · 滑块验证     │  │  · 在线更新     │ │
│   │  · Excel导入     │  │  · CookieCloud  │  │  · 告警通知     │ │
│   │  · 安全加价      │  │  · 合规护栏     │  │  · 健康检查     │ │
│   └─────────────────┘  └─────────────────┘  └─────────────────┘ │
│                                                                  │
│   ┌──────────────────────────────────────────────────────────┐   │
│   │  数据层: SQLite (WAL) + 文件存储 (config.yaml / .env)    │   │
│   └──────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────┘
```

### 技术栈

| 层级 | 技术 | 说明 |
|------|------|------|
| **前端** | React 18 / Vite / TailwindCSS / TypeScript | 响应式管理面板，全组件 TypeScript |
| **后端** | Python 3.10+ / asyncio / httpx | WebSocket 消息、AI 回复、报价引擎、配置管理 |
| **数据库** | SQLite (WAL 模式) | 零配置，内嵌运行，优化并发读写 |
| **消息通道** | WebSocket 直连闲鱼 | 毫秒级接收，内存队列 + SQLite 持久化 |
| **AI 服务** | OpenAI 兼容 API | DeepSeek / 通义千问 / 智谱 / 火山方舟 / OpenAI |
| **浏览器自动化** | DrissionPage + OpenCV | Cookie 刷新、滑块自动验证 |
| **通知** | HTTP Webhook | 飞书 / 企业微信 |
| **部署** | 离线安装包 / 一键脚本 | 全平台一键部署 |

---

## 项目结构

```
XIANYUGUANJIA/
├── src/                              # Python 后端
│   ├── __init__.py                   # 版本号定义 (__version__ = "8.0.0")
│   ├── main.py                       # 主入口（WebSocket + 消息监听）
│   ├── dashboard_server.py           # Dashboard HTTP 服务入口
│   ├── setup_wizard.py               # CLI 设置向导
│   ├── windows_launcher.py           # Windows GUI 部署工具
│   │
│   ├── core/                         # 核心基础模块
│   │   ├── config.py                 # 配置加载与管理
│   │   ├── config_models.py          # 配置 Pydantic 模型
│   │   ├── cookie_health.py          # Cookie 健康检查 (定时探测)
│   │   ├── cookie_grabber.py         # Cookie 静默自动刷新
│   │   ├── slider_solver.py          # 风控滑块自动验证 (NC/拼图)
│   │   ├── slider_store.py           # 滑块验证状态存储
│   │   ├── notify.py                 # 告警通知 (飞书/企微)
│   │   ├── update_config.py          # 在线更新配置
│   │   ├── compliance.py             # 合规护栏 (禁词/频率)
│   │   ├── drissionpage_client.py    # 浏览器自动化封装
│   │   ├── doctor.py                 # 环境诊断工具
│   │   └── logger.py                 # 日志模块
│   │
│   ├── dashboard/                    # Dashboard 服务层
│   │   ├── router.py                 # 路由注册
│   │   ├── config_service.py         # 配置管理服务
│   │   ├── repository.py             # 数据仓库 (SQLite)
│   │   └── routes/                   # API 路由
│   │       ├── system.py             # 版本/更新/状态
│   │       ├── config.py             # 配置读写
│   │       ├── cookie.py             # Cookie 管理
│   │       ├── messages.py           # 消息相关
│   │       ├── products.py           # 商品管理
│   │       ├── orders.py             # 订单管理
│   │       ├── quote.py              # 报价查询
│   │       ├── slider.py             # 滑块验证
│   │       └── dashboard_data.py     # Dashboard 数据聚合
│   │
│   └── modules/                      # 业务模块
│       ├── messages/                 # 消息自动化
│       │   ├── service.py            # 消息服务
│       │   ├── reply_engine.py       # 意图规则引擎 (30+ 规则)
│       │   ├── workflow.py           # 会话状态机
│       │   └── ws_live.py            # WebSocket 实时监听
│       ├── listing/                  # 商品自动化
│       │   ├── image_generator.py    # 图片生成 (7 套模板)
│       │   ├── publish_queue.py      # 发布队列
│       │   └── templates/            # 视觉模板引擎
│       ├── orders/                   # 订单自动化
│       │   └── xianguanjia.py        # 闲管家 API 集成
│       ├── quote/                    # 报价引擎
│       │   ├── engine.py             # 报价核心逻辑
│       │   ├── providers.py          # 报价数据源
│       │   ├── geo_resolver.py       # 地址解析
│       │   └── models.py             # 报价数据模型
│       └── accounts/                 # 多账号管理
│
├── client/                           # React 前端 (TypeScript)
│   ├── src/
│   │   ├── pages/                    # 页面组件
│   │   │   ├── Dashboard.tsx         # 数据看板
│   │   │   ├── Orders.tsx            # 订单中心
│   │   │   ├── products/             # 商品管理
│   │   │   ├── accounts/             # 账户管理
│   │   │   ├── messages/             # 消息中心
│   │   │   ├── analytics/            # 数据分析
│   │   │   └── config/               # 系统配置
│   │   └── components/               # 通用组件
│   │       ├── SetupWizard.tsx       # 首次设置向导
│   │       ├── SetupGuide.tsx        # 设置检查清单
│   │       ├── UpdateBanner.tsx      # 更新管理组件
│   │       ├── ApiStatusPanel.tsx    # 服务状态面板
│   │       └── Navbar.tsx            # 导航栏
│   └── package.json
│
├── scripts/                          # 部署与运维脚本
│   ├── build_release.sh              # 构建安装包 (macOS/Windows/通用)
│   ├── prepare_offline.sh            # 离线依赖打包
│   ├── update.sh / update.bat        # 在线更新执行脚本
│   ├── macos/                        # macOS 专用脚本
│   │   ├── install-desktop.sh        # 桌面快捷方式安装
│   │   └── install_service.sh        # LaunchAgent 安装
│   └── windows/                      # Windows 专用脚本
│       ├── install-desktop.bat       # 桌面快捷方式
│       └── build_exe.bat             # EXE 构建
│
├── config/                           # 配置文件
│   ├── config.example.yaml           # 主配置示例
│   ├── categories/                   # 品类配置
│   ├── templates/                    # 回复模板
│   └── rules.yaml                    # 意图规则
│
├── tests/                            # 测试套件
├── data/                             # 运行时数据 (SQLite/日志/备份)
├── start.sh / start.bat              # 一键启动
├── quick-start.sh / quick-start.bat  # 首次安装引导
├── supervisor.sh                     # 进程守护
├── requirements.txt                  # Python 依赖
├── .env.example                      # 环境变量示例
└── CHANGELOG.md                      # 更新日志
```

---

## 开发指南

### 本地开发

```bash
# 启动后端（终端 1）
python -m src.dashboard_server --port 8091

# 启动前端（终端 2，热更新）
cd client && npx vite --host
```

### 测试

```bash
# 运行全部测试
pytest tests/ --cov=src --cov-report=html

# 代码质量检查
ruff check src/
ruff format src/
```

### 构建

```bash
# 构建前端生产版本
cd client && npm run build

# 构建安装包（macOS / Windows / 通用 + 更新包）
bash scripts/build_release.sh

# 仅构建更新包（跳过离线依赖）
bash scripts/build_release.sh --skip-vendor --skip-frontend
```

### 环境诊断

```bash
# 检查运行环境是否满足要求
python -m src.core.doctor --strict
```

### 版本规范

项目遵循 [Semantic Versioning 2.0.0](https://semver.org/lang/zh-CN/)。版本号定义在 `src/__init__.py`，修改时需同步更新 `package.json`。

详见 [CONTRIBUTING.md](CONTRIBUTING.md)。

### 更新日志

详见 [CHANGELOG.md](CHANGELOG.md)。

---

## 免责声明

本软件为私有软件，未经授权禁止分发、复制或二次售卖。使用者需遵守闲鱼平台规则和相关法律法规，自行承担使用风险。开发者不对因使用本软件导致的任何损失承担责任。

---

<div align="center">

**闲鱼管家** · v8.0.0

</div>
