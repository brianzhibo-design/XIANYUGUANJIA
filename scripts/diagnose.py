#!/usr/bin/env python3
"""
闲鱼管家 — 新设备部署诊断脚本
用法: PYTHONPATH=. python3 scripts/diagnose.py

逐项检测 4 大问题:
  1. API 超时 (/service-status 15s 超时)
  2. 话术模板加载
  3. Playwright 浏览器拉起
  4. 自动回复链路
"""

from __future__ import annotations

import asyncio
import json
import os
import platform
import shutil
import sqlite3
import subprocess
import sys
import time
from pathlib import Path

# ── Windows 控制台 UTF-8 兼容 ─────────────────────────────
if platform.system() == "Windows":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# ── 颜色 ──────────────────────────────────────────────────
RED = "\033[0;31m"
GREEN = "\033[0;32m"
YELLOW = "\033[1;33m"
CYAN = "\033[0;36m"
BOLD = "\033[1m"
NC = "\033[0m"

passed_count = 0
failed_count = 0
warn_count = 0


def ok(msg: str) -> None:
    global passed_count
    passed_count += 1
    print(f"  {GREEN}✓{NC} {msg}")


def fail(msg: str, hint: str = "") -> None:
    global failed_count
    failed_count += 1
    print(f"  {RED}✗{NC} {msg}")
    if hint:
        print(f"    {YELLOW}→ {hint}{NC}")


def warn(msg: str, hint: str = "") -> None:
    global warn_count
    warn_count += 1
    print(f"  {YELLOW}!{NC} {msg}")
    if hint:
        print(f"    {YELLOW}→ {hint}{NC}")


def section(title: str) -> None:
    print(f"\n{BOLD}{CYAN}{'=' * 50}{NC}")
    print(f"{BOLD}{CYAN}  {title}{NC}")
    print(f"{BOLD}{CYAN}{'=' * 50}{NC}\n")


# ══════════════════════════════════════════════════════════
#  0. 基础环境
# ══════════════════════════════════════════════════════════
def check_environment():
    section("0. 基础环境")

    # Python 版本
    v = sys.version_info
    if v >= (3, 10):
        ok(f"Python {v.major}.{v.minor}.{v.micro}")
    else:
        fail(f"Python {v.major}.{v.minor}.{v.micro} — 需要 3.10+", "安装 Python 3.10 以上版本")

    # 操作系统
    os_name = platform.system()
    os_ver = platform.version()
    ok(f"操作系统: {os_name} {platform.release()} ({os_ver[:60]})")

    # Node.js
    node = shutil.which("node")
    if node:
        try:
            ver = subprocess.check_output([node, "-v"], timeout=5).decode().strip()
            ok(f"Node.js: {ver}")
        except Exception as e:
            warn(f"Node.js 存在但无法获取版本: {e}")
    else:
        fail("Node.js 未安装", "安装 Node.js 18+")

    # 关键目录
    for d in ["data", "logs", "config"]:
        p = Path(d)
        if p.exists():
            if os.access(p, os.W_OK):
                ok(f"目录可写: {d}/")
            else:
                fail(f"目录不可写: {d}/", f"chmod -R 755 {d}")
        else:
            warn(f"目录不存在: {d}/", f"mkdir -p {d}")

    # 端口占用
    for port in [8091, 3001, 5173]:
        try:
            import socket
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(1)
            result = s.connect_ex(("127.0.0.1", port))
            s.close()
            if result == 0:
                ok(f"端口 {port} 有服务在监听")
            else:
                warn(f"端口 {port} 无服务监听", "服务可能未启动")
        except Exception:
            warn(f"端口 {port} 检测失败")


# ══════════════════════════════════════════════════════════
#  1. API 超时诊断 (/service-status 为何 >15s)
# ══════════════════════════════════════════════════════════
def check_api_timeout():
    section("1. API 超时诊断 (/service-status)")

    import socket
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(2)
    if s.connect_ex(("127.0.0.1", 8091)) != 0:
        s.close()
        fail("Python 后端 (8091) 未启动，跳过 API 测试", "PYTHONPATH=. python3 src/dashboard_server.py")
        return
    s.close()

    try:
        import urllib.request

        # 1a. 基础健康检查
        t0 = time.time()
        try:
            req = urllib.request.Request("http://127.0.0.1:8091/api/health/check")
            resp = urllib.request.urlopen(req, timeout=5)
            elapsed = time.time() - t0
            if elapsed < 1:
                ok(f"/api/health/check: {elapsed:.1f}s")
            else:
                warn(f"/api/health/check: {elapsed:.1f}s — 偏慢", "检查 CPU / 磁盘 IO")
        except Exception as e:
            fail(f"/api/health/check 失败: {e}")

        # 1b. service-status（最可能超时的接口）
        t0 = time.time()
        try:
            req = urllib.request.Request("http://127.0.0.1:8091/api/service-status")
            resp = urllib.request.urlopen(req, timeout=20)
            elapsed = time.time() - t0
            body = json.loads(resp.read())

            if elapsed < 5:
                ok(f"/api/service-status: {elapsed:.1f}s")
            elif elapsed < 15:
                warn(f"/api/service-status: {elapsed:.1f}s — 接近超时阈值 15s")
            else:
                fail(f"/api/service-status: {elapsed:.1f}s — 超过前端 15s 超时阈值")

            # 分析慢在哪里
            _diagnose_service_status_bottleneck(body)

        except Exception as e:
            elapsed = time.time() - t0
            fail(f"/api/service-status 超时或失败 ({elapsed:.1f}s): {e}")
            print()
            print(f"    {YELLOW}可能原因:{NC}")
            print(f"    1. CookieHealthChecker.check_sync() 阻塞 — Cookie 在线探测 goofish.com 超时")
            print(f"    2. _risk_control_status_from_logs() 扫描日志文件过大")
            print(f"    3. ModuleConsole.status() 子进程检查卡住")
            print(f"    4. route_stats() 报价统计查询慢")
            print(f"    5. 前端 axios 超时 15s 太短（默认值）")

    except ImportError:
        fail("urllib 不可用")


def _diagnose_service_status_bottleneck(body: dict) -> None:
    """分析 service_status 返回体，推断哪个子步骤慢。"""
    # Cookie 健康检查
    cookie_health = body.get("cookie_health", {})
    if not body.get("cookie_exists"):
        warn("Cookie 未配置 — CookieHealthChecker 会尝试探测 goofish.com 后超时",
             "先配置 Cookie 再启动服务")
    elif not cookie_health.get("healthy"):
        warn(f"Cookie 不健康: {cookie_health.get('message', '未知')}",
             "Cookie 可能过期，在线探测 goofish.com 会增加延迟")

    # 模块进程
    modules = body.get("module", {})
    if isinstance(modules, dict):
        alive = modules.get("alive_count", 0)
        total = modules.get("total_modules", 0)
        if alive == 0:
            warn(f"无存活模块进程 ({alive}/{total})",
                 "presales 模块未启动，status 查询会触发进程检查 + 超时等待")

    # 风控日志扫描
    risk = body.get("risk_control", {})
    if isinstance(risk, dict) and risk.get("level") == "stale":
        ok("风控日志: 无异常信号")
    elif isinstance(risk, dict):
        warn(f"风控级别: {risk.get('level', 'unknown')}",
             "日志扫描可能耗时，检查 data/module_runtime/presales.log 文件大小")

    # 闲管家配置
    xgj = body.get("xianguanjia", {})
    if isinstance(xgj, dict) and not xgj.get("app_key"):
        warn("闲管家 app_key 未配置", "在 Dashboard 配置页或 .env 中设置 XGJ_APP_KEY")


# ══════════════════════════════════════════════════════════
#  2. 话术模板加载诊断
# ══════════════════════════════════════════════════════════
def check_reply_templates():
    section("2. 话术模板诊断")

    # 2a. 检查 system_config.json 中的 auto_reply 配置
    sys_cfg_path = Path("data/system_config.json")
    sys_cfg: dict = {}
    if sys_cfg_path.exists():
        try:
            sys_cfg = json.loads(sys_cfg_path.read_text(encoding="utf-8"))
            ok(f"system_config.json 存在 ({sys_cfg_path.stat().st_size} bytes)")
        except Exception as e:
            fail(f"system_config.json 解析失败: {e}")
    else:
        fail("data/system_config.json 不存在",
             "Dashboard 配置从未保存过 — 在前端 /config 页面保存一次")

    auto_reply_cfg = sys_cfg.get("auto_reply", {})
    if auto_reply_cfg:
        ok(f"auto_reply 配置段存在: {list(auto_reply_cfg.keys())}")
        default_reply = auto_reply_cfg.get("default_reply", "")
        if default_reply:
            ok(f"default_reply: \"{default_reply[:40]}...\"")
        else:
            warn("default_reply 为空 — 未配置默认回复话术",
                 "在 Dashboard → 自动回复 → 默认回复 中设置")
    else:
        warn("auto_reply 配置段缺失", "在 Dashboard → 自动回复中配置")

    # 2b. 检查 config.yaml 中的话术
    config_path = Path("config/config.yaml")
    if config_path.exists():
        try:
            import yaml
            cfg = yaml.safe_load(config_path.read_text(encoding="utf-8"))
            msg_cfg = cfg.get("messages", {}) if isinstance(cfg, dict) else {}
            if msg_cfg.get("default_reply"):
                ok(f"config.yaml messages.default_reply: \"{str(msg_cfg['default_reply'])[:40]}...\"")
            else:
                warn("config.yaml 中 messages.default_reply 未设置")

            # 检查 intent_rules
            intent_rules = msg_cfg.get("intent_rules", [])
            if intent_rules:
                ok(f"config.yaml 自定义意图规则: {len(intent_rules)} 条")
            else:
                ok("config.yaml 无自定义意图规则 — 使用内置默认规则")
        except Exception as e:
            warn(f"config.yaml 解析失败: {e}")
    else:
        warn("config/config.yaml 不存在 — 使用 config.example.yaml 默认值")

    # 2c. 尝试实例化 ReplyStrategyEngine 看话术是否正确加载
    try:
        from src.modules.messages.reply_engine import ReplyStrategyEngine, DEFAULT_INTENT_RULES

        engine = ReplyStrategyEngine(
            default_reply=auto_reply_cfg.get("default_reply", "您好，请问有什么可以帮您？"),
            virtual_default_reply=auto_reply_cfg.get("virtual_default_reply", ""),
        )
        ok(f"ReplyStrategyEngine 初始化成功 — {len(engine.rules)} 条规则")

        # 模拟测试
        test_cases = [
            ("你好", "打招呼"),
            ("多少钱", "报价询问"),
            ("广东到浙江3kg", "报价请求"),
            ("发货了吗", "售后"),
        ]
        for text, desc in test_cases:
            reply, skip = engine.generate_reply(text)
            if skip:
                ok(f"  「{text}」({desc}) → [跳过] ✓")
            elif reply:
                ok(f"  「{text}」({desc}) → \"{reply[:30]}...\"")
            else:
                warn(f"  「{text}」({desc}) → 空回复", "规则可能未覆盖此意图")

    except Exception as e:
        fail(f"ReplyStrategyEngine 初始化失败: {e}", "检查依赖是否安装完整")

    # 2d. 检查 AI 配置（AI 意图识别可能覆盖模板话术）
    ai_cfg = sys_cfg.get("ai", {})
    if ai_cfg.get("api_key"):
        ok(f"AI 已配置: provider={ai_cfg.get('provider', '?')}, model={ai_cfg.get('model', '?')}")
        ai_intent = auto_reply_cfg.get("ai_intent_enabled", False)
        if ai_intent:
            warn("AI 意图识别已开启 — AI 生成的回复可能覆盖模板话术",
                 "如需严格走模板，在 Dashboard → 自动回复 → 关闭 AI 意图识别")
        else:
            ok("AI 意图识别未开启 — 回复走模板规则")
    else:
        api_key_env = os.environ.get("AI_API_KEY", "")
        if api_key_env and not api_key_env.startswith("your_"):
            ok(f"AI API Key 来自环境变量 (len={len(api_key_env)})")
        else:
            warn("AI API Key 未配置 — 完全走模板回复",
                 "如需 AI 智能回复，在 Dashboard → AI 配置中设置")


# ══════════════════════════════════════════════════════════
#  3. Playwright / 浏览器拉起诊断
# ══════════════════════════════════════════════════════════
def check_playwright():
    section("3. Playwright 浏览器拉起诊断")

    os_name = platform.system()
    ok(f"当前平台: {os_name} {platform.machine()}")

    # 3a. playwright 是否安装
    try:
        import playwright
        pw_ver = getattr(playwright, "__version__", None)
        if not pw_ver:
            try:
                from importlib.metadata import version as pkg_version
                pw_ver = pkg_version("playwright")
            except Exception:
                pw_ver = "unknown"
        ok(f"playwright 库已安装: {pw_ver}")
    except ImportError:
        fail("playwright 库未安装", "pip install playwright")
        return

    # 3a-2. greenlet 依赖检查 (Windows 常见问题)
    try:
        import greenlet
        ok("greenlet 依赖正常")
    except ImportError as e:
        err_msg = str(e)
        if "DLL" in err_msg:
            fail(f"greenlet 导入失败: {err_msg}",
                 "安装 Microsoft Visual C++ Redistributable 2015-2022 (x64)")
        else:
            fail(f"greenlet 导入失败: {err_msg}", "pip install greenlet")

    # 3b. Chromium 浏览器是否下载
    try:
        result = subprocess.run(
            [sys.executable, "-c", """
import json, subprocess, sys
r = subprocess.run([sys.executable, '-m', 'playwright', 'install', '--dry-run', 'chromium'],
                   capture_output=True, text=True, timeout=10)
print(r.stdout[:500])
print(r.stderr[:500])
"""],
            capture_output=True, text=True, timeout=15,
        )
        output = result.stdout + result.stderr
        if "is already installed" in output.lower() or "already installed" in output.lower():
            ok("Chromium 浏览器已下载")
        else:
            warn("Chromium 可能未下载", "运行: playwright install chromium")
    except Exception:
        pass

    # 3c. 真实拉起测试
    try:
        result = subprocess.run(
            [sys.executable, "-c", """
import sys
try:
    from playwright.sync_api import sync_playwright
    p = sync_playwright().start()
    try:
        b = p.chromium.launch(headless=True, timeout=10000)
        page = b.new_page()
        page.goto("about:blank", timeout=5000)
        b.close()
        print("LAUNCH_OK")
    except Exception as e:
        print(f"LAUNCH_FAIL:{e}")
    finally:
        p.stop()
except Exception as e:
    print(f"IMPORT_FAIL:{e}")
"""],
            capture_output=True, text=True, timeout=30,
        )
        output = result.stdout.strip()
        stderr = result.stderr.strip()

        if "LAUNCH_OK" in output:
            ok("Chromium headless 拉起成功")
        elif "LAUNCH_FAIL" in output:
            error = output.split("LAUNCH_FAIL:", 1)[-1]
            fail(f"Chromium 拉起失败: {error[:120]}")

            if os_name == "Windows":
                print(f"\n    {YELLOW}Windows 常见原因:{NC}")
                print(f"    1. 未运行 'playwright install chromium' 下载浏览器")
                print(f"    2. 杀毒软件拦截 Chromium 进程")
                print(f"    3. 缺少 Visual C++ Redistributable")
                print(f"    4. 系统防火墙阻止 WebSocket 连接")
                print(f"    5. 路径包含中文或特殊字符")
            elif os_name == "Linux":
                print(f"\n    {YELLOW}Linux 常见原因:{NC}")
                print(f"    1. 缺少系统依赖: playwright install-deps chromium")
                print(f"    2. 无头服务器无 display: 确保用 headless=True")
                print(f"    3. 缺少 libgbm, libnss3, libatk 等库")
        elif "IMPORT_FAIL" in output:
            fail(f"playwright 导入失败: {output}")
        else:
            fail(f"Chromium 测试异常: stdout={output[:80]}, stderr={stderr[:80]}")

    except subprocess.TimeoutExpired:
        fail("Chromium 拉起超时 (>30s)", "可能缺少系统依赖或 Chromium 下载不完整")
    except Exception as e:
        fail(f"Chromium 测试异常: {e}")

    # 3d. rookiepy 检查（Cookie Level 1 直读浏览器 DB）
    try:
        import rookiepy
        ok(f"rookiepy 已安装 — 支持 Level 1 直读浏览器 Cookie")

        # 测试能否读取
        try:
            cookies = rookiepy.chrome([".goofish.com", ".taobao.com"])
            goofish_cookies = [c for c in cookies if "goofish" in c.get("domain", "")]
            if goofish_cookies:
                ok(f"rookiepy 读取到 {len(goofish_cookies)} 条 goofish cookie")
            else:
                warn("rookiepy 未读取到 goofish cookie — 该浏览器可能未登录闲鱼")
        except Exception as e:
            warn(f"rookiepy 读取失败: {str(e)[:80]}", "浏览器可能未安装或 Cookie 数据库被锁定")
    except ImportError:
        warn("rookiepy 未安装 — Level 1 直读浏览器 Cookie 不可用", "pip install rookiepy")


# ══════════════════════════════════════════════════════════
#  4. 自动回复链路诊断
# ══════════════════════════════════════════════════════════
def check_auto_reply():
    section("4. 自动回复链路诊断")

    # 4a. Cookie
    from dotenv import load_dotenv
    load_dotenv(override=False)

    cookie = os.environ.get("XIANYU_COOKIE_1", "")
    if not cookie or cookie.startswith("your_"):
        fail("XIANYU_COOKIE_1 未配置或是占位符", "在 .env 中设置有效的 Cookie")
    elif len(cookie) < 50:
        fail(f"XIANYU_COOKIE_1 太短 ({len(cookie)} 字符)，可能不完整")
    else:
        ok(f"XIANYU_COOKIE_1 已配置 ({len(cookie)} 字符)")

        # 检查关键字段
        from src.modules.messages.ws_live import parse_cookie_header
        parsed = parse_cookie_header(cookie)
        required_fields = {"unb": "用户ID", "cookie2": "会话Token", "sgcookie": "签名Cookie"}
        session_fields = {"_tb_token_": "TB Token", "_m_h5_tk": "H5 Token"}

        for field, desc in required_fields.items():
            if parsed.get(field):
                ok(f"  Cookie 字段 {field} ({desc}): ✓")
            else:
                fail(f"  Cookie 字段 {field} ({desc}): 缺失", "Cookie 不完整，需重新获取")

        for field, desc in session_fields.items():
            if parsed.get(field):
                ok(f"  Cookie 字段 {field} ({desc}): ✓")
            else:
                warn(f"  Cookie 字段 {field} ({desc}): 缺失", "运行时会自动补全")

    # 4b. WebSocket 依赖
    try:
        import websockets
        ok(f"websockets 库已安装: {websockets.__version__}")
    except ImportError:
        fail("websockets 库未安装 — WebSocket 通道不可用", "pip install websockets")

    # 4c. 闲管家凭证
    xgj_key = os.environ.get("XGJ_APP_KEY", "")
    xgj_secret = os.environ.get("XGJ_APP_SECRET", "")

    if not xgj_key and not xgj_secret:
        sys_cfg_path = Path("data/system_config.json")
        if sys_cfg_path.exists():
            try:
                cfg = json.loads(sys_cfg_path.read_text(encoding="utf-8"))
                xgj = cfg.get("xianguanjia", {})
                xgj_key = xgj.get("app_key", "")
                xgj_secret = xgj.get("app_secret", "")
            except Exception:
                pass

    if xgj_key and xgj_secret:
        ok(f"闲管家凭证: app_key={xgj_key[:8]}..., secret=****")
    elif xgj_key:
        warn("闲管家 app_secret 缺失", "在 Dashboard 配置页或 .env 中设置")
    else:
        fail("闲管家凭证未配置 (XGJ_APP_KEY / XGJ_APP_SECRET)",
             "WebSocket 签名依赖此凭证，会导致连接认证失败")

    # 4d. WebSocket 连通性测试
    print()
    try:
        import socket
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(5)
        try:
            # DNS 解析
            ip = socket.gethostbyname("wss-goofish.dingtalk.com")
            ok(f"DNS 解析 wss-goofish.dingtalk.com → {ip}")
        except socket.gaierror:
            fail("DNS 解析 wss-goofish.dingtalk.com 失败", "检查网络连接和 DNS 设置")

        try:
            s.connect(("wss-goofish.dingtalk.com", 443))
            ok("TCP 连接 wss-goofish.dingtalk.com:443 成功")
        except Exception as e:
            fail(f"TCP 连接 wss-goofish.dingtalk.com:443 失败: {e}",
                 "防火墙/代理可能阻止 WSS 连接")
        finally:
            s.close()
    except Exception as e:
        warn(f"WebSocket 连通性检测异常: {e}")

    # 4e. Cookie 在线验证
    if cookie and len(cookie) > 50:
        try:
            import urllib.request
            req = urllib.request.Request(
                "https://www.goofish.com/im",
                headers={"Cookie": cookie, "User-Agent": "Mozilla/5.0"},
            )
            t0 = time.time()
            resp = urllib.request.urlopen(req, timeout=10)
            elapsed = time.time() - t0
            status = resp.getcode()
            url = resp.geturl()

            if status == 200 and "login" not in url:
                ok(f"Cookie 在线验证通过 ({elapsed:.1f}s)")
            else:
                fail(f"Cookie 可能失效 — 重定向到 {url[:60]}",
                     "Cookie 已过期，需重新获取")
        except Exception as e:
            warn(f"Cookie 在线验证失败: {str(e)[:80]}",
                 "网络不通或 goofish.com 不可达")

    # 4f. 自动回复开关
    sys_cfg_path = Path("data/system_config.json")
    if sys_cfg_path.exists():
        try:
            cfg = json.loads(sys_cfg_path.read_text(encoding="utf-8"))
            ar = cfg.get("auto_reply", {})
            if ar.get("enabled", True):
                ok("自动回复开关: 已开启")
            else:
                fail("自动回复开关: 已关闭", "在 Dashboard → 自动回复 → 启用")
        except Exception:
            pass

    # 4g. presales 模块进程
    log_path = Path("data/module_runtime/presales.log")
    if log_path.exists():
        size = log_path.stat().st_size
        ok(f"presales 日志存在 ({size / 1024:.0f} KB)")

        # 读最后几行看状态
        try:
            lines = log_path.read_text(encoding="utf-8", errors="ignore").strip().split("\n")
            last_lines = lines[-5:]
            ws_connected = any("Connected to Goofish WebSocket" in l for l in last_lines)
            ws_error = any("auth" in l.lower() and ("error" in l.lower() or "fail" in l.lower()) for l in last_lines)

            if ws_connected:
                ok("WebSocket 最近日志: 已连接")
            elif ws_error:
                fail("WebSocket 最近日志: 认证失败", "检查 Cookie 和闲管家凭证")
            else:
                last = last_lines[-1] if last_lines else "(空)"
                # 去掉 ANSI 颜色
                import re
                clean = re.sub(r"\033\[[0-9;]*m", "", last)
                ok(f"presales 最后日志: {clean[:80]}")
        except Exception:
            pass
    else:
        warn("presales 日志不存在", "presales 模块可能从未启动")

    # 4h. 人工模式数据库
    mm_db = Path("data/manual_mode.db")
    if mm_db.exists():
        try:
            conn = sqlite3.connect(str(mm_db))
            count = conn.execute(
                "SELECT COUNT(*) FROM message_manual_mode WHERE enabled = 1"
            ).fetchone()[0]
            conn.close()
            if count > 0:
                warn(f"人工模式: {count} 个会话处于人工模式",
                     "这些会话不会自动回复，可在 Dashboard → 消息中心 → 人工模式中关闭")
            else:
                ok("人工模式: 无活跃的人工会话")
        except Exception as e:
            warn(f"人工模式数据库读取失败: {e}")
    else:
        ok("人工模式数据库: 尚未创建（首次运行时自动创建）")


# ══════════════════════════════════════════════════════════
#  汇总
# ══════════════════════════════════════════════════════════
def summary():
    section("诊断结果汇总")
    total = passed_count + failed_count + warn_count
    print(f"  总计 {total} 项检查:")
    print(f"    {GREEN}✓ 通过: {passed_count}{NC}")
    print(f"    {RED}✗ 失败: {failed_count}{NC}")
    print(f"    {YELLOW}! 警告: {warn_count}{NC}")
    print()

    if failed_count == 0:
        print(f"  {GREEN}{BOLD}🎉 所有关键检查通过！{NC}")
    else:
        print(f"  {RED}{BOLD}⚠️  有 {failed_count} 项关键问题需要修复{NC}")
        print(f"  请按上方 {YELLOW}→{NC} 提示逐一解决")
    print()


def main():
    print()
    print(f"{BOLD}{'=' * 50}{NC}")
    print(f"{BOLD}  闲鱼管家 — 新设备部署诊断{NC}")
    print(f"{BOLD}  {time.strftime('%Y-%m-%d %H:%M:%S')}{NC}")
    print(f"{BOLD}  cwd: {os.getcwd()}{NC}")
    print(f"{BOLD}{'=' * 50}{NC}")

    check_environment()
    check_api_timeout()
    check_reply_templates()
    check_playwright()
    check_auto_reply()
    summary()


if __name__ == "__main__":
    main()
