# 创建商品（单个）

## raw_html_path
`/Users/brianzhibo/openclaw/xianyu-openclaw/docs/external/xianguanjia/fullcrawl/raw/92f3c306c0a042f8.html`

## method
`POST`

## path
`/api/open/product/create`

## 请求字段表
| 字段名 | 类型 | 必填 | 说明 |
|---|---|---|---|
| appid | string | 是 | 开放平台 AppKey（Query） |
| timestamp | string | 是 | 秒级时间戳，5 分钟有效（Query） |
| sign | string | 是 | MD5 签名（Query） |
| seller_id | string | 否 | 商家 ID（仅商务对接） |
| product_id | int64 | 是 | 管家商品 ID |
| price | int | 否 | 商品价格（分，按接口能力可更新） |
| user_name | string[] | 否 | 指定上架店铺会员名列表（多店场景） |

## 返回字段表
| 字段名 | 类型 | 说明 |
|---|---|---|
| code | int | 0 成功，非 0 失败 |
| msg | string | 状态描述 |
| data | object | 创建受理结果（异步场景以回调为准） |

## 错误码
| 错误码 | 含义 | 处理建议 |
|---|---|---|
| 0 | 成功 | 正常处理业务结果。 |
| 400 | 参数错误/强校验失败 | 按字段类型与必填约束修正后重试。 |
| 401 | 签名错误或鉴权失败 | 重新计算签名并校准服务器时间。 |
| 429 | 请求过频 | 指数退避后重试。 |
| 500 | 服务内部错误 | 短暂重试；持续失败联系闲管家。 |

## 签名规则
- 使用 **MD5**。
- 先计算请求体原文的 `bodyMd5 = md5(bodyString)`；无 body 时使用 `md5("{}")`（或双方约定为 `md5("")`，保持请求与签名一致）。
- 普通对接签名串：`md5("appKey,bodyMd5,timestamp,appSecret")`。
- 商务对接（传 seller_id）签名串：`md5("appKey,bodyMd5,timestamp,seller_id,appSecret")`。
- Query 通用参数：`appid`、`timestamp`、`sign`；`seller_id` 仅商务对接传入。

## 幂等建议
- 以业务主键做幂等键，避免重复写：
  - 商品相关：`product_id`（多店场景可追加 `user_name` 维度）。
  - 订单改价：`order_no` + 目标价格。
  - 订单发货：`order_no` + `waybill_no`。
- 调用方应保存请求摘要（bodyMd5 + timestamp + 业务键）至少 24 小时。
- 命中重复请求时，优先返回上次成功结果，避免重复状态变更。

## 重试建议
- 可重试：网络超时、连接中断、HTTP 5xx、`429`。
- 不可重试：参数校验失败、签名错误、业务明确拒绝（如商品/订单状态不允许）。
- 重试策略：指数退避（1s/2s/4s）+ 随机抖动，最多 3 次。
- 超过重试上限后转人工排查，并保留请求/响应日志用于对账。
