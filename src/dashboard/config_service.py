"""Configuration CRUD service — system_config.json management."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_SYS_CONFIG_FILE = Path(__file__).resolve().parents[2] / "data" / "system_config.json"

_OLD_SYS_CONFIG_FILE = Path(__file__).resolve().parents[2] / "server" / "data" / "system_config.json"


def _migrate_config_if_needed() -> None:
    """One-time migration: move system_config.json from server/data/ to data/."""
    if _OLD_SYS_CONFIG_FILE.exists() and not _SYS_CONFIG_FILE.exists():
        import shutil
        _SYS_CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(_OLD_SYS_CONFIG_FILE), str(_SYS_CONFIG_FILE))
        logger.info("Migrated system_config.json from server/data/ to data/")


_migrate_config_if_needed()

_ALLOWED_CONFIG_SECTIONS = {
    "xianguanjia",
    "ai",
    "oss",
    "auto_reply",
    "auto_publish",
    "order_reminder",
    "pricing",
    "delivery",
    "notifications",
    "store",
    "auto_price_modify",
    "cookie_cloud",
    "slider_auto_solve",
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
    tmp.replace(_SYS_CONFIG_FILE)


SHIPPING_REGIONS: dict[int, Any] = {
    330000: {
        "name": "浙江省",
        "cities": {
            330100: {
                "name": "杭州市",
                "districts": {
                    330102: "上城区",
                    330105: "拱墅区",
                    330106: "西湖区",
                    330108: "滨江区",
                    330109: "萧山区",
                    330110: "余杭区",
                    330111: "富阳区",
                    330112: "临安区",
                    330113: "临平区",
                    330114: "钱塘区",
                },
            },
            330200: {
                "name": "宁波市",
                "districts": {
                    330203: "海曙区",
                    330205: "江北区",
                    330206: "北仑区",
                    330211: "镇海区",
                    330212: "鄞州区",
                },
            },
            330300: {
                "name": "温州市",
                "districts": {
                    330302: "鹿城区",
                    330303: "龙湾区",
                    330304: "瓯海区",
                },
            },
            330400: {
                "name": "嘉兴市",
                "districts": {
                    330402: "南湖区",
                    330411: "秀洲区",
                },
            },
            330600: {
                "name": "绍兴市",
                "districts": {
                    330602: "越城区",
                    330603: "柯桥区",
                    330604: "上虞区",
                },
            },
        },
    },
    310000: {
        "name": "上海市",
        "cities": {
            310100: {
                "name": "上海市",
                "districts": {
                    310101: "黄浦区",
                    310104: "徐汇区",
                    310105: "长宁区",
                    310106: "静安区",
                    310107: "普陀区",
                    310109: "虹口区",
                    310110: "杨浦区",
                    310112: "闵行区",
                    310113: "宝山区",
                    310114: "嘉定区",
                    310115: "浦东新区",
                    310116: "金山区",
                    310117: "松江区",
                    310118: "青浦区",
                    310120: "奉贤区",
                    310151: "崇明区",
                },
            },
        },
    },
    110000: {
        "name": "北京市",
        "cities": {
            110100: {
                "name": "北京市",
                "districts": {
                    110101: "东城区",
                    110102: "西城区",
                    110105: "朝阳区",
                    110106: "丰台区",
                    110107: "石景山区",
                    110108: "海淀区",
                    110111: "房山区",
                    110112: "通州区",
                    110113: "顺义区",
                    110114: "昌平区",
                    110115: "大兴区",
                },
            },
        },
    },
    440000: {
        "name": "广东省",
        "cities": {
            440100: {
                "name": "广州市",
                "districts": {
                    440103: "荔湾区",
                    440104: "越秀区",
                    440105: "海珠区",
                    440106: "天河区",
                    440111: "白云区",
                    440112: "黄埔区",
                    440113: "番禺区",
                    440114: "花都区",
                    440115: "南沙区",
                },
            },
            440300: {
                "name": "深圳市",
                "districts": {
                    440303: "罗湖区",
                    440304: "福田区",
                    440305: "南山区",
                    440306: "宝安区",
                    440307: "龙岗区",
                    440308: "盐田区",
                    440309: "龙华区",
                    440310: "坪山区",
                    440311: "光明区",
                },
            },
            441900: {
                "name": "东莞市",
                "districts": {
                    441900003: "东城街道",
                    441900004: "南城街道",
                    441900005: "万江街道",
                    441900006: "莞城街道",
                },
            },
        },
    },
    320000: {
        "name": "江苏省",
        "cities": {
            320100: {
                "name": "南京市",
                "districts": {
                    320102: "玄武区",
                    320104: "秦淮区",
                    320105: "建邺区",
                    320106: "鼓楼区",
                    320111: "浦口区",
                    320113: "栖霞区",
                    320114: "雨花台区",
                    320115: "江宁区",
                },
            },
            320500: {
                "name": "苏州市",
                "districts": {
                    320505: "虎丘区",
                    320506: "吴中区",
                    320507: "相城区",
                    320508: "姑苏区",
                    320509: "吴江区",
                    320571: "苏州工业园区",
                },
            },
            320200: {
                "name": "无锡市",
                "districts": {
                    320205: "锡山区",
                    320206: "惠山区",
                    320211: "滨湖区",
                    320213: "梁溪区",
                    320214: "新吴区",
                },
            },
        },
    },
}

CONFIG_SECTIONS: list[dict[str, Any]] = [
    {
        "key": "xianguanjia",
        "name": "闲管家配置",
        "fields": [
            {
                "key": "mode",
                "label": "接入模式",
                "type": "select",
                "options": ["self_developed", "business"],
                "default": "self_developed",
                "labels": {"self_developed": "自研应用", "business": "商务对接"},
                "hint": "自研应用：个人或自有 ERP 直连；商务对接：第三方代商家接入",
            },
            {
                "key": "app_key",
                "label": "AppKey",
                "type": "text",
                "required": True,
                "hint": "在闲管家开放平台创建应用后获取",
            },
            {
                "key": "app_secret",
                "label": "AppSecret",
                "type": "password",
                "required": True,
                "hint": "应用密钥，请妥善保管不要泄露",
            },
            {
                "key": "seller_id",
                "label": "商家 ID (Seller ID)",
                "type": "text",
                "required_when": {"mode": "business"},
                "hint": "商务对接模式下的商家标识，自研模式无需填写",
            },
            {
                "key": "base_url",
                "label": "API 网关",
                "type": "text",
                "default": "https://open.goofish.pro",
                "hint": "默认无需修改，仅在私有化部署时更改",
            },
            {
                "key": "default_item_biz_type",
                "label": "商品类型",
                "type": "select",
                "options": ["2", "0", "10", "16", "19", "24", "26", "35"],
                "default": "2",
                "labels": {
                    "2": "普通商品",
                    "0": "已验货",
                    "10": "验货宝",
                    "16": "品牌授权",
                    "19": "闲鱼严选",
                    "24": "闲鱼特卖",
                    "26": "品牌捡漏",
                    "35": "跨境商品",
                },
                "hint": "上架商品的业务类型，一般选「普通商品」",
            },
            {
                "key": "default_sp_biz_type",
                "label": "行业类型",
                "type": "select",
                "options": [
                    "99", "2", "1", "3", "9", "25", "24", "22",
                    "20", "17", "18", "21", "27", "28", "30",
                    "8", "16", "19", "29", "31", "33", "23",
                ],
                "default": "99",
                "labels": {
                    "1": "手机",
                    "2": "潮品",
                    "3": "家电",
                    "8": "乐器",
                    "9": "3C数码",
                    "16": "奢品",
                    "17": "母婴",
                    "18": "美妆个护",
                    "19": "文玩/珠宝",
                    "20": "游戏电玩",
                    "21": "家居",
                    "22": "虚拟游戏",
                    "23": "租号",
                    "24": "图书",
                    "25": "卡券",
                    "27": "食品",
                    "28": "潮玩",
                    "29": "二手车",
                    "30": "宠植",
                    "31": "工艺礼品",
                    "33": "汽车服务",
                    "99": "其他",
                },
                "hint": "商品所属行业，影响可选类目范围",
            },
            {
                "key": "default_channel_cat_id",
                "label": "闲鱼类目ID",
                "type": "category_picker",
                "required": True,
                "hint": "点击「查询类目」根据商品类型和行业自动获取可选类目",
            },
            {
                "key": "default_stuff_status",
                "label": "成色",
                "type": "select",
                "options": ["100", "-1", "99", "95", "90", "80", "70", "60", "50", "40", "30", "20", "10", "0"],
                "default": "100",
                "labels": {
                    "100": "全新",
                    "-1": "准新",
                    "99": "99新",
                    "95": "95新",
                    "90": "9新",
                    "80": "8新",
                    "70": "7新",
                    "60": "6新",
                    "50": "5新及以下",
                    "40": "未使用·中度瑕疵",
                    "30": "未使用·轻微瑕疵",
                    "20": "未使用·仅拆封",
                    "10": "未使用·准新",
                    "0": "无成色",
                },
                "hint": "商品成色，普通商品可选全新/准新/X新，品牌捡漏有更多选项",
            },
            {"key": "default_price", "label": "默认价格(元)", "type": "number", "default": 1, "hint": "队列无单独定价时使用此价格，单位元（如 9.9）"},
            {"key": "default_express_fee", "label": "默认运费(元)", "type": "number", "default": 0, "hint": "0 表示包邮，单位元（如 8 表示运费8元）"},
            {"key": "default_stock", "label": "默认库存", "type": "number", "default": 1},
            {
                "key": "shipping_region",
                "label": "发货地区",
                "type": "region_cascader",
                "keys": ["default_province", "default_city", "default_district"],
                "regions": SHIPPING_REGIONS,
                "hint": "选择发货所在的省/市/区",
            },
            {"key": "service_support", "label": "商品服务", "type": "text", "hint": "可选。如需标记七天无理由退货(SDR)等服务承诺，填入对应编码"},
            {"key": "outer_id", "label": "商家编码", "type": "text", "hint": "可选。自定义编码用于与你的 ERP 系统关联商品，最长 64 字符"},
            {
                "key": "product_callback_url",
                "label": "商品回调地址",
                "type": "text",
                "hint": "填入闲管家开放平台后台，用于接收上架结果通知",
            },
        ],
    },
    {
        "key": "ai",
        "name": "AI 配置",
        "fields": [
            {
                "key": "provider",
                "label": "提供商",
                "type": "select",
                "options": ["qwen", "deepseek", "openai"],
                "default": "qwen",
                "labels": {"qwen": "百炼千问 (Qwen)", "deepseek": "DeepSeek", "openai": "OpenAI"},
            },
            {"key": "api_key", "label": "API Key", "type": "text", "required": True},
            {
                "key": "model",
                "label": "模型",
                "type": "combobox",
                "default": "qwen-plus-latest",
                "options": [
                    "qwen-plus-latest",
                    "qwen-max-latest",
                    "qwen-turbo-latest",
                    "qwen-flash",
                    "qwen3-max",
                    "qwen3.5-plus",
                    "qwq-plus-latest",
                ],
            },
            {
                "key": "base_url",
                "label": "API 地址",
                "type": "text",
                "placeholder": "https://dashscope.aliyuncs.com/compatible-mode/v1",
            },
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
            {
                "key": "enabled",
                "label": "启用",
                "type": "toggle",
                "default": True,
                "hint": "关闭后系统不再自动回复买家消息",
            },
            {
                "key": "ai_intent_enabled",
                "label": "AI意图识别",
                "type": "toggle",
                "default": False,
                "hint": "使用 AI 分析买家消息意图后生成针对性回复",
            },
            {
                "key": "default_reply",
                "label": "默认回复",
                "type": "textarea",
                "hint": "所有规则均未匹配时的通用兜底回复",
            },
            {
                "key": "virtual_default_reply",
                "label": "虚拟商品默认回复",
                "type": "textarea",
                "hint": "虚拟商品（兑换码/卡密）场景的默认回复",
            },
            {
                "key": "quote_missing_template",
                "label": "报价引导话术",
                "type": "textarea",
                "default": "为了给你报最准确的价格，麻烦提供一下：{fields}\n格式示例：广东省 - 浙江省 - 3kg 30x20x15cm",
                "hint": "买家信息不完整时的引导回复，{fields} 自动替换为缺失信息",
            },
            {
                "key": "strict_format_reply_enabled",
                "label": "严格格式引导",
                "type": "toggle",
                "default": True,
                "hint": "开启后非报价消息也会引导买家按标准格式提供信息",
            },
            {
                "key": "force_non_empty_reply",
                "label": "强制非空回复",
                "type": "toggle",
                "default": True,
                "hint": "避免发送空内容，无匹配时使用兜底话术",
            },
            {
                "key": "non_empty_reply_fallback",
                "label": "兜底话术",
                "type": "textarea",
                "hint": "所有规则均未匹配且 AI 无返回时的最后兜底回复",
            },
            {
                "key": "quote_failed_template",
                "label": "报价失败话术",
                "type": "textarea",
                "default": "报价服务暂时繁忙，我先帮您转人工确认，确保价格准确。",
                "hint": "报价服务异常时的降级回复",
            },
            {
                "key": "quote_reply_max_couriers",
                "label": "报价最多展示快递数",
                "type": "number",
                "default": 10,
                "hint": "报价回复中最多展示多少家快递公司",
            },
            {
                "key": "keyword_replies_text",
                "label": "关键词快捷回复",
                "type": "textarea",
                "hint": "每行一条：关键词=回复内容",
            },
            {
                "key": "first_reply_delay",
                "label": "首次响应延迟（秒）",
                "type": "text",
                "default": "0.25-0.9",
                "hint": "收到消息后首次回复的随机延迟范围，格式：最小-最大（秒）",
            },
            {
                "key": "inter_reply_delay",
                "label": "多段回复间隔（秒）",
                "type": "text",
                "default": "0.4-1.2",
                "hint": "多段回复之间的随机间隔范围，格式：最小-最大（秒）",
            },
            {
                "key": "simulate_human_typing",
                "label": "模拟人工打字节奏",
                "type": "toggle",
                "default": False,
                "hint": "开启后回复前按文字长度模拟打字延迟，降低风控风险",
            },
            {
                "key": "typing_speed_range",
                "label": "打字速度（秒/字）",
                "type": "text",
                "default": "0.05-0.15",
                "hint": "每个字符的打字延迟范围，格式：最小-最大（秒）",
            },
            {
                "key": "typing_max_delay",
                "label": "打字延迟上限（秒）",
                "type": "number",
                "default": 8,
                "hint": "单次回复的最大模拟打字延迟",
            },
        ],
    },
    {
        "key": "auto_publish",
        "name": "自动上架",
        "fields": [
            {
                "key": "enabled",
                "label": "启用",
                "type": "toggle",
                "default": False,
                "hint": "开启后系统按策略自动上架新商品",
            },
            {
                "key": "default_category",
                "label": "默认品类",
                "type": "select",
                "options": ["express", "recharge", "exchange", "account", "movie_ticket", "game"],
                "default": "exchange",
                "hint": "新上架商品的默认品类归属",
            },
            {
                "key": "auto_compliance",
                "label": "自动合规检查",
                "type": "toggle",
                "default": True,
                "hint": "上架前自动检测违规关键词和敏感内容",
            },
            {
                "key": "cold_start_days",
                "label": "冷启动天数",
                "type": "number",
                "default": 2,
                "hint": "新店前 N 天为冷启动期，每天批量上架新链接",
            },
            {
                "key": "cold_start_daily_count",
                "label": "每日新建链接数",
                "type": "number",
                "default": 5,
                "hint": "冷启动期每天自动上架的链接数量",
            },
            {
                "key": "steady_replace_count",
                "label": "每日替换链接数",
                "type": "number",
                "default": 1,
                "hint": "稳定期每天替换流量最差的链接数量",
            },
            {
                "key": "max_active_listings",
                "label": "最大活跃链接数",
                "type": "number",
                "default": 10,
                "hint": "店铺同时存在的最大商品链接数上限",
            },
            {
                "key": "steady_replace_metric",
                "label": "替换依据",
                "type": "select",
                "options": ["views", "sales"],
                "default": "views",
                "hint": "按什么指标判断需要替换的最差链接（浏览量/销量）",
            },
        ],
    },
    {
        "key": "order_reminder",
        "name": "催单设置",
        "fields": [
            {"key": "enabled", "label": "启用催单", "type": "toggle", "default": True},
            {
                "key": "max_daily",
                "label": "每日最大次数",
                "type": "number",
                "default": 2,
                "hint": "单个买家每日最多收到几次催单",
            },
            {
                "key": "min_interval_hours",
                "label": "最小间隔(小时)",
                "type": "number",
                "default": 4,
                "hint": "两次催单之间至少间隔的小时数",
            },
            {
                "key": "silent_start",
                "label": "静默开始(时)",
                "type": "number",
                "default": 22,
                "hint": "静默时段内不发送催单",
            },
            {"key": "silent_end", "label": "静默结束(时)", "type": "number", "default": 8},
            {
                "key": "templates",
                "label": "催单话术模板",
                "type": "textarea",
                "default": "您好，您的订单还没有完成支付哦~ 如有疑问可以随时问我，确认需要的话请尽快支付，我好给您安排发货。\n---\n提醒一下，您有一笔待支付订单，商品已为您预留，请在规定时间内完成支付，以免影响发货哦~\n---\n最后提醒：您的订单即将超时关闭，如果还需要请尽快支付。若已不需要请忽略此消息。",
                "hint": "每条话术用 --- 分隔，按催单次数依次发送",
            },
            {
                "key": "auto_remind_enabled",
                "label": "自动催单",
                "type": "toggle",
                "default": False,
                "hint": "开启后系统自动对待付款订单发送催单消息，无需手动点击",
            },
            {
                "key": "auto_remind_delay_minutes",
                "label": "自动催单延迟(分钟)",
                "type": "number",
                "default": 5,
                "hint": "下单后等待多少分钟未付款才开始自动催单",
            },
        ],
    },
    {
        "key": "pricing",
        "name": "定价规则",
        "fields": [
            {
                "key": "auto_adjust",
                "label": "自动调价",
                "type": "toggle",
                "default": False,
                "hint": "开启后系统根据市场行情和库存自动调整价格",
            },
            {
                "key": "min_margin_percent",
                "label": "最低利润率(%)",
                "type": "number",
                "default": 10,
                "hint": "低于此利润率的价格不会被采用",
            },
            {
                "key": "max_discount_percent",
                "label": "最大降价幅度(%)",
                "type": "number",
                "default": 20,
                "hint": "单次调价不超过此幅度，防止价格波动过大",
            },
        ],
    },
    {
        "key": "delivery",
        "name": "发货规则",
        "fields": [
            {
                "key": "auto_delivery",
                "label": "自动发货",
                "type": "toggle",
                "default": True,
                "hint": "开启后，订单支付成功自动触发闲管家发货",
            },
            {
                "key": "delivery_timeout_minutes",
                "label": "发货超时(分钟)",
                "type": "number",
                "default": 30,
                "hint": "超过设定时长未发货将触发告警通知（需配置告警 Webhook）",
            },
            {
                "key": "notify_on_delivery",
                "label": "发货通知",
                "type": "toggle",
                "default": True,
                "hint": "（规划中）发货成功后通知买家，需配合闲管家消息通道",
            },
        ],
    },
    {
        "key": "auto_price_modify",
        "name": "自动改价",
        "fields": [
            {
                "key": "enabled",
                "label": "启用",
                "type": "toggle",
                "default": False,
                "hint": "买家下单未付款时，自动匹配聊天中的报价并修改订单价格",
            },
            {
                "key": "max_quote_age_seconds",
                "label": "报价有效期(秒)",
                "type": "number",
                "default": 7200,
                "hint": "超过此时间的报价不再用于自动改价",
            },
            {
                "key": "fallback_action",
                "label": "无匹配报价时",
                "type": "select",
                "options": ["skip", "use_listing_price"],
                "default": "skip",
                "labels": {"skip": "跳过不改价", "use_listing_price": "使用上架价格"},
                "hint": "找不到聊天报价时的处理策略",
            },
            {
                "key": "default_express_fee",
                "label": "默认运费(元)",
                "type": "number",
                "default": 0,
                "hint": "改价时的运费，0 表示包邮，单位元",
            },
            {
                "key": "poll_interval_seconds",
                "label": "轮询间隔(秒)",
                "type": "number",
                "default": 45,
                "hint": "每隔多少秒查询一次待付款订单，推荐 30-60 秒",
            },
            {
                "key": "notify_on_modify",
                "label": "改价通知",
                "type": "toggle",
                "default": True,
                "hint": "改价成功后发送通知",
            },
        ],
    },
    {
        "key": "notifications",
        "name": "告警通知",
        "fields": [
            {"key": "feishu_enabled", "label": "飞书通知", "type": "toggle", "default": False},
            {
                "key": "feishu_webhook",
                "label": "飞书 Webhook URL",
                "type": "password",
                "placeholder": "https://open.feishu.cn/open-apis/bot/v2/hook/xxx",
            },
            {"key": "wechat_enabled", "label": "企业微信通知", "type": "toggle", "default": False},
            {
                "key": "wechat_webhook",
                "label": "企业微信 Webhook URL",
                "type": "password",
                "placeholder": "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=xxx",
            },
            {"key": "notify_cookie_expire", "label": "Cookie 过期告警", "type": "toggle", "default": True},
            {"key": "notify_cookie_refresh", "label": "Cookie 刷新成功通知", "type": "toggle", "default": True},
            {"key": "notify_sla_alert", "label": "SLA 异常告警", "type": "toggle", "default": True},
            {"key": "notify_order_fail", "label": "订单异常告警", "type": "toggle", "default": True},
            {"key": "notify_after_sales", "label": "售后介入告警", "type": "toggle", "default": True},
            {"key": "notify_ship_fail", "label": "发货失败告警", "type": "toggle", "default": True},
            {"key": "notify_manual_takeover", "label": "人工接管告警", "type": "toggle", "default": True},
            {"key": "notify_risk_control", "label": "风控滑块告警 (RGV587)", "type": "toggle", "default": True},
        ],
    },
    {
        "key": "cookie_cloud",
        "name": "CookieCloud 配置（可选）",
        "fields": [
            {
                "key": "cookie_cloud_host",
                "label": "CookieCloud 服务地址",
                "type": "text",
                "default": "",
                "placeholder": "http://localhost:8091/cookie-cloud",
                "hint": "本系统已内置 CookieCloud 服务端，使用默认地址即可。留空时自动使用内置服务。",
            },
            {
                "key": "cookie_cloud_uuid",
                "label": "CookieCloud UUID",
                "type": "text",
                "default": "",
                "placeholder": "在浏览器 CookieCloud 扩展中生成",
                "hint": "打开扩展设置，点击「生成」按钮获取 UUID",
            },
            {
                "key": "cookie_cloud_password",
                "label": "CookieCloud 密码",
                "type": "password",
                "default": "",
                "placeholder": "在浏览器 CookieCloud 扩展中生成",
                "hint": "扩展中对应的加密密码，用于端对端加密",
            },
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
