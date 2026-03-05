# XianGuanJia Key Model（PR-1）

## 键定义与职责

- `xianyu_order_id`
  - 闲鱼侧订单主键。
  - 作为订单维度对账、状态推进的主关联键。

- `xianyu_product_id`
  - 闲鱼侧商品主键。
  - 用于商品同步、库存与上下架操作定位。

- `supply_order_no`
  - 虚拟货源侧订单号。
  - 用于虚拟货源查单/回调关联，与 `xianyu_order_id` 做跨系统映射。

- `external_event_id`
  - 上游事件唯一ID（若上游提供）。
  - 优先作为事件幂等键，避免重复消费。

- `dedupe_key`
  - 平台内部去重键。
  - 入库后作为“是否已处理”判定依据。

## dedupe_key 生成规则
1. 若 `external_event_id` 存在：
   - `dedupe_key = external_event_id`
2. 若 `external_event_id` 缺失：
   - 按业务语义构造稳定组合键并哈希，例如：
   - `sha256(channel + event_type + xianyu_order_id + supply_order_no + event_time_bucket + body_md5)`

## 说明
- `external_event_id` 与 `dedupe_key` 可相同（优先路径）。
- `external_event_id` 缺失时必须保证组合键字段稳定、可复现，避免同事件因字段顺序差异导致重复处理。
