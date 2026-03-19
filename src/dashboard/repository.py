"""Dashboard data access — live XianGuanJia API queries with TTL cache, SQLite fallback."""

from __future__ import annotations

import logging
import sqlite3
import threading
import time
from collections.abc import Iterator
from contextlib import closing, contextmanager
from datetime import datetime, timedelta
from typing import Any

logger = logging.getLogger(__name__)

ORDER_STATUS_LABELS: dict[int, str] = {
    11: "待付款",
    12: "待发货",
    21: "已发货",
    22: "已完成",
    23: "已退款",
    24: "已关闭",
}


class _TtlCache:
    """Thread-safe in-memory cache with per-key TTL."""

    def __init__(self, ttl: float = 60.0):
        self._ttl = ttl
        self._store: dict[str, tuple[float, Any]] = {}
        self._lock = threading.Lock()

    def get(self, key: str) -> Any | None:
        with self._lock:
            entry = self._store.get(key)
            if entry and (time.monotonic() - entry[0]) < self._ttl:
                return entry[1]
            return None

    def set(self, key: str, value: Any) -> None:
        with self._lock:
            self._store[key] = (time.monotonic(), value)

    def invalidate(self, key: str | None = None) -> None:
        with self._lock:
            if key:
                self._store.pop(key, None)
            else:
                self._store.clear()


_dashboard_cache = _TtlCache(ttl=60.0)


class LiveDashboardDataSource:
    """Fetches real dashboard data from XianGuanJia open-platform API."""

    def __init__(self, get_client_fn):
        self._get_client = get_client_fn

    def _client(self):
        return self._get_client()

    def _fetch_all_products(self) -> list[dict[str, Any]]:
        cached = _dashboard_cache.get("products_all")
        if cached is not None:
            return cached

        client = self._client()
        if not client:
            return []

        all_items: list[dict[str, Any]] = []
        page = 1
        while True:
            resp = client.list_products({"page_no": page, "page_size": 100})
            if not resp.ok:
                logger.warning("LiveDashboard: list_products failed page=%d: %s", page, resp.error_message)
                break
            data = resp.data if isinstance(resp.data, dict) else {}
            items = data.get("list", [])
            if not isinstance(items, list):
                break
            all_items.extend(items)
            total = data.get("count", len(all_items))
            if len(all_items) >= total or not items:
                break
            page += 1
            if page > 20:
                break

        _dashboard_cache.set("products_all", all_items)
        return all_items

    def _fetch_orders(self, *, page_size: int = 20, status: int | None = None) -> tuple[list[dict], int]:
        cache_key = f"orders_s{status}_ps{page_size}"
        cached = _dashboard_cache.get(cache_key)
        if cached is not None:
            return cached

        client = self._client()
        if not client:
            return [], 0

        payload: dict[str, Any] = {"page_no": 1, "page_size": page_size}
        if status is not None:
            payload["order_status"] = status

        resp = client.list_orders(payload)
        if not resp.ok:
            logger.warning("LiveDashboard: list_orders failed: %s", resp.error_message)
            return [], 0

        data = resp.data if isinstance(resp.data, dict) else {}
        items = data.get("list", [])
        count = int(data.get("count", 0))
        result = (items if isinstance(items, list) else [], count)
        _dashboard_cache.set(cache_key, result)
        return result

    def get_summary(self) -> dict[str, Any]:
        products = self._fetch_all_products()

        active = sum(1 for p in products if isinstance(p, dict) and p.get("product_status") == 22)
        total_sold = sum(int(p.get("sold", 0)) for p in products if isinstance(p, dict))

        _, total_order_count = self._fetch_orders(page_size=1)
        _, pending_count = self._fetch_orders(page_size=1, status=11)

        _, delivered_count = self._fetch_orders(page_size=1, status=12)
        _, shipped_count = self._fetch_orders(page_size=1, status=21)
        _, done_count = self._fetch_orders(page_size=1, status=22)
        paid_order_count = delivered_count + shipped_count + done_count
        conversion_rate_pct = round(paid_order_count / total_order_count * 100, 2) if total_order_count > 0 else 0.0

        return {
            "active_products": active,
            "pending_orders": pending_count,
            "total_sales": total_sold,
            "total_orders": total_order_count,
            "paid_order_count": paid_order_count,
            "conversion_rate_pct": conversion_rate_pct,
            "source": "xianguanjia_api",
        }

    def get_top_products(self, limit: int) -> list[dict[str, Any]]:
        products = self._fetch_all_products()
        on_sale = [p for p in products if isinstance(p, dict) and p.get("product_status") == 22]
        on_sale.sort(key=lambda p: int(p.get("sold", 0)), reverse=True)

        result = []
        for p in on_sale[:limit]:
            images = p.get("images", [])
            pic_url = images[0] if isinstance(images, list) and images else ""
            result.append(
                {
                    "product_id": str(p.get("product_id", "")),
                    "title": str(p.get("title", "")),
                    "sold": int(p.get("sold", 0)),
                    "price": p.get("price", 0),
                    "stock": int(p.get("stock", 0)),
                    "pic_url": pic_url,
                }
            )
        return result

    def get_recent_operations(self, limit: int) -> list[dict[str, Any]]:
        orders, _ = self._fetch_orders(page_size=min(limit, 50))

        result = []
        for order in orders:
            if not isinstance(order, dict):
                continue
            status_code = int(order.get("order_status", 0))
            status_label = ORDER_STATUS_LABELS.get(status_code, f"状态{status_code}")
            title = ""
            goods = order.get("goods")
            if isinstance(goods, dict):
                title = str(goods.get("title", ""))

            order_time = order.get("order_time", "")
            if isinstance(order_time, (int, float)) and order_time > 1000000000:
                order_time = datetime.fromtimestamp(order_time).strftime("%Y-%m-%d %H:%M:%S")

            result.append(
                {
                    "operation_type": f"订单 {status_label}",
                    "status": "success" if status_code in (12, 21, 22) else "pending",
                    "timestamp": str(order_time),
                    "message": title or f"订单 {order.get('order_no', '')}",
                }
            )
        return result

    def get_trend(self, metric: str, days: int) -> list[dict[str, Any]]:
        cache_key = f"trend_{metric}_{days}"
        cached = _dashboard_cache.get(cache_key)
        if cached is not None:
            return cached

        if metric == "sales":
            return self._trend_from_products(days, cache_key)

        client = self._client()
        if not client:
            return self._empty_trend(days)

        now = datetime.now()
        start_ts = int((now - timedelta(days=days)).timestamp())
        end_ts = int(now.timestamp())

        all_orders: list[dict] = []
        page = 1
        while True:
            payload: dict[str, Any] = {
                "page_no": page,
                "page_size": 100,
                "update_time": [start_ts, end_ts],
            }
            resp = client.list_orders(payload)
            if not resp.ok:
                break
            data = resp.data if isinstance(resp.data, dict) else {}
            items = data.get("list", [])
            if not isinstance(items, list) or not items:
                break
            all_orders.extend(items)
            total = int(data.get("count", 0))
            if len(all_orders) >= total:
                break
            page += 1
            if page > 10:
                break

        by_day: dict[str, int] = {}
        for order in all_orders:
            if not isinstance(order, dict):
                continue
            status_code = int(order.get("order_status", 0))
            if metric == "orders":
                pass
            elif metric == "completed" and status_code not in (12, 21, 22):
                continue

            ot = order.get("order_time", 0)
            if isinstance(ot, (int, float)) and ot > 1000000000:
                d = datetime.fromtimestamp(ot).strftime("%Y-%m-%d")
            else:
                d = str(ot)[:10]
            by_day[d] = by_day.get(d, 0) + 1

        result = []
        for i in range(days):
            d = (now - timedelta(days=days - 1 - i)).strftime("%Y-%m-%d")
            result.append({"date": d, "value": by_day.get(d, 0)})

        _dashboard_cache.set(cache_key, result)
        return result

    def _trend_from_products(self, days: int, cache_key: str) -> list[dict[str, Any]]:
        """Sales trend — since XGJ doesn't provide per-day sales, return total as today's value."""
        products = self._fetch_all_products()
        total_sold = sum(int(p.get("sold", 0)) for p in products if isinstance(p, dict))

        now = datetime.now()
        today = now.strftime("%Y-%m-%d")
        result = []
        for i in range(days):
            d = (now - timedelta(days=days - 1 - i)).strftime("%Y-%m-%d")
            result.append({"date": d, "value": total_sold if d == today else 0})

        _dashboard_cache.set(cache_key, result)
        return result

    @staticmethod
    def _empty_trend(days: int) -> list[dict[str, Any]]:
        now = datetime.now()
        return [{"date": (now - timedelta(days=days - 1 - i)).strftime("%Y-%m-%d"), "value": 0} for i in range(days)]


class DashboardRepository:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._ensure_tables()

    def _ensure_tables(self) -> None:
        with self._connect() as conn:
            ver = conn.execute("PRAGMA user_version").fetchone()[0]
            if ver < 1:
                conn.execute("""CREATE TABLE IF NOT EXISTS operation_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT DEFAULT (datetime('now','localtime')),
                    operation TEXT, operation_type TEXT,
                    product_id TEXT, account_id TEXT,
                    status TEXT, details TEXT
                )""")
                conn.execute("""CREATE TABLE IF NOT EXISTS products (
                    product_id TEXT PRIMARY KEY, title TEXT,
                    status TEXT DEFAULT 'active', price REAL, stock INTEGER DEFAULT 0,
                    pic_url TEXT, created_at TEXT DEFAULT (datetime('now','localtime'))
                )""")
                conn.execute("""CREATE TABLE IF NOT EXISTS product_metrics (
                    product_id TEXT PRIMARY KEY, views INTEGER DEFAULT 0,
                    wants INTEGER DEFAULT 0, sales INTEGER DEFAULT 0,
                    inquiries INTEGER DEFAULT 0,
                    timestamp TEXT DEFAULT (datetime('now','localtime')),
                    updated_at TEXT DEFAULT (datetime('now','localtime'))
                )""")
                conn.execute("PRAGMA user_version = 1")

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        with closing(sqlite3.connect(self.db_path)) as conn, conn:
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA busy_timeout=5000")
            yield conn

    def get_summary(self) -> dict[str, Any]:
        with self._connect() as conn:
            total_operations = conn.execute("SELECT COUNT(*) AS c FROM operation_logs").fetchone()["c"]
            today_operations = conn.execute(
                "SELECT COUNT(*) AS c FROM operation_logs WHERE date(timestamp)=date('now','localtime')"
            ).fetchone()["c"]
            active_products = conn.execute("SELECT COUNT(*) AS c FROM products WHERE status='active'").fetchone()["c"]
            sold_products = conn.execute("SELECT COUNT(*) AS c FROM products WHERE status='sold'").fetchone()["c"]
            total_views = conn.execute("SELECT COALESCE(SUM(views),0) AS s FROM product_metrics").fetchone()["s"]
            total_wants = conn.execute("SELECT COALESCE(SUM(wants),0) AS s FROM product_metrics").fetchone()["s"]
            total_sales = conn.execute("SELECT COALESCE(SUM(sales),0) AS s FROM product_metrics").fetchone()["s"]

        return {
            "total_operations": total_operations,
            "today_operations": today_operations,
            "active_products": active_products,
            "sold_products": sold_products,
            "total_views": total_views,
            "total_wants": total_wants,
            "total_sales": total_sales,
            "source": "local_db",
        }

    def get_trend(self, metric: str, days: int) -> list[dict[str, Any]]:
        if metric in ("orders", "completed"):
            return self._trend_from_operation_logs(metric, days)

        allowed = {"views", "wants", "sales", "inquiries"}
        if metric not in allowed:
            metric = "views"

        start_date = (datetime.now() - timedelta(days=days - 1)).strftime("%Y-%m-%d")

        column_map = {"views": "views", "wants": "wants", "sales": "sales", "inquiries": "inquiries"}
        col = column_map[metric]

        sql = f"""
            SELECT date(timestamp) AS d, COALESCE(SUM({col}),0) AS v
            FROM product_metrics
            WHERE date(timestamp) >= ?
            GROUP BY date(timestamp)
            ORDER BY d ASC
        """

        rows_by_day: dict[str, int] = {}
        with self._connect() as conn:
            for row in conn.execute(sql, (start_date,)).fetchall():
                rows_by_day[str(row["d"])] = int(row["v"])

        result = []
        for i in range(days):
            d = (datetime.now() - timedelta(days=days - 1 - i)).strftime("%Y-%m-%d")
            result.append({"date": d, "value": rows_by_day.get(d, 0)})
        return result

    def _trend_from_operation_logs(self, metric: str, days: int) -> list[dict[str, Any]]:
        start_date = (datetime.now() - timedelta(days=days - 1)).strftime("%Y-%m-%d")
        if metric == "completed":
            where = "AND (operation_type LIKE '%已完成%' OR operation_type LIKE '%已发货%' OR status = 'success')"
        else:
            where = ""
        sql = f"""
            SELECT date(timestamp) AS d, COUNT(*) AS v
            FROM operation_logs
            WHERE date(timestamp) >= ? {where}
            GROUP BY date(timestamp)
            ORDER BY d ASC
        """
        rows_by_day: dict[str, int] = {}
        with self._connect() as conn:
            for row in conn.execute(sql, (start_date,)).fetchall():
                rows_by_day[str(row["d"])] = int(row["v"])
        result = []
        for i in range(days):
            d = (datetime.now() - timedelta(days=days - 1 - i)).strftime("%Y-%m-%d")
            result.append({"date": d, "value": rows_by_day.get(d, 0)})
        return result

    def get_recent_operations(self, limit: int) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT operation_type, product_id, account_id, status, timestamp
                FROM operation_logs
                ORDER BY timestamp DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()

        return [dict(row) for row in rows]

    def get_top_products(self, limit: int) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT
                  p.product_id,
                  p.title,
                  p.status,
                  COALESCE(SUM(m.views),0) AS views,
                  COALESCE(SUM(m.wants),0) AS wants,
                  COALESCE(SUM(m.sales),0) AS sales
                FROM products p
                LEFT JOIN product_metrics m ON m.product_id = p.product_id
                GROUP BY p.product_id, p.title, p.status
                ORDER BY wants DESC, views DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()

        return [dict(row) for row in rows]
