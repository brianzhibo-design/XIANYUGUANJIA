"""从闲管家IM Electron应用直接读取Cookie。

闲管家-闲鱼客服聊天 是基于 Chromium 的 Electron 应用，
Cookie 以明文存储在 SQLite 数据库中（encrypted_value 长度为 0）。
本模块以只读模式读取该数据库，避免与运行中的 IM 产生锁冲突。
"""

from __future__ import annotations

import os
import platform
import sqlite3
import subprocess
import time
from pathlib import Path
from typing import Any

from src.core.logger import get_logger

logger = get_logger()

_TARGET_DOMAINS = (".goofish.com", ".taobao.com", ".tmall.com", "goofish.com", "passport.goofish.com")
_KEY_SESSION_COOKIE = "_m_h5_tk"
_MIN_TTL_SECONDS = 300


def _get_data_dir() -> Path | None:
    """Return the goofish-im Electron app data directory (macOS / Windows)."""
    system = platform.system()
    if system == "Darwin":
        return Path.home() / "Library" / "Application Support" / "goofish-im"
    if system == "Windows":
        for env_var in ("APPDATA", "LOCALAPPDATA"):
            base = os.environ.get(env_var, "")
            if base:
                candidate = Path(base) / "goofish-im"
                if candidate.is_dir():
                    return candidate
        for env_var in ("APPDATA", "LOCALAPPDATA"):
            base = os.environ.get(env_var, "")
            if base:
                return Path(base) / "goofish-im"
    return None


def _is_goofish_im_running() -> bool:
    system = platform.system()
    try:
        if system == "Darwin":
            r = subprocess.run(
                ["pgrep", "-f", "闲管家"],
                capture_output=True, timeout=5,
            )
            return r.returncode == 0
        if system == "Windows":
            r = subprocess.run(
                ["tasklist", "/FI", "IMAGENAME eq goofish-im.exe", "/NH"],
                capture_output=True, timeout=5,
            )
            return "goofish-im.exe" in r.stdout.decode("gbk", errors="ignore")
    except Exception:
        pass
    return False


def _find_best_partition(partitions_dir: Path, user_id: str = "") -> Path | None:
    """Find the best cookie partition directory.

    Priority: explicit user_id > numeric-named dir with newest Cookies file.
    """
    if not partitions_dir.is_dir():
        return None

    if user_id:
        candidate = partitions_dir / user_id / "Cookies"
        if candidate.exists():
            return candidate

    best: Path | None = None
    best_mtime: float = 0

    try:
        for entry in partitions_dir.iterdir():
            if not entry.is_dir() or not entry.name.isdigit():
                continue
            cookies_path = entry / "Cookies"
            if cookies_path.exists():
                mtime = cookies_path.stat().st_mtime
                if mtime > best_mtime:
                    best_mtime = mtime
                    best = cookies_path
    except OSError:
        pass

    return best


def _parse_m_h5_tk_ttl(value: str) -> float | None:
    """Parse TTL in seconds from _m_h5_tk value like 'hash_timestamp'."""
    parts = value.split("_")
    if len(parts) >= 2:
        try:
            expire_ts = int(parts[-1]) / 1000.0
            return expire_ts - time.time()
        except (ValueError, OverflowError):
            pass
    return None


def read_goofish_im_cookies(
    user_id: str = "",
    min_ttl: int = _MIN_TTL_SECONDS,
) -> dict[str, Any] | None:
    """Read cookies from the 闲管家IM Electron app's SQLite database.

    Returns dict with keys:
      - cookie_str: semicolon-joined cookie string
      - cookies: dict of name->value
      - source: "goofish_im"
      - m_h5_tk_ttl: remaining TTL in seconds (or None)
    Returns None if cookies cannot be read or are invalid.
    """
    data_dir = _get_data_dir()
    if not data_dir or not data_dir.is_dir():
        logger.debug("goofish_im: data dir not found")
        return None

    partitions_dir = data_dir / "Partitions"
    db_path = _find_best_partition(partitions_dir, user_id)

    if not db_path:
        root_cookies = data_dir / "Cookies"
        if root_cookies.exists():
            db_path = root_cookies

    if not db_path:
        logger.debug("goofish_im: no Cookies database found")
        return None

    try:
        uri = f"file:{db_path}?mode=ro&immutable=1"
        conn = sqlite3.connect(uri, uri=True, timeout=3)
        try:
            rows = conn.execute(
                "SELECT name, value, host_key FROM cookies "
                "WHERE length(value) > 0"
            ).fetchall()
        finally:
            conn.close()
    except (sqlite3.Error, OSError) as exc:
        logger.info(f"goofish_im: SQLite read error: {exc}")
        return None

    cookies: dict[str, str] = {}
    for name, value, host_key in rows:
        host_lower = host_key.lower()
        if not any(host_lower.endswith(d) or host_lower == d.lstrip(".") for d in _TARGET_DOMAINS):
            continue
        if name not in cookies:
            cookies[name] = value

    if not cookies:
        logger.debug("goofish_im: no goofish cookies found in DB")
        return None

    if "unb" not in cookies or "sgcookie" not in cookies:
        logger.info("goofish_im: missing critical auth cookies (unb/sgcookie)")
        return None

    m_h5_tk_ttl: float | None = None
    tk_val = cookies.get(_KEY_SESSION_COOKIE)
    if tk_val:
        m_h5_tk_ttl = _parse_m_h5_tk_ttl(tk_val)
        if m_h5_tk_ttl is not None and m_h5_tk_ttl < min_ttl:
            logger.info(
                f"goofish_im: _m_h5_tk TTL too low ({m_h5_tk_ttl:.0f}s < {min_ttl}s), skipping"
            )
            return None

    cookie_str = "; ".join(f"{k}={v}" for k, v in cookies.items())

    logger.info(
        f"goofish_im: read {len(cookies)} cookies from {db_path.parent.name}, "
        f"_m_h5_tk TTL={m_h5_tk_ttl:.0f}s" if m_h5_tk_ttl is not None else
        f"goofish_im: read {len(cookies)} cookies from {db_path.parent.name}"
    )

    return {
        "cookie_str": cookie_str,
        "cookies": cookies,
        "source": "goofish_im",
        "m_h5_tk_ttl": m_h5_tk_ttl,
        "im_running": _is_goofish_im_running(),
    }


def merge_cookies(
    im_cookies: dict[str, str],
    existing_cookie_str: str,
) -> str:
    """Merge IM cookies with existing cookies. IM values take priority."""
    existing: dict[str, str] = {}
    for pair in existing_cookie_str.split(";"):
        pair = pair.strip()
        if "=" not in pair:
            continue
        name, value = pair.split("=", 1)
        existing[name.strip()] = value.strip()

    merged = dict(existing)
    merged.update(im_cookies)

    return "; ".join(f"{k}={v}" for k, v in sorted(merged.items()))
