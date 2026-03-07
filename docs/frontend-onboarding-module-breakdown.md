# 前端与首次引导模块说明（当前主线版）

> 目标：让第一次接触项目的用户能在当前工作台中完成启动、配置和首轮自检。
> 范围：当前已实现页面、`SetupGuide` 首次配置引导，以及后续补强项。

## 1. 当前页面树

```text
/dashboard                    工作台总览 + 首次配置引导
/products                     商品管理
/products/auto-publish        AI 自动上架
/orders                       订单中心
/messages                     消息状态与日志
/accounts                     店铺管理
/config                       系统配置
/analytics                    数据分析
```

当前没有独立的 `/welcome/*` 安装流或旧 SaaS 登录流。

## 2. 已实现的首次引导

当前首次引导由 [client/src/components/SetupGuide.jsx](/Users/peterzhang/xianyu-openclaw/client/src/components/SetupGuide.jsx) 提供，嵌在 [client/src/pages/Dashboard.jsx](/Users/peterzhang/xianyu-openclaw/client/src/pages/Dashboard.jsx)。

它会检查 5 项：

1. `Node 代理（可选）`
2. `Python 后端`
3. `闲管家 API 配置`
4. `AI 服务配置`
5. `闲鱼 Cookie`

行为规则：

- 未全部完成时显示引导卡片。
- 已完成项显示绿色状态。
- 未完成项提供跳转到 `/config` 或 `/accounts` 的入口。
- 用户可以临时关闭引导，并写入本地存储。

## 3. 当前 onboarding 设计约束

- 不使用 mock 数据。
- 检查项直接调用真实 Python / Node 接口。
- 不额外引入登录页、注册页或旧产品壳层。
- 失败时优先给“去哪里修”的明确入口，而不是抽象错误。

## 4. 后续补强项

### Phase 1

- 把 Cookie 检查从“是否存在”升级为“是否有效 + 对应账号是谁”。
- 在引导中展示闲管家配置缺失的具体字段。

### Phase 2

- 为首单发布流程增加任务式引导。
- 在订单和商品页增加更明确的空状态说明。

### Phase 3

- 引入诊断包导出入口。
- 引入更完整的错误解释与恢复建议。

## 5. 验收标准

- 新用户能在工作台首页完成首次配置。
- 至少能定位 AI、闲管家和 Cookie 三类配置问题。
- 工作台不再出现与当前业务无关的旧认证或旧 SaaS 页面。
