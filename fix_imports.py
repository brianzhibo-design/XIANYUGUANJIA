with open('src/dashboard_server.py', 'r', encoding='utf-8') as f:
    content = f.read()

import_statement = """
import hashlib
import re
import gzip as _gzip_mod
import time

from src.dashboard.config_service import read_system_config as _read_system_config
from src.dashboard.mimic_ops import _safe_int
"""

content = content.replace('from src.dashboard.mimic_ops import MimicOps, _error_payload\n', 
                          'from src.dashboard.mimic_ops import MimicOps, _error_payload\n' + import_statement)

content = content.replace('_product_image_cache = {}\n', '')
content = content.replace('_PRODUCT_IMAGE_CACHE_TTL = 1800\n', '')
content = content.replace('def get_dashboard_readonly_aggregate', '_product_image_cache: dict[str, tuple[str, float]] = {}\n_PRODUCT_IMAGE_CACHE_TTL = 1800\n\ndef get_dashboard_readonly_aggregate')

with open('src/dashboard_server.py', 'w', encoding='utf-8') as f:
    f.write(content)
