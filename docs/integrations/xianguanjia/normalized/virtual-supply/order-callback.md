# 订单回调通知（归一化）

## 1. 用途
接收卡密/直充订单的异步结果（成功、失败、卡密明文、券码明细等）。

## 2. 请求路径方法
- **Path**：`https://open.goofish.pro/api/open/callback/virtual/order/notify/{token}`
- **Method**：`POST`
- **Content-Type**：`application/json`
- **Query**：`mch_id`、`timestamp`、`sign`

## 3. 请求字段
| 字段名 | 类型 | 必填 | 说明 | 示例 |
|---|---|---|---|---|
| order_type | int | 是 | 订单类型 | `1` |
| order_no | string | 是 | 管家订单号 | `1930200159667566229` |
| out_order_no | string | 是 | 业务侧订单号 | `API2024123012834901444` |
| order_status | int | 是 | 订单状态码 | `20` |
| end_time | int | 否 | 结束时间（Unix秒） | `1723870189` |
| card_items[] | array | 否 | 卡密列表 | `[{"card_no":"...","card_pwd":"..."}]` |
| ticket_items[] | array | 否 | 券码列表（含状态/有效期） | `[{"code_no":"...","status":1}]` |
| remark | string | 否 | 失败/补充说明 | `该运营商地区不支持充值` |

## 4. 返回字段
| 字段名 | 类型 | 说明 | 示例 |
|---|---|---|---|
| code | int | ACK码，0表示接收成功 | `0` |
| msg | string | ACK说明 | `OK` |

## 5. 错误码
| 错误码 | 含义 | 处理建议 |
|---|---|---|
| 0 | 接收成功 | 停止重试 |
| 非0/HTTP非2xx | 接收失败 | 对方将重试，排查签名/入库异常 |

## 6. 验签规则（必须执行）
- 回调URL Query中必须存在：`mch_id`、`timestamp`、`sign`。
- Body 参与验签使用**请求原始字节串**（不可二次序列化）。
- 计算步骤：
  1. 读取原始Body字符串 `bodyRaw`。
  2. 计算 `bodyMd5 = md5(bodyRaw)`。
  3. 按接入密钥拼接：`signPlain = "app_id,app_secret,bodyMd5,timestamp,mch_id,mch_secret"`。
  4. `expected = md5(signPlain)`。
  5. 常量时间比较 `expected == sign`，不通过直接返回HTTP 401/业务失败。
- 注意：`timestamp` 来自 Query，不从 Body 取值。

## 7. 幂等建议（落库级）
- 幂等键：`(order_no, out_order_no, order_status)`。
- 建唯一索引后先入库再执行业务；冲突视为重复回调并直接ACK成功。

## 8. 重放防护建议（不可省）
- 时间窗：校验 `abs(now - timestamp) <= 300s`，超窗拒绝。
- 去重缓存：保存 `sign` 或 `event_digest(md5(bodyRaw))` 5~10分钟，命中即判重放。
- 仅允许白名单IP（如已配置）。
- 回包固定：`{"code":0,"msg":"OK"}`。

## 9. 文档来源(raw_html_path)
- `raw_html_path`: `/Users/brianzhibo/openclaw/xianyu-openclaw/docs/external/xianguanjia/fullcrawl/raw/3ab35f4b476f8e42.html`
