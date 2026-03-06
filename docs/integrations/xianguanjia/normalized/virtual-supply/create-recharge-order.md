# 创建直充订单（归一化）

## 1. 用途
用于手机号/游戏账号等“直充类”商品下单。

## 2. 请求路径方法
- **Path**：`/goofish/order/recharge/create`
- **Method**：`POST`
- **Content-Type**：`application/json`
- **Query**：`mch_id`、`timestamp`、`sign`

## 3. 请求字段
| 字段名 | 类型 | 必填 | 说明 | 示例 |
|---|---|---|---|---|
| order_no | string | 是 | 平台订单号 | `1929063817978999932` |
| goods_no | string | 是 | 商品编号 | `12344532` |
| biz_content.account | string | 是 | 充值账号 | `13800138000` |
| biz_content.game_name | string | 否 | 游戏名 | `王者荣耀` |
| biz_content.game_role | string | 否 | 角色名 | `貂蝉` |
| biz_content.game_area | string | 否 | 大区 | `A区` |
| biz_content.game_server | string | 否 | 服务器 | `国服` |
| biz_content.buyer_ip | string | 否 | 买家IP | `113.87.236.130` |
| biz_content.buyer_area | string | 否 | 买家地域 | `深圳市` |
| buy_quantity | int | 是 | 数量 | `1` |
| max_amount | int | 是 | 金额上限（分） | `1000` |
| notify_url | string | 是 | 回调地址 | `https://open.goofish.pro/api/open/callback/virtual/order/notify/{token}` |
| biz_order_no | string | 否 | 业务幂等号 | `string` |
| product_id/product_sku/item_id | int | 否 | 透传字段 | `0` |

## 4. 返回字段
| 字段名 | 类型 | 说明 | 示例 |
|---|---|---|---|
| code | int | `0`成功 | `0` |
| msg | string | 返回说明 | `OK` |
| data | object | 下单结果 | `{}` |

## 5. 错误码
| 错误码 | 含义 | 处理建议 |
|---|---|---|
| 0 | 成功 | 正常处理 |
| 401 | 签名错误 | 核对签名 |
| 408 | 时间戳过期 | 校时后重试 |
| 1201 | 参数错误 | 修正后再下单 |
| 1209 | 下单超时 | 查单确认 |

## 6. 签名规则
`sign = md5("app_id,app_secret,bodyMd5,timestamp,mch_id,mch_secret")`。

## 7. 幂等建议
- 使用 `biz_order_no` 做幂等主键。
- 业务上同账号同商品短窗重复提交（如60s）要拦截。

## 8. 重试建议
超时/网络异常可重试3次；避免对同 `biz_order_no` 并发重试。

## 9. 文档来源(raw_html_path)
- `raw_html_path`: `/Users/brianzhibo/openclaw/xianyu-openclaw/docs/external/xianguanjia/fullcrawl/raw/1c920d368ea14d7c.html`
