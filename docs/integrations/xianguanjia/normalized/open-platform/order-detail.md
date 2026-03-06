# 闲管家开放平台 - 查询订单详情（归一化）

## 1. 用途
根据订单号查询单笔订单全量信息（交易、收货、履约、商品快照、退款相关字段），用于售后核查、履约追踪和对账落库。

## 2. 请求路径方法
- **Path**: `/api/open/order/detail`
- **Method**: `POST`
- **Content-Type**: `application/json`

## 3. 请求字段
| 字段名 | 类型 | 必填 | 说明 | 示例 |
|---|---|---|---|---|
| order_no | string | 是 | 订单号 | `3364202298717566229` |

## 4. 返回字段
> 该接口 raw 响应样例为对象结构（未包裹 `code/msg/data`），与列表接口样式不一致，需上游确认最终协议。

| 字段名 | 类型 | 说明 | 示例 |
|---|---|---|---|
| order_no | string | 订单号 | string |
| order_status | int | 订单状态（枚举待补） | 0 |
| order_type | int | 订单类型（枚举待补） | 0 |
| order_time | int | 下单时间（时间戳秒） | 0 |
| total_amount | int | 总金额（单位待补） | 0 |
| pay_amount | int | 实付金额（单位待补） | 0 |
| pay_no | string | 支付流水号 | string |
| pay_time | int | 支付时间（时间戳秒） | 0 |
| refund_status | int | 退款状态（枚举待补） | 0 |
| refund_amount | string | 退款金额（类型疑似异常，待补原文确认） | "1" |
| refund_time | int | 退款时间（时间戳秒） | 0 |
| receiver_mobile/receiver_name | string | 收货手机号/收货人 | string |
| prov_name/city_name/area_name/town_name | string | 省市区街道 | string |
| address | string | 详细地址 | string |
| waybill_no | string | 运单号 | string |
| express_code/express_name | string | 物流公司编码/名称 | string |
| express_fee | int | 运费 | 0 |
| consign_type | int | 发货类型（枚举待补） | 0 |
| consign_time | int | 发货时间（时间戳秒） | 0 |
| confirm_time | int | 确认收货时间（时间戳秒） | 0 |
| cancel_reason | string | 取消原因 | string |
| cancel_time | int | 取消时间（时间戳秒） | 0 |
| create_time/update_time | int | 创建/更新时间（时间戳秒） | 0 |
| buyer_eid/buyer_nick | string | 买家标识/昵称 | string |
| seller_eid/seller_name/seller_remark | string | 卖家标识/昵称/备注 | string |
| idle_biz_type | int | 业务类型（枚举待补） | 0 |
| pin_group_status | int | 拼团状态（枚举待补） | 0 |
| goods | object | 商品信息快照 | - |
| goods.quantity | int | 数量 | 0 |
| goods.price | int | 单价（单位待补） | 0 |
| goods.product_id/item_id | int | 商品ID/闲鱼item_id | 0 |
| goods.outer_id | string | 外部商品ID | string |
| goods.sku_id/sku_outer_id/sku_text | int/string | SKU信息 | - |
| goods.title | string | 商品标题 | string |
| goods.images | array<string> | 商品图片数组 | ["string"] |
| goods.service_support | string | 服务支持描述 | string |
| xyb_seller_amount | int | 卖家结算金额（语义待补） | 0 |
| is_tax_included | bool | 是否含税 | true |

## 5. 错误码
| 错误码 | 含义 | 处理建议 |
|---|---|---|
| 0 | 成功（接入说明给出的通用约定） | 正常处理 |
| 非0 | 失败（接口页未提供明细） | 记录原始响应并人工排查 |

> 阻塞项：raw 未给出本接口错误码、状态枚举、金额单位/refund_amount 类型定义。

## 6. 签名规则
签名规则来自开放平台接入说明（doc-2686716）：

- 是否需要签名：**是**
- 参与字段：`appKey`、`bodyMd5`、`timestamp`、`appSecret`
- 算法：`MD5`
- 规则：
  1. `bodyMd5 = md5(POST原文JSON字符串)`
  2. `sign = md5("appKey,bodyMd5,timestamp,appSecret")`
- 无 body 时：`md5("{}")` 或 `md5("")`，但请求体和签名计算体必须一致。
- 商务对接变体：可追加 `商家ID` 参与签名（文档标注为可选场景）。

## 7. 幂等建议
- 查询类接口天然幂等。
- 建议以 `order_no` 作为缓存键，设置短TTL降低重复查单压力。
- 对账流程中，以 `order_no + update_time` 判定是否需要覆盖落库。

## 8. 重试建议
- 可重试：网络超时、连接失败、网关5xx、限流。
- 不可重试：参数错误、签名错误、鉴权失败。
- 重试采用指数退避+随机抖动，避免查单风暴。

## 9. 文档来源(raw_html_path)
- 接口raw：`/Users/brianzhibo/openclaw/xianyu-openclaw/docs/external/xianguanjia/fullcrawl/raw/ebc0c67812236f8f.html`
- 接入说明（签名规则）raw：`/Users/brianzhibo/openclaw/xianyu-openclaw/docs/external/xianguanjia/fullcrawl/raw/47ceb03ae799d64d.html`
- URL映射清单：`/Users/brianzhibo/openclaw/xianyu-openclaw/docs/external/xianguanjia/fullcrawl/meta/manifest.json`

## 10. 阻塞标记建议（供 DOC-MAP）
- 建议值：`status=blocked_raw_missing`
- 理由：字段语义/枚举/错误码原文缺失，且响应包裹结构与同项目其它接口不一致，需补充原始定义后才能解除阻塞。