#!/usr/bin/env python3
"""滑块轨迹录制工具 — 连接 BitBrowser 窗口，手动拖拽采集真实鼠标轨迹。

使用方法:
    python scripts/record_slider_trajectory.py [--count 5]

脚本会:
1. 连接 BitBrowser 已有窗口
2. 导航到闲鱼 IM 页面触发滑块
3. 注入 JS 监听器捕获拖拽事件
4. 等待你手动拖拽滑块
5. 采集轨迹并保存到 data/slider_trajectories/
"""

from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

TRAJECTORY_DIR = ROOT / "data" / "slider_trajectories"
BB_API_URL = "http://127.0.0.1:54345"
GOOFISH_IM_URL = "https://www.goofish.com/im"

_RECORDER_JS = r"""
(function() {
    if (window.__trajRecorder) return 'already_installed';

    window.__trajRecorder = {
        recording: false,
        events: [],
        startX: 0,
        startY: 0,
        startTime: 0,
        done: false
    };
    var R = window.__trajRecorder;

    document.addEventListener('mousedown', function(e) {
        R.recording = true;
        R.events = [];
        R.startX = e.clientX;
        R.startY = e.clientY;
        R.startTime = performance.now();
        R.events.push({x: e.clientX, y: e.clientY, t: 0});
        R.done = false;
    }, true);

    document.addEventListener('mousemove', function(e) {
        if (!R.recording) return;
        R.events.push({
            x: e.clientX,
            y: e.clientY,
            t: performance.now() - R.startTime
        });
    }, true);

    document.addEventListener('mouseup', function(e) {
        if (!R.recording) return;
        R.events.push({
            x: e.clientX,
            y: e.clientY,
            t: performance.now() - R.startTime
        });
        R.recording = false;
        R.done = true;
    }, true);

    return 'installed';
})();
"""

_CHECK_DONE_JS = r"""
(function() {
    var R = window.__trajRecorder;
    if (!R) return null;
    if (!R.done) return null;
    return JSON.stringify(R.events);
})();
"""

_RESET_JS = r"""
(function() {
    if (window.__trajRecorder) {
        window.__trajRecorder.done = false;
        window.__trajRecorder.events = [];
    }
})();
"""


def _get_browser_id() -> str:
    cfg_path = ROOT / "data" / "system_config.json"
    if cfg_path.exists():
        cfg = json.loads(cfg_path.read_text("utf-8"))
        bid = (
            cfg.get("slider_auto_solve", {})
            .get("fingerprint_browser", {})
            .get("browser_id", "")
        )
        if bid:
            return bid
    print("错误: 未在 data/system_config.json 中找到 browser_id")
    sys.exit(1)


def _get_ws_url(browser_id: str) -> str:
    import httpx

    url = f"{BB_API_URL}/browser/open"
    for attempt in range(3):
        try:
            resp = httpx.post(url, json={"id": browser_id}, timeout=10)
            data = resp.json()
            if data.get("success"):
                ws = data.get("data", {}).get("ws")
                if ws:
                    return ws
            msg = str(data.get("msg", ""))
            if "正在打开" in msg:
                print(f"  BitBrowser 正在打开中, 重试 {attempt + 1}/3...")
                time.sleep(3)
                continue
            print(f"  BitBrowser API 错误: {data}")
            sys.exit(1)
        except Exception as exc:
            print(f"  BitBrowser 连接失败: {exc}")
            sys.exit(1)
    print("BitBrowser 打开超时")
    sys.exit(1)


def _normalize_events(raw_events: list[dict]) -> tuple[list[list[int]], int]:
    """将绝对坐标事件序列转为 [dx, dy, dt_ms] 相对移动。返回 (steps, total_distance)。"""
    if len(raw_events) < 3:
        return [], 0

    steps: list[list[int]] = []
    prev_x = raw_events[0]["x"]
    prev_y = raw_events[0]["y"]
    prev_t = raw_events[0]["t"]

    for ev in raw_events[1:]:
        dx = round(ev["x"] - prev_x)
        dy = round(ev["y"] - prev_y)
        dt = max(1, round(ev["t"] - prev_t))
        if dx != 0 or dy != 0:
            steps.append([dx, dy, dt])
        prev_x = ev["x"]
        prev_y = ev["y"]
        prev_t = ev["t"]

    total_x = sum(s[0] for s in steps)
    return steps, total_x


def _save_trajectory(steps: list[list[int]], distance: int, index: int) -> str:
    TRAJECTORY_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"traj_{ts}_{index:02d}.json"
    filepath = TRAJECTORY_DIR / filename
    data = {
        "recorded_at": datetime.now().isoformat(),
        "original_distance": distance,
        "total_steps": len(steps),
        "total_duration_ms": sum(s[2] for s in steps),
        "steps": steps,
    }
    filepath.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return str(filepath)


def main():
    import argparse

    parser = argparse.ArgumentParser(description="滑块轨迹录制工具")
    parser.add_argument("--count", type=int, default=5, help="录制轨迹数量 (默认 5)")
    args = parser.parse_args()

    print("=" * 50)
    print("滑块轨迹录制工具")
    print("=" * 50)

    browser_id = _get_browser_id()
    print(f"浏览器 ID: {browser_id[:8]}...")

    ws_url = _get_ws_url(browser_id)
    print(f"CDP 连接: {ws_url[:50]}...")

    try:
        from DrissionPage import Chromium
    except ImportError:
        print("错误: DrissionPage 未安装, 运行: pip install DrissionPage")
        sys.exit(1)

    browser = Chromium(ws_url)

    tab = None
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
        print(f"当前页面: {tab.url}")
    else:
        print("错误: 没有可用的标签页")
        sys.exit(1)

    print()
    print(f"准备录制 {args.count} 条轨迹")
    print("操作说明:")
    print("  1. 请在 BitBrowser 窗口中找到/触发滑块验证")
    print("  2. 用鼠标手动拖拽滑块（从左拖到右）")
    print("  3. 每次拖拽完成后脚本自动采集")
    print("  4. 页面会刷新以触发新的滑块")
    print()

    recorded = 0
    for i in range(args.count):
        print(f"\n--- 录制 {i + 1}/{args.count} ---")

        result = tab.run_js(_RECORDER_JS)
        if result == "already_installed":
            tab.run_js(_RESET_JS)
        print("JS 监听器已注入, 请在浏览器中拖拽滑块...")

        for wait in range(120):
            time.sleep(1)
            try:
                raw = tab.run_js(_CHECK_DONE_JS)
                if raw and raw != "null":
                    events = json.loads(raw)
                    if len(events) >= 5:
                        steps, distance = _normalize_events(events)
                        if len(steps) >= 3 and abs(distance) > 30:
                            filepath = _save_trajectory(steps, distance, i + 1)
                            recorded += 1
                            print(
                                f"  已采集: {len(steps)} 步, "
                                f"距离 {distance}px, "
                                f"耗时 {sum(s[2] for s in steps)}ms"
                            )
                            print(f"  保存到: {filepath}")
                            break
                        else:
                            print(f"  拖拽距离太短 ({distance}px), 请重新拖拽")
                            tab.run_js(_RESET_JS)
                    else:
                        tab.run_js(_RESET_JS)
            except Exception as exc:
                if wait > 0 and wait % 30 == 0:
                    print(f"  等待中... ({wait}s, {exc})")
        else:
            print("  超时 (120s), 跳过此条")

        if i < args.count - 1:
            print("  刷新页面以触发新滑块...")
            tab.run_js(_RESET_JS)
            tab.refresh()
            time.sleep(3)
            tab.run_js(_RECORDER_JS)

    print(f"\n{'=' * 50}")
    print(f"录制完成: {recorded}/{args.count} 条轨迹")
    print(f"保存目录: {TRAJECTORY_DIR}")
    print("=" * 50)

    pass


if __name__ == "__main__":
    main()
