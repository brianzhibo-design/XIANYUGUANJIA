"""风控滑块自动验证模块。

Phase 2: 自动打开浏览器呈现验证页面
Phase 3: 自动检测并求解滑块验证码（NC 滑块 / 拼图滑块）

安全降级：自动过滑块默认关闭，失败后保持浏览器窗口等用户手动操作。
"""

from __future__ import annotations

import asyncio
import glob
import json
import os
import platform
import random
import time
from datetime import datetime
from typing import Any

from src.core.logger import get_logger

logger = get_logger()

_SCREENSHOT_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data", "slider_screenshots")
_TRAJECTORY_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data", "slider_trajectories")
_SCREENSHOT_MAX_AGE_DAYS = 7
_SCREENSHOT_MAX_PER_TRIGGER = 4

_GOOFISH_IM_URL = "https://www.goofish.com/im"
_GOOFISH_DOMAINS = [".goofish.com", ".taobao.com", ".tmall.com"]


async def _take_screenshot(page: Any, label: str) -> str | None:
    """Take a screenshot and save to data/slider_screenshots/. Returns the path."""
    try:
        os.makedirs(_SCREENSHOT_DIR, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{ts}_{label}.png"
        filepath = os.path.join(_SCREENSHOT_DIR, filename)
        await page.screenshot(path=filepath, full_page=False)
        logger.info(f"Slider screenshot saved: {filename}")
        return filepath
    except Exception as exc:
        logger.debug(f"Screenshot failed: {exc}")
        return None


def cleanup_old_screenshots(max_age_days: int = _SCREENSHOT_MAX_AGE_DAYS) -> int:
    """Remove screenshots older than max_age_days."""
    if not os.path.isdir(_SCREENSHOT_DIR):
        return 0
    cutoff = time.time() - max_age_days * 86400
    removed = 0
    for f in os.listdir(_SCREENSHOT_DIR):
        fp = os.path.join(_SCREENSHOT_DIR, f)
        if os.path.isfile(fp) and os.path.getmtime(fp) < cutoff:
            try:
                os.remove(fp)
                removed += 1
            except OSError:
                pass
    return removed


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
    "[aria-label='滑块']",
    "[class*='btn_slide']",
    "[id*='n1z']",
    ".nc_wrapper span",
    "#nc_2_n1z",
    "#nc_3_n1z",
    "span[aria-label='滑块']",
]

NC_TRACK_SELECTORS = [
    "#nc_1__scale_text",
    ".nc_scale",
    "#aliyunCaptcha-sliding-track",
    ".slide-track",
    "#baxia-slideBar",
    ".nc_wrapper .nc_scale",
    "#nc_2__scale_text",
    "#nc_3__scale_text",
    "[class*='nc_scale']",
    "div.nc_scale",
]

CAPTCHA_IFRAME_XPATHS = [
    "xpath://iframe[@id='baxia-dialog-content']",
    "xpath://iframe[contains(@src,'action=captcha') and not(contains(@style,'none'))]",
]

POPUP_DISMISS_XPATHS = [
    "xpath://div[@aria-label='关闭' or @aria-label='Close']",
    "xpath://div[@role='button' and text()='跳过']",
]

POST_CAPTCHA_XPATHS = {
    "login_iframe": "xpath://iframe[@id='alibaba-login-box']",
    "quick_enter": "xpath://button[text()='快速进入']",
}

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
    ws_cfg = config or {}
    slider_cfg = ws_cfg.get("slider_auto_solve", {})
    if not isinstance(slider_cfg, dict):
        slider_cfg = {}
    fp_cfg = slider_cfg.get("fingerprint_browser", {})
    if not isinstance(fp_cfg, dict):
        fp_cfg = {}
    return {
        "enabled": bool(slider_cfg.get("enabled", False)),
        "max_attempts": int(slider_cfg.get("max_attempts", 2)),
        "cooldown_seconds": int(slider_cfg.get("cooldown_seconds", 90)),
        "headless": bool(slider_cfg.get("headless", False)),
        "fingerprint_browser": {
            "enabled": bool(fp_cfg.get("enabled", False)),
            "api_url": str(fp_cfg.get("api_url", "http://127.0.0.1:54345")).rstrip("/"),
            "browser_id": str(fp_cfg.get("browser_id", "")),
        },
    }


def _cubic_bezier(t: float, p0: float, p1: float, p2: float, p3: float) -> float:
    """Evaluate a cubic Bezier curve at parameter t."""
    u = 1 - t
    return u * u * u * p0 + 3 * u * u * t * p1 + 3 * u * t * t * p2 + t * t * t * p3


def generate_human_trajectory(distance: int) -> list[tuple[int, int, int]]:
    """Generate human-like mouse trajectory for slider drag.

    Returns list of (dx, dy, dt_ms) relative movements.

    Three-phase speed profile matching proven slider automation patterns:
    Phase 1 (~30%): slow cautious start, acceleration 0.3→1.8 px/step
    Phase 2 (~40%): steady cruising, ~2.0 px/step
    Phase 3 (~30%): confident acceleration, 2.5→7.0 px/step
    """
    if distance <= 0:
        return []

    num_steps = max(20, distance // 3)
    base_dt = random.randint(7, 9)

    phase1_end = int(num_steps * random.uniform(0.25, 0.35))
    phase3_start = num_steps - int(num_steps * random.uniform(0.25, 0.35))

    raw_speeds: list[float] = []
    for i in range(num_steps):
        if i < phase1_end:
            t = i / max(1, phase1_end)
            raw_speeds.append(_cubic_bezier(t, 0.3, 0.5, 1.0, 1.8))
        elif i < phase3_start:
            raw_speeds.append(2.0 + random.uniform(-0.3, 0.3))
        else:
            t = (i - phase3_start) / max(1, num_steps - phase3_start)
            raw_speeds.append(_cubic_bezier(t, 2.5, 3.0, 4.5, 7.0))

    speed_sum = sum(raw_speeds) or 1.0
    scale = distance / speed_sum

    y_drift_up = random.uniform(2, 6)
    y_drift_down = random.uniform(2, 6)
    prev_y_float = 0.0

    steps: list[tuple[int, int, int]] = []
    prev_x = 0
    cumulative = 0.0

    for i, spd in enumerate(raw_speeds):
        cumulative += spd * scale
        target_x = min(distance, round(cumulative))
        dx = target_x - prev_x
        prev_x = target_x

        progress = i / num_steps
        if progress < 0.4:
            target_y = y_drift_up * (progress / 0.4)
        elif progress < 0.7:
            target_y = y_drift_up * (1 - (progress - 0.4) / 0.3) - y_drift_down * ((progress - 0.4) / 0.3)
        else:
            target_y = -y_drift_down * (1 - (progress - 0.7) / 0.3)
        target_y += random.gauss(0, 0.4)
        dy = round(target_y) - round(prev_y_float)
        prev_y_float = target_y

        dt = base_dt + random.randint(-2, 2)

        if dx == 0 and dy == 0:
            continue
        steps.append((max(0, dx), dy, max(2, dt)))

    actual = sum(s[0] for s in steps)
    diff = distance - actual
    if diff != 0:
        steps.append((diff, 0, base_dt))

    return steps


_trajectory_cache: list[dict[str, Any]] | None = None


def load_recorded_trajectories() -> list[dict[str, Any]]:
    """从 data/slider_trajectories/ 加载所有录制轨迹 JSON。结果缓存。"""
    global _trajectory_cache
    if _trajectory_cache is not None:
        return _trajectory_cache

    trajectories: list[dict[str, Any]] = []
    pattern = os.path.join(_TRAJECTORY_DIR, "traj_*.json")
    for fp in glob.glob(pattern):
        try:
            with open(fp, encoding="utf-8") as f:
                data = json.load(f)
            steps = data.get("steps", [])
            if len(steps) >= 3:
                trajectories.append(data)
        except Exception:
            continue

    _trajectory_cache = trajectories
    if trajectories:
        logger.debug("Loaded %d recorded trajectories", len(trajectories))
    return trajectories


def replay_trajectory(distance: int) -> list[tuple[int, int, int]]:
    """选一条录制轨迹，缩放到目标距离，加入微量扰动。无录制时退回生成轨迹。

    Returns list of (dx, dy, dt_ms) relative movements.
    """
    recordings = load_recorded_trajectories()
    if not recordings:
        return generate_human_trajectory(distance)

    rec = random.choice(recordings)
    raw_steps: list[list[int]] = rec["steps"]
    orig_dist = rec.get("original_distance", 1)
    if orig_dist == 0:
        orig_dist = sum(s[0] for s in raw_steps) or 1

    scale = distance / orig_dist if orig_dist else 1.0

    steps: list[tuple[int, int, int]] = []
    cumulative_x = 0.0
    prev_int_x = 0

    for sx, sy, st in raw_steps:
        cumulative_x += sx * scale
        target_int_x = round(cumulative_x)
        dx = target_int_x - prev_int_x
        prev_int_x = target_int_x

        dy = sy + random.choice([-1, 0, 0, 0, 1]) if random.random() < 0.2 else sy
        dt = max(1, st + random.randint(-3, 3))
        steps.append((dx, dy, dt))

    actual = sum(s[0] for s in steps)
    diff = distance - actual
    if diff != 0:
        steps.append((diff, 0, random.randint(8, 25)))

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
    """Search all frames for slider elements. Returns (frame, element, type).

    When a baxia-dialog container is found, waits for and searches inside it
    for an NC slider component which loads asynchronously.
    """
    targets = [page, *list(page.frames)]

    for frame in targets:
        for sel in NC_SLIDER_SELECTORS:
            try:
                el = await frame.query_selector(sel)
                if el and await el.is_visible():
                    return frame, el, "nc"
            except Exception:
                continue

    baxia_dialog = None
    baxia_frame = None
    for frame in targets:
        for sel in PUZZLE_SELECTORS:
            try:
                el = await frame.query_selector(sel)
                if el and await el.is_visible():
                    if sel == ".baxia-dialog":
                        baxia_dialog = el
                        baxia_frame = frame
                    else:
                        return frame, el, "puzzle"
            except Exception:
                continue

    if baxia_dialog:
        nc_btn = await _wait_for_nc_inside_baxia(page, baxia_frame, baxia_dialog)
        if nc_btn:
            return nc_btn
        return baxia_frame, baxia_dialog, "puzzle"

    return None


async def _wait_for_nc_inside_baxia(page: Any, frame: Any, dialog_el: Any) -> tuple[Any, Any, str] | None:
    """Wait for the NC slider component to load inside a baxia-dialog.

    The NC component loads asynchronously via JS, so the container div
    appears before the slider button. We poll a few times to catch it.
    """
    nc_inner_selectors = [
        *NC_SLIDER_SELECTORS,
        ".baxia-dialog .btn_slide",
        ".baxia-dialog [class*='slide']",
        ".baxia-dialog span[class*='btn']",
    ]

    for wait_round in range(4):
        if wait_round > 0:
            await asyncio.sleep(1.5)

        all_frames = [frame] + [f for f in page.frames if f != frame]
        for f in all_frames:
            for sel in nc_inner_selectors:
                try:
                    el = await f.query_selector(sel)
                    if el and await el.is_visible():
                        logger.info(f"Baxia dialog: found NC button via '{sel}' (wait_round={wait_round})")
                        return f, el, "nc"
                except Exception:
                    continue

        try:
            iframes = await dialog_el.query_selector_all("iframe")
            for iframe_el in iframes:
                iframe_name = await iframe_el.get_attribute("name") or ""
                iframe_src = await iframe_el.get_attribute("src") or ""
                logger.info(
                    f"Baxia dialog: found iframe name='{iframe_name}' src='{iframe_src[:100]}' (wait_round={wait_round})"
                )
                for f in page.frames:
                    if f.name == iframe_name or (iframe_src and iframe_src in (f.url or "")):
                        for sel in NC_SLIDER_SELECTORS:
                            try:
                                el = await f.query_selector(sel)
                                if el and await el.is_visible():
                                    logger.info(f"Baxia iframe: found NC button via '{sel}'")
                                    return f, el, "nc"
                            except Exception:
                                continue
        except Exception:
            pass

    logger.info("Baxia dialog: no NC component found after polling, treating as puzzle")
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


async def _solve_nc_slider(page: Any, frame: Any, slider_el: Any) -> dict[str, Any]:
    """Attempt to solve NC slider (drag to right).

    Returns dict with keys: solved (bool), track_width, drag_distance,
    fail_reason, screenshot_path.
    """
    result: dict[str, Any] = {
        "solved": False,
        "track_width": None,
        "drag_distance": None,
        "fail_reason": None,
        "screenshot_path": None,
    }

    box = await slider_el.bounding_box()
    if not box:
        result["fail_reason"] = "no_bounding_box"
        return result

    track_width = await _find_track_width(frame)
    if not track_width:
        for f in page.frames:
            track_width = await _find_track_width(f)
            if track_width:
                break
    if not track_width:
        track_width = 300

    slider_width = int(box.get("width", 40))
    drag_distance = track_width - slider_width + random.randint(-3, 3)

    if drag_distance <= 10:
        drag_distance = 260

    result["track_width"] = track_width
    result["drag_distance"] = drag_distance

    start_x = int(box["x"] + box["width"] / 2)
    start_y = int(box["y"] + box["height"] / 2)

    trajectory = generate_human_trajectory(drag_distance)

    await page.mouse.move(start_x, start_y)
    await asyncio.sleep(random.uniform(0.05, 0.15))
    await page.mouse.down()
    await asyncio.sleep(random.uniform(0.02, 0.06))

    current_x, current_y = start_x, start_y
    for dx, dy, dt_ms in trajectory:
        current_x += dx
        current_y += dy
        await page.mouse.move(current_x, current_y)
        await asyncio.sleep(dt_ms / 1000.0)

    await asyncio.sleep(random.uniform(0.1, 0.3))
    await page.mouse.up()

    for _ in range(10):
        await asyncio.sleep(0.3)
        for err_sel in [".errloading", ".nc-lang-cnt"]:
            try:
                err_el = await page.query_selector(err_sel)
                if err_el and await err_el.is_visible():
                    err_text = await err_el.inner_text()
                    if any(kw in (err_text or "") for kw in ["出错", "请重试", "失败"]):
                        result["fail_reason"] = f"error_text:{err_text}"
                        result["screenshot_path"] = await _take_screenshot(page, "nc_error")
                        return result
            except Exception:
                pass
        if await _check_nc_success(frame, page=page):
            result["solved"] = True
            return result

    if await _check_nc_success(frame, page=page):
        result["solved"] = True
    else:
        result["fail_reason"] = "no_success_marker"
        result["screenshot_path"] = await _take_screenshot(page, "nc_failed")
    return result


async def _dump_baxia_dom(page: Any, frame: Any) -> None:
    """Dump DOM structure inside baxia-dialog for diagnostics."""
    try:
        all_frames = [frame] + [f for f in page.frames if f != frame]
        for f in all_frames:
            try:
                baxia = await f.query_selector(".baxia-dialog")
                if not baxia:
                    continue
                html_snippet = await f.evaluate(
                    """(el) => {
                        const children = el.querySelectorAll('*');
                        const items = [];
                        for (let i = 0; i < Math.min(children.length, 40); i++) {
                            const c = children[i];
                            items.push({
                                tag: c.tagName,
                                id: c.id || '',
                                cls: c.className || '',
                                visible: c.offsetParent !== null || c.style.display !== 'none'
                            });
                        }
                        return items;
                    }""",
                    baxia,
                )
                logger.info(f"Baxia DOM dump ({len(html_snippet)} elements):")
                for item in html_snippet:
                    if item.get("visible"):
                        tag = item.get("tag", "?")
                        el_id = item.get("id", "")
                        el_cls = str(item.get("cls", ""))[:80]
                        logger.info(f"  <{tag} id='{el_id}' class='{el_cls}'>")
                return
            except Exception:
                continue

        imgs = await frame.query_selector_all("img")
        logger.info(f"Frame img elements ({len(imgs)}):")
        for img in imgs[:15]:
            src = await img.get_attribute("src") or ""
            cls = await img.get_attribute("class") or ""
            el_id = await img.get_attribute("id") or ""
            logger.info(f"  img id='{el_id}' class='{cls}' src='{src[:80]}'")
    except Exception as exc:
        logger.info(f"DOM dump failed: {exc}")


async def _try_nc_fallback_inside_puzzle(page: Any, frame: Any) -> dict[str, Any]:
    """When puzzle detection found bg but no slice, try NC-style drag as fallback.

    Returns dict matching _solve_nc_slider return format.
    """
    logger.info("Puzzle fallback: searching for NC-style slider inside dialog...")

    nc_broad_selectors = [
        *NC_SLIDER_SELECTORS,
        ".baxia-dialog .btn_slide",
        ".baxia-dialog [class*='slide']",
        ".baxia-dialog span[class*='btn']",
        ".baxia-dialog [class*='nc']",
        "span[class*='btn_slide']",
    ]

    all_frames = [frame] + [f for f in page.frames if f != frame]

    for f in all_frames:
        for sel in nc_broad_selectors:
            try:
                el = await f.query_selector(sel)
                if el and await el.is_visible():
                    box = await el.bounding_box()
                    if not box or box["width"] < 10 or box["height"] < 10:
                        continue
                    logger.info(f"Puzzle fallback: found NC button via '{sel}', trying drag")
                    return await _solve_nc_slider(page, f, el)
            except Exception:
                continue

    try:
        for f in all_frames:
            draggables = await f.evaluate("""() => {
                const candidates = document.querySelectorAll(
                    '.baxia-dialog span, .baxia-dialog div, .baxia-dialog button'
                );
                const results = [];
                for (const el of candidates) {
                    const rect = el.getBoundingClientRect();
                    const style = window.getComputedStyle(el);
                    if (rect.width > 20 && rect.width < 80
                        && rect.height > 20 && rect.height < 80
                        && style.cursor !== 'default'
                        && style.display !== 'none') {
                        results.push({
                            tag: el.tagName,
                            id: el.id || '',
                            cls: el.className || '',
                            x: rect.x, y: rect.y,
                            w: rect.width, h: rect.height,
                            cursor: style.cursor
                        });
                    }
                }
                return results;
            }""")
            if draggables:
                logger.info(f"Puzzle fallback: found {len(draggables)} candidate draggable elements:")
                for d in draggables[:5]:
                    d_tag = d.get("tag")
                    d_id = d.get("id")
                    d_cls = str(d.get("cls", ""))[:60]
                    d_cur = d.get("cursor")
                    d_w = d.get("w", 0)
                    d_h = d.get("h", 0)
                    logger.info(f"  <{d_tag} id='{d_id}' class='{d_cls}' cursor='{d_cur}' {d_w}x{d_h}>")

                best = draggables[0]
                for d in draggables:
                    if d.get("cursor") in ("pointer", "move", "grab"):
                        best = d
                        break

                sel_str = ""
                if best.get("id"):
                    sel_str = f"#{best['id']}"
                elif best.get("cls"):
                    first_cls = str(best["cls"]).split()[0]
                    sel_str = f".{first_cls}"

                if sel_str:
                    el = await f.query_selector(sel_str)
                    if el:
                        logger.info(f"Puzzle fallback: trying drag on '{sel_str}'")
                        return await _solve_nc_slider(page, f, el)
    except Exception as exc:
        logger.info(f"Puzzle fallback evaluate failed: {exc}")

    logger.info("Puzzle fallback: no draggable element found")
    return {
        "solved": False,
        "fail_reason": "no_draggable_element",
        "screenshot_path": await _take_screenshot(page, "puzzle_fallback_none"),
    }


_PUZZLE_BG_SELECTORS = [
    ".yoda-image-bg",
    ".baxia-bg-img",
    "#aliyunCaptcha-puzzle-bg",
    "img.bg-img",
    ".nc-container img",
    "img[id*='bg']",
    "img[class*='bg']",
    "canvas.baxia-canvas",
]

_PUZZLE_SLICE_SELECTORS = [
    ".yoda-image-slice img",
    ".baxia-slice-img",
    "#aliyunCaptcha-puzzle-slice",
    "img.slice-img",
    "img[id*='slice']",
    "img[class*='slice']",
    ".yoda-image-slice",
    "img[id*='jigsaw']",
    "img[class*='jigsaw']",
    ".baxia-dialog img[data-type='slice']",
    ".baxia-dialog img:not([class*='bg'])",
    "canvas[class*='slice']",
    ".captcha-slider-puzzle img",
]


async def _solve_puzzle_slider(page: Any, frame: Any, slider_el: Any) -> dict[str, Any]:
    """Attempt to solve puzzle slider using opencv gap detection.

    Returns dict with keys: solved, puzzle_bg_found, puzzle_slice_found,
    puzzle_gap_x, puzzle_match_score, fail_reason, screenshot_path.
    """
    result: dict[str, Any] = {
        "solved": False,
        "puzzle_bg_found": False,
        "puzzle_slice_found": False,
        "puzzle_gap_x": None,
        "puzzle_match_score": None,
        "fail_reason": None,
        "screenshot_path": None,
    }
    try:
        all_frames = [frame] + [f for f in page.frames if f != frame]

        bg_el = None
        sl_el = None
        target_frame = frame

        for f in all_frames:
            for sel in _PUZZLE_BG_SELECTORS:
                try:
                    el = await f.query_selector(sel)
                    if el and await el.is_visible():
                        bg_el = el
                        target_frame = f
                        logger.info(f"Puzzle: found bg element via '{sel}'")
                        break
                except Exception:
                    continue
            if bg_el:
                break

        for attempt in range(3):
            if attempt > 0:
                await asyncio.sleep(1.0)
            for f in all_frames:
                for sel in _PUZZLE_SLICE_SELECTORS:
                    try:
                        el = await f.query_selector(sel)
                        if el and await el.is_visible():
                            sl_el = el
                            logger.info(f"Puzzle: found slice element via '{sel}' (attempt={attempt})")
                            break
                    except Exception:
                        continue
                if sl_el:
                    break
            if sl_el:
                break

        result["puzzle_bg_found"] = bg_el is not None
        result["puzzle_slice_found"] = sl_el is not None

        if not bg_el or not sl_el:
            logger.info(
                f"Puzzle slider: elements not found (bg={'found' if bg_el else 'MISSING'}, "
                f"slice={'found' if sl_el else 'MISSING'}). "
                "Trying fallback..."
            )
            result["screenshot_path"] = await _take_screenshot(page, "puzzle_missing_elements")
            await _dump_baxia_dom(page, target_frame)

            if bg_el and not sl_el:
                result["fail_reason"] = "slice_missing"
                nc_result = await _try_nc_fallback_inside_puzzle(page, target_frame)
                result["solved"] = nc_result.get("solved", False)
                result["screenshot_path"] = nc_result.get("screenshot_path") or result["screenshot_path"]
                if not result["solved"]:
                    result["fail_reason"] = nc_result.get("fail_reason") or "slice_missing_fallback_failed"
                return result

            result["fail_reason"] = "bg_and_slice_missing"
            return result

        bg_url = await bg_el.get_attribute("src") if bg_el else None
        sl_url = await sl_el.get_attribute("src") if sl_el else None

        if not bg_url or not sl_url:
            logger.info("Puzzle slider: image URLs not found, trying screenshot")
            bg_bytes = await bg_el.screenshot() if bg_el else None
            sl_bytes = await sl_el.screenshot() if sl_el else None
            if not bg_bytes or not sl_bytes:
                result["fail_reason"] = "image_capture_failed"
                return result
        else:
            import httpx

            async with httpx.AsyncClient(timeout=10) as client:
                bg_resp = await client.get(bg_url)
                sl_resp = await client.get(sl_url)
                bg_bytes = bg_resp.content
                sl_bytes = sl_resp.content

        logger.info(f"Puzzle: bg image {len(bg_bytes)} bytes, slice image {len(sl_bytes)} bytes")

        gap_x = find_puzzle_gap_opencv(bg_bytes, sl_bytes)
        result["puzzle_gap_x"] = gap_x
        if gap_x is None:
            logger.info("Puzzle slider: opencv gap detection failed")
            result["fail_reason"] = "opencv_gap_detection_failed"
            result["screenshot_path"] = await _take_screenshot(page, "puzzle_opencv_fail")
            return result

        logger.info(f"Puzzle: gap detected at x={gap_x}")

        slider_box = await slider_el.bounding_box()
        if not slider_box:
            result["fail_reason"] = "slider_no_bounding_box"
            return result

        bg_box = await bg_el.bounding_box()
        if bg_box:
            scale = bg_box["width"] / 360 if bg_box["width"] > 0 else 1.0
            drag_distance = int(gap_x / scale) if scale != 1.0 else gap_x
        else:
            drag_distance = gap_x

        logger.info(f"Puzzle: drag_distance={drag_distance}px")

        start_x = int(slider_box["x"] + slider_box["width"] / 2)
        start_y = int(slider_box["y"] + slider_box["height"] / 2)

        trajectory = generate_human_trajectory(drag_distance)

        await page.mouse.move(start_x, start_y)
        await asyncio.sleep(random.uniform(0.05, 0.15))
        await page.mouse.down()
        await asyncio.sleep(random.uniform(0.02, 0.06))

        current_x, current_y = start_x, start_y
        for dx, dy, dt_ms in trajectory:
            current_x += dx
            current_y += dy
            await page.mouse.move(current_x, current_y)
            await asyncio.sleep(dt_ms / 1000.0)

        await asyncio.sleep(random.uniform(0.01, 0.05))
        await page.mouse.up()

        for _ in range(10):
            await asyncio.sleep(0.3)
            if await _check_nc_success(target_frame, page=page):
                result["solved"] = True
                return result

        if await _check_nc_success(target_frame, page=page):
            result["solved"] = True
        else:
            result["fail_reason"] = "verification_not_passed"
            result["screenshot_path"] = await _take_screenshot(page, "puzzle_failed")
        return result

    except Exception as exc:
        logger.info(f"Puzzle slider solve error: {exc}")
        result["fail_reason"] = f"exception:{exc}"
        return result


def _extract_goofish_cookies(all_cookies: list[dict[str, Any]]) -> str | None:
    goofish = [c for c in all_cookies if any(d in (c.get("domain", "")) for d in _GOOFISH_DOMAINS)]
    if not goofish:
        return None
    cookie_str = "; ".join(f"{c['name']}={c['value']}" for c in goofish if c.get("name"))
    return cookie_str if len(cookie_str) > 50 else None


def _has_login_cookies(cookies: list[dict[str, Any]]) -> bool:
    names = {c.get("name", "") for c in cookies}
    return bool(names & _AUTH_COOKIES)




def _dismiss_popups_dp(tab: Any, _log: Any) -> None:
    """关闭遮挡滑块的弹窗（关闭按钮、跳过按钮等）。"""
    dismiss_selectors = [
        "xpath://div[@aria-label='关闭' or @aria-label='Close']",
        "xpath://div[@role='button' and text()='跳过']",
        "xpath://button[@aria-label='关闭']",
    ]
    for sel in dismiss_selectors:
        try:
            el = tab.ele(sel, timeout=1)
            if el:
                el.click()
                _log.info(f"Dismissed popup via '{sel}'")
                time.sleep(0.5)
        except Exception:
            continue


def _handle_post_captcha_dp(tab: Any, _log: Any) -> None:
    """验证成功后处理 alibaba-login-box iframe 中的'快速进入'按钮。"""
    try:
        login_iframe = tab.ele("xpath://iframe[@id='alibaba-login-box']", timeout=3)
        if not login_iframe:
            return
        _log.info("Found alibaba-login-box iframe, looking for '快速进入'...")
        quick_btn = tab.ele("xpath://button[text()='快速进入']", timeout=3)
        if quick_btn:
            quick_btn.click()
            _log.info("Clicked '快速进入' button")
            time.sleep(2)
    except Exception as exc:
        _log.debug(f"Post-captcha handling: {exc}")


def _find_captcha_iframe_dp(tab: Any, _log: Any) -> Any:
    """在 DrissionPage 中定位验证码 iframe。"""
    iframe_xpaths = [
        "xpath://iframe[@id='baxia-dialog-content']",
        "xpath://iframe[contains(@src,'action=captcha')]",
    ]
    for xpath in iframe_xpaths:
        try:
            iframe_el = tab.ele(xpath, timeout=2)
            if iframe_el:
                _log.info(f"Found captcha iframe via '{xpath}'")
                return iframe_el
        except Exception:
            continue
    return None


def _try_slider_drissionpage(
    fp_cfg: dict[str, Any],
    cookie_text: str,
    max_attempts: int,
    _log: Any,
) -> dict[str, Any] | None:
    """DrissionPage 滑块求解 — 连接 BitBrowser 已有窗口，使用 CDP 原生拖拽。

    同步函数，由 asyncio.to_thread() 调用。
    返回格式与 try_slider_recovery 一致。
    """
    recovery_start = time.time()
    attempts_log: list[dict[str, Any]] = []

    try:
        from DrissionPage import Chromium
    except ImportError:
        _log.warning("DrissionPage not installed, slider recovery unavailable. Run: pip install DrissionPage")
        return None

    api_url = fp_cfg.get("api_url", "")
    browser_id = fp_cfg.get("browser_id", "")
    if not api_url or not browser_id:
        _log.warning("DrissionPage: fingerprint_browser config incomplete (api_url=%s, browser_id=%s)", api_url, bool(browser_id))
        return None

    import httpx as _httpx

    ws_url = None
    _bb_open_url = f"{api_url.rstrip('/')}/browser/open"
    for _open_try in range(3):
        try:
            resp = _httpx.post(_bb_open_url, json={"id": browser_id}, timeout=10)
            data = resp.json()
            if data.get("success"):
                ws_url = data.get("data", {}).get("ws")
                break
            msg = str(data.get("msg", ""))
            if "正在打开" in msg or "opening" in msg.lower():
                _log.info(f"DrissionPage: BitBrowser still opening, retry {_open_try + 1}/3...")
                time.sleep(3)
                continue
            _log.info(f"DrissionPage: BitBrowser open failed: {data}")
            return None
        except Exception as exc:
            _log.info(f"DrissionPage: BitBrowser API error: {exc}")
            return None
    if not ws_url:
        _log.info("DrissionPage: no ws URL from BitBrowser after retries")
        return None

    browser = None
    try:
        browser = Chromium(ws_url)

        tab = None
        for t in browser.get_tabs():
            try:
                page = browser.get_tab(t)
                if page and "goofish.com/im" in (page.url or ""):
                    tab = page
                    break
            except Exception:
                continue

        if not tab:
            for t in browser.get_tabs():
                try:
                    page = browser.get_tab(t)
                    if page and "goofish.com" in (page.url or ""):
                        tab = page
                        break
                except Exception:
                    continue

        if not tab:
            tab = browser.latest_tab
            if tab:
                _log.info(f"DrissionPage: no goofish tab, navigating latest tab to {_GOOFISH_IM_URL}")
                tab.get(_GOOFISH_IM_URL)
            else:
                _log.info("DrissionPage: no tabs available")
                return None
        else:
            _log.info(f"DrissionPage: reloading tab {tab.url}")
            tab.refresh()

        time.sleep(3)

        _dismiss_popups_dp(tab, _log)

        for attempt in range(max_attempts):
            attempt_data: dict[str, Any] = {
                "attempt_num": attempt + 1,
                "slider_type": None,
                "result": "failed",
                "fail_reason": None,
                "screenshot_path": None,
                "browser_strategy": "drissionpage",
                "browser_connect_ms": int((time.time() - recovery_start) * 1000),
            }
            _log.info(f"DrissionPage slider attempt {attempt + 1}/{max_attempts}")

            time.sleep(2)

            slider_el = None
            slider_type = None

            captcha_iframe = _find_captcha_iframe_dp(tab, _log)
            search_targets = [captcha_iframe, tab] if captcha_iframe else [tab]

            nc_selectors = [
                "#nc_1_n1z", ".btn_slide", "#aliyunCaptcha-sliding-btn",
                ".slide-btn", "span[aria-label='滑块']",
                "xpath://span[@aria-label='滑块']",
            ]
            for target in search_targets:
                for sel in nc_selectors:
                    try:
                        el = target.ele(sel, timeout=2)
                        if el:
                            slider_el = el
                            slider_type = "nc"
                            break
                    except Exception:
                        continue
                if slider_el:
                    break

            if not slider_el:
                puzzle_selectors = [".yoda-image-slice", "#alicaptcha-puzzle", ".baxia-dialog"]
                for target in search_targets:
                    for sel in puzzle_selectors:
                        try:
                            el = target.ele(sel, timeout=2)
                            if el:
                                slider_el = el
                                slider_type = "puzzle"
                                break
                        except Exception:
                            continue
                    if slider_el:
                        break

            if not slider_el:
                attempt_data["fail_reason"] = "no_slider_found"
                _log.info("DrissionPage: no slider element found")
                try:
                    ss_path = os.path.join(_SCREENSHOT_DIR, f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_dp_no_slider.png")
                    os.makedirs(_SCREENSHOT_DIR, exist_ok=True)
                    tab.get_screenshot(path=ss_path)
                    attempt_data["screenshot_path"] = ss_path
                except Exception:
                    pass
                attempts_log.append(attempt_data)
                continue

            attempt_data["slider_type"] = slider_type

            if slider_type == "nc":
                try:
                    track_el = None
                    track_selectors = [
                        "#nc_1__scale_text", ".nc_scale",
                        "#aliyunCaptcha-sliding-track", ".slide-track",
                        "div.nc_scale",
                        "xpath://span[@aria-label='滑块']/ancestor::div[@class='nc_scale'][1]",
                    ]
                    for tsel in track_selectors:
                        try:
                            track_el = tab.ele(tsel, timeout=1)
                            if track_el:
                                break
                        except Exception:
                            continue

                    if track_el:
                        track_rect = track_el.rect
                        track_width = int(track_rect.size[0]) if track_rect else 300
                    else:
                        track_width = 300

                    slider_rect = slider_el.rect
                    slider_width = int(slider_rect.size[0]) if slider_rect else 40
                    drag_distance = track_width - slider_width + random.randint(-3, 3)
                    if drag_distance <= 10:
                        drag_distance = 260

                    attempt_data["nc_track_width"] = track_width
                    attempt_data["nc_drag_distance"] = drag_distance

                    trajectory = replay_trajectory(drag_distance)
                    traj_source = "recorded" if load_recorded_trajectories() else "generated"
                    _log.info(
                        f"DrissionPage NC drag: distance={drag_distance}, "
                        f"trajectory={traj_source}, steps={len(trajectory)}"
                    )

                    ac = tab.actions
                    ac.move_to(slider_el, duration=random.uniform(0.3, 0.8))
                    time.sleep(random.uniform(0.5, 1.5))
                    ac.hold()
                    time.sleep(random.uniform(0.05, 0.15))

                    for dx, dy, dt_ms in trajectory:
                        dur = max(0.02, dt_ms / 1000.0)
                        ac.move(dx, dy, duration=dur)

                    time.sleep(random.uniform(0.3, 0.8))
                    ac.release()

                except Exception as exc:
                    attempt_data["fail_reason"] = f"drag_error:{exc}"
                    attempts_log.append(attempt_data)
                    continue

                time.sleep(2)

                success = False
                for _ in range(6):
                    try:
                        body_text = tab.html or ""
                        if any(m in body_text for m in NC_SUCCESS_MARKERS):
                            success = True
                            break
                    except Exception:
                        pass
                    found_slider = False
                    for sel in ["#nc_1_n1z", ".btn_slide"]:
                        try:
                            if tab.ele(sel, timeout=0.5):
                                found_slider = True
                                break
                        except Exception:
                            pass
                    if not found_slider:
                        success = True
                        break
                    time.sleep(0.5)

                if success:
                    attempt_data["result"] = "success"
                    _log.info(f"DrissionPage NC slider solved on attempt {attempt + 1}")
                    _handle_post_captcha_dp(tab, _log)
                else:
                    attempt_data["fail_reason"] = "no_success_marker"
                    _log.info("DrissionPage: checking error indicator...")
                    try:
                        err_el = tab.ele("xpath://div[@class='errloading']", timeout=1)
                        if err_el:
                            err_text = err_el.text or ""
                            attempt_data["fail_reason"] = f"errloading:{err_text}"
                            _log.info(f"DrissionPage: error indicator found: {err_text}")
                    except Exception:
                        pass
                    try:
                        ss_path = os.path.join(_SCREENSHOT_DIR, f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_dp_nc_fail.png")
                        tab.get_screenshot(path=ss_path)
                        attempt_data["screenshot_path"] = ss_path
                    except Exception:
                        pass

            elif slider_type == "puzzle":
                attempt_data["fail_reason"] = "puzzle_not_implemented_dp"
                _log.info("DrissionPage: puzzle slider detected, not yet implemented in DP path")

            attempts_log.append(attempt_data)

            if attempt_data["result"] == "success":
                break

            time.sleep(random.uniform(2, 4))

        time.sleep(2)

        import asyncio as _aio
        cookie_str = None
        try:
            from src.core.bitbrowser_cdp import read_cookies_via_cdp
            loop = _aio.new_event_loop()
            try:
                cookie_str = loop.run_until_complete(read_cookies_via_cdp(ws_url))
            finally:
                loop.close()
        except Exception as exc:
            _log.debug(f"DrissionPage: cookie read failed: {exc}")

        return {
            "cookie": cookie_str,
            "attempts": attempts_log,
            "browser_strategy": "drissionpage",
            "total_duration_ms": int((time.time() - recovery_start) * 1000),
        }

    except Exception as exc:
        _log.info(f"DrissionPage slider error: {exc}")
        return {
            "cookie": None,
            "attempts": attempts_log,
            "error": str(exc),
            "browser_strategy": "drissionpage",
            "total_duration_ms": int((time.time() - recovery_start) * 1000),
        }
    finally:
        pass


async def try_slider_recovery(
    *,
    cookie_text: str,
    config: dict[str, Any] | None = None,
    logger: Any = None,
) -> dict[str, Any] | None:
    """Slider recovery via DrissionPage + BitBrowser.

    Returns {"cookie": str, "attempts": [...]} on success, None on failure.
    """
    _log = logger or get_logger()

    cleanup_old_screenshots()

    if not _has_display():
        _log.info("Slider recovery: no display available, skipping browser launch")
        return None

    slider_cfg = _get_slider_config(config)
    max_attempts = slider_cfg["max_attempts"]

    fp_cfg = slider_cfg.get("fingerprint_browser", {})
    if not fp_cfg.get("enabled"):
        _log.info("Slider recovery: fingerprint_browser not enabled, skipping")
        return None

    _log.info("Slider recovery: using DrissionPage (fingerprint_browser enabled)")
    return await asyncio.to_thread(
        _try_slider_drissionpage, fp_cfg, cookie_text, max_attempts, _log
    )
