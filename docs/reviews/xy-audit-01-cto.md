# XY-AUDIT-01 CTO技术总审报告

- 审查编号：XY-AUDIT-01
- 审查角色：CTO技术总审
- 审查范围：架构一致性、模块边界、关键链路（售前/运营/售后）、配置与可维护性、覆盖率补测改动技术债
- 审查方式：只读静态审查（未改动业务代码）

---

## 总结结论（技术维度）

**结论：No-Go（当前不建议直接放行）**

原因：发现 2 个 **P1** 级问题，分别影响自动恢复链路稳定性与配置可控性；另有若干 **P2** 架构与可维护性问题，短期可带病运行但会持续放大维护成本。

---

## 分级问题清单

## P1-01 配置键漂移被静默吞掉，存在“看似已配置、实则未生效”的隐式默认风险

**证据**
- `src/core/config_models.py:236-264`：`ConfigModel` 未声明 `extra='forbid'`，Pydantic 默认会忽略未知字段。
- `config/config.yaml:84-85`：使用 `messages.fast_first_reply_enabled` / `messages.first_reply_target_seconds`。
- `src/core/config_models.py:137-139`：实际模型字段为 `fast_reply_enabled` / `reply_target_seconds`。
- `config/config.yaml:277`：使用 `quote.cost_api_key`。
- `src/core/config_models.py:183-205`：`QuoteConfig` 中无 `cost_api_key` 字段（仅 `providers` 等结构）。

**风险**
- 运营/研发误以为参数已生效，实际系统回落到默认值，导致线上行为不可预测。
- 对售前首响SLA和报价链路参数调整失真，增加排障时间。

**修复建议**
1. 在配置模型启用严格校验（未知键直接报错），至少在 CI/启动阶段 fail-fast。
2. 增加配置 lint：对 `config/config.yaml` 做 schema 对齐检查，输出“未知键清单”。
3. 将历史兼容键做显式迁移映射（一次性告警+自动转换），避免 silent fallback。

---

## P1-02 presales 自动恢复状态机与并发控制不一致，存在重复恢复/阻塞放大风险

**证据**
- `src/dashboard_server.py:679-697`：`_trigger_presales_recover_after_cookie_update()` 每次都直接 `module_console.control(recover)`，没有基于 cookie 指纹的幂等短路。
- `src/dashboard_server.py:2418-2429`：`_maybe_auto_recover_presales()` 在锁内执行 `module_console.control(recover)`（阻塞外部子进程调用），锁粒度过大。
- `src/dashboard_server.py:2437-2438`：`_last_cookie_fp/_last_token_error` 在锁外更新，状态快照与 recover 执行并非同一临界区。

**风险**
- 多请求并发下可能出现重复 recover 触发，导致模块频繁 stop/start 抖动。
- 锁内阻塞外部 CLI 调用会拉长关键接口响应时间，极端情况下放大“恢复风暴”。

**修复建议**
1. 将 recover 触发改为“先锁内判定幂等并标记，再锁外执行恢复”，缩小临界区。
2. `update_cookie/import_cookie_plugin_files` 触发恢复前先比较 `cookie_fp` 与 `last_auto_recover_cookie_fp`，相同则直接返回 no-op。
3. 明确状态机转移表（token_error/cookie_changed/recover_inflight），并补充并发单测。

---

## P2-01 `src/cli.py` 与 `dashboard_server.py` 模块编排“能力一致但参数语义不一致”

**证据**
- CLI 默认：`src/cli.py:1735` `--interval` 默认 `1.0` 秒；`src/cli.py:1730` status窗口默认 `1440` 分钟；`src/cli.py:1746` logs 默认 `80` 行。
- Dashboard 封装默认：`src/dashboard_server.py:232-237` status窗口固定 `60` 分钟；`src/dashboard_server.py:240` logs 默认 `120` 行；`src/dashboard_server.py:265-317` start/restart/recover 统一注入 `--interval 5 --init-default-tasks`。

**风险**
- 同一模块动作在 CLI 与 Dashboard 上观测口径不同（尤其 SLA window），容易出现“命令行正常/面板异常”认知分裂。
- 运维手册难统一，故障复盘时参数不可比。

**修复建议**
1. 将模块控制参数抽成单一配置源（例如 `module_control_defaults`），CLI 与 Dashboard 共用。
2. 对 status/logs 显示当前生效参数，避免隐式默认。
3. 在 Dashboard 控制面板允许可见化调整 interval/window，避免硬编码。

---

## P2-02 服务健康判定过度绑定 presales，运营/售后失效不会触发统一降级

**证据**
- `src/dashboard_server.py:2517-2519`：`xianyu_connected` 仅基于 presales 进程与 token 风险。
- `src/dashboard_server.py:2520-2521`：service_status 降级判断仅依赖 `xianyu_connected`/risk_level。
- `src/dashboard_server.py:2553-2556`：虽返回 `alive_count/total_modules`，但未纳入最终降级判定逻辑。

**风险**
- 运营或售后模块挂掉时，服务仍可能显示 running/degraded 不敏感，影响值班决策。

**修复建议**
1. 健康模型改为分模块加权（presales/operations/aftersales）并输出总体状态。
2. 至少引入“关键模块存活阈值”策略：任一关键模块 down -> degraded。

---

## P2-03 近两轮覆盖率补测暴露“以测试补洞代替解耦”的结构性技术债

**证据**
- `src/cli.py` 体量 `1831` 行（单文件高耦合命令分发）。
- `tests/test_targeted_round6_part1.py:3`：测试内已明确记录 `src/cli.py` 分发函数体量过大、覆盖率成本高。
- `tests/test_targeted_round10_part1.py:40-48`：直接测试私有函数 `_run_messages_sla_benchmark`（耦合内部实现）。
- 大量“targeted_round/targeted_xy_cov”文件（如 `tests/test_targeted_round10_part1.py`, `tests/test_targeted_round11_part1.py`, `tests/test_targeted_round12_part1.py`）显示近期补测以碎片化定向用例为主。

**风险**
- 回归测试对内部细节敏感，重构阻力持续上升。
- 功能新增将继续把 CLI 与 Dashboard 推向“巨石入口+大量猴补测试”模式。

**修复建议**
1. 将 `cmd_module/cmd_messages/cmd_orders` 等拆分为独立 command handler 模块。
2. 把私有逻辑下沉为可复用 service 层，测试优先覆盖稳定接口而非私有函数。
3. 设立“覆盖率提升伴随解耦”门禁：新增 targeted 测试时需附至少一项结构拆分。

---

## 针对必查项的结论

1. **`src/cli.py` 与 `dashboard_server.py` 模块编排一致性**：
   - 结论：**主流程一致（都通过 `src.cli module` 控制）但参数默认不一致**，属 **P2** 运维语义偏差。

2. **presales 自动恢复与 cookie 更新链路竞态/状态机漏洞**：
   - 结论：存在 **P1** 风险，主要是幂等与锁粒度问题（重复 recover / 阻塞放大）。

3. **配置项与环境变量重复/冲突/隐式默认风险**：
   - 结论：存在 **P1** 风险，表现为未知配置键被静默忽略、样例 env 与实际读取键存在漂移。

4. **近两轮覆盖率补测是否引入结构性技术债**：
   - 结论：存在 **P2** 技术债，补测有效提升覆盖但强化了私有实现耦合，未同步完成架构解耦。

---

## Go / No-Go（仅技术维度）

**No-Go**。

建议至少完成 P1-01、P1-02 修复并补充回归后再放行；P2 可排入后续两迭代治理计划。
