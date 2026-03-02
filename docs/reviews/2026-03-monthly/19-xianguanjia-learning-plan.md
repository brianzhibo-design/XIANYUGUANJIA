# 闲管家能力专项学习与最小接入方案（面向现有系统）

- 任务ID：XY-XIANGUANJIA-20260302-K
- 时间：2026-03-02
- 工作目录：`/Users/brianzhibo/Documents/New project/xianyu-openclaw`
- 目标：基于最近提交，梳理“闲管家”可接入能力边界，并给出最小接入架构 + 分阶段落地计划

---

## 1) 基于最新提交的能力边界梳理

> 本次按提交主题归并：`xianguanjia api client / price updates / shipping / dashboard fulfillment`

### A. API Client 能力（对应 `src/lite/xianyu_api.py`，近期并入于 `52878a7`）

**已具备**
1. Cookie 解析与更新：`parse_cookie_string`、`update_cookie`。
2. 鉴权链路最小闭环：
   - `has_login()`：登录预检（`passport.goofish.com/newlogin/hasLogin.do`）
   - `get_token()`：获取 access token（`mtop.taobao.idlemessage.pc.login.token`）
3. 商品详情读取：`get_item_info(item_id)`（`mtop.taobao.idle.pc.detail`）。
4. 具备重试和 token 缓存（短期复用）机制。

**边界/缺口**
1. 当前是“读取/鉴权型 client”，**未覆盖订单发货写操作 API**（如发货、物流回传、签收回写）。
2. 依赖 Cookie + mtop sign，风控/验证码场景下可用性波动大。
3. 没有统一的“错误码语义层”（例如统一区分 token 失效、风控、网络抖动）。

---

### B. 价格更新能力（对应 `src/modules/operations/service.py` + quote 体系）

**已具备**
1. 单商品改价：`update_price(product_id, new_price, original_price)`（浏览器自动化点击“调价”）。
2. 批量改价：`batch_update_price(updates)`。
3. 运营日志打点：`analytics.log_operation("PRICE_UPDATE"/"BATCH_PRICE_UPDATE")`。
4. 报价侧已有成本表/加价规则基础（dashboard 配置页可导入路线与加价规则）。

**边界/缺口**
1. 目前改价主要走前端自动化（UI selector），**不是后端稳定 API 事务写入**。
2. “闲管家价格变更”若要接入，尚缺**外部价格事件 -> 本地改价任务**的标准队列与幂等键。
3. 缺少“价格变更回执”结构（成功/失败原因/重试状态）供外部系统对账。

---

### C. Shipping / 履约能力（对应 `src/modules/orders/service.py`，提交 `616099a` + 后续流程补强）

**已具备**
1. 订单状态映射：中文状态 -> 内部状态（`pending/processing/shipping/completed/after_sales/closed`）。
2. 订单落库与追溯：
   - `orders` + `order_events` 两张表
   - `upsert_order()`、`trace_order()`
3. 发货动作抽象：`deliver()` 区分 `virtual` 与 `physical`。
4. 售后流程：`create_after_sales_case()`、`record_after_sales_followup()`。
5. 人工接管：`set_manual_takeover()`。
6. CLI 已具备基础操作：`orders upsert/deliver/after-sales/takeover/resume/trace`。

**边界/缺口**
1. `deliver()` 当前是**动作抽象**（写事件+状态推进），并未真正调用快递下单/面单平台。
2. 缺少“发货回传 API”入口（例如第三方物流状态 webhook -> 本地订单状态同步）。
3. 缺少运单号、物流公司编码、签收节点等结构化字段（当前主要在 detail_json 事件中临时承载）。

---

### D. Dashboard Fulfillment 能力（对应 `src/dashboard_server.py`，提交 `7b59b51` 持续增强）

**已具备**
1. 服务健康看板：`/api/status`（服务状态、风险、恢复、模块在线数）。
2. 消息/报价看板：回复量、趋势、路线数据、风控状态。
3. 配置管理：Cookie、路线、加价、模板导入。

**边界/缺口**
1. 当前看板偏“售前/系统态”，**没有专门履约看板（订单池、发货SLA、异常单）**。
2. 没有“发货回传”专属页面与指标（回传延迟、回传失败率、重试队列积压）。
3. 缺少对外履约集成可观测（闲管家调用耗时、成功率、错误码分布）。

---

## 2) 最小接入架构（面向现有系统）

### 目标
在不重构现有大盘和消息系统前提下，把“闲管家”接成一个可灰度、可回滚的履约能力增量层。

### 2.1 架构分层（最小可行）

1. **Client 层（新增）**：`src/integrations/xianguanjia/client.py`
   - 职责：封装闲管家 API（鉴权、下单/发货、物流查询、回传确认）
   - 统一返回：`ok/data/error_code/error_message/retryable`

2. **价格更新层（新增适配器）**：`src/integrations/xianguanjia/price_sync.py`
   - 输入：闲管家价格变更事件（主动拉取或回调）
   - 输出：写入本地 `price_update_jobs`（建议新增表）并驱动 `OperationsService.update_price`
   - 关键：`external_event_id` 幂等

3. **发货回传层（新增）**：`src/integrations/xianguanjia/shipping_sync.py`
   - 输入：本地订单发货事件 / 外部物流状态回传
   - 输出：更新 `orders` 主状态 + `order_events` 轨迹
   - 关键字段：`order_id / tracking_no / courier_code / shipment_status / event_time`

4. **履约看板层（扩展 dashboard）**
   - 在 `dashboard_server.py` 增加 `/api/fulfillment/summary`（或同类接口）
   - 指标最小集：
     - `待处理订单数`
     - `发货中订单数`
     - `售后中订单数`
     - `发货回传成功率(24h)`
     - `超时未回传订单数`

### 2.2 数据流（最小闭环）

1. 订单进入：`orders upsert`（已有）
2. 触发履约：`orders deliver`（已有）
3. 新增发货回传：闲管家回传 -> `shipping_sync` -> `orders/order_events`
4. dashboard 拉取履约汇总 -> 页面展示与告警

---

## 3) 分阶段落地计划 + 风险

### 阶段1：MVP（3天）

**目标**：先打通“可运行闭环”，不追求功能全。

#### D1
- 建立 `xianguanjia client` 骨架（鉴权、统一错误码、超时/重试策略）。
- 加入 `.env`/config 的闲管家配置项（endpoint、token、timeout）。

#### D2
- 建立 `shipping_sync`：
  - 支持最小发货回传字段入库
  - `orders` 状态从 `processing/shipping` 可推进
  - 写 `order_events` 审计轨迹

#### D3
- dashboard 增加履约摘要 API + 卡片展示（summary 级）
- 冒烟验收：
  1) upsert 订单
  2) deliver
  3) 模拟闲管家回传
  4) dashboard 显示状态变化

**MVP 验收口径**
- 单链路成功率 ≥ 95%（测试数据）
- 回传幂等生效（重复事件不重复推进状态）
- 能定位失败原因（错误码 + 日志）

---

### 阶段2：v1（7天）

**目标**：补齐生产可运维能力。

#### Day 4-5
- 价格更新同步（price_sync）接入：外部价格事件 -> 本地改价任务
- 增加失败重试与死信队列（最小可先用 SQLite 任务表）

#### Day 6
- 履约看板增强：
  - 异常单列表
  - 回传延迟分布
  - 成功率趋势（24h/7d）

#### Day 7
- 灰度开关 + 回滚策略：
  - `XIANGUANJIA_ENABLED`
  - 失败时自动降级到“本地履约流程 + 人工接管提示”
- 完成联调文档与SOP

**v1 验收口径**
- 发货回传成功率 ≥ 98%
- 关键路径可观测（请求耗时、错误码分布、重试次数）
- 出现外部故障时，系统可自动降级且不阻断核心流程

---

## 4) 主要风险与应对

1. **鉴权/风控风险（高）**
   - 风险：Cookie/token 机制波动导致 client 不稳定
   - 应对：统一错误码 + 熔断 + 手动恢复入口 + dashboard 告警

2. **状态一致性风险（高）**
   - 风险：外部回传乱序/重复导致订单状态错乱
   - 应对：事件幂等键、状态机守卫（只允许合法跃迁）

3. **可观测不足风险（中）**
   - 风险：联调失败难定位
   - 应对：每次外调记录 request_id、order_id、error_code、latency

4. **UI 自动化与 API 双轨风险（中）**
   - 风险：价格更新依赖 UI，稳定性受页面改版影响
   - 应对：将 UI 改价封装为任务执行器，后续可平滑切换到 API

5. **交付范围膨胀风险（中）**
   - 风险：7天内同时做全量履约/售后/对账过重
   - 应对：先做“回传闭环 + summary看板”，高级分析放 v1.1

---

## 5) 结论（给决策层）

当前代码基础已经具备“售前自动化 + 订单履约MVP + 运营看板”的底座，**最短路径是补齐闲管家集成层（client + shipping_sync）并在 dashboard 增加履约摘要**。  
建议按“3天打通闭环、7天补齐生产可运维”的节奏推进，优先控制鉴权稳定性与状态一致性两大风险。
