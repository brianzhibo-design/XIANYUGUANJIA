"""发布队列系统。

管理每日待发布的商品列表，支持自动生成、编辑、逐条/批量发布。
存储：data/publish_queue.json，建议通过 project_root 传入绝对路径。
"""

from __future__ import annotations

import asyncio
import json
import random
import time
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.core.logger import get_logger

logger = get_logger()

QUEUE_FILE = Path("data/publish_queue.json")

TITLE_TEMPLATES: dict[str, list[str]] = {
    "express": [
        "便宜快递代下单 代发 {brands} 优惠发快递 菜鸟裹裹上门取件 全国可寄",
        "【首重{price}元起】全国寄件 快递代下单 {brands} 免费上门取件",
        "寄快递低至五折 {brands} 上门取件 个人商家退换货均可",
        "便宜寄快递 快递代发优惠折扣 {brands} 菜鸟裹裹上门取件",
        "{brands}快递代下单 低价寄全国 大小件均可 免费上门取件",
        "快递代发 寄件特惠 {brands} 全国可发 上门取件 价格优惠",
        "全国寄快递 {brands} 首重低至{price}元 免费上门 大件小件都能发",
        "{brands}快递优惠 便宜代下单 菜鸟裹裹上门取件 全国不限",
        "寄快递省钱 {brands} 代发代下单 上门取件当日可发 全国通用",
        "便宜发快递 {brands} 快递代下单代发 优惠寄件 免费上门取件",
        "{brands}快递 低价寄全国 首重{price}元起 菜鸟裹裹上门取件",
        "快递代下单 {brands} 大件小件均可寄 全国免费上门取件",
        "寄件优惠 {brands} 快递代发代下单 首重{price}元起 全国可发",
        "{brands}快递代寄 便宜优惠 上门取件 个人商家退换货通用",
        "低价寄快递 快递代下单 {brands} 菜鸟上门取件 全国通发",
        "便宜快递 {brands} 代发代下单 首重{price}元起 免费上门",
    ],
}

PRICE_OPTIONS: dict[str, list[str]] = {
    "express": ["1", "1", "1", "1.5", "2", "3"],
}

DESC_TEMPLATES: dict[str, list[str]] = {
    "express": [
        "问价：\n"
        "----------------------\n"
        "寄件地--收件地--重量\n\n"
        "例如：浙江-湖南-1kg\n"
        "----------------------\n\n"
        "在线秒回，欢迎前来咨询~~~\n\n"
        "支持{brands}等主流快递\n"
        "全国免费上门取件，大件小件都能发！\n"
        "个人寄件、商家发货、退换货均可",

        "【下单流程】：\n"
        "①发给我: 例如 浙江-广东-1kg\n"
        "②我报价给您，接受就拍下\n"
        "③我改价，您付款\n\n"
        "支持{brands}等快递\n"
        "线上下单，快递员免费上门取件！\n\n"
        "⚠ 请报实际重量，超重需补差价\n"
        "体积重=长×宽×高/8000（单位厘米）\n\n"
        "在线秒回，欢迎咨询！",

        "支持{brands}等主流快递，低价寄全国\n\n"
        "📦 下单流程：直接告诉我 寄件地-收件地-重量\n"
        "💰 报价后拍下不付款，我改价后您再付款\n"
        "🚚 付款后快递员免费上门取件\n\n"
        "个人/商家/退换货均可使用\n"
        "大件小件都能发，在线秒回",

        "{brands}快递代下单，全国可发\n\n"
        "怎么下单？\n"
        "告诉我：寄件地-收件地-重量\n"
        "例如：杭州-北京-2kg\n\n"
        "我给你报价，满意就拍下\n"
        "快递员免费上门取件\n\n"
        "万一破损丢件，快递赔，保障拉满\n"
        "在线秒回，欢迎咨询~~",

        "全国寄快递 低价优惠\n\n"
        "----------------------\n"
        "报价格式：寄件地-收件地-重量\n"
        "如：上海-成都-3kg\n"
        "----------------------\n\n"
        "支持{brands}等快递\n"
        "免费上门取件，秒出单号\n"
        "个人商家退换货都能用\n\n"
        "注意：请报实际重量\n"
        "超重需要补差价哦\n"
        "在线秒回！随时欢迎咨询",
    ],
}


@dataclass
class QueueItem:
    id: str
    status: str  # draft / ready / publishing / published / failed
    scheduled_date: str  # YYYY-MM-DD
    category: str
    title: str
    description: str
    price: float | None = None
    frame_id: str = ""
    brand_asset_ids: list[str] = field(default_factory=list)
    generated_images: list[str] = field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""
    error: str | None = None
    action: str = "cold_start"  # cold_start / steady_replace
    replace_product_id: str | None = None
    published_product_id: str | None = None
    scheduled_time: str = ""  # HH:MM 格式的计划发布时间
    composition: dict[str, str] = field(default_factory=dict)  # 组合模式图层选择


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


_PUBLISH_WINDOWS = [
    (8, 30, 11, 30),   # 上午高峰（含通勤）
    (12, 0, 14, 0),    # 午休高峰
    (19, 30, 22, 0),   # 晚间高峰（下班后主力时段）
]


def _allocate_publish_times(count: int) -> list[str]:
    """在活跃时段内均匀分配发布时间，返回 HH:MM 列表。

    将三个活跃窗口的总分钟数均分给 count 条队列项，
    每个时间点加 +-15min 随机偏移模拟自然发布节奏。
    """
    slots_minutes: list[int] = []
    for h1, m1, h2, m2 in _PUBLISH_WINDOWS:
        start = h1 * 60 + m1
        end = h2 * 60 + m2
        slots_minutes.extend(range(start, end))
    if not slots_minutes or count <= 0:
        return []

    step = max(1, len(slots_minutes) // count)
    times: list[str] = []
    used: set[str] = set()
    for i in range(count):
        base = slots_minutes[min(i * step, len(slots_minutes) - 1)]
        t = ""
        for _attempt in range(20):
            jitter = random.randint(-15, 15)
            total = max(0, min(base + jitter, 23 * 60 + 59))
            t = f"{total // 60:02d}:{total % 60:02d}"
            if t not in used:
                break
        else:
            total = base
            while f"{total // 60:02d}:{total % 60:02d}" in used:
                total += 1
            t = f"{total // 60:02d}:{total % 60:02d}"
        used.add(t)
        times.append(t)
    times.sort()
    return times


def _today() -> str:
    return datetime.now().strftime("%Y-%m-%d")


class PublishQueue:
    """发布队列 CRUD + 批量发布。"""

    def __init__(
        self,
        queue_file: Path | str | None = None,
        project_root: Path | str | None = None,
    ) -> None:
        if queue_file is not None:
            self._path = Path(queue_file).resolve()
        elif project_root is not None:
            self._path = Path(project_root).resolve() / "data" / "publish_queue.json"
        else:
            self._path = Path(queue_file or QUEUE_FILE)

    def _load(self) -> list[dict]:
        if not self._path.exists():
            return []
        try:
            with open(self._path, encoding="utf-8") as f:
                data = json.load(f)
            return data if isinstance(data, list) else []
        except (json.JSONDecodeError, OSError):
            return []

    def _save(self, items: list[dict]) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._path, "w", encoding="utf-8") as f:
            json.dump(items, f, ensure_ascii=False, indent=2)

    def get_queue(self, date: str | None = None) -> list[QueueItem]:
        raw = self._load()
        items = [self._dict_to_item(d) for d in raw]
        if date:
            items = [it for it in items if it.scheduled_date == date]
        return items

    def get_item(self, item_id: str) -> QueueItem | None:
        for d in self._load():
            if d.get("id") == item_id:
                return self._dict_to_item(d)
        return None

    def add_item(self, item: QueueItem) -> QueueItem:
        if not item.id:
            item.id = str(uuid.uuid4())
        if not item.created_at:
            item.created_at = _now_iso()
        item.updated_at = _now_iso()

        raw = self._load()
        raw.append(asdict(item))
        self._save(raw)
        return item

    def update_item(self, item_id: str, updates: dict[str, Any]) -> QueueItem | None:
        raw = self._load()
        for d in raw:
            if d.get("id") == item_id:
                for k, v in updates.items():
                    if k != "id":
                        d[k] = v
                d["updated_at"] = _now_iso()
                self._save(raw)
                return self._dict_to_item(d)
        return None

    def delete_item(self, item_id: str) -> bool:
        raw = self._load()
        before = len(raw)
        raw = [d for d in raw if d.get("id") != item_id]
        if len(raw) == before:
            return False
        self._save(raw)
        return True

    def has_queue_for_date(self, date: str) -> bool:
        return any(d.get("scheduled_date") == date for d in self._load())

    async def generate_daily_queue(
        self,
        category: str = "express",
        user_schedule: dict | None = None,
    ) -> list[QueueItem]:
        """根据调度计划生成今日队列。幂等：已有则跳过。"""
        today = _today()
        if self.has_queue_for_date(today):
            logger.info(f"Queue already exists for {today}, skipping generation")
            return self.get_queue(today)

        from .scheduler import AutoPublishScheduler

        sched = AutoPublishScheduler(schedule=user_schedule)
        plan = sched.compute_daily_plan()
        action = plan.get("action", "skip")

        if action == "skip":
            logger.info("Scheduler says skip today")
            return []

        count = plan.get("new_count", 1)
        frames = self._get_available_frame_ids()

        from .brand_assets import BrandAssetManager
        mgr = BrandAssetManager()
        assets = mgr.list_assets(category=category)
        all_asset_ids = [a["id"] for a in assets]

        from .auto_publish import AutoPublishService
        svc = AutoPublishService()

        scheduled_times = _allocate_publish_times(count)

        items: list[QueueItem] = []
        for i in range(count):
            title, description = await self._ai_generate_content(svc, category, i)

            brand_items = self._load_brand_items_for_generation(mgr, all_asset_ids)
            from .templates.themes import get_random_variant
            variant = get_random_variant(category)
            frame_params = {
                "brand_items": brand_items,
                "headline": variant.get("headline", ""),
                "sub_headline": variant.get("sub_headline", ""),
                "labels": variant.get("labels", ""),
                "tagline": variant.get("tagline", ""),
            }

            frame_id = random.choice(frames) if frames else "grid_paper"
            from .image_generator import generate_frame_images
            local_images = await generate_frame_images(
                frame_id=frame_id, category=category, params=frame_params,
            )
            used_layers = {}

            replace_id = None
            if action == "steady_replace" and plan.get("replace_ids"):
                replace_ids = plan["replace_ids"]
                if i < len(replace_ids):
                    replace_id = replace_ids[i]

            item = QueueItem(
                id=str(uuid.uuid4()),
                status="draft",
                scheduled_date=today,
                category=category,
                title=title,
                description=description,
                frame_id=frame_id,
                brand_asset_ids=all_asset_ids,
                generated_images=local_images,
                created_at=_now_iso(),
                updated_at=_now_iso(),
                action=action,
                replace_product_id=replace_id,
                scheduled_time=scheduled_times[i] if i < len(scheduled_times) else "",
                composition=used_layers,
            )
            self.add_item(item)
            items.append(item)
            logger.info(f"Generated queue item {i+1}/{count}: {item.id} composition={used_layers}")

        return items

    async def regenerate_images(self, item_id: str) -> QueueItem | None:
        """重新生成指定队列项的图片。

        有 composition 字段时使用组合模式（重新随机修饰器），否则沿用 frame_id。
        """
        item = self.get_item(item_id)
        if item is None:
            return None

        from .brand_assets import BrandAssetManager
        mgr = BrandAssetManager()
        brand_items = self._load_brand_items_for_generation(mgr, item.brand_asset_ids)

        from .templates.themes import get_random_variant
        variant = get_random_variant(item.category)
        frame_params = {
            "brand_items": brand_items,
            "headline": variant.get("headline", ""),
            "sub_headline": variant.get("sub_headline", ""),
            "labels": variant.get("labels", ""),
            "tagline": variant.get("tagline", ""),
        }

        updates: dict[str, Any] = {"status": "draft"}

        if not item.frame_id:
            frames = self._get_available_frame_ids()
            item_frame = random.choice(frames) if frames else "grid_paper"
            updates["frame_id"] = item_frame
        else:
            item_frame = item.frame_id

        from .image_generator import generate_frame_images
        local_images = await generate_frame_images(
            frame_id=item_frame,
            category=item.category,
            params=frame_params,
        )
        updates["generated_images"] = local_images
        updates["composition"] = {}

        return self.update_item(item_id, updates)

    async def publish_item(self, item_id: str, config: dict | None = None) -> dict:
        """发布单条队列项。"""
        item = self.get_item(item_id)
        if item is None:
            return {"ok": False, "error": "队列项不存在"}

        if item.status == "published":
            return {"ok": False, "error": "已发布，不可重复发布"}

        cfg = config or {}
        xgj_cfg = cfg.get("xianguanjia", {})
        if not xgj_cfg.get("app_key") or not xgj_cfg.get("app_secret"):
            return {"ok": False, "error": "闲管家 AppKey/AppSecret 未配置，请在「系统配置 → 闲管家」中填写"}
        if not str(xgj_cfg.get("default_channel_cat_id", "")).strip():
            return {"ok": False, "error": "闲鱼类目ID 未配置，请在「系统配置 → 闲管家 → 默认闲鱼类目ID」中填写"}

        oss_cfg = cfg.get("oss", {})
        required_oss = ("access_key_id", "access_key_secret", "bucket", "endpoint")
        if not all(oss_cfg.get(k) for k in required_oss):
            return {"ok": False, "error": "OSS 存储未配置，请在「系统配置 → 阿里云 OSS」中填写完整"}

        if not xgj_cfg.get("default_province") or not xgj_cfg.get("default_city") or not xgj_cfg.get("default_district"):
            return {"ok": False, "error": "发货地区未配置，请在「系统配置 → 闲管家」中填写省/市/区行政编码"}

        self.update_item(item_id, {"status": "publishing"})

        from .auto_publish import AutoPublishService
        svc = AutoPublishService(config=config)

        if not item.generated_images:
            self.update_item(item_id, {"status": "failed", "error": "没有生成图片"})
            return {"ok": False, "error": "没有生成图片"}

        raw_time = getattr(item, "scheduled_time", None) or ""
        scheduled_time_str = None
        if raw_time and ":" in raw_time:
            scheduled_time_str = f"{item.scheduled_date} {raw_time}:00"

        preview_data = {
            "title": item.title,
            "description": item.description,
            "price": item.price,
            "local_images": item.generated_images,
            "scheduled_time": scheduled_time_str,
        }

        result = await svc.publish_from_preview(preview_data)

        if result.get("ok"):
            new_status = "publishing" if result.get("publish_async") else "published"
            self.update_item(item_id, {
                "status": new_status,
                "published_product_id": result.get("product_id"),
                "error": None,
            })
        else:
            self.update_item(item_id, {
                "status": "failed",
                "error": result.get("error", "发布失败"),
            })

        return result

    async def publish_batch(
        self,
        item_ids: list[str],
        interval_seconds: int = 30,
        config: dict | None = None,
    ) -> list[dict]:
        """批量发布，每条之间等待 interval_seconds ± 随机偏移。"""
        results = []
        for i, item_id in enumerate(item_ids):
            if i > 0:
                jitter = random.randint(-10, 30)
                wait = max(15, interval_seconds + jitter)
                await asyncio.sleep(wait)
            result = await self.publish_item(item_id, config=config)
            result["item_id"] = item_id
            results.append(result)
        return results

    def _get_available_frame_ids(self) -> list[str]:
        try:
            from .templates.frames import list_frames
            return [f["id"] for f in list_frames()]
        except Exception:
            return ["grid_paper", "clipboard", "torn_paper"]

    def _load_brand_items_for_generation(
        self, mgr: Any, asset_ids: list[str]
    ) -> list[dict[str, str]]:
        items = []
        for aid in asset_ids:
            path = mgr.get_asset_path(aid)
            if path is None:
                continue
            entry = None
            for a in mgr.list_assets():
                if a["id"] == aid:
                    entry = a
                    break
            from .brand_assets import file_to_data_uri
            items.append({
                "name": entry["name"] if entry else "brand",
                "src": file_to_data_uri(path),
            })
        return items

    async def _ai_generate_content(
        self, svc: Any, category: str, index: int
    ) -> tuple[str, str]:
        """使用 ContentService 生成标题和描述，AI 不可用时用模版池回退。"""
        try:
            content = svc.content_service.generate_listing_content({
                "name": category,
                "category": category,
                "features": [],
                "condition": "全新",
                "reason": "闲置出",
            })
            title = content.get("title", "")
            description = content.get("description", "")
            if title and len(title) > 3 and "【转卖】" not in title:
                return title, description
        except Exception as exc:
            logger.warning(f"AI content generation failed: {exc}")

        return self._fallback_content(category)

    def _fallback_content(self, category: str) -> tuple[str, str]:
        """AI 不可用时，从模版池生成标题和描述。"""
        from .brand_assets import BrandAssetManager
        mgr = BrandAssetManager()
        assets = mgr.list_assets(category=category)
        brand_names = sorted(set(a.get("name", "") for a in assets if a.get("name")))
        brands_str = "·".join(brand_names[:4]) if brand_names else "圆通·中通·韵达"

        prices = PRICE_OPTIONS.get(category, ["3"])
        price = random.choice(prices)

        templates = TITLE_TEMPLATES.get(category, TITLE_TEMPLATES.get("express", []))
        desc_templates = DESC_TEMPLATES.get(category, DESC_TEMPLATES.get("express", []))

        title = random.choice(templates).format(brands=brands_str, price=price) if templates else f"{category} 商品"
        desc = random.choice(desc_templates).format(brands=brands_str, price=price) if desc_templates else ""
        return title, desc

    @staticmethod
    def _dict_to_item(d: dict) -> QueueItem:
        return QueueItem(
            id=d.get("id", ""),
            status=d.get("status", "draft"),
            scheduled_date=d.get("scheduled_date", ""),
            category=d.get("category", "express"),
            title=d.get("title", ""),
            description=d.get("description", ""),
            price=d.get("price"),
            frame_id=d.get("frame_id", ""),
            brand_asset_ids=d.get("brand_asset_ids", []),
            generated_images=d.get("generated_images", []),
            created_at=d.get("created_at", ""),
            updated_at=d.get("updated_at", ""),
            error=d.get("error"),
            action=d.get("action", "cold_start"),
            replace_product_id=d.get("replace_product_id"),
            published_product_id=d.get("published_product_id"),
            scheduled_time=d.get("scheduled_time", ""),
            composition=d.get("composition", {}),
        )
