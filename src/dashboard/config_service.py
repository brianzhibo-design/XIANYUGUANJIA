"""Configuration CRUD service — system_config.json management."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_SYS_CONFIG_FILE = Path(__file__).resolve().parents[2] / "server" / "data" / "system_config.json"

_ALLOWED_CONFIG_SECTIONS = {
    "xianguanjia", "ai", "oss", "auto_reply", "auto_publish",
    "order_reminder", "pricing", "delivery", "notifications", "store",
}

_SENSITIVE_CONFIG_KEYS = ["app_secret", "api_key", "access_key_secret", "mch_secret", "webhook"]


def read_system_config() -> dict[str, Any]:
    try:
        if _SYS_CONFIG_FILE.exists():
            return json.loads(_SYS_CONFIG_FILE.read_text(encoding="utf-8"))
    except Exception as e:
        logger.error("Failed to read system config: %s", e)
    return {}


def write_system_config(data: dict[str, Any]) -> None:
    _SYS_CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp = _SYS_CONFIG_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.rename(_SYS_CONFIG_FILE)


CONFIG_SECTIONS: list[dict[str, Any]] = [
    {
        "key": "xianguanjia",
        "name": "闲管家配置",
        "fields": [
            {"key": "mode", "label": "接入模式", "type": "select", "options": ["self_developed", "business"], "default": "self_developed", "labels": {"self_developed": "自研应用", "business": "商务对接"}, "hint": "自研应用：个人或自有 ERP 直连；商务对接：第三方代商家接入"},
            {"key": "app_key", "label": "AppKey", "type": "text", "required": True, "hint": "在闲管家开放平台创建应用后获取"},
            {"key": "app_secret", "label": "AppSecret", "type": "password", "required": True, "hint": "应用密钥，请妥善保管不要泄露"},
            {"key": "seller_id", "label": "商家 ID (Seller ID)", "type": "text", "required_when": {"mode": "business"}, "hint": "商务对接模式下的商家标识，自研模式无需填写"},
            {"key": "base_url", "label": "API 网关", "type": "text", "default": "https://open.goofish.pro", "hint": "默认无需修改，仅在私有化部署时更改"},
        ],
    },
    {
        "key": "ai",
        "name": "AI 配置",
        "fields": [
            {"key": "provider", "label": "提供商", "type": "select", "options": ["qwen", "deepseek", "openai"], "default": "qwen", "labels": {"qwen": "百炼千问 (Qwen)", "deepseek": "DeepSeek", "openai": "OpenAI"}},
            {"key": "api_key", "label": "API Key", "type": "text", "required": True},
            {"key": "model", "label": "模型", "type": "combobox", "default": "qwen-plus-latest", "options": ["qwen-plus-latest", "qwen-max-latest", "qwen-turbo-latest", "qwen-flash", "qwen3-max", "qwen3.5-plus", "qwq-plus-latest"]},
            {"key": "base_url", "label": "API 地址", "type": "text", "placeholder": "https://dashscope.aliyuncs.com/compatible-mode/v1"},
        ],
    },
    {
        "key": "oss",
        "name": "阿里云 OSS",
        "fields": [
            {"key": "access_key_id", "label": "Access Key ID", "type": "text", "required": True},
            {"key": "access_key_secret", "label": "Access Key Secret", "type": "password", "required": True},
            {"key": "bucket", "label": "Bucket", "type": "text", "required": True},
            {"key": "endpoint", "label": "Endpoint", "type": "text", "required": True},
            {"key": "prefix", "label": "路径前缀", "type": "text", "default": "xianyu/listing/"},
            {"key": "custom_domain", "label": "自定义域名", "type": "text"},
        ],
    },
    {
        "key": "auto_reply",
        "name": "自动回复",
        "fields": [
            {"key": "enabled", "label": "启用", "type": "toggle", "default": True},
            {"key": "ai_intent_enabled", "label": "AI意图识别", "type": "toggle", "default": False},
            {"key": "default_reply", "label": "默认回复", "type": "textarea"},
            {"key": "virtual_default_reply", "label": "虚拟商品默认回复", "type": "textarea"},
        ],
    },
    {
        "key": "auto_publish",
        "name": "自动上架",
        "fields": [
            {"key": "enabled", "label": "启用", "type": "toggle", "default": False, "hint": "开启后系统按策略自动上架新商品"},
            {"key": "default_category", "label": "默认品类", "type": "select", "options": ["express", "recharge", "exchange", "account", "movie_ticket", "game"], "default": "exchange", "hint": "新上架商品的默认品类归属"},
            {"key": "auto_compliance", "label": "自动合规检查", "type": "toggle", "default": True, "hint": "上架前自动检测违规关键词和敏感内容"},
        ],
    },
    {
        "key": "order_reminder",
        "name": "催单设置",
        "fields": [
            {"key": "enabled", "label": "启用催单", "type": "toggle", "default": True},
            {"key": "max_daily", "label": "每日最大次数", "type": "number", "default": 2, "hint": "单个买家每日最多收到几次催单"},
            {"key": "min_interval_hours", "label": "最小间隔(小时)", "type": "number", "default": 4, "hint": "两次催单之间至少间隔的小时数"},
            {"key": "silent_start", "label": "静默开始(时)", "type": "number", "default": 22, "hint": "静默时段内不发送催单"},
            {"key": "silent_end", "label": "静默结束(时)", "type": "number", "default": 8},
            {"key": "templates", "label": "催单话术模板", "type": "textarea", "default": "您好，您的订单还没有完成支付哦~ 如有疑问可以随时问我，确认需要的话请尽快支付，我好给您安排发货。\n---\n提醒一下，您有一笔待支付订单，商品已为您预留，请在规定时间内完成支付，以免影响发货哦~\n---\n最后提醒：您的订单即将超时关闭，如果还需要请尽快支付。若已不需要请忽略此消息。", "hint": "每条话术用 --- 分隔，按催单次数依次发送"},
        ],
    },
    {
        "key": "pricing",
        "name": "定价规则",
        "fields": [
            {"key": "auto_adjust", "label": "自动调价", "type": "toggle", "default": False, "hint": "开启后系统根据市场行情和库存自动调整价格"},
            {"key": "min_margin_percent", "label": "最低利润率(%)", "type": "number", "default": 10, "hint": "低于此利润率的价格不会被采用"},
            {"key": "max_discount_percent", "label": "最大降价幅度(%)", "type": "number", "default": 20, "hint": "单次调价不超过此幅度，防止价格波动过大"},
        ],
    },
    {
        "key": "delivery",
        "name": "发货规则",
        "fields": [
            {"key": "auto_delivery", "label": "自动发货", "type": "toggle", "default": True, "hint": "开启后，订单支付成功自动触发闲管家发货"},
            {"key": "delivery_timeout_minutes", "label": "发货超时(分钟)", "type": "number", "default": 30, "hint": "超过设定时长未发货将触发告警通知"},
            {"key": "notify_on_delivery", "label": "发货通知", "type": "toggle", "default": True, "hint": "发货成功后通知买家"},
        ],
    },
    {
        "key": "notifications",
        "name": "告警通知",
        "fields": [
            {"key": "feishu_enabled", "label": "飞书通知", "type": "toggle", "default": False},
            {"key": "feishu_webhook", "label": "飞书 Webhook URL", "type": "password", "placeholder": "https://open.feishu.cn/open-apis/bot/v2/hook/xxx"},
            {"key": "wechat_enabled", "label": "企业微信通知", "type": "toggle", "default": False},
            {"key": "wechat_webhook", "label": "企业微信 Webhook URL", "type": "password", "placeholder": "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=xxx"},
            {"key": "notify_cookie_expire", "label": "Cookie 过期告警", "type": "toggle", "default": True},
            {"key": "notify_cookie_refresh", "label": "Cookie 刷新成功通知", "type": "toggle", "default": True},
            {"key": "notify_sla_alert", "label": "SLA 异常告警", "type": "toggle", "default": True},
            {"key": "notify_order_fail", "label": "订单异常告警", "type": "toggle", "default": True},
            {"key": "notify_after_sales", "label": "售后介入告警", "type": "toggle", "default": True},
            {"key": "notify_ship_fail", "label": "发货失败告警", "type": "toggle", "default": True},
            {"key": "notify_manual_takeover", "label": "人工接管告警", "type": "toggle", "default": True},
        ],
    },
]


def mask_sensitive(config: dict[str, Any]) -> dict[str, Any]:
    """Return a copy of config with sensitive values masked."""
    masked = {}
    for section_key, section_val in config.items():
        if isinstance(section_val, dict):
            masked[section_key] = {}
            for k, v in section_val.items():
                if any(sk in k for sk in _SENSITIVE_CONFIG_KEYS) and v:
                    masked[section_key][k] = str(v)[:4] + "****"
                else:
                    masked[section_key][k] = v
        else:
            masked[section_key] = section_val
    return masked


def update_config(updates: dict[str, Any]) -> dict[str, Any]:
    """Merge updates into system config, return updated config."""
    current = read_system_config()
    for section, values in updates.items():
        if section not in _ALLOWED_CONFIG_SECTIONS:
            continue
        if not isinstance(values, dict):
            current[section] = values
            continue
        if section not in current:
            current[section] = {}
        for k, v in values.items():
            if any(sk in k for sk in _SENSITIVE_CONFIG_KEYS) and isinstance(v, str) and v.endswith("****"):
                continue
            current[section][k] = v
    write_system_config(current)
    return current
