"""运行环境与配置诊断。"""

from __future__ import annotations

import json
import os
import socket
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from src.core.config import get_config
from src.core.startup_checks import resolve_runtime_mode, run_all_checks
from src.modules.quote import CostTableRepository

_SUGGESTIONS = {
    "浏览器运行时": "可通过 `.env` 设置 `APP_RUNTIME=auto|lite|pro`，推荐先用 `auto`。",
    "Python版本": "请安装 Python 3.10+，并使用 `python3 -m venv .venv` 创建虚拟环境。",
    "Legacy Browser Gateway": "如需启用 legacy browser gateway，请先执行 `docker compose up -d`，再重试 doctor。",
    "Lite 浏览器驱动": "请执行 `pip install playwright`，然后执行 `playwright install chromium`。",
    "数据库": "请确认数据库目录可写，并检查 `config/config.yaml` 中 database.path 配置。",
    "闲鱼Cookie": "请在 `.env` 中设置有效的 `XIANYU_COOKIE_1`。",
    "Cookie有效性": "请重新抓取并更新闲鱼 Cookie，避免使用过期会话。",
    "Cookie在线有效性": "Cookie 已过期，请重新从浏览器获取并更新 `.env` 中的 `XIANYU_COOKIE_1`。",
    "AI服务": "可配置 `DEEPSEEK_API_KEY` 或 `OPENAI_API_KEY`，未配置将退化到模板模式。",
    ".env 文件": "请复制 `.env.example` 为 `.env`，并补齐关键配置。",
    "配置文件": "请确保 `config/config.yaml` 存在，或从 `config/config.example.yaml` 复制生成。",
    "Dashboard守护状态": "请使用 `python3 -m src.dashboard_server --port 8091` 或对应 bat 脚本启动面板服务。",
    "消息首响SLA": "建议开启 `messages.fast_reply_enabled=true` 且 `reply_target_seconds<=3`。",
    "自动报价成本源": "请提供成本表（data/quote_costs）或配置 `quote.cost_api_url`。",
    "报价Mock门禁": "请在配置中设置 `quote.providers.remote.allow_mock=false`，并确认生产环境未通过环境变量覆盖为 true。",
    "BitBrowser 指纹浏览器": (
        "请从 https://www.bitbrowser.net 下载安装 BitBrowser，启动后"
        "在管理面板 → 系统配置 → 滑块验证 中配置 API 地址和 browser_id。"
    ),
    "CookieCloud 自动同步": (
        "服务端已内置无需额外部署。请安装 Chrome/Edge CookieCloud 扩展，"
        "然后在管理面板 → 系统配置 → CookieCloud 中填入 UUID 和密码。"
    ),
    "Dashboard 配置完整性": (
        "请在管理面板中完成首次配置（AI、CookieCloud、自动回复），"
        "或从旧设备导入 data/system_config.json。"
    ),
}


def _check_port_open(port: int, host: str = "127.0.0.1", timeout: float = 0.3) -> bool:
    if port <= 0:
        return False
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(timeout)
            return sock.connect_ex((host, port)) == 0
    except OSError:
        return False


def _append_check(
    checks: list[dict[str, Any]],
    *,
    name: str,
    passed: bool,
    message: str,
    critical: bool,
    suggestion: str | None = None,
    meta: dict[str, Any] | None = None,
) -> None:
    resolved_suggestion = ""
    if not passed:
        resolved_suggestion = suggestion or _SUGGESTIONS.get(name, "")

    checks.append(
        {
            "name": name,
            "passed": bool(passed),
            "critical": bool(critical),
            "message": message,
            "suggestion": resolved_suggestion,
            "meta": meta or {},
        }
    )


def _extra_checks(skip_quote: bool = False) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    runtime = resolve_runtime_mode()

    env_exists = Path(".env").exists()
    _append_check(
        checks,
        name=".env 文件",
        passed=env_exists,
        message="已检测到 .env" if env_exists else "未检测到 .env",
        critical=False,
    )

    cfg_candidates = [Path("config/config.yaml"), Path("config/config.example.yaml")]
    cfg_path = next((path for path in cfg_candidates if path.exists()), None)
    _append_check(
        checks,
        name="配置文件",
        passed=cfg_path is not None,
        message=f"已使用配置: {cfg_path}" if cfg_path else "未找到 config/config.yaml 或 config/config.example.yaml",
        critical=True,
    )

    web_port = int(os.getenv("FRONTEND_PORT") or os.getenv("OPENCLAW_WEB_PORT", "5173"))
    if runtime == "lite":
        _append_check(
            checks,
            name="Web UI 端口",
            passed=True,
            message=f"lite 模式默认跳过 127.0.0.1:{web_port} 检查",
            critical=False,
            meta={"port": web_port, "skipped": True, "runtime": runtime},
        )
    else:
        web_listening = _check_port_open(web_port)
        _append_check(
            checks,
            name="Web UI 端口",
            passed=web_listening,
            message=f"检测到监听 127.0.0.1:{web_port}" if web_listening else f"未检测到监听 127.0.0.1:{web_port}",
            critical=False,
            suggestion="如需启动前端工作台，请执行 `./start.sh` 或 `docker compose up -d`。",
            meta={"port": web_port},
        )

    dashboard_port = int(os.getenv("DASHBOARD_PORT", "8091"))
    dashboard_listening = _check_port_open(dashboard_port)
    _append_check(
        checks,
        name="Dashboard 端口",
        passed=dashboard_listening,
        message=(
            f"检测到监听 127.0.0.1:{dashboard_port}"
            if dashboard_listening
            else f"未检测到监听 127.0.0.1:{dashboard_port}"
        ),
        critical=False,
        suggestion="如需可视化后台，请执行 `python3 -m src.dashboard_server --port 8091`。",
        meta={"port": dashboard_port},
    )

    dashboard_api_ok = False
    dashboard_api_msg = "Dashboard API 未检测"
    if dashboard_listening:
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{dashboard_port}/api/status", timeout=8.0) as resp:
                raw = resp.read().decode("utf-8", errors="ignore")
                payload = json.loads(raw)
                if isinstance(payload, dict) and "service_status" in payload:
                    dashboard_api_ok = True
                    dashboard_api_msg = "Dashboard API 正常"
                else:
                    dashboard_api_msg = "Dashboard API 响应缺少 service_status"
        except urllib.error.URLError as exc:
            dashboard_api_msg = f"Dashboard API 不可用: {exc.reason}"
        except Exception as exc:
            dashboard_api_msg = f"Dashboard API 检查失败: {exc}"
    else:
        dashboard_api_msg = "Dashboard 端口未监听，跳过 API 连通性检查"

    _append_check(
        checks,
        name="Dashboard守护状态",
        passed=dashboard_api_ok,
        message=dashboard_api_msg,
        critical=False,
        meta={"port": dashboard_port, "port_listening": dashboard_listening},
    )

    try:
        config = get_config()
        messages_cfg = config.get_section("messages", {})
        fast_reply_enabled = bool(messages_cfg.get("fast_reply_enabled", False))
        reply_target_seconds = float(messages_cfg.get("reply_target_seconds", 3.0))
        sla_ok = fast_reply_enabled and reply_target_seconds <= 3.0
        _append_check(
            checks,
            name="消息首响SLA",
            passed=sla_ok,
            message=(
                f"已启用快速首响，目标 {reply_target_seconds:.2f}s"
                if sla_ok
                else f"未满足首响目标：fast_reply_enabled={fast_reply_enabled}, target={reply_target_seconds:.2f}s"
            ),
            critical=False,
            meta={
                "fast_reply_enabled": fast_reply_enabled,
                "reply_target_seconds": reply_target_seconds,
            },
        )
    except Exception as exc:
        _append_check(
            checks,
            name="消息首响SLA",
            passed=False,
            message=f"检查失败: {exc}",
            critical=False,
        )

    # BitBrowser 指纹浏览器检测
    try:
        config = get_config()
        ws_cfg = config.get_section("messages", {}).get("ws", {})
        slider_cfg = ws_cfg.get("slider_auto_solve", {}) if isinstance(ws_cfg, dict) else {}
        fp_cfg = slider_cfg.get("fingerprint_browser", {}) if isinstance(slider_cfg, dict) else {}
        fp_enabled = bool(fp_cfg.get("enabled", False)) if isinstance(fp_cfg, dict) else False

        if not fp_enabled:
            _append_check(
                checks,
                name="BitBrowser 指纹浏览器",
                passed=True,
                message="未启用（可选功能，用于降低风控检测概率）",
                critical=False,
            )
        else:
            api_url = str(fp_cfg.get("api_url", "http://127.0.0.1:54345"))
            try:
                port = int(api_url.rstrip("/").split(":")[-1])
            except (ValueError, IndexError):
                port = 54345
            port_open = _check_port_open(port)
            browser_id = str(fp_cfg.get("browser_id", "")).strip()
            _append_check(
                checks,
                name="BitBrowser 指纹浏览器",
                passed=port_open and bool(browser_id),
                message=(
                    f"API {'可达' if port_open else '不可达'} (:{port}), "
                    f"browser_id={'已配置' if browser_id else '未配置'}"
                ),
                critical=False,
                meta={"port": port, "port_open": port_open, "browser_id_set": bool(browser_id)},
            )
    except Exception as exc:
        _append_check(
            checks,
            name="BitBrowser 指纹浏览器",
            passed=True,
            message=f"检查跳过: {exc}",
            critical=False,
        )

    # CookieCloud 自动同步配置检测
    cc_uuid = os.getenv("COOKIE_CLOUD_UUID", "").strip()
    cc_pwd = os.getenv("COOKIE_CLOUD_PASSWORD", "").strip()
    if not cc_uuid or not cc_pwd:
        try:
            cfg_path = Path("data/system_config.json")
            if cfg_path.exists():
                sys_cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
                cc = sys_cfg.get("cookie_cloud", {}) if isinstance(sys_cfg.get("cookie_cloud"), dict) else {}
                cc_uuid = cc_uuid or str(cc.get("cookie_cloud_uuid", "")).strip()
                cc_pwd = cc_pwd or str(cc.get("cookie_cloud_password", "")).strip()
        except Exception:
            pass
    cc_configured = bool(cc_uuid and cc_pwd)
    cc_decryptable = False
    cc_decrypt_msg = ""
    if cc_configured:
        import hashlib
        cc_host = os.getenv("COOKIE_CLOUD_HOST", "").strip()
        if not cc_host:
            try:
                cfg_path = Path("data/system_config.json")
                if cfg_path.exists():
                    _sc = json.loads(cfg_path.read_text(encoding="utf-8"))
                    _cc = _sc.get("cookie_cloud", {}) if isinstance(_sc.get("cookie_cloud"), dict) else {}
                    cc_host = str(_cc.get("cookie_cloud_host", "")).strip()
            except Exception:
                pass
        if not cc_host:
            cc_host = "http://localhost:8091/cookie-cloud"
        try:
            import urllib.request
            url = f"{cc_host.rstrip('/')}/get/{cc_uuid}"
            req = urllib.request.Request(
                url,
                data=json.dumps({"password": cc_pwd}).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=5.0) as resp:
                body = json.loads(resp.read().decode("utf-8", errors="ignore"))
            encrypted = body.get("encrypted")
            if encrypted:
                from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
                from cryptography.hazmat.primitives import padding as sym_padding
                import base64
                key_raw = f"{cc_uuid}-{cc_pwd}"
                key_hash = hashlib.md5(key_raw.encode("utf-8")).hexdigest()[:16]
                raw_bytes = base64.b64decode(encrypted)
                iv, ct = raw_bytes[:16], raw_bytes[16:]
                cipher = Cipher(algorithms.AES(key_hash.encode()), modes.CBC(iv))
                decryptor = cipher.decryptor()
                padded = decryptor.update(ct) + decryptor.finalize()
                unpadder = sym_padding.PKCS7(128).unpadder()
                unpadder.update(padded) + unpadder.finalize()
                cc_decryptable = True
                cc_decrypt_msg = "已配置，密码验证通过"
            elif body.get("cookie_data"):
                cc_decryptable = True
                cc_decrypt_msg = "已配置，数据可读取（未加密）"
            else:
                cc_decrypt_msg = "已配置，但服务返回空数据"
        except Exception as exc:
            exc_str = str(exc)
            if "padding" in exc_str.lower() or "decrypt" in exc_str.lower():
                cc_decrypt_msg = "已配置，但密码不匹配（Invalid padding）"
            else:
                cc_decrypt_msg = f"已配置，但连接失败: {exc_str[:80]}"

    _append_check(
        checks,
        name="CookieCloud 自动同步",
        passed=cc_configured,
        message=cc_decrypt_msg if cc_configured else "未配置（推荐配置以实现 Cookie 自动同步恢复）",
        critical=False,
        suggestion=(
            "密码不匹配，请在管理面板 → 系统配置 → CookieCloud 中重新配置，"
            "确保密码与浏览器插件中的一致。"
        ) if (cc_configured and not cc_decryptable and "密码" in cc_decrypt_msg) else None,
    )

    # system_config.json 完整性检测
    _IMPORTANT_SECTIONS = {"ai", "cookie_cloud", "auto_reply"}
    sys_cfg_path = Path("data/system_config.json")
    sys_cfg_exists = sys_cfg_path.exists()
    sys_cfg_sections_present: set[str] = set()
    if sys_cfg_exists:
        try:
            _sys = json.loads(sys_cfg_path.read_text(encoding="utf-8"))
            if isinstance(_sys, dict):
                sys_cfg_sections_present = _IMPORTANT_SECTIONS & set(_sys.keys())
        except Exception:
            pass

    sys_cfg_ok = sys_cfg_exists and sys_cfg_sections_present == _IMPORTANT_SECTIONS
    missing_sections = _IMPORTANT_SECTIONS - sys_cfg_sections_present
    if not sys_cfg_exists:
        sys_cfg_message = "data/system_config.json 不存在，Dashboard 配置尚未初始化"
    elif missing_sections:
        sys_cfg_message = f"缺少配置段: {', '.join(sorted(missing_sections))}"
    else:
        sys_cfg_message = f"已配置 {len(sys_cfg_sections_present)} 个关键段"
    _append_check(
        checks,
        name="Dashboard 配置完整性",
        passed=sys_cfg_ok,
        message=sys_cfg_message,
        critical=False,
        suggestion="请在管理面板中完成首次配置（AI、CookieCloud、自动回复），或从旧设备导入 data/system_config.json。",
    )

    if skip_quote:
        return checks

    # Cookie 在线有效性探测（仅当 Cookie 已配置时执行）
    cookie_val = os.getenv("XIANYU_COOKIE_1", "")
    if cookie_val and cookie_val != "your_cookie_here" and len(cookie_val) > 20:
        try:
            from src.core.cookie_health import CookieHealthChecker

            checker = CookieHealthChecker(cookie_text=cookie_val, timeout_seconds=8.0)
            result = checker.check_sync(force=True)
            _append_check(
                checks,
                name="Cookie在线有效性",
                passed=bool(result.get("healthy", False)),
                message=str(result.get("message", "未知")),
                critical=False,
                meta=result,
            )
        except Exception as exc:
            _append_check(
                checks,
                name="Cookie在线有效性",
                passed=False,
                message=f"探测失败: {exc}",
                critical=False,
            )

    try:
        config = get_config()
        quote_cfg = config.get_section("quote", {})
        mode = str(quote_cfg.get("mode", "rule_only")).strip().lower()
        repo = CostTableRepository(
            table_dir=quote_cfg.get("cost_table_dir", "data/quote_costs"),
            include_patterns=quote_cfg.get("cost_table_patterns", ["*.xlsx", "*.csv"]),
        )
        stats = repo.get_stats(max_files=30)
        total_records = int(stats.get("total_records", 0))
        api_ready = bool(str(quote_cfg.get("cost_api_url", "")).strip())
        needs_cost_source = mode in {"cost_table_plus_markup", "api_cost_plus_markup"}
        source_ready = total_records > 0 or api_ready
        passed = (not needs_cost_source) or source_ready
        message = (
            f"mode={mode}, records={total_records}, api_ready={api_ready}"
            if passed
            else f"mode={mode} 需要成本源，但 records={total_records}, api_ready={api_ready}"
        )
        _append_check(
            checks,
            name="自动报价成本源",
            passed=passed,
            message=message,
            critical=False,
            meta={
                "mode": mode,
                "total_records": total_records,
                "api_ready": api_ready,
                "files": stats.get("files", []),
            },
        )
    except Exception as exc:
        _append_check(
            checks,
            name="自动报价成本源",
            passed=False,
            message=f"检查失败: {exc}",
            critical=False,
        )

    return checks


def run_doctor(skip_gateway: bool = False, skip_quote: bool = False) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []

    startup_checks = run_all_checks(skip_browser=bool(skip_gateway))
    for item in startup_checks:
        _append_check(
            checks,
            name=item.name,
            passed=item.passed,
            message=item.message,
            critical=item.critical,
        )

    checks.extend(_extra_checks(skip_quote=skip_quote))

    total = len(checks)
    passed_count = sum(1 for c in checks if c["passed"])
    failed = [c for c in checks if not c["passed"]]
    critical_failed = [c for c in failed if c["critical"]]
    warning_failed = [c for c in failed if not c["critical"]]

    next_steps: list[str] = []
    seen: set[str] = set()
    for item in failed:
        suggestion = str(item.get("suggestion", "")).strip()
        if suggestion and suggestion not in seen:
            seen.add(suggestion)
            next_steps.append(suggestion)

    return {
        "ready": len(critical_failed) == 0,
        "summary": {
            "total": total,
            "passed": passed_count,
            "failed": len(failed),
            "critical_failed": len(critical_failed),
            "warning_failed": len(warning_failed),
        },
        "checks": checks,
        "next_steps": next_steps,
    }
