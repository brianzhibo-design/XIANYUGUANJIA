# MEMORY.md — 闲鱼管家项目记忆

> **读我优先级：本文件 > QUICKSTART.md > README.md**
> 本文件是项目的结构化记忆，记录关键决策、经验教训、架构约束、业务规则和所有记忆位置。
> 供后续 AI 会话快速理解上下文，避免重复踩坑。

---

## 零、项目导航与记忆位置

### 0.1 项目路径

```
主仓库: ~/openclaw/xianyu-openclaw/
工作树: ~/openclaw/xianyu-openclaw/.claude/worktrees/heuristic-swartz/   ← 当前活跃开发分支
```

### 0.2 记忆位置一览

| 类型 | 位置 | 说明 |
|------|------|------|
| **项目记忆** | `MEMORY.md`（本文件） | 业务规则、架构决策、经验教训 — **AI 必读** |
| **快速入门** | `QUICKSTART.md` | 启动指南、目录结构、部署说明 |
| **项目说明** | `README.md` | 项目概述、功能列表、架构图 |
| **Cursor 对话记录** | `~/.cursor/projects/.../agent-transcripts/` | 12 轮历史对话（JSONL 格式），含完整开发上下文 |
| **Cursor 方案记录** | `~/.cursor/plans/` | **135 个** `.plan.md` 方案文件，记录每次功能开发/修复的设计 |
| **Workspace 规则** | Cursor 自动注入 `AGENTS.md`（来自根 workspace） | 会话引导规则 |
| **运行时上下文** | `service.py:_quote_context_memory`（内存） | 每个会话的报价上下文，TTL 1h |
| **运行时对话** | `service.py:_append_chat_history`（内存） | 最近 5 条对话历史 |
| **人工模式状态** | `data/manual_mode.db`（SQLite） | 人工接管持久化 |
| **知识库** | `data/express_faq.json` | FAQ 问答对 |
| **学习日志** | `data/unmatched_messages.jsonl` | 未匹配消息，供后续优化 |

### 0.3 关键方案文件（按主题）

需要了解某个功能的设计背景时，查阅 `~/.cursor/plans/` 下的对应方案：

| 主题 | 方案文件名 |
|------|-----------|
| 自动回复规则 | `自动回复规则全面优化`、`全面优化回复话术`、`会话阶段机制+话术优化` |
| AI 集成 | `ai配置链路贯通`、`ai_智能信息提取+回复` |
| 人工介入 | `人工介入自动停止回复`、`修复人工介入检测` |
| 报价系统 | `修复报价加价规则`、`报价公式展示优化` |
| Cookie/风控 | `风控滑块恢复方案`、`cookie_完整性修复`、`静默自动刷新cookie` |
| 部署 | `国内无外网部署适配`、`本地一键部署`、`部署集成与pr提交` |
| 测试 | `100+复杂场景测试`、`话术修复+测试恢复` |

### 0.4 项目目录结构

```
.
├── src/                           # Python 后端核心
│   ├── core/                      #   配置、日志、Cookie、加密、合规
│   ├── dashboard/                 #   仪表盘（配置服务、数据仓库、模块控制）
│   │   └── vendor/                #   本地 CDN 资源（Chart.js）
│   ├── dashboard_server.py        #   Python HTTP 主服务（端口 8091）
│   └── modules/
│       ├── messages/              #   ★ 消息服务（自动回复核心）
│       │   ├── service.py         #     主服务：报价、阶段跟踪、AI
│       │   ├── ws_live.py         #     WebSocket 通道
│       │   ├── reply_engine.py    #     意图规则引擎
│       │   ├── manual_mode.py     #     人工模式管理
│       │   └── workflow.py        #     会话工作流
│       ├── quote/                 #   ★ 报价引擎
│       │   ├── engine.py          #     报价计算
│       │   ├── cost_table.py      #     成本表
│       │   └── geo_resolver.py    #     城市→省份解析
│       ├── content/               #   AI 内容生成
│       ├── orders/                #   订单管理
│       ├── listing/               #   商品发布
│       ├── accounts/              #   账号管理
│       ├── virtual_goods/         #   虚拟商品（兑换码）
│       └── ...                    #   analytics, media, ticketing 等
├── client/                        # React 前端（Vite + TypeScript）
│   └── src/
│       ├── pages/                 #   Dashboard, Messages, Products, Orders, Config
│       ├── api/                   #   API 调用（axios）
│       └── components/            #   通用组件
├── config/
│   ├── config.yaml                # 主业务配置
│   └── config.example.yaml        # 配置模板
├── data/                          # 运行时数据
│   ├── express_faq.json           # FAQ 知识库
│   ├── unmatched_messages.jsonl   # 未匹配消息
│   ├── manual_mode.db             # 人工模式 SQLite
│   └── cost_table_*.xlsx          # 成本表
├── tests/                         # 161 条自动回复测试 + 服务层测试
├── MEMORY.md                      # ← 你正在读的文件
├── QUICKSTART.md                  # 快速启动指南
├── README.md                      # 项目说明
├── supervisor.sh                  # ★ 进程守护（健康检查 + 自动重启）— 推荐使用
├── quick-start.sh / .bat          # 交互式启动脚本
├── start.sh / .bat                # 一键启动脚本（无守护）
├── docker-compose.yml             # Docker 编排
├── Dockerfile.python              # Python 容器
└── .env                           # 环境变量
```

### 0.5 服务端口

| 服务 | 开发端口 | Docker 端口 | 入口文件 |
|------|---------|-------------|---------|
| React 前端 | 5173 | 80 (nginx) | `client/src/main.tsx` |
| Python 后端 | 8091 | 8091 | `src/dashboard_server.py` |

### 0.6 数据流

```
买家发消息 → 闲鱼服务器 → WebSocket sync push → ws_live.py._push_event
  → 入队 → MessagesService.process_session
    → 人工模式检查（ManualModeStore + HTTP 消息拉取比对）
    → 阶段检测（presale/checkout/aftersale）
    → 意图匹配（reply_engine 规则 → AI 回退）
    → 报价计算（quote/engine）
    → 合规检查
    → send_text 发送回复（WS 或 DOM）
```

---

## 一、项目定位

闲鱼管家（Xianyu OpenClaw）是为闲鱼卖家设计的 **全自动化运营工作台**。核心场景是**快递代发**（express 品类）：买家在闲鱼询问快递价格 → 机器人自动报价 → 买家下单 → 卖家改价 → 付款后自动发兑换码 → 买家到小橙序下单寄件。

技术栈：Python 3.10+ asyncio（后端）+ React 18 + Vite + Tailwind（前端）。

---

## 二、核心业务规则（必须遵守）

### 2.1 价格体系

- **闲鱼价格** = 小橙序成本价 + 加价（由 `quote/cost_table.py` + markup 规则决定）
- **首单优惠**：首次使用小橙序的手机号，首重仅需 3 元起（续重不变）。这不是"3 元优惠"，是"首重 3 元起"
- **非首单用户**：按正常价计费，正常价也比自寄便宜 5 折起
- **计费规则**：`billing_weight = max(actual_weight, volumetric_weight)`，体积重 = 长×宽×高/8000
- **单位**：重量必须转换为 kg（支持识别 g、斤、公斤等），尺寸必须转换为 cm（支持识别 mm）

### 2.2 下单流程话术

```
先拍下链接不付款 → 我改价 → 付款后自动发兑换码 → 到小橙序下单即可
地址和手机号在小橙序填写，闲鱼这边不需要提供
```

### 2.3 快递限制

- 闲鱼特价渠道仅支持韵达、圆通、中通、申通
- 顺丰/京东不在特价路线中，回复："闲鱼特价渠道暂不支持顺丰/京东，但在小橙序直接下单也比其他平台优惠"
- 不要说"没有顺丰"，而是引导到小橙序

### 2.4 会话阶段

系统跟踪每个会话的阶段 (`session_phase`)：
- `presale` — 询价阶段（默认）
- `checkout` — 下单/付款阶段（触发词：我已拍下、待付款等）
- `aftersale` — 售后阶段（触发词：我已付款、已发货等）

阶段影响回复策略：售后阶段不再推送报价模板，而是回复售后相关内容。

---

## 三、架构关键决策

### 3.1 消息通道：WebSocket 优先

- 通过 DingTalk WS 协议连接闲鱼 IM（`ws_live.py`）
- WS 使用 `_m_h5_tk` Cookie 签名获取 accessToken
- **关键发现：WS sync push 不会推送卖家自己发送的消息**（包括机器人发送和手动发送），因此不能通过 WS 监听 `sender_id == my_user_id` 来检测人工介入

### 3.2 人工介入检测机制

由于 WS 不推送卖家消息，采用「**机器人发送追踪 + HTTP API 拉取比对**」方案：

1. `send_text` 成功后记录消息签名到 `_bot_sent_sigs`（内存 TTL 缓存，2 小时）
2. `process_session` 前通过 mtop HTTP API 拉取会话最近消息（缓存 30 秒）
3. 找到 `sender_id == my_user_id` 的消息后，比对 `is_bot_sent()` — 不在追踪中的即为人工发送
4. 人工发送 → 标记 `ManualModeStore`（SQLite 持久化）→ 跳过自动回复
5. 超时自动恢复（默认 1 小时）或前端手动恢复

### 3.3 配置三层架构

```
.env (环境变量) → config/config.yaml (YAML) → data/system_config.json (前端可视化配置)
```

- `system_config.json` 由前端 UI 管理，保存后同步到 `config.yaml`
- AI 配置（api_key、model、provider）在 `system_config.json` 的 `ai` 节点
- `MessagesService` 初始化时从两处读取配置并合并

### 3.4 AI 集成策略

- AI 作为**回退机制**，规则引擎优先匹配
- 支持千问（Qwen）、DeepSeek、OpenAI 三种 provider
- AI 任务：`quote_extract`（信息提取）、`express_reply`（回复生成）
- FAQ 知识库：`data/express_faq.json`
- 未匹配消息记录：`data/unmatched_messages.jsonl`

### 3.5 回复引擎优先级

```
priority 越小 = 越优先匹配
  10-49: 核心意图规则（express_sf_jd, express_code_usage, express_luggage 等）
  50:    一般意图规则
  200:   legacy 关键词规则（从 keyword_replies 转换）
```

---

## 四、经验教训（踩过的坑）

### 4.1 单位换算

- **重大 Bug**：早期报价金额异常（上万元），根因是尺寸单位 mm 未转换为 cm，导致体积重计算错误
- **修复**：在报价前统一将 mm 转 cm，将 g 转 kg

### 4.2 正则匹配中文

- `\b` 词边界在中英混合文本中不可靠
- 中文全角标点（，、。）需要在正则中显式处理
- "省内" 模式需要特殊处理（如"广东省内"→ 寄件和收件都在广东）

### 4.3 Legacy 规则覆盖

- 旧版 `keyword_replies`（如"便宜"→ 通用回复）的优先级曾设为 30，高于新 intent_rules
- **修复**：将 legacy 规则优先级改为 200，确保新规则优先

### 4.4 售后阶段回退

- 买家付款后发"怎么补"、"码呢"等消息，被错误识别为新的询价请求（阶段从 aftersale 回退到 presale）
- **修复**：严格化阶段回退条件，要求同时满足有效的 origin/destination/weight 且地址发生变化

### 4.5 Cookie 与风控

- 闲鱼 Cookie 有效期 7-30 天
- `_m_h5_tk` 是关键 Cookie，过期会导致 WS 连接失败
- 风控滑块（RGV587）需要 Playwright Chromium 自动解决
- CookieCloud 可用于多设备同步 Cookie

### 4.6 AI 配置链路

- 用户在前端配置了 AI（system_config.json），但后端未读取 → AI 功能不生效
- **修复**：`MessagesService` 和 `ContentService` 初始化时从 `system_config.json` 读取 AI 配置作为 fallback

### 4.7 WS 不推送卖家消息

- 闲鱼 WS sync push 只推送对方（买家）消息，不推送自己（卖家/机器人）的消息
- 最初在 `_push_event` 中添加 `sender_id == my_user_id` 检测是死代码
- **修复**：改用 HTTP API 主动拉取 + bot 发送追踪比对

---

## 五、文件速查

### 5.1 核心代码

| 文件 | 职责 |
|------|------|
| `src/modules/messages/service.py` | 消息处理主服务，报价生成，阶段跟踪，AI 集成 |
| `src/modules/messages/ws_live.py` | WebSocket 通道，消息收发，人工模式追踪 |
| `src/modules/messages/reply_engine.py` | 意图规则引擎（IntentRule 定义、匹配、优先级） |
| `src/modules/messages/manual_mode.py` | 人工模式管理（SQLite 持久化） |
| `src/modules/messages/workflow.py` | 会话工作流状态 |
| `src/modules/quote/engine.py` | 报价计算引擎 |
| `src/modules/quote/geo_resolver.py` | 地理位置解析（城市→省份） |
| `src/modules/quote/cost_table.py` | 快递成本表 |
| `src/modules/content/service.py` | AI 内容服务（千问/DeepSeek/OpenAI） |
| `src/dashboard_server.py` | Python HTTP 服务（端口 8091），API 路由 |
| `src/core/config.py` | 配置加载（单例） |

### 5.2 配置文件

| 文件 | 用途 |
|------|------|
| `config/config.yaml` | 主业务配置 |
| `config/config.example.yaml` | 配置模板 |
| `data/system_config.json` | 前端管理的配置 |
| `.env` | 环境变量（Cookie、API Key 等） |

### 5.3 数据文件

| 文件 | 用途 |
|------|------|
| `data/express_faq.json` | FAQ 知识库 |
| `data/unmatched_messages.jsonl` | 未匹配消息日志 |
| `data/manual_mode.db` | 人工模式 SQLite |
| `data/cost_table_*.xlsx` | 快递成本表 |

### 5.4 前端页面

| 页面 | 路径 | 功能 |
|------|------|------|
| Dashboard | `/dashboard` | 仪表盘 |
| Messages | `/messages` | 消息中心（回复日志 + 对话沙盒 + 人工模式管理） |
| Products | `/products` | 商品管理 |
| Orders | `/orders` | 订单管理 |
| Accounts | `/accounts` | 店铺/Cookie 管理 |
| Config | `/config` | 系统配置（自动回复、AI、告警等） |

---

## 六、部署要点

- **端口**：前端 5173（开发）/ 80（Docker），Python 8091
- **国内部署**：`quick-start.sh` 自动检测网络环境，无外网时切换阿里云 pip/npm/Playwright 镜像
- **Docker**：`docker-compose build --build-arg MIRROR=china` 使用国内源构建
- **Chart.js**：本地托管在 `src/dashboard/vendor/chart.umd.min.js`，CDN 作为 fallback
- **AI 推荐**：国内环境使用百炼千问（Qwen），兼容 OpenAI 接口

---

## 七、API 端点速查

### 7.1 关键 API

| 方法 | 路径 | 用途 |
|------|------|------|
| GET | `/api/status` | 系统状态 |
| GET | `/api/replies` | 回复日志 |
| POST | `/api/test-reply` | 对话沙盒测试 |
| GET | `/api/manual-mode` | 当前人工模式会话列表 |
| POST | `/api/manual-mode` | 开启/关闭人工模式 |
| GET | `/api/intent-rules` | 意图规则列表 |
| GET/PUT | `/api/config` | 系统配置读写 |

---

## 八、待办与已知限制

1. **mtop 消息拉取 API** (`mtop.taobao.idle.pc.im.conversation.message.list`) 尚未在生产验证，如不可用需退化为前端手动标记
2. **多账号支持**：架构已预留，但当前主要测试单账号场景
3. **复购识别**：已有基础逻辑，但无法查询小橙序后台判断用户是否真的是首单
4. **滑块自动解决**：依赖 Playwright Chromium，成功率不稳定，需要人工兜底

---

## 九、重大变更记录

### 9.1 Node.js 后端彻底移除（2026-03-14）

**变更摘要**：项目从三层架构（Python + Node.js + React）简化为双服务架构（Python + React/Vite）。

**已删除**：
- `server/` 目录（Express 后端：webhook 验签、XGJ API 代理、config CRUD）— 功能已全部由 Python 实现
- `src/dashboard/embedded_html.py`（2833 行内嵌 HTML 回退仪表盘）— 死代码

**路径迁移**：
- `system_config.json` 从 `server/data/` → `data/`（含自动迁移逻辑，10 处代码更新）
- `.gitignore` 对应更新 `server/data/cookie_cloud/` → `data/cookie_cloud/`

**前端清理**：
- `useHealthCheck.ts`：移除 `node: ServiceHealth`
- `SetupGuide.tsx`：移除 `nodeBackend` 检查步骤
- `ApiStatusPanel.tsx`：确认无需修改

**启动脚本**：
- `start.sh` / `start.bat` / `quick-start.sh` / `quick-start.bat`：移除 Node.js 进程管理

**文档更新**：README.md、QUICKSTART.md、USER_GUIDE.md、docker-compose.yml、.env.example、package.json

**⚠ 注意**：任何引用 `server/` 目录、端口 3001、或 `Node 薄代理` 的文档/分析已过时。

### 9.2 进程守护机制（2026-03-14）

**问题**：Python `ThreadingHTTPServer` 偶发挂死（进程存活但不响应 HTTP），服务无法自愈。

**方案**：新增 `supervisor.sh`
- 每 15 秒对 Python（`/api/config`）和 Vite（`/`）发 HTTP 健康检查
- 连续 2 次无响应 → 强制 kill + 自动重启
- 进程退出 → 立即重启
- 日志写入 `logs/supervisor.log`
- 启动时自动清理残留端口占用

**推荐启动方式**：`./supervisor.sh` 代替 `./start.sh`

### 9.3 自动回复日志修复（2026-03-14）

**问题**：消息页面"自动回复日志"显示空白卡片。

**根因**：`get_replies()` 从 `workflow.db:session_state_transitions.metadata` 读取消息内容，但旧版代码写入 metadata 时只存了 `{"quote": false, "quote_success": false}`，缺少 `buyer_message`、`reply_text`。

**修复**：`get_replies()` 增加两级数据回退：
1. 优先读 `metadata`（新代码写入的记录有完整数据）
2. `buyer_message` 缺失 → 从 `workflow_jobs.payload_json` 获取
3. `reply_text` 缺失 → 从 `compliance.db:compliance_audit` 获取（SQLite ATTACH 跨库查询）

### 9.4 数据库文件说明

| 数据库 | 路径 | 用途 |
|--------|------|------|
| `data/workflow.db` | 会话状态机 + 任务调度 + SLA 事件 |
| `data/compliance.db` | 合规审计日志（每条发出的消息） |
| `data/manual_mode.db` | 人工模式持久化 |
| `data/agent.db` | 商品运营日志 |
| `data/quote_ledger.db` | 报价台账 |
| `data/followup.db` | 追单记录 |
| `data/orders.db` | 订单数据 |
| `data/message_dedup.db` | 消息去重（当前未初始化） |
| `data/system_config.json` | 前端可视化配置（非数据库） |
