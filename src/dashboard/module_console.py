"""Module control via CLI — start/stop/restart/status/logs for presales/operations/aftersales."""

from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

MODULE_TARGETS = ("presales", "operations", "aftersales")


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


class ModuleConsole:
    """通过 CLI 复用模块状态与控制能力。"""

    _STATUS_CACHE_TTL: float = 15.0

    def __init__(self, project_root: str | Path):
        self.project_root = Path(project_root).resolve()
        self._status_cache: dict[str, Any] | None = None
        self._status_cache_ts: float = 0.0
        self._status_cache_key: str = ""

    def _run_module_cli(
        self,
        action: str,
        target: str,
        extra_args: list[str] | None = None,
        timeout_seconds: int = 120,
    ) -> dict[str, Any]:
        cmd = [
            sys.executable,
            "-m",
            "src.cli",
            "module",
            "--action",
            action,
            "--target",
            target,
            *(extra_args or []),
        ]

        try:
            proc = subprocess.run(
                cmd,
                cwd=str(self.project_root),
                capture_output=True,
                text=True,
                timeout=max(10, int(timeout_seconds)),
            )
        except Exception as exc:
            return {"error": f"Module CLI execution failed: {exc}", "_cli_cmd": " ".join(cmd)}

        payload = _extract_json_payload(proc.stdout)

        if proc.returncode != 0:
            base: dict[str, Any]
            if isinstance(payload, dict):
                base = dict(payload)
            else:
                base = {"error": f"module command failed ({proc.returncode})"}
            if "error" not in base:
                stderr = (proc.stderr or "").strip()
                base["error"] = stderr or f"module command failed ({proc.returncode})"
            base["_cli_code"] = proc.returncode
            base["_cli_stderr"] = (proc.stderr or "").strip()
            base["_cli_cmd"] = " ".join(cmd)
            return base

        if isinstance(payload, dict):
            return payload
        if isinstance(payload, list):
            return {"items": payload}
        return {"ok": True, "stdout": (proc.stdout or "").strip(), "_cli_cmd": " ".join(cmd)}

    def status(self, window_minutes: int = 60, limit: int = 20) -> dict[str, Any]:
        cache_key = f"{window_minutes}:{limit}"
        now = time.time()
        if (
            self._status_cache is not None
            and cache_key == self._status_cache_key
            and (now - self._status_cache_ts) < self._STATUS_CACHE_TTL
        ):
            return self._status_cache
        result = self._run_module_cli(
            action="status",
            target="all",
            extra_args=["--window-minutes", str(window_minutes), "--limit", str(limit)],
            timeout_seconds=90,
        )
        self._status_cache = result
        self._status_cache_key = cache_key
        self._status_cache_ts = now
        return result

    def logs(self, target: str, tail_lines: int = 120) -> dict[str, Any]:
        safe_target = target if target in {"all", *MODULE_TARGETS} else "all"
        return self._run_module_cli(
            action="logs",
            target=safe_target,
            extra_args=["--tail-lines", str(max(10, min(int(tail_lines), 500)))],
            timeout_seconds=90,
        )

    def check(self) -> dict[str, Any]:
        return self._run_module_cli(action="check", target="all", extra_args=[], timeout_seconds=120)

    def control(self, action: str, target: str) -> dict[str, Any]:
        act = str(action or "").strip().lower()
        tgt = str(target or "").strip().lower()

        if act not in {"start", "stop", "restart", "recover"}:
            return {"error": f"Unsupported module action: {act}"}
        if tgt not in {"all", *MODULE_TARGETS}:
            return {"error": f"Unsupported module target: {tgt}"}

        args: list[str] = []
        if act in ("start", "restart", "recover"):
            args.extend(
                [
                    "--mode",
                    "daemon",
                    "--background",
                    "--interval",
                    "5",
                    "--limit",
                    "20",
                    "--claim-limit",
                    "10",
                    "--issue-type",
                    "delay",
                    "--init-default-tasks",
                ]
            )
            if act in ("restart", "recover"):
                args.extend(["--stop-timeout", "6"])
        else:
            args.extend(["--stop-timeout", "6"])

        result = self._run_module_cli(action=act, target=tgt, extra_args=args, timeout_seconds=120)
        self._status_cache = None
        return result
