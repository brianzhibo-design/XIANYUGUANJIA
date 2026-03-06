# 创建券码订单（归一化）

## 1. 用途
用于创建“券码类”订单，后续通过券码回调接收具体券码状态。

## 2. 请求路径方法
- **Path**：`/goofish/order/ticket/create`
- **Method**：`POST`
- **Content-Type**：`application/json`
- **Query**：`mch_id`、`timestamp`、`sign`

## 3. 请求字段
| 字段名 | 类型 | 必填 | 说明 | 示例 |
|---|---|---|---|---|
| order_no | string | 是 | 平台侧订单号 | `1929063817978999932` |
| goods_no | string | 是 | 货源商品编号 | `12344532` |
| buy_quantity | int | 是 | 下单数量 | `1` |
| max_amount | int | 是 | 可接受最高金额（分） | `1000` |
| biz_order_no | string | 否 | 业务侧幂等单号 | `API2024123012834901444` |
| buyer_eid | string | 否 | 买家标识（券核销链路） | `string` |
| valid_start_time | int | 否 | 生效时间（Unix秒） | `0` |
| valid_end_time | int | 否 | 失效时间（Unix秒） | `0` |
| is_expire_refund | bool | 否 | 过期是否自动退款 | `true` |
| is_unuse_refund | bool | 否 | 未使用是否可退 | `true` |
| notify_url | string | 是 | 订单/券码通知地址 | `https://open.goofish.pro/api/open/callback/virtual/order/notify/{token}` |
| product_id/product_sku/item_id | int | 否 | 透传字段 | `0` |

## 4. 返回字段
| 字段名 | 类型 | 说明 | 示例 |
|---|---|---|---|
| code | int | `0`成功 | `0` |
| msg | string | 返回说明 | `OK` |
| data | object | 下单结果对象 | `{}` |

## 5. 错误码
| 错误码 | 含义 | 处理建议 |
|---|---|---|
| 0 | 成功 | 正常处理 |
| 401 | 签名错误 | 校验签名串、时间戳、Body原文是否一致 |
| 403 | IP 不在白名单 | 检查来源IP白名单 |
| 408 | 时间戳过期 | 校准NTP |
| 1201 | 下单参数错误 | 修正参数 |
| 1209 | 下单超时 | 查单或等待回调 |

## 6. 签名规则
同接入说明：`sign = md5("app_id,app_secret,bodyMd5,timestamp,mch_id,mch_secret")`。

## 7. 幂等建议
- 幂等键：`biz_order_no`（首选），降级使用`order_no`。
- 重复请求统一返回首次单据，不重复创建券码。

## 8. 重试建议
仅重试超时/5xx，参数或鉴权错误直接失败。

## 9. 文档来源(raw_html_path)
- `raw_html_path`: `/Users/brianzhibo/openclaw/xianyu-openclaw/docs/external/xianguanjia/fullcrawl/raw/3b21f385b9978974.html`
