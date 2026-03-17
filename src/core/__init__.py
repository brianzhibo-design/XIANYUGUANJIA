"""
核心模块
Core Module

提供配置管理、日志系统等基础能力。
浏览器相关功能请直接从 src.core.browser_client 或 src.core.playwright_client 导入。
"""

from .config import Config
from .logger import Logger

__all__ = ["Config", "Logger"]
