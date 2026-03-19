"""自动上架调度器。

全品类统一冷启动策略：
- D1: 新建 5 条链接
- D2: 新建 5 条链接
- D3+: 每天替换 1 条流量最差的链接

使用 JSON 文件持久化调度状态，每日执行一次。
"""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.core.logger import get_logger

logger = get_logger()

DEFAULT_PUBLISH_SCHEDULE = {
    "cold_start_days": 2,
    "cold_start_daily_count": 5,
    "steady_replace_count": 1,
    "steady_replace_metric": "views",
    "max_active_listings": 10,
}

STATE_FILE = Path("data/auto_publish_state.json")


@dataclass
class SchedulerState:
    """Persisted scheduler state."""

    first_run_date: str = ""
    total_days_active: int = 0
    last_run_date: str = ""
    active_listing_ids: list[str] = field(default_factory=list)
    history: list[dict[str, Any]] = field(default_factory=list)

    def save(self, path: Path | None = None) -> None:
        p = path or STATE_FILE
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            json.dump(asdict(self), f, ensure_ascii=False, indent=2)

    @classmethod
    def load(cls, path: Path | None = None) -> SchedulerState:
        p = path or STATE_FILE
        if not p.exists():
            return cls()
        try:
            with open(p, encoding="utf-8") as f:
                data = json.load(f)
            return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
        except Exception:
            return cls()


class AutoPublishScheduler:
    """Daily auto-publish scheduler with cold-start ramp-up and worst-performer replacement."""

    def __init__(
        self,
        schedule: dict[str, Any] | None = None,
        state_path: Path | None = None,
    ) -> None:
        self.schedule = {**DEFAULT_PUBLISH_SCHEDULE, **(schedule or {})}
        self.state_path = state_path or STATE_FILE
        self.state = SchedulerState.load(self.state_path)

    def _today_str(self) -> str:
        return datetime.now(timezone.utc).strftime("%Y-%m-%d")

    def already_ran_today(self) -> bool:
        return self.state.last_run_date == self._today_str()

    def compute_daily_plan(self) -> dict[str, Any]:
        """Compute what actions to take today without executing them.

        Returns a plan dict:
          - action: "cold_start" | "steady_replace" | "skip"
          - new_count: number of new listings to create
          - replace_count: number of worst-performers to replace
          - day_number: which day we are on (1-indexed)
        """
        today = self._today_str()
        if self.state.last_run_date == today:
            return {"action": "skip", "reason": "already_ran_today", "day_number": self.state.total_days_active}

        if not self.state.first_run_date:
            day_number = 1
        else:
            day_number = self.state.total_days_active + 1

        cold_days = self.schedule["cold_start_days"]
        daily_count = self.schedule["cold_start_daily_count"]
        replace_count = self.schedule["steady_replace_count"]
        max_active = self.schedule["max_active_listings"]

        if day_number <= cold_days:
            current_active = len(self.state.active_listing_ids)
            can_add = max(0, max_active - current_active)
            new_count = min(daily_count, can_add)
            return {
                "action": "cold_start",
                "new_count": new_count,
                "replace_count": 0,
                "day_number": day_number,
            }
        else:
            return {
                "action": "steady_replace",
                "new_count": replace_count,
                "replace_count": replace_count,
                "day_number": day_number,
            }

    def find_worst_performers(
        self,
        metrics: list[dict[str, Any]],
        count: int = 1,
    ) -> list[str]:
        """Given a list of {product_id, views, wants, ...}, return the worst `count` product_ids."""
        metric_key = self.schedule.get("steady_replace_metric", "views")
        active_set = set(self.state.active_listing_ids)
        relevant = [m for m in metrics if m.get("product_id") in active_set]
        relevant.sort(key=lambda m: m.get(metric_key, 0))
        return [m["product_id"] for m in relevant[:count]]

    def record_execution(
        self,
        plan: dict[str, Any],
        created_ids: list[str],
        removed_ids: list[str],
    ) -> None:
        """After executing a plan, update persisted state."""
        today = self._today_str()
        if not self.state.first_run_date:
            self.state.first_run_date = today

        self.state.total_days_active = plan.get("day_number", self.state.total_days_active)
        self.state.last_run_date = today

        for rid in removed_ids:
            if rid in self.state.active_listing_ids:
                self.state.active_listing_ids.remove(rid)

        self.state.active_listing_ids.extend(created_ids)

        self.state.history.append(
            {
                "date": today,
                "action": plan.get("action"),
                "day_number": plan.get("day_number"),
                "created": created_ids,
                "removed": removed_ids,
                "active_count": len(self.state.active_listing_ids),
                "ts": time.time(),
            }
        )
        if len(self.state.history) > 90:
            self.state.history = self.state.history[-90:]

        self.state.save(self.state_path)

    def get_status(self) -> dict[str, Any]:
        """Return current scheduler status for dashboard display."""
        plan = self.compute_daily_plan()
        return {
            "schedule": self.schedule,
            "state": {
                "first_run_date": self.state.first_run_date,
                "total_days_active": self.state.total_days_active,
                "last_run_date": self.state.last_run_date,
                "active_listings": len(self.state.active_listing_ids),
                "active_listing_ids": self.state.active_listing_ids,
            },
            "today_plan": plan,
            "recent_history": self.state.history[-7:],
        }
