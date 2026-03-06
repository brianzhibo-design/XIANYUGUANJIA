# 券码退款回调通知（归一化）

## 1. 用途
接收券码订单退款结果（退款类型、金额、原因、场景、时间）。

## 2. 请求路径方法
- **Path**：`/goofish/order/refund/notify`
- **Method**：`POST`
- **Content-Type**：`application/json`
- **Query**：`mch_id`、`timestamp`、`sign`

## 3. 请求字段
| 字段名 | 类型 | 必填 | 说明 | 示例 |
|---|---|---|---|---|
| order_no | string | 是 | 管家订单号 | `1930200159667566229` |
| order_type | int | 是 | 订单类型 | `3` |
| out_order_no | string | 是 | 业务订单号 | `API2024123012834901444` |
| biz_order_no | string | 否 | 业务幂等号 | `string` |
| refund_type | int | 是 | 退款类型 | `1` |
| refund_amount | int | 是 | 退款金额（分） | `0` |
| refund_reason | string | 否 | 退款原因 | `string` |
| refund_scene | string | 否 | 退款场景 | `expire_refund` |
| refund_time | int | 否 | 退款时间（Unix秒） | `0` |

## 4. 返回字段
| 字段名 | 类型 | 说明 | 示例 |
|---|---|---|---|
| code | int | ACK码 | `0` |
| msg | string | ACK信息 | `OK` |

## 5. 错误码
| 错误码 | 含义 | 处理建议 |
|---|---|---|
| 0 | 接收成功 | 结束 |
| 非0/HTTP非2xx | 接收失败 | 上游重试，排查签名/去重/事务 |

## 6. 验签规则（必须执行）
- Query参数：`mch_id`、`timestamp`、`sign` 必填。
- 验签步骤：原始Body取MD5→按`app_id,app_secret,bodyMd5,timestamp,mch_id,mch_secret`拼接→MD5→常量时间比较。
- 失败处理：立即拒绝并记审计日志，不落业务账。

## 7. 幂等建议（落库级）
- 幂等键：`(order_no, out_order_no, refund_type, refund_time)`。
- 同键重复仅返回ACK，不重复冲正/退款入账。

## 8. 重放防护建议（不可省）
- 时间窗：`timestamp` 与服务端当前时间差不超过300秒。
- 去重：缓存`sign`和`md5(bodyRaw)`，TTL≥10分钟。
- 回包固定：`{"code":0,"msg":"OK"}`。

## 9. 文档来源(raw_html_path)
- `raw_html_path`: `/Users/brianzhibo/openclaw/xianyu-openclaw/docs/external/xianguanjia/fullcrawl/raw/32a00d377c73f700.html`
