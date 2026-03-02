# XY-MOD-003 交叉验证与质量门禁方案

- **任务ID**：XY-MOD-003
- **适用范围**：全本地运行（Lite/本地 Python）+ 新手部署（One-click / Windows bat）
- **目标**：在发布前对各模块进行统一、可执行、可复核的 Go/No-Go 质量判定
- **模块范围**：
  1. M0 基础部署与运行环境（新手部署）
  2. M1 售前模块（presales）
  3. M2 运营模块（operations）
  4. M3 售后模块（aftersales）

---

## 1. 门禁总原则（统一适用于所有模块）

1. **功能 / 稳定性 / 易用性 / 安全 / 回滚** 五维全部达标才可放行。
2. 任一模块出现 **P0/P1 缺陷未闭环**，直接 **No-Go**。
3. 所有结论必须有证据（命令、日志、截图、报告）可追溯。
4. 灰度发布必须有可观测指标与止损阈值，超阈值立即回滚。
5. 每次修复后必须执行对应回归，不允许“只修不测”。

---

## 2. 模块验证矩阵（五维）

## M0 基础部署与运行环境（新手部署）

| 维度 | 可执行检查项 | 通过阈值（Gate） | 证据要求 |
|---|---|---|---|
| 功能 | 一键部署/快速启动可完成；CLI 可运行；dashboard 可访问 | 新机器按文档从 0 到可运行 ≤ 30 分钟；关键命令成功率 100% | 终端完整日志、执行时长记录、dashboard 截图 |
| 稳定性 | 连续重启与重复启动验证（3 轮） | 连续 3 轮启动/停止无残留僵尸进程；失败重试后成功率 ≥ 99% | `module status`、`module logs` 输出，进程列表 |
| 易用性 | 新手按步骤执行（不依赖隐性知识） | 文档步骤成功率 ≥ 95%；关键报错有明确提示与下一步建议 | 新手演练记录、常见错误截图、修正文档 diff |
| 安全 | `.env`、token、日志脱敏检查 | 不提交密钥；日志无明文 token/cookie；默认配置最小暴露面 | `git status`、日志抽检结果、配置审计记录 |
| 回滚 | 启动失败后恢复到可工作基线 | 回滚路径可在 10 分钟内执行完成，恢复后健康检查通过 | 回滚命令记录、恢复后 `module check --strict` 结果 |

**M0 Go/No-Go**  
- **Go**：五维全部通过，且新手首次部署成功。  
- **No-Go**：部署路径中断、需人工改源码才能启动、或凭证/日志安全不合规。

---

## M1 售前模块（presales）

| 维度 | 可执行检查项 | 通过阈值（Gate） | 证据要求 |
|---|---|---|---|
| 功能 | `module check/start/status/logs`；会话扫描、任务认领、回复生成/发送链路 | 主流程成功率 ≥ 98%；关键子流程（扫描→认领→生成→发送）全通 | 命令输出、样例会话ID、处理统计 |
| 稳定性 | daemon 模式运行 60 分钟；异常网络/空任务队列场景 | 无崩溃；异常场景自动恢复；内存/CPU 无异常飙升 | 60 分钟窗口状态、错误计数、资源采样 |
| 易用性 | 默认参数即可跑通；失败提示清晰 | 新手无需额外参数可执行一次闭环；报错可定位到配置项 | 新手执行录像/截图、错误提示示例 |
| 安全 | 回复内容合规；消息发送权限边界 | 不越权发送；敏感信息不外泄；审计日志可追踪 | 消息审计日志、权限配置截图 |
| 回滚 | `module stop` + `module recover` | recover 一次成功率 100%；回滚后可重新 start 并处理新会话 | recover 日志、回滚前后状态对比 |

**M1 Go/No-Go**  
- **Go**：功能主链路通过，60 分钟稳定运行通过，recover 验证通过。  
- **No-Go**：消息错发、会话处理中断不可恢复、或高频崩溃。

---

## M2 运营模块（operations）

| 维度 | 可执行检查项 | 通过阈值（Gate） | 证据要求 |
|---|---|---|---|
| 功能 | 默认任务初始化、擦亮/数据采集任务执行、任务状态查询 | 任务执行成功率 ≥ 98%；关键任务（polish/metrics）均至少成功 1 次 | 任务执行日志、成功/失败计数 |
| 稳定性 | 定时循环运行（≥ 2 个周期）+ 并发任务场景 | 连续周期无死锁/重复执行；任务延迟可控（偏差 ≤ 20%） | 调度日志、周期时间统计 |
| 易用性 | `--init-default-tasks` 新手可直接使用 | 新手首次运行不需手改配置文件；CLI 输出包含下一步建议 | 终端输出截图、文档步骤校验 |
| 安全 | 操作频控、平台合规参数检查 | 频控规则生效（不超配额）；违规参数被拒绝执行 | 合规模块日志、拒绝策略记录 |
| 回滚 | 跳过高风险任务/停止调度后恢复 | `--skip-polish`/`module stop` 可立即止损；恢复后任务可继续 | 止损操作记录、恢复验证日志 |

**M2 Go/No-Go**  
- **Go**：任务链路可稳定跑完周期，频控与止损可用。  
- **No-Go**：任务失控（重复执行/超频）、或无法快速停机止损。

---

## M3 售后模块（aftersales）

| 维度 | 可执行检查项 | 通过阈值（Gate） | 证据要求 |
|---|---|---|---|
| 功能 | 工单拉取、分类（delay/refund/quality）、回复策略与发送 | 三类 issue 均可处理；批处理成功率 ≥ 98% | 样例工单处理记录、分类统计 |
| 稳定性 | daemon 运行 + 空单/异常单/人工接管单场景 | 无崩溃；异常单被正确隔离；人工接管单不误处理 | 场景化测试日志、异常隔离证明 |
| 易用性 | 默认 `issue-type` 可改；`--include-manual` 行为可理解 | 参数语义清晰；新手可按帮助文档完成一次处理 | CLI help 截图、执行记录 |
| 安全 | 工单数据最小暴露；发送对象正确 | 不串单/不误发；敏感字段不出现在公共日志 | 发送日志抽检、脱敏日志片段 |
| 回滚 | 处理中断后可重启续跑且不重复发送 | 回滚后重复发送率 0；工单状态一致性通过 | 重启前后工单状态对比、幂等性日志 |

**M3 Go/No-Go**  
- **Go**：三类售后闭环通过、无串单误发、重启幂等通过。  
- **No-Go**：误发/串单、重复发送、状态错乱。

---

## 3. 统一通过阈值（发布总闸）

- 测试总门槛：
  - `pytest` 全绿（当前基线：663 passed）
  - 全量覆盖率 `TOTAL >= 35%`（当前基线远高于阈值）
  - 增量覆盖 `diff-cover >= 80%`
  - 代码质量：`ruff check` + `ruff format --check` 全通过
- 线上发布门槛：
  - 模块级五维 Gate 全通过
  - 无未闭环 P0/P1
  - 已完成灰度观察并满足止损阈值

> 任一条不满足，统一判定 **No-Go**。

---

## 4. 证据清单模板（每模块都必须提交）

1. **执行命令清单**（含时间、执行人、环境）
2. **结果摘要**（pass/fail、成功率、耗时、错误数）
3. **关键日志片段**（含模块名、会话/工单ID、trace）
4. **截图证据**（dashboard、CLI 输出、异常告警）
5. **回滚演练记录**（触发条件、执行步骤、恢复结果）
6. **结论单**（Go/No-Go + 风险说明 + 责任人签字）

---

## 5. 灰度流程（全本地/新手部署适配版）

### Phase 0：预检（必须通过）
- `module check --target all --strict`
- 质量门禁脚本：`STRICT=1 bash scripts/check_code_quality.sh`
- 未通过则禁止进入灰度。

### Phase 1：单模块灰度（低风险先行）
- 顺序：`operations -> presales -> aftersales`
- 每次仅放开 1 个模块，观察 30~60 分钟：
  - 错误率
  - 任务成功率
  - 资源波动
  - 误发/重复处理事件

### Phase 2：双模块联动灰度
- `operations + presales`，再 `presales + aftersales`
- 验证跨模块耦合（任务写入/读取、消息链路、调度互斥）

### Phase 3：全模块灰度
- `--target all` 连续运行 2 小时
- 达标后可转正式运行。

### 灰度止损阈值（任一触发即回滚）
- 连续 5 分钟错误率 > 2%
- 出现误发/串单 1 次及以上
- 模块崩溃 2 次及以上
- 关键任务积压超过 2 个调度周期

---

## 6. 回归流程（修复后强制执行）

1. **最小回归**：仅执行受影响模块 checklist（15~30 分钟）
2. **跨模块回归**：执行受影响上下游模块联测
3. **全量回归**（发布前）
   - `ruff check src/`
   - `ruff format --check src/`
   - `pytest tests/ --cov=src --cov-report=xml --cov-fail-under=35`
   - `diff_cover coverage.xml --compare-branch=origin/main --fail-under=80`
4. **回归通过后复核 Go/No-Go**，并更新证据包

---

## 7. 模块可执行测试清单（可直接复制执行）

> 建议均在项目根目录执行：`/Users/brianzhibo/Documents/New project/xianyu-openclaw`

### 7.1 通用门禁
```bash
python3 -m ruff check src/
python3 -m ruff format --check src/
python3 -m pytest tests/ -v --tb=short --cov=src --cov-report=xml --cov-fail-under=35
python3 -m diff_cover coverage.xml --compare-branch=origin/main --fail-under=80
```

### 7.2 M0 基础部署/新手路径
```bash
bash scripts/one_click_deploy.sh
python3 -m src.cli module --action check --target all --strict
python3 -m src.cli module --action status --target all --window-minutes 60
python3 -m src.cli module --action stop --target all
```

### 7.3 M1 售前模块
```bash
python3 -m src.cli module --action check --target presales --strict
python3 -m src.cli module --action start --target presales --mode daemon --limit 20 --interval 5
python3 -m src.cli module --action status --target presales --window-minutes 60
python3 -m src.cli module --action logs --target presales --tail-lines 80
python3 -m src.cli module --action recover --target presales --stop-timeout 6
```

### 7.4 M2 运营模块
```bash
python3 -m src.cli module --action check --target operations --strict
python3 -m src.cli module --action start --target operations --mode daemon --init-default-tasks --interval 30
python3 -m src.cli module --action status --target operations --window-minutes 60
python3 -m src.cli module --action logs --target operations --tail-lines 80
python3 -m src.cli module --action stop --target operations
```

### 7.5 M3 售后模块
```bash
python3 -m src.cli module --action check --target aftersales --strict
python3 -m src.cli module --action start --target aftersales --mode daemon --limit 20 --interval 15 --issue-type delay
python3 -m src.cli module --action status --target aftersales --window-minutes 60
python3 -m src.cli module --action logs --target aftersales --tail-lines 80
python3 -m src.cli module --action stop --target aftersales
```

---

## 8. 最终放行判定模板

- **模块判定**：
  - M0：Go / No-Go
  - M1：Go / No-Go
  - M2：Go / No-Go
  - M3：Go / No-Go
- **总判定**：
  - 所有模块均 Go 且总闸通过 => **Release Go**
  - 任一模块 No-Go 或总闸不通过 => **Release No-Go**
- **风险备注**：列出已知风险、缓解措施、责任人、复测时间。

---

## 9. 结论

本方案已满足验收标准：
- 按模块给出验证矩阵（功能/稳定性/易用性/安全/回滚）；
- 明确通过阈值与证据要求；
- 提供灰度与回归流程；
- 覆盖全本地运行 + 新手部署场景；
- 每个模块都含可执行测试清单与 Go/No-Go 标准。
