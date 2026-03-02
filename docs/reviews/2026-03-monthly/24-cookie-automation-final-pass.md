# 24-cookie-automation-final-pass

- Task: XY-COOKIE-20260302-I
- Dispatcher: 蛋蛋(main)
- Date: 2026-03-02
- Scope: 自动获取新cookie并热更新，修复 WS 重连从 FAIL_SYS_USER_VALIDATE 恢复到 Connected

## Final Verdict

**CONDITIONAL PASS**

说明：主链路已实现并通过新增/调整测试，具备自动抓取、校验、原子替换、持久化、回滚与退避能力；但“并行任务 N（cookie source adapter）/O（回归矩阵）产物”尚未在本分支看到独立交付物，当前为主分支内置实现，故给出 CONDITIONAL PASS。

## Implemented Hardening

### 1) 风控失败分支策略（FAIL_SYS_USER_VALIDATE）

位置：`src/lite/cookie_renewal.py`

- 新增分类：`_classify_failure()`
  - `FAIL_SYS_USER_VALIDATE + cookie invalid signals` -> `cookie_invalid`
  - `FAIL_SYS_USER_VALIDATE` -> `transient_risk`
- 新增状态：
  - `recoverable_backoff`（可自动恢复）
  - `waiting_new_cookie`（需要新 cookie）
- 新增重试控制：
  - 指数退避：`failure_backoff_*`
  - 风控预算：`risk_retry_budget`
  - 冷却窗口：`risk_cooldown_seconds`
- 新增可观测字段：
  - `risk_fail_count`
  - `last_risk_code`
  - `next_retry_at`

### 2) cookie 源可用性检查 + 主动抓取（触发式+周期式）

位置：
- `src/lite/cookie_renewal.py`
- `src/lite/__main__.py`

实现：
- 周期式：`run_forever()` 每轮执行 `_try_auto_refresh_cookie_source(reason="periodic_browser_cookie_probe")`
- 触发式：`renew()` 失败恢复前执行 `_try_auto_refresh_cookie_source(reason="triggered_browser_cookie_probe:...")`
- 浏览器抓取实现：`_browser_cookie_provider()`
  - 通过 `create_browser_client(runtime=auto)` 获取已登录浏览器 cookies
  - 过滤 goofish/taobao/xianyu 相关域
  - 组装 header cookie 字符串

### 3) 校验后替换 + 原子更新 + 重连

位置：`src/lite/cookie_renewal.py`

- 先校验：`_validate_candidate_cookie()`
  - 暂时注入候选 cookie
  - `has_login` + `get_token(force_refresh=True)` 成功才通过
- 再提交：`_apply_cookie_atomically()`
  - 同步更新 `api_client` 与 `ws_client` auth context
  - 执行 `force_reconnect("cookie_renewed")`

### 4) 持久化到 LITE_COOKIE_FILE

位置：`src/lite/cookie_renewal.py`

- 新增 `cookie_file_path` 参数
- `_persist_cookie()` 将最新可用 cookie 写入文件
- 周期/触发抓取到 cookie 后立即持久化；恢复成功后也持久化

### 5) 失败回滚 + 退避

位置：`src/lite/cookie_renewal.py`

- 新增 `_rollback_cookie_context()`：恢复 api/ws 旧上下文
- 恢复失败后按分类进入：
  - `recoverable_backoff`
  - `waiting_new_cookie`
  - `failed_reconnect`
- 所有失败路径都会计算并暴露 `next_retry_at`，避免重连风暴

## Tests Added/Updated

文件：`tests/test_lite_cookie_renewal_automation.py`

新增/增强覆盖：
1. `test_risk_branch_backoff_and_budget_to_waiting_cookie`
   - 验证 FAIL_SYS_USER_VALIDATE 风控分支：先退避，再预算耗尽进入等待状态
2. `test_empty_cookie_source_enters_waiting_state_not_loop`
   - 验证 cookie 未更新时进入 waiting_new_cookie，而非死循环重连
3. `test_auto_fetch_cookie_and_persist_file`
   - 验证自动抓取 cookie + 持久化 + 热更新重连
4. 原有用例同步调整为 waiting 状态语义（替代旧 suppress 断言）

## Verification Evidence

执行命令：

```bash
./.venv/bin/python -m pytest -q --no-cov tests/test_lite_cookie_renewal.py tests/test_lite_cookie_renewal_automation.py
```

结果：

- `10 passed in 2.37s`

## Operational Observability

通过 `cookie_renewal.status()` 与审计日志 `LITE_COOKIE_AUDIT_LOG_PATH` 可区分：

- 卡在等待新 cookie：`state=waiting_new_cookie`
- 仍可自动恢复：`state=recoverable_backoff`
- 风控累计与下次重试：`risk_fail_count/last_risk_code/next_retry_at`

## Integration Notes for Parallel Tasks N/O

- N（cookie source adapter）需求已在主链路内置 `_browser_cookie_provider` + `_try_auto_refresh_cookie_source` 对接点；若 N 产物有独立适配器模块，可直接替换 `browser_cookie_provider` 注入实现。
- O（回归矩阵）可直接纳入本次新增 3 条核心场景用例，建议在 CI 增加以下矩阵项：
  - transient risk 连续失败预算耗尽
  - empty/same-cookie source
  - auto-fetch + persist + reconnect + rollback

