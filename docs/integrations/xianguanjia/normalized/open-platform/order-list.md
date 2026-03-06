# 闲管家开放平台 - 查询订单列表（归一化）

## 1. 用途
用于按分页条件拉取订单列表，支持按订单状态过滤，供订单同步、售后对账、履约状态看板使用。

## 2. 请求路径方法
- **Path**: `/api/open/order/list`
- **Method**: `POST`
- **Content-Type**: `application/json`

## 3. 请求字段
| 字段名 | 类型 | 必填 | 说明 | 示例 |
|---|---|---|---|---|
| page_size | int | 是 | 每页条数 | 10 |
| page_no | int | 是 | 页码（从1开始） | 1 |
| order_status | int | 否 | 订单状态过滤 | 22 |

## 4. 返回字段
> 依据 raw 示例可确认的字段如下；未在 raw 中出现但业务可能存在的字段需补原文后再补充。

| 字段名 | 类型 | 说明 | 示例 |
|---|---|---|---|
| code | int | 业务状态码，`0` 表示成功 | 0 |
| msg | string | 状态说明 | OK |
| data.list | array<object> | 订单列表 | 见下 |
| data.list[].order_no | string | 订单号 | `3364202298717566229` |
| data.list[].order_status | int | 订单状态 | 22 |
| data.list[].order_time | int | 下单时间（时间戳秒） | 1685087039 |
| data.list[].total_amount | int | 订单总金额（单位待补） | 8000 |
| data.list[].pay_amount | int | 实付金额（单位待补） | 1 |
| data.list[].pay_no | string | 支付流水号 | `2023052622001114731441899001` |
| data.list[].pay_time | int | 支付时间（时间戳秒） | 1685087067 |
| data.list[].refund_status | int | 退款状态 | 0 |
| data.list[].refund_time | int | 退款时间（时间戳秒） | 0 |
| data.list[].receiver_mobile | string | 收货手机号 | `15889106633` |
| data.list[].receiver_name | string | 收货人 | 萧祁锐 |
| data.list[].prov_name/city_name/area_name/town_name | string | 省市区街道 | 广东省/深圳市/南山区/粤海街道 |
| data.list[].address | string | 详细地址 | 桂庙新村 |
| data.list[].waybill_no | string | 运单号 | `JT3032658260816` |
| data.list[].express_code | string | 物流公司编码 | other |
| data.list[].express_name | string | 物流公司名称 | `""` |
| data.list[].express_fee | int | 运费 | 0 |
| data.list[].consign_type | int | 发货类型 | 1 |
| data.list[].consign_time | int | 发货时间（时间戳秒） | 1685087379 |
| data.list[].confirm_time | int | 确认收货时间（时间戳秒） | 1685951386 |
| data.list[].cancel_reason | string | 取消原因 | `""` |
| data.list[].cancel_time | int | 取消时间（时间戳秒） | 0 |
| data.list[].create_time/update_time | int | 创建/更新时间（时间戳秒） | 1685087040/1685951390 |
| data.list[].buyer_eid/buyer_nick | string | 买家信息 | - |
| data.list[].seller_eid/seller_name/seller_remark | string | 卖家信息 | - |
| data.list[].goods | object | 商品快照 | 见下 |
| data.list[].goods.quantity | int | 数量 | 1 |
| data.list[].goods.price | int | 商品价格（单位待补） | 8000 |
| data.list[].goods.product_id/item_id | int | 商品ID/闲鱼item_id | - |
| data.list[].goods.outer_id | string | 外部商品ID | `1111` |
| data.list[].goods.sku_id/sku_outer_id/sku_text | int/string | SKU信息 | - |
| data.list[].goods.title | string | 商品标题 | - |
| data.list[].goods.images | array<string> | 商品图 | URL数组 |
| data.list[].goods.service_support | string | 服务支持描述 | `""` |

## 5. 错误码
| 错误码 | 含义 | 处理建议 |
|---|---|---|
| 0 | 成功 | 正常处理数据 |
| 非0 | 失败（该接口 raw 未给出明细） | 记录 `code/msg/request_id`，按不可重试业务错误处理并人工排查 |

> 阻塞项：该接口页面 raw 未包含**开放平台专属错误码字典**与**order_status 枚举表**，建议补充原文。

## 6. 签名规则
签名规则来自同一套开放平台接入说明（doc-2686716）：

- 是否需要签名：**是**
- 参与字段：`appKey`、`bodyMd5`、`timestamp`、`appSecret`
- 算法：`MD5`
- 规则：
  1. `bodyMd5 = md5(POST原文JSON字符串)`
  2. `sign = md5("appKey,bodyMd5,timestamp,appSecret")`
- 无 body 时：文档注明可对 `{}` 或空串做 MD5，但请求体与签名所用 body 必须一致。
- 商务对接附加规则（文档备注）：存在 `商家ID` 参与签名的变体，非商务对接可忽略。

## 7. 幂等建议
- 读接口天然幂等，但建议按 `page_no + page_size + order_status + 同步窗口` 构造缓存键。
- 大批量同步时，使用「时间窗口 + 游标」避免翻页期间数据漂移。
- 若要做增量，优先结合 `update_time` 做高水位同步，避免漏单/重复处理。

## 8. 重试建议
- 仅对网络超时、网关5xx、限流类错误重试（指数退避+抖动）。
- 业务 `code != 0` 默认不重试，转人工或死信队列。
- 列表查询建议短超时+多次快速失败，避免阻塞全量同步流水线。

## 9. 文档来源(raw_html_path)
- 接口raw：`/Users/brianzhibo/openclaw/xianyu-openclaw/docs/external/xianguanjia/fullcrawl/raw/f9e712aa600d69b6.html`
- 接入说明（签名规则）raw：`/Users/brianzhibo/openclaw/xianyu-openclaw/docs/external/xianguanjia/fullcrawl/raw/47ceb03ae799d64d.html`
- URL映射清单：`/Users/brianzhibo/openclaw/xianyu-openclaw/docs/external/xianguanjia/fullcrawl/meta/manifest.json`

## 10. 阻塞标记建议（供 DOC-MAP）
- 建议值：`status=blocked_raw_missing`
- 理由：当前raw缺少订单状态枚举与错误码明细原文，无法完成强确定性字段语义映射。