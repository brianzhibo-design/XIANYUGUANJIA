"""
品牌资产管理模块
Brand Asset Manager

管理商品listing图片生成所用的品牌图标上传、存储与元数据。
Storage: data/brand_assets/{uuid}.{ext}, manifest.json
"""

from __future__ import annotations

import base64
import json
import mimetypes
import re
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path


# 允许的图片扩展名，防止任意文件上传
ALLOWED_EXTENSIONS = frozenset({"png", "jpg", "jpeg", "gif", "webp", "svg"})

_MIME_MAP = {
    "png": "image/png",
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "gif": "image/gif",
    "webp": "image/webp",
    "svg": "image/svg+xml",
}


def file_to_data_uri(path: Path) -> str:
    """将本地图片文件转为 base64 data URI。

    浏览器加载本地 HTML 时，安全策略可能禁止跨域加载 ``file://`` 资源，
    因此将图片内联为 data URI 以确保正常渲染。
    """
    ext = path.suffix.lstrip(".").lower()
    mime = _MIME_MAP.get(ext) or mimetypes.guess_type(str(path))[0] or "image/png"
    with open(path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode()
    return f"data:{mime};base64,{b64}"


def _normalize_extension(ext: str) -> str:
    """将扩展名标准化为小写，去除前导点。"""
    e = ext.strip().lstrip(".").lower()
    if e == "jpg":
        return "jpg"
    return e


class BrandAssetManager:
    """
    品牌图标资产管理器。

    负责品牌图标的上传、列表、删除与路径查询。
    存储结构：data/brand_assets/{uuid}.{ext} 为文件，manifest.json 为元数据数组。
    使用锁确保 manifest 读写线程安全。
    """

    def __init__(self, base_dir: str | Path = "data/brand_assets") -> None:
        self._base = Path(base_dir)
        self._manifest_path = self._base / "manifest.json"
        self._lock = threading.RLock()

    def _ensure_dir(self) -> None:
        """确保存储目录存在。"""
        self._base.mkdir(parents=True, exist_ok=True)

    def _load_manifest(self) -> list[dict]:
        """加载 manifest，线程安全由调用方持锁保证。"""
        if not self._manifest_path.exists():
            return []
        try:
            with open(self._manifest_path, encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            return []
        return data if isinstance(data, list) else []

    def _save_manifest(self, entries: list[dict]) -> None:
        """保存 manifest，线程安全由调用方持锁保证。"""
        self._ensure_dir()
        with open(self._manifest_path, "w", encoding="utf-8") as f:
            json.dump(entries, f, ensure_ascii=False, indent=2)

    def list_assets(self, category: str | None = None) -> list[dict]:
        """
        列出所有品牌资产，可按 category 过滤。

        Args:
            category: 可选，仅返回该品类（如 express/recharge）的资产。

        Returns:
            资产字典列表，每个包含 id, name, category, filename, uploaded_at。
        """
        with self._lock:
            entries = self._load_manifest()
        if category is None:
            return list(entries)
        return [e for e in entries if e.get("category") == category]

    def add_asset(
        self,
        name: str,
        category: str,
        file_data: bytes,
        file_ext: str,
    ) -> dict:
        """
        保存上传文件并写入 manifest，返回新建资产元数据。

        Args:
            name: 用户给定的品牌名称，如 "顺丰"。
            category: 品类，如 express/recharge。
            file_data: 文件二进制内容。
            file_ext: 文件扩展名，如 png/jpg/svg。

        Returns:
            新建资产字典，包含 id, name, category, filename, uploaded_at。

        Raises:
            ValueError: 扩展名不允许。
        """
        ext = _normalize_extension(file_ext)
        if ext not in ALLOWED_EXTENSIONS:
            raise ValueError(f"Unsupported extension '{file_ext}', allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}")
        # 限制 name/category 为安全字符
        safe_name = re.sub(r"[^\w\u4e00-\u9fff\- ]", "", (name or "").strip()) or "unnamed"
        safe_category = re.sub(r"[^\w\-]", "", (category or "").strip()) or "default"

        asset_id = str(uuid.uuid4())
        filename = f"{asset_id}.{ext}"
        file_path = self._base / filename
        uploaded_at = datetime.now(timezone.utc).isoformat()

        self._ensure_dir()
        with open(file_path, "wb") as f:
            f.write(file_data)

        entry = {
            "id": asset_id,
            "name": safe_name,
            "category": safe_category,
            "filename": filename,
            "uploaded_at": uploaded_at,
        }

        with self._lock:
            entries = self._load_manifest()
            entries.append(entry)
            self._save_manifest(entries)

        return dict(entry)

    def delete_asset(self, asset_id: str) -> bool:
        """
        从 manifest 移除资产并删除磁盘文件。

        Args:
            asset_id: 资产 UUID。

        Returns:
            是否成功删除；若资产不存在则返回 False。
        """
        with self._lock:
            entries = self._load_manifest()
            idx = next((i for i, e in enumerate(entries) if e.get("id") == asset_id), None)
            if idx is None:
                return False
            entry = entries.pop(idx)
            self._save_manifest(entries)

        file_path = self._base / entry.get("filename", "")
        if file_path.exists() and file_path.is_file():
            try:
                file_path.unlink()
            except OSError:
                pass
        return True

    def get_brands_grouped(self, category: str | None = None) -> dict[str, list[dict]]:
        """按品牌名分组返回素材。

        Args:
            category: 可选品类过滤。

        Returns:
            ``{"顺丰": [asset1, asset2], "中通": [asset3]}``
        """
        assets = self.list_assets(category=category)
        grouped: dict[str, list[dict]] = {}
        for a in assets:
            grouped.setdefault(a.get("name", "unnamed"), []).append(a)
        return grouped

    def get_asset_path(self, asset_id: str) -> Path | None:
        """
        返回资产的本地文件路径。

        Args:
            asset_id: 资产 UUID。

        Returns:
            本地 Path，若资产不存在则 None。
        """
        with self._lock:
            entries = self._load_manifest()
            entry = next((e for e in entries if e.get("id") == asset_id), None)
        if entry is None:
            return None
        file_path = self._base / entry.get("filename", "")
        return file_path if file_path.exists() and file_path.is_file() else None
