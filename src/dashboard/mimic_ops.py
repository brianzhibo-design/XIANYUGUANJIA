"""轻量后台可视化与模块控制服务。"""

from __future__ import annotations

import asyncio
import csv
import hashlib
import io
import json
import logging
import os
import re
import sqlite3
import subprocess
import sys
import threading
import time
import zipfile
from contextlib import closing
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import yaml

from src.core.config import get_config
from src.dashboard.config_service import (
    read_system_config as _read_system_config,
)
from src.dashboard.module_console import MODULE_TARGETS, ModuleConsole
from src.modules.messages.service import MessagesService
from src.modules.quote.cost_table import CostTableRepository, normalize_courier_name
from src.modules.quote.setup import DEFAULT_MARKUP_RULES, QuoteSetupService
from src.modules.virtual_goods.service import VirtualGoodsService

logger = logging.getLogger(__name__)

_product_image_cache: dict[str, tuple[str, float]] = {}
_PRODUCT_IMAGE_CACHE_TTL = 1800  # 30 minutes


def _safe_int(value: str | None, default: int, min_value: int, max_value: int) -> int:
    try:
        if value is None:
            return default
        n = int(value)
        if n < min_value:
            return min_value
        if n > max_value:
            return max_value
        return n
    except (TypeError, ValueError):
        return default


def _error_payload(message: str, code: str = "INTERNAL_ERROR", details: Any = None) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "success": False,
        "error": str(message),
        "error_code": str(code),
        "error_message": str(message),
    }
    if details is not None:
        payload["details"] = details
    return payload


def _extract_json_payload(text: str) -> Any | None:
    raw = str(text or "").strip()
    if not raw:
        return None

    try:
        return json.loads(raw)
    except Exception:
        pass

    for lch, rch in (("{", "}"), ("[", "]")):
        start = raw.find(lch)
        end = raw.rfind(rch)
        if start != -1 and end != -1 and end > start:
            candidate = raw[start : end + 1]
            try:
                return json.loads(candidate)
            except Exception:
                continue
    return None


_YAML_CONFIG_PATH = Path(__file__).resolve().parents[1] / "config" / "config.yaml"
_YAML_EXAMPLE_PATH = Path(__file__).resolve().parents[1] / "config" / "config.example.yaml"

_AUTO_REPLY_TO_YAML_KEYS = {
    "default_reply": "default_reply",
    "virtual_default_reply": "virtual_default_reply",
    "enabled": "enabled",
    "ai_intent_enabled": "ai_intent_enabled",
    "quote_missing_template": "quote_missing_template",
    "strict_format_reply_enabled": "strict_format_reply_enabled",
    "force_non_empty_reply": "force_non_empty_reply",
    "non_empty_reply_fallback": "non_empty_reply_fallback",
    "quote_failed_template": "quote_failed_template",
    "quote_reply_max_couriers": "quote_reply_max_couriers",
    "first_reply_delay": "first_reply_delay_seconds",
    "inter_reply_delay": "inter_reply_delay_seconds",
}


def _sync_system_config_to_yaml(sys_config: dict[str, Any]) -> None:
    """Write relevant system_config fields back to config.yaml so the runtime picks them up."""
    yaml_path = _YAML_CONFIG_PATH if _YAML_CONFIG_PATH.exists() else _YAML_EXAMPLE_PATH
    if not yaml_path.exists():
        return
    try:
        raw = yaml_path.read_text(encoding="utf-8")
        cfg = yaml.safe_load(raw) or {}
    except Exception:
        return

    changed = False

    ar = sys_config.get("auto_reply")
    if isinstance(ar, dict):
        msgs = cfg.setdefault("messages", {})
        _RANGE_KEYS = {"first_reply_delay", "inter_reply_delay"}
        for src_key, dst_key in _AUTO_REPLY_TO_YAML_KEYS.items():
            if src_key in ar:
                val = ar[src_key]
                if src_key in _RANGE_KEYS and isinstance(val, str) and "-" in val:
                    try:
                        parts = val.split("-", 1)
                        val = [float(parts[0].strip()), float(parts[1].strip())]
                    except (ValueError, IndexError):
                        pass
                msgs[dst_key] = val
                changed = True
        kw_text = ar.get("keyword_replies_text")
        if isinstance(kw_text, str) and kw_text.strip():
            kw_dict: dict[str, str] = {}
            for line in kw_text.strip().splitlines():
                line = line.strip()
                if "=" in line:
                    k, v = line.split("=", 1)
                    k, v = k.strip(), v.strip()
                    if k and v:
                        kw_dict[k] = v
            if kw_dict:
                msgs["keyword_replies"] = kw_dict
                changed = True
        custom_rules = ar.get("custom_intent_rules")
        if isinstance(custom_rules, list):
            msgs["intent_rules"] = [
                {
                    k: v
                    for k, v in r.items()
                    if k
                    in (
                        "name",
                        "keywords",
                        "reply",
                        "patterns",
                        "priority",
                        "categories",
                        "needs_human",
                        "human_reason",
                        "phase",
                        "skip_reply",
                    )
                }
                for r in custom_rules
                if isinstance(r, dict) and r.get("name")
            ]
            changed = True

    for section_key in ("pricing", "delivery"):
        sec = sys_config.get(section_key)
        if isinstance(sec, dict):
            cfg.setdefault(section_key, {}).update(sec)
            changed = True

    store = sys_config.get("store")
    if isinstance(store, dict) and "category" in store:
        cfg.setdefault("store", {})["category"] = store["category"]
        changed = True

    slider = sys_config.get("slider_auto_solve")
    if isinstance(slider, dict):
        ws_cfg = cfg.setdefault("messages", {}).setdefault("ws", {})
        slider_dict = {
            "enabled": bool(slider.get("enabled", False)),
            "max_attempts": int(slider.get("max_attempts", 2)),
            "cooldown_seconds": int(slider.get("cooldown_seconds", 300)),
            "headless": bool(slider.get("headless", False)),
        }
        fp = slider.get("fingerprint_browser")
        if isinstance(fp, dict):
            slider_dict["fingerprint_browser"] = {
                "enabled": bool(fp.get("enabled", False)),
                "api_url": str(fp.get("api_url", "http://127.0.0.1:54345")),
                "browser_id": str(fp.get("browser_id", "")),
            }
        ws_cfg["slider_auto_solve"] = slider_dict
        changed = True

    if changed:
        try:
            tmp = yaml_path.with_suffix(".tmp")
            tmp.write_text(
                yaml.dump(cfg, allow_unicode=True, default_flow_style=False, sort_keys=False), encoding="utf-8"
            )
            tmp.rename(yaml_path)
        except Exception as exc:
            logger.warning("Failed to sync config to YAML: %s", exc)


def _test_xgj_connection(
    *,
    app_key: str,
    app_secret: str,
    base_url: str,
    mode: str = "self_developed",
    seller_id: str = "",
) -> dict[str, Any]:
    """Test connectivity to 闲管家 using OpenPlatformClient with proper query-param auth."""
    from src.integrations.xianguanjia.open_platform_client import OpenPlatformClient

    client = OpenPlatformClient(
        base_url=base_url,
        app_key=app_key,
        app_secret=app_secret,
        mode=mode,
        seller_id=seller_id,
        timeout=8.0,
    )
    t0 = time.time()
    resp = client.list_authorized_users()
    latency = int((time.time() - t0) * 1000)
    if resp.ok:
        return {"ok": True, "message": "连通", "latency_ms": latency}
    return {"ok": False, "message": resp.error_message or "连接失败", "latency_ms": latency}


DEFAULT_WEIGHT_TEMPLATE = (
    "{origin_province}到{dest_province} {billing_weight}kg 参考价格\n"
    "{courier}: {price} 元\n"
    "预计时效：{eta_days}\n"
    "重要提示：\n"
    "体积重大于实际重量时按体积计费！"
)
DEFAULT_VOLUME_TEMPLATE = (
    "{origin_province}到{dest_province} {billing_weight}kg 参考价格\n"
    "体积重规则：{volume_formula}\n"
    "{courier}: {price} 元\n"
    "预计时效：{eta_days}\n"
    "重要提示：\n"
    "体积重大于实际重量时按体积计费！"
)


def _run_async(coro: Any) -> Any:
    """在 HTTP 线程内安全执行协程。"""

    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def _now_iso() -> str:
    return datetime.now().strftime("%Y-%m-%dT%H:%M:%S")


class MimicOps:
    """模仿 XianyuAutoAgent 的页面与操作能力。"""

    _ROUTE_FILE_EXTS = {".xlsx", ".xls", ".csv"}
    _MARKUP_FILE_EXTS = {".xlsx", ".xls", ".csv", ".json", ".yaml", ".yml", ".txt", ".md"}
    _MARKUP_IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".bmp", ".webp", ".gif"}
    _MARKUP_REQUIRED_FIELDS = ("normal_first_add", "member_first_add", "normal_extra_add", "member_extra_add")
    _MARKUP_FIELD_ALIASES: dict[str, tuple[str, ...]] = {
        "courier": ("运力", "快递", "快递公司", "物流", "渠道", "公司", "courier", "carrier", "name"),
        "normal_first_add": (
            "normal_first_add",
            "普通首重",
            "首重普通",
            "首重溢价普通",
            "首重加价普通",
            "first_normal",
            "normal_first",
        ),
        "member_first_add": (
            "member_first_add",
            "会员首重",
            "首重会员",
            "首重溢价会员",
            "首重加价会员",
            "first_member",
            "member_first",
            "vip_first",
        ),
        "normal_extra_add": (
            "normal_extra_add",
            "普通续重",
            "续重普通",
            "续重溢价普通",
            "续重加价普通",
            "extra_normal",
            "normal_extra",
        ),
        "member_extra_add": (
            "member_extra_add",
            "会员续重",
            "续重会员",
            "续重溢价会员",
            "续重加价会员",
            "extra_member",
            "member_extra",
            "vip_extra",
        ),
    }
    _COOKIE_REQUIRED_KEYS = ("_tb_token_", "cookie2", "sgcookie", "unb")
    _COOKIE_RECOMMENDED_KEYS = ("XSRF-TOKEN", "last_u_xianyu_web", "tfstk", "t", "cna")
    _COOKIE_DOMAIN_ALLOWLIST = ("goofish.com", "passport.goofish.com")
    _COOKIE_IMPORT_EXTS = {".txt", ".json", ".log", ".cookies", ".csv", ".tsv", ".har"}
    _COOKIE_HINT_KEYS = ("_tb_token_", "cookie2", "sgcookie", "unb", "_m_h5_tk", "_m_h5_tk_enc")
    _COOKIE_NAME_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_-]*$")
    _ANSI_ESCAPE_RE = re.compile(r"\x1B\[[0-?]*[ -/]*[@-~]")
    _LOG_TIME_RE = re.compile(r"(\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2})")
    _RISK_BLOCK_PATTERNS = (
        "fail_sys_user_validate",
        "rgv587",
        "账号异常",
        "账号风险",
        "安全验证",
        "访问受限",
        "封控",
        "封禁",
    )
    _RISK_WARN_PATTERNS = (
        "http 400",
        "http 403",
        "forbidden",
        "unauthorized",
        "token api failed",
        "需要验证码",
        "验证码",
        "校验失败",
    )
    _RISK_SIGNAL_WINDOW_MINUTES = 120

    def __init__(self, project_root: str | Path, module_console: ModuleConsole):
        self.project_root = Path(project_root).resolve()
        self.module_console = module_console
        self._service_started_at = _now_iso()
        self._instance_id = f"dashboard-{os.getpid()}-{int(time.time())}"
        self._python_exec = sys.executable
        self._service_state: dict[str, Any] = {
            "suspended": False,
            "stopped": False,
            "updated_at": _now_iso(),
        }
        self._last_cookie_fp = ""
        self._last_token_error: str | None = None
        self._last_auto_recover_cookie_fp = ""
        self._last_auto_recover_at = ""
        self._last_auto_recover_result: dict[str, Any] = {}
        self._last_presales_dead_restart_at: float = 0.0
        self._recover_lock = threading.Lock()
        self._cost_table_repo: Any = None
        self._shared_cookie_checker: Any = None
        self._risk_log_cache: dict[str, Any] | None = None
        self._risk_log_cache_ts: float = 0.0

    @property
    def env_path(self) -> Path:
        return self.project_root / ".env"

    @property
    def logs_dir(self) -> Path:
        return self.project_root / "logs"

    @property
    def cookie_plugin_dir(self) -> Path:
        return self.project_root / "third_party" / "Get-cookies.txt-LOCALLY"

    def _read_env_lines(self) -> list[str]:
        if not self.env_path.exists():
            return []
        return self.env_path.read_text(encoding="utf-8", errors="ignore").splitlines()

    def _get_env_value(self, key: str) -> str:
        key_norm = f"{key}="
        for line in self._read_env_lines():
            if line.startswith(key_norm):
                return line[len(key_norm) :]
        return os.getenv(key, "")

    def _set_env_value(self, key: str, value: str) -> None:
        key_norm = f"{key}="
        lines = self._read_env_lines()
        updated = False
        for idx, line in enumerate(lines):
            if line.startswith(key_norm):
                lines[idx] = f"{key}={value}"
                updated = True
                break
        if not updated:
            lines.append(f"{key}={value}")
        self.env_path.parent.mkdir(parents=True, exist_ok=True)
        self.env_path.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")
        os.environ[key] = value

    @staticmethod
    def _to_bool(value: Any, default: bool = False) -> bool:
        if isinstance(value, bool):
            return value
        text = str(value or "").strip().lower()
        if not text:
            return default
        return text in {"1", "true", "yes", "on", "enabled"}

    def _get_env_bool(self, key: str, default: bool = False) -> bool:
        raw = self._get_env_value(key)
        return self._to_bool(raw, default=default)

    def _get_xianguanjia_settings(self) -> dict[str, Any]:
        app_key = self._get_env_value("XGJ_APP_KEY").strip()
        app_secret = self._get_env_value("XGJ_APP_SECRET").strip()
        merchant_id = self._get_env_value("XGJ_MERCHANT_ID").strip()
        base_url = self._get_env_value("XGJ_BASE_URL").strip() or "https://open.goofish.pro"
        auto_price_enabled = self._get_env_bool("XGJ_AUTO_PRICE_ENABLED", default=True)
        auto_ship_enabled = self._get_env_bool("XGJ_AUTO_SHIP_ENABLED", default=True)
        auto_ship_on_paid = self._get_env_bool("XGJ_AUTO_SHIP_ON_PAID", default=True)
        return {
            "configured": bool(app_key and app_secret),
            "app_key": app_key,
            "app_secret": app_secret,
            "merchant_id": merchant_id,
            "base_url": base_url,
            "auto_price_enabled": auto_price_enabled,
            "auto_ship_enabled": auto_ship_enabled,
            "auto_ship_on_paid": auto_ship_on_paid,
        }

    @staticmethod
    def _mask_secret(value: str) -> str:
        text = str(value or "").strip()
        if len(text) <= 6:
            return "*" * len(text)
        return text[:3] + "*" * (len(text) - 6) + text[-3:]

    def get_xianguanjia_settings(self) -> dict[str, Any]:
        settings = self._get_xianguanjia_settings()
        return {
            "success": True,
            "configured": settings["configured"],
            "app_key": settings["app_key"],
            "app_secret_masked": self._mask_secret(settings["app_secret"]),
            "merchant_id": settings["merchant_id"],
            "base_url": settings["base_url"],
            "auto_price_enabled": settings["auto_price_enabled"],
            "auto_ship_enabled": settings["auto_ship_enabled"],
            "auto_ship_on_paid": settings["auto_ship_on_paid"],
            "callback_url": "/api/orders/callback",
        }

    def save_xianguanjia_settings(self, payload: dict[str, Any]) -> dict[str, Any]:
        data = dict(payload or {})
        updates = {
            "XGJ_APP_KEY": str(data.get("app_key") or self._get_env_value("XGJ_APP_KEY")).strip(),
            "XGJ_APP_SECRET": str(data.get("app_secret") or self._get_env_value("XGJ_APP_SECRET")).strip(),
            "XGJ_MERCHANT_ID": str(data.get("merchant_id") or self._get_env_value("XGJ_MERCHANT_ID")).strip(),
            "XGJ_BASE_URL": str(data.get("base_url") or self._get_env_value("XGJ_BASE_URL")).strip()
            or "https://open.goofish.pro",
            "XGJ_AUTO_PRICE_ENABLED": "1"
            if self._to_bool(data.get("auto_price_enabled"), default=self._get_env_bool("XGJ_AUTO_PRICE_ENABLED", True))
            else "0",
            "XGJ_AUTO_SHIP_ENABLED": "1"
            if self._to_bool(data.get("auto_ship_enabled"), default=self._get_env_bool("XGJ_AUTO_SHIP_ENABLED", True))
            else "0",
            "XGJ_AUTO_SHIP_ON_PAID": "1"
            if self._to_bool(data.get("auto_ship_on_paid"), default=self._get_env_bool("XGJ_AUTO_SHIP_ON_PAID", True))
            else "0",
        }
        for key, value in updates.items():
            self._set_env_value(key, value)

        saved = self.get_xianguanjia_settings()
        saved["message"] = "闲管家设置已更新"
        return saved

    def _xianguanjia_service_config(self) -> dict[str, Any]:
        settings = self._get_xianguanjia_settings()
        sys_cfg = _read_system_config()
        xgj_sys = sys_cfg.get("xianguanjia", {}) if isinstance(sys_cfg.get("xianguanjia"), dict) else {}

        # env 为空时从 system_config 回退；用于 SystemConfig 写入 system_config.json 但 .env 未同步的场景
        app_key = (settings["app_key"] or "").strip() or str(xgj_sys.get("app_key", "")).strip()
        app_secret = (settings["app_secret"] or "").strip() or str(xgj_sys.get("app_secret", "")).strip()
        base_url = (
            (settings["base_url"] or "").strip()
            or str(xgj_sys.get("base_url", "")).strip()
            or "https://open.goofish.pro"
        )
        merchant_id = (settings["merchant_id"] or "").strip() or str(xgj_sys.get("merchant_id", "")).strip() or None

        merged_xgj = dict(xgj_sys)
        merged_xgj.update(
            {
                "enabled": bool(app_key and app_secret),
                "app_key": app_key,
                "app_secret": app_secret,
                "merchant_id": merchant_id or None,
                "base_url": base_url,
            }
        )

        result: dict[str, Any] = {"xianguanjia": merged_xgj}
        oss_cfg = sys_cfg.get("oss")
        if isinstance(oss_cfg, dict) and oss_cfg:
            clean_oss = {k: v for k, v in oss_cfg.items() if v and not str(v).endswith("****")}
            if clean_oss:
                result["oss"] = clean_oss
        return result

    def retry_xianguanjia_delivery(self, payload: dict[str, Any]) -> dict[str, Any]:
        from src.modules.orders.service import OrderFulfillmentService

        svc_cfg = self._xianguanjia_service_config()
        if not (svc_cfg.get("xianguanjia", {}).get("enabled", False)):
            return _error_payload("闲管家凭证未配置", code="XGJ_NOT_CONFIGURED")

        data = dict(payload or {})
        shipping_info = data.get("shipping_info")
        if not isinstance(shipping_info, dict):
            shipping_info = {}

        for field in (
            "order_no",
            "waybill_no",
            "express_code",
            "express_name",
            "ship_name",
            "ship_mobile",
            "ship_province",
            "ship_city",
            "ship_area",
            "ship_address",
        ):
            if field in data and data.get(field) not in (None, ""):
                shipping_info[field] = data.get(field)

        order_id = str(data.get("order_id") or data.get("order_no") or "").strip()
        if not order_id:
            return _error_payload("缺少订单号", code="MISSING_ORDER_ID")

        service = OrderFulfillmentService(
            db_path=str(self.project_root / "data" / "orders.db"),
            config=self._xianguanjia_service_config(),
        )
        try:
            result = service.deliver(
                order_id=order_id,
                dry_run=self._to_bool(data.get("dry_run"), default=False),
                shipping_info=shipping_info or None,
            )
        except Exception as exc:
            return _error_payload(f"发货重试失败: {exc}", code="XGJ_RETRY_SHIP_FAILED")
        return {"success": True, **result}

    def retry_xianguanjia_price(self, payload: dict[str, Any]) -> dict[str, Any]:
        from src.modules.operations.service import OperationsService

        svc_cfg = self._xianguanjia_service_config()
        if not (svc_cfg.get("xianguanjia", {}).get("enabled", False)):
            return _error_payload("闲管家凭证未配置", code="XGJ_NOT_CONFIGURED")

        data = dict(payload or {})
        product_id = str(data.get("product_id") or data.get("productId") or "").strip()
        if not product_id:
            return _error_payload("缺少商品 ID", code="MISSING_PRODUCT_ID")

        try:
            new_price = float(data.get("new_price"))
        except Exception:
            return _error_payload("缺少有效的新价格", code="INVALID_NEW_PRICE")

        original_price_raw = data.get("original_price")
        original_price = None
        if original_price_raw not in (None, ""):
            try:
                original_price = float(original_price_raw)
            except Exception:
                return _error_payload("原价格式无效", code="INVALID_ORIGINAL_PRICE")

        service = OperationsService(config=self._xianguanjia_service_config())
        try:
            result = _run_async(service.update_price(product_id, new_price, original_price))
        except Exception as exc:
            return _error_payload(f"改价重试失败: {exc}", code="XGJ_RETRY_PRICE_FAILED")
        return {"success": bool(result.get("success")), **result}

    def handle_order_callback(self, payload: dict[str, Any]) -> dict[str, Any]:
        from src.modules.orders.service import OrderFulfillmentService

        data = dict(payload or {})
        svc_cfg = self._xianguanjia_service_config()
        xgj_enabled = bool(svc_cfg.get("xianguanjia", {}).get("enabled", False))
        service = OrderFulfillmentService(
            db_path=str(self.project_root / "data" / "orders.db"),
            config=svc_cfg,
        )

        sys_cfg = _read_system_config()
        delivery_cfg = sys_cfg.get("delivery", {})
        settings = self._get_xianguanjia_settings()
        auto_delivery_override = delivery_cfg.get("auto_delivery")
        if auto_delivery_override is not None:
            use_auto = bool(auto_delivery_override) and xgj_enabled
        else:
            use_auto = bool(xgj_enabled and settings["auto_ship_enabled"] and settings["auto_ship_on_paid"])

        try:
            result = service.process_callback(
                data,
                dry_run=self._to_bool(data.get("dry_run"), default=False),
                auto_deliver=use_auto,
            )
        except Exception as exc:
            return _error_payload(f"回调处理失败: {exc}", code="XGJ_CALLBACK_FAILED")

        result["settings"] = {
            "configured": settings["configured"],
            "auto_ship_enabled": settings["auto_ship_enabled"],
            "auto_ship_on_paid": settings["auto_ship_on_paid"],
            "auto_delivery_source": "system_config" if auto_delivery_override is not None else "env",
        }
        return result

    def handle_order_push(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Handle order push notification from Xianyu.

        Processes order callback AND triggers auto-price-modify for
        status 11 (pending payment) orders asynchronously.
        """
        order_status = payload.get("order_status")
        order_no = str(payload.get("order_no", ""))

        callback_result = self.handle_order_callback(payload)

        if order_status == 11 and order_no:
            sys_cfg = _read_system_config()
            apm_cfg = sys_cfg.get("auto_price_modify", {})
            if apm_cfg.get("enabled"):
                import threading

                t = threading.Thread(
                    target=self._auto_modify_price_sync,
                    args=(order_no, payload, apm_cfg),
                    daemon=True,
                )
                t.start()
                callback_result["auto_price_modify_triggered"] = True

        return callback_result

    def _auto_modify_price_sync(self, order_no: str, push_payload: dict[str, Any], apm_cfg: dict[str, Any]) -> None:
        """Background thread: look up quote and modify order price."""
        try:
            from src.integrations.xianguanjia.open_platform_client import OpenPlatformClient
            from src.modules.quote.ledger import get_quote_ledger

            settings = self._get_xianguanjia_settings()
            if not settings["configured"]:
                logger.warning("Auto-price-modify: xianguanjia not configured")
                return

            xgj_cfg = self._xianguanjia_service_config().get("xianguanjia", {})
            client_fields = {"base_url", "app_key", "app_secret", "timeout", "mode", "seller_id"}
            client_kwargs = {k: v for k, v in xgj_cfg.items() if k in client_fields and v}
            client = OpenPlatformClient(**client_kwargs)

            detail_resp = client.get_order_detail({"order_no": order_no})
            if not detail_resp.ok:
                logger.warning("Auto-price-modify: failed to get order detail for %s", order_no)
                return

            detail = detail_resp.data or {}
            buyer_nick = str(detail.get("buyer_nick", ""))
            buyer_eid = str(detail.get("buyer_eid", "")).strip()
            goods = detail.get("goods") or {}
            item_id = str(goods.get("item_id", ""))
            total_amount = int(detail.get("total_amount", 0))

            if not buyer_nick and not buyer_eid:
                logger.info("Auto-price-modify: no buyer_nick/buyer_eid in order %s", order_no)
                return

            max_age = int(apm_cfg.get("max_quote_age_seconds", 7200))
            ledger = get_quote_ledger()
            quote = ledger.find_by_buyer(
                buyer_nick,
                item_id=item_id,
                max_age_seconds=max_age,
                sender_user_id=buyer_eid,
            )

            if not quote:
                fallback = apm_cfg.get("fallback_action", "skip")
                if fallback == "use_listing_price":
                    logger.info(
                        "Auto-price-modify: no quote for buyer=%s order=%s, "
                        "fallback=use_listing_price — accepting at current price",
                        buyer_nick,
                        order_no,
                    )
                    return
                logger.info(
                    "Auto-price-modify: no matching quote for buyer=%s order=%s, fallback=%s",
                    buyer_nick,
                    order_no,
                    fallback,
                )
                return

            quote_rows = quote.get("quote_rows", [])
            courier_choice = quote.get("courier_choice", "")

            target_fee = None
            if courier_choice:
                for row in quote_rows:
                    if str(row.get("courier", "")).strip() == courier_choice.strip():
                        target_fee = row.get("total_fee")
                        break
            if target_fee is None and quote_rows:
                target_fee = min(r.get("total_fee", 0) for r in quote_rows if r.get("total_fee"))

            if target_fee is None:
                logger.info("Auto-price-modify: no valid fee in quote for order=%s", order_no)
                return

            target_price_cents = round(float(target_fee) * 100)
            express_fee_cents = int(float(apm_cfg.get("default_express_fee", 0)) * 100)

            if target_price_cents == total_amount:
                logger.info("Auto-price-modify: price already correct for order=%s", order_no)
                return

            import time as _time

            retry_delays = (2, 4, 8)
            last_exc = None
            modify_resp = None
            for attempt in range(1 + len(retry_delays)):
                try:
                    modify_resp = client.modify_order_price(
                        {
                            "order_no": order_no,
                            "order_price": target_price_cents,
                            "express_fee": express_fee_cents,
                        }
                    )
                    if modify_resp.ok:
                        logger.info(
                            "Auto-price-modify: SUCCESS order=%s from=%d to=%d (express=%d)",
                            order_no,
                            total_amount,
                            target_price_cents,
                            express_fee_cents,
                        )
                        self._mark_order_processed_in_poller(order_no)
                        return
                    last_exc = None
                    if not getattr(modify_resp, "retryable", False) or attempt >= len(retry_delays):
                        break
                    delay = retry_delays[attempt]
                    logger.info(
                        "Auto-price-modify: retry in %ds (attempt %d) order=%s error=%s",
                        delay,
                        attempt + 1,
                        order_no,
                        modify_resp.error_message,
                    )
                    _time.sleep(delay)
                except Exception as exc:
                    last_exc = exc
                    if attempt >= len(retry_delays):
                        break
                    from src.integrations.xianguanjia.errors import is_retryable_error

                    if not is_retryable_error(exc):
                        raise
                    delay = retry_delays[attempt]
                    logger.info(
                        "Auto-price-modify: retry in %ds (attempt %d) order=%s exc=%s",
                        delay,
                        attempt + 1,
                        order_no,
                        type(exc).__name__,
                    )
                    _time.sleep(delay)

            if modify_resp is not None and not modify_resp.ok:
                logger.warning(
                    "Auto-price-modify: FAILED order=%s error=%s",
                    order_no,
                    modify_resp.error_message,
                )
            if last_exc is not None:
                raise last_exc

        except Exception:
            logger.error("Auto-price-modify: unexpected error for order=%s", order_no, exc_info=True)

    @staticmethod
    def _mark_order_processed_in_poller(order_no: str) -> None:
        """Notify the poller that this order was already handled by the push callback."""
        try:
            from src.modules.orders.auto_price_poller import get_price_poller

            poller = get_price_poller()
            if poller is not None:
                poller._processed[order_no] = __import__("time").time()
        except Exception:
            pass

    def _resolve_session_id_for_order(self, order_no: str) -> str:
        """Try to find the chat session_id for a given order.

        Priority: local orders DB > QuoteLedger (via buyer_nick) > ws_live reverse map.
        """
        # 1. 查本地订单库
        try:
            from src.modules.orders.service import OrderFulfillmentService

            ofs = OrderFulfillmentService(
                config=self._xianguanjia_service_config(),
            )
            order = ofs.get_order(order_no)
            if order and str(order.get("session_id", "")).strip():
                return str(order["session_id"]).strip()
        except Exception:
            pass

        # 2. 通过闲管家 API 获取 buyer_nick，再查 QuoteLedger
        buyer_nick = ""
        try:
            from src.integrations.xianguanjia.open_platform_client import OpenPlatformClient

            xgj_cfg = self._xianguanjia_service_config().get("xianguanjia", {})
            client_fields = {"base_url", "app_key", "app_secret", "timeout", "mode", "seller_id"}
            client_kwargs = {k: v for k, v in xgj_cfg.items() if k in client_fields and v}
            if client_kwargs.get("app_key") and client_kwargs.get("app_secret"):
                client = OpenPlatformClient(**client_kwargs)
                detail_resp = client.get_order_detail({"order_no": order_no})
                if detail_resp.ok and isinstance(detail_resp.data, dict):
                    buyer_nick = str(detail_resp.data.get("buyer_nick", "")).strip()
        except Exception:
            pass

        if buyer_nick:
            try:
                from src.modules.quote.ledger import get_quote_ledger

                quote = get_quote_ledger().find_by_buyer(buyer_nick)
                if quote and str(quote.get("session_id", "")).strip():
                    return str(quote["session_id"]).strip()
            except Exception:
                pass

        # 3. ws_live 反向映射
        try:
            from src.modules.messages.ws_live import get_session_by_buyer_nick

            sid = get_session_by_buyer_nick(buyer_nick) if buyer_nick else ""
            if sid:
                return sid
        except Exception:
            pass

        return ""

    def handle_product_callback(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Handle product callback notification (async publish result)."""
        product_id = payload.get("product_id")
        task_type = payload.get("task_type")
        task_result = payload.get("task_result")
        payload.get("item_id")
        err_code = payload.get("err_code", "")
        err_msg = payload.get("err_msg", "")
        product_status = payload.get("product_status")
        publish_status = payload.get("publish_status")

        logger.info(
            "Product callback: product_id=%s task_type=%s result=%s status=%s/%s err=%s/%s",
            product_id,
            task_type,
            task_result,
            product_status,
            publish_status,
            err_code,
            err_msg,
        )

        if product_id and task_type in (10, 11):
            try:
                from src.modules.listing.publish_queue import PublishQueue

                queue = PublishQueue(project_root=self.project_root)
                for item in queue.get_queue():
                    pid = (
                        item.get("published_product_id")
                        if isinstance(item, dict)
                        else getattr(item, "published_product_id", None)
                    )
                    status = item.get("status") if isinstance(item, dict) else getattr(item, "status", None)
                    item_id_val = item.get("id") if isinstance(item, dict) else getattr(item, "id", None)
                    if pid == product_id and status == "publishing":
                        if task_result == 1:
                            queue.update_item(
                                item_id_val,
                                {
                                    "status": "published",
                                    "error": None,
                                },
                            )
                            logger.info("Product callback: marked queue item %s as published", item_id_val)
                        elif task_result == 2:
                            queue.update_item(
                                item_id_val,
                                {
                                    "status": "failed",
                                    "error": f"上架失败: [{err_code}] {err_msg}",
                                },
                            )
                            logger.warning("Product callback: marked queue item %s as failed: %s", item_id_val, err_msg)
                        break
            except Exception:
                logger.error("Product callback: failed to update publish queue", exc_info=True)

        return {"success": True, "product_id": product_id, "task_result": task_result}

    def _virtual_goods_service(self) -> VirtualGoodsService:
        return VirtualGoodsService(
            db_path=str(self.project_root / "data" / "orders.db"),
            config=self._xianguanjia_service_config(),
        )

    @staticmethod
    def _vg_service_metrics(result: dict[str, Any]) -> dict[str, Any]:
        metrics = result.get("metrics")
        if isinstance(metrics, dict):
            return metrics
        data = result.get("data")
        if isinstance(data, dict):
            return data
        return {}

    @staticmethod
    def _vg_int(metrics: dict[str, Any], key: str) -> int:
        try:
            return int(metrics.get(key) or 0)
        except Exception:
            return 0

    def _build_virtual_goods_dashboard_panels(
        self,
        dashboard_result: dict[str, Any],
        manual_orders: list[dict[str, Any]],
        funnel_result: dict[str, Any] | None,
        exception_result: dict[str, Any] | None,
        fulfillment_result: dict[str, Any] | None,
        product_result: dict[str, Any] | None,
    ) -> dict[str, Any]:
        metrics = self._vg_service_metrics(dashboard_result)
        errors = dashboard_result.get("errors") if isinstance(dashboard_result.get("errors"), list) else []

        failed_callbacks = self._vg_int(metrics, "failed_callbacks")
        timeout_backlog = self._vg_int(metrics, "timeout_backlog")
        unknown_event_kind = self._vg_int(metrics, "unknown_event_kind")
        timeout_seconds = self._vg_int(metrics, "timeout_seconds")

        funnel_data = (
            funnel_result.get("data")
            if isinstance(funnel_result, dict) and isinstance(funnel_result.get("data"), dict)
            else {}
        )
        funnel_stage_totals = (
            funnel_data.get("stage_totals") if isinstance(funnel_data.get("stage_totals"), dict) else {}
        )

        exception_data = (
            exception_result.get("data")
            if isinstance(exception_result, dict) and isinstance(exception_result.get("data"), dict)
            else {}
        )
        exception_items = exception_data.get("items") if isinstance(exception_data.get("items"), list) else []

        fulfillment_data = (
            fulfillment_result.get("data")
            if isinstance(fulfillment_result, dict) and isinstance(fulfillment_result.get("data"), dict)
            else {}
        )
        fulfillment_summary = (
            fulfillment_data.get("summary") if isinstance(fulfillment_data.get("summary"), dict) else {}
        )

        product_data = (
            product_result.get("data")
            if isinstance(product_result, dict) and isinstance(product_result.get("data"), dict)
            else {}
        )
        product_summary_raw = product_data.get("summary") if isinstance(product_data.get("summary"), dict) else {}

        stable_product_fields = [
            "exposure_count",
            "paid_order_count",
            "paid_amount_cents",
            "refund_order_count",
            "exception_count",
            "manual_takeover_count",
            "conversion_rate_pct",
        ]
        product_summary: dict[str, Any] = {}
        product_field_state: dict[str, str] = {}
        for key in stable_product_fields:
            if key in product_summary_raw:
                product_summary[key] = product_summary_raw.get(key)
                product_field_state[key] = "available"
            else:
                product_summary[key] = None
                product_field_state[key] = "placeholder"

        exception_pool: list[dict[str, Any]] = [x for x in exception_items if isinstance(x, dict)]
        if unknown_event_kind > 0 and not any(
            str(x.get("type") or "").upper() == "UNKNOWN_EVENT_KIND" for x in exception_pool
        ):
            exception_pool.insert(
                0,
                {
                    "priority": "P0",
                    "type": "UNKNOWN_EVENT_KIND",
                    "count": unknown_event_kind,
                    "summary": "检测到未知事件类型回调，需人工排查映射。",
                },
            )
        if failed_callbacks > 0 and not any(
            str(x.get("type") or "").upper() == "FAILED_CALLBACK" for x in exception_pool
        ):
            exception_pool.append(
                {
                    "priority": "P1",
                    "type": "FAILED_CALLBACK",
                    "count": failed_callbacks,
                    "summary": "回调处理失败，建议优先重放失败回调。",
                }
            )
        if timeout_backlog > 0 and not any(
            str(x.get("type") or "").upper() == "TIMEOUT_BACKLOG" for x in exception_pool
        ):
            exception_pool.append(
                {
                    "priority": "P1",
                    "type": "TIMEOUT_BACKLOG",
                    "count": timeout_backlog,
                    "summary": f"存在超时未处理回调（超时阈值 {timeout_seconds}s）。",
                }
            )
        for err in errors:
            if not isinstance(err, dict):
                continue
            if str(err.get("code") or "").upper() == "UNKNOWN_EVENT_KIND" and unknown_event_kind <= 0:
                exception_pool.append(
                    {
                        "priority": "P0",
                        "type": "UNKNOWN_EVENT_KIND",
                        "count": int(err.get("count") or 1),
                        "summary": str(err.get("message") or "unknown event_kind detected"),
                    }
                )

        stage_totals_int = {str(k): self._vg_int(funnel_stage_totals, str(k)) for k in funnel_stage_totals.keys()}
        funnel_total = sum(stage_totals_int.values())

        return {
            "operations_funnel_overview": {
                "stage_totals": stage_totals_int,
                "total_metric_count": int(
                    ((funnel_result.get("metrics") or {}).get("total_metric_count") or funnel_total)
                    if isinstance(funnel_result, dict)
                    else funnel_total
                ),
                "source": str((funnel_result.get("metrics") or {}).get("source") or "ops_funnel_stage_daily")
                if isinstance(funnel_result, dict)
                else "ops_funnel_stage_daily",
            },
            "exception_priority_pool": {
                "total_items": len(exception_pool),
                "items": exception_pool,
            },
            "fulfillment_efficiency": {
                "fulfilled_orders": self._vg_int(fulfillment_summary, "fulfilled_orders"),
                "failed_orders": self._vg_int(fulfillment_summary, "failed_orders"),
                "fulfillment_rate_pct": float(
                    fulfillment_summary["fulfillment_rate_pct"]
                    if "fulfillment_rate_pct" in fulfillment_summary
                    and fulfillment_summary["fulfillment_rate_pct"] is not None
                    else 0.0
                ),
                "failure_rate_pct": float(
                    fulfillment_summary["failure_rate_pct"]
                    if "failure_rate_pct" in fulfillment_summary and fulfillment_summary["failure_rate_pct"] is not None
                    else 0.0
                ),
                "avg_fulfillment_seconds": float(
                    fulfillment_summary["avg_fulfillment_seconds"]
                    if "avg_fulfillment_seconds" in fulfillment_summary
                    and fulfillment_summary["avg_fulfillment_seconds"] is not None
                    else 0.0
                ),
                "p95_fulfillment_seconds": float(
                    fulfillment_summary["p95_fulfillment_seconds"]
                    if "p95_fulfillment_seconds" in fulfillment_summary
                    and fulfillment_summary["p95_fulfillment_seconds"] is not None
                    else 0.0
                ),
            },
            "product_operations": {
                "summary": product_summary,
                "field_state": product_field_state,
                "manual_takeover_count": int(product_summary.get("manual_takeover_count") or len(manual_orders)),
                "manual_takeover_orders": [
                    {
                        "xianyu_order_id": str(item.get("xianyu_order_id") or ""),
                        "fulfillment_status": str(item.get("fulfillment_status") or ""),
                        "reason": str(item.get("reason") or ""),
                    }
                    for item in manual_orders
                ],
            },
            "drill_down": {
                "inspect_endpoint": "/api/virtual-goods/inspect-order",
                "query_key": "order_id",
                "message": "输入订单号查看成品化明细视图。",
                "actions": [
                    {"name": "claim_callback", "enabled": False, "reason": "Dashboard 为只读视图"},
                    {"name": "replay_callback", "enabled": False, "reason": "Dashboard 为只读视图"},
                    {"name": "manual_takeover", "enabled": False, "reason": "Dashboard 为只读视图"},
                ],
            },
        }

    def get_virtual_goods_metrics(self) -> dict[str, Any]:
        service = self._virtual_goods_service()
        query = getattr(service, "get_dashboard_metrics", None)
        if not callable(query):
            return _error_payload(
                "virtual_goods service query `get_dashboard_metrics` is unavailable",
                code="VG_QUERY_NOT_AVAILABLE",
            )

        result = query()
        if not isinstance(result, dict):
            return _error_payload("virtual_goods metrics payload invalid", code="VG_METRICS_INVALID")
        legacy_metrics_payload = not any(
            key in result for key in ("ok", "action", "code", "message", "data", "metrics", "errors", "ts")
        )

        manual_query = getattr(service, "list_manual_takeover_orders", None)
        manual_orders: list[dict[str, Any]] = []
        if callable(manual_query):
            raw_manual = manual_query()
            if isinstance(raw_manual, dict):
                raw_manual = raw_manual.get("data", {}).get("items", [])
            if isinstance(raw_manual, list):
                manual_orders = [x for x in raw_manual if isinstance(x, dict)]

        funnel_result = None
        if callable(getattr(service, "get_funnel_metrics", None)):
            funnel_result = service.get_funnel_metrics(limit=500)

        exception_result = None
        if callable(getattr(service, "list_priority_exceptions", None)):
            exception_result = service.list_priority_exceptions(limit=100, status="open")

        fulfillment_result = None
        if callable(getattr(service, "get_fulfillment_efficiency_metrics", None)):
            fulfillment_result = service.get_fulfillment_efficiency_metrics(limit=500)

        product_result = None
        if callable(getattr(service, "get_product_operation_metrics", None)):
            product_result = service.get_product_operation_metrics(limit=500)

        payload = {
            "success": bool(result.get("ok", True)),
            "module": "virtual_goods",
            "service_response": {
                "ok": bool(result.get("ok", True)),
                "action": str(result.get("action") or "get_dashboard_metrics"),
                "code": str(result.get("code") or "OK"),
                "message": str(result.get("message") or ""),
                "ts": str(result.get("ts") or ""),
            },
            "dashboard_panels": self._build_virtual_goods_dashboard_panels(
                result,
                manual_orders,
                funnel_result,
                exception_result,
                fulfillment_result,
                product_result,
            ),
            "manual_takeover_count": len(manual_orders),
            "generated_at": _now_iso(),
        }
        if legacy_metrics_payload:
            payload["metrics"] = dict(result)
        return payload

    def get_dashboard_readonly_aggregate(self) -> dict[str, Any]:
        """Dashboard 只读聚合接口（运营视图）。"""
        payload = self.get_virtual_goods_metrics()
        if not payload.get("success"):
            return payload

        panels = payload.get("dashboard_panels") if isinstance(payload.get("dashboard_panels"), dict) else {}
        return {
            "success": True,
            "module": "virtual_goods",
            "readonly": True,
            "service_response": payload.get("service_response", {}),
            "sections": {
                "operations_funnel_overview": panels.get("operations_funnel_overview", {}),
                "exception_priority_pool": panels.get("exception_priority_pool", {}),
                "fulfillment_efficiency": panels.get("fulfillment_efficiency", {}),
                "product_operations": panels.get("product_operations", {}),
                "drill_down": panels.get("drill_down", {}),
            },
            "generated_at": payload.get("generated_at") or _now_iso(),
        }

    def inspect_virtual_goods_order(self, order_id: str) -> dict[str, Any]:
        oid = str(order_id or "").strip()
        if not oid:
            return _error_payload("Missing order_id", code="MISSING_ORDER_ID")

        service = self._virtual_goods_service()
        inspect = getattr(service, "inspect_order", None)
        if not callable(inspect):
            return _error_payload(
                "virtual_goods service query `inspect_order` is unavailable",
                code="VG_QUERY_NOT_AVAILABLE",
            )

        try:
            result = inspect(oid)
        except TypeError:
            result = inspect(order_id=oid)
        if not isinstance(result, dict):
            return _error_payload("virtual_goods inspect payload invalid", code="VG_INSPECT_INVALID")

        data = result.get("data") if isinstance(result.get("data"), dict) else result
        order = data.get("order") if isinstance(data.get("order"), dict) else {}
        callbacks_raw = data.get("callbacks") if isinstance(data.get("callbacks"), list) else []
        exception_pool_raw = (
            data.get("exception_priority_pool") if isinstance(data.get("exception_priority_pool"), dict) else {}
        )
        exception_items_raw = (
            exception_pool_raw.get("items") if isinstance(exception_pool_raw.get("items"), list) else []
        )

        callbacks_view = [
            {
                "callback_id": int(cb.get("id") or 0),
                "external_event_id": str(cb.get("external_event_id") or ""),
                "dedupe_key": str(cb.get("dedupe_key") or ""),
                "event_kind": str(cb.get("event_kind") or ""),
                "verify_passed": bool(cb.get("verify_passed")),
                "processed": bool(cb.get("processed")),
                "attempt_count": int(cb.get("attempt_count") or 0),
                "last_process_error": str(cb.get("last_process_error") or ""),
                "created_at": str(cb.get("created_at") or ""),
                "processed_at": str(cb.get("processed_at") or ""),
            }
            for cb in callbacks_raw
            if isinstance(cb, dict)
        ]
        unknown_count = sum(
            1
            for cb in callbacks_view
            if str(cb.get("event_kind") or "").strip().lower() in {"unknown", "unknown_event_kind"}
        )

        callback_chain = [
            {
                "step": idx + 1,
                "event_kind": item.get("event_kind"),
                "verify_passed": item.get("verify_passed"),
                "processed": item.get("processed"),
                "created_at": item.get("created_at"),
                "processed_at": item.get("processed_at"),
            }
            for idx, item in enumerate(callbacks_view)
        ]
        claim_replay_trace = [
            {
                "callback_id": item.get("callback_id"),
                "external_event_id": item.get("external_event_id"),
                "dedupe_key": item.get("dedupe_key"),
                "attempt_count": item.get("attempt_count"),
                "processed": item.get("processed"),
            }
            for item in callbacks_view
        ]
        recent_errors = [
            {
                "callback_id": item.get("callback_id"),
                "error": item.get("last_process_error"),
                "event_kind": item.get("event_kind"),
                "at": item.get("processed_at") or item.get("created_at"),
            }
            for item in callbacks_view
            if str(item.get("last_process_error") or "").strip()
        ][:5]

        exception_items = [x for x in exception_items_raw if isinstance(x, dict)]
        if unknown_count > 0 and not any(
            str(x.get("type") or "").upper() == "UNKNOWN_EVENT_KIND" for x in exception_items
        ):
            exception_items.insert(
                0,
                {
                    "priority": "P0",
                    "type": "UNKNOWN_EVENT_KIND",
                    "count": unknown_count,
                    "summary": "该订单存在 unknown event_kind 回调，已纳入异常池。",
                },
            )

        inspect_payload = {
            "order": order,
            "callbacks": callbacks_raw,
        }
        return {
            "success": bool(result.get("ok", True)),
            "module": "virtual_goods",
            "order_id": oid,
            "inspect": inspect_payload,
            "service_response": {
                "ok": bool(result.get("ok", True)),
                "action": str(result.get("action") or "inspect_order"),
                "code": str(result.get("code") or "OK"),
                "message": str(result.get("message") or ""),
                "ts": str(result.get("ts") or ""),
            },
            "drill_down_view": {
                "order": {
                    "xianyu_order_id": str(order.get("xianyu_order_id") or oid),
                    "order_status": str(order.get("order_status") or ""),
                    "fulfillment_status": str(order.get("fulfillment_status") or ""),
                    "updated_at": str(order.get("updated_at") or ""),
                },
                "current_status": {
                    "xianyu_order_id": str(order.get("xianyu_order_id") or oid),
                    "order_status": str(order.get("order_status") or ""),
                    "fulfillment_status": str(order.get("fulfillment_status") or ""),
                    "updated_at": str(order.get("updated_at") or ""),
                },
                "manual_takeover": {
                    "enabled": bool(order.get("manual_takeover")),
                    "reason": str(order.get("last_error") or ""),
                },
                "callback_chain": callback_chain,
                "claim_replay_trace": claim_replay_trace,
                "recent_errors": recent_errors,
                "exception_priority_pool": {
                    "total_items": len(exception_items),
                    "items": exception_items,
                },
                "actions": [
                    {"name": "claim_callback", "enabled": False, "reason": "只读视图，不支持执行动作"},
                    {"name": "replay_callback", "enabled": False, "reason": "只读视图，不支持执行动作"},
                    {"name": "manual_takeover", "enabled": False, "reason": "只读视图，不支持执行动作"},
                ],
            },
        }

    def get_cookie(self) -> dict[str, Any]:
        cookie = (os.getenv("XIANYU_COOKIE_1", "") or self._get_env_value("XIANYU_COOKIE_1")).strip()
        return {
            "success": bool(cookie),
            "cookie": cookie,
            "length": len(cookie),
        }

    @staticmethod
    def _cookie_fingerprint(cookie_text: str) -> str:
        raw = str(cookie_text or "").strip()
        if not raw:
            return ""
        return hashlib.sha1(raw.encode("utf-8", errors="ignore")).hexdigest()[:16]

    @classmethod
    def _cookie_pairs_to_text(cls, pairs: list[tuple[str, str]]) -> tuple[str, int]:
        items: list[str] = []
        seen: set[str] = set()
        for name, value in pairs:
            key = str(name or "").strip()
            val = str(value or "").strip()
            if not key or not val:
                continue
            if not cls._COOKIE_NAME_RE.fullmatch(key):
                continue
            if key in seen:
                continue
            seen.add(key)
            items.append(f"{key}={val}")
        return "; ".join(items), len(items)

    @classmethod
    def _extract_cookie_pairs_from_json(cls, raw_text: str) -> list[tuple[str, str]]:
        text = str(raw_text or "").strip()
        if not text:
            return []
        try:
            payload = json.loads(text)
        except Exception:
            return []

        pairs: list[tuple[str, str]] = []

        def _collect(items: Any) -> None:
            if not isinstance(items, list):
                return
            for item in items:
                if not isinstance(item, dict):
                    continue
                name = item.get("name") or item.get("key")
                value = item.get("value")
                if name is None or value is None:
                    continue
                pairs.append((str(name), str(value)))

        if isinstance(payload, list):
            _collect(payload)
        elif isinstance(payload, dict):
            if "name" in payload and "value" in payload:
                pairs.append((str(payload.get("name")), str(payload.get("value"))))
            _collect(payload.get("cookies"))
            _collect(payload.get("items"))

        return pairs

    @classmethod
    def _is_allowed_cookie_domain(cls, domain: str) -> bool:
        value = str(domain or "").strip().lower().lstrip(".")
        if not value:
            return True
        return any(value.endswith(allowed) for allowed in cls._COOKIE_DOMAIN_ALLOWLIST)

    @classmethod
    def _extract_cookie_pairs_from_header(cls, raw_text: str) -> list[tuple[str, str]]:
        text = str(raw_text or "").replace("\ufeff", "").replace("\x00", "").strip()
        if not text:
            return []
        text = re.sub(r"^\s*cookie\s*:\s*", "", text, flags=re.IGNORECASE)
        parts = re.split(r";|\n", text)
        pairs: list[tuple[str, str]] = []
        for part in parts:
            seg = str(part or "").strip()
            if not seg or "=" not in seg:
                continue
            key, value = seg.split("=", 1)
            pairs.append((key.strip(), value.strip()))
        return pairs

    @classmethod
    def _extract_cookie_pairs_from_lines(cls, raw_text: str) -> list[tuple[str, str]]:
        text = str(raw_text or "").replace("\ufeff", "").replace("\x00", "")
        pairs: list[tuple[str, str]] = []
        for line in text.splitlines():
            s = str(line or "").strip()
            if not s or s.startswith("#"):
                continue

            # Netscape cookies.txt: domain, flag, path, secure, expiry, name, value
            if "\t" in s:
                cols = [c.strip() for c in s.split("\t") if c.strip()]
                if len(cols) >= 7:
                    if cls._is_allowed_cookie_domain(cols[0]):
                        pairs.append((cols[5], cols[6]))
                    continue
                if len(cols) >= 2 and cls._COOKIE_NAME_RE.fullmatch(cols[0]):
                    # DevTools 表格常见格式：name value domain ...
                    if len(cols) >= 3 and not cls._is_allowed_cookie_domain(cols[2]):
                        continue
                    pairs.append((cols[0], cols[1]))
                    continue

            cols = [c.strip() for c in s.split() if c.strip()]
            if len(cols) >= 2 and cls._COOKIE_NAME_RE.fullmatch(cols[0]):
                pairs.append((cols[0], cols[1]))
                continue

            if "=" in s:
                key, value = s.split("=", 1)
                pairs.append((key.strip(), value.strip()))
        return pairs

    @classmethod
    def parse_cookie_text(cls, text: str) -> dict[str, Any]:
        raw = str(text or "").strip()
        if not raw:
            return {"success": False, "error": "Cookie string cannot be empty"}

        candidates: list[dict[str, Any]] = []
        for source, extractor in (
            ("json", cls._extract_cookie_pairs_from_json),
            ("header", cls._extract_cookie_pairs_from_header),
            ("table_or_netscape", cls._extract_cookie_pairs_from_lines),
        ):
            cookie_text, count = cls._cookie_pairs_to_text(extractor(raw))
            if count > 0 and cookie_text:
                candidates.append({"format": source, "cookie": cookie_text, "count": count})

        if not candidates:
            return {
                "success": False,
                "error": "Unable to parse cookie text. Please use header/json/cookies.txt format.",
            }

        candidates.sort(key=lambda x: (int(x.get("count", 0)), x.get("format") == "header"), reverse=True)
        best = candidates[0]
        cookie_text = str(best["cookie"])
        count = int(best["count"])
        missing_required = [k for k in cls._COOKIE_REQUIRED_KEYS if f"{k}=" not in cookie_text]
        return {
            "success": True,
            "cookie": cookie_text,
            "length": len(cookie_text),
            "cookie_items": count,
            "detected_format": str(best["format"]),
            "missing_required": missing_required,
        }

    def _recovery_stage_label(self, stage: str) -> str:
        mapping = {
            "healthy": "链路正常",
            "token_error": "鉴权异常",
            "waiting_cookie_update": "等待更新 Cookie",
            "waiting_reconnect": "等待重连",
            "recover_triggered": "已触发自动恢复",
            "inactive": "服务未运行",
            "monitoring": "监控中",
        }
        key = str(stage or "").strip().lower()
        return mapping.get(key, "状态未知")

    def _is_cookie_cloud_configured(self) -> bool:
        sys_cfg = _read_system_config()
        cc_cfg = sys_cfg.get("cookie_cloud", {}) if isinstance(sys_cfg.get("cookie_cloud"), dict) else {}
        return bool(cc_cfg.get("cookie_cloud_uuid") and cc_cfg.get("cookie_cloud_password"))

    def _recovery_advice(self, stage: str, token_error: str | None = None) -> str:
        s = str(stage or "").strip().lower()
        t = str(token_error or "").strip().upper()
        cc = self._is_cookie_cloud_configured()
        slider_cfg = get_config().get_section("messages", {}).get("ws", {}).get("slider_auto_solve", {})
        slider_auto = bool(slider_cfg.get("enabled", False)) if isinstance(slider_cfg, dict) else False
        if s == "recover_triggered":
            return "已触发售前恢复，建议等待 5-20 秒后刷新状态。"
        if s == "waiting_reconnect":
            return "Cookie 已更新但尚未连通，可点击“售前一键恢复”立即重试。"
        if s == "waiting_cookie_update":
            if t == "FAIL_SYS_USER_VALIDATE":
                if cc:
                    return "请在闲鱼网页重新登录，CookieCloud 会自动同步新 Cookie，系统将秒级自动恢复。"
                return "请在闲鱼网页重新登录后导出最新 Cookie，再执行“售前一键恢复”。"
            if t in ("RGV587", "RGV587_SERVER_BUSY"):
                if slider_auto:
                    return (
                        "触发平台风控（RGV587），系统正在自动尝试滑块验证...\n"
                        "如自动验证失败，会弹出浏览器窗口，请手动完成滑块拖动。\n"
                        + (
                            "CookieCloud 即时同步已启用，验证后秒级恢复。"
                            if cc
                            else "验证后请手动复制 Cookie 粘贴保存。"
                        )
                    )
                if cc:
                    return (
                        "触发平台风控（RGV587），请按以下步骤操作：\n"
                        "1. 在浏览器打开 goofish.com/im（闲鱼消息页）\n"
                        "2. 完成滑块验证\n"
                        "3. 在 CookieCloud 扩展中点「手动同步」立即生效\n"
                        "系统将秒级自动恢复（CookieCloud 即时同步已启用）。\n"
                        "提示：在「系统设置 → 集成服务」中开启自动滑块验证可实现全自动恢复。"
                    )
                return (
                    "触发平台风控（RGV587），请按以下步骤操作：\n"
                    "1. 在浏览器打开 goofish.com/im（闲鱼消息页）\n"
                    "2. 完成滑块验证\n"
                    "3. 按 F12 → Network → 复制任意请求的 Cookie\n"
                    "4. 粘贴到本页面的「手动粘贴 Cookie」区域并保存\n"
                    "5. 点击“售前一键恢复”\n"
                    "提示：配置 CookieCloud 可实现滑块验证后秒级自动恢复，无需手动复制。"
                )
            if cc:
                return "请更新 Cookie 后等待 CookieCloud 自动同步，系统将秒级自动恢复。"
            return "请更新 Cookie 后重试恢复。"
        if s == "token_error":
            if t == "WS_HTTP_400":
                return "连接通道异常，请先点“售前一键恢复”；若持续失败再更新 Cookie。"
            if t in ("RGV587", "RGV587_SERVER_BUSY"):
                if slider_auto:
                    return "触发平台风控，系统正在自动尝试滑块验证。" + (
                        " CookieCloud 即时同步已启用，验证后秒级恢复。" if cc else ""
                    )
                if cc:
                    return (
                        "触发平台风控，请在浏览器打开 goofish.com/im 完成滑块验证，"
                        "在 CookieCloud 扩展中点「手动同步」，系统将秒级自动恢复。"
                    )
                return (
                    "触发平台风控，请在闲鱼网页版打开「消息」页面通过滑块验证后，"
                    "手动复制 Cookie 并粘贴保存（F12 → Network → Cookie），然后执行“售前一键恢复”。\n"
                    "提示：配置 CookieCloud 可实现验证后秒级自动恢复。"
                )
            return "存在鉴权错误，建议更新 Cookie 后重连。"
        if s == "inactive":
            return "服务未运行，请先在首页启动服务。"
        if s == "healthy":
            return "当前链路可用，可正常自动回复。"
        return "监控中，请刷新状态查看最新结果。"

    def _trigger_presales_recover_after_cookie_update(self, cookie_text: str) -> dict[str, Any]:
        cookie_fp = self._cookie_fingerprint(cookie_text)
        if not cookie_fp:
            return {"triggered": False, "message": "cookie_empty"}

        result = self.module_console.control(action="recover", target="presales")
        has_error = bool(result.get("error")) if isinstance(result, dict) else True
        now = _now_iso()
        with self._recover_lock:
            self._last_auto_recover_cookie_fp = cookie_fp
            self._last_auto_recover_at = now
            self._last_auto_recover_result = result if isinstance(result, dict) else {}
            self._last_cookie_fp = cookie_fp
        return {
            "triggered": not has_error,
            "result": result,
            "at": now,
            "message": "recover_ok" if not has_error else "recover_failed",
        }

    def update_cookie(self, cookie: str, *, auto_recover: bool = False) -> dict[str, Any]:
        parsed = self.parse_cookie_text(str(cookie or ""))
        if not parsed.get("success"):
            return parsed
        cookie_text = str(parsed.get("cookie") or "").strip()
        if not cookie_text:
            return {"success": False, "error": "Cookie string cannot be empty"}
        self._set_env_value("XIANYU_COOKIE_1", cookie_text)
        diagnosis = self.diagnose_cookie(cookie_text)
        payload: dict[str, Any] = {
            "success": True,
            "message": "Cookie updated",
            "length": len(cookie_text),
            "cookie_items": int(parsed.get("cookie_items", 0) or 0),
            "detected_format": str(parsed.get("detected_format") or "header"),
            "missing_required": parsed.get("missing_required", []),
            "cookie_grade": diagnosis.get("grade", "未知"),
            "cookie_actions": diagnosis.get("actions", []),
            "cookie_diagnosis": diagnosis,
        }
        try:
            from src.modules.messages.ws_live import notify_ws_cookie_changed

            notify_ws_cookie_changed()
        except Exception:
            pass

        should_recover = auto_recover and str(diagnosis.get("grade") or "") != "不可用"
        if should_recover:
            recover = self._trigger_presales_recover_after_cookie_update(cookie_text)
            payload["auto_recover"] = recover
            if recover.get("triggered"):
                payload["message"] = "Cookie updated and presales recovery triggered"
            else:
                payload["message"] = "Cookie updated, but presales recovery failed"
        return payload

    @classmethod
    def _cookie_domain_filter_stats(cls, raw_text: str) -> dict[str, Any]:
        text = str(raw_text or "").replace("\ufeff", "").replace("\x00", "")
        checked = 0
        rejected = 0
        samples: list[str] = []

        def _check_domain(domain: str) -> None:
            nonlocal checked, rejected
            dom = str(domain or "").strip().lower()
            if not dom:
                return
            checked += 1
            if not cls._is_allowed_cookie_domain(dom):
                rejected += 1
                if len(samples) < 5:
                    samples.append(dom)

        # 文本行（Netscape / 表格）
        for line in text.splitlines():
            s = str(line or "").strip()
            if not s or s.startswith("#"):
                continue
            if "\t" not in s:
                continue
            cols = [c.strip() for c in s.split("\t") if c.strip()]
            if len(cols) >= 7:
                _check_domain(cols[0])
            elif len(cols) >= 3:
                _check_domain(cols[2])

        # JSON 结构中的 domain 字段
        try:
            payload = json.loads(text)
        except Exception:
            payload = None
        if payload is not None:
            queue: list[Any] = [payload]
            while queue:
                item = queue.pop()
                if isinstance(item, dict):
                    if "domain" in item:
                        _check_domain(str(item.get("domain") or ""))
                    for v in item.values():
                        if isinstance(v, (dict, list)):
                            queue.append(v)
                elif isinstance(item, list):
                    queue.extend(item)

        return {
            "allowlist": list(cls._COOKIE_DOMAIN_ALLOWLIST),
            "checked": checked,
            "rejected": rejected,
            "applied": True,
            "rejected_samples": samples,
        }

    def diagnose_cookie(self, cookie_text: str) -> dict[str, Any]:
        raw = str(cookie_text or "").strip()
        if not raw:
            return {
                "success": False,
                "grade": "不可用",
                "error": "Cookie text is empty",
                "actions": ["请先粘贴 Cookie 文本，或上传插件导出的 cookies 文件。"],
            }

        parsed = self.parse_cookie_text(raw)
        domain_filter = self._cookie_domain_filter_stats(raw)
        if not parsed.get("success"):
            return {
                "success": False,
                "grade": "不可用",
                "error": str(parsed.get("error") or "解析失败"),
                "domain_filter": domain_filter,
                "actions": [
                    "请使用 headers/json/cookies.txt 任一格式重试。",
                    "建议在登录闲鱼后立即导出 Cookie，再上传。",
                ],
            }

        normalized = str(parsed.get("cookie") or "")
        cookie_map = {k: v for k, v in self._extract_cookie_pairs_from_header(normalized)}
        required_all = [*list(self._COOKIE_REQUIRED_KEYS), "_m_h5_tk", "_m_h5_tk_enc"]
        required_present = [k for k in required_all if k in cookie_map]
        required_missing = [k for k in required_all if k not in cookie_map]
        recommended_present = [k for k in self._COOKIE_RECOMMENDED_KEYS if k in cookie_map]
        recommended_missing = [k for k in self._COOKIE_RECOMMENDED_KEYS if k not in cookie_map]
        critical_missing = [k for k in self._COOKIE_REQUIRED_KEYS if k in required_missing]
        session_missing = [k for k in ("_m_h5_tk", "_m_h5_tk_enc") if k in required_missing]

        length = int(parsed.get("length", 0) or 0)
        cookie_items = int(parsed.get("cookie_items", 0) or 0)
        m_h5_tk_ttl = self._parse_m_h5_tk_ttl(cookie_map.get("_m_h5_tk", ""))
        m_h5_tk_expired = m_h5_tk_ttl is not None and m_h5_tk_ttl <= 0
        m_h5_tk_expiring_soon = m_h5_tk_ttl is not None and 0 < m_h5_tk_ttl < 900

        grade = "可用"
        if critical_missing or cookie_items < 4:
            grade = "不可用"
        elif m_h5_tk_expired:
            grade = "不可用"
        elif session_missing or length < 80:
            grade = "高风险"
        elif m_h5_tk_expiring_soon:
            grade = "高风险"
        elif len(recommended_missing) >= 2:
            grade = "高风险"

        actions: list[str] = []
        if critical_missing:
            actions.append(f"缺少关键字段：{', '.join(critical_missing)}，请重新登录后导出完整 Cookie。")
        if m_h5_tk_expired:
            actions.append("_m_h5_tk 已过期，请在闲鱼网页版刷新页面后重新导出 Cookie。")
        elif m_h5_tk_expiring_soon:
            ttl_min = int((m_h5_tk_ttl or 0) / 60)
            actions.append(f"_m_h5_tk 将在 {ttl_min} 分钟内过期，建议尽快刷新页面重新导出 Cookie。")
        if session_missing:
            actions.append("缺少 _m_h5_tk/_m_h5_tk_enc，建议刷新页面后重新导出。")
        if domain_filter.get("rejected", 0):
            actions.append("检测到非 goofish 域 Cookie，系统已自动过滤。")
        if recommended_missing:
            actions.append(
                "缺少会话增强字段："
                + ", ".join(recommended_missing)
                + "；建议在插件中使用 Export All Cookies（全量导出）后重试。"
            )
        if grade == "可用":
            actions.append("可直接保存并在首页执行“售前一键恢复”。")

        result: dict[str, Any] = {
            "success": True,
            "grade": grade,
            "detected_format": str(parsed.get("detected_format") or "unknown"),
            "length": length,
            "cookie_items": cookie_items,
            "required_present": required_present,
            "required_missing": required_missing,
            "recommended_present": recommended_present,
            "recommended_missing": recommended_missing,
            "domain_filter": domain_filter,
            "actions": actions,
        }
        if m_h5_tk_ttl is not None:
            result["m_h5_tk_ttl_seconds"] = round(m_h5_tk_ttl)
        return result

    @staticmethod
    def _parse_m_h5_tk_ttl(raw: str) -> float | None:
        """Parse _m_h5_tk value ({hex}_{epoch_ms}) and return seconds until expiry."""
        parts = str(raw or "").split("_")
        if len(parts) < 2:
            return None
        try:
            expire_ms = int(parts[1])
            return (expire_ms / 1000.0) - time.time()
        except (ValueError, OverflowError):
            return None

    @classmethod
    def _is_cookie_import_file(cls, filename: str) -> bool:
        suffix = Path(filename).suffix.lower()
        if suffix in cls._COOKIE_IMPORT_EXTS:
            return True
        # 一些插件/工具导出的文件无后缀（如 `cookies`），允许走内容识别。
        return suffix == "" and bool(Path(filename).name)

    @classmethod
    def _looks_like_cookie_plugin_bundle(cls, member_names: list[str]) -> bool:
        names = [str(name or "").replace("\\", "/").strip().lower() for name in member_names if str(name or "").strip()]
        if not names:
            return False

        if any("get-cookies.txt-locally/src/manifest.json" in item for item in names):
            return True

        basenames = {Path(item).name for item in names}
        has_manifest = "manifest.json" in basenames
        has_popup = "popup.mjs" in basenames or "popup.js" in basenames
        has_background = "background.mjs" in basenames or "background.js" in basenames
        if has_manifest and (has_popup or has_background):
            return True

        # 插件源码常见特征文件，manifest + 任一特征可判定为安装包而非导出 cookie。
        plugin_markers = (
            "get-cookies.txt-locally",
            "cookie_format.mjs",
            "get_all_cookies.mjs",
            "save_to_file.mjs",
            "popup-options.css",
        )
        if has_manifest and any(any(marker in item for marker in plugin_markers) for item in names):
            return True
        return False

    @classmethod
    def _cookie_hint_hit_keys(cls, cookie_text: str) -> list[str]:
        text = str(cookie_text or "")
        hits = [k for k in cls._COOKIE_HINT_KEYS if f"{k}=" in text]
        return hits

    @classmethod
    def _score_cookie_candidate(cls, payload: dict[str, Any]) -> tuple[int, int, int]:
        missing = payload.get("missing_required")
        missing_count = len(missing) if isinstance(missing, list) else len(cls._COOKIE_REQUIRED_KEYS)
        required_hit = max(0, len(cls._COOKIE_REQUIRED_KEYS) - missing_count)
        cookie_items = int(payload.get("cookie_items", 0) or 0)
        length = int(payload.get("length", 0) or 0)
        return required_hit, cookie_items, length

    def import_cookie_plugin_files(
        self, files: list[tuple[str, bytes]], *, auto_recover: bool = False
    ) -> dict[str, Any]:
        if not files:
            return {"success": False, "error": "No files uploaded"}

        candidates: list[dict[str, Any]] = []
        imported_files: list[str] = []
        skipped_files: list[str] = []
        details: list[str] = []
        plugin_bundle_detected = False

        def _collect_text_candidate(source_name: str, raw: bytes) -> None:
            text = self._decode_text_bytes(raw)
            parsed = self.parse_cookie_text(text)
            if not parsed.get("success"):
                skipped_files.append(source_name)
                details.append(f"{source_name} -> {parsed.get('error', 'parse failed')}")
                return
            hit_keys = self._cookie_hint_hit_keys(str(parsed.get("cookie") or ""))
            if not hit_keys:
                skipped_files.append(source_name)
                details.append(f"{source_name} -> parsed but missing known keys ({', '.join(self._COOKIE_HINT_KEYS)})")
                return

            candidates.append(
                {
                    "source_file": source_name,
                    "parsed": parsed,
                    "hit_keys": hit_keys,
                }
            )
            imported_files.append(source_name)

        for filename, content in files:
            file_name = str(filename or "").strip()
            suffix = Path(file_name).suffix.lower()

            if suffix == ".zip":
                try:
                    with zipfile.ZipFile(io.BytesIO(content), mode="r") as zf:
                        member_names = [str(info.filename or "") for info in zf.infolist()]
                        if self._looks_like_cookie_plugin_bundle(member_names):
                            plugin_bundle_detected = True
                        for info in zf.infolist():
                            if info.is_dir():
                                continue
                            repaired_name = self._repair_zip_name(info.filename)
                            member_name = Path(repaired_name).name
                            if not member_name:
                                continue
                            if "__MACOSX" in repaired_name or member_name.startswith("._"):
                                skipped_files.append(f"{file_name}:{repaired_name}")
                                continue
                            if not self._is_cookie_import_file(member_name):
                                skipped_files.append(f"{file_name}:{repaired_name}")
                                continue
                            try:
                                raw = zf.read(info)
                                if not raw:
                                    skipped_files.append(f"{file_name}:{repaired_name}")
                                    details.append(f"{file_name}:{repaired_name} -> empty file")
                                    continue
                                _collect_text_candidate(f"{file_name}:{member_name}", raw)
                            except Exception as exc:
                                skipped_files.append(f"{file_name}:{repaired_name}")
                                details.append(f"{file_name}:{repaired_name} -> {exc}")
                except zipfile.BadZipFile:
                    skipped_files.append(file_name)
                    details.append(f"{file_name} -> invalid zip file")
                except Exception as exc:
                    skipped_files.append(file_name)
                    details.append(f"{file_name} -> {exc}")
                continue

            if not self._is_cookie_import_file(file_name):
                skipped_files.append(file_name)
                continue
            _collect_text_candidate(file_name, content)

        if not candidates:
            if plugin_bundle_detected:
                return {
                    "success": False,
                    "error": "Detected plugin installation bundle, not exported cookies.",
                    "hint": "请先在浏览器安装插件并导出 cookies.txt/JSON，再上传导出文件。",
                    "imported_files": imported_files,
                    "skipped_files": skipped_files,
                    "details": details,
                }
            return {
                "success": False,
                "error": "No valid cookie content found in uploaded files.",
                "imported_files": imported_files,
                "skipped_files": skipped_files,
                "details": details,
            }

        best = max(candidates, key=lambda item: self._score_cookie_candidate(item["parsed"]))
        parsed = dict(best.get("parsed", {}))
        cookie_text = str(parsed.get("cookie") or "").strip()
        if not cookie_text:
            return {
                "success": False,
                "error": "Parsed cookie is empty.",
                "imported_files": imported_files,
                "skipped_files": skipped_files,
                "details": details,
            }

        self._set_env_value("XIANYU_COOKIE_1", cookie_text)
        try:
            from src.modules.messages.ws_live import notify_ws_cookie_changed

            notify_ws_cookie_changed()
        except Exception:
            pass
        diagnosis = self.diagnose_cookie(cookie_text)
        payload: dict[str, Any] = {
            "success": True,
            "message": "Cookie imported from plugin export",
            "source_file": str(best.get("source_file") or ""),
            "cookie": cookie_text,
            "length": int(parsed.get("length", 0) or 0),
            "cookie_items": int(parsed.get("cookie_items", 0) or 0),
            "detected_format": str(parsed.get("detected_format") or "unknown"),
            "missing_required": parsed.get("missing_required", []),
            "imported_files": imported_files,
            "skipped_files": skipped_files,
            "details": details,
            "cookie_grade": diagnosis.get("grade", "未知"),
            "cookie_actions": diagnosis.get("actions", []),
            "cookie_diagnosis": diagnosis,
            "recognized_key_hits": best.get("hit_keys", []),
        }
        should_recover = auto_recover and str(diagnosis.get("grade") or "") != "不可用"
        if should_recover:
            recover = self._trigger_presales_recover_after_cookie_update(cookie_text)
            payload["auto_recover"] = recover
            if recover.get("triggered"):
                payload["message"] = "Cookie imported and presales recovery triggered"
            else:
                payload["message"] = "Cookie imported, but presales recovery failed"
        return payload

    def export_cookie_plugin_bundle(self) -> tuple[bytes, str]:
        base = self.cookie_plugin_dir
        src_dir = base / "src"
        if not base.exists() or not src_dir.exists():
            raise FileNotFoundError("Bundled plugin source not found under third_party/Get-cookies.txt-LOCALLY")

        include_paths = [
            "src",
            "LICENSE",
            "README.upstream.md",
            "privacy-policy.upstream.md",
            "SOURCE_INFO.txt",
        ]

        buf = io.BytesIO()
        with zipfile.ZipFile(buf, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
            for rel in include_paths:
                target = base / rel
                if not target.exists():
                    continue
                if target.is_file():
                    zf.write(target, arcname=f"Get-cookies.txt-LOCALLY/{rel}")
                    continue
                for fp in target.rglob("*"):
                    if not fp.is_file():
                        continue
                    arc = f"Get-cookies.txt-LOCALLY/{fp.relative_to(base).as_posix()}"
                    zf.write(fp, arcname=arc)

        filename = "Get-cookies.txt-LOCALLY_bundle.zip"
        return buf.getvalue(), filename

    def _quote_dir(self) -> Path:
        cfg = get_config().get_section("quote", {})
        table_dir = str(cfg.get("cost_table_dir", "data/quote_costs"))
        path = Path(table_dir)
        if not path.is_absolute():
            path = self.project_root / path
        path.mkdir(parents=True, exist_ok=True)
        return path

    _route_stats_cache: dict[str, Any] | None = None
    _route_stats_mtime: float = 0.0
    _route_stats_ts: float = 0.0
    _ROUTE_STATS_TTL: float = 120.0
    _route_stats_lock = threading.Lock()

    def route_stats(self) -> dict[str, Any]:
        now = time.time()
        if self._route_stats_cache is not None and (now - self._route_stats_ts) < self._ROUTE_STATS_TTL:
            return self._route_stats_cache

        if not self._route_stats_lock.acquire(blocking=True, timeout=30):
            if self._route_stats_cache is not None:
                return self._route_stats_cache
            return {"success": True, "stats": {}}

        try:
            if self._route_stats_cache is not None and (time.time() - self._route_stats_ts) < self._ROUTE_STATS_TTL:
                return self._route_stats_cache

            cfg = get_config().get_section("quote", {})
            patterns = cfg.get("cost_table_patterns", ["*.xlsx", "*.xls", "*.csv"])
            if not isinstance(patterns, list):
                patterns = ["*.xlsx", "*.xls", "*.csv"]
            for required in ("*.xlsx", "*.xls", "*.csv"):
                if required not in patterns:
                    patterns.append(required)
            quote_dir = self._quote_dir()
            files = []
            latest_mtime = 0.0
            for pattern in patterns:
                for fp in quote_dir.glob(str(pattern)):
                    if fp.is_file():
                        files.append(fp)
                        latest_mtime = max(latest_mtime, fp.stat().st_mtime)

            route_count = 0
            courier_set: set[str] = set()
            courier_details: dict[str, int] = {}
            parse_errors: list[str] = []

            try:
                repo = CostTableRepository(table_dir=quote_dir)
                repo._reload_if_needed()
                records = repo._records
                route_count += len(records)
                for rec in records:
                    courier = str(getattr(rec, "courier", "") or "").strip()
                    if not courier:
                        continue
                    courier_set.add(courier)
                    courier_details[courier] = int(courier_details.get(courier, 0) or 0) + 1
            except Exception as exc:
                parse_errors.append(f"quote_costs: {exc}")

            last_updated = "-"
            if latest_mtime > 0:
                last_updated = datetime.fromtimestamp(latest_mtime).strftime("%Y-%m-%d %H:%M:%S")

            stats = {
                "couriers": len(courier_set),
                "routes": int(route_count),
                "tables": len(set(files)),
                "last_updated": last_updated,
                "courier_details": dict(sorted(courier_details.items(), key=lambda x: x[0])),
                "files": [str(p.name) for p in sorted(set(files))[:200]],
            }
            if parse_errors:
                stats["parse_error"] = " | ".join(parse_errors[:5])
            result = {"success": True, "stats": stats}
            self._route_stats_cache = result
            self._route_stats_mtime = latest_mtime
            self._route_stats_ts = time.time()
            return result
        finally:
            self._route_stats_lock.release()

    def _workflow_db_path(self) -> Path:
        messages_cfg = get_config().get_section("messages", {})
        workflow_cfg = messages_cfg.get("workflow", {}) if isinstance(messages_cfg.get("workflow"), dict) else {}
        raw = str(workflow_cfg.get("db_path", "data/workflow.db") or "data/workflow.db")
        path = Path(raw)
        if not path.is_absolute():
            path = self.project_root / path
        return path

    def get_unmatched_message_stats(self, max_lines: int = 3000, top_n: int = 10) -> dict[str, Any]:
        """统计 data/unmatched_messages.jsonl 的高频词与趋势。"""
        from collections import Counter

        path = self.project_root / "data" / "unmatched_messages.jsonl"
        if not path.exists():
            return {
                "ok": True,
                "total_count": 0,
                "top_keywords": [],
                "daily_counts": [],
            }
        lines: list[str] = []
        try:
            with open(path, encoding="utf-8") as f:
                for line in f:
                    lines.append(line)
                    if len(lines) > max_lines:
                        lines.pop(0)
        except Exception as exc:
            logger.warning("unmatched_messages read failed: %s", exc)
            return {"ok": False, "error": str(exc), "total_count": 0, "top_keywords": [], "daily_counts": []}
        total = len(lines)
        msgs: list[str] = []
        daily: dict[str, int] = {}
        for line in lines:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
                msg = (obj.get("msg") or "").strip()
                if msg:
                    msgs.append(msg)
                ts = obj.get("ts", "")
                if ts:
                    day = ts[:10]
                    daily[day] = daily.get(day, 0) + 1
            except Exception:
                continue
        counter: Counter[str] = Counter()
        for msg in msgs:
            for seg in re.findall(r"[\u4e00-\u9fa5]{2,4}", msg):
                if len(seg) >= 2:
                    counter[seg] += 1
            for part in re.split(r"[，。！？、；：\s]+", msg):
                part = part.strip()
                if part and len(part) >= 2 and not part.isdigit():
                    counter[part] += 1
        top_keywords = [{"word": w, "count": c} for w, c in counter.most_common(top_n)]
        daily_counts = [{"date": d, "count": daily[d]} for d in sorted(daily.keys(), reverse=True)[:14]]
        return {
            "ok": True,
            "total_count": total,
            "top_keywords": top_keywords,
            "daily_counts": daily_counts,
        }

    def _query_message_stats_from_workflow(self) -> dict[str, Any] | None:
        db_path = self._workflow_db_path()
        if not db_path.exists():
            return None

        reply_states = ("REPLIED", "QUOTED")
        ok_status = ("success", "forced")
        try:
            with closing(sqlite3.connect(db_path)) as conn:
                conn.row_factory = sqlite3.Row
                conn.execute("PRAGMA journal_mode=WAL")
                conn.execute("PRAGMA busy_timeout=5000")

                total_replied = int(
                    conn.execute(
                        """
                        SELECT COUNT(DISTINCT session_id) AS c
                        FROM session_state_transitions
                        WHERE status IN (?, ?)
                          AND to_state IN (?, ?)
                        """,
                        (ok_status[0], ok_status[1], reply_states[0], reply_states[1]),
                    ).fetchone()["c"]
                )

                today_replied = int(
                    conn.execute(
                        """
                        SELECT COUNT(DISTINCT session_id) AS c
                        FROM session_state_transitions
                        WHERE status IN (?, ?)
                          AND to_state IN (?, ?)
                          AND date(datetime(created_at), 'localtime') = date('now', 'localtime')
                          AND session_id IN (
                              SELECT session_id FROM session_tasks
                              WHERE date(datetime(created_at), 'localtime') = date('now', 'localtime')
                          )
                        """,
                        (ok_status[0], ok_status[1], reply_states[0], reply_states[1]),
                    ).fetchone()["c"]
                )

                recent_replied = int(
                    conn.execute(
                        """
                        SELECT COUNT(DISTINCT session_id) AS c
                        FROM session_state_transitions
                        WHERE status IN (?, ?)
                          AND to_state IN (?, ?)
                          AND datetime(created_at) >= datetime('now', '-60 minutes')
                        """,
                        (ok_status[0], ok_status[1], reply_states[0], reply_states[1]),
                    ).fetchone()["c"]
                )

                total_conversations = int(conn.execute("SELECT COUNT(*) AS c FROM session_tasks").fetchone()["c"])
                today_conversations = int(
                    conn.execute(
                        """SELECT COUNT(*) AS c FROM session_tasks
                           WHERE date(datetime(created_at), 'localtime') = date('now', 'localtime')""",
                    ).fetchone()["c"]
                )
                total_messages = int(conn.execute("SELECT COUNT(*) AS c FROM workflow_jobs").fetchone()["c"])

                hourly_rows = conn.execute(
                    """
                    SELECT strftime('%H', datetime(created_at), 'localtime') AS h, COUNT(*) AS c
                    FROM session_state_transitions
                    WHERE status IN (?, ?)
                      AND to_state IN (?, ?)
                      AND datetime(created_at) >= datetime('now', '-24 hours')
                    GROUP BY h
                    """,
                    (ok_status[0], ok_status[1], reply_states[0], reply_states[1]),
                ).fetchall()

                daily_rows = conn.execute(
                    """
                    SELECT strftime('%Y-%m-%d', datetime(created_at), 'localtime') AS d, COUNT(*) AS c
                    FROM session_state_transitions
                    WHERE status IN (?, ?)
                      AND to_state IN (?, ?)
                      AND date(datetime(created_at), 'localtime') >= date('now', 'localtime', '-6 days')
                    GROUP BY d
                    """,
                    (ok_status[0], ok_status[1], reply_states[0], reply_states[1]),
                ).fetchall()

            hourly = {str(r["h"]): int(r["c"]) for r in hourly_rows if r["h"] is not None}
            daily = {str(r["d"]): int(r["c"]) for r in daily_rows if r["d"] is not None}
            return {
                "total_replied": total_replied,
                "today_replied": today_replied,
                "recent_replied": recent_replied,
                "total_conversations": total_conversations,
                "today_conversations": today_conversations,
                "total_messages": total_messages,
                "hourly_replies": hourly,
                "daily_replies": daily,
            }
        except Exception:
            return None

    @staticmethod
    def _safe_filename(name: str) -> str:
        base_name = Path(str(name or "")).name
        ext = Path(base_name).suffix.lower()
        stem_raw = Path(base_name).stem
        stem = re.sub(r"[^0-9A-Za-z_\-\u4e00-\u9fa5]+", "_", stem_raw).strip("_-")
        if not stem:
            stem = f"upload_{int(time.time())}"
        if ext not in MimicOps._ROUTE_FILE_EXTS:
            ext = ".xlsx"
        return f"{stem}{ext}"

    @staticmethod
    def _repair_zip_name(name: str) -> str:
        raw = str(name or "")
        if not raw:
            return raw
        try:
            return raw.encode("cp437").decode("utf-8")
        except Exception:
            pass
        for enc in ("gbk", "gb18030", "big5"):
            try:
                return raw.encode("cp437").decode(enc)
            except Exception:
                continue
        return raw

    @classmethod
    def _is_route_table_file(cls, filename: str) -> bool:
        return Path(filename).suffix.lower() in cls._ROUTE_FILE_EXTS

    def _save_route_content(self, quote_dir: Path, filename: str, content: bytes) -> str:
        base_name = Path(filename).name
        clean = self._safe_filename(base_name)
        if not self._is_route_table_file(clean):
            raise ValueError(f"Unsupported file type: {base_name}")

        target = quote_dir / clean
        if target.exists():
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            candidate = quote_dir / f"{target.stem}_{ts}{target.suffix}"
            idx = 1
            while candidate.exists():
                idx += 1
                candidate = quote_dir / f"{target.stem}_{ts}_{idx}{target.suffix}"
            target = candidate
        target.write_bytes(content)
        return target.name

    def import_route_files(self, files: list[tuple[str, bytes]]) -> dict[str, Any]:
        if not files:
            return {"success": False, "error": "No files uploaded"}
        quote_dir = self._quote_dir()
        saved: list[str] = []
        skipped: list[str] = []
        errors: list[str] = []
        zip_count = 0
        for filename, content in files:
            file_name = str(filename or "").strip()
            suffix = Path(file_name).suffix.lower()

            if suffix == ".zip":
                zip_count += 1
                try:
                    with zipfile.ZipFile(io.BytesIO(content), mode="r") as zf:
                        for info in zf.infolist():
                            if info.is_dir():
                                continue
                            repaired_name = self._repair_zip_name(info.filename)
                            member_name = Path(repaired_name).name
                            if not member_name:
                                continue
                            if "__MACOSX" in repaired_name or member_name.startswith("._"):
                                skipped.append(repaired_name)
                                continue
                            if not self._is_route_table_file(member_name):
                                skipped.append(repaired_name)
                                continue
                            try:
                                data = zf.read(info)
                                saved_name = self._save_route_content(quote_dir, member_name, data)
                                saved.append(saved_name)
                            except Exception as exc:
                                skipped.append(repaired_name)
                                errors.append(f"{file_name}:{repaired_name} -> {exc}")
                except zipfile.BadZipFile:
                    skipped.append(file_name)
                    errors.append(f"{file_name} -> invalid zip file")
                except Exception as exc:
                    skipped.append(file_name)
                    errors.append(f"{file_name} -> {exc}")
                continue

            if self._is_route_table_file(file_name):
                try:
                    saved_name = self._save_route_content(quote_dir, file_name, content)
                    saved.append(saved_name)
                except Exception as exc:
                    skipped.append(file_name)
                    errors.append(f"{file_name} -> {exc}")
            else:
                skipped.append(file_name)

        if not saved:
            return {
                "success": False,
                "error": "No supported route files found. Use .xlsx/.xls/.csv or a .zip containing them.",
                "skipped_files": skipped,
                "details": errors,
            }

        stats = self.route_stats().get("stats", {})
        self._cost_table_repo = None
        message = f"Imported {len(saved)} file(s)"
        if zip_count > 0:
            message += f" from {zip_count} zip archive(s)"
        return {
            "success": True,
            "message": message,
            "saved_files": saved,
            "skipped_files": skipped,
            "details": errors,
            "stats": stats,
        }

    def export_routes_zip(self) -> tuple[bytes, str]:
        quote_dir = self._quote_dir()
        files = sorted([*quote_dir.glob("*.xlsx"), *quote_dir.glob("*.xls"), *quote_dir.glob("*.csv")])
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
            for fp in files:
                zf.write(fp, arcname=fp.name)
        filename = f"routes_export_{datetime.now().strftime('%Y%m%d')}.zip"
        return buf.getvalue(), filename

    def reset_database(self, db_type: str) -> dict[str, Any]:
        target = str(db_type or "all").strip().lower()
        result: dict[str, Any] = {"success": True, "results": {}}

        if target in {"routes", "all"}:
            quote_dir = self._quote_dir()
            deleted = 0
            for fp in [*quote_dir.glob("*.xlsx"), *quote_dir.glob("*.xls"), *quote_dir.glob("*.csv")]:
                fp.unlink(missing_ok=True)
                deleted += 1
            result["results"]["routes"] = {"message": f"Deleted {deleted} cost table files"}
            self._cost_table_repo = None

        if target in {"chat", "all"}:
            removed: list[str] = []
            for rel in ("data/workflow.db", "data/message_workflow_state.json", "data/messages_followup_state.json"):
                p = self.project_root / rel
                if p.exists():
                    p.unlink()
                    removed.append(rel)
            result["results"]["chat"] = {"message": f"Removed {len(removed)} chat workflow file(s)", "files": removed}

        return result

    @property
    def template_path(self) -> Path:
        return self.project_root / "config" / "templates" / "reply_templates.json"

    def get_template(self, default: bool = False) -> dict[str, Any]:
        if default:
            return {
                "success": True,
                "weight_template": DEFAULT_WEIGHT_TEMPLATE,
                "volume_template": DEFAULT_VOLUME_TEMPLATE,
            }
        if self.template_path.exists():
            try:
                data = json.loads(self.template_path.read_text(encoding="utf-8"))
                return {
                    "success": True,
                    "weight_template": str(data.get("weight_template") or DEFAULT_WEIGHT_TEMPLATE),
                    "volume_template": str(data.get("volume_template") or DEFAULT_VOLUME_TEMPLATE),
                }
            except Exception:
                pass
        return {
            "success": True,
            "weight_template": DEFAULT_WEIGHT_TEMPLATE,
            "volume_template": DEFAULT_VOLUME_TEMPLATE,
        }

    def save_template(self, weight_template: str, volume_template: str) -> dict[str, Any]:
        payload = {
            "weight_template": str(weight_template or DEFAULT_WEIGHT_TEMPLATE).strip() or DEFAULT_WEIGHT_TEMPLATE,
            "volume_template": str(volume_template or DEFAULT_VOLUME_TEMPLATE).strip() or DEFAULT_VOLUME_TEMPLATE,
            "updated_at": _now_iso(),
        }
        self.template_path.parent.mkdir(parents=True, exist_ok=True)
        self.template_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return {"success": True, "message": "Template saved", **payload}

    def get_replies(self) -> list[dict[str, Any]]:
        """查询自动回复日志（关联 workflow_jobs + compliance_audit 补充缺失数据）。"""
        db = self.project_root / "data" / "workflow.db"
        if not db.exists():
            return []
        try:
            conn = sqlite3.connect(str(db))
            conn.row_factory = sqlite3.Row

            comp_db = self.project_root / "data" / "compliance.db"
            has_comp = comp_db.exists()
            if has_comp:
                conn.execute("ATTACH DATABASE ? AS comp", (str(comp_db),))

            rows = conn.execute(
                """SELECT id, session_id, to_state, metadata, created_at
                   FROM session_state_transitions
                   WHERE to_state IN ('REPLIED','QUOTED') AND status='success'
                   ORDER BY created_at DESC LIMIT 200"""
            ).fetchall()

            sids = list({r["session_id"] for r in rows})

            job_map: dict[str, dict] = {}
            if sids:
                ph = ",".join("?" * len(sids))
                for jr in conn.execute(
                    f"SELECT session_id, payload_json FROM workflow_jobs"
                    f" WHERE session_id IN ({ph}) AND stage='reply' ORDER BY id DESC",
                    sids,
                ):
                    if jr["session_id"] not in job_map:
                        job_map[jr["session_id"]] = json.loads(jr["payload_json"]) if jr["payload_json"] else {}

            audit_map: dict[str, str] = {}
            if has_comp and sids:
                ph = ",".join("?" * len(sids))
                for ar in conn.execute(
                    f"SELECT session_id, content FROM comp.compliance_audit"
                    f" WHERE session_id IN ({ph}) AND action='message_send' AND blocked=0"
                    f" ORDER BY created_at DESC",
                    sids,
                ):
                    if ar["session_id"] not in audit_map:
                        audit_map[ar["session_id"]] = ar["content"]

            conn.close()
        except Exception:
            return []

        logs: list[dict[str, Any]] = []
        for r in rows:
            meta = json.loads(r["metadata"]) if r["metadata"] else {}
            payload = job_map.get(r["session_id"], {})
            logs.append(
                {
                    "id": str(r["id"]),
                    "session_id": r["session_id"],
                    "buyer_message": meta.get("buyer_message") or payload.get("last_message", ""),
                    "reply_text": meta.get("reply_text") or audit_map.get(r["session_id"], ""),
                    "intent": "quote" if meta.get("quote") else meta.get("intent", "auto_reply"),
                    "item_title": meta.get("peer_name") or payload.get("peer_name", ""),
                    "replied_at": r["created_at"],
                }
            )
        return logs

    def get_reply_templates(self) -> dict[str, Any]:
        """返回回复模板配置（原 get_replies 功能）。"""
        template = self.get_template(default=False)
        return {
            "success": bool(template.get("success")),
            "replies": {
                "weight_template": str(template.get("weight_template") or DEFAULT_WEIGHT_TEMPLATE),
                "volume_template": str(template.get("volume_template") or DEFAULT_VOLUME_TEMPLATE),
            },
            "updated_at": str(template.get("updated_at") or ""),
        }

    @staticmethod
    def _decode_text_bytes(content: bytes) -> str:
        data = bytes(content or b"")
        for encoding in ("utf-8-sig", "utf-8", "gb18030", "gbk", "big5"):
            try:
                return data.decode(encoding)
            except UnicodeDecodeError:
                continue
        return data.decode("utf-8", errors="ignore")

    @staticmethod
    def _markup_float(value: Any) -> float | None:
        if value is None:
            return None
        if isinstance(value, (int, float)):
            return float(value)
        text = str(value).strip()
        if not text:
            return None
        text = text.replace("，", ",").replace(",", "")
        match = re.search(r"-?\d+(?:\.\d+)?", text)
        if not match:
            return None
        try:
            return float(match.group(0))
        except ValueError:
            return None

    @staticmethod
    def _clean_markup_token(value: Any) -> str:
        text = str(value or "").strip().lower()
        if not text:
            return ""
        text = text.replace("（", "(").replace("）", ")")
        text = re.sub(r"[\s_\-:|/\\,，;；。'\"]+", "", text)
        return text

    @classmethod
    def _normalize_markup_courier(cls, value: Any) -> str:
        raw = str(value or "").strip()
        if not raw:
            return ""
        if "默认" in raw or re.search(r"\bdefault\b", raw, flags=re.IGNORECASE):
            return "default"

        normalized = normalize_courier_name(raw)
        if normalized in DEFAULT_MARKUP_RULES:
            return normalized

        for courier in sorted([k for k in DEFAULT_MARKUP_RULES.keys() if k != "default"], key=len, reverse=True):
            if courier in raw:
                return courier

        noise_tokens = ("首重", "续重", "溢价", "加价", "普通", "会员", "运力", "价格", "元")
        if any(token in raw for token in noise_tokens):
            return ""

        if re.fullmatch(r"[\u4e00-\u9fa5A-Za-z0-9]{2,12}", normalized):
            return normalized
        return ""

    @classmethod
    def _match_markup_header(cls, header: str, field: str) -> bool:
        token = cls._clean_markup_token(header)
        if not token:
            return False

        if field == "courier":
            return any(alias in token for alias in ["运力", "快递", "物流", "courier", "carrier", "渠道"])
        if field == "normal_first_add":
            return ("首重" in token or "first" in token) and ("普通" in token or "normal" in token or "普" in token)
        if field == "member_first_add":
            return ("首重" in token or "first" in token) and ("会员" in token or "member" in token or "vip" in token)
        if field == "normal_extra_add":
            return ("续重" in token or "extra" in token or "续费" in token) and (
                "普通" in token or "normal" in token or "普" in token
            )
        if field == "member_extra_add":
            return ("续重" in token or "extra" in token or "续费" in token) and (
                "会员" in token or "member" in token or "vip" in token
            )
        return False

    @classmethod
    def _resolve_markup_header_map(cls, rows: list[list[Any]]) -> tuple[dict[str, int], int]:
        max_check = min(len(rows), 10)
        best_map: dict[str, int] = {}
        best_end = -1
        best_score = 0

        for start in range(max_check):
            for span in (2, 1):
                if start + span > len(rows):
                    continue
                width = max(len(rows[idx]) for idx in range(start, start + span))
                combined_headers: dict[int, str] = {}
                for col in range(width):
                    parts: list[str] = []
                    for idx in range(start, start + span):
                        row = rows[idx]
                        if col < len(row):
                            value = str(row[col] or "").strip()
                            if value:
                                parts.append(value)
                    combined_headers[col] = " ".join(parts)

                mapping: dict[str, int] = {}
                for col, head in combined_headers.items():
                    for field in ("courier", *cls._MARKUP_REQUIRED_FIELDS):
                        if field in mapping:
                            continue
                        if cls._match_markup_header(head, field):
                            mapping[field] = col

                score = len([f for f in cls._MARKUP_REQUIRED_FIELDS if f in mapping])
                if "courier" in mapping and score >= 3 and score > best_score:
                    best_map = mapping
                    best_end = start + span - 1
                    best_score = score

        return best_map, best_end

    def _build_markup_rule(
        self, row_payload: dict[str, Any], fallback_numbers: list[float] | None = None
    ) -> dict[str, float]:
        default_row = dict(DEFAULT_MARKUP_RULES.get("default", {}))
        ordered_numbers = list(fallback_numbers or [])
        built: dict[str, float] = {}
        for idx, field in enumerate(self._MARKUP_REQUIRED_FIELDS):
            value: Any | None = row_payload.get(field)
            if value is None and idx < len(ordered_numbers):
                value = ordered_numbers[idx]
            built[field] = self._to_non_negative_float(value, default_row.get(field, 0.0))
        return built

    def _coerce_markup_row(self, value: Any) -> dict[str, float] | None:
        default_row = dict(DEFAULT_MARKUP_RULES.get("default", {}))
        if isinstance(value, dict):
            cleaned: dict[str, Any] = {}
            for k, v in value.items():
                token = self._clean_markup_token(k)
                if token:
                    cleaned[token] = v

            row_payload: dict[str, Any] = {}
            hit_count = 0
            for field in self._MARKUP_REQUIRED_FIELDS:
                aliases = [
                    self._clean_markup_token(field),
                    *[self._clean_markup_token(x) for x in self._MARKUP_FIELD_ALIASES[field]],
                ]
                value_found: Any | None = None
                for alias in aliases:
                    if alias in cleaned:
                        value_found = cleaned[alias]
                        break
                if value_found is not None:
                    hit_count += 1
                    row_payload[field] = value_found

            fallback_numbers = [n for n in (self._markup_float(v) for v in value.values()) if n is not None]
            if hit_count == 0 and len(fallback_numbers) < 4:
                return None
            return self._build_markup_rule(row_payload, fallback_numbers=fallback_numbers)

        if isinstance(value, (list, tuple)):
            nums = [n for n in (self._markup_float(x) for x in value) if n is not None]
            if len(nums) >= 4:
                return self._build_markup_rule({}, fallback_numbers=nums)
            return None

        number = self._markup_float(value)
        if number is not None:
            return self._build_markup_rule(
                {
                    "normal_first_add": number,
                    "member_first_add": default_row.get("member_first_add", 0.25),
                    "normal_extra_add": default_row.get("normal_extra_add", 0.5),
                    "member_extra_add": default_row.get("member_extra_add", 0.3),
                }
            )
        return None

    def _parse_markup_rules_from_mapping(self, mapping: Any) -> dict[str, dict[str, float]]:
        if not isinstance(mapping, dict):
            return {}
        parsed: dict[str, dict[str, float]] = {}
        for key, raw in mapping.items():
            courier = self._normalize_markup_courier(key)
            if not courier:
                continue
            row = self._coerce_markup_row(raw)
            if row is None:
                continue
            parsed[courier] = row
        return parsed

    @staticmethod
    def _split_text_rows(text: str) -> list[list[str]]:
        lines = [line.strip() for line in str(text or "").splitlines() if line.strip()]
        if not lines:
            return []

        sample = lines[:8]
        delimiter_scores = {
            ",": sum(line.count(",") for line in sample),
            "\t": sum(line.count("\t") for line in sample),
            ";": sum(line.count(";") for line in sample),
            "|": sum(line.count("|") for line in sample),
        }
        delimiter = max(delimiter_scores, key=lambda d: delimiter_scores[d])
        if delimiter_scores[delimiter] <= 0:
            return []

        if delimiter == "|":
            return [[part.strip() for part in line.strip("|").split("|")] for line in lines if "|" in line]

        reader = csv.reader(io.StringIO("\n".join(lines)), delimiter=delimiter)
        return [[str(cell or "").strip() for cell in row] for row in reader]

    def _parse_markup_rules_from_rows(self, rows: list[list[Any]]) -> dict[str, dict[str, float]]:
        if not rows:
            return {}
        mapping, header_end = self._resolve_markup_header_map(rows)
        parsed: dict[str, dict[str, float]] = {}

        data_rows = rows[header_end + 1 :] if header_end >= 0 else rows
        for row in data_rows:
            if not row or not any(str(cell or "").strip() for cell in row):
                continue

            courier = ""
            if "courier" in mapping and mapping["courier"] < len(row):
                courier = self._normalize_markup_courier(row[mapping["courier"]])
            if not courier:
                for cell in row[:2]:
                    courier = self._normalize_markup_courier(cell)
                    if courier:
                        break
            if not courier:
                continue

            row_payload: dict[str, Any] = {}
            extracted = 0
            for field in self._MARKUP_REQUIRED_FIELDS:
                col_idx = mapping.get(field)
                if col_idx is None or col_idx >= len(row):
                    continue
                n = self._markup_float(row[col_idx])
                if n is None:
                    continue
                row_payload[field] = n
                extracted += 1

            fallback_numbers = [n for n in (self._markup_float(cell) for cell in row) if n is not None]
            if extracted == 0 and len(fallback_numbers) < 4:
                continue
            parsed[courier] = self._build_markup_rule(row_payload, fallback_numbers=fallback_numbers)

        return parsed

    def _parse_markup_rules_from_text(self, text: str) -> dict[str, dict[str, float]]:
        parsed: dict[str, dict[str, float]] = {}

        row_based = self._split_text_rows(text)
        if row_based:
            parsed.update(self._parse_markup_rules_from_rows(row_based))

        lines = [str(line or "").strip() for line in str(text or "").splitlines() if str(line or "").strip()]
        pending_courier = ""
        pending_numbers: list[float] = []

        for line in lines:
            courier = self._normalize_markup_courier(line)
            numbers = [
                n for n in (self._markup_float(x) for x in re.findall(r"-?\d+(?:\.\d+)?", line)) if n is not None
            ]

            if courier and len(numbers) >= 4:
                parsed[courier] = self._build_markup_rule({}, fallback_numbers=numbers)
                pending_courier = ""
                pending_numbers = []
                continue

            if courier:
                pending_courier = courier
                pending_numbers = list(numbers)
                continue

            if pending_courier:
                pending_numbers.extend(numbers)
                if len(pending_numbers) >= 4:
                    parsed[pending_courier] = self._build_markup_rule({}, fallback_numbers=pending_numbers)
                    pending_courier = ""
                    pending_numbers = []

        return parsed

    def _parse_markup_rules_from_json_like(self, payload: Any) -> dict[str, dict[str, float]]:
        if payload is None:
            return {}

        if isinstance(payload, dict):
            if "markup_rules" in payload:
                return self._parse_markup_rules_from_mapping(payload.get("markup_rules"))
            return self._parse_markup_rules_from_mapping(payload)

        if isinstance(payload, list):
            parsed: dict[str, dict[str, float]] = {}
            for item in payload:
                if not isinstance(item, dict):
                    continue
                courier = ""
                for alias in self._MARKUP_FIELD_ALIASES["courier"]:
                    value = item.get(alias)
                    courier = self._normalize_markup_courier(value)
                    if courier:
                        break
                if not courier:
                    for key in ("courier", "carrier", "name"):
                        courier = self._normalize_markup_courier(item.get(key))
                        if courier:
                            break
                if not courier:
                    continue
                row = self._coerce_markup_row(item)
                if row:
                    parsed[courier] = row
            return parsed
        return {}

    def _extract_text_from_image(self, content: bytes) -> str:
        try:
            from PIL import Image, ImageOps
        except Exception as exc:  # pragma: no cover - env dependent
            raise ValueError(f"Pillow unavailable: {exc}") from exc

        image = Image.open(io.BytesIO(content))
        image = ImageOps.grayscale(image)
        image = ImageOps.autocontrast(image)

        try:
            import pytesseract  # type: ignore

            text = pytesseract.image_to_string(image, lang="chi_sim+eng", config="--psm 6")
            if text.strip():
                return text
        except Exception:
            pass

        # Fallback: system tesseract CLI
        import tempfile

        temp_path = Path(tempfile.mkstemp(prefix="markup_ocr_", suffix=".png")[1])
        try:
            image.save(temp_path)
            proc = subprocess.run(
                ["tesseract", str(temp_path), "stdout", "-l", "chi_sim+eng", "--psm", "6"],
                capture_output=True,
                text=True,
                timeout=20,
                check=False,
            )
            if proc.returncode != 0:
                stderr = (proc.stderr or "").strip()
                raise ValueError(f"tesseract failed ({proc.returncode}): {stderr or 'no stderr'}")
            out = str(proc.stdout or "")
            if not out.strip():
                raise ValueError("OCR result is empty")
            return out
        except FileNotFoundError as exc:  # pragma: no cover - env dependent
            raise ValueError("No OCR engine found. Install `pytesseract` or system `tesseract` first.") from exc
        finally:
            temp_path.unlink(missing_ok=True)

    def _parse_markup_rules_from_xlsx_bytes(self, content: bytes) -> dict[str, dict[str, float]]:
        import tempfile

        temp_path = Path(tempfile.mkstemp(prefix="markup_xlsx_", suffix=".xlsx")[1])
        try:
            temp_path.write_bytes(content)
            repo = CostTableRepository(table_dir=temp_path)
            rows_by_sheet = repo._iter_xlsx_rows(temp_path)
            rows: list[list[Any]] = []
            for _, sheet_rows in rows_by_sheet.items():
                rows.extend(sheet_rows)
            return self._parse_markup_rules_from_rows(rows)
        finally:
            temp_path.unlink(missing_ok=True)

    def _infer_markup_rules_from_route_table(self, filename: str, content: bytes) -> dict[str, dict[str, float]]:
        ext = Path(str(filename or "")).suffix.lower()
        if ext not in {".xlsx", ".csv"}:
            return {}

        import tempfile

        temp_path = Path(tempfile.mkstemp(prefix="route_infer_", suffix=ext)[1])
        try:
            temp_path.write_bytes(content)
            repo = CostTableRepository(table_dir=temp_path)
            repo.get_stats(max_files=1)
            records = getattr(repo, "_records", [])
            if not records:
                return {}

            default_row = dict(DEFAULT_MARKUP_RULES.get("default", {}))
            inferred: dict[str, dict[str, float]] = {}
            for rec in records:
                courier = self._normalize_markup_courier(getattr(rec, "courier", ""))
                if not courier or courier == "default":
                    continue
                inferred[courier] = dict(default_row)
            return inferred
        except Exception:
            return {}
        finally:
            temp_path.unlink(missing_ok=True)

    def _parse_markup_rules_from_file(self, filename: str, content: bytes) -> tuple[dict[str, dict[str, float]], str]:
        ext = Path(str(filename or "")).suffix.lower()
        data = bytes(content or b"")
        if ext in self._MARKUP_IMAGE_EXTS:
            text = self._extract_text_from_image(data)
            return self._parse_markup_rules_from_text(text), "image_ocr"

        if ext == ".xlsx":
            parsed = self._parse_markup_rules_from_xlsx_bytes(data)
            if parsed:
                return parsed, "excel_xml"
            inferred = self._infer_markup_rules_from_route_table(filename, data)
            if inferred:
                return inferred, "route_cost_infer"
            return {}, "excel_xml"

        if ext == ".xls":
            try:
                import pandas as pd
            except Exception as exc:  # pragma: no cover - dependency guard
                raise ValueError(f"excel parse failed: {exc}") from exc
            try:
                book = pd.read_excel(io.BytesIO(data), sheet_name=None, header=None)
            except Exception as exc:
                raise ValueError(f"excel parse failed: {exc}") from exc
            rows: list[list[Any]] = []
            for _, frame in (book or {}).items():
                if frame is None or getattr(frame, "empty", False):
                    continue
                rows.extend(frame.fillna("").values.tolist())
            parsed = self._parse_markup_rules_from_rows(rows)
            if parsed:
                return parsed, "excel"
            inferred = self._infer_markup_rules_from_route_table(filename, data)
            if inferred:
                return inferred, "route_cost_infer"
            return {}, "excel"

        text = self._decode_text_bytes(data)
        if ext == ".json":
            payload = _extract_json_payload(text)
            return self._parse_markup_rules_from_json_like(payload), "json"
        if ext in {".yaml", ".yml"}:
            payload = yaml.safe_load(text) if text.strip() else {}
            return self._parse_markup_rules_from_json_like(payload), "yaml"
        if ext in {".csv", ".txt", ".md"}:
            payload = _extract_json_payload(text)
            if payload is not None:
                parsed = self._parse_markup_rules_from_json_like(payload)
                if parsed:
                    return parsed, "json_text"
            parsed_text = self._parse_markup_rules_from_text(text)
            if parsed_text:
                return parsed_text, "text_table"
            inferred = self._infer_markup_rules_from_route_table(filename, data)
            if inferred:
                return inferred, "route_cost_infer"
            return {}, "text_table"

        raise ValueError(f"Unsupported file type: {filename}")

    def import_markup_files(self, files: list[tuple[str, bytes]]) -> dict[str, Any]:
        if not files:
            return {"success": False, "error": "No files uploaded"}

        parsed_rules: dict[str, dict[str, float]] = {}
        imported_files: list[str] = []
        skipped_files: list[str] = []
        details: list[str] = []
        formats: dict[str, int] = {}

        def _collect_one(name: str, data: bytes, source_prefix: str = "") -> None:
            file_name = str(name or "").strip()
            ext = Path(file_name).suffix.lower()
            if ext not in (self._MARKUP_FILE_EXTS | self._MARKUP_IMAGE_EXTS):
                skipped_files.append(f"{source_prefix}{file_name}")
                return
            try:
                parsed, fmt = self._parse_markup_rules_from_file(file_name, data)
                if not parsed:
                    skipped_files.append(f"{source_prefix}{file_name}")
                    details.append(f"{source_prefix}{file_name} -> no markup rule rows found")
                    return
                parsed_rules.update(parsed)
                imported_files.append(f"{source_prefix}{file_name}")
                formats[fmt] = int(formats.get(fmt, 0) or 0) + 1
            except Exception as exc:
                skipped_files.append(f"{source_prefix}{file_name}")
                details.append(f"{source_prefix}{file_name} -> {exc}")

        for filename, content in files:
            file_name = str(filename or "").strip()
            suffix = Path(file_name).suffix.lower()
            if suffix == ".zip":
                try:
                    with zipfile.ZipFile(io.BytesIO(content), mode="r") as zf:
                        for info in zf.infolist():
                            if info.is_dir():
                                continue
                            repaired_name = self._repair_zip_name(info.filename)
                            member_name = Path(repaired_name).name
                            if not member_name:
                                continue
                            if "__MACOSX" in repaired_name or member_name.startswith("._"):
                                skipped_files.append(f"{file_name}:{repaired_name}")
                                continue
                            _collect_one(member_name, zf.read(info), source_prefix=f"{file_name}:")
                except zipfile.BadZipFile:
                    skipped_files.append(file_name)
                    details.append(f"{file_name} -> invalid zip file")
                except Exception as exc:
                    skipped_files.append(file_name)
                    details.append(f"{file_name} -> {exc}")
                continue

            _collect_one(file_name, content)

        if not parsed_rules:
            return {
                "success": False,
                "error": "No valid markup rules found in uploaded files.",
                "imported_files": imported_files,
                "skipped_files": skipped_files,
                "details": details,
            }

        existing_payload = self.get_markup_rules()
        merged_rules = existing_payload.get("markup_rules", {})
        if not isinstance(merged_rules, dict):
            merged_rules = {}
        merged_rules = dict(merged_rules)
        merged_rules.update(parsed_rules)

        saved = self.save_markup_rules(merged_rules)
        if not saved.get("success"):
            return saved

        return {
            **saved,
            "imported_files": imported_files,
            "skipped_files": skipped_files,
            "details": details,
            "detected_formats": dict(sorted(formats.items(), key=lambda item: item[0])),
            "imported_couriers": [k for k in sorted(parsed_rules.keys()) if k != "default"],
        }

    @property
    def config_path(self) -> Path:
        return self.project_root / "config" / "config.yaml"

    @staticmethod
    def _to_non_negative_float(value: Any, default: float = 0.0) -> float:
        try:
            val = float(value)
            if val < 0:
                return 0.0
            return round(val, 4)
        except (TypeError, ValueError):
            return float(default)

    def _normalize_markup_rules(self, rules: Any) -> dict[str, dict[str, float]]:
        base_default = dict(DEFAULT_MARKUP_RULES.get("default", {}))
        if not isinstance(rules, dict):
            return {"default": base_default}

        normalized: dict[str, dict[str, float]] = {}
        for key, raw in rules.items():
            courier = str(key or "").strip()
            if not courier:
                continue
            payload = raw if isinstance(raw, dict) else {}
            normalized[courier] = {
                "normal_first_add": self._to_non_negative_float(
                    payload.get("normal_first_add"), base_default.get("normal_first_add", 0.5)
                ),
                "member_first_add": self._to_non_negative_float(
                    payload.get("member_first_add"), base_default.get("member_first_add", 0.25)
                ),
                "normal_extra_add": self._to_non_negative_float(
                    payload.get("normal_extra_add"), base_default.get("normal_extra_add", 0.5)
                ),
                "member_extra_add": self._to_non_negative_float(
                    payload.get("member_extra_add"), base_default.get("member_extra_add", 0.3)
                ),
            }

        if "default" not in normalized:
            normalized["default"] = base_default

        ordered: dict[str, dict[str, float]] = {"default": normalized.pop("default")}
        for key in sorted(normalized.keys()):
            ordered[key] = normalized[key]
        return ordered

    def get_markup_rules(self) -> dict[str, Any]:
        setup = QuoteSetupService(config_path=str(self.config_path))
        data, _ = setup._load_yaml()
        quote_cfg = data.get("quote", {}) if isinstance(data, dict) else {}
        rules = quote_cfg.get("markup_rules", {}) if isinstance(quote_cfg, dict) else {}
        normalized = self._normalize_markup_rules(rules if rules else DEFAULT_MARKUP_RULES)
        return {
            "success": True,
            "markup_rules": normalized,
            "couriers": [k for k in normalized.keys() if k != "default"],
            "updated_at": _now_iso(),
        }

    def save_markup_rules(self, rules: Any) -> dict[str, Any]:
        normalized = self._normalize_markup_rules(rules)
        if not normalized:
            return {"success": False, "error": "No valid markup rules"}

        setup = QuoteSetupService(config_path=str(self.config_path))
        data, existed = setup._load_yaml()
        quote_cfg = data.get("quote")
        if not isinstance(quote_cfg, dict):
            quote_cfg = {}
            data["quote"] = quote_cfg
        quote_cfg["markup_rules"] = normalized

        backup_path = setup._backup_existing_file() if existed else None
        setup._write_yaml(data)
        try:
            get_config().reload(str(self.config_path))
        except Exception:
            pass

        return {
            "success": True,
            "message": "Markup rules saved",
            "backup_path": str(backup_path) if backup_path else "",
            "markup_rules": normalized,
        }

    def get_pricing_config(self) -> dict[str, Any]:
        """读取 YAML 中的 markup_categories、xianyu_discount、抛比和大件运力优先级。"""
        setup = QuoteSetupService(config_path=str(self.config_path))
        data, _ = setup._load_yaml()
        quote_cfg = data.get("quote", {}) if isinstance(data, dict) else {}
        return {
            "success": True,
            "markup_categories": quote_cfg.get("markup_categories", {}),
            "xianyu_discount": quote_cfg.get("xianyu_discount", {}),
            "volume_divisor_default": quote_cfg.get("volume_divisor_default", 8000),
            "volume_divisors": quote_cfg.get("volume_divisors", {}),
            "freight_courier_priority": quote_cfg.get("freight_courier_priority", []),
            "service_categories": [
                "线上快递",
                "线下快递",
                "线上快运",
                "线下快运",
                "同城寄",
                "电动车",
                "分销",
                "商家寄件",
            ],
            "updated_at": _now_iso(),
        }

    def save_pricing_config(
        self,
        markup_categories: Any = None,
        xianyu_discount: Any = None,
        volume_divisor_default: Any = None,
        volume_divisors: Any = None,
        freight_courier_priority: Any = None,
    ) -> dict[str, Any]:
        """保存加价表、让利表、抛比和大件运力优先级到 YAML。"""
        setup = QuoteSetupService(config_path=str(self.config_path))
        data, existed = setup._load_yaml()
        quote_cfg = data.get("quote")
        if not isinstance(quote_cfg, dict):
            quote_cfg = {}
            data["quote"] = quote_cfg

        if isinstance(markup_categories, dict):
            quote_cfg["markup_categories"] = markup_categories
        if isinstance(xianyu_discount, dict):
            quote_cfg["xianyu_discount"] = xianyu_discount
        if volume_divisor_default is not None:
            try:
                val = float(volume_divisor_default)
                if val > 0:
                    quote_cfg["volume_divisor_default"] = val
            except (TypeError, ValueError):
                pass
        if isinstance(volume_divisors, dict):
            normalized: dict[str, Any] = {}
            for cat, courier_cfg in volume_divisors.items():
                if not isinstance(courier_cfg, dict):
                    continue
                inner: dict[str, float] = {}
                for k, v in courier_cfg.items():
                    try:
                        fv = float(v)
                        if fv > 0:
                            inner[str(k).strip()] = fv
                    except (TypeError, ValueError):
                        pass
                if inner:
                    normalized[str(cat).strip()] = inner
            quote_cfg["volume_divisors"] = normalized
        if isinstance(freight_courier_priority, list):
            quote_cfg["freight_courier_priority"] = [str(c).strip() for c in freight_courier_priority if str(c).strip()]

        setup._backup_existing_file() if existed else None
        setup._write_yaml(data)
        # Bridge: also persist to system_config.json so MessagesService/QuoteEngine picks it up.
        try:
            import json as _json

            from src.dashboard.config_service import write_system_config as _write_sys

            sys_path = self.project_root / "data" / "system_config.json"
            sys_data: dict[str, Any] = {}
            if sys_path.exists():
                try:
                    sys_data = _json.loads(sys_path.read_text(encoding="utf-8"))
                except Exception:
                    pass
            sys_data["quote"] = dict(quote_cfg)
            _write_sys(sys_data)
        except Exception:
            pass
        try:
            get_config().reload(str(self.config_path))
        except Exception:
            pass
        # Hot-reload the live MessagesService quote engine so it takes effect immediately.
        try:
            from src.modules.messages.service import _active_service

            if _active_service is not None:
                _active_service.reload_quote_engine()
        except Exception:
            pass

        return {"success": True, "updated_at": _now_iso()}

    def _get_cost_table_repo(self):
        from src.modules.quote.cost_table import CostTableRepository

        if self._cost_table_repo is None:
            self._cost_table_repo = CostTableRepository(table_dir=str(self._quote_dir()))
        return self._cost_table_repo

    def get_cost_summary(self) -> dict[str, Any]:
        """从成本表 xlsx 读取各运力概览数据（只读）。"""
        repo = self._get_cost_table_repo()
        stats = repo.get_stats()

        # 按运力聚合概览，取同一路线最低总成本
        repo._reload_if_needed()
        courier_summary: dict[str, dict] = {}
        for record in repo._records:
            key = record.courier
            total = record.first_cost + record.extra_cost
            if key not in courier_summary:
                courier_summary[key] = {
                    "courier": key,
                    "service_type": record.service_type,
                    "base_weight": record.base_weight,
                    "route_count": 0,
                    "cheapest_first": record.first_cost,
                    "cheapest_extra": record.extra_cost,
                    "_cheapest_total": total,
                    "cheapest_route": f"{record.origin}->{record.destination}",
                }
            info = courier_summary[key]
            info["route_count"] += 1
            if total < info["_cheapest_total"]:
                info["cheapest_first"] = record.first_cost
                info["cheapest_extra"] = record.extra_cost
                info["_cheapest_total"] = total
                info["cheapest_route"] = f"{record.origin}->{record.destination}"

        for info in courier_summary.values():
            info.pop("_cheapest_total", None)

        return {
            "success": True,
            "couriers": list(courier_summary.values()),
            "total_records": stats["total_records"],
            "total_files": stats["total_files"],
        }

    def query_route_cost(self, origin: str, destination: str) -> dict[str, Any]:
        """查询指定路线下各运力的成本明细。"""
        origin = (origin or "").strip()
        destination = (destination or "").strip()
        if not origin or not destination:
            return {"success": False, "error": "请输入始发地和目的地"}

        repo = self._get_cost_table_repo()
        candidates = repo.find_candidates(origin=origin, destination=destination, courier=None, limit=500)

        courier_summary: dict[str, dict] = {}
        for record in candidates:
            key = record.courier
            total = record.first_cost + record.extra_cost
            if key not in courier_summary:
                courier_summary[key] = {
                    "courier": key,
                    "service_type": record.service_type,
                    "base_weight": record.base_weight,
                    "route_count": 0,
                    "cheapest_first": record.first_cost,
                    "cheapest_extra": record.extra_cost,
                    "_cheapest_total": total,
                    "cheapest_route": f"{record.origin}->{record.destination}",
                }
            info = courier_summary[key]
            info["route_count"] += 1
            if total < info["_cheapest_total"]:
                info["cheapest_first"] = record.first_cost
                info["cheapest_extra"] = record.extra_cost
                info["_cheapest_total"] = total
                info["cheapest_route"] = f"{record.origin}->{record.destination}"

        for info in courier_summary.values():
            info.pop("_cheapest_total", None)

        return {
            "success": True,
            "origin": origin,
            "destination": destination,
            "couriers": list(courier_summary.values()),
        }

    def _module_runtime_log(self, target: str) -> Path:
        return self.project_root / "data" / "module_runtime" / f"{target}.log"

    def list_log_files(self) -> dict[str, Any]:
        files: list[dict[str, Any]] = []
        runtime_dir = self.project_root / "data" / "module_runtime"
        conversations_dir = self.logs_dir / "conversations"

        for fp in runtime_dir.glob("*.log"):
            if not fp.is_file():
                continue
            stat = fp.stat()
            files.append(
                {
                    "name": f"runtime/{fp.name}",
                    "path": str(fp),
                    "size": stat.st_size,
                    "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    "type": "runtime",
                }
            )

        for fp in self.logs_dir.glob("*.log"):
            if not fp.is_file():
                continue
            stat = fp.stat()
            files.append(
                {
                    "name": f"app/{fp.name}",
                    "path": str(fp),
                    "size": stat.st_size,
                    "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    "type": "app",
                }
            )

        for fp in conversations_dir.glob("*.log"):
            if not fp.is_file():
                continue
            stat = fp.stat()
            files.append(
                {
                    "name": f"conversations/{fp.name}",
                    "path": str(fp),
                    "size": stat.st_size,
                    "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    "type": "conversation",
                }
            )

        files.sort(key=lambda x: str(x.get("modified", "")), reverse=True)
        return {"success": True, "files": files}

    def _resolve_log_file(self, file_name: str) -> Path:
        name = str(file_name or "").strip()
        if name in {"presales", "operations", "aftersales"}:
            return self._module_runtime_log(name)
        if name.startswith("runtime/"):
            return self.project_root / "data" / "module_runtime" / name.replace("runtime/", "", 1)
        if name.startswith("app/"):
            return self.logs_dir / name.replace("app/", "", 1)
        if name.startswith("conversations/"):
            return self.logs_dir / "conversations" / name.replace("conversations/", "", 1)

        safe_name = Path(name).name
        app_path = self.logs_dir / safe_name
        if app_path.exists():
            return app_path
        return self.project_root / "data" / "module_runtime" / safe_name

    def read_log_content(
        self,
        file_name: str,
        tail: int = 200,
        page: int | None = None,
        size: int | None = None,
        search: str = "",
    ) -> dict[str, Any]:
        name = str(file_name or "").strip()
        if not name:
            return {"success": False, "error": "file is required"}

        fp = self._resolve_log_file(name)

        if not fp.exists():
            return {"success": False, "error": "log file not found", "file": str(fp)}

        lines = fp.read_text(encoding="utf-8", errors="ignore").splitlines()

        search_text = str(search or "").strip().lower()
        if search_text:
            lines = [line for line in lines if search_text in line.lower()]

        if page is not None or size is not None:
            page_n = max(1, int(page or 1))
            page_size = max(10, min(int(size or 100), 2000))
            total_lines = len(lines)
            total_pages = (total_lines + page_size - 1) // page_size if total_lines > 0 else 1
            if page_n > total_pages:
                page_n = total_pages
            start = (page_n - 1) * page_size
            end = start + page_size
            return {
                "success": True,
                "file": str(fp),
                "lines": lines[start:end],
                "total_lines": total_lines,
                "page": page_n,
                "total_pages": total_pages,
                "page_size": page_size,
                "search": search_text,
            }

        tail_n = max(1, min(int(tail), 5000))
        return {"success": True, "file": str(fp), "lines": lines[-tail_n:], "total_lines": len(lines)}

    @classmethod
    def _strip_ansi(cls, text: str) -> str:
        return cls._ANSI_ESCAPE_RE.sub("", str(text or "")).strip()

    @classmethod
    def _extract_log_time(cls, text: str) -> str:
        cleaned = cls._strip_ansi(text)
        m = cls._LOG_TIME_RE.search(cleaned)
        return str(m.group(1)) if m else ""

    @classmethod
    def _parse_log_datetime(cls, text: str) -> datetime | None:
        ts_str = cls._extract_log_time(text)
        if not ts_str:
            return None
        try:
            return datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            return None

    _RISK_LOG_CACHE_TTL: float = 5.0

    def _risk_control_status_from_logs(self, target: str = "presales", tail_lines: int = 300) -> dict[str, Any]:
        now = time.time()
        if self._risk_log_cache is not None and (now - self._risk_log_cache_ts) < self._RISK_LOG_CACHE_TTL:
            return self._risk_log_cache

        result = self._risk_control_status_from_logs_uncached(target=target, tail_lines=tail_lines)
        self._risk_log_cache = result
        self._risk_log_cache_ts = now
        return result

    def _risk_control_status_from_logs_uncached(
        self, target: str = "presales", tail_lines: int = 300
    ) -> dict[str, Any]:
        fp = self._module_runtime_log(target)
        _empty = {
            "last_event": "",
            "last_event_at": "",
            "checked_lines": 0,
            "source_log": str(fp),
            "updated_at": _now_iso(),
        }
        if not fp.exists():
            return {
                "level": "unknown",
                "label": "未检测（无日志）",
                "score": 0,
                "signals": ["日志文件不存在"],
                **_empty,
            }

        try:
            lines = fp.read_text(encoding="utf-8", errors="ignore").splitlines()
        except Exception as e:
            return {
                "level": "unknown",
                "label": "未检测（读取失败）",
                "score": 0,
                "signals": [f"日志读取失败: {e}"],
                **_empty,
            }

        tail_n = max(50, min(int(tail_lines or 300), 2000))
        recent = [self._strip_ansi(line) for line in lines[-tail_n:] if str(line or "").strip()]
        if not recent:
            return {"level": "unknown", "label": "未检测（空日志）", "score": 0, "signals": ["日志内容为空"], **_empty}

        block_hits: list[tuple[int, str]] = []
        warn_hits: list[tuple[int, str]] = []
        ws_400_lines: list[tuple[int, str]] = []
        connected_hits: list[tuple[int, str]] = []

        _RECOVERY_SKIP = ("succeeded", "成功", "已恢复", "已过期")

        for idx, line in enumerate(recent):
            lowered = line.lower()
            if "connected to goofish websocket transport" in lowered:
                connected_hits.append((idx, line))
            if any(token in lowered for token in self._RISK_BLOCK_PATTERNS):
                if not any(skip in lowered for skip in _RECOVERY_SKIP):
                    block_hits.append((idx, line))
                continue
            if any(token in lowered for token in self._RISK_WARN_PATTERNS):
                warn_hits.append((idx, line))
            if "websocket" in lowered and "http 400" in lowered:
                ws_400_lines.append((idx, line))

        now = datetime.now()
        window = timedelta(minutes=self._RISK_SIGNAL_WINDOW_MINUTES)

        def _split_by_freshness(
            hits: list[tuple[int, str]],
        ) -> tuple[list[tuple[int, str]], list[tuple[int, str]]]:
            active, stale = [], []
            for idx, line in hits:
                ts = self._parse_log_datetime(line)
                if ts is None:
                    stale.append((idx, line))
                elif (now - ts) > window:
                    stale.append((idx, line))
                else:
                    active.append((idx, line))
            return active, stale

        active_blocks, stale_blocks = _split_by_freshness(block_hits)
        active_warns, stale_warns = _split_by_freshness(warn_hits)
        active_ws400, stale_ws400 = _split_by_freshness(ws_400_lines)

        level = "normal"
        label = "正常"
        score = 0
        signals: list[str] = ["未发现封控信号"]
        last_event = recent[-1]

        if active_blocks:
            level = "blocked"
            label = "疑似封控"
            score = min(100, 75 + len(active_blocks) * 4)
            signals = [f"高风险信号 x{len(active_blocks)}"]
            if active_ws400:
                signals.append(f"WebSocket HTTP 400 x{len(active_ws400)}")
            last_event = active_blocks[-1][1]
        elif stale_blocks and not active_blocks:
            last_block_time = self._extract_log_time(stale_blocks[-1][1])
            level = "normal"
            label = "正常"
            score = 0
            signals = [
                f"历史高风险信号 x{len(stale_blocks)}（最后于 {last_block_time}，已超过 {self._RISK_SIGNAL_WINDOW_MINUTES} 分钟，已过期）"
            ]
            last_event = stale_blocks[-1][1]
        elif len(active_ws400) >= 10 or active_warns:
            level = "warning"
            label = "风险预警"
            score = min(85, 30 + len(active_warns) * 4 + len(active_ws400) * 2)
            signals = []
            if active_ws400:
                signals.append(f"WebSocket HTTP 400 x{len(active_ws400)}")
            if active_warns:
                signals.append(f"异常告警 x{len(active_warns)}")
            last_event = (active_warns or active_ws400)[-1][1]
        elif stale_warns or stale_ws400:
            stale_total = len(stale_warns) + len(stale_ws400)
            last_stale = stale_warns[-1] if stale_warns else stale_ws400[-1]
            last_stale_time = self._extract_log_time(last_stale[1])
            level = "normal"
            label = "正常"
            score = 0
            signals = [
                f"历史异常信号 x{stale_total}（最后于 {last_stale_time}，已超过 {self._RISK_SIGNAL_WINDOW_MINUTES} 分钟，已过期）"
            ]
            last_event = last_stale[1]

        last_connected_at = ""
        if connected_hits:
            last_connected_line = connected_hits[-1][1]
            last_connected_idx = connected_hits[-1][0]
            last_connected_at = self._extract_log_time(last_connected_line)
            last_risk_idx = -1
            if active_blocks:
                last_risk_idx = max(last_risk_idx, active_blocks[-1][0])
            if active_warns:
                last_risk_idx = max(last_risk_idx, active_warns[-1][0])
            if active_ws400:
                last_risk_idx = max(last_risk_idx, active_ws400[-1][0])
            if last_connected_idx > last_risk_idx >= 0:
                level = "normal"
                label = "已恢复连接"
                score = 0
                signals = ["最近已恢复连接"]
                last_event = last_connected_line

        if level in ("blocked", "warning") and self._last_auto_recover_at:
            try:
                recover_dt = datetime.fromisoformat(self._last_auto_recover_at.replace("Z", "+00:00")).replace(
                    tzinfo=None
                )
                last_risk_line = (active_blocks or active_warns or active_ws400 or [(-1, "")])[-1][1]
                last_risk_dt = self._parse_log_datetime(last_risk_line)
                if last_risk_dt and recover_dt > last_risk_dt:
                    level = "recovering"
                    label = "Cookie 已刷新，等待恢复"
                    score = max(0, score // 4)
                    signals = [f"Cookie 于 {self._last_auto_recover_at[:19]} 刷新，晚于最后风控信号"]
            except (ValueError, TypeError):
                pass

        return {
            "level": level,
            "label": label,
            "score": int(score),
            "signals": signals,
            "last_event": str(last_event)[-180:],
            "last_event_at": self._extract_log_time(last_event),
            "last_connected_at": last_connected_at,
            "checked_lines": len(recent),
            "source_log": str(fp),
            "updated_at": _now_iso(),
        }

    _sandbox_services: dict[str, tuple[float, MessagesService]] = {}
    _SANDBOX_TTL = 1800

    def _get_sandbox_service(self, session_id: str) -> MessagesService:
        now = time.time()
        stale = [k for k, (ts, _) in self._sandbox_services.items() if now - ts > self._SANDBOX_TTL]
        for k in stale:
            self._sandbox_services.pop(k, None)
        entry = self._sandbox_services.get(session_id)
        if entry is not None:
            self._sandbox_services[session_id] = (now, entry[1])
            return entry[1]
        msg_cfg = get_config().get_section("messages", {})
        svc = MessagesService(controller=None, config=msg_cfg)
        self._sandbox_services[session_id] = (now, svc)
        return svc

    def test_reply(self, payload: dict[str, Any]) -> dict[str, Any]:
        started = time.perf_counter()
        message = str(payload.get("message") or payload.get("user_message") or payload.get("user_msg") or "").strip()
        item_title = str(payload.get("item_title") or payload.get("item") or payload.get("item_desc") or "").strip()
        session_id = str(payload.get("session_id") or "").strip()
        origin = str(payload.get("origin") or "").strip()
        destination = str(payload.get("destination") or "").strip()
        weight_val = payload.get("weight")

        message_eval = message
        if origin and destination and weight_val not in {None, ""}:
            extras: list[str] = []
            length = payload.get("length")
            width = payload.get("width")
            height = payload.get("height")
            volume_weight = payload.get("volume_weight")
            courier = str(payload.get("courier") or "").strip()
            if length not in {None, ""} and width not in {None, ""} and height not in {None, ""}:
                extras.append(f"{length}x{width}x{height}cm")
            if volume_weight not in {None, ""}:
                extras.append(f"体积重{volume_weight}kg")
            if courier and courier.lower() != "auto":
                extras.append(courier)
            structured = f"从{origin}寄到{destination} {weight_val}kg"
            if extras:
                structured = f"{structured} {' '.join(extras)}"
            message_eval = f"{message} {structured}".strip() if message else structured

        if session_id:
            service = self._get_sandbox_service(session_id)
        else:
            msg_cfg = get_config().get_section("messages", {})
            service = MessagesService(controller=None, config=msg_cfg)
        reply, detail = _run_async(
            service._generate_reply_with_quote(message_eval, item_title=item_title, session_id=session_id)
        )

        quote_part: dict[str, Any] | None = None
        if isinstance(detail, dict) and bool(detail.get("is_quote")):
            quote_result = detail.get("quote_result")
            all_couriers = detail.get("quote_all_couriers")
            if isinstance(quote_result, dict):
                quote_part = quote_result
            if isinstance(all_couriers, list):
                quote_part = {"best": quote_part or {}, "all_couriers": all_couriers}

        intent = "quote" if bool(detail.get("is_quote")) else "general"
        agent = (
            "MessagesService+AutoQuoteEngine"
            if quote_part is not None
            else ("MessagesService+RuleBasedReplyStrategy" if intent == "general" else "MessagesService")
        )
        response_time_ms = (time.perf_counter() - started) * 1000
        return {
            "success": True,
            "reply": reply,
            "quote": quote_part,
            "intent": intent,
            "agent": agent,
            "detail": detail,
            "response_time_ms": response_time_ms,
            "response_time": response_time_ms,
        }

    _PRESALES_DEAD_RESTART_COOLDOWN = 60.0

    def _maybe_auto_recover_presales(
        self,
        *,
        service_status: str,
        token_error: str | None,
        cookie_text: str,
        presales_alive: bool = True,
    ) -> dict[str, Any]:
        cookie_fp = self._cookie_fingerprint(cookie_text)
        auto_triggered = False
        reason = "monitoring"
        stage = "monitoring"
        result: dict[str, Any] = {}

        if not presales_alive and service_status in ("running", "degraded"):
            now_ts = time.time()
            if (now_ts - self._last_presales_dead_restart_at) >= self._PRESALES_DEAD_RESTART_COOLDOWN:
                with self._recover_lock:
                    if (now_ts - self._last_presales_dead_restart_at) >= self._PRESALES_DEAD_RESTART_COOLDOWN:
                        self._last_presales_dead_restart_at = now_ts
                        result = self.module_console.control(action="recover", target="presales")
                        auto_triggered = not bool(result.get("error")) if isinstance(result, dict) else False
                        self._last_auto_recover_at = _now_iso()
                        self._last_auto_recover_result = result if isinstance(result, dict) else {}
                        stage = "recover_triggered"
                        reason = "presales_dead_auto_restart"
                        logger.info(
                            "presales 进程已死，自动重启 triggered=%s",
                            auto_triggered,
                        )
                self._last_cookie_fp = cookie_fp
                self._last_token_error = token_error
                return {
                    "stage": stage,
                    "stage_label": self._recovery_stage_label(stage),
                    "auto_recover_triggered": auto_triggered,
                    "reason": reason,
                    "advice": self._recovery_advice(stage, token_error),
                    "last_auto_recover_at": self._last_auto_recover_at,
                    "last_auto_recover_result": self._last_auto_recover_result,
                }
            else:
                stage = "cooldown"
                reason = "presales_dead_restart_cooldown"
                self._last_cookie_fp = cookie_fp
                self._last_token_error = token_error
                return {
                    "stage": stage,
                    "stage_label": self._recovery_stage_label(stage),
                    "auto_recover_triggered": False,
                    "reason": reason,
                    "advice": self._recovery_advice(stage, token_error),
                    "last_auto_recover_at": self._last_auto_recover_at,
                    "last_auto_recover_result": self._last_auto_recover_result,
                }

        if service_status in {"stopped", "suspended"}:
            reason = "service_not_running"
            stage = "inactive"
        elif token_error != "FAIL_SYS_USER_VALIDATE":
            reason = "token_healthy_or_non_validate_error"
            stage = "healthy" if token_error is None else "token_error"
        elif not cookie_fp:
            reason = "cookie_empty"
            stage = "waiting_cookie_update"
        elif cookie_fp == self._last_auto_recover_cookie_fp:
            reason = "same_cookie_already_recovered"
            stage = "waiting_reconnect"
        elif self._last_token_error == "FAIL_SYS_USER_VALIDATE" and cookie_fp != self._last_cookie_fp:
            stage = "recover_triggered"
            reason = "cookie_updated_after_validate_error"
            with self._recover_lock:
                # 双重检查，避免并发请求重复触发 recover。
                if cookie_fp != self._last_auto_recover_cookie_fp:
                    result = self.module_console.control(action="recover", target="presales")
                    auto_triggered = not bool(result.get("error")) if isinstance(result, dict) else False
                    self._last_auto_recover_cookie_fp = cookie_fp
                    self._last_auto_recover_at = _now_iso()
                    self._last_auto_recover_result = result if isinstance(result, dict) else {}
                else:
                    reason = "same_cookie_already_recovered"
                    stage = "waiting_reconnect"
        else:
            reason = "waiting_cookie_update"
            stage = "waiting_cookie_update"

        # 更新快照，供下一轮识别“cookie 是否发生变化”。
        self._last_cookie_fp = cookie_fp
        self._last_token_error = token_error

        return {
            "stage": stage,
            "stage_label": self._recovery_stage_label(stage),
            "auto_recover_triggered": auto_triggered,
            "reason": reason,
            "advice": self._recovery_advice(stage, token_error),
            "last_auto_recover_at": self._last_auto_recover_at,
            "last_auto_recover_result": self._last_auto_recover_result,
        }

    def _route_stats_nonblocking(self) -> dict[str, Any]:
        """Return cached route_stats if available; never block on cold Excel parsing."""
        if self._route_stats_cache is not None:
            return self._route_stats_cache
        return {"success": True, "stats": {}}

    def service_status(self) -> dict[str, Any]:
        module_status = self.module_console.status(window_minutes=60, limit=20)
        cookie = self.get_cookie()
        cookie_text = str(cookie.get("cookie", "") or "")
        route_stats = self._route_stats_nonblocking()
        xgj_settings = self.get_xianguanjia_settings()
        risk_control = self._risk_control_status_from_logs(target="presales", tail_lines=300)
        modules = module_status.get("modules") if isinstance(module_status, dict) else {}
        if not isinstance(modules, dict):
            modules = {}

        if self._service_state.get("stopped"):
            service_status = "stopped"
        elif self._service_state.get("suspended"):
            service_status = "suspended"
        else:
            service_status = "running"

        alive_count = int(module_status.get("alive_count", 0)) if isinstance(module_status, dict) else 0
        total_modules = (
            int(module_status.get("total_modules", len(MODULE_TARGETS)))
            if isinstance(module_status, dict)
            else len(MODULE_TARGETS)
        )

        presales_mod = modules.get("presales", {}) if isinstance(modules.get("presales"), dict) else {}
        presales_sla = presales_mod.get("sla", {}) if isinstance(presales_mod.get("sla"), dict) else {}
        presales_process = presales_mod.get("process", {}) if isinstance(presales_mod.get("process"), dict) else {}
        workflow = presales_mod.get("workflow", {}) if isinstance(presales_mod.get("workflow"), dict) else {}
        route_stat_payload = route_stats.get("stats", {}) if isinstance(route_stats, dict) else {}
        route_stats_by_courier = (
            route_stat_payload.get("courier_details", {}) if isinstance(route_stat_payload, dict) else {}
        )
        risk_level = str(risk_control.get("level", "unknown") or "unknown").lower()
        risk_signals_raw = risk_control.get("signals", [])
        risk_signals = (
            [str(x).strip() for x in risk_signals_raw if str(x).strip()] if isinstance(risk_signals_raw, list) else []
        )
        risk_signal_text = " ".join(risk_signals)
        risk_event_text = str(risk_control.get("last_event", "") or "")
        risk_text = f"{risk_signal_text} {risk_event_text}".lower()

        workflow_states = workflow.get("states", {}) if isinstance(workflow.get("states"), dict) else {}
        workflow_jobs = workflow.get("jobs", {}) if isinstance(workflow.get("jobs"), dict) else {}
        fallback_total_replied = int(workflow_states.get("REPLIED", 0) or 0) + int(
            workflow_states.get("QUOTED", 0) or 0
        )
        fallback_total_conversations = sum(int(v or 0) for v in workflow_states.values())
        fallback_total_messages = sum(int(v or 0) for v in workflow_jobs.values())
        message_stats = self._query_message_stats_from_workflow() or {
            "total_replied": fallback_total_replied,
            "today_replied": 0,
            "recent_replied": int(presales_sla.get("event_count", 0) or 0),
            "total_conversations": fallback_total_conversations,
            "today_conversations": 0,
            "total_messages": fallback_total_messages,
            "hourly_replies": {},
            "daily_replies": {},
        }

        token_error: str | None = None
        if risk_level not in ("stale", "normal"):
            if "fail_sys_user_validate" in risk_text:
                token_error = "FAIL_SYS_USER_VALIDATE"
            elif "rgv587" in risk_text or "被挤爆" in risk_text:
                token_error = "RGV587_SERVER_BUSY"
            elif "token api failed" in risk_text:
                token_error = "TOKEN_API_FAILED"
            elif "websocket" in risk_text and "http 400" in risk_text:
                token_error = "WS_HTTP_400"

        cookie_update_required = bool(token_error == "FAIL_SYS_USER_VALIDATE")
        token_available = bool(cookie.get("success", False)) and token_error is None
        xianyu_connected = (
            bool(presales_process.get("alive", False)) and token_error is None and risk_level != "blocked"
        )
        if service_status == "running" and (not xianyu_connected or risk_level in {"warning", "blocked"}):
            service_status = "degraded"
        recovery = self._maybe_auto_recover_presales(
            service_status=service_status,
            token_error=token_error,
            cookie_text=cookie_text,
            presales_alive=bool(presales_process.get("alive", False)),
        )
        recovery_stage = str(recovery.get("stage") or "monitoring").strip().lower() or "monitoring"
        next_retry_at: str | None = None
        if recovery_stage in {"recover_triggered", "waiting_reconnect"}:
            last_auto_recover_at = str(recovery.get("last_auto_recover_at") or "").strip()
            if last_auto_recover_at:
                try:
                    dt = datetime.fromisoformat(last_auto_recover_at.replace("Z", "+00:00"))
                    next_retry_at = (dt + timedelta(seconds=20)).strftime("%Y-%m-%dT%H:%M:%S")
                except Exception:
                    next_retry_at = None

        user_id = None
        for key, value in self._extract_cookie_pairs_from_header(cookie_text):
            if str(key or "").strip() == "unb":
                user_id = str(value or "").strip() or None
                break

        cookie_health_info: dict[str, Any] = {"healthy": False, "message": "未检查", "score": 0}
        try:
            if cookie_text:
                from src.core.cookie_health import CookieHealthChecker

                if self._shared_cookie_checker is None:
                    self._shared_cookie_checker = CookieHealthChecker(cookie_text, timeout_seconds=5.0)
                else:
                    self._shared_cookie_checker.cookie_text = cookie_text
                _ck_result = self._shared_cookie_checker.check_sync(force=False)
                cookie_health_info = {
                    "healthy": bool(_ck_result.get("healthy")),
                    "message": _ck_result.get("message", ""),
                    "score": 100 if _ck_result.get("healthy") else 0,
                }
            else:
                cookie_health_info = {"healthy": False, "message": "Cookie 未配置", "score": 0}
        except Exception:
            pass

        cc_configured = self._is_cookie_cloud_configured()

        return {
            "success": True,
            "service": dict(self._service_state),
            "module": module_status,
            "cookie_exists": bool(cookie.get("success", False)),
            "cookie_valid": bool(cookie.get("success", False)),
            "cookie_length": int(cookie.get("length", 0) or 0),
            "cookie_health": cookie_health_info,
            "xianyu_connected": xianyu_connected,
            "token_available": token_available,
            "token_error": token_error,
            "cookie_update_required": cookie_update_required,
            "cookie_cloud_configured": cc_configured,
            "slider_auto_solve_enabled": bool(
                get_config()
                .get_section("messages", {})
                .get("ws", {})
                .get("slider_auto_solve", {})
                .get("enabled", False)
            ),
            "user_id": user_id,
            "last_token_refresh": risk_control.get("last_event_at") if token_error is None else None,
            "service_start_time": self._service_started_at,
            "instance_id": self._instance_id,
            "project_root": str(self.project_root),
            "python_exec": self._python_exec,
            "started_at": self._service_started_at,
            "route_stats": route_stat_payload,
            "route_stats_by_courier": route_stats_by_courier,
            "message_stats": message_stats,
            "xianguanjia": xgj_settings,
            "risk_control": risk_control,
            "recovery": recovery,
            "recovery_stage": recovery_stage,
            "next_retry_at": next_retry_at,
            "risk_signals": risk_signals,
            "system_running": alive_count > 0,
            "alive_count": alive_count,
            "total_modules": total_modules,
            "service_status": service_status,
        }

    def service_control(self, action: str) -> dict[str, Any]:
        act = str(action or "").strip().lower()
        if act not in {"suspend", "resume", "stop", "start"}:
            return {"success": False, "error": f"Unsupported action: {act}"}

        if act == "suspend":
            stop_result = self.module_console.control(action="stop", target="all")
            self._service_state["suspended"] = True
            self._service_state["stopped"] = False
            self._service_state["updated_at"] = _now_iso()
            return {
                "success": True,
                "action": act,
                "status": "suspended",
                "message": "服务已挂起",
                "result": stop_result,
                "service": dict(self._service_state),
            }

        if act == "stop":
            stop_result = self.module_console.control(action="stop", target="all")
            self._service_state["suspended"] = False
            self._service_state["stopped"] = True
            self._service_state["updated_at"] = _now_iso()
            return {
                "success": True,
                "action": act,
                "status": "stopped",
                "message": "服务已停止",
                "result": stop_result,
                "service": dict(self._service_state),
            }

        start_result = self.module_console.control(action="start", target="all")
        self._service_state["suspended"] = False
        self._service_state["stopped"] = False
        self._service_state["updated_at"] = _now_iso()
        return {
            "success": True,
            "action": act,
            "status": "running",
            "message": "服务已恢复运行" if act == "resume" else "服务已启动",
            "result": start_result,
            "service": dict(self._service_state),
        }

    def service_recover(self, target: str = "presales") -> dict[str, Any]:
        tgt = str(target or "presales").strip().lower()
        if tgt not in MODULE_TARGETS:
            return {"success": False, "error": f"Unsupported target: {tgt}"}

        result = self.module_console.control(action="recover", target=tgt)
        has_error = bool(result.get("error")) if isinstance(result, dict) else True
        status = self.service_status()
        return {
            "success": not has_error,
            "target": tgt,
            "action": "recover",
            "result": result,
            "service_status": status.get("service_status"),
            "xianyu_connected": bool(status.get("xianyu_connected", False)),
            "token_error": status.get("token_error"),
            "cookie_update_required": bool(status.get("cookie_update_required", False)),
            "message": "售前链路恢复完成" if not has_error else f"恢复失败: {result.get('error', 'unknown')}",
        }

    def service_auto_fix(self) -> dict[str, Any]:
        actions: list[str] = []
        status_before = self.service_status()
        svc_state = str(status_before.get("service_status") or "")

        if svc_state == "stopped":
            _ = self.service_control("start")
            actions.append("start_service")
        elif svc_state == "suspended":
            _ = self.service_control("resume")
            actions.append("resume_service")

        if bool(status_before.get("cookie_update_required", False)):
            return {
                "success": False,
                "action": "auto_fix",
                "actions": actions,
                "needs_cookie_update": True,
                "message": "当前为鉴权失效，需先更新 Cookie，系统无法自动修复此项。",
                "status_before": status_before,
                "status_after": self.service_status(),
            }

        recover = self.service_recover("presales")
        actions.append("recover_presales")
        check = self.module_console.check(skip_gateway=True)
        status_after = self.service_status()

        can_work = bool(status_after.get("xianyu_connected", False)) and not bool(
            status_after.get("cookie_update_required", False)
        )
        return {
            "success": bool(can_work),
            "action": "auto_fix",
            "actions": actions,
            "recover": recover,
            "doctor": check,
            "status_before": status_before,
            "status_after": status_after,
            "needs_cookie_update": bool(status_after.get("cookie_update_required", False)),
            "message": "自动修复完成" if can_work else "已执行自动修复，但仍需检查 Cookie 或平台风控状态。",
        }


# Embedded HTML hack removed. UI is strictly served from client/dist now.
