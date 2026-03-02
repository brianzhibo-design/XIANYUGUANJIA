# XY-AUDIT-02 后端/API审查报告（报价引擎 / 消息模块 / 订单与workflow）

- 审查范围：`src/modules/quote`、`src/modules/messages`、`src/modules/orders`、`src/modules/operations`
- 审查方式：静态只读代码审查（未改动业务代码）
- 结论摘要：存在 **并发认领竞态、认证失败后的“永久降级/长停”、报价并行回退缺陷、领域边界耦合与断层** 等高风险问题。建议优先处理前 1~4 项。

---

## Top 10 高价值问题（按风险排序）

## 1) Workflow Job 认领非原子，存在双Worker重复消费风险（高）
- **证据**：`src/modules/messages/workflow.py:397-412`
  - 先 `SELECT pending` 再逐条 `UPDATE status='running' WHERE id=?`，无状态条件、无原子 claim。
- **触发条件**：两个进程/线程几乎同时调用 `claim_jobs()`。
- **影响范围**：同一会话可能被重复回复、重复状态推进、SLA/告警统计污染。
- **修复优先级**：**P0**

## 2) complete/fail 未校验 lease owner，可能覆盖他人执行结果（高）
- **证据**：`src/modules/messages/workflow.py:424-430, 432-456`
  - `complete_job` / `fail_job` 仅按 `id` 更新，不校验当前仍为 `running` 或 lease 未过期。
- **触发条件**：job lease 过期被 recover 后被新 worker 认领，旧 worker 晚到再 `complete/fail`。
- **影响范围**：任务状态错乱（done/pending/dead被串改），重试策略失真。
- **修复优先级**：**P0**

## 3) WS transport 初始化失败后被永久“熔断”到 DOM，不会自动自愈（高）
- **证据**：`src/modules/messages/service.py:385-388, 409-414`
  - `_ws_unavailable_reason` 一旦写入，后续直接返回 `None`；无重置/重试窗口。
- **触发条件**：启动时 cookie 短暂失效、网络抖动、依赖包瞬时异常。
- **影响范围**：长期退化到 DOM 轮询，实时性下降，负载上升，恢复需重启服务。
- **修复优先级**：**P1**

## 4) api+cost_table 并行模式下：API快速失败会直接抛错，无法回退到cost_table（高）
- **证据**：`src/modules/quote/engine.py:196-206`
  - `await asyncio.wait({api_task}, ...)` 后若 `api_task` 已完成但异常，`api_task.result()`直接抛出；未进入 table fallback 分支。
- **触发条件**：API快速返回 4xx/5xx/解析异常，而成本表本可成功。
- **影响范围**：报价失败率异常升高，破坏“并行优先API、失败回退表”的设计目标。
- **修复优先级**：**P1**

## 5) WS认证错误判定过宽，可能把短暂网络/协议异常当鉴权失败并长时间挂起（高）
- **证据**：`src/modules/messages/ws_live.py:392-406, 802-816`
  - `_is_auth_related_error` 包含泛化关键词（如 `http 400`）；命中后可进入 cookie 更新等待策略。
- **触发条件**：网关返回400（非鉴权语义）、中间层错误文案误匹配。
- **影响范围**：重连策略误判，吞吐下降，甚至长期等待cookie更新。
- **修复优先级**：**P1**

## 6) WS接收循环对单条坏包容错不足，可能导致连接被反复打断（中高）
- **证据**：`src/modules/messages/ws_live.py:785-791`
  - `json.loads(msg_text)` 未做单包 try/except，异常会跳到外层断连重连。
- **触发条件**：服务端推送非JSON/截断包/脏数据。
- **影响范围**：可用性下降、重连风暴、消息积压。
- **修复优先级**：**P1**

## 7) `transport=auto` 路径中即便 WS 已可用，未读会话仍倾向DOM扫描（中）
- **证据**：`src/modules/messages/service.py:512-514`
  - `auto` 模式下在 ws_ready 分支直接 `return await _get_unread_sessions_dom(...)`。
- **触发条件**：配置为 auto 且存在 browser controller。
- **影响范围**：WS价值被削弱，性能/实时性收益不足，代码路径复杂度上升。
- **修复优先级**：**P2**

## 8) cost_table 文件解析缺少隔离，单坏表可拖垮整个成本库加载（中）
- **证据**：`src/modules/quote/cost_table.py:279-286, 498-559`
  - `_reload_if_needed` 遍历文件直接 `_load_xlsx/_load_csv`，解析异常未按文件隔离。
- **触发条件**：某个 xlsx/csv 损坏、格式异常、zip/xml解析异常。
- **影响范围**：该次加载全失败，报价链路更频繁落到规则价或直接失败。
- **修复优先级**：**P2**

## 9) Workflow 与订单领域未形成闭环：只处理“回复/报价”，无订单状态联动（中）
- **证据**：
  - `src/modules/messages/workflow.py:663-710`（job stage 实质围绕 reply/quote）
  - `src/modules/orders/service.py:95-235`（订单履约/售后能力独立存在）
- **触发条件**：会话进入下单/售后阶段后仍由消息workflow单线处理。
- **影响范围**：售前（quote）与售后（order/after_sales）状态割裂，难以保证业务一致性和可追溯性。
- **修复优先级**：**P2**

## 10) orders/operations/presales 边界不清：职责交叉但缺少统一编排层（中）
- **证据**：
  - `src/modules/messages/service.py:946-1129`（售前报价、上下文跟单逻辑集中在消息服务）
  - `src/modules/operations/service.py:95-233`（店铺运营动作独立）
  - `src/modules/orders/service.py:169-234`（履约/售后独立）
- **触发条件**：业务从“咨询报价→成交→履约/售后”跨域流转。
- **影响范围**：跨模块状态和责任归属不清，异常恢复与审计链路断点多。
- **修复优先级**：**P2**

---

## “1天内可落地”修复清单（建议按顺序）

1. **Job认领原子化（P0）**
   - 将 `claim_jobs` 改为单SQL原子 claim（如 `UPDATE ... WHERE id IN (SELECT ... LIMIT N)` + `RETURNING`，或事务+状态条件）。
2. **完成/失败写入加状态保护（P0）**
   - `complete_job/fail_job` 增加 `WHERE id=? AND status='running'`（可附带 lease 校验）。
3. **修复并行报价回退缺陷（P1）**
   - `api_task.result()` 改为 try/except；API异常时优先等待/采用 `table_task` 结果。
4. **WS不可用原因引入TTL重试（P1）**
   - `_ws_unavailable_reason` 不应永久阻断；加入冷却重试窗口/主动清零机制。
5. **收窄鉴权错误识别（P1）**
   - 从关键词匹配升级为结构化判定（ret code/业务码），移除泛化 `http 400`。
6. **WS单包解析容错（P1）**
   - 为 `json.loads` 与 `_handle_sync` 增加 per-message try/except，坏包丢弃并计数，不触发断连。
7. **auto模式流量策略修正（P2）**
   - `ws_ready=True` 时优先走WS；DOM仅作兜底，不要常态覆盖。
8. **cost_table按文件隔离异常（P2）**
   - `_reload_if_needed` 中对每个文件独立 try/except，记录坏文件并继续加载其余文件。
9. **补一条跨域编排线（P2）**
   - 在 workflow 增加“订单事件桥接”接口（最小可行：reply成功后触发 order sync hook）。
10. **补充并发与恢复测试（P2）**
   - 增加 2-worker claim 冲突、lease 过期覆盖、WS鉴权失败恢复、API失败+table成功的回归用例。

---

## 备注
- 本次为只读审查，未改动业务代码。
- 以上问题按“稳定性与业务一致性”优先排序，优先处理 1~4 即可显著降低线上风险。
