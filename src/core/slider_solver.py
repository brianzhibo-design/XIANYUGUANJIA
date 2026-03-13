"""风控滑块自动验证模块。

Phase 2: 自动打开浏览器呈现验证页面
Phase 3: 自动检测并求解滑块验证码（NC 滑块 / 拼图滑块）

安全降级：自动过滑块默认关闭，失败后保持浏览器窗口等用户手动操作。
"""

from __future__ import annotations

import asyncio
import math
import os
import platform
import random
import time
from typing import Any

from src.core.logger import get_logger

logger = get_logger()

_GOOFISH_IM_URL = "https://www.goofish.com/im"
_GOOFISH_DOMAINS = [".goofish.com", ".taobao.com", ".tmall.com"]

NC_SLIDER_SELECTORS = [
    "#nc_1_n1z",
    "#nc_1__scale_text",
    ".nc-lang-cnt",
    "#aliyunCaptcha-sliding-btn",
    ".btn_slide",
    ".scale_text .nc-lang-cnt",
    "#baxia-slideBar .btn_slide",
    "#baxia-dialog-content .btn_slide",
    ".slide-btn",
]

NC_TRACK_SELECTORS = [
    "#nc_1__scale_text",
    ".nc_scale",
    "#aliyunCaptcha-sliding-track",
    ".slide-track",
    "#baxia-slideBar",
    ".nc_wrapper .nc_scale",
]

PUZZLE_SELECTORS = [
    ".yoda-image-slice",
    ".baxia-dialog",
    "#aliyunCaptcha-puzzle",
]

NC_SUCCESS_MARKERS = [
    "验证通过",
    "验证成功",
    "success",
]

_SLIDER_GONE_SELECTORS = [
    "#nc_1_n1z",
    ".btn_slide",
    "#aliyunCaptcha-sliding-btn",
    ".nc-lang-cnt",
    "#baxia-dialog-content",
]

_AUTH_COOKIES = {"unb", "cookie2", "sgcookie"}


def _has_display() -> bool:
    system = platform.system()
    if system in ("Darwin", "Windows"):
        return True
    return bool(os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))


def _get_slider_config(config: dict[str, Any] | None) -> dict[str, Any]:
    ws_cfg = (config or {})
    slider_cfg = ws_cfg.get("slider_auto_solve", {})
    if not isinstance(slider_cfg, dict):
        slider_cfg = {}
    return {
        "enabled": bool(slider_cfg.get("enabled", False)),
        "max_attempts": int(slider_cfg.get("max_attempts", 2)),
        "cooldown_seconds": int(slider_cfg.get("cooldown_seconds", 300)),
        "headless": bool(slider_cfg.get("headless", False)),
    }


def generate_human_trajectory(distance: int) -> list[tuple[int, int, int]]:
    """Generate human-like mouse trajectory for slider drag.

    Returns list of (dx, dy, dt_ms) relative movements.

    Key characteristics matching Alibaba's detection:
    - Total duration 1400-1800ms
    - ease-out-expo speed curve (fast start, slow end)
    - Random vertical jitter +/- 1-3px
    - Occasional micro-retreat (1-2px backward)
    - Initial pause after mouse down (100-300ms)
    """
    if distance <= 0:
        return []

    total_duration_ms = random.randint(1400, 1800)
    num_steps = max(20, distance // 3)

    steps: list[tuple[int, int, int]] = []
    steps.append((0, 0, random.randint(100, 300)))

    prev_x = 0
    for i in range(1, num_steps + 1):
        progress = i / num_steps
        eased = 1 - math.pow(2, -10 * progress) if progress < 1 else 1
        target_x = int(eased * distance)

        if random.random() < 0.08 and i > 3:
            target_x = max(prev_x - random.randint(1, 2), 0)

        dx = target_x - prev_x
        if dx == 0 and i < num_steps:
            continue

        dy = random.choice([-1, 0, 0, 0, 1]) if random.random() < 0.4 else 0
        if i > num_steps * 0.7:
            dy = random.choice([-1, 0, 0, 0, 0, 0, 1])

        dt = max(5, int(total_duration_ms / num_steps))
        if i > num_steps * 0.8:
            dt = int(dt * random.uniform(1.5, 2.5))
        elif i < num_steps * 0.2:
            dt = int(dt * random.uniform(0.5, 0.8))

        dt += random.randint(-3, 3)
        steps.append((dx, dy, max(3, dt)))
        prev_x = target_x

    final_dx = distance - prev_x
    if final_dx != 0:
        steps.append((final_dx, 0, random.randint(30, 80)))

    steps.append((0, 0, random.randint(100, 250)))
    return steps


def find_puzzle_gap_opencv(background_bytes: bytes, slider_bytes: bytes) -> int | None:
    """Use opencv template matching to find the puzzle gap x-coordinate."""
    try:
        import cv2
        import numpy as np
    except ImportError:
        logger.debug("opencv-python not installed, cannot solve puzzle slider")
        return None

    bg_arr = np.frombuffer(background_bytes, np.uint8)
    sl_arr = np.frombuffer(slider_bytes, np.uint8)
    bg_img = cv2.imdecode(bg_arr, cv2.IMREAD_GRAYSCALE)
    sl_img = cv2.imdecode(sl_arr, cv2.IMREAD_GRAYSCALE)

    if bg_img is None or sl_img is None:
        return None

    bg_edge = cv2.Canny(bg_img, 100, 200)
    sl_edge = cv2.Canny(sl_img, 100, 200)

    result = cv2.matchTemplate(bg_edge, sl_edge, cv2.TM_CCOEFF_NORMED)
    _, max_val, _, max_loc = cv2.minMaxLoc(result)

    if max_val < 0.3:
        return None

    return max_loc[0]


async def _find_slider_in_frames(page: Any) -> tuple[Any, Any, str] | None:
    """Search all frames for slider elements. Returns (frame, element, type)."""
    targets = [page] + list(page.frames)
    for frame in targets:
        for sel in NC_SLIDER_SELECTORS:
            try:
                el = await frame.query_selector(sel)
                if el and await el.is_visible():
                    return frame, el, "nc"
            except Exception:
                continue
        for sel in PUZZLE_SELECTORS:
            try:
                el = await frame.query_selector(sel)
                if el and await el.is_visible():
                    return frame, el, "puzzle"
            except Exception:
                continue
    return None


async def _find_track_width(frame: Any) -> int | None:
    for sel in NC_TRACK_SELECTORS:
        try:
            track = await frame.query_selector(sel)
            if track:
                box = await track.bounding_box()
                if box and box.get("width", 0) > 50:
                    return int(box["width"])
        except Exception:
            continue
    return None


async def _check_nc_success(frame: Any, page: Any = None) -> bool:
    try:
        text = await frame.evaluate("() => document.body.innerText")
        if any(m in (text or "") for m in NC_SUCCESS_MARKERS):
            return True
    except Exception:
        pass
    if page:
        try:
            for sel in _SLIDER_GONE_SELECTORS:
                el = await page.query_selector(sel)
                if el and await el.is_visible():
                    return False
            return True
        except Exception:
            pass
    return False


async def _solve_nc_slider(page: Any, frame: Any, slider_el: Any) -> bool:
    """Attempt to solve NC slider (drag to right)."""
    box = await slider_el.bounding_box()
    if not box:
        return False

    track_width = await _find_track_width(frame)
    if not track_width:
        for f in page.frames:
            track_width = await _find_track_width(f)
            if track_width:
                break
    if not track_width:
        track_width = 300

    slider_width = int(box.get("width", 40))
    drag_distance = track_width - slider_width

    if drag_distance <= 10:
        drag_distance = 260

    start_x = int(box["x"] + box["width"] / 2)
    start_y = int(box["y"] + box["height"] / 2)

    trajectory = generate_human_trajectory(drag_distance)

    await page.mouse.move(start_x, start_y)
    await asyncio.sleep(random.uniform(0.2, 0.5))
    await page.mouse.down()
    await asyncio.sleep(random.uniform(0.05, 0.15))

    current_x, current_y = start_x, start_y
    for dx, dy, dt_ms in trajectory:
        current_x += dx
        current_y += dy
        await page.mouse.move(current_x, current_y)
        await asyncio.sleep(dt_ms / 1000.0)

    await asyncio.sleep(random.uniform(0.05, 0.2))
    await page.mouse.up()
    await asyncio.sleep(2.5)

    return await _check_nc_success(frame, page=page)


async def _solve_puzzle_slider(page: Any, frame: Any, slider_el: Any) -> bool:
    """Attempt to solve puzzle slider using opencv gap detection."""
    try:
        bg_el = None
        for sel in [".yoda-image-bg", ".baxia-bg-img", "#aliyunCaptcha-puzzle-bg", "img.bg-img"]:
            bg_el = await frame.query_selector(sel)
            if bg_el:
                break

        sl_el = None
        for sel in [".yoda-image-slice img", ".baxia-slice-img", "#aliyunCaptcha-puzzle-slice", "img.slice-img"]:
            sl_el = await frame.query_selector(sel)
            if sl_el:
                break

        if not bg_el or not sl_el:
            logger.debug("Puzzle slider: background or slider image element not found")
            return False

        bg_url = await bg_el.get_attribute("src")
        sl_url = await sl_el.get_attribute("src")

        if not bg_url or not sl_url:
            logger.debug("Puzzle slider: image URLs not found, trying screenshot")
            bg_bytes = await bg_el.screenshot()
            sl_bytes = await sl_el.screenshot()
        else:
            import httpx
            async with httpx.AsyncClient(timeout=10) as client:
                bg_resp = await client.get(bg_url)
                sl_resp = await client.get(sl_url)
                bg_bytes = bg_resp.content
                sl_bytes = sl_resp.content

        gap_x = find_puzzle_gap_opencv(bg_bytes, sl_bytes)
        if gap_x is None:
            logger.info("Puzzle slider: opencv gap detection failed")
            return False

        slider_box = await slider_el.bounding_box()
        if not slider_box:
            return False

        bg_box = await bg_el.bounding_box()
        if bg_box:
            scale = bg_box["width"] / 360 if bg_box["width"] > 0 else 1.0
            drag_distance = int(gap_x / scale) if scale != 1.0 else gap_x
        else:
            drag_distance = gap_x

        start_x = int(slider_box["x"] + slider_box["width"] / 2)
        start_y = int(slider_box["y"] + slider_box["height"] / 2)

        trajectory = generate_human_trajectory(drag_distance)

        await page.mouse.move(start_x, start_y)
        await asyncio.sleep(random.uniform(0.1, 0.3))
        await page.mouse.down()

        current_x, current_y = start_x, start_y
        for dx, dy, dt_ms in trajectory:
            current_x += dx
            current_y += dy
            await page.mouse.move(current_x, current_y)
            await asyncio.sleep(dt_ms / 1000.0)

        await page.mouse.up()
        await asyncio.sleep(2.5)

        return await _check_nc_success(frame)

    except Exception as exc:
        logger.info(f"Puzzle slider solve error: {exc}")
        return False


def _extract_goofish_cookies(all_cookies: list[dict[str, Any]]) -> str | None:
    goofish = [c for c in all_cookies if any(d in (c.get("domain", "")) for d in _GOOFISH_DOMAINS)]
    if not goofish:
        return None
    cookie_str = "; ".join(f"{c['name']}={c['value']}" for c in goofish if c.get("name"))
    return cookie_str if len(cookie_str) > 50 else None


def _has_login_cookies(cookies: list[dict[str, Any]]) -> bool:
    names = {c.get("name", "") for c in cookies}
    return bool(names & _AUTH_COOKIES)


_CDP_PORTS = [9222, 9223, 9224]


async def _try_connect_cdp(pw: Any, _log: Any) -> tuple[Any, Any, bool] | None:
    """Try connecting to an already-running Chrome via CDP."""
    import socket
    for port in _CDP_PORTS:
        s = socket.socket()
        s.settimeout(0.5)
        try:
            s.connect(("127.0.0.1", port))
            s.close()
        except Exception:
            continue
        try:
            browser = await pw.chromium.connect_over_cdp(f"http://127.0.0.1:{port}")
            contexts = browser.contexts
            if contexts:
                _log.info(f"Slider recovery: connected to existing Chrome via CDP port {port}")
                return browser, contexts[0], True
            _log.info(f"Slider recovery: CDP connected but no contexts on port {port}")
            await browser.close()
        except Exception as e:
            _log.debug(f"CDP connect failed on port {port}: {e}")
    return None


async def _try_launch_with_profile(pw: Any, headless: bool, _log: Any) -> tuple[Any, Any, bool] | None:
    """Launch Chrome using the user's real profile (persistent context)."""
    system = platform.system()
    candidates: list[str] = []
    if system == "Darwin":
        home = os.path.expanduser("~")
        candidates = [
            f"{home}/Library/Application Support/Google/Chrome",
            f"{home}/Library/Application Support/Microsoft Edge",
        ]
    elif system == "Linux":
        home = os.path.expanduser("~")
        candidates = [f"{home}/.config/google-chrome", f"{home}/.config/chromium"]
    elif system == "Windows":
        local = os.environ.get("LOCALAPPDATA", "")
        candidates = [f"{local}\\Google\\Chrome\\User Data", f"{local}\\Microsoft\\Edge\\User Data"]

    for user_data_dir in candidates:
        if not os.path.isdir(user_data_dir) or not os.path.isdir(os.path.join(user_data_dir, "Default")):
            continue
        try:
            context = await pw.chromium.launch_persistent_context(
                user_data_dir,
                headless=headless,
                channel="chrome",
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--no-first-run",
                    "--no-default-browser-check",
                ],
                viewport={"width": 1280, "height": 800},
                ignore_default_args=["--enable-automation"],
            )
            _log.info(f"Slider recovery: launched with Chrome profile from {user_data_dir}")
            return None, context, False
        except Exception as e:
            _log.debug(f"Profile launch failed ({user_data_dir}): {e}")
    return None


async def _try_launch_fresh(pw: Any, headless: bool, cookie_text: str, _log: Any) -> tuple[Any, Any, bool] | None:
    """Fallback: launch a fresh browser and inject cookies."""
    browser = None
    for channel in ("chrome", "msedge", None):
        try:
            kw: dict[str, Any] = {
                "headless": headless,
                "args": ["--disable-blink-features=AutomationControlled"],
            }
            if channel:
                kw["channel"] = channel
            browser = await pw.chromium.launch(**kw)
            break
        except Exception:
            continue
    if not browser:
        return None

    context = await browser.new_context(
        viewport={"width": 1280 + random.randint(-30, 30), "height": 800 + random.randint(-20, 20)},
        user_agent=(
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        ),
    )
    if cookie_text:
        cookies_to_inject = []
        for pair in cookie_text.split(";"):
            pair = pair.strip()
            if "=" not in pair:
                continue
            name, value = pair.split("=", 1)
            for domain in [".goofish.com", ".taobao.com"]:
                cookies_to_inject.append({"name": name.strip(), "value": value.strip(), "domain": domain, "path": "/"})
        if cookies_to_inject:
            await context.add_cookies(cookies_to_inject)

    _log.info("Slider recovery: launched fresh browser (cookies may be incomplete)")
    return browser, context, False


async def try_slider_recovery(
    *,
    cookie_text: str,
    config: dict[str, Any] | None = None,
    logger: Any = None,
) -> dict[str, Any] | None:
    """Slider recovery with three-tier browser strategy.

    1. Connect to existing Chrome via CDP (best: real cookies, real session)
    2. Launch with user's Chrome Profile (good: real cookies, new window)
    3. Launch fresh browser with injected cookies (fallback: incomplete cookies)

    Returns {"cookie": str} on success, None on failure.
    """
    _log = logger or get_logger()

    if not _has_display():
        _log.info("Slider recovery: no display available, skipping browser launch")
        return None

    slider_cfg = _get_slider_config(config)
    auto_solve = slider_cfg["enabled"]
    max_attempts = slider_cfg["max_attempts"]
    cooldown = slider_cfg["cooldown_seconds"]
    headless = slider_cfg["headless"]

    try:
        from playwright.async_api import async_playwright
    except ImportError:
        _log.debug("Playwright not available for slider recovery")
        return None

    try:
        from playwright_stealth import stealth_async
    except ImportError:
        stealth_async = None

    pw = None
    browser = None
    context = None
    is_cdp = False
    try:
        pw = await async_playwright().start()

        # Strategy 1: connect to existing Chrome via CDP
        cdp_result = await _try_connect_cdp(pw, _log)
        if cdp_result:
            browser, context, is_cdp = cdp_result
        else:
            # Strategy 2: launch with user's Chrome profile
            profile_result = await _try_launch_with_profile(pw, headless, _log)
            if profile_result:
                browser, context, is_cdp = profile_result
            else:
                # Strategy 3: fresh browser with injected cookies
                fresh_result = await _try_launch_fresh(pw, headless, cookie_text, _log)
                if fresh_result:
                    browser, context, is_cdp = fresh_result

        if not context:
            _log.info("Slider recovery: all browser strategies failed")
            return None

        if is_cdp:
            pages = context.pages
            page = None
            for p in pages:
                if "goofish.com" in (p.url or ""):
                    page = p
                    _log.info(f"Slider recovery: reusing existing goofish tab: {p.url}")
                    break
            if not page:
                page = await context.new_page()
                _log.info(f"Slider recovery: navigating to {_GOOFISH_IM_URL}")
                try:
                    await page.goto(_GOOFISH_IM_URL, wait_until="domcontentloaded", timeout=30000)
                except Exception as nav_exc:
                    _log.info(f"Slider recovery: navigation error: {nav_exc}")
        else:
            page = context.pages[0] if context.pages else await context.new_page()
            if stealth_async is not None:
                try:
                    await stealth_async(page)
                except Exception:
                    pass
            _log.info(f"Slider recovery: navigating to {_GOOFISH_IM_URL}")
            try:
                await page.goto(_GOOFISH_IM_URL, wait_until="domcontentloaded", timeout=30000)
            except Exception as nav_exc:
                _log.info(f"Slider recovery: navigation error: {nav_exc}")

        await asyncio.sleep(3)

        if auto_solve:
            for attempt in range(max_attempts):
                _log.info(f"Slider auto-solve attempt {attempt + 1}/{max_attempts}")
                await asyncio.sleep(2)

                slider_info = await _find_slider_in_frames(page)
                if not slider_info:
                    all_cookies = await context.cookies()
                    if _has_login_cookies(all_cookies):
                        cookie_str = _extract_goofish_cookies(all_cookies)
                        if cookie_str:
                            _log.info("Slider recovery: no slider found, valid cookies detected")
                            return {"cookie": cookie_str}
                    _log.info("Slider recovery: no slider element found on page")
                    break

                frame, slider_el, slider_type = slider_info
                _log.info(f"Slider detected: type={slider_type}")

                solved = False
                if slider_type == "nc":
                    solved = await _solve_nc_slider(page, frame, slider_el)
                elif slider_type == "puzzle":
                    solved = await _solve_puzzle_slider(page, frame, slider_el)

                if solved:
                    _log.info("Slider verification passed!")
                    try:
                        await page.wait_for_load_state("networkidle", timeout=10000)
                    except Exception:
                        pass
                    await asyncio.sleep(3)

                    all_cookies = await context.cookies()
                    cookie_str = _extract_goofish_cookies(all_cookies)
                    if cookie_str and _has_login_cookies(all_cookies):
                        return {"cookie": cookie_str}
                    _log.info("Slider solved but cookies incomplete, waiting for page reload...")
                    await asyncio.sleep(5)
                    try:
                        await page.reload(wait_until="domcontentloaded", timeout=15000)
                    except Exception:
                        pass
                    await asyncio.sleep(3)
                    all_cookies = await context.cookies()
                    cookie_str = _extract_goofish_cookies(all_cookies)
                    if cookie_str:
                        return {"cookie": cookie_str}
                else:
                    _log.info(f"Slider auto-solve attempt {attempt + 1} failed")
                    if attempt < max_attempts - 1:
                        _log.info(f"Waiting {cooldown}s before next attempt...")
                        await asyncio.sleep(cooldown)

        if not headless and not is_cdp:
            _log.info("Slider recovery: monitoring browser for manual verification...")
            deadline = time.time() + 1800
            while time.time() < deadline:
                if browser and not browser.is_connected():
                    break
                all_cookies = await context.cookies()
                if _has_login_cookies(all_cookies):
                    cookie_str = _extract_goofish_cookies(all_cookies)
                    if cookie_str:
                        _log.info("Slider recovery: manual verification detected")
                        return {"cookie": cookie_str}
                await asyncio.sleep(3)

        return None

    except Exception as exc:
        _log.info(f"Slider recovery error: {exc}")
        return None
    finally:
        if not is_cdp:
            if browser:
                try:
                    await browser.close()
                except Exception:
                    pass
            elif context:
                try:
                    await context.close()
                except Exception:
                    pass
        if pw:
            try:
                await pw.stop()
            except Exception:
                pass
