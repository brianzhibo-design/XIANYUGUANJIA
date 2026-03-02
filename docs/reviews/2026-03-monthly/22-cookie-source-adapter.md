# 22 - Cookie Source Adapter（自动获取新 Cookie）

## 背景
现有 `cookie_renewal` 依赖 `cookie_loader`（文件/env）与可选浏览器 provider。为了实现“优先从本地已登录浏览器会话自动获取 goofish cookie，失败降级到文件/env”，新增统一的 cookie source adapter。

## 变更概览

### 1) 新增统一 Adapter
文件：`src/lite/cookie_source_adapter.py`

- `CookieSnapshot`
  - `cookie_text`
  - `fingerprint`
  - `updated_at`
  - `source`
- `BrowserSessionCookieSource`
  - 从本地浏览器会话读取 cookie（`create_browser_client(...).get_cookies()`）
  - 仅拼装 `goofish/taobao/xianyu` 域相关 cookie
- `FileEnvCookieSource`
  - 兜底读取：`cookie_file` -> `LITE_COOKIE/XIANYU_COOKIE_1` -> inline
- `CookieSourceAdapter`
  - 统一接口：`get_latest_cookie()`
  - 策略：浏览器优先，失败/空结果自动降级到 file/env

### 2) 对 cookie_renewal 输出统一接口消费
文件：`src/lite/cookie_renewal.py`

- 构造参数新增：`cookie_source_adapter`
- 新增 `_get_latest_cookie_snapshot(reason)`：
  - 优先调用 `cookie_source_adapter.get_latest_cookie()`
  - 成功时记录审计、持久化 cookie
  - 异常时记录失败审计
  - 为兼容旧逻辑，回退至既有 `browser_cookie_provider`
- 在 `run_forever()` 周期探测、`renew()` 触发续期路径均改为先走统一 adapter。

> 兼容性：未传入 `cookie_source_adapter` 时，仍按旧路径工作，不破坏现有链路。

### 3) 主流程接入
文件：`src/lite/__main__.py`

- 组装 `CookieSourceAdapter(browser_source=BrowserSessionCookieSource(), fallback_source=FileEnvCookieSource(...))`
- 传入 `CookieRenewalManager(cookie_source_adapter=...)`
- 移除入口中散落的浏览器 cookie 解析函数，避免逻辑重复。

## 最小验证

### 测试新增
- `tests/test_lite_cookie_source_adapter.py`
  - `test_cookie_source_adapter_prefers_browser_snapshot`
  - `test_cookie_source_adapter_fallback_when_browser_empty`
- `tests/test_lite_cookie_renewal.py`
  - `test_cookie_renewal_uses_cookie_source_adapter`

## 验收对应
- ✅ 可被主流程调用：`__main__` 已接线
- ✅ 浏览器优先：adapter 首选 browser source
- ✅ 失败可降级：自动 fallback file/env
- ✅ 统一接口：`get_latest_cookie` + `fingerprint` + `updated_at`
