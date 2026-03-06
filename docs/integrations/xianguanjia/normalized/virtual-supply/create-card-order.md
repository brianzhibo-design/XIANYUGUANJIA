# 创建卡密订单（归一化）

## 1. 用途
用于向闲管家虚拟货源发起“卡密类”下单，创建后由订单回调返回卡密明文。

## 2. 请求路径方法
- **Path**：`/goofish/order/purchase/create`
- **Method**：`POST`
- **Content-Type**：`application/json`
- **Query**：`mch_id`、`timestamp`、`sign`

## 3. 请求字段
| 字段名 | 类型 | 必填 | 说明 | 示例 |
|---|---|---|---|---|
| order_no | string | 是 | 平台侧订单号（请求唯一） | `1929063817978999932` |
| goods_no | string | 是 | 货源商品编号 | `12344532` |
| buy_quantity | int | 是 | 购买数量 | `1` |
| max_amount | int | 是 | 可接受最高金额（分） | `1000` |
| notify_url | string | 是 | 订单回调地址 | `https://open.goofish.pro/api/open/callback/virtual/order/notify/{token}` |
| biz_order_no | string | 否 | 业务侧幂等单号（强烈建议传） | `API2024123012834901444` |
| product_id | int | 否 | 业务产品ID（透传） | `0` |
| product_sku | int | 否 | SKU ID（透传） | `0` |
| item_id | int | 否 | 子商品ID（透传） | `0` |

## 4. 返回字段
| 字段名 | 类型 | 说明 | 示例 |
|---|---|---|---|
| code | int | 业务码，`0`成功 | `0` |
| msg | string | 返回说明 | `OK` |
| data | object | 下单结果对象（至少含订单标识） | `{"order_no":"...","out_order_no":"..."}` |

## 5. 错误码
| 错误码 | 含义 | 处理建议 |
|---|---|---|
| 0 | 成功 | 正常处理 |
| 401 | 签名错误 | 校验签名串、时间戳、Body原文是否一致 |
| 403 | IP 不在白名单 | 检查回调/调用来源IP白名单 |
| 408 | 时间戳过期 | 校准NTP，确保时间窗内请求 |
| 1201 | 下单参数错误 | 按字段约束修正请求体 |
| 1209 | 下单超时 | 走查单/异步回调确认最终结果 |

## 6. 签名规则
- 是否需要签名：`是`
- 签名参与字段：`app_id, app_secret, bodyMd5, timestamp, mch_id, mch_secret`
- 算法：`MD5`
- 拼接规则：`md5("app_id,app_secret,bodyMd5,timestamp,mch_id,mch_secret")`
- `bodyMd5`：对 **HTTP Body原文字符串** 做 MD5（必须与实际发送字节一致）

## 7. 幂等建议
- 幂等键：`biz_order_no`（首选）+ `goods_no`。
- 唯一性：同商户(`mch_id`)下全局唯一。
- 重复请求：若幂等键已存在，返回首次创建结果，不重复扣款。

## 8. 重试建议
- 可重试：网络超时、5xx、`1209`。
- 不可重试：`401/403/1201`。
- 使用指数退避：1s/2s/4s，最多3次；超限改为查单+等回调。

## 9. 文档来源(raw_html_path)
- `raw_html_path`: `/Users/brianzhibo/openclaw/xianyu-openclaw/docs/external/xianguanjia/fullcrawl/raw/7c2913e6930c682c.html`
