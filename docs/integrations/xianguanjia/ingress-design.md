# XianGuanJia Ingress 设计（PR-1）

## 回调入口路由
- 开放平台回调：`POST /api/open/callback/xianguanjia/open-platform`
- 虚拟货源回调：`POST /api/open/callback/xianguanjia/virtual-supply`

## Raw Body 读取规则
1. 必须优先读取 HTTP 原始 body 字节串（不做字段重排）。
2. 验签输入使用原始 body；业务解析使用验签通过后的 JSON 反序列化对象。
3. 空 body 统一按文档规则参与签名（`md5("")` 或 `md5("{}")`）。

## 验签顺序
1. 先按路由确定签名体系（开放平台 or 虚拟货源）。
2. 提取 query/header 中签名参数与 timestamp。
3. 使用对应 `verify_*_callback_signature(...)` 做验签。
4. 验签通过后才进入业务处理。

## 验签失败策略
- 直接拒绝业务处理，记录审计日志（来源 IP、request_id、sign、timestamp）。
- 返回统一失败 ACK（HTTP 401/403，按网关策略）。
- 不写入业务状态，不触发后续补偿。

## external_event_id / dedupe_key
- `external_event_id`：优先采用上游明确事件ID（若有）。
- `dedupe_key`：用于幂等去重；优先 `external_event_id`，否则回退组合键规则（见 key-model.md）。

## Replay 防护
- timestamp 过期拒绝（默认 5 分钟窗口）。
- 对同一 `dedupe_key` 做幂等表落库 + TTL（建议 >= 24h）。
- 记录首次处理时间与结果，重复事件直接返回已处理 ACK。

## ACK 策略
- 验签失败：返回失败 ACK。
- 验签成功但业务处理中：返回接收 ACK（避免上游重放风暴），内部异步继续。
- 幂等命中：返回成功 ACK（表示已处理）。
