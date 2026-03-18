import sys

def split():
    with open('src/dashboard_server.py', 'r', encoding='utf-8') as f:
        lines = f.readlines()
        
    # Find the DashboardHandler class
    split_index = -1
    for i, line in enumerate(lines):
        if line.startswith('class DashboardHandler(BaseHTTPRequestHandler):'):
            split_index = i
            break
            
    if split_index == -1:
        print("Could not find DashboardHandler")
        sys.exit(1)
        
    mimic_lines = lines[:split_index]
    handler_lines = lines[split_index:]
    
    # We need to extract imports from mimic_lines that are needed by handler_lines
    # And we also add imports to handler_lines
    import_header = """\
\"\"\"轻量后台可视化与模块控制服务（分离版）。\"\"\"

from __future__ import annotations

import argparse
import cgi
import json
import logging
import mimetypes
import os
import sqlite3
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from src.core.config import get_config
from src.dashboard.module_console import ModuleConsole
from src.dashboard.repository import DashboardRepository, LiveDashboardDataSource
from src.dashboard.router import RouteContext, dispatch_delete, dispatch_get, dispatch_post, dispatch_put
from src.dashboard.mimic_ops import MimicOps, _error_payload

logger = logging.getLogger(__name__)

# Embedded HTML hack removed. UI is strictly served from client/dist now.

"""
    
    with open('src/dashboard/mimic_ops.py', 'w', encoding='utf-8') as f:
        f.writelines(mimic_lines)
        
    with open('src/dashboard_server.py', 'w', encoding='utf-8') as f:
        f.write(import_header)
        f.writelines(handler_lines)
        
split()
