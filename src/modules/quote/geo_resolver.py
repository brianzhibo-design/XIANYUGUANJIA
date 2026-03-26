"""省市解析与混配匹配支持。"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path

_SUFFIXES: tuple[str, ...] = tuple(
    sorted(("特别行政区", "自治区", "自治州", "地区", "省", "市", "盟", "区", "县"), key=len, reverse=True)
)

_logger = logging.getLogger(__name__)

# 省级地名（normalize 后）→ 用于快运/成本表查询的参考城市（省会或直辖市本体）
_PROVINCE_CAPITAL_CITIES: dict[str, str] = {
    "北京": "北京",
    "天津": "天津",
    "上海": "上海",
    "重庆": "重庆",
    "河北": "石家庄",
    "山西": "太原",
    "内蒙古": "呼和浩特",
    "辽宁": "沈阳",
    "吉林": "长春",
    "黑龙江": "哈尔滨",
    "江苏": "南京",
    "浙江": "杭州",
    "安徽": "合肥",
    "福建": "福州",
    "江西": "南昌",
    "山东": "济南",
    "河南": "郑州",
    "湖北": "武汉",
    "湖南": "长沙",
    "广东": "广州",
    "广西": "南宁",
    "海南": "海口",
    "四川": "成都",
    "贵州": "贵阳",
    "云南": "昆明",
    "西藏": "拉萨",
    "陕西": "西安",
    "甘肃": "兰州",
    "青海": "西宁",
    "宁夏": "银川",
    "新疆": "乌鲁木齐",
}


class GeoResolver:
    """读取城市-省份映射并提供标准化/混配能力。"""

    def __init__(self, mapping_file: str | Path | None = None):
        default_path = Path(__file__).resolve().parents[3] / "data" / "geo" / "city_province.json"
        self.mapping_file = Path(mapping_file) if mapping_file else default_path
        self._city_to_province: dict[str, str] = {}
        self._province_aliases: dict[str, str] = {}
        self._load()

    def _load(self) -> None:
        if not self.mapping_file.exists():
            _logger.warning(
                "GeoResolver: city_province.json not found at %s — "
                "all city/province lookups will return empty results. "
                "Please ensure data/geo/city_province.json is present.",
                self.mapping_file,
            )
            self._city_to_province = {}
            self._province_aliases = {}
            return

        payload = json.loads(self.mapping_file.read_text(encoding="utf-8"))
        # Support both flat structure {"city": "province", ...} and nested {"city_to_province": {...}}
        if isinstance(payload, dict):
            city_map = payload.get("city_to_province", payload) if "city_to_province" in payload else payload
        else:
            city_map = {}

        normalized_city_map: dict[str, str] = {}
        province_aliases: dict[str, str] = {}
        for city, province in city_map.items():
            city_name = self.normalize(city)
            province_name = self.normalize(province)
            if not city_name or not province_name:
                continue
            normalized_city_map[city_name] = province_name
            province_aliases[province_name] = province_name
            full = self.ensure_full_province_suffix(province_name)
            if full:
                province_aliases[self.normalize(full)] = province_name

        self._city_to_province = normalized_city_map
        self._province_aliases = province_aliases

    @staticmethod
    def normalize(name: str | None) -> str:
        text = re.sub(r"\s+", "", str(name or "").strip())
        if not text:
            return ""
        for suffix in _SUFFIXES:
            if text.endswith(suffix):
                return text[: -len(suffix)]
        return text

    @staticmethod
    def ensure_full_province_suffix(name: str | None) -> str:
        text = str(name or "").strip()
        if not text:
            return ""
        for suffix in ("省", "市", "自治区", "特别行政区"):
            if text.endswith(suffix):
                return text
        return f"{text}省"

    def province_of(self, name: str | None) -> str:
        normalized = self.normalize(name)
        if not normalized:
            return ""
        if normalized in self._province_aliases:
            return self._province_aliases[normalized]
        return self._city_to_province.get(normalized, "")

    def is_province_level(self, name: str | None) -> bool:
        """判断地址是否仅为省级（非市级）。"""
        normalized = self.normalize(name)
        if not normalized:
            return False
        return normalized in self._province_aliases and normalized not in self._city_to_province

    def province_to_capital(self, name: str | None) -> str | None:
        """若 name 为省级地名，返回用于报价的参考城市（省会/直辖市）；否则返回 None。"""
        normalized = self.normalize(name)
        if not normalized:
            return None
        return _PROVINCE_CAPITAL_CITIES.get(normalized)

    def resolve_freight_location(self, name: str | None) -> str:
        """快运报价用：省级自动落到省会参考市，其余保持原样。"""
        raw = str(name or "").strip()
        if not raw:
            return raw
        if not self.is_province_level(raw):
            return raw
        cap = self.province_to_capital(raw)
        return cap if cap else raw

    def expand_city_province_candidates(self, name: str | None) -> list[str]:
        normalized = self.normalize(name)
        if not normalized:
            return []

        candidates = [normalized]
        province = self.province_of(normalized)
        if province and province not in candidates:
            candidates.append(province)
        return candidates

    def cross_candidates(self, origin: str, destination: str) -> list[tuple[str, str]]:
        origin_candidates = self.expand_city_province_candidates(origin)
        destination_candidates = self.expand_city_province_candidates(destination)
        pairs: list[tuple[str, str]] = []
        for o in origin_candidates:
            for d in destination_candidates:
                pair = (o, d)
                if pair not in pairs:
                    pairs.append(pair)
        return pairs
