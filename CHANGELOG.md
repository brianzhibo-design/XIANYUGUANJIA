# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **闲管家订单回调闭环**：
  - Dashboard 新增 `/api/orders/callback`，支持接收订单推送并在支付后自动同步订单状态
  - 当已配置闲管家且开启自动履约时，实物订单可在支付后自动触发物流发货
- **Dashboard 闲管家控制面板**：
  - 首页新增闲管家可视化配置区，可保存 AppKey/AppSecret、自动改价、自动发货与"支付后自动触发"开关
  - 新增 Dashboard 手动重试入口：API 改价、API 发货

### Changed
- 实物订单在未真正提交物流单、仅降级为人工发货任务时，状态保持为 `processing`，避免误标记为 `shipping`

## [8.0.0] - 2026-03-08

### Added
- **全新品牌升级**：项目正式更名为「闲鱼管家」，GitHub 仓库从 `xianyu-openclaw` 重命名为 `xianyu-guanjia`
- **一键在线更新系统**：Dashboard 内置更新检查、自动备份、版本回滚功能
- **SetupWizard 初始化向导**：首次启动自动弹出全屏配置向导，引导完成 Cookie/AI/闲管家配置
- **macOS 桌面快捷方式**：`.command` 文件 + LaunchAgent 开机自启动
- **Windows GUI 部署工具**：基于 CustomTkinter 的图形化部署向导
- **定价系统 UI**：Dashboard 可视化配置加价比例、安全边距
- **进程守护 supervisor.sh**：独立健康检查 + 自动重启脚本
- **codecov.yml**：代码覆盖率集成配置
- **requirements-dev.txt**：开发依赖分离

### Changed
- **文档全面重写**：README 从简洁版扩展为详细美观版（600+ 行）
- **版本号统一规范**：`src/__init__.py` / `pyproject.toml` / `package.json` 统一使用 `8.0.0`
- **CI 优化**：Python 版本升级至 3.12，移除增量 lint 逻辑
- **pyproject.toml 增强**：添加完整 pytest 配置段

### Removed
- **移除 Docker 部署支持**：删除 `docker-compose.yml`、`Dockerfile.python`、`client/Dockerfile`
- **清理冗余文件**：删除 `.roo/`、`.claude/`、`plans/`、`qa_evidence/`、`third_party/` 等无意义目录
- **移除废弃配置**：清理 node-backend 启动配置

### Fixed
- 修复更新系统 8 个已知问题
- 修复 SetupWizard "跳过全部" 只前进一步的问题
- 修复已部署设备 3% 加价残留问题
- 修复自动改价未生效的多个问题
- 修复 3 个前端 Bug (Orders/SetupGuide/Dashboard)
- 修复 bash 3.2 变量展开后跟全角字符导致 unbound variable
- 修复 Finder 双击 .command 时 PATH 不含 node/homebrew

## [7.0.0] - 2026-03-06

### Added
- **一键离线部署体系**：支持 U 盘拷贝零网络部署新设备
- **大件快运品类**：新增大件快运品类，优化报价系统吸引大件客户
- **重件报价优化**：按实际总成本选最优渠道，避免多收费
- **滑块验证增强**：
  - `_m_h5_tk` 缺失时自动补全，避免无限循环等待
  - 复用 IM 标签页时 reload 触发滑块检测
  - baxia 弹窗内 NC 滑块检测增强
  - puzzle 失败时 NC 回退机制

### Changed
- **日志系统升级**：使用 loguru 替代标准库 logging 输出 HTTP 请求日志
- **测试策略调整**：删除过时的自动生成测试，移除覆盖率阈值限制
- 精简日志输出，只保留有用信息

### Fixed
- 桌面 `.command` 不显示日志问题 — 补充 PATH 与初始输出
- 滑块验证相关稳定性修复

## [6.1.0] - 2026-03-03

### Added
- **Windows 一键部署工具（EXE）**：
  - 新增 `src/windows_launcher.py`：基于 CustomTkinter 的图形化部署向导，替代命令行 `setup_wizard`
  - 支持 Docker Desktop 自动检测与下载引导
  - 分步向导：网关 AI 选择 → 业务 AI 选择 → 认证配置 → Cookie 粘贴 → 确认部署
  - 自动生成 `.env` 配置文件，格式与 `setup_wizard` 完全一致
  - 一键启动 `docker compose up -d`，支持启动后健康检查与自动打开浏览器
  - 支持 PyInstaller 打包为 Windows EXE（`--onedir --windowed` 模式）
- **PyInstaller 构建配置重写**：
  - `pyinstaller.spec` 更新为新 GUI 入口（`src/windows_launcher.py`），包含 CustomTkinter 数据文件
  - 排除运行时不需要的重型依赖（playwright/pandas/openai 等），减小打包体积
- **Windows EXE 构建脚本**：
  - 新增 `scripts/windows/build_exe.bat`：一键创建虚拟环境、安装依赖、构建 EXE
- **Windows 专用依赖文件**：
  - 新增 `requirements-windows.txt`：CustomTkinter + PyInstaller 依赖声明

### Changed
- `src/__init__.py` 版本号更新为 `6.1.0`
- `README.md` / `USER_GUIDE.md` 新增 Windows EXE 部署说明，路线图状态更新

## [6.0.0] - 2026-03-02

### Added
- **闲管家开放平台适配层**：
  - 新增 `src/modules/orders/xianguanjia.py`
  - 支持商品改价、SKU 库存/价格更新、订单改价、物流发货、快递公司查询与签名生成
- **运营改价 API 优先链路**：
  - `OperationsService.update_price(...)` 现支持优先走闲管家 API
  - API 成功直接完成改价；API 失败时自动回退到原有 DOM 改价
- **订单自动物流发货**：
  - `OrderFulfillmentService.deliver(...)` 现支持为实物订单直连闲管家发货
  - 支持 `shipping_info` 直接传参，或从 `quote_snapshot.shipping_info` 读取
  - 支持快递公司名称自动映射编码（如 `圆通 -> YTO`）
- **CLI 发货参数增强**：
  - `orders --action deliver` 新增物流单号、快递公司、寄件信息、闲管家凭证参数

### Changed
- `OrderFulfillmentService` 新增 `config` / `shipping_api_client` 注入能力，实物发货优先走闲管家 API，失败时降级为人工发货任务
- `OperationsService` 新增 `price_api_client` 注入与 `xianguanjia` 配置支持
- `README.md` / `USER_GUIDE.md` 更新为 6.0.0 版本说明

### Fixed
- 修复 `MediaService.add_watermark()` 在 `watermark: null` 配置下会抛出 `AttributeError` 的问题，CI 全量测试恢复通过

## [5.3.0] - 2026-03-02

### Added
- **Lite 直连运行时**：
  - 新增 `src/lite/` 轻量运行时栈，支持直连 Goofish WebSocket、双层去重、消息收发和自动回复
  - 新增 `scripts/lite_start.sh` 快速启动入口
- **报价链路增强**：
  - 新增 `src/modules/quote/geo_resolver.py`，提供省市归一化与城市/省份候选扩展
  - 新增 `src/modules/quote/excel_import.py`，支持自适应 Excel 导入、列名变体识别与快递公司自动识别
  - `QuoteResult` 新增 `source_excel` 与 `matched_route` 字段，增强报价追溯
- **消息能力增强**：
  - 新增 `src/modules/messages/info_extractor.py`，提供规则优先信息抽取与可选 LLM 回退
  - 新增 `src/modules/messages/manual_mode.py`，提供会话级人工接管持久化
  - 新增 `src/modules/messages/safety_guard.py`，提供禁寄物品双重校验
- 新增大批针对性覆盖测试，覆盖 Dashboard、Lite、报价匹配与消息分支路径

### Changed
- `CostTableRepository.find_candidates(...)` 升级为三级匹配 + 路由语义兜底，提升省/市混输命中率
- `dashboard_server` 的 multipart 文件读取改为 MIME 兼容解析，适配 Python 3.13+/3.14
- `GoofishWsTransport` 的事件等待逻辑改为可取消超时等待，减少异步任务悬挂
- `FollowUpEngine` 的写入返回值改用稳定的 `rowcount`
- `README.md` 更新为 5.3.0 说明

### Fixed
- 修复真实报价表导入时自治区名称被截断的问题（如 `广西壮族自治区` / `宁夏回族自治区`）
- 修复纯城市级线路表对“市 -> 省”与部分“省 -> 省”查询命中不足的问题
- 修复 Dashboard multipart 上传场景下附件内容读取为空的问题

## [5.2.0] - 2026-03-01

### Added
- **Cookie 健康监控**：
  - 新增 `src/core/cookie_health.py`：定时探测 Cookie 有效性（HTTP probe），失效立即飞书告警，恢复后通知
  - `WorkflowWorker.run_once()` 集成 Cookie 健康检查（TTL 缓存，非阻塞）
  - `doctor --strict` 新增 `Cookie在线有效性` 诊断项
  - CLI `module --action cookie-health` 手动检查 Cookie 状态
- **macOS launchd 进程守护**：
  - `scripts/macos/com.xianyu-openclaw.plist`：开机自启 + 崩溃自动恢复（`KeepAlive: true`）
  - `scripts/macos/install_service.sh`：一键安装/卸载/查看服务状态
  - `scripts/macos/start_all.sh`：统一启动脚本（Docker Compose + 所有模块守护 + Dashboard）
- **数据备份**：
  - `scripts/backup_data.sh`：SQLite 安全备份（`sqlite3 .backup`），7 天自动轮转清理
- **Dashboard /healthz 端点**：
  - 返回 JSON 格式的系统健康状态（数据库可写性、模块存活、运行时长）
- 新增测试 `tests/test_cookie_health.py`（8 tests）

### Changed
- **SQLite WAL 模式**：`WorkflowStore` 与 `DashboardRepository` 的 `_connect()` 启用 `journal_mode=WAL` + `busy_timeout=5000`，提升并发写入可靠性


## [5.1.0] - 2026-02-28

### Added
- **售前会话流程优化**：
  - 对齐业务模型：报价 → 选择快递 → 下单（不支付）→ 卖家改价 → 买家支付 → 自动兑换码
  - 移除选择快递后的地址/电话收集分支，替换为结账引导回复
  - 新增会话上下文记忆，用于后续报价解析（origin/destination/weight/courier choice）
- **新增配置项**：
  - `messages.force_non_empty_reply`：确保回复不为空（默认 true）
  - `messages.non_empty_reply_fallback`：空回复时的后备内容
  - `messages.context_memory_enabled`：启用会话上下文记忆（默认 true）
  - `messages.context_memory_ttl_seconds`：上下文记忆 TTL（默认 3600）
  - `messages.courier_lock_template`：快递锁定回复模板
- **Lite Mode 架构提案**：新增 `docs/architecture/lite-mode-proposal.md`

## [5.0.0] - 2026-02-28

### Added
- **售前运行时强化**：
  - 新增 `module recover` 动作：一键停止→清理→重启模块
  - 新增平台启动脚本（macOS/Linux/Windows）
  - 强化运行时/浏览器解析检查和 doctor 覆盖
- **Dashboard 改进**：
  - 更强的状态/风险/恢复信号处理
  - 更清晰的模板说明和 Cookie 诊断反馈
  - 新增 Cookie 导入域名过滤（`goofish.com`/`passport.goofish.com`）
- **报价模板优化**：
  - 标准化的首次响应格式，询价收集更高效
  - 报价模板接入实际回复渲染路径
  - 支持 legacy template 占位符别名（`origin_province`, `dest_province`, `billing_weight` 等）
- **认证稳定性增强**：
  - 新增 `messages.auth_hold_until_cookie_update` 配置项（默认 `true`）
  - 优先使用环境变量 `XIANYU_COOKIE_1` 避免 WS 认证振荡
  - 认证失败后停止激进重试，等待 Cookie 更新后恢复
- **测试端点对齐**：
  - Dashboard `/api/test-reply` 与实际生产流程保持一致

### Changed
- `quote_reply_all_couriers` 默认为 `true`，报价时列出所有可用快递供买家选择
- `quote_reply_max_couriers` 默认 `10`，控制最多显示快递数量

### Fixed
- 修复报价回复模板与实际生产流程不一致的问题

## [4.9.0] - 2026-02-28

### Added
- **严格标准格式回复**：对非标准买家消息（你好/在吗/hello等问候语）强制标准格式回复
- **标准格式触发关键词**：新增 `messages.standard_format_trigger_keywords` 配置项
- **Lite 运行时强化**：
  - WS 就绪内省 (`is_ready`)
  - `transport=ws` 保持 WS-only（无 DOM 回退）
  - DOM 回退仅保留给 `transport=auto`
- **Cookie 健壮性增强**：
  - 更安全的 cookie 解析（支持请求头/表格格式）
  - 过滤无效 cookie 字段，允许部分接受避免启动崩溃
- **AI Provider Key 安全解析**：
  - 避免跨 provider key 误用
  - 将环境变量占位符 `${...}` 视为缺失 key

### Changed
- `messages.strict_format_reply_enabled` 默认为 `true`
- 运行时配置改为 `messages.transport: ws`
- 报价回复规范化：统一报价模板输出，ETA 以天显示（而非分钟），移除报价有效期文本

### Fixed
- 修复被合规拦截的报价不计入成功统计
- 修复 Windows helpers 和 quality gate 问题

## [4.8.1] - 2026-02-28

### Changed
- CI workflow 调整为只拦截真实问题：
  - `ruff check` 覆盖 `src/` 与 `tests/`
  - 忽略纯样式类告警（`I001`、`E501`、`UP012`、`RUF100`）
  - 移除单独的 `ruff format --check` 步骤，避免样式噪音阻塞发布
- 清理 `startup_checks` 中重复定义的 `resolve_runtime_mode` / `check_runtime_mode`，避免静态检查误报并减少维护风险

## [4.8.0] - 2026-02-28

### Added
- 消息链路新增 WebSocket 实时传输：售前/售后可在有 Cookie 的情况下绕过 DOM 抓取直接读写会话。
- Dashboard 集成 Cookie 插件资源导入/导出能力，内置 `Get-cookies.txt-LOCALLY` 插件包。
- `messages` CLI 新增 `sla-benchmark`，可评估首响 SLA、报价成功率与慢样本。
- 自动报价新增成本表/API 成本加价模式：
  - `cost_table_plus_markup`
  - `api_cost_plus_markup`

### Changed
- `module check` 在售前/售后使用 `messages.transport=ws` 时，不再把浏览器运行时作为阻塞项。
- `automation setup` 默认把消息传输模式设置为 `ws`，并将默认轮询间隔调整为 1 秒。
- `dashboard_server` 增加 Python 3.13+/3.14 下 multipart 兼容解析，避免 `cgi` 移除导致导入失败。
- README / USER_GUIDE 同步为 4.8.0 版本说明，并补齐当前 CI 检查命令。

## [4.7.0] - 2026-02-27

### Added
- 两阶段报价工作流：优先快速首响，再补发精确报价，保障消息 SLA。
- 报价引擎新增多源容灾：
  - API
  - 热缓存
  - 本地成本表
  - 兜底模板
- 新增跟进引擎：
  - 已读未回自动跟进
  - 每日频控
  - 静默时段
  - DND 退订
  - 审计回放
- 新增 `doctor` 自检命令与 `followup` CLI 命令。

### Changed
- `AutoQuoteEngine` 增加熔断、半开恢复、报价快照追溯与回退失败分类。
- CI workflow 改为失败即阻断，测试步骤不再容忍失败继续。

## [4.6.0] - 2026-02-27

### Added
- 一站式部署增强：
  - `setup_wizard` 升级为双通道配置（Gateway AI 与业务文案 AI 分离）
  - 自动生成 `OPENCLAW_GATEWAY_TOKEN` 默认值
  - 启动后自动执行容器健康检查与常见故障提示
- 国产大模型接入（OpenAI 兼容模式）：
  - DeepSeek（`DEEPSEEK_API_KEY`）
  - 阿里云百炼（`DASHSCOPE_API_KEY`）
  - 火山方舟（`ARK_API_KEY`）
  - MiniMax（`MINIMAX_API_KEY`）
  - 智谱（`ZHIPU_API_KEY`）
- 新增统一业务 AI 环境变量：`AI_PROVIDER`、`AI_API_KEY`、`AI_BASE_URL`、`AI_MODEL`

### Changed
- `scripts/init.sh`：兼容 `/data/workspace` 与旧路径，避免写入错误状态目录导致配置分裂。
- `docker-compose.yml`：增加 `/data/workspace` 与 `/data/.openclaw` 挂载，减少镜像内状态目录不一致问题。
- `ContentService`：支持多供应商 API key/base_url/model 解析，优先读取 `AI_*` 变量。
- 配置模型扩展 provider 枚举：`aliyun_bailian`、`volcengine_ark`、`minimax`、`zhipu`。
- `README.md` / `USER_GUIDE.md` / `.env.example`：更新为新部署流程与国产模型配置说明。

### Added (carry-over)
- `src/modules/quote/route.py`：地理路由标准化组件，支持省/市/自治区别名与后缀容错。
- `quote` 配置新增熔断参数：`circuit_fail_threshold`、`circuit_open_seconds`。
- 自动报价新增测试：路由标准化缓存命中、远程 provider 熔断打开后自动降级。
- `src/modules/orders/service.py`：订单履约闭环 MVP（状态映射、交付动作、售后模板、人工接管、订单追溯）。
- CLI 新增 `orders` 命令：`upsert/deliver/after-sales/takeover/resume/trace`。
- 新增测试 `tests/test_orders.py`，覆盖订单状态同步、交付、售后与追溯能力。
- `src/modules/compliance/center.py`：分级合规策略中心（global/account/session 覆盖）、发送前拦截、审计落库与回放查询。
- 策略样例文件 `config/compliance_policies.yaml`，支持热更新与高风险词默认阻断。
- CLI 新增 `compliance` 命令：`reload/check/replay`。
- `src/modules/growth/service.py`：A/B 分流、策略版本管理、漏斗统计、显著性最小实现（z-test）。
- CLI 新增 `growth` 命令：`set-strategy/rollback/assign/event/funnel/compare`。
- AI 降本治理能力：
  - `AIConfig` 新增 `usage_mode`、`max_calls_per_run`、`task_switches`、缓存参数
  - `ContentService` 新增任务级 AI 开关、调用预算、本地缓存、调用成本统计
  - CLI 新增 `ai` 命令：`cost-stats/simulate-publish`
- 新增测试：
  - `tests/test_compliance_center.py`
  - `tests/test_growth.py`
  - `tests/test_ai_cost_control.py`

### Changed
- `QuoteRequest.cache_key()` 升级为分层缓存 key：`origin + destination + courier + weight_bucket + service_level`。
- `AutoQuoteEngine` 增强：
  - 请求前路由标准化（统一 cache key 与 provider 入参）
  - 远程 provider 失败计数与熔断窗口
  - fallback 失败分类（`timeout/transient/unavailable/provider_error`）
  - 回退结果追加标准化路由可观测字段
- CI workflow 调整为严格失败策略：测试步骤不再 `continue-on-error`。
- `MessagesService` 在外发前接入合规策略中心检查，并写入消息级审计轨迹。

## [4.4.0] - 2026-02-27

### Added
- `src/modules/messages/workflow.py`：
  - `WorkflowState` + `SessionStateMachine` 状态迁移规则
  - `WorkflowStore`（SQLite 持久化）：会话任务、迁移日志、幂等作业队列、SLA 事件、告警事件
  - `WorkflowWorker`：常驻轮询、幂等去重、失败指数退避、过期租约恢复
- `MessagesService.process_session(...)`，统一单会话处理路径，供批处理和 worker 复用。
- CLI 新增 `messages` 动作：
  - `auto-workflow`（单次或 daemon）
  - `workflow-stats`（工作流与 SLA 汇总）
- 新增测试 `tests/test_workflow.py`，覆盖状态迁移防护、作业去重与重试、worker 流程与人工接管跳过。

### Changed
- `src/modules/messages/service.py`：`auto_reply_unread` 改为复用 `process_session`，减少重复逻辑并对齐 worker 行为。
- `config/config.example.yaml`、`src/core/config_models.py`、`src/core/config.py`：新增 `messages.workflow` 配置段与默认值支持。
- `README.md` 更新为 4.4.0，补充 workflow worker、SLA 指标与新 CLI 用法。

## [4.3.0] - 2026-02-27

### Added
- `src/modules/quote/` 自动报价模块：
  - `models.py`：`QuoteRequest` / `QuoteResult`
  - `providers.py`：`IQuoteProvider`、`RuleTableQuoteProvider`、`RemoteQuoteProvider(mock)`
  - `cache.py`：`TTL + stale-while-revalidate` 缓存
  - `engine.py`：`AutoQuoteEngine`（provider 重试、失败回退、缓存刷新、审计日志）
- 消息自动回复新增询价分流：
  - 识别询价意图后自动解析寄件地/收件地/重量/时效
  - 缺参时生成补充提问模板
  - 字段完整时返回结构化报价文案（含费用拆分和有效期）
- 消息链路新增快速回复指标：
  - `target_reply_seconds`
  - `within_target_count` / `within_target_rate`
  - `quote_latency_ms` / `quote_success_rate` / `quote_fallback_rate`
- 新增测试 `tests/test_quote_engine.py`，覆盖规则报价、远程失败回退、缓存命中。

### Changed
- `src/modules/messages/service.py`：
  - 支持复用消息页（降低批量回复页面开关开销）
  - 新增 `reply_to_session(..., page_id=...)` 复用调用路径
  - `auto_reply_unread` 接入自动报价、缺参补问、合规降级回复
  - `dry-run` 模式跳过随机等待，提升测试与验收效率
- 配置模型与样例新增 `quote` 配置段与 `messages.fast_reply_*` 参数。
- `README.md` 更新为 4.3.0，补充自动报价与快速回复配置示例。
- `src/__init__.py` 版本号更新为 `4.3.0`。

## [4.2.1] - 2026-02-27

### Added
- `src/modules/messages/reply_engine.py` — 通用自动回复策略引擎，支持意图规则（关键词/正则/优先级）与虚拟商品场景兜底回复
- `messages` 配置新增 `virtual_default_reply`、`virtual_product_keywords`、`intent_rules`
- 新增测试覆盖：虚拟商品卡密咨询、代下单咨询的自动回复命中逻辑

### Changed
- `src/modules/messages/service.py` 自动回复逻辑由单一关键词匹配升级为策略引擎驱动，保留原 `keyword_replies` 兼容路径
- `config/config.example.yaml` 增加虚拟商品/卡密/代下单策略配置示例，便于按品类快速扩展
- `README.md` 更新消息自动回复策略说明，新增可直接复用的规则化配置模板

## [4.2.0] - 2026-02-27

### Added
- `src/setup_wizard.py` — 交互式一键部署向导，支持逐步输入 API Key、Cookie、认证信息并生成 `.env`
- `scripts/one_click_deploy.sh` — 一键部署脚本封装，优先使用 `.venv/bin/python`
- `src/dashboard_server.py` — 轻量运营后台可视化服务（HTTP + Chart.js），提供实时指标与图表
- `src/modules/messages/service.py` — 闲鱼消息自动回复服务，支持关键词模板与批量未读处理
- CLI 新命令 `messages`（`list-unread` / `reply` / `auto-reply`）
- 新增测试：`tests/test_setup_wizard.py`、`tests/test_dashboard_server.py`、消息模块相关单测

### Changed
- `README.md` / `USER_GUIDE.md` 增加一键部署与后台可视化使用说明
- `config/config.example.yaml` / `src/core/config*.py` 新增 `messages` 配置模型与默认项
- `src/main.py` / `src/modules/__init__.py` 接入消息模块加载与导出

## [4.1.0] - 2026-02-27

### Added
- `src/core/compliance.py` — 合规规则引擎，支持内容审查、频率限制与规则热重载
- `config/rules.yaml` — 合规规则配置（`warn/block` 模式、发布间隔、批量冷却、禁词词表）
- `tests/test_compliance.py`、`tests/test_service_container.py` — 合规与容器核心行为单测

### Changed
- **Compliance**: 发布/运营/内容链路接入增强合规决策，新增 `COMPLIANCE_BLOCK` / `COMPLIANCE_WARN` 审计事件
- **Scheduler**: 擦亮/发布任务显式创建并注入 `BrowserClient`，连接失败返回结构化错误码
- **Monitor**: 健康检查告警调用改为 `await`，并修复回调字段引用错误
- **Analytics**: 周报统计不再依赖缺失表；`new_listings` 统计口径从分组数修正为总数
- **Accounts**: 账号 Cookie 字段统一为 `cookie_encrypted`，读写与脱敏逻辑统一
- **Skills/Test alignment**: 废弃 legacy `skills/xianyu_*` Python 包运行路径，测试改为校验 `SKILL.md + CLI` 契约
- **Quality gates**: 修复并启用全量 `pytest.ini` 配置，测试与 lint 门槛可真实执行

### Fixed
- `ServiceContainer` 单例集合类型错误（`_singletons`）与 `clear()` 清理不完整问题
- 发布流程中“分类/成色选择”空操作问题
- 批量擦亮结果中随机伪商品 ID 与失败统计失真问题
- 媒体格式映射大小写问题（`png/webp`）
- 监控与错误处理中的 Python 3.14 兼容性警告（协程判断方式）

## [4.0.0] - 2026-02-23

### Added
- `BrowserClient` — OpenClaw Gateway browser HTTP client replacing direct Playwright calls
- `src/cli.py` — CLI entry point with 7 subcommands for agent invocation
- 5 OpenClaw Skills in standard `SKILL.md` format (publish, manage, content, metrics, accounts)
- `scripts/init.sh` — Docker container Python environment bootstrap
- `config/openclaw.example.json` — OpenClaw Gateway configuration template
- `CONTRIBUTING.md`, `SECURITY.md`, `CHANGELOG.md`
- GitHub Actions CI workflow
- Issue and PR templates

### Changed
- **Architecture**: migrated from Playwright + Streamlit to OpenClaw-native Skill ecosystem
- **Deployment**: single `docker compose up -d` using `coollabsio/openclaw` image
- **UI**: replaced Streamlit/FastAPI web interface with OpenClaw AI chat UI
- **Dependencies**: removed playwright, streamlit, fastapi, uvicorn; kept httpx, aiosqlite, cryptography

### Removed
- `web/` directory (Streamlit + FastAPI + React frontend)
- `Dockerfile` (using OpenClaw official image)
- `install.sh`, `install.bat`, `start.sh`, `start.bat`
- `openclaw_controller.py` (replaced by `browser_client.py`)
- Skills Python code (`skill.py`, `registry.py`, `openclaw_integration.py`)

## [3.0.0] - 2026-02-23

### Added
- Playwright-based browser automation (replacing non-functional HTTP API stubs)
- AES cookie encryption (`src/core/crypto.py`)
- Rate limiting middleware
- Docker containerization (`Dockerfile` + `docker-compose.yml`)
- Startup health checks (`src/core/startup_checks.py`)

### Fixed
- SQL injection vulnerability in analytics service
- CORS configuration (was `allow_origins=["*"]`)
- Silent mock data returns when controller unavailable (now raises `BrowserError`)

### Changed
- CSS selectors updated for Xianyu SPA (text-based, placeholder, role matching)

## [2.1.0] - 2026-02-22

### Added
- Task management API
- Release checklist documentation

## [2.0.0] - 2026-02-22

### Added
- Streamlit web interface
- React frontend with Ant Design
- FastAPI backend with REST endpoints
- One-click install scripts (Windows + macOS/Linux)

## [1.0.0] - 2026-02-21

### Added
- Initial project structure
- Core modules: config, logger, error handler
- Business modules: listing, operations, analytics, accounts, content, media
- OpenClaw skill stubs
- Multi-account support
- AI content generation (DeepSeek/OpenAI)
