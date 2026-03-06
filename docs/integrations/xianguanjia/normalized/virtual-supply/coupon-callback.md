# 券码回调通知（归一化）

## 1. 用途
接收单张券码维度状态变更（发码、使用、撤销）。

## 2. 请求路径方法
- **Path**：`https://open.goofish.pro/api/open/callback/virtual/order/ticket/notify`
- **Method**：`POST`
- **Content-Type**：`application/json`
- **Query**：`mch_id`、`timestamp`、`sign`

## 3. 请求字段
| 字段名 | 类型 | 必填 | 说明 | 示例 |
|---|---|---|---|---|
| order_no | string | 是 | 管家订单号 | `string` |
| out_order_no | string | 是 | 业务订单号 | `string` |
| code_no | string | 是 | 券码编号 | `string` |
| status | int | 是 | 券码状态 | `1` |
| use_time | int | 否 | 使用时间（Unix秒） | `0` |
| revoke_time | int | 否 | 撤销时间（Unix秒） | `0` |

## 4. 返回字段
| 字段名 | 类型 | 说明 | 示例 |
|---|---|---|---|
| code | int | ACK码 | `0` |
| msg | string | ACK信息 | `OK` |

## 5. 错误码
| 错误码 | 含义 | 处理建议 |
|---|---|---|
| 0 | 接收成功 | 结束 |
| 非0/HTTP非2xx | 接收失败 | 上游重试，先排查验签与幂等 |

## 6. 验签规则（必须执行）
- Query参数：`mch_id`、`timestamp`、`sign` 必填。
- 验签字段：`app_id`、`app_secret`、`bodyMd5`、`timestamp`、`mch_id`、`mch_secret`。
- 步骤：取原始Body→算`bodyMd5`→拼接明文→MD5→常量时间比较。

## 7. 幂等建议（落库级）
- 幂等键：`(order_no, out_order_no, code_no, status)`。
- 重复通知不重复变更券状态，直接ACK成功。

## 8. 重放防护建议（不可省）
- `timestamp` 时间窗 ±300 秒。
- 缓存最近 `sign`/`md5(bodyRaw)` 10 分钟防重放。
- 回包固定：`{"code":0,"msg":"OK"}`。

## 9. 文档来源(raw_html_path)
- `raw_html_path`: `/Users/brianzhibo/openclaw/xianyu-openclaw/docs/external/xianguanjia/fullcrawl/raw/7830a4d4a7f6e8e5.html`
