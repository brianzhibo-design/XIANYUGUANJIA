# 闲管家开放平台 - 订单物流发货（归一化）

## 1. 用途
根据订单号提交物流发货信息（运单号、快递公司、寄件人信息），用于实物订单履约、自动同步物流到闲鱼。

## 2. 请求路径方法
- **Base URL**: `https://open.goofish.pro`
- **Path**: `/api/open/order/ship`
- **Method**: `POST`
- **Content-Type**: `application/json`

## 3. 请求字段
| 字段名 | 类型 | 必填 | 说明 | 示例 |
|---|---|---|---|---|
| order_no | string | 是 | 闲鱼订单号 | 3364202298717566229 |
| waybill_no | string | 是 | 物流单号 | JT3032658260816 |
| express_code | string | 是 | 快递公司编码（见 express-companies 接口） | sf |
| express_name | string | 条件必填 | 当 `express_code=other` 时必填，传实际快递公司名称 | 某某速运 |
| remark | string | 否 | 发货备注 | - |
| ship_name | string | 条件必填 | 寄件人姓名（见下方寄件人组合说明） | 张三 |
| ship_mobile | string | 条件必填 | 寄件人手机号（见下方寄件人组合说明） | 13800138000 |
| ship_district_id | string | 条件必填 | 寄件地区编码（见下方寄件人组合说明） | - |
| ship_prov_name | string | 条件必填 | 寄件省份（见下方寄件人组合说明） | 广东省 |
| ship_city_name | string | 条件必填 | 寄件城市（见下方寄件人组合说明） | 深圳市 |
| ship_area_name | string | 条件必填 | 寄件区县（见下方寄件人组合说明） | 南山区 |
| ship_address | string | 条件必填 | 寄件详细地址（见下方寄件人组合说明） | XX路XX号 |

### 寄件人信息三种合法组合
以下三选一，字段需成组传入：

| 组合 | 字段 |
|---|---|
| 1 | ship_name + ship_mobile + ship_district_id + ship_address |
| 2 | ship_name + ship_mobile + ship_prov_name + ship_city_name + ship_area_name + ship_address |
| 3 | ship_district_id + ship_address（无姓名/手机时） |

## 4. 返回字段
| 字段名 | 类型 | 说明 | 示例 |
|---|---|---|---|
| code | int | 0 成功，非 0 失败 | 0 |
| msg | string | 状态说明 | OK |
| data | object | 发货受理结果 | {} |

## 5. 错误码
| 错误码 | 含义 | 处理建议 |
|---|---|---|
| 0 | 成功 | 正常处理业务结果。 |
| 400 | 参数错误/强校验失败 | 按字段类型与必填约束修正后重试。 |
| 401 | 签名错误或鉴权失败 | 重新计算签名并校准服务器时间。 |
| 429 | 请求过频 | 指数退避后重试。 |
| 500 | 服务内部错误 | 短暂重试；持续失败联系闲管家。 |

## 6. 签名规则
- 是否需要签名：**是**
- 参与字段：`appKey`、`bodyMd5`、`timestamp`、`appSecret`
- 算法：`MD5`
- 规则：
  1. `bodyMd5 = md5(POST原文JSON字符串)`；无 body 时使用 `md5("{}")`
  2. 普通对接：`sign = md5("appKey,bodyMd5,timestamp,appSecret")`
  3. 商务对接（传 seller_id）：`sign = md5("appKey,bodyMd5,timestamp,seller_id,appSecret")`
- Query 通用参数：`appid`、`timestamp`、`sign`；`seller_id` 仅商务对接传入。
- Base URL：`https://open.goofish.pro`

## 7. 幂等建议
- 以 `order_no + waybill_no` 作为幂等键。
- 调用方应保存请求摘要（bodyMd5 + timestamp + 业务键）至少 24 小时。
- 命中重复请求时，优先返回上次成功结果，避免重复状态变更。

## 8. 重试建议
- 可重试：网络超时、连接中断、HTTP 5xx、429。
- 不可重试：参数校验失败、签名错误、业务明确拒绝（如订单状态不允许发货）。
- 重试策略：指数退避（1s/2s/4s）+ 随机抖动，最多 3 次。
- 超过重试上限后转人工排查，并保留请求/响应日志用于对账。

## 9. 文档来源(raw_html_path)
- 接口raw：`docs/external/xianguanjia/fullcrawl/raw/02ed8480b69042ee.html`
- 接入说明（签名规则）raw：`docs/external/xianguanjia/fullcrawl/raw/47ceb03ae799d64d.html`
