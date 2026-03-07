# 2026-03-07 API-first Main Release

## 概要

本次发布基于当前 `main`，目标是把仓库的默认主线稳定在 API-first 架构：

- Python 作为唯一核心业务引擎
- React 作为运营工作台
- Node 作为 webhook / proxy
- OpenClaw 不再作为默认依赖

## 本次收口内容

- 把 PR #41 中可复用的工作台、自动上架和部署思路通过 PR #42 重建到当前主线。
- 移除旧 `client/server` code-review SaaS 壳层的主路径影响。
- 页面全部对接真实 Python 接口，不保留展示型 mock。
- 将 `Legacy Browser Runtime` 明确降级为补充链路。
- 修正文档到当前 API-first 口径。
- 修复 `setup_wizard` 的兼容性回归，恢复全量测试通过。
- 清理远端已合并分支和本地陈旧工作分支，仓库只保留当前需要继续使用的分支。

## 发布前检查

- `client`: `npm run build` 通过
- `server`: `npm test -- --runInBand` 通过
- `python`: `python3 -m compileall src` 通过
- `python`: `.venv/bin/python -m pytest --tb=short -q` 通过
  - `891 passed`
  - `coverage 89.04%`
- smoke:
  - Python `/healthz` 通过
  - Python `/api/config/sections` 通过
  - Python `/api/accounts` 通过
  - Node `/health` 通过
  - Node `/api/config/sections` 通过

## 文档口径

以下文档已按当前 `main` 更新：

- `README.md`
- `QUICKSTART.md`
- `USER_GUIDE.md`
- `docs/API.md`
- `docs/DEPLOYMENT.md`
- `docs/PROJECT_PLAN.md`
- `docs/PROJECT_MINDMAP_CLEAR_V1.md`
- `docs/PROJECT_MODULE_ROADMAP_XY-MOD-004.md`
- `docs/SUCCESS_BENCHMARK_AND_SURPASS_PLAN.md`
- `docs/frontend-onboarding-module-breakdown.md`
- `docs/qa-release-verdict.md`

## 仍需线下确认

- 使用真实闲管家凭证进行一次目标环境联调。
- 继续推进多店铺、消息链路状态统一和运维面收敛。
