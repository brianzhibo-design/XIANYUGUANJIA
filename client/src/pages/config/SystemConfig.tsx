import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { getSystemConfig, getConfigSections, saveSystemConfig } from '../../api/config';
import { getBrandAssets, uploadBrandAsset, deleteBrandAsset, type BrandAsset } from '../../api/listing';
import { api } from '../../api/index';
import { useStoreCategory, CATEGORY_META } from '../../contexts/StoreCategoryContext';
import toast from 'react-hot-toast';
import {
  Settings, Save, RefreshCw, Send, Bell, CheckCircle2, XCircle,
  ExternalLink, Info, Plug, ChevronDown, ChevronUp, FileText, Zap,
  DollarSign, Store, X, ArrowRight, Upload, Trash2, Image as ImageIcon,
  Receipt, Package,
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
      default_reply: '您好！我们提供全国快递代发服务。请告诉我始发地、目的地和大概重量，我帮您查询报价。\n付款后请提供完整的收件信息（姓名、电话、地址），我们会尽快安排发货。',
      virtual_default_reply: '',
      ai_intent_enabled: true,
      enabled: true,
    },
    pricing: { auto_adjust: false, min_margin_percent: 15, max_discount_percent: 15 },
    delivery: { auto_delivery: false, delivery_timeout_minutes: 60 },
    summary: ['自动回复 → 快递代发专用话术', '定价 → 保守方案（利润率 15%）', '发货 → 手动发货（需填快递单号）'],
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

const BRAND_GUIDE: Record<string, string> = {
  express: '请上传您代发的快递品牌 logo（如顺丰、中通、韵达），系统将自动排列组合生成商品主图',
  exchange: '请上传相关平台 logo（如 Steam、Xbox、PS），系统将生成带平台标识的商品主图',
  recharge: '请上传充值平台 logo（如移动、联通、电信），用于生成充值代充主图',
  movie_ticket: '请上传院线 logo（如万达、CGV、IMAX），用于生成电影票代购主图',
  account: '请上传平台/游戏 logo，用于生成账号交易商品主图',
  game: '请上传游戏 logo，用于生成游戏道具商品主图',
};

function BrandAssetsSection({ category }: { category: string }) {
  const [assets, setAssets] = useState<BrandAsset[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [newName, setNewName] = useState('');
  const fileRef = useRef<HTMLInputElement>(null);

  const fetchAssets = useCallback(async () => {
    try {
      const res = await getBrandAssets();
      if (res.data?.ok) setAssets(res.data.assets || []);
    } catch { /* ignore */ }
    setLoading(false);
  }, []);

  useEffect(() => { fetchAssets(); }, [fetchAssets]);

  const handleUpload = async () => {
    const file = fileRef.current?.files?.[0];
    if (!file) { toast.error('请选择图片文件'); return; }
    if (!newName.trim()) { toast.error('请输入品牌名称'); return; }
    setUploading(true);
    try {
      const res = await uploadBrandAsset(file, newName.trim(), category);
      if (res.data?.ok) {
        toast.success(`已上传「${newName.trim()}」`);
        setNewName('');
        if (fileRef.current) fileRef.current.value = '';
        fetchAssets();
      } else {
        toast.error('上传失败');
      }
    } catch (err: any) {
      toast.error('上传失败: ' + (err?.response?.data?.error || err.message));
    }
    setUploading(false);
  };

  const handleDelete = async (id: string, name: string) => {
    try {
      const res = await deleteBrandAsset(id);
      if (res.data?.ok) {
        toast.success(`已删除「${name}」`);
        setAssets(prev => prev.filter(a => a.id !== id));
      }
    } catch { toast.error('删除失败'); }
  };

  const guide = BRAND_GUIDE[category] || '上传与您商品相关的品牌/平台 logo，AI 将用它们生成美观的商品展示图';

  return (
    <div>
      <h3 className="text-sm font-bold text-xy-text-primary mb-4 flex items-center gap-2 pb-2 border-b border-xy-border">
        <ImageIcon className="w-4 h-4 text-violet-500" /> 品牌素材库
      </h3>
      <p className="text-sm text-xy-text-secondary mb-4">{guide}</p>

      <div className="flex items-end gap-3 mb-4">
        <div className="flex-1 max-w-xs">
          <label className="xy-label text-xs">品牌名称</label>
          <input
            type="text"
            className="xy-input px-3 py-2 text-sm"
            placeholder="如：顺丰、中通"
            value={newName}
            onChange={e => setNewName(e.target.value)}
          />
        </div>
        <div className="flex-1 max-w-xs">
          <label className="xy-label text-xs">Logo 图片</label>
          <input
            ref={fileRef}
            type="file"
            accept="image/png,image/jpeg,image/webp,image/svg+xml"
            className="xy-input px-3 py-1.5 text-sm file:mr-3 file:py-1 file:px-3 file:rounded-lg file:border-0 file:bg-xy-brand-50 file:text-xy-brand-600 file:font-medium file:text-xs"
          />
        </div>
        <button
          onClick={handleUpload}
          disabled={uploading}
          className="flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-lg bg-violet-50 border border-violet-300 text-violet-700 hover:bg-violet-100 transition-colors disabled:opacity-50"
        >
          {uploading ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Upload className="w-4 h-4" />}
          上传
        </button>
      </div>

      {loading ? (
        <div className="grid grid-cols-2 sm:grid-cols-4 md:grid-cols-6 gap-3">
          {[1, 2, 3].map(i => <div key={i} className="h-24 bg-xy-gray-100 rounded-xl animate-pulse" />)}
        </div>
      ) : assets.length === 0 ? (
        <div className="text-center py-8 text-xy-text-muted text-sm border-2 border-dashed border-xy-border rounded-xl">
          暂无品牌素材，请上传品牌 logo 图片
        </div>
      ) : (
        <div className="grid grid-cols-2 sm:grid-cols-4 md:grid-cols-6 gap-3">
          {assets.map(asset => (
            <div key={asset.id} className="group relative bg-xy-gray-50 rounded-xl border border-xy-border p-3 text-center">
              <div className="w-full aspect-square flex items-center justify-center mb-2 bg-white rounded-lg overflow-hidden">
                <img
                  src={`/api/brand-assets/file/${asset.filename}`}
                  alt={asset.name}
                  className="max-w-full max-h-full object-contain"
                  onError={e => { (e.target as HTMLImageElement).style.display = 'none'; }}
                />
              </div>
              <p className="text-xs font-medium text-xy-text-primary truncate">{asset.name}</p>
              <p className="text-[10px] text-xy-text-muted">{asset.category}</p>
              <button
                onClick={() => handleDelete(asset.id, asset.name)}
                className="absolute top-1.5 right-1.5 p-1 bg-white/80 rounded-md opacity-0 group-hover:opacity-100 transition-opacity hover:bg-red-50"
              >
                <Trash2 className="w-3.5 h-3.5 text-red-500" />
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

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
    setXgjTesting(true);
    setXgjTestResult(null);
    try {
      const res = await api.get('/health/check');
      const xgj = res.data?.xgj;
      if (xgj?.ok) {
        setXgjTestResult({ ok: true, message: `连接成功（延迟 ${xgj.latency_ms || '?'}ms）` });
        toast.success('闲管家连接测试成功');
      } else {
        setXgjTestResult({ ok: false, message: xgj?.message || '连接失败' });
        toast.error('闲管家连接失败: ' + (xgj?.message || '未知错误'));
      }
    } catch (err: any) {
      setXgjTestResult({ ok: false, message: err.message || '请求失败' });
      toast.error('连接测试异常');
    } finally {
      setXgjTesting(false);
    }
  }, []);

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
              })() : field.type === 'toggle' ? (
                <ToggleSwitch checked={!!value} onChange={() => handleChange(sectionKey, field.key, !value)} />
              ) : (
                <input
                  type={field.type || 'text'}
                  className="xy-input px-3 py-2"
                  value={value}
                  placeholder={field.placeholder || ''}
                  onChange={e => handleChange(sectionKey, field.key, e.target.value)}
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
            </div>
          )}

          {/* ── 自动回复 ── */}
          {activeTab === 'auto_reply' && (
            <div className="xy-card p-6 animate-in fade-in slide-in-from-right-4 space-y-6">
              <CategoryContextBanner category={category} />
              <div>
                <h2 className="text-lg font-bold text-xy-text-primary flex items-center gap-2"><FileText className="w-5 h-5" /> 自动回复设置</h2>
                <p className="text-sm text-xy-text-secondary mt-1">配置自动回复开关、AI 意图识别和回复模板</p>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="flex items-center justify-between p-4 bg-xy-gray-50 rounded-xl border border-xy-border">
                  <div>
                    <p className="font-medium text-xy-text-primary">启用自动回复</p>
                    <p className="text-xs text-xy-text-secondary mt-0.5">收到买家消息时自动生成回复</p>
                  </div>
                  <ToggleSwitch checked={config.auto_reply?.enabled !== false} onChange={() => handleChange('auto_reply', 'enabled', !(config.auto_reply?.enabled !== false))} />
                </div>
                <div className="flex items-center justify-between p-4 bg-xy-gray-50 rounded-xl border border-xy-border">
                  <div>
                    <p className="font-medium text-xy-text-primary">AI 意图识别</p>
                    <p className="text-xs text-xy-text-secondary mt-0.5">使用 AI 分析买家消息意图后生成针对性回复</p>
                  </div>
                  <ToggleSwitch checked={!!config.auto_reply?.ai_intent_enabled} onChange={() => handleChange('auto_reply', 'ai_intent_enabled', !config.auto_reply?.ai_intent_enabled)} />
                </div>
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

              <div className="space-y-4">
                <div>
                  <label className="xy-label">通用回复模板</label>
                  <textarea className="xy-input px-3 py-2 h-28 resize-none" placeholder="买家消息的默认自动回复内容..." value={config.auto_reply?.default_reply || ''} onChange={e => handleChange('auto_reply', 'default_reply', e.target.value)} />
                </div>
                <div>
                  <label className="xy-label">虚拟商品回复模板</label>
                  <textarea className="xy-input px-3 py-2 h-28 resize-none" placeholder="虚拟商品（兑换码/卡密）的专用回复模板..." value={config.auto_reply?.virtual_default_reply || ''} onChange={e => handleChange('auto_reply', 'virtual_default_reply', e.target.value)} />
                </div>
              </div>

              <div className="p-4 bg-blue-50 rounded-lg border border-blue-200 text-sm text-blue-700">
                <p className="font-medium mb-2">模板变量说明</p>
                <div className="grid grid-cols-2 gap-x-4 gap-y-1">
                  <div><code className="bg-blue-100 px-1 rounded">{'{{buyer_name}}'}</code> 买家昵称</div>
                  <div><code className="bg-blue-100 px-1 rounded">{'{{item_title}}'}</code> 商品标题</div>
                  <div><code className="bg-blue-100 px-1 rounded">{'{{item_price}}'}</code> 商品价格</div>
                  <div><code className="bg-blue-100 px-1 rounded">{'{{order_id}}'}</code> 订单号</div>
                </div>
                <p className="mt-2 text-xs text-blue-500">提示：模板保存后，可在「消息中心 &gt; 测试沙盒」中模拟测试效果</p>
              </div>
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
                </>}
              >
                {renderSectionFields('auto_publish')}
              </CollapsibleSection>

              {/* 品牌素材库 */}
              <CollapsibleSection
                title="品牌素材库"
                icon={<ImageIcon className="w-4 h-4 text-violet-500" />}
                summary={<span className="px-1.5 py-0.5 rounded bg-violet-50 text-violet-600 text-[11px]">用于商品主图生成</span>}
              >
                <BrandAssetsSection category={category} />
              </CollapsibleSection>
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
