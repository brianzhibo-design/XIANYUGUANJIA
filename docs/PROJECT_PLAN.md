# 项目计划

## 主线目标

把仓库长期收敛到一条明确主线：

1. 去掉 OpenClaw 作为运行前提。
2. 保留 Python 作为唯一核心业务引擎。
3. 商品、订单、配置、自动上架优先走闲管家 / Open Platform API。
4. API 无法覆盖的能力，才保留 WS 或站点侧补充链路。
5. React 页面全部接真实接口，不提供展示型 mock。

## 当前状态

当前 `main` 已完成以下收敛：

- 用 PR #41 中可复用的工作台信息架构替换旧 `client/server` SaaS 壳层。
- 通过 PR #42 把这套工作台重建到当前主线，而不是直接合并旧分支。
- 配置中心、商品、订单、自动上架页面已切到真实 Python 接口。
- 消息中心移除本地伪发送，只展示真实状态和日志。
- Node 收窄为 `config` 代理、`xgj` proxy 和 webhook 验签。
- `Legacy Browser Runtime` 已降级为补充链路，不再作为默认依赖。

## 当前模块分工

- `client/`：React 运营工作台
- `server/`：Node 薄代理与 webhook 校验
- `src/`：Python 核心业务、运维接口和诊断能力

## 下一阶段

### Phase 1：配置和账号收敛

- 继续稳定 Python 配置 contract。
- 补齐多店铺切换和真实账号映射。
- 消除仍需要 `openclaw` 兼容别名的内部命名。

### Phase 2：消息与回调整合

- 统一消息链路的 API-first + WS fallback 状态面板。
- 评估把 Node 的 webhook 验签逻辑逐步下沉到 Python。
- 明确回调重试、幂等和可观测字段。

### Phase 3：运维面统一

- 收敛历史 Dashboard HTML 与 React 工作台的重叠能力。
- 把常见诊断能力迁到 React 页面，同时保留 CLI / Python 运维底座。
- 建立固定发布门禁和 release 文档模板。

## 发布门禁

- 前端构建通过。
- Node 测试通过。
- Python 测试通过。
- 关键健康检查和核心接口 smoke 通过。
- 文档与当前 `main` 的真实行为一致。

## 非目标

- 不恢复旧 code-review SaaS 逻辑。
- 不把 Node 重新做成主业务后端。
- 不为了页面演示引入 mock 数据。
- 不让 `Legacy Browser Runtime` 重新成为默认必需依赖。
