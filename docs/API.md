# API 文档

当前主线有两套 HTTP 服务：

- `Python Core`：核心业务接口，默认 `http://localhost:8091`
- `Node Proxy`：薄代理与 webhook 验签，默认 `http://localhost:3001`

前端工作台主要直接调用 Python 接口；Node 只负责代理和 webhook 场景。

## Python Core

### 健康与状态

- `GET /healthz`
- `GET /api/status`
- `GET /api/summary`
- `GET /api/trend`
- `GET /api/top-products`
- `GET /api/recent-operations`

### 配置与账号

- `GET /api/config`
- `POST /api/config`
- `GET /api/config/sections`
- `GET /api/accounts`
- `POST /api/update-cookie`

### 商品、订单与闲管家

- `GET /api/xgj/products`
- `GET /api/xgj/orders`
- `POST /api/xgj/settings`
- `POST /api/xgj/retry-price`
- `POST /api/xgj/retry-ship`
- `POST /api/xgj/product/publish`
- `POST /api/xgj/product/unpublish`
- `POST /api/xgj/order/modify-price`
- `POST /api/xgj/order/deliver`
- `POST /api/orders/callback`

### 自动上架

- `GET /api/listing/templates`
- `POST /api/listing/preview`
- `POST /api/listing/publish`
- `GET /api/generated-image?path=...`

### 运行控制与诊断

- `POST /api/module/control`
- `GET /api/module/status`
- `GET /api/module/check`
- `GET /api/module/logs`
- `POST /api/service/control`
- `POST /api/service/recover`
- `POST /api/service/auto-fix`
- `GET /api/logs/files`
- `GET /api/logs/content`
- `GET /api/logs/realtime/stream`

### 兼容保留的 Dashboard / 运维接口

这些接口仍然存在，但不再是 React 工作台的主要入口：

- `GET /api/dashboard`
- `GET /api/virtual-goods/metrics`
- `GET /api/virtual-goods/inspect-order`
- `POST /api/virtual-goods/inspect-order`
- `GET /api/get-cookie`
- `GET /api/route-stats`
- `GET /api/export-routes`
- `GET /api/download-cookie-plugin`
- `GET /api/get-template`
- `GET /api/replies`
- `GET /api/get-markup-rules`
- `POST /api/import-cookie-plugin`
- `POST /api/parse-cookie`
- `POST /api/cookie-diagnose`
- `POST /api/import-routes`
- `POST /api/import-markup`
- `POST /api/reset-database`
- `POST /api/save-template`
- `POST /api/save-markup-rules`
- `POST /api/test-reply`

### 兼容保留的 HTML 运维页面

- `GET /`
- `GET /cookie`
- `GET /test`
- `GET /logs`
- `GET /logs/realtime`

它们是历史 Dashboard / 内部诊断界面，不是当前主工作台。

## Node Proxy

### 健康检查

- `GET /health`

### 配置代理

- `GET /api/config`
- `POST /api/config`
- `PUT /api/config`
- `GET /api/config/sections`

这些接口只是把请求转发给 Python。

### 闲管家代理 / webhook

- `POST /api/xgj/proxy`
- `POST /api/xgj/order/receive`
- `POST /api/xgj/product/receive`

说明：

- `/api/xgj/proxy` 用于透传 Open Platform 请求。
- `/api/xgj/*/receive` 会先做签名校验，再转发给 Python `/api/orders/callback` 等回调接口。

## CLI

项目仍保留：

```bash
python -m src.cli
```

它用于模块诊断和恢复，不再承担旧式 OpenClaw 主调度职责。

## 约束

- 所有前端页面都必须走真实接口。
- 不允许为了展示而在接口层返回 mock 数据。
- Python 是唯一业务真相源，Node 不是配置真相源。
- `Legacy Browser Runtime` 只作为补充链路保留，不能重新成为默认依赖。
