"""轻量后台可视化与模块控制服务（分离版）。"""

from __future__ import annotations

import argparse
import json
import logging
import mimetypes
import os
import sqlite3
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from src.core.config import get_config
from src.dashboard.module_console import ModuleConsole
from src.dashboard.repository import DashboardRepository, LiveDashboardDataSource
from src.dashboard.router import RouteContext, dispatch_delete, dispatch_get, dispatch_post, dispatch_put
from src.dashboard.mimic_ops import MimicOps, _error_payload

import hashlib
import re
import gzip as _gzip_mod

from src.dashboard.config_service import read_system_config as _read_system_config
from src.dashboard.mimic_ops import _safe_int

logger = logging.getLogger(__name__)

# Embedded HTML hack removed. UI is strictly served from client/dist now.

_product_image_cache: dict[str, tuple[str, float]] = {}
_PRODUCT_IMAGE_CACHE_TTL = 1800


class DashboardHandler(BaseHTTPRequestHandler):
    repo: DashboardRepository
    module_console: ModuleConsole
    mimic_ops: MimicOps

    def _send_cors_headers(self) -> None:
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self._send_cors_headers()
        self.send_header("Content-Length", "0")
        self.end_headers()

    def _send_json(self, payload: Any, status: int = 200) -> None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self._send_cors_headers()
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _send_html(self, html: str, status: int = 200) -> None:
        data = html.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _send_bytes(self, data: bytes, content_type: str, status: int = 200, download_name: str | None = None) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        if download_name:
            self.send_header("Content-Disposition", f'attachment; filename="{download_name}"')
        self.end_headers()
        self.wfile.write(data)

    @staticmethod
    def _enrich_product_images(
        resp_data: dict[str, Any],
        base_url: str,
        app_key: str,
        app_secret: str,
        mode: str,
        seller_id: str,
    ) -> None:
        """Inject pic_url into product list response by fetching detail API with caching."""
        try:
            products = resp_data.get("data", {}).get("list", [])
            if not products:
                return
        except (AttributeError, TypeError):
            return

        now = time.time()
        to_fetch: list[str] = []

        for p in products:
            pid = str(p.get("product_id", ""))
            if not pid:
                continue
            cached = _product_image_cache.get(pid)
            if cached and (now - cached[1]) < _PRODUCT_IMAGE_CACHE_TTL:
                p["pic_url"] = cached[0]
            else:
                to_fetch.append(pid)

        if not to_fetch:
            return

        import httpx

        from src.integrations.xianguanjia.signing import (
            sign_business_request,
            sign_open_platform_request,
        )

        try:
            with httpx.Client(timeout=10.0) as hc:
                for pid in to_fetch:
                    try:
                        try:
                            pid_val: int | str = int(pid)
                        except (ValueError, TypeError):
                            pid_val = pid
                        detail_body = json.dumps({"product_id": pid_val}, ensure_ascii=False)
                        ts = str(int(time.time()))
                        if mode == "business" and seller_id:
                            sig = sign_business_request(
                                app_key=app_key,
                                app_secret=app_secret,
                                seller_id=seller_id,
                                timestamp=ts,
                                body=detail_body,
                            )
                        else:
                            sig = sign_open_platform_request(
                                app_key=app_key,
                                app_secret=app_secret,
                                timestamp=ts,
                                body=detail_body,
                            )
                        detail_resp = hc.post(
                            f"{base_url}/api/open/product/detail",
                            params={"appid": app_key, "timestamp": ts, "sign": sig},
                            content=detail_body,
                            headers={"Content-Type": "application/json"},
                        )
                        detail = detail_resp.json()
                        pic_url = ""
                        detail_data = detail.get("data", {}) or {}
                        shops = detail_data.get("publish_shop")
                        shop_iter: list[dict[str, Any]] = []
                        if isinstance(shops, list):
                            shop_iter = shops
                        elif isinstance(shops, dict):
                            shop_iter = [v for v in shops.values() if isinstance(v, dict)]
                        for shop in shop_iter:
                            imgs = shop.get("images", [])
                            if isinstance(imgs, list) and imgs:
                                pic_url = str(imgs[0])
                                break
                        if not pic_url:
                            imgs_top = detail_data.get("images", [])
                            if isinstance(imgs_top, list) and imgs_top:
                                pic_url = str(imgs_top[0])
                        _product_image_cache[pid] = (pic_url, time.time())
                    except Exception:
                        logger.debug("Failed to fetch product detail for %s", pid)
                        _product_image_cache[pid] = ("", time.time())
        except Exception:
            logger.debug("httpx client error during image enrichment", exc_info=True)

        for p in products:
            pid = str(p.get("product_id", ""))
            cached = _product_image_cache.get(pid)
            if cached and not p.get("pic_url"):
                p["pic_url"] = cached[0]

    def _build_publish_config(self) -> dict[str, Any]:
        """构建包含 xianguanjia + oss 的发布配置，供 publish_item/publish_batch 使用。"""
        return self.mimic_ops._xianguanjia_service_config()

    def _handle_listing_preview(self, body: dict[str, Any]) -> dict[str, Any]:
        """生成自动上架预览。"""
        try:
            import asyncio

            from src.modules.listing.auto_publish import AutoPublishService

            service = AutoPublishService(config=self.mimic_ops._xianguanjia_service_config())
            loop = asyncio.new_event_loop()
            try:
                return loop.run_until_complete(service.generate_preview(body))
            finally:
                loop.close()
        except Exception as e:
            return {"ok": False, "step": "error", "error": str(e)}

    def _handle_listing_publish(self, body: dict[str, Any]) -> dict[str, Any]:
        """执行自动上架。"""
        try:
            sys_cfg = _read_system_config()
            ap_cfg = sys_cfg.get("auto_publish", {})
            if not ap_cfg.get("enabled", False):
                return {"ok": False, "error": "自动上架未启用，请在设置中开启"}

            import asyncio

            from src.integrations.xianguanjia.open_platform_client import OpenPlatformClient
            from src.modules.listing.auto_publish import AutoPublishService

            cfg = self.mimic_ops._xianguanjia_service_config().get("xianguanjia", {})
            app_key = str(cfg.get("app_key", "")).strip()
            app_secret = str(cfg.get("app_secret", "")).strip()
            if not app_key or not app_secret:
                return {"ok": False, "step": "init", "error": "闲管家 API 未配置"}

            api_client = OpenPlatformClient(
                base_url=str(cfg.get("base_url", "https://open.goofish.pro")).strip(),
                app_key=app_key,
                app_secret=app_secret,
            )
            service = AutoPublishService(
                api_client=api_client,
                config=self.mimic_ops._xianguanjia_service_config(),
            )

            preview_data = body.get("preview_data")
            loop = asyncio.new_event_loop()
            try:
                if preview_data and isinstance(preview_data, dict):
                    return loop.run_until_complete(service.publish_from_preview(preview_data))
                return loop.run_until_complete(service.publish(body))
            finally:
                loop.close()
        except Exception as e:
            return {"ok": False, "step": "error", "error": str(e)}

    def _read_json_body(self) -> dict[str, Any]:
        try:
            content_len = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            content_len = 0
        if content_len <= 0:
            return {}
        raw = self.rfile.read(content_len)
        if not raw:
            return {}
        try:
            data = json.loads(raw.decode("utf-8"))
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}

    def _read_form_or_json_body(self) -> dict[str, Any]:
        content_type = str(self.headers.get("Content-Type", "")).lower()
        content_encoding = str(self.headers.get("Content-Encoding", "")).lower()
        try:
            content_len = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            content_len = 0
        if content_len <= 0:
            return {}
        raw = self.rfile.read(content_len)
        if not raw:
            return {}
        if "gzip" in content_encoding:
            try:
                raw = _gzip_mod.decompress(raw)
            except Exception:
                return {}
        if "application/json" in content_type:
            try:
                data = json.loads(raw.decode("utf-8", errors="ignore"))
                return data if isinstance(data, dict) else {}
            except Exception:
                return {}
        try:
            parsed = parse_qs(raw.decode("utf-8", errors="ignore"))
            return {k: v[0] if len(v) == 1 else v for k, v in parsed.items()}
        except Exception:
            return {}

    def _read_multipart_files(self) -> list[tuple[str, bytes]]:
        content_type = self.headers.get("Content-Type", "")
        if "multipart/form-data" not in content_type:
            return []
        try:
            content_length = int(self.headers.get("Content-Length", "0"))
            if content_length <= 0:
                return []
            raw_data = self.rfile.read(content_length)
        except Exception:
            return []
        if not raw_data:
            return []

        from email import policy
        from email.parser import BytesParser

        # 构造 MIME 外壳，让 parsebytes 可以解析仅 body 的 multipart 数据。
        if raw_data.lstrip().lower().startswith(b"content-type:"):
            mime_raw = raw_data
        else:
            mime_raw = b"".join(
                [
                    f"Content-Type: {content_type}\r\n".encode("utf-8", errors="ignore"),
                    b"MIME-Version: 1.0\r\n\r\n",
                    raw_data,
                ]
            )

        try:
            msg = BytesParser(policy=policy.default).parsebytes(mime_raw)
        except Exception:
            return []

        files: list[tuple[str, bytes]] = []
        for part in msg.walk():
            if part.is_multipart():
                continue
            disposition = str(part.get_content_disposition() or "").strip().lower()
            if disposition not in {"attachment", "form-data"}:
                continue
            filename = part.get_filename()
            if not filename:
                continue
            payload = part.get_payload(decode=True)
            if payload is None:
                payload = b""
            if isinstance(payload, str):
                payload = payload.encode("utf-8", errors="ignore")
            if isinstance(payload, bytearray):
                payload = bytes(payload)
            if not isinstance(payload, bytes):
                continue
            files.append((str(filename), payload))
        return files

    def _make_xgj_client(self):
        """Create an OpenPlatformClient if credentials are configured, else return None."""
        try:
            from src.integrations.xianguanjia.open_platform_client import OpenPlatformClient

            xgj_cfg = self.mimic_ops._xianguanjia_service_config().get("xianguanjia", {})
            app_key = str(xgj_cfg.get("app_key", "")).strip()
            app_secret = str(xgj_cfg.get("app_secret", "")).strip()
            if not (app_key and app_secret):
                return None
            client_fields = {"base_url", "app_key", "app_secret", "timeout", "mode", "seller_id"}
            kwargs = {k: v for k, v in xgj_cfg.items() if k in client_fields and v}
            return OpenPlatformClient(**kwargs)
        except Exception:
            return None

    def _get_live_dashboard(self) -> LiveDashboardDataSource:
        return LiveDashboardDataSource(self._make_xgj_client)

    def _enrich_summary_with_message_and_order_stats(self, result: dict[str, Any]) -> None:
        """Merge inquiries, reply_rate_pct, paid_order_count, conversion_rate_pct into summary."""
        try:
            status = self.mimic_ops.service_status()
            msg = status.get("message_stats") or {}
            today_inquiries = int(msg.get("today_conversations", 0) or 0)
            today_replied = int(msg.get("today_replied", 0) or 0)
            result["inquiries"] = today_inquiries
            result["total_replied"] = today_replied
            result["reply_rate_pct"] = (
                round(100.0 * today_replied / today_inquiries, 1) if today_inquiries else 0.0
            )
            result["total_inquiries"] = int(msg.get("total_conversations", 0) or 0)
            result["total_replied_all"] = int(msg.get("total_replied", 0) or 0)
        except Exception:
            result.setdefault("inquiries", 0)
            result.setdefault("total_replied", 0)
            result.setdefault("reply_rate_pct", 0.0)
        try:
            agg = self.mimic_ops.get_dashboard_readonly_aggregate()
            if isinstance(agg, dict) and agg.get("success"):
                sections = agg.get("sections") or {}
                po = sections.get("product_operations") or {}
                summary = po.get("summary") or {}
                result["paid_order_count"] = summary.get("paid_order_count")
                result["conversion_rate_pct"] = summary.get("conversion_rate_pct")
        except Exception:
            result.setdefault("paid_order_count", None)
            result.setdefault("conversion_rate_pct", None)

    def _legacy_dashboard_payload(self, path: str, query: dict[str, list[str]]) -> dict[str, Any]:
        live = self._get_live_dashboard()
        try:
            if path == "/api/summary":
                result = live.get_summary()
                if result.get("source") == "xianguanjia_api":
                    self._enrich_summary_with_message_and_order_stats(result)
                    return result
        except Exception:
            logger.debug("LiveDashboard summary failed, falling back to local DB", exc_info=True)

        try:
            if path == "/api/top-products":
                limit = _safe_int((query.get("limit") or ["12"])[0], default=12, min_value=1, max_value=200)
                result = live.get_top_products(limit=limit)
                if result:
                    return {"products": result, "source": "xianguanjia_api"}
        except Exception:
            logger.debug("LiveDashboard top-products failed, falling back", exc_info=True)

        try:
            if path == "/api/recent-operations":
                limit = _safe_int((query.get("limit") or ["20"])[0], default=20, min_value=1, max_value=200)
                result = live.get_recent_operations(limit=limit)
                if result:
                    return {"operations": result, "source": "xianguanjia_api"}
        except Exception:
            logger.debug("LiveDashboard recent-operations failed, falling back", exc_info=True)

        try:
            if path == "/api/trend":
                metric = (query.get("metric") or ["orders"])[0]
                days = _safe_int((query.get("days") or ["30"])[0], default=30, min_value=1, max_value=120)
                result = live.get_trend(metric=metric, days=days)
                if result:
                    return {"trend": result, "source": "xianguanjia_api"}
        except Exception:
            logger.debug("LiveDashboard trend failed, falling back", exc_info=True)

        if path == "/api/summary":
            result = self.repo.get_summary()
            self._enrich_summary_with_message_and_order_stats(result)
            return result
        if path == "/api/trend":
            metric = (query.get("metric") or ["views"])[0]
            days = _safe_int((query.get("days") or ["30"])[0], default=30, min_value=1, max_value=120)
            if metric == "replies":
                try:
                    status = self.mimic_ops.service_status()
                    daily = (status.get("message_stats") or {}).get("daily_replies", {})
                    trend = [{"date": d, "value": c} for d, c in sorted(daily.items())]
                    return {"trend": trend, "source": "workflow_db"}
                except Exception:
                    return {"trend": [], "source": "workflow_db"}
            return self.repo.get_trend(metric=metric, days=days)
        if path == "/api/recent-operations":
            limit = _safe_int((query.get("limit") or ["20"])[0], default=20, min_value=1, max_value=200)
            return self.repo.get_recent_operations(limit=limit)
        limit = _safe_int((query.get("limit") or ["12"])[0], default=12, min_value=1, max_value=200)
        return self.repo.get_top_products(limit=limit)

    def _aggregate_dashboard_payload(self, path: str) -> dict[str, Any] | None:
        aggregate_query = getattr(self.mimic_ops, "get_dashboard_readonly_aggregate", None)
        if not callable(aggregate_query):
            return None

        aggregate = aggregate_query()
        if not isinstance(aggregate, dict):
            return None
        if not aggregate.get("success"):
            return aggregate

        sections = aggregate.get("sections") if isinstance(aggregate.get("sections"), dict) else {}
        panel_map = {
            "/api/summary": "operations_funnel_overview",
            "/api/trend": "fulfillment_efficiency",
            "/api/recent-operations": "exception_priority_pool",
            "/api/top-products": "product_operations",
        }
        key = panel_map.get(path, "operations_funnel_overview")
        panel_payload = sections.get(key) if isinstance(sections.get(key), dict) else {}
        return {
            "success": True,
            "readonly": True,
            "source": "virtual_goods_service.get_dashboard_metrics",
            "view": key,
            "data": panel_payload,
        }

    _CC_UUID_RE = re.compile(r"^[a-zA-Z0-9_-]+$")

    def _handle_cookie_cloud(self, sub_path: str, method: str) -> None:
        cc_dir = Path(__file__).resolve().parents[1] / "server" / "data" / "cookie_cloud"
        cc_dir.mkdir(parents=True, exist_ok=True)

        if sub_path == "/update" and method == "POST":
            body = self._read_form_or_json_body()
            encrypted = str(body.get("encrypted", "")).strip()
            uuid_val = str(body.get("uuid", "")).strip()
            crypto_type = str(body.get("crypto_type", "legacy")).strip()
            if not encrypted or not uuid_val or not self._CC_UUID_RE.match(uuid_val):
                self._send_json({"action": "error"}, status=400)
                return
            fp = cc_dir / f"{uuid_val}.json"
            fp.write_text(
                json.dumps({"encrypted": encrypted, "crypto_type": crypto_type}),
                encoding="utf-8",
            )
            cookie_applied = self._try_instant_cookie_apply(encrypted, uuid_val)
            self._send_json({"action": "done", "cookie_applied": cookie_applied})
            return

        m = re.match(r"^/get/([a-zA-Z0-9_-]+)$", sub_path)
        if m:
            uuid_val = m.group(1)
            fp = cc_dir / f"{uuid_val}.json"
            if not fp.exists():
                self._send_json({"error": "Not Found"}, status=404)
                return
            try:
                data = json.loads(fp.read_text(encoding="utf-8"))
            except Exception:
                self._send_json({"error": "Data corrupt"}, status=500)
                return
            body = self._read_form_or_json_body() if method == "POST" else {}
            pwd = str(body.get("password", "")).strip() if body else ""
            if pwd and data.get("encrypted"):
                try:
                    from src.core.cookie_grabber import CookieGrabber

                    key_hash = hashlib.md5(f"{uuid_val}-{pwd}".encode()).hexdigest()[:16]
                    decrypted = CookieGrabber._decrypt_cookiecloud(data["encrypted"], key_hash)
                    if decrypted:
                        self._send_json(decrypted)
                        return
                except Exception:
                    pass
            self._send_json(data)
            return

        if sub_path in ("", "/", "/health"):
            self._send_json({"status": "ok", "service": "cookiecloud-embedded"})
            return

        self._send_json({"error": "Not Found"}, status=404)

    @staticmethod
    def _read_cc_credentials() -> tuple[str, str]:
        """Read CookieCloud uuid and password from env or system_config.json."""
        uuid_val = os.environ.get("COOKIE_CLOUD_UUID", "").strip()
        password = os.environ.get("COOKIE_CLOUD_PASSWORD", "").strip()
        if not uuid_val or not password:
            try:
                cfg_path = Path(__file__).resolve().parents[1] / "data" / "system_config.json"
                if cfg_path.exists():
                    cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
                    cc = cfg.get("cookie_cloud", {}) if isinstance(cfg.get("cookie_cloud"), dict) else {}
                    uuid_val = uuid_val or str(cc.get("cookie_cloud_uuid") or cfg.get("cookie_cloud_uuid", "")).strip()
                    password = (
                        password or str(cc.get("cookie_cloud_password") or cfg.get("cookie_cloud_password", "")).strip()
                    )
            except Exception:
                pass
        return uuid_val, password

    def _try_instant_cookie_apply(self, encrypted: str, uuid_val: str) -> bool:
        """After /cookie-cloud/update writes data, immediately decrypt and apply if UUID matches."""
        cfg_uuid, cfg_pwd = self._read_cc_credentials()
        if not cfg_pwd or not cfg_uuid or uuid_val != cfg_uuid:
            return False
        try:
            from src.core.cookie_grabber import CookieGrabber

            key_hash = hashlib.md5(f"{uuid_val}-{cfg_pwd}".encode()).hexdigest()[:16]
            cookie_data = CookieGrabber._decrypt_cookiecloud(encrypted, key_hash)
            if not cookie_data:
                return False

            target_domains = {".goofish.com", ".taobao.com", ".tmall.com", "goofish.com", "taobao.com"}
            parts: list[str] = []
            for domain, cookies_list in cookie_data.items():
                domain_lower = domain.lower().strip(".")
                if not any(domain_lower.endswith(d.strip(".")) for d in target_domains):
                    continue
                if isinstance(cookies_list, list):
                    for ck in cookies_list:
                        name = str(ck.get("name", "")).strip()
                        value = str(ck.get("value", "")).strip()
                        if name and value:
                            parts.append(f"{name}={value}")
                elif isinstance(cookies_list, dict):
                    for name, value in cookies_list.items():
                        if str(name).strip() and str(value).strip():
                            parts.append(f"{str(name).strip()}={str(value).strip()}")

            if not parts:
                return False

            cookie_str = "; ".join(parts)
            result = self.mimic_ops.update_cookie(cookie_str, auto_recover=True)
            applied = bool(result.get("success"))
            if applied:
                logger.info(f"CookieCloud instant apply: {len(parts)} cookies applied")
            return applied
        except Exception as exc:
            logger.debug(f"CookieCloud instant apply failed: {exc}")
            return False

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)

        try:
            if path.startswith("/cookie-cloud/") or path == "/cookie-cloud":
                self._handle_cookie_cloud(path[len("/cookie-cloud") :].rstrip("/") or "/", method="GET")
                return

            # --- Route dispatch (decorator-registered routes) ---
            _ctx = RouteContext(
                _handler=self,
                path=path,
                query=query,
            )
            if dispatch_get(path, _ctx):
                return

            if path in {"/", "/cookie", "/test", "/logs", "/logs/realtime"}:
                self._serve_spa_file(path)
                return

            # ---------- vendor static files (Chart.js etc.) ----------
            if path.startswith("/vendor/"):
                self._serve_vendor_file(path)
                return

            # ---------- SPA static file serving ----------
            if path.startswith("/api/") or path == "/not-found":
                self._send_json(_error_payload("Not Found", code="NOT_FOUND"), status=404)
                return

            self._serve_spa_file(path)

        except sqlite3.Error as e:
            self._send_json(_error_payload(f"Database error: {e}", code="DATABASE_ERROR"), status=500)
        except Exception as e:  # pragma: no cover - safety net
            self._send_json(_error_payload(str(e), code="INTERNAL_ERROR"), status=500)

    def _serve_spa_file(self, path: str) -> None:
        """Serve React SPA static files from client/dist/."""
        dist_dir = Path(__file__).resolve().parents[1] / "client" / "dist"
        if not dist_dir.exists():
            self._send_html(
                "<html><body><h1>Dashboard Not Built</h1><p>Please run <code>npm run build</code> in the <code>client/</code> directory.</p></body></html>"
            )
            return

        file_path = dist_dir / path.lstrip("/")
        if file_path.is_file():
            content_type, _ = mimetypes.guess_type(str(file_path))
            content_type = content_type or "application/octet-stream"
            data = file_path.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(data)))
            if "/assets/" in path:
                self.send_header("Cache-Control", "public, max-age=31536000, immutable")
            self.end_headers()
            self.wfile.write(data)
            return

        index_html = dist_dir / "index.html"
        if index_html.is_file():
            self._send_html(index_html.read_text(encoding="utf-8"))
        else:
            self._send_html("<html><body><h1>Dashboard Error</h1><p>index.html missing.</p></body></html>")

    def _serve_vendor_file(self, path: str) -> None:
        """Serve bundled vendor files from src/dashboard/vendor/ (e.g. Chart.js)."""
        filename = Path(path.lstrip("/")).name
        if not filename or ".." in path:
            self._send_json(_error_payload("Not Found", code="NOT_FOUND"), status=404)
            return
        vendor_dir = Path(__file__).resolve().parent / "dashboard" / "vendor"
        file_path = vendor_dir / filename
        if not file_path.is_file():
            self._send_json(_error_payload("Not Found", code="NOT_FOUND"), status=404)
            return
        content_type, _ = mimetypes.guess_type(str(file_path))
        content_type = content_type or "application/octet-stream"
        data = file_path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "public, max-age=604800")
        self.end_headers()
        self.wfile.write(data)

    def do_PUT(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path
        try:
            # --- Route dispatch (decorator-registered routes) ---
            _ctx = RouteContext(
                _handler=self,
                path=path,
                query=parse_qs(parsed.query),
            )
            if dispatch_put(path, _ctx):
                return

            self._send_json(_error_payload("Not Found", code="NOT_FOUND"), status=404)
        except Exception as e:
            self._send_json(_error_payload(str(e), code="INTERNAL_ERROR"), status=500)

    def do_DELETE(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path
        try:
            _ctx = RouteContext(
                _handler=self,
                path=path,
                query=parse_qs(parsed.query),
            )
            if dispatch_delete(path, _ctx):
                return
            self._send_json(_error_payload("Not Found", code="NOT_FOUND"), status=404)
        except Exception as e:
            self._send_json(_error_payload(str(e), code="INTERNAL_ERROR"), status=500)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path

        try:
            if path.startswith("/cookie-cloud/") or path == "/cookie-cloud":
                self._handle_cookie_cloud(path[len("/cookie-cloud") :].rstrip("/") or "/", method="POST")
                return

            # --- Route dispatch (decorator-registered routes) ---
            _ctx = RouteContext(
                _handler=self,
                path=path,
                query=parse_qs(urlparse(self.path).query),
            )
            if dispatch_post(path, _ctx):
                return

            self._send_json(_error_payload("Not Found", code="NOT_FOUND"), status=404)
        except Exception as e:  # pragma: no cover - safety net
            self._send_json(_error_payload(str(e), code="INTERNAL_ERROR"), status=500)

    _QUIET_PREFIXES = (
        "/api/update/status",
        "/api/dashboard/summary",
        "/api/system/status",
        "/api/summary",
        "/api/status",
        "/api/trend",
        "/api/top-products",
        "/api/recent-operations",
        "/api/slider/stats",
        "/api/slider/events",
        "/healthz",
        "/assets/",
        "/favicon",
    )

    def log_message(self, format: str, *args: Any) -> None:
        from loguru import logger as _loguru

        path = getattr(self, "path", "").split("?")[0]
        code = str(args[1]) if len(args) >= 2 else ""
        if path.startswith(self._QUIET_PREFIXES) and code == "200":
            return
        reqline = str(args[0]).split(" HTTP/")[0] if args else ""
        _loguru.info("{} → {}", reqline or path, code)


def run_server(host: str = "127.0.0.1", port: int = 8091, db_path: str | None = None) -> None:
    import signal

    import src.dashboard.routes  # noqa: F401 — trigger route registration

    config = get_config()
    resolved_db = db_path or config.database.get("path", "data/agent.db")

    Path(resolved_db).parent.mkdir(parents=True, exist_ok=True)
    DashboardHandler.repo = DashboardRepository(resolved_db)
    DashboardHandler.module_console = ModuleConsole(project_root=Path(__file__).resolve().parents[1])
    DashboardHandler.mimic_ops = MimicOps(
        project_root=Path(__file__).resolve().parents[1],
        module_console=DashboardHandler.module_console,
    )

    # Cookie 静默自动刷新
    auto_refresh_enabled = os.environ.get("COOKIE_AUTO_REFRESH", "true").lower() in ("true", "1", "yes")
    refresher = None
    if auto_refresh_enabled:
        try:
            from src.core.cookie_grabber import CookieAutoRefresher

            interval = int(os.environ.get("COOKIE_REFRESH_INTERVAL", "30"))
            mimic_ops = DashboardHandler.mimic_ops

            def _on_refreshed(cookie: str) -> None:
                try:
                    mimic_ops.update_cookie(cookie, auto_recover=True)
                except Exception as exc:
                    logger.error(f"Cookie 自动刷新回调失败: {exc}")

            refresher = CookieAutoRefresher(interval_minutes=interval, on_refreshed=_on_refreshed)
            refresher.start()
            DashboardHandler._cookie_auto_refresher = refresher
        except Exception as exc:
            logger.error(f"Cookie 自动刷新启动失败: {exc}")

    # 自动改价/催单轮询
    price_poller = None
    sys_cfg = _read_system_config()
    apm_cfg = sys_cfg.get("auto_price_modify", {})
    remind_cfg = sys_cfg.get("order_reminder", {})
    if apm_cfg.get("enabled") or remind_cfg.get("auto_remind_enabled"):
        from src.modules.orders.auto_price_poller import AutoPricePoller, set_price_poller

        poll_interval = int(apm_cfg.get("poll_interval_seconds", 15))
        price_poller = AutoPricePoller(get_config_fn=_read_system_config, interval=poll_interval)
        price_poller.start()
        set_price_poller(price_poller)
        DashboardHandler._price_poller = price_poller

    server = ThreadingHTTPServer((host, port), DashboardHandler)

    shutdown_event = threading.Event()

    def _shutdown(signum, frame):
        logger.info("收到信号 %s，正在关闭...", signum)
        shutdown_event.set()
        if refresher:
            refresher.stop()
        if price_poller:
            price_poller.stop()
        server.shutdown()

    signal.signal(signal.SIGTERM, _shutdown)
    signal.signal(signal.SIGINT, _shutdown)

    # -- 看门狗守护线程 --
    module_console = DashboardHandler.module_console
    _wd_restart_count = 0
    _wd_last_restart_at = 0.0
    _WD_COOLDOWN = 1800
    _WD_MAX_RESTARTS = 3
    _WD_INTERVAL = 120

    def _watchdog_loop() -> None:
        nonlocal _wd_restart_count, _wd_last_restart_at
        shutdown_event.wait(60)
        while not shutdown_event.is_set():
            shutdown_event.wait(_WD_INTERVAL)
            if shutdown_event.is_set():
                break
            now_ts = time.time()
            if _wd_restart_count >= _WD_MAX_RESTARTS and (now_ts - _wd_last_restart_at) < _WD_COOLDOWN:
                continue
            if (now_ts - _wd_last_restart_at) >= _WD_COOLDOWN:
                _wd_restart_count = 0

            try:
                status_result = module_console.status(window_minutes=5, limit=5)
                modules = status_result.get("modules") or {}
                presales_running = False
                if isinstance(modules, dict):
                    presales_info = modules.get("presales", {})
                    if isinstance(presales_info, dict):
                        proc = presales_info.get("process", {})
                        presales_running = bool(proc.get("alive", False)) if isinstance(proc, dict) else False
                elif isinstance(modules, list):
                    for m in modules:
                        if isinstance(m, dict) and m.get("name") == "presales" and m.get("status") == "running":
                            presales_running = True
                            break

                if not presales_running:
                    logger.warning("Watchdog: presales 模块未运行，尝试自动启动...")
                    try:
                        module_console._run_module_cli(action="start", target="presales", timeout_seconds=30)
                        _wd_restart_count += 1
                        _wd_last_restart_at = time.time()
                        logger.info("Watchdog: presales 模块已自动启动 (count=%d)", _wd_restart_count)
                    except Exception as start_exc:
                        logger.error("Watchdog: presales 自动启动失败: %s", start_exc)

                    if _wd_restart_count >= _WD_MAX_RESTARTS:
                        try:
                            from src.core.notify import send_system_notification

                            send_system_notification(
                                f"【闲鱼自动化】⚠️ presales 模块连续 {_WD_MAX_RESTARTS} 次异常重启，"
                                f"进入 {_WD_COOLDOWN // 60} 分钟静默期。请检查日志排查问题。",
                                event="watchdog_alert",
                            )
                        except Exception:
                            pass

                if refresher and not refresher.running:
                    logger.warning("Watchdog: CookieAutoRefresher 已停止，尝试重启...")
                    try:
                        refresher.start()
                        logger.info("Watchdog: CookieAutoRefresher 已重启")
                    except Exception as r_exc:
                        logger.error("Watchdog: CookieAutoRefresher 重启失败: %s", r_exc)
            except Exception as wd_exc:
                logger.debug("Watchdog tick error: %s", wd_exc)

    wd_thread = threading.Thread(target=_watchdog_loop, daemon=True, name="watchdog")
    wd_thread.start()

    from loguru import logger as _loguru
    from src.dashboard.router import all_routes

    routes = all_routes()
    total = sum(len(v) for v in routes.values())
    _loguru.info("已注册 {} 个 API 路由", total)
    _loguru.info("Dashboard running: http://{}:{}", host, port)
    _loguru.info("Using database: {}", resolved_db)
    server.serve_forever()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="闲鱼后台可视化服务")
    parser.add_argument("--host", default="127.0.0.1", help="监听地址")
    parser.add_argument("--port", type=int, default=8091, help="监听端口")
    parser.add_argument("--db-path", default=None, help="数据库路径（默认读取配置）")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    run_server(host=args.host, port=args.port, db_path=args.db_path)


if __name__ == "__main__":
    import sys

    sys.modules.setdefault("src.dashboard_server", sys.modules[__name__])
    main()
