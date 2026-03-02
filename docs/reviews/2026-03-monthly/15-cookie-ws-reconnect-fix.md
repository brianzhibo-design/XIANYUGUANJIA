# 15-cookie-ws-reconnect-fix

## 背景
问题现象：Cookie 续期成功后，Lite WS 仍持续 auth fail，无法回到 `Connected`。

## 复现路径（失败链路）
1. WS 连接断开/鉴权失败，触发 `CookieRenewalManager.renew()`。
2. `renew()` 中先 `api_client.update_cookie(new_cookie)`，会重置并重建：
   - `api_client.device_id`
   - `api_client.user_id`
   - token 缓存（`_token`）
3. 随后仅调用了 `ws_client.update_cookie(new_cookie)`，**没有同步 WS 鉴权上下文中的 `device_id/my_user_id`**。
4. 之后 `api_client.get_token(force_refresh=True)` 生成的新 token 绑定新 cookie + 新 device_id；
5. 但 WS 首帧 `/reg` 仍携带旧 `did`（`LiteWsClient.device_id`），造成 token 与 did 不一致，服务端拒绝，进入重连后重复失败。

## 根因定位
根因是 **token 来源与 WS 首帧鉴权参数在 cookie 恢复后的上下文不一致**：
- token 来源：`XianyuApiClient`（已更新 cookie/device_id）
- WS 首帧鉴权：`LiteWsClient._register()`（仍旧 device_id）

这属于 cookie 同步时序后的状态不一致，不是续期状态机本身逻辑错误。

## 修复方案（最小改造）
目标：不改续期流程主干，只补齐 WS 侧鉴权上下文同步。

### 代码改动
1. `src/lite/ws_client.py`
   - 新增 `update_auth_context(cookie, device_id, my_user_id)`：原子更新 WS 鉴权上下文。
2. `src/lite/cookie_renewal.py`
   - 在 `api_client.update_cookie(cookie_text)` 后，优先调用 `ws_client.update_auth_context(...)` 同步：
     - `cookie`
     - `device_id`（来自 `api_client.device_id`）
     - `my_user_id`（来自 `api_client.user_id`）
   - 向后兼容：若 ws client 未实现新方法，回退到原 `update_cookie()`。

### 为什么是最小改造
- 未改 token 刷新策略。
- 未改重连退避/周期检查逻辑。
- 未改 WS 主循环状态机分支，仅补齐恢复时的认证上下文一致性。

## 回归测试
新增测试：
- `tests/test_lite_cookie_renewal.py::test_cookie_renewal_updates_ws_auth_context_for_reconnect`

覆盖点：
- 续期后 WS 不仅 cookie 更新，`device_id/my_user_id` 也随 API 侧更新。
- 触发一次 `force_reconnect()`，验证恢复闭环关键步骤。

## 本地验证
### 1) 新增回归用例（精准）
```bash
.venv/bin/pytest -q -o addopts='' tests/test_lite_cookie_renewal.py::test_cookie_renewal_updates_ws_auth_context_for_reconnect
```
结果：`1 passed`

### 2) Lite 相关测试子集
```bash
.venv/bin/pytest -q -o addopts='' tests/test_lite_cookie_renewal.py tests/test_lite_stack.py
```
结果：`17 passed`

> 说明：仓库 `pytest.ini` 含全局 coverage fail-under，执行子集时使用 `-o addopts=''` 关闭默认附加参数，确保可复现该问题修复验证。

## 验收对照
- [x] 失效 -> 恢复后可回到 Connected（通过修复 token/did 上下文不一致，打通重连鉴权闭环）
- [x] 无重连死循环（续期后重连使用一致鉴权参数，不再因 did/token 不匹配重复 auth fail）
- [x] 测试可复现（新增回归 + Lite 子集均通过）
