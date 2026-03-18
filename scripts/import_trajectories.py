#!/usr/bin/env python3
"""从 wilinz/slider_captcha_trajectory_gen 导入真实人类滑块轨迹。

数据源: https://github.com/wilinz/slider_captcha_trajectory_gen
文件: training_data.jsonl (1,246 条真实录制轨迹)

用法:
    # 自动从 GitHub 下载
    python scripts/import_trajectories.py

    # 指定本地文件
    python scripts/import_trajectories.py --input /path/to/training_data.jsonl
"""

from __future__ import annotations

import json
import os
import re
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TRAJECTORY_DIR = ROOT / "data" / "slider_trajectories"
JSONL_URL = (
    "https://raw.githubusercontent.com/wilinz/slider_captcha_trajectory_gen"
    "/main/training_data.jsonl"
)

INPUT_RE = re.compile(r"distance:(\d+),canvas:(\d+)")
POINT_RE = re.compile(r"(-?\d+),(-?\d+),(\d+)")


def parse_line(line: str) -> dict | None:
    """解析一行 JSONL，返回 {original_distance, canvas, steps} 或 None。"""
    try:
        obj = json.loads(line)
    except json.JSONDecodeError:
        return None

    text: str = obj.get("text", "")

    m_input = INPUT_RE.search(text)
    if not m_input:
        return None
    distance = int(m_input.group(1))
    canvas = int(m_input.group(2))

    output_start = text.find("<|output|>")
    output_end = text.find("<|end|>")
    if output_start < 0 or output_end < 0:
        return None
    raw_output = text[output_start + len("<|output|>"):output_end]

    points = []
    for token in raw_output.split(";"):
        m = POINT_RE.match(token.strip())
        if m:
            points.append((int(m.group(1)), int(m.group(2)), int(m.group(3))))

    if len(points) < 3:
        return None

    steps: list[list[int]] = []
    for i in range(1, len(points)):
        dx = points[i][0] - points[i - 1][0]
        dy = points[i][1] - points[i - 1][1]
        dt = points[i][2]
        if dx != 0 or dy != 0:
            steps.append([dx, dy, max(1, dt)])

    if len(steps) < 3 or distance < 30:
        return None

    return {
        "original_distance": distance,
        "canvas": canvas,
        "total_steps": len(steps),
        "total_duration_ms": sum(s[2] for s in steps),
        "source": "wilinz/slider_captcha_trajectory_gen",
        "steps": steps,
    }


def download_jsonl(dest: Path) -> None:
    print(f"正在从 GitHub 下载 training_data.jsonl ...")
    urllib.request.urlretrieve(JSONL_URL, str(dest))
    size_kb = dest.stat().st_size / 1024
    print(f"下载完成: {size_kb:.1f} KB")


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="导入开源滑块轨迹数据")
    parser.add_argument("--input", type=str, default=None, help="本地 training_data.jsonl 路径")
    args = parser.parse_args()

    if args.input:
        jsonl_path = Path(args.input)
    else:
        jsonl_path = ROOT / "data" / "training_data.jsonl"
        if not jsonl_path.exists():
            jsonl_path.parent.mkdir(parents=True, exist_ok=True)
            download_jsonl(jsonl_path)

    if not jsonl_path.exists():
        print(f"错误: 文件不存在 {jsonl_path}")
        sys.exit(1)

    TRAJECTORY_DIR.mkdir(parents=True, exist_ok=True)

    imported = 0
    skipped = 0
    with open(jsonl_path, "r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            result = parse_line(line)
            if result is None:
                skipped += 1
                continue

            filename = f"traj_import_{imported + 1:04d}.json"
            filepath = TRAJECTORY_DIR / filename
            filepath.write_text(json.dumps(result, indent=2), encoding="utf-8")
            imported += 1

    print(f"\n导入完成:")
    print(f"  成功: {imported} 条轨迹")
    print(f"  跳过: {skipped} 条 (格式不符或质量不足)")
    print(f"  保存目录: {TRAJECTORY_DIR}")

    if imported > 0:
        sample = json.loads((TRAJECTORY_DIR / "traj_import_0001.json").read_text("utf-8"))
        print(f"\n示例轨迹 (traj_import_0001.json):")
        print(f"  距离: {sample['original_distance']}px")
        print(f"  步数: {sample['total_steps']}")
        print(f"  耗时: {sample['total_duration_ms']}ms")
        print(f"  前3步: {sample['steps'][:3]}")


if __name__ == "__main__":
    main()
