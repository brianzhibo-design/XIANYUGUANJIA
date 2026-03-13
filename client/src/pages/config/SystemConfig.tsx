import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { getSystemConfig, getConfigSections, saveSystemConfig } from '../../api/config';
/* Brand asset imports removed — managed in AutoPublish.tsx */
import { api } from '../../api/index';
import { useStoreCategory, CATEGORY_META } from '../../contexts/StoreCategoryContext';
import toast from 'react-hot-toast';
import {
  Settings, Save, RefreshCw, Send, Bell, CheckCircle2, XCircle,
  ExternalLink, Info, Plug, ChevronDown, ChevronUp, FileText, Zap,
  DollarSign, Store, X, ArrowRight, Trash2,
  Receipt, Package, TrendingUp, MessageSquare, Eye, Shield,
} from 'lucide-react';

interface CategoryDefaults {
  auto_reply: {
    default_reply: string;
    virtual_default_reply: string;
    ai_intent_enabled: boolean;
    enabled: boolean;
  };
  pricing: {
    auto_adjust: boolean;
    min_margin_percent: number;
    max_discount_percent: number;
  };
  delivery: {
    auto_delivery: boolean;
    delivery_timeout_minutes: number;
  };
  summary: string[];
}

const GENERIC_DEFAULTS: CategoryDefaults = {
  auto_reply: {
    default_reply: '您好！感谢您的咨询。请问有什么可以帮您的吗？',
    virtual_default_reply: '您好！本商品为虚拟商品，购买后自动发送。如有问题请联系客服。',
    ai_intent_enabled: true,
    enabled: true,
  },
  pricing: { auto_adjust: true, min_margin_percent: 10, max_discount_percent: 20 },
  delivery: { auto_delivery: true, delivery_timeout_minutes: 30 },
  summary: ['自动回复 → 通用话术', '定价 → 均衡方案', '发货 → 自动发货'],
};

const CATEGORY_DEFAULTS: Record<string, CategoryDefaults> = {
  express: {
    auto_reply: {
      default_reply: '直接拍就行拍完给您兑换码',
      virtual_default_reply: '兑换码是兑换余额的，点下单使用余额支付即可',
      ai_intent_enabled: true,
      enabled: true,
    },
    pricing: { auto_adjust: false, min_margin_percent: 15, max_discount_percent: 15 },
    delivery: { auto_delivery: false, delivery_timeout_minutes: 60 },
    summary: ['自动回复 → 快递兑换码业务话术', '定价 → 保守方案（利润率 15%）', '发货 → 手动发货（需填快递单号）'],
  },
  exchange: {
    auto_reply: {
      default_reply: '您好！本商品为兑换码/卡密，购买后系统自动发送到聊天窗口。\n如遇兑换问题请联系客服，我们会第一时间协助处理。',
      virtual_default_reply: '【自动发货】您的兑换码已发送，请查收聊天消息。\n使用方法：复制兑换码 → 打开对应平台 → 兑换/充值\n如有问题请随时联系我们。',
      ai_intent_enabled: true,
      enabled: true,
    },
    pricing: { auto_adjust: true, min_margin_percent: 5, max_discount_percent: 10 },
    delivery: { auto_delivery: true, delivery_timeout_minutes: 5 },
    summary: ['自动回复 → 兑换码/卡密专用话术', '定价 → 激进方案（利润率 5%）', '发货 → 自动发码（付款后 5 秒）'],
  },
  recharge: {
    ...GENERIC_DEFAULTS,
    auto_reply: {
      default_reply: '您好！支持三网话费/流量充值，下单时请留下手机号，充值后到账通知您。',
      virtual_default_reply: '您的充值已提交处理，预计几分钟内到账。如有问题请联系客服。',
      ai_intent_enabled: true,
      enabled: true,
    },
    summary: ['自动回复 → 充值代充话术', '定价 → 均衡方案', '发货 → 自动发货'],
  },
  movie_ticket: {
    ...GENERIC_DEFAULTS,
    auto_reply: {
      default_reply: '您好！支持全国影院电影票代购，请告诉我影片、影院和场次，我帮您查询低价票。',
      virtual_default_reply: '您的电影票已出票，请查收聊天消息中的取票码。',
      ai_intent_enabled: true,
      enabled: true,
    },
    summary: ['自动回复 → 电影票代购话术', '定价 → 均衡方案', '发货 → 自动发货'],
  },
  account: {
    ...GENERIC_DEFAULTS,
    auto_reply: {
      default_reply: '您好！本店出售优质账号，支持验号。下单前请先咨询确认账号详情。',
      virtual_default_reply: '账号信息已发送到聊天窗口，请及时修改密码和绑定信息。',
      ai_intent_enabled: true,
      enabled: true,
    },
    delivery: { auto_delivery: false, delivery_timeout_minutes: 30 },
    summary: ['自动回复 → 账号交易话术', '定价 → 均衡方案', '发货 → 手动发货（需验号）'],
  },
  game: {
    ...GENERIC_DEFAULTS,
    auto_reply: {
      default_reply: '您好！支持多款游戏道具/点券代购，请告诉我游戏名称、区服和需求，我帮您报价。',
      virtual_default_reply: '您的游戏道具已处理完成，请登录游戏查收。如有问题请联系客服。',
      ai_intent_enabled: true,
      enabled: true,
    },
    summary: ['自动回复 → 游戏道具话术', '定价 → 均衡方案', '发货 → 自动发货'],
  },
};

const PRICING_PRESETS = {
  conservative: { label: '保守定价', desc: '高利润率，低降价幅度', min_margin_percent: 20, max_discount_percent: 10, auto_adjust: false },
  balanced: { label: '均衡定价', desc: '平衡利润与销量', min_margin_percent: 10, max_discount_percent: 20, auto_adjust: true },
  aggressive: { label: '激进定价', desc: '低利润率，高降价幅度，追求销量', min_margin_percent: 5, max_discount_percent: 35, auto_adjust: true },
};

const SECTION_GUIDES: Record<string, string> = {
  xianguanjia: '闲管家是连接闲鱼平台的核心网关，提供订单管理、消息推送、商品操作等 API。配置后系统可自动处理订单和消息。',
  ai: 'AI 提供商负责智能回复、意图识别等功能。选择合适的模型并填入 API Key 即可启用。推荐使用百炼千问（Qwen），中文电商场景最稳定。',
  oss: '阿里云 OSS 用于存储商品图片等静态资源。如果不需要图片自动上传功能，可跳过此配置。',
};

const AI_PROVIDER_GUIDES: Record<string, any> = {
  qwen: {
    name: '百炼千问 (Qwen)',
    baseUrl: 'https://dashscope.aliyuncs.com/compatible-mode/v1',
    model: 'qwen-plus-latest',
    applyUrl: 'https://bailian.console.aliyun.com/',
    tip: '推荐。兼容 OpenAI 接口，中文电商场景最稳定。支持联网搜索和多模态。',
    models: [
      { value: 'qwen-plus-latest', label: 'Qwen-Plus（推荐，性价比高）' },
      { value: 'qwen-max-latest', label: 'Qwen-Max（最强推理）' },
      { value: 'qwen-turbo-latest', label: 'Qwen-Turbo（最快速度）' },
      { value: 'qwen-flash', label: 'Qwen-Flash（极速低成本）' },
      { value: 'qwen3-max', label: 'Qwen3-Max（Qwen3 旗舰）' },
      { value: 'qwen3.5-plus', label: 'Qwen3.5-Plus（最新一代）' },
      { value: 'qwq-plus-latest', label: 'QwQ-Plus（深度思考）' },
      { value: 'qwen3-coder-plus', label: 'Qwen3-Coder-Plus（代码优化）' },
      { value: 'qwen3-235b-a22b', label: 'Qwen3-235B（开源免费）' },
      { value: 'qwen3-32b', label: 'Qwen3-32B（开源免费）' },
    ],
  },
  deepseek: {
    name: 'DeepSeek',
    baseUrl: 'https://api.deepseek.com/v1',
    model: 'deepseek-chat',
    applyUrl: 'https://platform.deepseek.com/',
    tip: '性价比高，长文本能力强，适合复杂商品描述场景。',
    models: [
      { value: 'deepseek-chat', label: 'DeepSeek-Chat（通用对话）' },
      { value: 'deepseek-reasoner', label: 'DeepSeek-Reasoner（深度推理）' },
    ],
  },
  openai: {
    name: 'OpenAI',
    baseUrl: 'https://api.openai.com/v1',
    model: 'gpt-4o-mini',
    applyUrl: 'https://platform.openai.com/',
    tip: '需海外网络，英文能力最强，中文电商场景建议搭配 System Prompt 优化。',
    models: [
      { value: 'gpt-4o-mini', label: 'GPT-4o Mini（经济实惠）' },
      { value: 'gpt-4o', label: 'GPT-4o（强力多模态）' },
      { value: 'gpt-4.1-mini', label: 'GPT-4.1 Mini（最新轻量）' },
      { value: 'gpt-4.1', label: 'GPT-4.1（最新旗舰）' },
    ],
  },
};

const TAB_GROUPS = [
  { group: '基础设置', tabs: [
    { key: 'store_category', name: '店铺品类', icon: Store },
    { key: 'integrations', name: '集成服务', icon: Plug },
  ]},
  { group: '业务规则', tabs: [
    { key: 'auto_reply', name: '自动回复', icon: FileText },
    { key: 'orders', name: '订单管理', icon: Receipt },
    { key: 'products', name: '商品运营', icon: Package },
  ]},
  { group: '系统', tabs: [
    { key: 'notifications', name: '告警通知', icon: Bell },
  ]},
];

const ALL_TABS = TAB_GROUPS.flatMap(g => g.tabs);

const TAB_COMPAT: Record<string, string> = {
  xianguanjia: 'integrations',
  ai: 'integrations',
  oss: 'integrations',
  cookie_cloud: 'integrations',
  auto_publish: 'products',
  order_reminder: 'orders',
  pricing: 'orders',
  delivery: 'orders',
  automation: 'orders',
};

const NOTIFICATION_EVENTS = [
  { key: 'notify_cookie_expire', label: 'Cookie 过期告警' },
  { key: 'notify_cookie_refresh', label: 'Cookie 刷新成功' },
  { key: 'notify_sla_alert', label: 'SLA 异常告警' },
  { key: 'notify_order_fail', label: '订单异常告警' },
  { key: 'notify_after_sales', label: '售后介入告警' },
  { key: 'notify_ship_fail', label: '发货失败告警' },
  { key: 'notify_manual_takeover', label: '人工接管告警' },
];

// ─── 对话流程模拟器 ─────────────────────────────────────
interface ChatMsg { role: 'buyer' | 'system'; text: string; rule?: string; }

const CONVERSATION_SCENARIOS: Record<string, { label: string; chats: ChatMsg[] }> = {
  express: {
    label: '快递代发（兑换码模式）',
    chats: [
      { role: 'buyer', text: '在吗' },
      { role: 'system', text: '在的，请问需要寄什么快递？请发送 寄件城市-收件城市-重量（kg），我帮你查最优价格。', rule: '在线咨询' },
      { role: 'buyer', text: '怎么买' },
      { role: 'system', text: '直接拍就行拍完给您兑换码', rule: '购买流程（仅快递）' },
      { role: 'buyer', text: '你是哪里到哪里的呢' },
      { role: 'system', text: '你是哪里到哪里的呢', rule: '路线咨询（仅快递）' },
      { role: 'buyer', text: '兑换码怎么用' },
      { role: 'system', text: '兑换码是兑换余额的，点下单使用余额支付即可', rule: '兑换码使用（仅快递）' },
      { role: 'buyer', text: '上门取件吗' },
      { role: 'system', text: '下单后联系快递员沟通好上门取件时间哈', rule: '取件安排（仅快递）' },
      { role: 'buyer', text: '有顺丰吗' },
      { role: 'system', text: '顺丰京东没有了哈', rule: '品牌缺货（仅快递）' },
      { role: 'buyer', text: '能便宜点吗' },
      { role: 'system', text: '价格已经尽量优惠，量大或长期合作可以再沟通方案。', rule: '讲价规则' },
      { role: 'buyer', text: '退款吧' },
      { role: 'system', text: '这边给你退款，直接转你可以吗？退款对链接不太好，方便吗？', rule: '退款话术（仅快递）' },
    ],
  },
  exchange: {
    label: '兑换码/卡密',
    chats: [
      { role: 'buyer', text: '在吗' },
      { role: 'system', text: '', rule: '通用回复模板' },
      { role: 'buyer', text: '兑换码怎么发' },
      { role: 'system', text: '这是虚拟商品，付款后会通过平台聊天发卡密/兑换信息，请按商品说明使用。', rule: '卡密发放规则' },
      { role: 'buyer', text: '怎么用' },
      { role: 'system', text: '下单后我会提供对应使用说明，遇到问题可随时留言，我会协助处理。', rule: '使用咨询规则' },
      { role: 'buyer', text: '多久发' },
      { role: 'system', text: '虚拟商品通常付款后几分钟内处理，高峰期会稍有延迟，我会尽快给你。', rule: '发货时间规则' },
    ],
  },
  recharge: {
    label: '充值代充',
    chats: [
      { role: 'buyer', text: '在吗' },
      { role: 'system', text: '', rule: '通用回复模板' },
      { role: 'buyer', text: '能充联通吗' },
      { role: 'system', text: '支持代下单服务，请把具体需求、数量和时效发我，我确认后马上安排。', rule: '代下单规则' },
      { role: 'buyer', text: '多久到账' },
      { role: 'system', text: '虚拟商品通常付款后几分钟内处理，高峰期会稍有延迟，我会尽快给你。', rule: '发货时间规则' },
      { role: 'buyer', text: '安全吗' },
      { role: 'system', text: '建议全程走闲鱼平台流程交易，按平台规则下单和确认，双方都更有保障。', rule: '平台安全规则' },
    ],
  },
  account: {
    label: '账号交易',
    chats: [
      { role: 'buyer', text: '在吗' },
      { role: 'system', text: '', rule: '通用回复模板' },
      { role: 'buyer', text: '账号能验吗' },
      { role: 'system', text: '', rule: '通用回复模板' },
      { role: 'buyer', text: '怎么用' },
      { role: 'system', text: '下单后我会提供对应使用说明，遇到问题可随时留言，我会协助处理。', rule: '使用咨询规则' },
      { role: 'buyer', text: '靠谱吗' },
      { role: 'system', text: '建议全程走闲鱼平台流程交易，按平台规则下单和确认，双方都更有保障。', rule: '平台安全规则' },
    ],
  },
  movie_ticket: {
    label: '电影票代购',
    chats: [
      { role: 'buyer', text: '有票吗' },
      { role: 'system', text: '', rule: '通用回复模板' },
      { role: 'buyer', text: '能代购吗' },
      { role: 'system', text: '支持代下单服务，请把具体需求、数量和时效发我，我确认后马上安排。', rule: '代下单规则' },
      { role: 'buyer', text: '多久出票' },
      { role: 'system', text: '虚拟商品通常付款后几分钟内处理，高峰期会稍有延迟，我会尽快给你。', rule: '发货时间规则' },
    ],
  },
  game: {
    label: '游戏道具',
    chats: [
      { role: 'buyer', text: '在吗' },
      { role: 'system', text: '', rule: '通用回复模板' },
      { role: 'buyer', text: '能代充吗' },
      { role: 'system', text: '支持代下单服务，请把具体需求、数量和时效发我，我确认后马上安排。', rule: '代下单规则' },
      { role: 'buyer', text: '怎么用' },
      { role: 'system', text: '下单后我会提供对应使用说明，遇到问题可随时留言，我会协助处理。', rule: '使用咨询规则' },
      { role: 'buyer', text: '能便宜点吗' },
      { role: 'system', text: '价格已经尽量优惠，量大或长期合作可以再沟通方案。', rule: '讲价规则' },
    ],
  },
};

function ConversationSimulator({ category, config }: { category: string; config: any }) {
  const scenario = CONVERSATION_SCENARIOS[category] || CONVERSATION_SCENARIOS.express;
  const defaultReply = config.auto_reply?.default_reply || '您好！感谢您的咨询。请问有什么可以帮您的吗？';
  const meta = CATEGORY_META[category];

  return (
    <div className="bg-gradient-to-b from-gray-50 to-white rounded-xl border border-xy-border overflow-hidden">
      <div className="px-4 py-2.5 bg-white border-b border-xy-border flex items-center justify-between">
        <h4 className="text-sm font-bold text-xy-text-primary flex items-center gap-2">
          <Eye className="w-4 h-4 text-xy-brand-500" /> 对话效果预览
        </h4>
        <span className="text-[11px] text-xy-text-muted bg-xy-gray-100 px-2 py-0.5 rounded-full">
          {meta?.icon} {scenario.label}品类
        </span>
      </div>
      <div className="p-4 space-y-3 max-h-[400px] overflow-y-auto" style={{ background: 'linear-gradient(180deg, #f5f5f5 0%, #ebebeb 100%)' }}>
        {scenario.chats.map((msg, i) => {
          const displayText = (msg.role === 'system' && msg.text === '') ? defaultReply : msg.text;
          const isLive = msg.role === 'system' && msg.text === '';
          return (
            <div key={i} className={`flex ${msg.role === 'buyer' ? 'justify-start' : 'justify-end'}`}>
              <div className={`max-w-[80%] ${msg.role === 'buyer' ? '' : 'text-right'}`}>
                {msg.rule && (
                  <p className={`text-[10px] mb-0.5 ${msg.role === 'buyer' ? 'text-left' : 'text-right'} text-gray-400`}>
                    {isLive ? '⚡ 来自：你的通用回复模板' : `🤖 ${msg.rule}`}
                  </p>
                )}
                <div className={`inline-block px-3 py-2 rounded-xl text-sm whitespace-pre-line leading-relaxed ${
                  msg.role === 'buyer'
                    ? 'bg-white text-gray-800 shadow-sm border border-gray-200 rounded-tl-sm'
                    : isLive
                      ? 'bg-xy-brand-500 text-white shadow-sm rounded-tr-sm ring-2 ring-xy-brand-200'
                      : 'bg-emerald-500 text-white shadow-sm rounded-tr-sm'
                }`}>
                  {displayText}
                </div>
                <p className={`text-[10px] mt-0.5 ${msg.role === 'buyer' ? 'text-left' : 'text-right'} text-gray-400`}>
                  {msg.role === 'buyer' ? '👤 买家' : '🤖 系统自动回复'}
                </p>
              </div>
            </div>
          );
        })}
      </div>
      <div className="px-4 py-2 bg-white border-t border-xy-border">
        <p className="text-[11px] text-gray-500">
          <span className="inline-block w-3 h-3 rounded bg-xy-brand-500 mr-1 align-middle" /> 橙色气泡 = 使用你配置的通用回复模板（可在下方修改）&nbsp;&nbsp;
          <span className="inline-block w-3 h-3 rounded bg-emerald-500 mr-1 align-middle" /> 绿色气泡 = 系统内置规则自动匹配
        </p>
      </div>
    </div>
  );
}

// ─── 内置规则表 ─────────────────────────────────────
type RulePhase = 'universal' | 'presale' | 'presale_human' | 'aftersale';
interface BuiltinRule { intent: string; keywords: string; reply: string; scope?: string; phase: RulePhase; needsHuman?: boolean }

const BUILTIN_RULES: BuiltinRule[] = [
  // 通用
  { phase: 'universal', intent: '平台安全', keywords: '靠谱吗、安全、担保、骗子、走平台', reply: '放心哦，全程走闲鱼平台交易，按平台规则下单确认，双方都有保障~' },
  { phase: 'universal', intent: '讲价', keywords: '最低、便宜、优惠、少点、能便宜', reply: '亲，这个价格已经很实惠了呢~ 量大的话可以再商量哦~' },
  // 快递售前 - 需人工
  { phase: 'presale_human', intent: '超偏远地区', keywords: '新疆、西藏', reply: '亲，新疆/西藏属于偏远地区续重会贵一些~ 方便告诉我包裹的长宽高吗？我帮您精确核算~', scope: '仅快递', needsHuman: true },
  { phase: 'presale_human', intent: '体积计费', keywords: '体积大、长宽高、棉被、懒人沙发', reply: '体积较大的物品会按体积重计费（长x宽x高/8000），方便告诉我具体长宽高吗？我帮您算~', scope: '仅快递', needsHuman: true },
  { phase: 'presale_human', intent: '大件/搬家', keywords: '搬家、毕业寄、大件', reply: '大件/搬家可以走德邦哦~ 我帮您确认一下具体方案~', scope: '仅快递', needsHuman: true },
  // 快递售前 - 自动回复
  { phase: 'presale', intent: '咨询在不在', keywords: '在吗、还在、有货吗', reply: '在的亲~ 您是从哪里寄到哪里呢？告诉我城市和重量帮您查最优价~', scope: '仅快递' },
  { phase: 'presale', intent: '购买流程', keywords: '怎么买、怎么拍、怎么下单', reply: '先拍下不付款，我帮您改价，付款后系统自动发兑换码给您~', scope: '仅快递' },
  { phase: 'presale', intent: '兑换码使用', keywords: '怎么用、怎么使用、兑换码', reply: '兑换码是兑换余额用的~ 下单时选择使用余额支付就好啦~', scope: '仅快递' },
  { phase: 'presale', intent: '代下单', keywords: '代下单、帮我下单', reply: '亲，我们不做代下单了~ 拍下付款后系统会发兑换码给您，用兑换码到小橙序下单就好~', scope: '仅快递' },
  { phase: 'presale', intent: '路线咨询', keywords: '哪里到哪里、寄到哪、从哪寄', reply: '亲，您是从哪里寄到哪里呢？告诉我城市和重量帮您查价~', scope: '仅快递' },
  { phase: 'presale', intent: '上门取件', keywords: '上门取件、取件时间', reply: '下单后联系快递员沟通好上门取件时间就行啦~ 也可以搜索「商达人」小橙序预约上门取件哦~', scope: '仅快递' },
  { phase: 'presale', intent: '商达人取件', keywords: '商达人、商达人取件', reply: '在小橙序搜索「商达人」点击进入 → 右下角「我的」→「兑换优惠」兑换余额 → 返回首页填写寄件和收件地址、选快递公司 → 用余额支付下单即可~', scope: '仅快递' },
  { phase: 'presale', intent: '包装费', keywords: '包装费、耗材费', reply: '包装费需要跟快递员确认，这个是快递员那边的收费哦~', scope: '仅快递' },
  { phase: 'presale', intent: '品牌缺货', keywords: '有顺丰吗、有京东吗', reply: '不好意思，暂时没有顺丰和京东的渠道呢~', scope: '仅快递' },
  { phase: 'presale', intent: '仅限首单', keywords: '第二次、再买、续费', reply: '亲，这个链接仅限首单哦~ 后续在小橙序直接下单就行，价格已经是官方5折了~', scope: '仅快递' },
  { phase: 'presale', intent: '老用户优惠', keywords: '老用户、老客户、更优惠', reply: '小橙序的价格已经是官方5折了，首重续重都有折扣哦~', scope: '仅快递' },
  { phase: 'presale', intent: '有效期', keywords: '过期、有效期', reply: '不会过期的~ 未兑换就一直有效，兑换成余额后也一直在账户里哦~', scope: '仅快递' },
  { phase: 'presale', intent: '禁寄物品', keywords: '能发吗、可以寄吗', reply: '刀具、易燃品、电池、生鲜、数码产品暂时不支持寄送呢~ 具体可以问我帮您确认~', scope: '仅快递' },
  { phase: 'presale', intent: '保价', keywords: '保价、保价费', reply: '圆通可以保价，保价费1元~ 韵达不支持保价，选保价后韵达不显示，取消保价韵达就出来了哦~', scope: '仅快递' },
  { phase: 'presale', intent: '网点问题', keywords: '不接单、运力不足、被取消', reply: '亲，您那边的快递网点暂时不接单了~ 换别的快递重新下单试试哦~', scope: '仅快递' },
  { phase: 'presale', intent: '快递单号', keywords: '上传单号、填单号', reply: '可以的~ 不管是抖音还是闲鱼、淘宝、拼多多都可以，选自行寄回填写快递单号就行~', scope: '仅快递' },
  { phase: 'presale', intent: '实名认证', keywords: '实名、身份证', reply: '去圆通/韵达官方小橙序，点我的，有个实名认证，认证一下就好了，是互通的~', scope: '仅快递' },
  // 快递售后 - 引导小橙序客服
  { phase: 'aftersale', intent: '退款', keywords: '退款、不想要了、退钱', reply: '好的亲，我会尽快帮您处理退款，请稍等一下哦~', scope: '仅快递', needsHuman: true },
  { phase: 'aftersale', intent: '退款申请', keywords: '申请退款、走退款', reply: '收到您的退款申请，我会尽快帮您处理~ 如有问题随时联系我哦~', scope: '仅快递', needsHuman: true },
  { phase: 'aftersale', intent: '投诉/丢件', keywords: '丢件、破损、投诉', reply: '非常抱歉给您带来不便~ 请把快递单号发我，我会尽快帮您处理！', scope: '仅快递', needsHuman: true },
  { phase: 'aftersale', intent: '余额不够', keywords: '余额不够、抵扣不了', reply: '亲，是不是选错快递公司了呢？截图给我看一下~ 如需帮助可以在小橙序点击「联系客服」哦~', scope: '仅快递', needsHuman: true },
  { phase: 'aftersale', intent: '揽收慢', keywords: '没来取、不来取、揽收慢', reply: '如果急件可以先换快递公司下单~ 揽收问题可以在小橙序点击「联系客服」反馈哦~', scope: '仅快递', needsHuman: true },
  { phase: 'aftersale', intent: '差评风险', keywords: '差评、体验差', reply: '非常抱歉给您不好的体验~ 请在小橙序首页点击「联系客服」，客服会第一时间帮您处理的~', scope: '仅快递', needsHuman: true },
];

const PHASE_LABELS: Record<RulePhase, { label: string; color: string }> = {
  universal: { label: '通用', color: 'bg-blue-50 text-blue-600' },
  presale: { label: '售前·自动', color: 'bg-green-50 text-green-600' },
  presale_human: { label: '售前·需人工', color: 'bg-yellow-50 text-yellow-700' },
  aftersale: { label: '售后·引导客服', color: 'bg-red-50 text-red-600' },
};

const PHASE_ORDER: RulePhase[] = ['universal', 'presale_human', 'presale', 'aftersale'];

function BuiltinRulesTable() {
  const grouped = PHASE_ORDER.map(phase => ({
    phase,
    ...PHASE_LABELS[phase],
    rules: BUILTIN_RULES.filter(r => r.phase === phase),
  }));

  return (
    <div className="space-y-3">
      <p className="text-xs text-xy-text-secondary">
        以下规则始终生效。标记「仅快递」的规则仅在快递品类下触发。售后规则引导客户到小橙序联系客服。如需覆盖，在上方「关键词快捷回复」中添加相同关键词（优先级最高）。
      </p>
      {grouped.map(group => (
        <div key={group.phase} className="space-y-1">
          <div className="flex items-center gap-2 py-1">
            <span className={`px-2 py-0.5 rounded-full text-[11px] font-semibold ${group.color}`}>{group.label}</span>
            <span className="text-xs text-gray-400">{group.rules.length} 条规则</span>
          </div>
          <div className="divide-y divide-xy-border border border-xy-border rounded-xl overflow-hidden">
            {group.rules.map((rule, i) => (
              <div key={i} className="p-3 hover:bg-xy-gray-50 transition-colors">
                <div className="flex items-start gap-3">
                  <div className="flex-shrink-0 flex flex-col items-start gap-1">
                    <span className="px-2 py-0.5 rounded-full bg-indigo-50 text-indigo-600 text-[11px] font-medium">{rule.intent}</span>
                    {rule.scope && <span className="px-1.5 py-0.5 rounded bg-orange-50 text-orange-600 text-[10px] font-medium">{rule.scope}</span>}
                    {rule.needsHuman && <span className="px-1.5 py-0.5 rounded bg-rose-50 text-rose-600 text-[10px] font-medium">转人工</span>}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-xs text-gray-500 mb-1">
                      触发词：<span className="text-xy-text-primary font-medium">{rule.keywords}</span>
                    </p>
                    <p className="text-sm text-xy-text-primary">{rule.reply}</p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      ))}
      <GuideCard summary="回复优先级说明">
        <p>1. 你的「关键词快捷回复」（优先级 30，最高）</p>
        <p>2. 快递售前/售后专用规则（优先级 45-50）</p>
        <p>3. 通用内置规则（优先级 100）</p>
        <p>4. 虚拟商品回复 / 通用报价引导模板（兜底）</p>
        <p className="text-orange-600 mt-1">注：售后规则回复中会引导客户到小橙序联系客服，仅做日志记录不触发闲鱼转人工</p>
      </GuideCard>
    </div>
  );
}

function CopyableUrl({ label, url }: { label: string; url: string }) {
  const [copied, setCopied] = useState(false);
  const handleCopy = () => {
    navigator.clipboard.writeText(url).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  };
  return (
    <div className="flex items-center gap-2">
      <span className="text-xs text-xy-text-muted w-20 flex-shrink-0">{label}</span>
      <code className="flex-1 text-xs bg-white border border-xy-border rounded px-2.5 py-1.5 text-xy-text-primary select-all break-all">{url}</code>
      <button onClick={handleCopy} type="button" className="flex-shrink-0 px-2.5 py-1.5 text-xs rounded border border-xy-border bg-white hover:bg-xy-gray-50 transition-colors text-xy-text-secondary">
        {copied ? '已复制' : '复制'}
      </button>
    </div>
  );
}

function PushUrlDisplay() {
  const origin = typeof window !== 'undefined' ? window.location.origin : '';
  const orderUrl = `${origin}/api/xgj/order/receive`;
  const productUrl = `${origin}/api/xgj/product/receive`;
  return (
    <div className="mt-5 bg-blue-50/60 border border-blue-200 p-4 rounded-lg">
      <h4 className="font-semibold text-blue-900 text-sm mb-1 flex items-center gap-2">
        <Bell className="w-4 h-4" /> 消息推送 URL
      </h4>
      <p className="text-xs text-blue-600 mb-3">将以下地址填入闲管家开放平台的「消息推送地址」配置中。需确保本系统可从公网访问（可使用 ngrok、frp 等内网穿透工具）。</p>
      <div className="space-y-2">
        <CopyableUrl label="订单推送" url={orderUrl} />
        <CopyableUrl label="商品推送" url={productUrl} />
      </div>
    </div>
  );
}

function CollapsibleSection({ title, summary, guide, defaultOpen = false, children, icon }: {
  title: string;
  summary?: React.ReactNode;
  guide?: string;
  defaultOpen?: boolean;
  children: React.ReactNode;
  icon?: React.ReactNode;
}) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div className="border border-xy-border rounded-xl overflow-hidden">
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center justify-between px-5 py-4 bg-xy-gray-50 hover:bg-xy-gray-100 transition-colors text-left"
        type="button"
      >
        <div className="flex items-center gap-2 min-w-0">
          {icon}
          <span className="font-bold text-xy-text-primary text-sm">{title}</span>
        </div>
        <div className="flex items-center gap-3 flex-shrink-0">
          {!open && summary && (
            <div className="hidden sm:flex items-center gap-1.5 text-xs text-xy-text-secondary">
              {summary}
            </div>
          )}
          {open ? <ChevronUp className="w-4 h-4 text-xy-text-muted" /> : <ChevronDown className="w-4 h-4 text-xy-text-muted" />}
        </div>
      </button>
      {open && (
        <div className="px-5 py-5 space-y-6">
          {guide && <p className="text-sm text-xy-text-secondary pb-4 border-b border-xy-border">{guide}</p>}
          {children}
        </div>
      )}
    </div>
  );
}

function GuideCard({ summary, children }: { summary: string; children: React.ReactNode }) {
  const [expanded, setExpanded] = useState(false);
  return (
    <div className="p-3 bg-blue-50/60 rounded-lg border border-blue-200/50 text-sm">
      <button onClick={() => setExpanded(!expanded)} className="w-full text-left flex items-center justify-between" type="button">
        <span className="text-blue-700">{summary}</span>
        <span className="text-xs text-blue-500 underline ml-2 flex-shrink-0">{expanded ? '收起' : '了解详情'}</span>
      </button>
      {expanded && <div className="mt-3 text-blue-600 text-xs space-y-1">{children}</div>}
    </div>
  );
}

function ToggleSwitch({ checked, onChange }: { checked: boolean; onChange: () => void }) {
  return (
    <button
      type="button"
      className={`w-12 h-6 rounded-full transition-colors relative ${checked ? 'bg-green-500' : 'bg-gray-300'}`}
      onClick={onChange}
    >
      <div className={`absolute top-1 bg-white w-4 h-4 rounded-full transition-transform ${checked ? 'left-7' : 'left-1'}`} />
    </button>
  );
}

function CategorySwitchModal({
  open,
  targetCat,
  onApply,
  onSkip,
  onCancel,
}: {
  open: boolean;
  targetCat: string;
  onApply: () => void;
  onSkip: () => void;
  onCancel: () => void;
}) {
  if (!open) return null;
  const meta = CATEGORY_META[targetCat];
  const defaults = CATEGORY_DEFAULTS[targetCat] || GENERIC_DEFAULTS;
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 animate-in fade-in" onClick={onCancel}>
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-lg mx-4 overflow-hidden" onClick={e => e.stopPropagation()}>
        <div className="px-6 pt-6 pb-4 flex items-start justify-between">
          <div>
            <h3 className="text-lg font-bold text-xy-text-primary">切换到「{meta?.label}」</h3>
            <p className="text-sm text-xy-text-secondary mt-1">系统可根据品类自动调整以下配置</p>
          </div>
          <button onClick={onCancel} className="p-1 hover:bg-xy-gray-100 rounded-lg transition-colors">
            <X className="w-5 h-5 text-xy-text-muted" />
          </button>
        </div>
        <div className="px-6 pb-4">
          <div className="bg-xy-gray-50 rounded-xl p-4 space-y-2">
            {defaults.summary.map((item, i) => (
              <div key={i} className="flex items-center gap-2 text-sm text-xy-text-primary">
                <ArrowRight className="w-3.5 h-3.5 text-xy-brand-500 flex-shrink-0" />
                {item}
              </div>
            ))}
          </div>
          <p className="text-xs text-xy-text-muted mt-3">已有的精细化配置（报价引擎、路线加价、意图规则等）不受影响</p>
        </div>
        <div className="px-6 pb-6 flex gap-3">
          <button onClick={onApply} className="xy-btn-primary flex-1 py-2.5">应用推荐配置</button>
          <button onClick={onSkip} className="flex-1 py-2.5 border border-xy-border rounded-xl text-sm font-medium text-xy-text-secondary hover:bg-xy-gray-50 transition-colors">仅切换品类</button>
        </div>
      </div>
    </div>
  );
}

function CategoryContextBanner({ category }: { category: string }) {
  const meta = CATEGORY_META[category];
  if (!meta) return null;
  const defaults = CATEGORY_DEFAULTS[category] || GENERIC_DEFAULTS;
  return (
    <div className="flex items-center gap-3 px-4 py-3 bg-gradient-to-r from-xy-brand-50 to-orange-50 rounded-xl border border-xy-brand-200 mb-6">
      <span className="text-xl">{meta.icon}</span>
      <div className="flex-1 min-w-0">
        <span className="text-sm font-medium text-xy-text-primary">当前品类：{meta.label}</span>
        <div className="flex flex-wrap gap-2 mt-1">
          {defaults.summary.map((s, i) => (
            <span key={i} className="text-[10px] bg-white/70 text-xy-text-secondary px-1.5 py-0.5 rounded">{s}</span>
          ))}
        </div>
      </div>
    </div>
  );
}

/* BrandAssetsSection removed — now in AutoPublish.tsx */

export default function SystemConfig() {
  const { category, switchCategory } = useStoreCategory();
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();

  const [sectionMap, setSectionMap] = useState<Record<string, any>>({});
  const [config, setConfig] = useState<Record<string, any>>({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [switchModal, setSwitchModal] = useState<{ open: boolean; targetCat: string }>({ open: false, targetCat: '' });
  const [isDirty, setIsDirty] = useState(false);
  const savedConfigRef = useRef<Record<string, any>>({});
  const [activeTab, setActiveTab] = useState(() => {
    const tab = searchParams.get('tab');
    if (!tab) return 'store_category';
    if (tab === 'cookie') return 'store_category';
    return TAB_COMPAT[tab] || (ALL_TABS.some(t => t.key === tab) ? tab : 'store_category');
  });

  const [xgjTesting, setXgjTesting] = useState(false);
  const [xgjTestResult, setXgjTestResult] = useState<any>(null);
  const [aiTesting, setAiTesting] = useState(false);
  const [aiTestResult, setAiTestResult] = useState<any>(null);
  const [testingSend, setTestingSend] = useState<string | null>(null);
  const [setupProgress, setSetupProgress] = useState<Record<string, any> | null>(null);
  const [categoryList, setCategoryList] = useState<any[]>([]);
  const [categoryLoading, setCategoryLoading] = useState(false);
  const [categorySearch, setCategorySearch] = useState('');

  useEffect(() => {
    if (searchParams.get('tab') === 'cookie') {
      navigate('/accounts', { replace: true });
    }
  }, [searchParams, navigate]);

  useEffect(() => { fetchConfig(); fetchSetupProgress(); }, []);

  const fetchSetupProgress = async () => {
    try {
      const res = await api.get('/config/setup-progress');
      if (res.data?.ok) setSetupProgress(res.data);
    } catch { /* ignore */ }
  };

  const fetchConfig = async () => {
    setLoading(true);
    try {
      const [secRes, cfgRes] = await Promise.all([getConfigSections(), getSystemConfig()]);
      if (secRes.data?.ok) {
        const map: Record<string, any> = {};
        (secRes.data.sections || []).forEach((s: any) => { map[s.key] = s; });
        setSectionMap(map);
      }
      if (cfgRes.data?.ok) {
        const loaded = cfgRes.data.config || {};
        setConfig(loaded);
        savedConfigRef.current = JSON.parse(JSON.stringify(loaded));
        setIsDirty(false);
      }
    } catch {
      toast.error('加载配置失败');
    } finally {
      setLoading(false);
    }
  };

  const handleSave = useCallback(async (explicitConfig?: Record<string, any>) => {
    setSaving(true);
    const toSave = explicitConfig || config;
    try {
      const res = await saveSystemConfig(toSave);
      if (res.data?.ok) {
        toast.success('配置保存成功');
        const saved = res.data.config || toSave;
        setConfig(saved);
        savedConfigRef.current = JSON.parse(JSON.stringify(saved));
        setIsDirty(false);
      } else {
        toast.error(res.data?.error || '保存失败');
      }
    } catch {
      toast.error('保存出错');
    } finally {
      setSaving(false);
    }
  }, [config]);

  const handleChange = (sectionKey: string, fieldKey: string, value: any) => {
    setConfig(prev => ({
      ...prev,
      [sectionKey]: { ...(prev[sectionKey] || {}), [fieldKey]: value },
    }));
    setIsDirty(true);
  };

  const handleTestNotification = async (channel: string) => {
    const notifyCfg = config.notifications || {};
    const webhookKey = channel === 'feishu' ? 'feishu_webhook' : 'wechat_webhook';
    const webhookUrl = notifyCfg[webhookKey] || '';
    if (!webhookUrl || webhookUrl.includes('****')) {
      toast.error('请先填写并保存 Webhook URL');
      return;
    }
    setTestingSend(channel);
    try {
      const res = await api.post('/notifications/test', { channel, webhook_url: webhookUrl });
      if (res.data?.ok) {
        toast.success(channel === 'feishu' ? '飞书测试消息发送成功' : '企业微信测试消息发送成功');
      } else {
        toast.error(res.data?.error || '发送失败');
      }
    } catch (err: any) {
      toast.error('发送失败: ' + (err?.response?.data?.error || err.message));
    } finally {
      setTestingSend(null);
    }
  };

  const handleXgjTest = useCallback(async () => {
    const xgjCfg = config.xianguanjia || {};
    const appKey = xgjCfg.app_key || '';
    const appSecret = xgjCfg.app_secret || '';
    if (!appKey || String(appKey).includes('****')) {
      setXgjTestResult({ ok: false, message: '请先填写 AppKey' });
      toast.error('请先填写 AppKey');
      return;
    }
    if (!appSecret || String(appSecret).includes('****')) {
      setXgjTestResult({ ok: false, message: '请先填写 AppSecret' });
      toast.error('请先填写 AppSecret');
      return;
    }
    setXgjTesting(true);
    setXgjTestResult(null);
    try {
      const res = await api.post('/xgj/test-connection', {
        app_key: appKey,
        app_secret: appSecret,
        base_url: xgjCfg.base_url || '',
        mode: xgjCfg.mode || 'self_developed',
        seller_id: xgjCfg.seller_id || '',
      });
      if (res.data?.ok) {
        setXgjTestResult({ ok: true, message: `连接成功（延迟 ${res.data.latency_ms || '?'}ms）` });
        toast.success('闲管家连接测试成功');
      } else {
        setXgjTestResult({ ok: false, message: res.data?.message || '连接失败' });
        toast.error('闲管家连接失败: ' + (res.data?.message || '未知错误'));
      }
    } catch (err: any) {
      const msg = err?.response?.data?.message || err.message || '请求失败';
      setXgjTestResult({ ok: false, message: msg });
      toast.error('连接测试异常: ' + msg);
    } finally {
      setXgjTesting(false);
    }
  }, [config.xianguanjia]);

  const handleAiTest = useCallback(async () => {
    const aiCfg = config.ai || {};
    const provider = aiCfg.provider || 'qwen';
    const guide = AI_PROVIDER_GUIDES[provider];
    const apiKey = aiCfg.api_key || '';
    const baseUrl = aiCfg.base_url || guide?.baseUrl || '';
    const model = aiCfg.model || guide?.model || 'qwen-plus';
    if (!apiKey) {
      setAiTestResult({ ok: false, message: '请先填写 API Key' });
      toast.error('请先填写 API Key');
      return;
    }
    setAiTesting(true);
    setAiTestResult(null);
    try {
      const res = await api.post('/ai/test', { api_key: apiKey, base_url: baseUrl, model });
      if (res.data?.ok) {
        setAiTestResult({ ok: true, message: res.data.message });
        toast.success('AI 连接测试成功');
      } else {
        setAiTestResult({ ok: false, message: res.data?.message || '连接失败' });
        toast.error('AI 连接失败: ' + (res.data?.message || '未知错误'));
      }
    } catch (err: any) {
      const msg = err?.response?.data?.message || err.message || '请求失败';
      setAiTestResult({ ok: false, message: msg });
      toast.error('AI 测试异常: ' + msg);
    } finally {
      setAiTesting(false);
    }
  }, [config.ai]);

  const switchTab = (key: string) => {
    if (isDirty) {
      const confirmed = window.confirm('有未保存的修改，切换标签将丢失更改。是否继续？');
      if (!confirmed) return;
      setConfig(JSON.parse(JSON.stringify(savedConfigRef.current)));
      setIsDirty(false);
    }
    setActiveTab(key);
    setSearchParams({ tab: key }, { replace: true });
  };

  const handleCategoryClick = (newCat: string) => {
    if (newCat === category) return;
    setSwitchModal({ open: true, targetCat: newCat });
  };

  const applyCategoryDefaults = async (targetCat: string) => {
    const defaults = CATEGORY_DEFAULTS[targetCat] || GENERIC_DEFAULTS;
    let newConfig: Record<string, any> = {};
    setConfig(prev => {
      const next = { ...prev };
      next.auto_reply = {
        ...(prev.auto_reply || {}),
        default_reply: defaults.auto_reply.default_reply,
        virtual_default_reply: defaults.auto_reply.virtual_default_reply,
        ai_intent_enabled: defaults.auto_reply.ai_intent_enabled,
        enabled: defaults.auto_reply.enabled,
      };
      next.pricing = {
        ...(prev.pricing || {}),
        auto_adjust: defaults.pricing.auto_adjust,
        min_margin_percent: defaults.pricing.min_margin_percent,
        max_discount_percent: defaults.pricing.max_discount_percent,
      };
      next.delivery = {
        ...(prev.delivery || {}),
        auto_delivery: defaults.delivery.auto_delivery,
        delivery_timeout_minutes: defaults.delivery.delivery_timeout_minutes,
      };
      newConfig = next;
      return next;
    });
    await switchCategory(targetCat);
    setSwitchModal({ open: false, targetCat: '' });
    toast.success(`已切换到「${CATEGORY_META[targetCat]?.label}」并应用推荐配置`);
    handleSave(newConfig);
  };

  const handleSwitchOnly = async (targetCat: string) => {
    await switchCategory(targetCat);
    setSwitchModal({ open: false, targetCat: '' });
    toast.success(`已切换到「${CATEGORY_META[targetCat]?.label}」`);
  };

  const isConfigured = (sectionKey: string): boolean => {
    const data = config[sectionKey] || {};
    switch (sectionKey) {
      case 'xianguanjia': return !!data.app_key && !String(data.app_key).includes('****');
      case 'ai': return !!data.api_key && !String(data.api_key).includes('****');
      case 'oss': return !!data.access_key_id && !String(data.access_key_id).includes('****');
      case 'cookie_cloud': return !!data.cookie_cloud_host;
      default: return Object.keys(data).length > 0;
    }
  };

  const renderSectionFields = (sectionKey: string) => {
    const section = sectionMap[sectionKey];
    if (!section?.fields) return null;
    const sectionData = config[sectionKey] || {};
    const selectedProvider = config.ai?.provider || 'qwen';

    return (
      <div className="space-y-5 max-w-2xl">
        {section.fields.map((field: any) => {
          const value = sectionData[field.key] !== undefined ? sectionData[field.key] : (field.default ?? '');

          if (field.required_when) {
            const [condKey, condVal] = Object.entries(field.required_when)[0] as [string, any];
            const actual = sectionData[condKey] !== undefined
              ? sectionData[condKey]
              : (section.fields.find((f: any) => f.key === condKey)?.default || '');
            if (actual !== condVal) return null;
          }

          const isConditionalRequired = field.required_when && (() => {
            const [condKey, condVal] = Object.entries(field.required_when)[0] as [string, any];
            const actual = sectionData[condKey] !== undefined ? sectionData[condKey] : '';
            return actual === condVal;
          })();

          return (
            <div key={field.key}>
              <label className="xy-label flex items-center justify-between">
                <span>
                  {field.label}
                  {(field.required || isConditionalRequired) && <span className="text-red-500 ml-1">*</span>}
                </span>
              </label>

              {field.type === 'textarea' ? (
                <textarea
                  className="xy-input px-3 py-2 h-24"
                  value={value}
                  placeholder={field.placeholder || ''}
                  onChange={e => handleChange(sectionKey, field.key, e.target.value)}
                />
              ) : field.type === 'select' ? (
                <select
                  className="xy-input px-3 py-2"
                  value={value}
                  onChange={e => handleChange(sectionKey, field.key, e.target.value)}
                >
                  {field.options?.map((opt: string) => (
                    <option key={opt} value={opt}>{field.labels?.[opt] || opt}</option>
                  ))}
                </select>
              ) : field.type === 'combobox' ? (() => {
                const providerModels = sectionKey === 'ai'
                  ? (AI_PROVIDER_GUIDES[selectedProvider]?.models || [])
                  : (field.options || []).map((o: any) => typeof o === 'string' ? { value: o, label: o } : o);
                const optionValues = providerModels.map((m: any) => m.value);
                const isCustom = value && !optionValues.includes(value);
                return (
                  <div className="space-y-2" key={field.key}>
                    <select
                      className="xy-input px-3 py-2"
                      value={isCustom ? '__custom__' : value}
                      onChange={e => handleChange(sectionKey, field.key, e.target.value === '__custom__' ? '' : e.target.value)}
                    >
                      {providerModels.map((m: any) => (
                        <option key={m.value} value={m.value}>{m.label}</option>
                      ))}
                      <option value="__custom__">自定义模型...</option>
                    </select>
                    {isCustom && (
                      <input
                        type="text"
                        className="xy-input px-3 py-2"
                        value={value}
                        placeholder="输入自定义模型名称"
                        onChange={e => handleChange(sectionKey, field.key, e.target.value)}
                      />
                    )}
                  </div>
                );
              })() : field.type === 'region_cascader' ? (() => {
                const keys = field.keys || [];
                const regions = field.regions || {};
                const provinceCode = sectionData[keys[0]] || 0;
                const cityCode = sectionData[keys[1]] || 0;
                const districtCode = sectionData[keys[2]] || 0;
                const provinceData = regions[provinceCode];
                const cities = provinceData?.cities || {};
                const cityData = cities[cityCode];
                const districts = cityData?.districts || {};
                return (
                  <div className="flex gap-3">
                    <select
                      className="xy-input px-3 py-2 flex-1"
                      value={provinceCode}
                      onChange={e => {
                        const pCode = Number(e.target.value);
                        const pData = regions[pCode];
                        const firstCity = pData?.cities ? Number(Object.keys(pData.cities)[0]) : 0;
                        const firstCityData = pData?.cities?.[firstCity];
                        const firstDistrict = firstCityData?.districts ? Number(Object.keys(firstCityData.districts)[0]) : 0;
                        handleChange(sectionKey, keys[0], pCode);
                        handleChange(sectionKey, keys[1], firstCity);
                        handleChange(sectionKey, keys[2], firstDistrict);
                      }}
                    >
                      <option value={0}>选择省份</option>
                      {Object.entries(regions).map(([code, data]: [string, any]) => (
                        <option key={code} value={code}>{data.name}</option>
                      ))}
                    </select>
                    <select
                      className="xy-input px-3 py-2 flex-1"
                      value={cityCode}
                      onChange={e => {
                        const cCode = Number(e.target.value);
                        const cData = cities[cCode];
                        const firstDistrict = cData?.districts ? Number(Object.keys(cData.districts)[0]) : 0;
                        handleChange(sectionKey, keys[1], cCode);
                        handleChange(sectionKey, keys[2], firstDistrict);
                      }}
                    >
                      <option value={0}>选择城市</option>
                      {Object.entries(cities).map(([code, data]: [string, any]) => (
                        <option key={code} value={code}>{data.name}</option>
                      ))}
                    </select>
                    <select
                      className="xy-input px-3 py-2 flex-1"
                      value={districtCode}
                      onChange={e => handleChange(sectionKey, keys[2], Number(e.target.value))}
                    >
                      <option value={0}>选择区县</option>
                      {Object.entries(districts).map(([code, name]: [string, any]) => (
                        <option key={code} value={code}>{name}</option>
                      ))}
                    </select>
                  </div>
                );
              })() : field.type === 'category_picker' ? (() => {
                const fetchCategories = async () => {
                  setCategoryLoading(true);
                  setCategoryList([]);
                  setCategorySearch('');
                  try {
                    const itemBizType = Number(sectionData['default_item_biz_type'] || 2);
                    const spBizType = Number(sectionData['default_sp_biz_type'] || 99);
                    const res = await api.post('/xgj/proxy', {
                      apiPath: '/api/open/product/category/list',
                      payload: { item_biz_type: itemBizType, sp_biz_type: spBizType },
                    });
                    const list = res.data?.data?.data?.list || res.data?.data?.list || [];
                    if (list.length === 0) {
                      toast.error('未查询到类目，请检查闲管家配置和商品类型/行业类型');
                    } else {
                      setCategoryList(list);
                      toast.success(`查询到 ${list.length} 个可用类目`);
                    }
                  } catch (err: any) {
                    toast.error('查询类目失败: ' + (err?.response?.data?.error || err?.message || '请检查闲管家配置'));
                  } finally {
                    setCategoryLoading(false);
                  }
                };
                const keyword = categorySearch.trim().toLowerCase();
                const filtered = keyword
                  ? categoryList.filter((c: any) =>
                      (c.channel_cat_name || c.sp_biz_name || '').toLowerCase().includes(keyword)
                      || (c.channel_cat_id || '').toLowerCase().includes(keyword))
                  : categoryList;
                const MAX_DISPLAY = 50;
                const displayed = filtered.slice(0, MAX_DISPLAY);
                return (
                  <div className="space-y-2">
                    <div className="flex gap-2">
                      <input
                        type="text"
                        className="xy-input px-3 py-2 flex-1"
                        value={value || ''}
                        placeholder="点击右侧按钮查询可用类目"
                        onChange={e => handleChange(sectionKey, field.key, e.target.value)}
                      />
                      <button
                        type="button"
                        className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm rounded-lg whitespace-nowrap disabled:opacity-50 transition-colors"
                        onClick={fetchCategories}
                        disabled={categoryLoading}
                      >
                        {categoryLoading ? '查询中...' : '查询类目'}
                      </button>
                    </div>
                    {categoryList.length > 0 && (
                      <div className="border border-gray-600 rounded-lg overflow-hidden">
                        <div className="px-3 py-2 bg-gray-800/50 border-b border-gray-700">
                          <input
                            type="text"
                            className="xy-input px-3 py-1.5 w-full text-sm"
                            placeholder={`搜索类目名称（共 ${categoryList.length} 个类目）`}
                            value={categorySearch}
                            onChange={e => setCategorySearch(e.target.value)}
                          />
                        </div>
                        <div className="max-h-56 overflow-y-auto">
                          {displayed.length === 0 ? (
                            <div className="px-3 py-4 text-sm text-gray-500 text-center">
                              未找到匹配「{categorySearch}」的类目
                            </div>
                          ) : displayed.map((cat: any, idx: number) => (
                            <button
                              key={cat.channel_cat_id || idx}
                              type="button"
                              className={`w-full text-left px-3 py-2 text-sm hover:bg-blue-600/20 transition-colors flex justify-between items-center ${
                                value === cat.channel_cat_id ? 'bg-blue-600/30 text-blue-300' : 'text-gray-300'
                              }`}
                              onClick={() => {
                                handleChange(sectionKey, field.key, cat.channel_cat_id);
                                toast.success(`已选择: ${cat.channel_cat_name || cat.sp_biz_name || cat.channel_cat_id}`);
                              }}
                            >
                              <span>{cat.channel_cat_name || cat.sp_biz_name || '未知类目'}</span>
                              <span className="text-xs text-gray-500 font-mono ml-2">{cat.channel_cat_id}</span>
                            </button>
                          ))}
                        </div>
                        {filtered.length > MAX_DISPLAY && (
                          <div className="px-3 py-1.5 text-xs text-gray-500 bg-gray-800/50 border-t border-gray-700 text-center">
                            已显示前 {MAX_DISPLAY} 条，共 {filtered.length} 条匹配 — 输入关键词缩小范围
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                );
              })() : field.type === 'toggle' ? (
                <ToggleSwitch checked={!!value} onChange={() => handleChange(sectionKey, field.key, !value)} />
              ) : (
                <input
                  type={field.type || 'text'}
                  className="xy-input px-3 py-2"
                  value={value}
                  placeholder={field.placeholder || ''}
                  onChange={e => handleChange(sectionKey, field.key, field.type === 'number' ? Number(e.target.value) : e.target.value)}
                />
              )}
              {field.hint && <p className="text-xs text-gray-400 mt-1">{field.hint}</p>}
            </div>
          );
        })}
      </div>
    );
  };

  if (loading) {
    return (
      <div className="xy-page max-w-5xl xy-enter">
        <div className="flex justify-between mb-6">
          <div className="w-1/3">
            <div className="h-8 bg-xy-gray-200 rounded-lg w-1/2 mb-2 animate-pulse" />
            <div className="h-4 bg-xy-gray-200 rounded w-2/3 animate-pulse" />
          </div>
        </div>
        <div className="flex flex-col md:flex-row gap-6">
          <div className="md:w-64 flex-shrink-0">
            <div className="xy-card p-4 space-y-2">
              {[1, 2, 3, 4, 5].map(i => <div key={i} className="h-10 bg-xy-gray-100 rounded animate-pulse" />)}
            </div>
          </div>
          <div className="flex-1 xy-card p-6 space-y-6">
            <div className="h-6 bg-xy-gray-200 rounded w-1/4 animate-pulse mb-8" />
            {[1, 2, 3].map(i => (
              <div key={i} className="space-y-2">
                <div className="h-4 bg-xy-gray-200 rounded w-32 animate-pulse" />
                <div className="h-10 bg-xy-gray-100 rounded animate-pulse" />
              </div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  const selectedProvider = config.ai?.provider || 'qwen';
  const providerGuide = AI_PROVIDER_GUIDES[selectedProvider];

  return (
    <div className="xy-page max-w-5xl xy-enter">
      <div className="flex flex-col md:flex-row justify-between md:items-end gap-4 mb-6">
        <div>
          <h1 className="xy-title flex items-center gap-2">
            <Settings className="w-6 h-6 text-xy-brand-500" /> 系统配置
          </h1>
          <p className="xy-subtitle mt-1">管理集成服务、自动化规则和告警通知</p>
        </div>
        {activeTab !== 'store_category' && (
          <button onClick={() => handleSave()} disabled={saving} className={`xy-btn-primary flex items-center gap-2 ${isDirty ? 'ring-2 ring-orange-400 ring-offset-2' : ''}`}>
            {saving ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
            保存设置
            {isDirty && <span className="ml-1 w-2 h-2 rounded-full bg-orange-400 animate-pulse" />}
          </button>
        )}
      </div>

      <div className="flex flex-col md:flex-row gap-6">
        {/* Sidebar */}
        <div className="md:w-56 flex-shrink-0">
          <div className="xy-card overflow-hidden">
            <div className="flex flex-col">
              {TAB_GROUPS.map((group, gi) => {
                const progressKeyMap: Record<string, string[]> = {
                  store_category: ['store_category'],
                  integrations: ['xianguanjia', 'ai'],
                  auto_reply: ['auto_reply'],
                  notifications: ['notifications'],
                };
                return (
                  <React.Fragment key={group.group}>
                    {gi > 0 && <div className="border-t border-xy-border" />}
                    <div className="px-4 pt-3 pb-1">
                      <span className="text-[10px] font-semibold text-xy-text-muted uppercase tracking-wider">{group.group}</span>
                    </div>
                    {group.tabs.map(tab => {
                      const Icon = tab.icon;
                      const keys = progressKeyMap[tab.key];
                      let dot: React.ReactNode = null;
                      if (setupProgress && keys) {
                        const allDone = keys.every(k => setupProgress[k]);
                        dot = <span className={`ml-auto w-2 h-2 rounded-full flex-shrink-0 ${allDone ? 'bg-green-400' : 'bg-orange-400'}`} />;
                      }
                      return (
                        <button
                          key={tab.key}
                          onClick={() => switchTab(tab.key)}
                          aria-selected={activeTab === tab.key}
                          role="tab"
                          className={`text-left px-4 py-3 text-sm font-medium transition-colors border-l-4 flex items-center gap-2.5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-xy-brand-500 ${
                            activeTab === tab.key
                              ? 'border-l-xy-brand-500 bg-xy-brand-50 text-xy-brand-600'
                              : 'border-l-transparent text-xy-text-secondary hover:bg-xy-gray-50'
                          }`}
                        >
                          <Icon className="w-4 h-4" />
                          {tab.name}
                          {dot}
                        </button>
                      );
                    })}
                  </React.Fragment>
                );
              })}
            </div>
          </div>
          {setupProgress && (
            <div className="mt-3 px-3 py-2 bg-xy-gray-50 rounded-lg border border-xy-border">
              <div className="flex items-center justify-between mb-1.5">
                <span className="text-xs text-xy-text-muted">配置完成度</span>
                <span className="text-xs font-medium text-xy-brand-600">{setupProgress.overall_percent}%</span>
              </div>
              <div className="w-full bg-xy-gray-200 rounded-full h-1.5">
                <div className="bg-xy-brand-500 h-1.5 rounded-full transition-all" style={{ width: `${setupProgress.overall_percent}%` }} />
              </div>
            </div>
          )}
        </div>

        {/* Content */}
        <div className="flex-1 min-w-0">
          {/* ── 店铺品类 ── */}
          {activeTab === 'store_category' && (
            <div className="xy-card p-6 animate-in fade-in slide-in-from-right-4">
              <h2 className="text-lg font-bold text-xy-text-primary mb-1">店铺品类</h2>
              <p className="text-sm text-xy-text-secondary mb-6">选择你的主营品类，系统将根据品类自动适配功能、话术模板和合规规则</p>
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                {Object.entries(CATEGORY_META).map(([key, meta]) => (
                  <button
                    key={key}
                    onClick={() => handleCategoryClick(key)}
                    className={`text-left p-4 rounded-xl border-2 transition-all ${
                      category === key
                        ? 'border-xy-brand-500 bg-orange-50 ring-2 ring-xy-brand-200'
                        : 'border-xy-border hover:border-xy-brand-300 hover:bg-xy-gray-50'
                    }`}
                  >
                    <div className="flex items-center gap-3 mb-2">
                      <span className="text-2xl">{meta.icon}</span>
                      <span className="font-bold text-xy-text-primary">{meta.label}</span>
                      {category === key && (
                        <span className="ml-auto text-xs font-medium text-xy-brand-600 bg-xy-brand-100 px-2 py-0.5 rounded-full">当前</span>
                      )}
                    </div>
                    <p className="text-sm text-xy-text-secondary">{meta.desc}</p>
                  </button>
                ))}
              </div>
              <div className="mt-6 p-4 bg-blue-50 rounded-xl border border-blue-200">
                <p className="text-sm text-blue-700">
                  <strong>提示：</strong>切换品类后，系统将提示您是否自动应用推荐的回复话术、定价和发货规则。
                  已有的精细化配置（报价引擎、路线加价、意图规则等）不受影响。
                </p>
              </div>

              {setupProgress && setupProgress.overall_percent < 100 && (
                <div className="mt-6 p-5 bg-gradient-to-r from-emerald-50 to-teal-50 rounded-xl border border-emerald-200">
                  <h3 className="text-sm font-bold text-emerald-900 mb-3 flex items-center gap-2">
                    <ArrowRight className="w-4 h-4" /> 下一步配置引导
                  </h3>
                  <div className="space-y-2">
                    {!setupProgress.xianguanjia && (
                      <button onClick={() => switchTab('integrations')} className="w-full text-left px-3 py-2 rounded-lg bg-white/60 hover:bg-white border border-emerald-200/50 text-sm text-emerald-800 transition-colors flex items-center gap-2">
                        <span className="w-5 h-5 rounded-full bg-orange-100 text-orange-600 flex items-center justify-center text-xs font-bold flex-shrink-0">1</span>
                        配置闲管家连接 → 获取 AppKey 和 AppSecret
                      </button>
                    )}
                    {!setupProgress.ai && (
                      <button onClick={() => switchTab('integrations')} className="w-full text-left px-3 py-2 rounded-lg bg-white/60 hover:bg-white border border-emerald-200/50 text-sm text-emerald-800 transition-colors flex items-center gap-2">
                        <span className="w-5 h-5 rounded-full bg-blue-100 text-blue-600 flex items-center justify-center text-xs font-bold flex-shrink-0">2</span>
                        配置 AI 提供商 → 启用智能回复和意图识别
                      </button>
                    )}
                    {!setupProgress.auto_reply && (
                      <button onClick={() => switchTab('auto_reply')} className="w-full text-left px-3 py-2 rounded-lg bg-white/60 hover:bg-white border border-emerald-200/50 text-sm text-emerald-800 transition-colors flex items-center gap-2">
                        <span className="w-5 h-5 rounded-full bg-violet-100 text-violet-600 flex items-center justify-center text-xs font-bold flex-shrink-0">3</span>
                        设置自动回复模板 → 配置回复话术和规则
                      </button>
                    )}
                    {!setupProgress.notifications && (
                      <button onClick={() => switchTab('notifications')} className="w-full text-left px-3 py-2 rounded-lg bg-white/60 hover:bg-white border border-emerald-200/50 text-sm text-emerald-800 transition-colors flex items-center gap-2">
                        <span className="w-5 h-5 rounded-full bg-amber-100 text-amber-600 flex items-center justify-center text-xs font-bold flex-shrink-0">4</span>
                        配置告警通知 → 接收 Cookie 过期、订单异常等告警
                      </button>
                    )}
                  </div>
                </div>
              )}
            </div>
          )}

          <CategorySwitchModal
            open={switchModal.open}
            targetCat={switchModal.targetCat}
            onApply={() => applyCategoryDefaults(switchModal.targetCat)}
            onSkip={() => handleSwitchOnly(switchModal.targetCat)}
            onCancel={() => setSwitchModal({ open: false, targetCat: '' })}
          />

          {/* ── 集成服务 ── */}
          {activeTab === 'integrations' && (
            <div className="space-y-4 animate-in fade-in slide-in-from-right-4">
              <div className="xy-card p-6 pb-4">
                <h2 className="text-lg font-bold text-xy-text-primary flex items-center gap-2">
                  <Plug className="w-5 h-5" /> 集成服务
                </h2>
                <p className="text-sm text-xy-text-secondary mt-1">管理闲管家、AI 提供商和 OSS 存储的连接配置</p>
              </div>

              {/* 闲管家 */}
              <CollapsibleSection
                title="闲管家配置"
                guide={SECTION_GUIDES.xianguanjia}
                defaultOpen={isConfigured('xianguanjia')}
                icon={<Settings className="w-4 h-4 text-orange-500" />}
                summary={<span className={`px-1.5 py-0.5 rounded text-[11px] ${isConfigured('xianguanjia') ? 'bg-green-100 text-green-700' : 'bg-orange-100 text-orange-600'}`}>{isConfigured('xianguanjia') ? '已连接' : '未配置'}</span>}
              >
                {renderSectionFields('xianguanjia')}
                <div className="mt-6 flex items-center gap-3">
                  <button
                    onClick={handleXgjTest}
                    disabled={xgjTesting}
                    className="flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-lg border border-orange-300 text-orange-700 bg-orange-50 hover:bg-orange-100 transition-colors disabled:opacity-50"
                  >
                    {xgjTesting ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
                    测试连接
                  </button>
                  {xgjTestResult && (
                    <span className={`text-sm flex items-center gap-1 ${xgjTestResult.ok ? 'text-green-600' : 'text-red-600'}`}>
                      {xgjTestResult.ok ? <CheckCircle2 className="w-4 h-4" /> : <XCircle className="w-4 h-4" />}
                      {xgjTestResult.message}
                    </span>
                  )}
                </div>
                <PushUrlDisplay />
                <div className="mt-4 bg-gradient-to-r from-orange-50 to-amber-50 border border-orange-200 p-5 rounded-lg text-sm">
                  <h4 className="font-bold text-orange-900 mb-3 flex items-center gap-2">
                    <Info className="w-4 h-4" /> 新手引导：从零配置闲管家
                  </h4>
                  <ol className="list-decimal list-inside space-y-2 text-orange-800">
                    <li><strong>注册开放平台账号</strong> — 前往 <a href="https://www.goofish.pro" target="_blank" rel="noreferrer" className="underline ml-1">闲管家官网</a>，使用闲鱼/淘宝账号登录</li>
                    <li><strong>创建应用</strong> — 登录后在「我的应用」中新建应用，获取 <strong>AppKey</strong> 和 <strong>AppSecret</strong></li>
                    <li>
                      <strong>选择接入模式</strong>
                      <ul className="ml-6 mt-1 space-y-1 list-disc list-inside text-orange-700">
                        <li><strong>自研应用</strong>：个人卖家或自有系统直连</li>
                        <li><strong>商务对接</strong>：第三方服务商代运营，额外需要 Seller ID</li>
                      </ul>
                    </li>
                    <li><strong>填入配置</strong> — 把上方字段填写完整后点击「保存设置」</li>
                    <li><strong>测试连接</strong> — 点击「测试连接」按钮，确认绿色「连接成功」</li>
                    <li><strong>配置消息推送</strong> — 将上方「消息推送 URL」区域中的地址复制到闲管家开放平台的「消息推送地址」配置中</li>
                    <li><strong>配置商品默认参数</strong> — 设置商品类型、行业类型，然后点击「查询类目」搜索并选择对应类目。确认默认价格、运费、成色和发货地区无误</li>
                  </ol>
                  <div className="mt-4 pt-3 border-t border-orange-200/60">
                    <p className="text-xs text-orange-600">
                      <strong>API 网关</strong>默认为 <code className="bg-white/60 px-1 rounded">https://open.goofish.pro</code>。
                      如遇问题，参考
                      <a href="https://s.apifox.cn/3ac13d69-5a38-4536-ae9b-a54001854ef8" target="_blank" rel="noreferrer" className="underline ml-1">
                        开放平台文档 <ExternalLink className="w-3 h-3 inline" />
                      </a>
                    </p>
                  </div>
                </div>
              </CollapsibleSection>

              {/* AI 配置 */}
              <CollapsibleSection
                title="AI 配置"
                guide={SECTION_GUIDES.ai}
                defaultOpen={isConfigured('ai')}
                icon={<Zap className="w-4 h-4 text-blue-500" />}
                summary={<>
                  <span className={`px-1.5 py-0.5 rounded text-[11px] ${isConfigured('ai') ? 'bg-green-100 text-green-700' : 'bg-orange-100 text-orange-600'}`}>{isConfigured('ai') ? '已配置' : '未配置'}</span>
                  {config.ai?.model && <span className="px-1.5 py-0.5 rounded bg-blue-50 text-blue-600 text-[11px]">{config.ai.model}</span>}
                </>}
              >
                {renderSectionFields('ai')}
                <div className="mt-6 flex items-center gap-3">
                  <button
                    onClick={handleAiTest}
                    disabled={aiTesting}
                    className="flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-lg border border-blue-300 text-blue-700 bg-blue-50 hover:bg-blue-100 transition-colors disabled:opacity-50"
                  >
                    {aiTesting ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
                    测试 AI 连接
                  </button>
                  {aiTestResult && (
                    <span className={`text-sm flex items-center gap-1 ${aiTestResult.ok ? 'text-green-600' : 'text-red-600'}`}>
                      {aiTestResult.ok ? <CheckCircle2 className="w-4 h-4" /> : <XCircle className="w-4 h-4" />}
                      {aiTestResult.message}
                    </span>
                  )}
                </div>
                {providerGuide && (
                  <div className="mt-4 bg-gradient-to-r from-blue-50 to-indigo-50 border border-blue-200 p-5 rounded-lg text-sm">
                    <h4 className="font-bold text-blue-900 mb-3 flex items-center gap-2">
                      <Info className="w-4 h-4" /> {providerGuide.name} 配置指南
                    </h4>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-blue-800">
                      <div>
                        <span className="text-blue-600 text-xs uppercase tracking-wide">API 地址</span>
                        <p className="font-mono text-xs bg-white/60 px-2 py-1 rounded mt-0.5 break-all">{providerGuide.baseUrl}</p>
                      </div>
                      <div>
                        <span className="text-blue-600 text-xs uppercase tracking-wide">推荐模型</span>
                        <p className="font-mono text-xs bg-white/60 px-2 py-1 rounded mt-0.5">{providerGuide.model}</p>
                      </div>
                    </div>
                    <p className="mt-3 text-blue-700">{providerGuide.tip}</p>
                    <a href={providerGuide.applyUrl} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 mt-3 text-blue-600 hover:text-blue-800 font-medium underline text-xs">
                      前往申请 API Key <ExternalLink className="w-3 h-3" />
                    </a>
                  </div>
                )}
              </CollapsibleSection>

              {/* 阿里云 OSS */}
              <CollapsibleSection
                title="阿里云 OSS"
                guide={SECTION_GUIDES.oss}
                defaultOpen={isConfigured('oss')}
                icon={<Store className="w-4 h-4 text-emerald-500" />}
                summary={<span className={`px-1.5 py-0.5 rounded text-[11px] ${isConfigured('oss') ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'}`}>{isConfigured('oss') ? '已配置' : '可选'}</span>}
              >
                {renderSectionFields('oss')}
              </CollapsibleSection>

              {/* CookieCloud */}
              <CollapsibleSection
                title="CookieCloud 配置"
                defaultOpen={isConfigured('cookie_cloud')}
                icon={<RefreshCw className="w-4 h-4 text-purple-500" />}
                summary={<span className={`px-1.5 py-0.5 rounded text-[11px] ${isConfigured('cookie_cloud') ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'}`}>{isConfigured('cookie_cloud') ? '已配置' : '可选'}</span>}
              >
                {renderSectionFields('cookie_cloud')}
                <div className="mt-4 bg-gradient-to-r from-purple-50 to-violet-50 border border-purple-200 p-5 rounded-lg text-sm">
                  <h4 className="font-bold text-purple-900 mb-3 flex items-center gap-2">
                    <Info className="w-4 h-4" /> CookieCloud 配置指南（内置服务端，无需额外部署）
                  </h4>
                  <ol className="list-decimal list-inside space-y-2 text-purple-800">
                    <li>
                      <strong>安装浏览器扩展</strong> — 在 Chrome/Edge 中安装
                      <a href="https://chromewebstore.google.com/detail/cookiecloud/ffjiejobkoibkjlhjnlgmcnnigeelbdl" target="_blank" rel="noreferrer" className="underline ml-1">
                        CookieCloud 扩展 <ExternalLink className="w-3 h-3 inline" />
                      </a>
                    </li>
                    <li>
                      <strong>配置扩展</strong> — 打开扩展设置：
                      <ul className="ml-6 mt-1 space-y-1 list-disc list-inside text-purple-700">
                        <li>服务器地址填 <code className="bg-white/60 px-1.5 py-0.5 rounded text-xs font-mono">http://localhost:8091/cookie-cloud</code></li>
                        <li>点击「生成」获取 <strong>UUID</strong> 和 <strong>密码</strong></li>
                        <li>同步域名添加 <code className="bg-white/60 px-1 rounded text-xs">.goofish.com</code> <code className="bg-white/60 px-1 rounded text-xs">.taobao.com</code> <code className="bg-white/60 px-1 rounded text-xs">.tmall.com</code></li>
                        <li>同步间隔建议 <strong>10 分钟</strong></li>
                      </ul>
                    </li>
                    <li><strong>填入上方配置</strong> — 服务地址留空（自动使用内置服务），将扩展中的 UUID 和密码填入，点击「保存设置」</li>
                  </ol>
                  <div className="mt-3 pt-3 border-t border-purple-200/60 space-y-2">
                    <p className="text-xs text-purple-600">
                      <strong>工作原理</strong>：浏览器保持闲鱼登录 → 扩展自动同步 Cookie 到内置服务端 → 系统即时解密并应用（秒级生效），实现全自动免维护。
                      优先级：CookieCloud &gt; 浏览器数据库(rookiepy) &gt; 手动更新。
                    </p>
                    <p className="text-xs text-purple-700 bg-purple-100/60 rounded px-2 py-1.5">
                      <strong>风控恢复提示</strong>：触发 RGV587 风控后，在浏览器完成滑块验证，然后在 CookieCloud 扩展中点击「手动同步」，系统将秒级自动恢复，无需手动复制 Cookie。
                    </p>
                    <a href="https://github.com/easychen/CookieCloud" target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 mt-1 text-purple-600 hover:text-purple-800 font-medium underline text-xs">
                      CookieCloud 项目文档 <ExternalLink className="w-3 h-3" />
                    </a>
                  </div>
                </div>
              </CollapsibleSection>

              {/* 风控滑块自动验证 */}
              <CollapsibleSection
                title="风控滑块自动验证"
                defaultOpen={!!config.slider_auto_solve?.enabled}
                icon={<Shield className="w-4 h-4 text-amber-500" />}
                summary={<span className={`px-1.5 py-0.5 rounded text-[11px] ${config.slider_auto_solve?.enabled ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'}`}>{config.slider_auto_solve?.enabled ? '已开启' : '已关闭'}</span>}
              >
                <div className="space-y-4">
                  <div className="bg-gradient-to-r from-amber-50 to-orange-50 border border-amber-300 p-4 rounded-lg">
                    <p className="text-sm text-amber-900 font-medium flex items-center gap-2">
                      <Shield className="w-4 h-4" /> 风险提示
                    </p>
                    <p className="text-xs text-amber-800 mt-1">
                      自动过滑块使用 Playwright 模拟浏览器操作，存在一定的账号封控风险。建议在了解风险后再开启。
                      开启后，RGV587 风控触发时系统会自动尝试滑块验证；失败后会弹出浏览器窗口供手动操作。
                    </p>
                  </div>

                  <div className="flex items-center justify-between p-3 bg-xy-gray-50 rounded-xl border border-xy-border">
                    <div>
                      <p className="font-medium text-xy-text-primary">启用自动滑块验证</p>
                      <p className="text-xs text-xy-text-secondary mt-0.5">RGV587 触发后自动尝试过滑块</p>
                    </div>
                    <ToggleSwitch checked={!!config.slider_auto_solve?.enabled} onChange={() => handleChange('slider_auto_solve', 'enabled', !config.slider_auto_solve?.enabled)} />
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                      <label className="xy-label">最大尝试次数</label>
                      <input
                        type="number"
                        className="xy-input px-3 py-2 w-full"
                        value={config.slider_auto_solve?.max_attempts ?? 2}
                        min={1}
                        max={5}
                        onChange={e => handleChange('slider_auto_solve', 'max_attempts', Number(e.target.value))}
                      />
                      <p className="text-[11px] text-gray-400 mt-1">每轮 RGV587 最多自动尝试次数（建议 1-3）</p>
                    </div>
                    <div>
                      <label className="xy-label">冷却间隔（秒）</label>
                      <input
                        type="number"
                        className="xy-input px-3 py-2 w-full"
                        value={config.slider_auto_solve?.cooldown_seconds ?? 300}
                        min={60}
                        max={3600}
                        onChange={e => handleChange('slider_auto_solve', 'cooldown_seconds', Number(e.target.value))}
                      />
                      <p className="text-[11px] text-gray-400 mt-1">两次尝试之间的等待时间</p>
                    </div>
                  </div>

                  <div className="flex items-center justify-between p-3 bg-xy-gray-50 rounded-xl border border-xy-border">
                    <div>
                      <p className="font-medium text-xy-text-primary text-sm">无头模式</p>
                      <p className="text-xs text-xy-text-secondary mt-0.5">后台静默运行浏览器（关闭后可看到浏览器窗口，方便手动接管）</p>
                    </div>
                    <ToggleSwitch checked={!!config.slider_auto_solve?.headless} onChange={() => handleChange('slider_auto_solve', 'headless', !config.slider_auto_solve?.headless)} />
                  </div>
                </div>
              </CollapsibleSection>
            </div>
          )}

          {/* ── 自动回复 ── */}
          {activeTab === 'auto_reply' && (
            <div className="space-y-4 animate-in fade-in slide-in-from-right-4">
              <div className="xy-card p-6 pb-4">
                <h2 className="text-lg font-bold text-xy-text-primary flex items-center gap-2"><MessageSquare className="w-5 h-5" /> 自动回复设置</h2>
                <p className="text-sm text-xy-text-secondary mt-1">配置买家消息的自动回复策略，设置后系统会按下方模拟的方式回复买家</p>
              </div>
              <CategoryContextBanner category={category} />

              {/* ═══ 第一层：核心设置 ═══ */}
              <div className="xy-card p-6 space-y-5">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="font-medium text-xy-text-primary">启用自动回复</p>
                    <p className="text-xs text-xy-text-secondary mt-0.5">收到买家消息时自动生成回复</p>
                  </div>
                  <ToggleSwitch checked={config.auto_reply?.enabled !== false} onChange={() => handleChange('auto_reply', 'enabled', !(config.auto_reply?.enabled !== false))} />
                </div>

                <div>
                  <h3 className="text-sm font-bold text-xy-text-primary mb-3 flex items-center gap-2"><Zap className="w-4 h-4 text-amber-500" /> 一键应用预设话术</h3>
                  <div className="flex flex-wrap gap-2">
                    {Object.entries(CATEGORY_DEFAULTS).map(([key, defaults]) => {
                      const meta = CATEGORY_META[key];
                      if (!meta) return null;
                      const isCurrent = key === category;
                      const isActive = config.auto_reply?.default_reply === defaults.auto_reply.default_reply;
                      return (
                        <button key={key} onClick={() => {
                          handleChange('auto_reply', 'default_reply', defaults.auto_reply.default_reply);
                          handleChange('auto_reply', 'virtual_default_reply', defaults.auto_reply.virtual_default_reply);
                          toast.success(`已应用「${meta.label}」话术`);
                        }} className={`px-3 py-1.5 text-sm border rounded-lg transition-colors ${
                          isActive ? 'border-xy-brand-500 bg-xy-brand-50 text-xy-brand-700 font-medium' :
                          isCurrent ? 'border-xy-brand-300 bg-orange-50/50 hover:bg-xy-brand-50' :
                          'border-xy-border hover:bg-xy-gray-50 hover:border-xy-brand-300'
                        }`}>
                          {meta.icon} {meta.label}话术
                          {isActive && <span className="ml-1 text-xs text-xy-brand-500">(当前)</span>}
                        </button>
                      );
                    })}
                  </div>
                </div>

                {/* 对话流程模拟器 */}
                <ConversationSimulator category={category} config={config} />
              </div>

              {/* ═══ 第二层：回复模板 ═══ */}
              <CollapsibleSection
                title="回复模板"
                defaultOpen
                icon={<FileText className="w-4 h-4 text-blue-500" />}
                summary={<span className="px-1.5 py-0.5 rounded bg-blue-50 text-blue-600 text-[11px]">通用 + 虚拟商品 + 关键词</span>}
              >
                <div className="space-y-4">
                  <div>
                    <label className="xy-label">通用回复模板</label>
                    <textarea className="xy-input px-3 py-2 h-24 resize-none" placeholder="买家消息的默认自动回复内容..." value={config.auto_reply?.default_reply || ''} onChange={e => handleChange('auto_reply', 'default_reply', e.target.value)} />
                    <p className="text-[11px] text-gray-400 mt-1">所有内置规则和报价引导均未匹配时，使用此模板回复</p>
                  </div>
                  <div>
                    <label className="xy-label">虚拟商品回复模板</label>
                    <textarea className="xy-input px-3 py-2 h-24 resize-none" placeholder="虚拟商品（兑换码/卡密）的专用回复模板..." value={config.auto_reply?.virtual_default_reply || ''} onChange={e => handleChange('auto_reply', 'virtual_default_reply', e.target.value)} />
                    <p className="text-[11px] text-gray-400 mt-1">系统判断为虚拟商品时优先使用此模板</p>
                  </div>
                  <div className="border-t border-xy-border pt-4">
                    <label className="xy-label flex items-center gap-2">关键词快捷回复 <span className="text-[11px] font-normal text-gray-400">(优先于通用模板)</span></label>
                    <textarea className="xy-input px-3 py-2 h-28 resize-none text-sm font-mono" placeholder={"还在=在的亲，请问需要寄什么快递？\n最低=价格已经尽量实在了，诚心要的话可以小刀。\n包邮=默认不包邮，具体看地区可以商量。"} value={config.auto_reply?.keyword_replies_text || ''} onChange={e => handleChange('auto_reply', 'keyword_replies_text', e.target.value)} />
                    <p className="text-[11px] text-gray-400 mt-1">每行一条，格式：<code className="bg-gray-100 px-1 rounded">关键词=回复内容</code>。买家消息包含关键词时直接回复。</p>
                  </div>
                </div>
              </CollapsibleSection>

              {/* ═══ 第三层：高级设置 ═══ */}
              <CollapsibleSection
                title="高级设置"
                icon={<Settings className="w-4 h-4 text-gray-400" />}
                summary={<span className="px-1.5 py-0.5 rounded bg-gray-100 text-gray-500 text-[11px]">适合进阶用户</span>}
              >
                <div className="space-y-4">
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    <div className="flex items-center justify-between p-3 bg-xy-gray-50 rounded-xl border border-xy-border">
                      <div>
                        <p className="font-medium text-xy-text-primary text-sm">AI 意图识别</p>
                        <p className="text-[11px] text-xy-text-secondary mt-0.5">用 AI 分析买家消息意图</p>
                      </div>
                      <ToggleSwitch checked={!!config.auto_reply?.ai_intent_enabled} onChange={() => handleChange('auto_reply', 'ai_intent_enabled', !config.auto_reply?.ai_intent_enabled)} />
                    </div>
                    <div className="flex items-center justify-between p-3 bg-xy-gray-50 rounded-xl border border-xy-border">
                      <div>
                        <p className="font-medium text-xy-text-primary text-sm">严格格式引导</p>
                        <p className="text-[11px] text-xy-text-secondary mt-0.5">招呼语也引导标准格式</p>
                      </div>
                      <ToggleSwitch checked={config.auto_reply?.strict_format_reply_enabled !== false} onChange={() => handleChange('auto_reply', 'strict_format_reply_enabled', !(config.auto_reply?.strict_format_reply_enabled !== false))} />
                    </div>
                    <div className="flex items-center justify-between p-3 bg-xy-gray-50 rounded-xl border border-xy-border">
                      <div>
                        <p className="font-medium text-xy-text-primary text-sm">强制非空回复</p>
                        <p className="text-[11px] text-xy-text-secondary mt-0.5">无匹配时用兜底话术</p>
                      </div>
                      <ToggleSwitch checked={config.auto_reply?.force_non_empty_reply !== false} onChange={() => handleChange('auto_reply', 'force_non_empty_reply', !(config.auto_reply?.force_non_empty_reply !== false))} />
                    </div>
                    <div className="flex items-center justify-between p-3 bg-xy-gray-50 rounded-xl border border-xy-border">
                      <div>
                        <p className="font-medium text-xy-text-primary text-sm">报价最多展示快递数</p>
                        <p className="text-[11px] text-xy-text-secondary mt-0.5">报价结果中的快递数量上限</p>
                      </div>
                      <input type="number" className="xy-input px-2 py-1 w-16 text-center text-sm" value={config.auto_reply?.quote_reply_max_couriers ?? 10} onChange={e => handleChange('auto_reply', 'quote_reply_max_couriers', Number(e.target.value))} />
                    </div>
                  </div>
                  <div>
                    <label className="xy-label">报价引导话术</label>
                    <textarea className="xy-input px-3 py-2 h-20 resize-none text-sm" placeholder="为了给你报最准确的价格，麻烦提供一下：{fields}..." value={config.auto_reply?.quote_missing_template || ''} onChange={e => handleChange('auto_reply', 'quote_missing_template', e.target.value)} />
                    <p className="text-[11px] text-gray-400 mt-1"><code className="bg-gray-100 px-1 rounded">{'{fields}'}</code> 自动替换为缺失信息（寄件城市、收件城市、包裹重量）</p>
                  </div>
                  <div>
                    <label className="xy-label">兜底话术</label>
                    <textarea className="xy-input px-3 py-2 h-16 resize-none text-sm" placeholder="所有规则均未匹配时的最后兜底回复..." value={config.auto_reply?.non_empty_reply_fallback || ''} onChange={e => handleChange('auto_reply', 'non_empty_reply_fallback', e.target.value)} />
                  </div>
                  <div>
                    <label className="xy-label">报价失败话术</label>
                    <textarea className="xy-input px-3 py-2 h-16 resize-none text-sm" placeholder="报价服务异常时的降级回复..." value={config.auto_reply?.quote_failed_template || ''} onChange={e => handleChange('auto_reply', 'quote_failed_template', e.target.value)} />
                  </div>
                </div>
              </CollapsibleSection>

              {/* ═══ 内置规则一览 ═══ */}
              <CollapsibleSection
                title="系统内置意图规则"
                icon={<Shield className="w-4 h-4 text-indigo-500" />}
                summary={<span className="px-1.5 py-0.5 rounded bg-indigo-50 text-indigo-600 text-[11px]">7 条规则始终生效</span>}
              >
                <BuiltinRulesTable />
              </CollapsibleSection>
            </div>
          )}

          {/* ── 订单管理 ── */}
          {activeTab === 'orders' && (
            <div className="space-y-4 animate-in fade-in slide-in-from-right-4">
              <div className="xy-card p-6 pb-4">
                <h2 className="text-lg font-bold text-xy-text-primary flex items-center gap-2"><Receipt className="w-5 h-5" /> 订单管理</h2>
                <p className="text-sm text-xy-text-secondary mt-1">定价策略、发货规则和催单设置</p>
              </div>
              <CategoryContextBanner category={category} />

              {/* 定价规则 */}
              <CollapsibleSection
                title="定价规则"
                defaultOpen
                icon={<DollarSign className="w-4 h-4 text-amber-500" />}
                summary={<>
                  <span className={`px-1.5 py-0.5 rounded text-[11px] ${config.pricing?.auto_adjust ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'}`}>{config.pricing?.auto_adjust ? '自动调价' : '手动定价'}</span>
                  <span className="px-1.5 py-0.5 rounded bg-xy-brand-50 text-xy-brand-600 text-[11px]">利润 {config.pricing?.min_margin_percent ?? 10}%</span>
                  <span className="px-1.5 py-0.5 rounded bg-orange-50 text-orange-600 text-[11px]">降幅 {config.pricing?.max_discount_percent ?? 20}%</span>
                </>}
              >
                <div className="mb-4">
                  <p className="text-xs font-medium text-xy-text-secondary mb-2">快速应用预设方案</p>
                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                    {Object.entries(PRICING_PRESETS).map(([key, preset]) => {
                      const catDefaults = CATEGORY_DEFAULTS[category]?.pricing || GENERIC_DEFAULTS.pricing;
                      const isRecommended = preset.min_margin_percent === catDefaults.min_margin_percent && preset.auto_adjust === catDefaults.auto_adjust;
                      const isActive = config.pricing?.min_margin_percent === preset.min_margin_percent && config.pricing?.max_discount_percent === preset.max_discount_percent && !!config.pricing?.auto_adjust === preset.auto_adjust;
                      return (
                        <button key={key} onClick={() => {
                          handleChange('pricing', 'auto_adjust', preset.auto_adjust);
                          handleChange('pricing', 'min_margin_percent', preset.min_margin_percent);
                          handleChange('pricing', 'max_discount_percent', preset.max_discount_percent);
                          toast.success(`已应用「${preset.label}」方案`);
                        }} className={`text-left p-3 rounded-xl border transition-all ${
                          isActive ? 'border-xy-brand-500 bg-xy-brand-50 ring-1 ring-xy-brand-200' :
                          'border-xy-border hover:border-xy-brand-300 hover:bg-xy-brand-50'
                        }`}>
                          <p className="font-bold text-sm text-xy-text-primary flex items-center gap-2">
                            {preset.label}
                            {isRecommended && <span className="text-[10px] font-medium text-xy-brand-500 bg-xy-brand-100 px-1.5 py-0.5 rounded-full">推荐</span>}
                            {isActive && <span className="text-[10px] font-medium text-green-600 bg-green-100 px-1.5 py-0.5 rounded-full">当前</span>}
                          </p>
                          <p className="text-xs text-xy-text-secondary mt-0.5">{preset.desc}</p>
                        </button>
                      );
                    })}
                  </div>
                </div>
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <div><p className="font-medium text-sm text-xy-text-primary">自动调价</p><p className="text-xs text-xy-text-secondary">系统根据市场行情和库存自动调整价格</p></div>
                    <ToggleSwitch checked={!!config.pricing?.auto_adjust} onChange={() => handleChange('pricing', 'auto_adjust', !config.pricing?.auto_adjust)} />
                  </div>
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="xy-label">最低利润率 (%)</label>
                      <input type="number" className="xy-input px-3 py-2" value={config.pricing?.min_margin_percent ?? 10} onChange={e => handleChange('pricing', 'min_margin_percent', Number(e.target.value))} />
                      <p className="text-xs text-gray-400 mt-1">低于此利润率的价格不会被采用</p>
                    </div>
                    <div>
                      <label className="xy-label">最大降价幅度 (%)</label>
                      <input type="number" className="xy-input px-3 py-2" value={config.pricing?.max_discount_percent ?? 20} onChange={e => handleChange('pricing', 'max_discount_percent', Number(e.target.value))} />
                      <p className="text-xs text-gray-400 mt-1">单次调价不超过此幅度</p>
                    </div>
                  </div>
                </div>
                <GuideCard summary="快递品类用户可在「商品管理 > 加价规则」中配置更精细的路线加价">
                  <p>此处的定价规则为全局兜底策略，针对不同路线可设置更精细的定价偏移。</p>
                </GuideCard>
              </CollapsibleSection>

              {/* 催单设置 */}
              <CollapsibleSection
                title="催单设置"
                icon={<Bell className="w-4 h-4 text-purple-500" />}
                summary={<>
                  <span className={`px-1.5 py-0.5 rounded text-[11px] ${config.order_reminder?.enabled !== false ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'}`}>{config.order_reminder?.enabled !== false ? '已启用' : '已关闭'}</span>
                  <span className="px-1.5 py-0.5 rounded bg-purple-50 text-purple-600 text-[11px]">{config.order_reminder?.max_daily ?? 2}次/日</span>
                </>}
              >
                <GuideCard summary={
                  category === 'express' ? '快递品类建议：催单话术中提示买家提供收件信息，加速下单流程' :
                  ['exchange', 'recharge', 'game'].includes(category) ? '虚拟品类建议：催单话术中强调付款后秒发，降低买家犹豫' :
                  '通用建议：催单话术保持友好语气，说明商品优势促进成交'
                }>
                  <p>系统对未支付订单自动执行合规检查（静默时段、频率限制、免打扰名单）后选择话术并通过闲鱼 IM 发送给买家。</p>
                </GuideCard>
                <div className="mt-4">{renderSectionFields('order_reminder')}</div>

                <div className="mt-5">
                  <label className="xy-label">催单话术模板</label>
                  <p className="text-xs text-xy-text-muted mb-2">每条话术用 <code className="bg-xy-gray-100 px-1 rounded">---</code> 分隔，系统按催单次数依次发送（第1次/第2次/最终提醒）</p>
                  <textarea
                    className="xy-input px-3 py-2 h-36 resize-none text-sm"
                    placeholder={"首次催付话术\n---\n二次催付话术\n---\n最终催付话术"}
                    value={config.order_reminder?.templates || '您好，您的订单还没有完成支付哦~ 如有疑问可以随时问我，确认需要的话请尽快支付，我好给您安排发货。\n---\n提醒一下，您有一笔待支付订单，商品已为您预留，请在规定时间内完成支付，以免影响发货哦~\n---\n最后提醒：您的订单即将超时关闭，如果还需要请尽快支付。若已不需要请忽略此消息。'}
                    onChange={e => handleChange('order_reminder', 'templates', e.target.value)}
                  />
                </div>
              </CollapsibleSection>

              {/* 发货规则 */}
              <CollapsibleSection
                title="发货规则"
                icon={<CheckCircle2 className="w-4 h-4 text-blue-500" />}
                summary={<>
                  <span className={`px-1.5 py-0.5 rounded text-[11px] ${config.delivery?.auto_delivery ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'}`}>{config.delivery?.auto_delivery ? '自动发货' : '手动发货'}</span>
                  <span className="px-1.5 py-0.5 rounded bg-blue-50 text-blue-600 text-[11px]">超时 {config.delivery?.delivery_timeout_minutes ?? 30}分钟</span>
                </>}
              >
                <GuideCard summary={
                  category === 'express' ? '快递品类实物发货需要提供快递单号和物流公司信息' :
                  ['exchange', 'recharge', 'game', 'movie_ticket', 'account'].includes(category) ? '虚拟商品发货完全由闲管家平台自动完成，开启自动发货后无需人工介入' :
                  '自动发货由闲管家平台执行，此开关控制订单支付后是否自动触发发货'
                }>
                  <p>发货超时后将触发告警通知（需在「告警通知」中配置 Webhook）。</p>
                </GuideCard>
                <div className="mt-4">{renderSectionFields('delivery')}</div>
              </CollapsibleSection>
            </div>
          )}

          {/* ── 商品运营 ── */}
          {activeTab === 'products' && (
            <div className="space-y-4 animate-in fade-in slide-in-from-right-4">
              <div className="xy-card p-6 pb-4">
                <h2 className="text-lg font-bold text-xy-text-primary flex items-center gap-2"><Package className="w-5 h-5" /> 商品运营</h2>
                <p className="text-sm text-xy-text-secondary mt-1">自动上架策略和品牌素材管理</p>
              </div>
              <CategoryContextBanner category={category} />

              {/* 自动上架 */}
              <CollapsibleSection
                title="自动上架"
                defaultOpen
                icon={<Store className="w-4 h-4 text-emerald-500" />}
                summary={<>
                  <span className={`px-1.5 py-0.5 rounded text-[11px] ${config.auto_publish?.enabled ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'}`}>{config.auto_publish?.enabled ? '已启用' : '未启用'}</span>
                  {config.auto_publish?.enabled && (
                    <span className="px-1.5 py-0.5 rounded bg-emerald-50 text-emerald-600 text-[11px]">
                      最多 {config.auto_publish?.max_active_listings ?? 10} 条链接
                    </span>
                  )}
                </>}
              >
                {/* 开关 + 基础设置 */}
                <div className="space-y-4">
                  <div className="flex items-center justify-between p-4 bg-xy-gray-50 rounded-xl border border-xy-border">
                    <div>
                      <p className="font-medium text-xy-text-primary">启用自动上架</p>
                      <p className="text-xs text-xy-text-secondary mt-0.5">开启后系统按策略自动上架新商品</p>
                    </div>
                    <ToggleSwitch checked={!!config.auto_publish?.enabled} onChange={() => handleChange('auto_publish', 'enabled', !config.auto_publish?.enabled)} />
                  </div>

                  {config.auto_publish?.enabled && (
                    <>
                      {/* 策略时间线可视化 */}
                      <div className="p-4 bg-gradient-to-r from-emerald-50 to-blue-50 rounded-xl border border-emerald-200">
                        <h4 className="text-sm font-bold text-xy-text-primary mb-3 flex items-center gap-2">
                          <TrendingUp className="w-4 h-4 text-emerald-500" /> 上架策略概览
                        </h4>
                        <div className="flex items-center gap-0">
                          {/* 冷启动阶段 */}
                          <div className="flex-1 text-center">
                            <div className="bg-emerald-500 text-white text-xs font-bold py-2 px-3 rounded-l-lg">
                              D1 ~ D{config.auto_publish?.cold_start_days ?? 2}
                            </div>
                            <p className="text-xs text-emerald-700 mt-1.5 font-medium">冷启动期</p>
                            <p className="text-[11px] text-emerald-600">每天新建 {config.auto_publish?.cold_start_daily_count ?? 5} 条</p>
                          </div>
                          <div className="text-emerald-400 text-lg font-bold">→</div>
                          {/* 稳定阶段 */}
                          <div className="flex-1 text-center">
                            <div className="bg-blue-500 text-white text-xs font-bold py-2 px-3 rounded-r-lg">
                              D{(config.auto_publish?.cold_start_days ?? 2) + 1}+
                            </div>
                            <p className="text-xs text-blue-700 mt-1.5 font-medium">稳定运营</p>
                            <p className="text-[11px] text-blue-600">每天替换 {config.auto_publish?.steady_replace_count ?? 1} 条最差链接</p>
                          </div>
                        </div>
                        <p className="text-[11px] text-gray-500 mt-2 text-center">
                          最大活跃链接 {config.auto_publish?.max_active_listings ?? 10} 条 · 替换依据：{(config.auto_publish?.steady_replace_metric ?? 'views') === 'views' ? '浏览量' : '销量'}
                        </p>
                      </div>

                      {/* 调度参数编辑 */}
                      <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                        <div>
                          <label className="xy-label">冷启动天数</label>
                          <input type="number" min={1} max={14} className="xy-input px-3 py-2" value={config.auto_publish?.cold_start_days ?? 2} onChange={e => handleChange('auto_publish', 'cold_start_days', Math.max(1, Number(e.target.value)))} />
                          <p className="text-[11px] text-gray-400 mt-1">前 N 天批量上架</p>
                        </div>
                        <div>
                          <label className="xy-label">每日新建链接数</label>
                          <input type="number" min={1} max={20} className="xy-input px-3 py-2" value={config.auto_publish?.cold_start_daily_count ?? 5} onChange={e => handleChange('auto_publish', 'cold_start_daily_count', Math.max(1, Number(e.target.value)))} />
                          <p className="text-[11px] text-gray-400 mt-1">冷启动期每天</p>
                        </div>
                        <div>
                          <label className="xy-label">每日替换链接数</label>
                          <input type="number" min={1} max={10} className="xy-input px-3 py-2" value={config.auto_publish?.steady_replace_count ?? 1} onChange={e => handleChange('auto_publish', 'steady_replace_count', Math.max(1, Number(e.target.value)))} />
                          <p className="text-[11px] text-gray-400 mt-1">稳定期每天</p>
                        </div>
                        <div>
                          <label className="xy-label">最大活跃链接数</label>
                          <input type="number" min={1} max={50} className="xy-input px-3 py-2" value={config.auto_publish?.max_active_listings ?? 10} onChange={e => handleChange('auto_publish', 'max_active_listings', Math.max(1, Number(e.target.value)))} />
                          <p className="text-[11px] text-gray-400 mt-1">店铺上限</p>
                        </div>
                        <div>
                          <label className="xy-label">替换依据</label>
                          <select className="xy-input px-3 py-2" value={config.auto_publish?.steady_replace_metric ?? 'views'} onChange={e => handleChange('auto_publish', 'steady_replace_metric', e.target.value)}>
                            <option value="views">浏览量最低</option>
                            <option value="sales">销量最低</option>
                          </select>
                          <p className="text-[11px] text-gray-400 mt-1">判断"最差"链接</p>
                        </div>
                        <div>
                          <label className="xy-label">默认品类</label>
                          <select className="xy-input px-3 py-2" value={config.auto_publish?.default_category ?? 'exchange'} onChange={e => handleChange('auto_publish', 'default_category', e.target.value)}>
                            {Object.entries(CATEGORY_META).map(([k, m]) => (
                              <option key={k} value={k}>{m.icon} {m.label}</option>
                            ))}
                          </select>
                          <p className="text-[11px] text-gray-400 mt-1">新商品默认归属</p>
                        </div>
                      </div>

                      <div className="flex items-center justify-between p-3 bg-xy-gray-50 rounded-xl border border-xy-border">
                        <div>
                          <p className="font-medium text-sm text-xy-text-primary">自动合规检查</p>
                          <p className="text-xs text-xy-text-secondary">上架前自动检测违规关键词和敏感内容</p>
                        </div>
                        <ToggleSwitch checked={config.auto_publish?.auto_compliance !== false} onChange={() => handleChange('auto_publish', 'auto_compliance', !(config.auto_publish?.auto_compliance !== false))} />
                      </div>
                    </>
                  )}
                </div>
              </CollapsibleSection>

              {/* 品牌素材库 — 已迁移到自动上架页面 */}
              <div className="bg-violet-50 border border-violet-200 rounded-xl p-4 flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-violet-800">品牌素材库 & 模板管理</p>
                  <p className="text-xs text-violet-600 mt-0.5">管理品牌图片和商品主图模板已移至自动上架页面</p>
                </div>
                <a href="/products/auto-publish?tab=assets" className="px-3 py-1.5 text-xs font-medium bg-violet-600 text-white rounded-lg hover:bg-violet-700 transition-colors">
                  前往管理 →
                </a>
              </div>
            </div>
          )}

          {/* ── 告警通知 ── */}
          {activeTab === 'notifications' && (
            <div className="xy-card p-6 animate-in fade-in slide-in-from-right-4 space-y-6">
              <div>
                <h2 className="text-lg font-bold text-xy-text-primary flex items-center gap-2"><Bell className="w-5 h-5" /> 告警通知</h2>
                <p className="text-sm text-xy-text-secondary mt-1">配置通知渠道和事件推送规则</p>
              </div>

              {/* 通知渠道 */}
              <div>
                <h3 className="text-sm font-bold text-xy-text-primary mb-3">通知渠道</h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {/* 飞书 */}
                  <div className={`p-5 rounded-xl border-2 transition-colors ${config.notifications?.feishu_enabled ? 'border-blue-300 bg-blue-50/30' : 'border-xy-border'}`}>
                    <div className="flex items-center justify-between mb-3">
                      <span className="font-bold text-xy-text-primary">飞书</span>
                      <ToggleSwitch checked={!!config.notifications?.feishu_enabled} onChange={() => handleChange('notifications', 'feishu_enabled', !config.notifications?.feishu_enabled)} />
                    </div>
                    {config.notifications?.feishu_enabled && (
                      <div className="space-y-3">
                        <div>
                          <label className="xy-label text-xs">Webhook URL</label>
                          <input
                            type="text"
                            className="xy-input px-3 py-2 text-sm"
                            placeholder="https://open.feishu.cn/open-apis/bot/v2/hook/xxx"
                            value={config.notifications?.feishu_webhook || ''}
                            onChange={e => handleChange('notifications', 'feishu_webhook', e.target.value)}
                          />
                        </div>
                        <button
                          onClick={() => handleTestNotification('feishu')}
                          disabled={testingSend === 'feishu'}
                          className="flex items-center gap-2 px-3 py-1.5 text-xs font-medium rounded-lg border border-blue-300 text-blue-700 bg-white hover:bg-blue-50 transition-colors disabled:opacity-50"
                        >
                          {testingSend === 'feishu' ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <Send className="w-3.5 h-3.5" />}
                          测试通知
                        </button>
                      </div>
                    )}
                  </div>

                  {/* 企业微信 */}
                  <div className={`p-5 rounded-xl border-2 transition-colors ${config.notifications?.wechat_enabled ? 'border-green-300 bg-green-50/30' : 'border-xy-border'}`}>
                    <div className="flex items-center justify-between mb-3">
                      <span className="font-bold text-xy-text-primary">企业微信</span>
                      <ToggleSwitch checked={!!config.notifications?.wechat_enabled} onChange={() => handleChange('notifications', 'wechat_enabled', !config.notifications?.wechat_enabled)} />
                    </div>
                    {config.notifications?.wechat_enabled && (
                      <div className="space-y-3">
                        <div>
                          <label className="xy-label text-xs">Webhook URL</label>
                          <input
                            type="text"
                            className="xy-input px-3 py-2 text-sm"
                            placeholder="https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=xxx"
                            value={config.notifications?.wechat_webhook || ''}
                            onChange={e => handleChange('notifications', 'wechat_webhook', e.target.value)}
                          />
                        </div>
                        <button
                          onClick={() => handleTestNotification('wechat')}
                          disabled={testingSend === 'wechat'}
                          className="flex items-center gap-2 px-3 py-1.5 text-xs font-medium rounded-lg border border-green-300 text-green-700 bg-white hover:bg-green-50 transition-colors disabled:opacity-50"
                        >
                          {testingSend === 'wechat' ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <Send className="w-3.5 h-3.5" />}
                          测试通知
                        </button>
                      </div>
                    )}
                  </div>
                </div>
              </div>

              {/* 事件通知开关 */}
              <div>
                <h3 className="text-sm font-bold text-xy-text-primary mb-3">事件通知</h3>
                <p className="text-xs text-xy-text-secondary mb-3">选择需要推送通知的事件类型</p>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                  {NOTIFICATION_EVENTS.map(evt => (
                    <div key={evt.key} className="flex items-center justify-between px-4 py-3 bg-xy-gray-50 rounded-lg border border-xy-border">
                      <span className="text-sm text-xy-text-primary">{evt.label}</span>
                      <ToggleSwitch
                        checked={config.notifications?.[evt.key] !== false}
                        onChange={() => handleChange('notifications', evt.key, !(config.notifications?.[evt.key] !== false))}
                      />
                    </div>
                  ))}
                </div>
              </div>

              <div className="p-4 bg-blue-50 rounded-lg border border-blue-200 text-sm text-blue-700">
                <p>配置 Webhook 后，Cookie 过期、订单异常、售后介入等重要事件将实时推送通知。飞书使用<strong>自定义机器人</strong>的 Webhook 地址；企业微信使用<strong>群机器人</strong>的 Webhook 地址。</p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
