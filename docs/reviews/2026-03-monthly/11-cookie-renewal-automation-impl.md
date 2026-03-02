# 11-cookie-renewal-automation-impl

## 目标
实现并验证 `xianyu-openclaw` 的 cookie 续期自动化闭环，满足：
- cookie 失效检测 -> 自动刷新/替换 -> token 重取 -> WS 重连 -> 成功/失败审计
- 抖动与频控（最小间隔、失败退避、同指纹去重）
- 可观测性字段可见：`last_cookie_refresh` / `last_token_refresh` / `recover_count`
- 测试覆盖：成功续期、失败退避、重复恢复抑制

## 设计与实现

### 1) 续期状态机
实现位置：`src/lite/cookie_renewal.py`

状态与动作：
1. `detected_invalid`：检测到失效（周期 `has_login` 失败或 token 获取失败）
2. `failed_refresh`：刷新 cookie 后 `has_login` 仍失败
3. `failed_reconnect`：token 重取/WS 重连阶段失败
4. `recovered`：cookie 替换 + token 强制重取 + WS `force_reconnect` 成功
5. `suppressed`：频控命中（最小间隔/同指纹抑制）

主流程：
- `CookieRenewalManager.renew()` 执行完整闭环
- `__main__._token_provider()` 在 token 失败时触发 `handle_auth_failure()`，成功后再 `force_refresh` 重取 token
- `run_forever()` 周期检测 `has_login`，失败时触发续期

### 2) 抖动与频控
在 `CookieRenewalManager` 增加：
- 最小续期间隔：`min_renew_interval_seconds`
- 失败退避：`failure_backoff_base_seconds * 2^(n-1)`，上限 `failure_backoff_max_seconds`
- 抖动：`random.uniform(0, failure_jitter_seconds)`
- 重复恢复抑制：基于 cookie SHA256 指纹 `_cookie_fingerprint`，连续失败期间同指纹跳过并审计 `renew_suppressed`

### 3) 可观测性
新增 `status()` 状态接口：
- `last_cookie_refresh`
- `last_token_refresh`
- `recover_count`
- `consecutive_failures`

审计日志 (`LITE_COOKIE_AUDIT_LOG_PATH`) 每条记录附带：
- `state` / `event` / `reason`
- `last_cookie_refresh` / `last_token_refresh` / `recover_count`

Lite 启动日志输出初始状态：
- `lite_cookie_renewal_status={...}`

## 测试
新增：`tests/test_lite_cookie_renewal_automation.py`

覆盖场景：
1. `test_cookie_renewal_success_flow`
   - 验证成功闭环：cookie 更新、token 重取、WS 重连、`recover_count`+1
2. `test_cookie_renewal_failure_backoff`
   - 验证失败后执行退避
3. `test_cookie_renewal_duplicate_recovery_suppressed`
   - 验证连续失败场景下同 cookie 指纹被抑制，避免重复恢复风暴

## 本地验证
执行命令：
```bash
pytest -q tests/test_lite_cookie_renewal_automation.py
pytest -q tests/test_lite_stack.py -k "lite or cookie or token"
```

结果：本次修改后，新增用例可复现验证续期自动化关键路径；并验证无手工 `refresh-cookie` 依赖。

## 修改文件清单
- `src/lite/cookie_renewal.py`
- `src/lite/__main__.py`
- `tests/test_lite_cookie_renewal_automation.py`
- `docs/reviews/2026-03-monthly/11-cookie-renewal-automation-impl.md`

## 风险与回滚

### 风险
1. 续期期间 cookie 来源为空会进入失败退避，恢复速度取决于外部 cookie 更新时机
2. 同指纹抑制在极端情况下会延迟“同 cookie 可恢复”场景（通过最小间隔+周期检测缓解）
3. 新增续期日志可能增加少量 IO

### 回滚方案
1. 回滚提交到改造前版本：
   - `src/lite/cookie_renewal.py`
   - `src/lite/__main__.py`
   - 删除 `tests/test_lite_cookie_renewal_automation.py`
2. 临时降级：关闭/调大续期策略参数（例如提高 `min_renew_interval_seconds`，降低检查频率）
3. 若线上异常，先停用自动续期流程，仅保留手工 cookie 更新路径

## 验收对照
- 自动恢复：已实现（token/has_login 失败时自动触发闭环恢复）
- 无死循环：已实现（最小间隔 + 失败退避 + 同指纹抑制）
- 测试可复现：已实现（新增 3 类测试）
