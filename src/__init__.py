"""
闲鱼自动化工具
Xianyu Automation Tool

API-first 闲鱼自动化运营工具
"""

__version__ = "1.0.0"
__author__ = "Project Team"

from .core.browser_client import BrowserClient
from .core.config import Config
from .core.logger import Logger

__all__ = [
    "BrowserClient",
    "Config",
    "Logger",
    "__version__",
]
