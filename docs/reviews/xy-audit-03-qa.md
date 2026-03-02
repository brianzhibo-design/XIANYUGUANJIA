# XY-AUDIT-03 QA与发布可用性审查报告

- **任务编号**: XY-AUDIT-03  
- **审查角色**: QA与发布可用性审查  
- **审查方式**: 只读审查（未修改业务代码）  
- **审查时间**: 2026-03-02 (GMT+8)

## 一、发布结论

## **Not Ready**

当前自动化测试总体通过率高、关键模块覆盖率高，但存在**发布门禁级缺口**：
1) 覆盖率口径在仓库内存在多个互相冲突的“最终值”；
2) 与“售前自动化链路”相关的端到端证据不足（现有以单元/组件/模拟为主，缺少真实链路闭环证据）。

---

## 二、必查项审查结果

## 1) 测试覆盖率口径是否一致（总覆盖、关键模块覆盖、xpass/warnings）

### 结论：**不一致（阻塞）**

### 证据
- `qa_report.txt` 显示：
  - `663 passed`
  - `XPASS=0, XFAIL=0`
  - warning 1 条（`configfile: pytest.ini (WARNING: ignoring pytest config in pyproject.toml!)`）
  - 总覆盖率：`98.91%`（`coverage_qa_check.json`）
- `coverage_qa_check.json`：`98.9101%`（11744 statements, 11616 covered）
- 但仓库中同时存在多个“final”覆盖率文件，口径冲突明显：
  - `coverage_final_0302.json` = `99.2933%`
  - `coverage_final2_0302.json` = `99.8212%`
  - `coverage_after_030b.json` = `14.6117%`（显著异常）

### 影响
- 当前“发布覆盖率”不可唯一复现，存在“取哪个文件算门禁”的治理风险。

---

## 2) 售前自动化链路是否有端到端验证证据

### 结论：**证据不足（阻塞）**

### 已有证据（偏组件级/集成级）
- 自动化配置：`tests/test_automation_setup.py`
- 工作流状态机与worker：`tests/test_workflow.py`
- WebSocket消息适配：`tests/test_messages_ws_live.py`, `tests/test_messages_ws_live_more.py`
- dashboard恢复/诊断逻辑：`tests/test_dashboard_server.py`
- CLI模块流程：`tests/test_cli_module.py`, `tests/test_cli_more.py`, `tests/test_cli_targeted_round*.py`

### 缺口
- 未看到“真实售前链路”闭环测试证据（例如：真实配置/真实运行进程/真实消息输入到报价回复产出、并验证状态与日志联动）。
- 现有大量测试使用 Dummy/Stub/monkeypatch，能保证分层逻辑，但不足以替代发布前E2E门禁。

---

## 3) dashboard 与 CLI 关键路径是否有回归测试保护

### 结论：**有，且覆盖较强（非阻塞）**

### 证据
- 覆盖率（`coverage_qa_check.json`）：
  - `src/cli.py`：`100%`（987/987）
  - `src/dashboard_server.py`：`99%`（1969/1997）
- 回归测试数量（按文件统计）
  - CLI相关：
    - `tests/test_cli_module.py` (11)
    - `tests/test_cli_more.py` (5)
    - `tests/test_cli_targeted_round5_part1.py` (5)
    - `tests/test_cli_targeted_round9_part1.py` (5)
  - Dashboard相关：
    - `tests/test_dashboard_server.py` (49)
    - `tests/test_targeted_round10_dashboard_server_handler.py` (5)
    - `tests/test_targeted_round9_part2_dashboard_server.py` (10)

### 观察
- 关键路径（module check/start/stop/recover、cookie导入诊断、risk status、service status）均有回归保护。

---

## 4) 失败场景（cookie空、cookie未更新、认证失败、ws断连）是否有测试

### 结论：**有覆盖（非阻塞）**

### 对照证据
- **cookie空**
  - `tests/test_messages_ws_live_more.py::test_cookie_apply_raises_without_unb`
  - `tests/test_targeted_xy_cov_020a.py::test_apply_cookie_text_rejects_empty_cookie`
  - `tests/test_targeted_xy_cov_029a.py` 中空cookie/解析失败分支
- **cookie未更新/需更新**
  - `tests/test_dashboard_server.py::test_service_status_marks_degraded_on_auth_failure`（`cookie_update_required`）
  - `tests/test_dashboard_server.py::test_service_status_auto_recover_on_cookie_change_after_validate_error`
  - `tests/test_messages_ws_live.py::test_ws_transport_auth_hold_until_cookie_update_enabled_by_default`
- **认证失败**
  - `tests/test_messages_ws_live.py::test_ws_transport_auth_error_marker`
  - `tests/test_dashboard_server.py::test_service_status_marks_degraded_on_auth_failure`
  - 多处 `FAIL_SYS_USER_VALIDATE` 分支测试（dashboard / targeted coverage）
- **ws断连**
  - `tests/test_dashboard_server.py::test_risk_control_status_detects_warning_signal`
  - `tests/test_dashboard_server.py::test_risk_control_status_recovers_when_connected_after_failures`
  - `tests/test_messages_ws_live*.py` 中重连/等待cookie更新/认证回退逻辑

---

## 三、发布阻塞项（Blocking）

1. **覆盖率口径不唯一**  
   发布证据存在多份互相冲突的 coverage JSON（含异常低值），无法形成单一、可审计的发布门禁口径。

2. **售前自动化E2E证据不足**  
   当前以分层测试为主，缺少“售前链路真实闭环”发布前证据，无法充分评估上线后集成回归风险。

---

## 四、非阻塞项（Non-blocking）

1. `pytest.ini` 与 `pyproject.toml` pytest 配置并存，触发 warning（短期不影响通过，但建议治理）。
2. dashboard/CLI 已有高覆盖与大量回归测试，结构上风险可控。

---

## 五、最小补测方案（半天内可完成）

> 目标：在不大改框架的前提下补齐发布门禁证据。

1. **统一覆盖率门禁口径（约0.5h）**
   - 固化唯一命令：
     - `.venv/bin/python -m pytest --tb=short -q --cov=src --cov-report=json:coverage_release_gate.json`
   - 发布仅认 `coverage_release_gate.json` + 当次 `qa_report.txt`。
   - 清理/归档历史临时 coverage 文件，避免误用。

2. **补1条售前自动化最小E2E（约2h）**
   - 建议新增 `tests/e2e/test_presales_minimal_e2e.py`（或等价命名）
   - 最小闭环：
     1) 注入可用cookie配置；
     2) 启动 presales workflow 一次运行；
     3) 输入一条报价类会话消息；
     4) 断言：产生回复结果 + workflow状态推进 + SLA统计更新 + dashboard/模块状态可读。
   - 允许使用本地测试替身服务，但需覆盖“跨模块真实调用链”而非纯函数mock。

3. **补1条认证失败恢复E2E（约1.5h）**
   - 场景：`FAIL_SYS_USER_VALIDATE` -> 标记 `cookie_update_required` -> 更新cookie -> recover -> 状态恢复。
   - 断言恢复前后 service_status/risk_control 变化完整可见。

4. **补1条 ws断连恢复E2E（约1h）**
   - 场景：ws断连日志信号 -> warning/degraded -> connected 事件后恢复 normal。
   - 断言 dashboard 风险等级和连接状态切换。

> 补测完成后，若全绿并产出单一门禁报告，可将发布结论提升为 **Conditionally Ready/Ready**。

---

## 六、审查摘要

- **优点**：全量 663 用例通过，CLI/dashboard覆盖率与回归深度较好，关键失败场景已有较多分层测试。  
- **主要风险**：发布证据口径不统一 + 售前链路缺少端到端闭环验证。  
- **当前建议**：先补齐上述两类阻塞项，再执行发布。
