import React, { useState, useEffect, useCallback } from 'react';
import { api } from '../api/index';
import { saveSystemConfig } from '../api/config';
import { useStoreCategory, CATEGORY_META } from '../contexts/StoreCategoryContext';
import {
  Cookie, Bot, Settings, Cloud, Bell, Store,
  ChevronRight, ChevronLeft, Check, Loader2,
  ExternalLink, AlertCircle, CheckCircle2, SkipForward,
} from 'lucide-react';

const STEPS = [
  { key: 'cookie', label: 'Cookie', icon: Cookie },
  { key: 'ai', label: 'AI 服务', icon: Bot },
  { key: 'xgj', label: '闲管家', icon: Settings },
  { key: 'cookiecloud', label: 'CookieCloud', icon: Cloud },
  { key: 'notify', label: '告警通知', icon: Bell },
  { key: 'category', label: '店铺品类', icon: Store },
] as const;

interface WizardData {
  cookie1: string;
  cookie2: string;
  ai: {
    provider: string;
    api_key: string;
    model: string;
    base_url: string;
  };
  xgj: {
    mode: string;
    app_key: string;
    app_secret: string;
    seller_id: string;
    base_url: string;
    default_item_biz_type: string;
    default_sp_biz_type: string;
    default_channel_cat_id: string;
    default_stuff_status: string;
    default_price: number;
    default_express_fee: number;
    default_stock: number;
    default_province: string;
    default_city: string;
    default_district: string;
    service_support: string;
    outer_id: string;
    product_callback_url: string;
  };
  cookiecloud: {
    cookie_cloud_host: string;
    cookie_cloud_uuid: string;
    cookie_cloud_password: string;
  };
  notifications: {
    feishu_enabled: boolean;
    feishu_webhook: string;
    wechat_enabled: boolean;
    wechat_webhook: string;
  };
  storeCategory: string;
}

const AI_PROVIDERS = [
  { id: 'qwen', label: '百炼千问 (Qwen)', model: 'qwen-plus-latest', base_url: 'https://dashscope.aliyuncs.com/compatible-mode/v1' },
  { id: 'deepseek', label: 'DeepSeek', model: 'deepseek-chat', base_url: 'https://api.deepseek.com/v1' },
  { id: 'openai', label: 'OpenAI', model: 'gpt-4o-mini', base_url: 'https://api.openai.com/v1' },
];

const ITEM_BIZ_TYPES: Record<string, string> = {
  '2': '普通商品', '0': '已验货', '10': '验货宝', '16': '品牌授权',
  '19': '闲鱼严选', '24': '闲鱼特卖', '26': '品牌捡漏', '35': '跨境商品',
};

const STUFF_STATUS: Record<string, string> = {
  '100': '全新', '-1': '准新', '99': '99新', '95': '95新', '90': '9新',
  '80': '8新', '70': '7新', '60': '6新', '50': '5新及以下',
};

const DEFAULT_DATA: WizardData = {
  cookie1: '', cookie2: '',
  ai: { provider: 'qwen', api_key: '', model: 'qwen-plus-latest', base_url: 'https://dashscope.aliyuncs.com/compatible-mode/v1' },
  xgj: {
    mode: 'self_developed', app_key: '', app_secret: '', seller_id: '',
    base_url: 'https://open.goofish.pro',
    default_item_biz_type: '2', default_sp_biz_type: '99',
    default_channel_cat_id: '', default_stuff_status: '100',
    default_price: 1, default_express_fee: 0, default_stock: 1,
    default_province: '', default_city: '', default_district: '',
    service_support: '', outer_id: '', product_callback_url: '',
  },
  cookiecloud: { cookie_cloud_host: '', cookie_cloud_uuid: '', cookie_cloud_password: '' },
  notifications: { feishu_enabled: false, feishu_webhook: '', wechat_enabled: false, wechat_webhook: '' },
  storeCategory: 'express',
};

export default function SetupWizard() {
  const [show, setShow] = useState(false);
  const [loading, setLoading] = useState(true);
  const [step, setStep] = useState(0);
  const [data, setData] = useState<WizardData>(DEFAULT_DATA);
  const [saving, setSaving] = useState(false);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [testResults, setTestResults] = useState<Record<string, { ok: boolean; msg: string } | null>>({});
  const { switchCategory } = useStoreCategory();

  useEffect(() => {
    checkWizardStatus();
  }, []);

  const checkWizardStatus = async () => {
    try {
      const res = await api.get('/wizard/status');
      if (!res.data?.completed) {
        await loadExistingConfig();
        setShow(true);
      }
    } catch {
      // API not available yet or wizard endpoint missing
    } finally {
      setLoading(false);
    }
  };

  const loadExistingConfig = async () => {
    try {
      const res = await api.get('/config');
      const cfg = res.data?.config || {};
      setData(prev => ({
        ...prev,
        ai: {
          provider: cfg.ai?.provider || prev.ai.provider,
          api_key: (cfg.ai?.api_key && !String(cfg.ai.api_key).includes('****')) ? cfg.ai.api_key : '',
          model: cfg.ai?.model || prev.ai.model,
          base_url: cfg.ai?.base_url || prev.ai.base_url,
        },
        xgj: {
          ...prev.xgj,
          ...(cfg.xianguanjia || {}),
          app_key: (cfg.xianguanjia?.app_key && !String(cfg.xianguanjia.app_key).includes('****')) ? cfg.xianguanjia.app_key : '',
          app_secret: (cfg.xianguanjia?.app_secret && !String(cfg.xianguanjia.app_secret).includes('****')) ? cfg.xianguanjia.app_secret : '',
        },
        cookiecloud: {
          cookie_cloud_host: cfg.cookie_cloud?.cookie_cloud_host || '',
          cookie_cloud_uuid: cfg.cookie_cloud?.cookie_cloud_uuid || '',
          cookie_cloud_password: '',
        },
        notifications: {
          feishu_enabled: cfg.notifications?.feishu_enabled || false,
          feishu_webhook: (cfg.notifications?.feishu_webhook && !String(cfg.notifications.feishu_webhook).includes('****')) ? cfg.notifications.feishu_webhook : '',
          wechat_enabled: cfg.notifications?.wechat_enabled || false,
          wechat_webhook: (cfg.notifications?.wechat_webhook && !String(cfg.notifications.wechat_webhook).includes('****')) ? cfg.notifications.wechat_webhook : '',
        },
        storeCategory: cfg.store?.category || 'express',
      }));
    } catch { /* ignore */ }
  };

  const validate = useCallback((): boolean => {
    const e: Record<string, string> = {};
    if (step === 0) {
      if (!data.cookie1.trim()) e.cookie1 = '请粘贴闲鱼 Cookie';
    } else if (step === 1) {
      if (!data.ai.api_key.trim()) e.ai_key = '请填写 API Key';
    } else if (step === 2) {
      if (!data.xgj.app_key.trim()) e.xgj_app_key = '请填写 AppKey';
      if (!data.xgj.app_secret.trim()) e.xgj_app_secret = '请填写 AppSecret';
      if (data.xgj.mode === 'business' && !data.xgj.seller_id.trim()) e.xgj_seller_id = '商务对接模式需要填写 Seller ID';
    }
    setErrors(e);
    return Object.keys(e).length === 0;
  }, [step, data]);

  const saveStepConfig = async () => {
    setSaving(true);
    try {
      if (step === 0) {
        await api.post('/update-cookie', { cookie: data.cookie1 });
      } else if (step === 1) {
        const p = AI_PROVIDERS.find(x => x.id === data.ai.provider);
        await saveSystemConfig({
          ai: {
            provider: data.ai.provider,
            api_key: data.ai.api_key,
            model: data.ai.model || p?.model || 'qwen-plus-latest',
            base_url: data.ai.base_url || p?.base_url || '',
          },
        });
      } else if (step === 2) {
        await saveSystemConfig({ xianguanjia: { ...data.xgj } });
      } else if (step === 3) {
        if (data.cookiecloud.cookie_cloud_uuid) {
          await saveSystemConfig({ cookie_cloud: { ...data.cookiecloud } });
        }
      } else if (step === 4) {
        await saveSystemConfig({ notifications: { ...data.notifications } });
      } else if (step === 5) {
        await switchCategory(data.storeCategory);
      }
    } catch (err: any) {
      setErrors({ _save: err.message || '保存失败' });
      setSaving(false);
      return false;
    }
    setSaving(false);
    return true;
  };

  const handleNext = async () => {
    if (!validate()) return;
    const ok = await saveStepConfig();
    if (!ok) return;
    if (step < STEPS.length - 1) {
      setStep(step + 1);
      setErrors({});
      setTestResults({});
    } else {
      await completeWizard();
    }
  };

  const handleSkip = async () => {
    setErrors({});
    setTestResults({});
    await completeWizard();
  };

  const completeWizard = async () => {
    setSaving(true);
    try {
      await api.post('/wizard/complete');
    } catch { /* non-critical */ }
    setSaving(false);
    setShow(false);
  };

  const testConnection = async (type: 'ai' | 'xgj') => {
    setTestResults(prev => ({ ...prev, [type]: null }));
    try {
      const res = await api.get('/health/check');
      const d = res.data?.[type];
      if (d) {
        setTestResults(prev => ({
          ...prev,
          [type]: { ok: d.ok, msg: d.ok ? `连通 (${d.latency_ms || 0}ms)` : d.message },
        }));
      }
    } catch {
      setTestResults(prev => ({ ...prev, [type]: { ok: false, msg: '测试失败，请检查网络' } }));
    }
  };

  if (loading || !show) return null;

  const canSkip = step >= 3;
  const isLastStep = step === STEPS.length - 1;

  return (
    <div className="fixed inset-0 z-50 bg-xy-bg flex flex-col overflow-hidden">
      {/* Header */}
      <div className="flex-none px-6 py-4 border-b border-xy-border bg-xy-surface">
        <div className="max-w-3xl mx-auto flex items-center justify-between">
          <h1 className="text-lg font-bold text-xy-text-primary">闲鱼管家 - 初始配置向导</h1>
          <button
            onClick={handleSkip}
            className="text-sm text-xy-text-muted hover:text-xy-text-secondary transition-colors"
          >
            {isLastStep ? '完成' : '跳过全部'}
          </button>
        </div>
      </div>

      {/* Progress */}
      <div className="flex-none px-6 py-3 bg-xy-surface border-b border-xy-border">
        <div className="max-w-3xl mx-auto flex items-center justify-center gap-1">
          {STEPS.map((s, i) => {
            const Icon = s.icon;
            const done = i < step;
            const active = i === step;
            return (
              <React.Fragment key={s.key}>
                <button
                  onClick={() => i < step && setStep(i)}
                  disabled={i > step}
                  className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                    active ? 'bg-xy-brand-50 text-xy-brand-600 border border-xy-brand-200' :
                    done ? 'text-green-600 hover:bg-green-50 cursor-pointer' :
                    'text-xy-text-muted'
                  }`}
                >
                  {done ? <Check className="w-4 h-4" /> : <Icon className="w-4 h-4" />}
                  <span className="hidden sm:inline">{s.label}</span>
                </button>
                {i < STEPS.length - 1 && (
                  <ChevronRight className={`w-3.5 h-3.5 shrink-0 ${done ? 'text-green-400' : 'text-xy-gray-300'}`} />
                )}
              </React.Fragment>
            );
          })}
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto px-6 py-8">
        <div className="max-w-2xl mx-auto">
          {step === 0 && <StepCookie data={data} setData={setData} errors={errors} />}
          {step === 1 && <StepAI data={data} setData={setData} errors={errors} testResult={testResults.ai} onTest={() => testConnection('ai')} />}
          {step === 2 && <StepXGJ data={data} setData={setData} errors={errors} testResult={testResults.xgj} onTest={() => testConnection('xgj')} />}
          {step === 3 && <StepCookieCloud data={data} setData={setData} />}
          {step === 4 && <StepNotify data={data} setData={setData} />}
          {step === 5 && <StepCategory data={data} setData={setData} />}
        </div>
      </div>

      {/* Footer */}
      <div className="flex-none px-6 py-4 border-t border-xy-border bg-xy-surface">
        <div className="max-w-2xl mx-auto flex items-center justify-between">
          <button
            onClick={() => { setStep(step - 1); setErrors({}); setTestResults({}); }}
            disabled={step === 0}
            className="flex items-center gap-1.5 px-4 py-2 text-sm font-medium text-xy-text-secondary hover:text-xy-text-primary disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
          >
            <ChevronLeft className="w-4 h-4" /> 上一步
          </button>
          <div className="flex items-center gap-3">
            {canSkip && !isLastStep && (
              <button
                onClick={handleSkip}
                className="flex items-center gap-1.5 px-4 py-2 text-sm font-medium text-xy-text-muted hover:text-xy-text-secondary transition-colors"
              >
                <SkipForward className="w-4 h-4" /> 跳过
              </button>
            )}
            {errors._save && (
              <span className="text-sm text-red-500">{errors._save}</span>
            )}
            <button
              onClick={handleNext}
              disabled={saving}
              className="flex items-center gap-1.5 px-6 py-2.5 bg-xy-brand-500 text-white text-sm font-medium rounded-xl hover:bg-xy-brand-600 disabled:opacity-50 transition-colors shadow-sm"
            >
              {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : null}
              {isLastStep ? '完成配置' : '保存并继续'}
              {!isLastStep && <ChevronRight className="w-4 h-4" />}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

/* ---------- Step Components ---------- */

interface StepProps {
  data: WizardData;
  setData: React.Dispatch<React.SetStateAction<WizardData>>;
  errors?: Record<string, string>;
  testResult?: { ok: boolean; msg: string } | null;
  onTest?: () => void;
}

function SectionTitle({ children }: { children: React.ReactNode }) {
  return <h2 className="text-xl font-bold text-xy-text-primary mb-1">{children}</h2>;
}

function SectionDesc({ children }: { children: React.ReactNode }) {
  return <p className="text-sm text-xy-text-secondary mb-6">{children}</p>;
}

function FieldLabel({ required, children }: { required?: boolean; children: React.ReactNode }) {
  return (
    <label className="block text-sm font-medium text-xy-text-primary mb-1">
      {children}
      {required && <span className="text-red-400 ml-0.5">*</span>}
    </label>
  );
}

function FieldHint({ children }: { children: React.ReactNode }) {
  return <p className="text-xs text-xy-text-muted mt-1">{children}</p>;
}

function FieldError({ msg }: { msg?: string }) {
  if (!msg) return null;
  return (
    <p className="text-xs text-red-500 mt-1 flex items-center gap-1">
      <AlertCircle className="w-3 h-3" /> {msg}
    </p>
  );
}

function TestResult({ result }: { result?: { ok: boolean; msg: string } | null }) {
  if (!result) return null;
  return (
    <span className={`text-sm flex items-center gap-1 ${result.ok ? 'text-green-600' : 'text-red-500'}`}>
      {result.ok ? <CheckCircle2 className="w-4 h-4" /> : <AlertCircle className="w-4 h-4" />}
      {result.msg}
    </span>
  );
}

function StepCookie({ data, setData, errors }: StepProps) {
  return (
    <div>
      <SectionTitle>第 1 步：获取闲鱼 Cookie</SectionTitle>
      <SectionDesc>
        系统需要 Cookie 来代替你操作闲鱼平台。
        <a href="https://goofish.com" target="_blank" rel="noopener noreferrer" className="text-xy-brand-500 hover:underline inline-flex items-center gap-0.5 ml-1">
          打开闲鱼 <ExternalLink className="w-3 h-3" />
        </a>
      </SectionDesc>

      <div className="bg-xy-gray-50 rounded-xl p-4 mb-6 text-sm text-xy-text-secondary">
        <p className="font-medium text-xy-text-primary mb-2">获取步骤：</p>
        <ol className="list-decimal list-inside space-y-1">
          <li>在浏览器打开 goofish.com 并登录</li>
          <li>按 F12 打开开发者工具</li>
          <li>切换到 Network 标签页</li>
          <li>刷新页面，点击任意请求</li>
          <li>在 Headers 中找到 Cookie 字段，复制全部内容</li>
        </ol>
      </div>

      <div className="space-y-4">
        <div>
          <FieldLabel required>XIANYU_COOKIE_1</FieldLabel>
          <textarea
            value={data.cookie1}
            onChange={e => setData(d => ({ ...d, cookie1: e.target.value }))}
            placeholder="从浏览器复制的完整 Cookie..."
            rows={4}
            className="w-full px-3 py-2 bg-xy-surface border border-xy-border rounded-xl text-sm text-xy-text-primary placeholder-xy-text-muted focus:outline-none focus:ring-2 focus:ring-xy-brand-200 focus:border-xy-brand-300 resize-none"
          />
          <FieldError msg={errors?.cookie1} />
        </div>
        <div>
          <FieldLabel>XIANYU_COOKIE_2（可选，多店铺）</FieldLabel>
          <textarea
            value={data.cookie2}
            onChange={e => setData(d => ({ ...d, cookie2: e.target.value }))}
            placeholder="可留空"
            rows={2}
            className="w-full px-3 py-2 bg-xy-surface border border-xy-border rounded-xl text-sm text-xy-text-primary placeholder-xy-text-muted focus:outline-none focus:ring-2 focus:ring-xy-brand-200 focus:border-xy-brand-300 resize-none"
          />
        </div>
      </div>
    </div>
  );
}

function StepAI({ data, setData, errors, testResult, onTest }: StepProps) {
  const provider = AI_PROVIDERS.find(p => p.id === data.ai.provider) || AI_PROVIDERS[0];

  const handleProviderChange = (id: string) => {
    const p = AI_PROVIDERS.find(x => x.id === id)!;
    setData(d => ({ ...d, ai: { ...d.ai, provider: id, model: p.model, base_url: p.base_url } }));
  };

  return (
    <div>
      <SectionTitle>第 2 步：配置 AI 服务</SectionTitle>
      <SectionDesc>AI 用于智能回复买家消息和生成商品文案。推荐使用百炼千问或 DeepSeek。</SectionDesc>

      <div className="space-y-4">
        <div>
          <FieldLabel required>AI 服务商</FieldLabel>
          <div className="grid grid-cols-3 gap-2">
            {AI_PROVIDERS.map(p => (
              <button
                key={p.id}
                onClick={() => handleProviderChange(p.id)}
                className={`px-4 py-3 rounded-xl border text-sm font-medium transition-colors ${
                  data.ai.provider === p.id
                    ? 'border-xy-brand-300 bg-xy-brand-50 text-xy-brand-600'
                    : 'border-xy-border bg-xy-surface text-xy-text-secondary hover:border-xy-brand-200'
                }`}
              >
                {p.label}
              </button>
            ))}
          </div>
        </div>
        <div>
          <FieldLabel required>API Key</FieldLabel>
          <input
            type="password"
            value={data.ai.api_key}
            onChange={e => setData(d => ({ ...d, ai: { ...d.ai, api_key: e.target.value } }))}
            placeholder={`输入 ${provider.label} API Key`}
            className="w-full px-3 py-2 bg-xy-surface border border-xy-border rounded-xl text-sm text-xy-text-primary placeholder-xy-text-muted focus:outline-none focus:ring-2 focus:ring-xy-brand-200 focus:border-xy-brand-300"
          />
          <FieldError msg={errors?.ai_key} />
        </div>
        <div>
          <FieldLabel>模型</FieldLabel>
          <input
            type="text"
            value={data.ai.model}
            onChange={e => setData(d => ({ ...d, ai: { ...d.ai, model: e.target.value } }))}
            placeholder={provider.model}
            className="w-full px-3 py-2 bg-xy-surface border border-xy-border rounded-xl text-sm text-xy-text-primary placeholder-xy-text-muted focus:outline-none focus:ring-2 focus:ring-xy-brand-200 focus:border-xy-brand-300"
          />
          <FieldHint>留空使用默认模型: {provider.model}</FieldHint>
        </div>
        <div>
          <FieldLabel>API 地址</FieldLabel>
          <input
            type="text"
            value={data.ai.base_url}
            onChange={e => setData(d => ({ ...d, ai: { ...d.ai, base_url: e.target.value } }))}
            placeholder={provider.base_url}
            className="w-full px-3 py-2 bg-xy-surface border border-xy-border rounded-xl text-sm text-xy-text-primary placeholder-xy-text-muted focus:outline-none focus:ring-2 focus:ring-xy-brand-200 focus:border-xy-brand-300"
          />
          <FieldHint>通常无需修改，使用自定义代理或中转时填写</FieldHint>
        </div>
        {onTest && (
          <div className="flex items-center gap-3">
            <button
              onClick={onTest}
              className="text-sm font-medium text-xy-brand-500 hover:text-xy-brand-600 transition-colors"
            >
              测试连接
            </button>
            <TestResult result={testResult} />
          </div>
        )}
      </div>
    </div>
  );
}

function StepXGJ({ data, setData, errors, testResult, onTest }: StepProps) {
  const updateXGJ = (key: string, value: any) => {
    setData(d => ({ ...d, xgj: { ...d.xgj, [key]: value } }));
  };

  return (
    <div>
      <SectionTitle>第 3 步：配置闲管家</SectionTitle>
      <SectionDesc>
        闲管家开放平台提供消息同步、商品管理和订单处理能力。
        <a href="https://open.goofish.pro" target="_blank" rel="noopener noreferrer" className="text-xy-brand-500 hover:underline inline-flex items-center gap-0.5 ml-1">
          开放平台 <ExternalLink className="w-3 h-3" />
        </a>
      </SectionDesc>

      {/* API Credentials */}
      <div className="bg-xy-gray-50 rounded-xl p-5 mb-6">
        <h3 className="text-sm font-bold text-xy-text-primary mb-4">API 凭证</h3>
        <div className="space-y-3">
          <div>
            <FieldLabel>接入模式</FieldLabel>
            <select
              value={data.xgj.mode}
              onChange={e => updateXGJ('mode', e.target.value)}
              className="w-full px-3 py-2 bg-xy-surface border border-xy-border rounded-xl text-sm text-xy-text-primary focus:outline-none focus:ring-2 focus:ring-xy-brand-200"
            >
              <option value="self_developed">自研应用</option>
              <option value="business">商务对接</option>
            </select>
            <FieldHint>个人或自有 ERP 选「自研应用」；代商家接入选「商务对接」</FieldHint>
          </div>
          <div>
            <FieldLabel required>AppKey</FieldLabel>
            <input
              type="text" value={data.xgj.app_key}
              onChange={e => updateXGJ('app_key', e.target.value)}
              placeholder="在闲管家开放平台创建应用后获取"
              className="w-full px-3 py-2 bg-xy-surface border border-xy-border rounded-xl text-sm text-xy-text-primary placeholder-xy-text-muted focus:outline-none focus:ring-2 focus:ring-xy-brand-200"
            />
            <FieldError msg={errors?.xgj_app_key} />
          </div>
          <div>
            <FieldLabel required>AppSecret</FieldLabel>
            <input
              type="password" value={data.xgj.app_secret}
              onChange={e => updateXGJ('app_secret', e.target.value)}
              placeholder="应用密钥，请妥善保管"
              className="w-full px-3 py-2 bg-xy-surface border border-xy-border rounded-xl text-sm text-xy-text-primary placeholder-xy-text-muted focus:outline-none focus:ring-2 focus:ring-xy-brand-200"
            />
            <FieldError msg={errors?.xgj_app_secret} />
          </div>
          {data.xgj.mode === 'business' && (
            <div>
              <FieldLabel required>Seller ID</FieldLabel>
              <input
                type="text" value={data.xgj.seller_id}
                onChange={e => updateXGJ('seller_id', e.target.value)}
                placeholder="商务对接模式下的商家标识"
                className="w-full px-3 py-2 bg-xy-surface border border-xy-border rounded-xl text-sm text-xy-text-primary placeholder-xy-text-muted focus:outline-none focus:ring-2 focus:ring-xy-brand-200"
              />
              <FieldError msg={errors?.xgj_seller_id} />
            </div>
          )}
          <div>
            <FieldLabel>API 网关</FieldLabel>
            <input
              type="text" value={data.xgj.base_url}
              onChange={e => updateXGJ('base_url', e.target.value)}
              placeholder="https://open.goofish.pro"
              className="w-full px-3 py-2 bg-xy-surface border border-xy-border rounded-xl text-sm text-xy-text-primary placeholder-xy-text-muted focus:outline-none focus:ring-2 focus:ring-xy-brand-200"
            />
            <FieldHint>默认无需修改</FieldHint>
          </div>
          {onTest && (
            <div className="flex items-center gap-3 pt-1">
              <button onClick={onTest} className="text-sm font-medium text-xy-brand-500 hover:text-xy-brand-600 transition-colors">
                测试连接
              </button>
              <TestResult result={testResult} />
            </div>
          )}
        </div>
      </div>

      {/* Product Defaults */}
      <div className="bg-xy-gray-50 rounded-xl p-5">
        <h3 className="text-sm font-bold text-xy-text-primary mb-1">商品默认值</h3>
        <p className="text-xs text-xy-text-muted mb-4">上架商品时的默认设置，可随时在配置页修改</p>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <FieldLabel>商品类型</FieldLabel>
            <select value={data.xgj.default_item_biz_type} onChange={e => updateXGJ('default_item_biz_type', e.target.value)}
              className="w-full px-3 py-2 bg-xy-surface border border-xy-border rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-xy-brand-200">
              {Object.entries(ITEM_BIZ_TYPES).map(([v, l]) => <option key={v} value={v}>{l}</option>)}
            </select>
          </div>
          <div>
            <FieldLabel>成色</FieldLabel>
            <select value={data.xgj.default_stuff_status} onChange={e => updateXGJ('default_stuff_status', e.target.value)}
              className="w-full px-3 py-2 bg-xy-surface border border-xy-border rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-xy-brand-200">
              {Object.entries(STUFF_STATUS).map(([v, l]) => <option key={v} value={v}>{l}</option>)}
            </select>
          </div>
          <div>
            <FieldLabel>默认价格(元)</FieldLabel>
            <input type="number" value={data.xgj.default_price} onChange={e => updateXGJ('default_price', parseFloat(e.target.value) || 0)}
              className="w-full px-3 py-2 bg-xy-surface border border-xy-border rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-xy-brand-200" />
          </div>
          <div>
            <FieldLabel>默认运费(元)</FieldLabel>
            <input type="number" value={data.xgj.default_express_fee} onChange={e => updateXGJ('default_express_fee', parseFloat(e.target.value) || 0)}
              className="w-full px-3 py-2 bg-xy-surface border border-xy-border rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-xy-brand-200" />
            <FieldHint>0 表示包邮</FieldHint>
          </div>
          <div>
            <FieldLabel>默认库存</FieldLabel>
            <input type="number" value={data.xgj.default_stock} onChange={e => updateXGJ('default_stock', parseInt(e.target.value) || 1)}
              className="w-full px-3 py-2 bg-xy-surface border border-xy-border rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-xy-brand-200" />
          </div>
          <div>
            <FieldLabel>闲鱼类目ID</FieldLabel>
            <input type="text" value={data.xgj.default_channel_cat_id} onChange={e => updateXGJ('default_channel_cat_id', e.target.value)}
              placeholder="可在配置页查询类目"
              className="w-full px-3 py-2 bg-xy-surface border border-xy-border rounded-xl text-sm placeholder-xy-text-muted focus:outline-none focus:ring-2 focus:ring-xy-brand-200" />
          </div>
          <div className="col-span-2">
            <FieldLabel>商家编码</FieldLabel>
            <input type="text" value={data.xgj.outer_id} onChange={e => updateXGJ('outer_id', e.target.value)}
              placeholder="可选，用于与你的 ERP 系统关联"
              className="w-full px-3 py-2 bg-xy-surface border border-xy-border rounded-xl text-sm placeholder-xy-text-muted focus:outline-none focus:ring-2 focus:ring-xy-brand-200" />
          </div>
          <div className="col-span-2">
            <FieldLabel>商品回调地址</FieldLabel>
            <input type="text" value={data.xgj.product_callback_url} onChange={e => updateXGJ('product_callback_url', e.target.value)}
              placeholder="可选，填入闲管家后台接收上架结果通知"
              className="w-full px-3 py-2 bg-xy-surface border border-xy-border rounded-xl text-sm placeholder-xy-text-muted focus:outline-none focus:ring-2 focus:ring-xy-brand-200" />
          </div>
        </div>
      </div>
    </div>
  );
}

function StepCookieCloud({ data, setData }: StepProps) {
  const update = (key: string, value: string) => {
    setData(d => ({ ...d, cookiecloud: { ...d.cookiecloud, [key]: value } }));
  };

  return (
    <div>
      <SectionTitle>第 4 步：CookieCloud（可选）</SectionTitle>
      <SectionDesc>
        CookieCloud 浏览器扩展可自动同步 Cookie，减少手动更新。
        <a href="https://microsoftedge.microsoft.com/addons/detail/cookiecloud/bffenpfpjikaeocaihdonmgnjjdddiign" target="_blank" rel="noopener noreferrer"
          className="text-xy-brand-500 hover:underline inline-flex items-center gap-0.5 ml-1">
          Edge 扩展商店 <ExternalLink className="w-3 h-3" />
        </a>
      </SectionDesc>

      <div className="bg-xy-gray-50 rounded-xl p-4 mb-6 text-sm text-xy-text-secondary">
        <p>本系统已内置 CookieCloud 服务端，安装浏览器扩展后配置 UUID 和密码即可自动同步。</p>
      </div>

      <div className="space-y-4">
        <div>
          <FieldLabel>CookieCloud 服务地址</FieldLabel>
          <input type="text" value={data.cookiecloud.cookie_cloud_host} onChange={e => update('cookie_cloud_host', e.target.value)}
            placeholder="留空使用内置服务"
            className="w-full px-3 py-2 bg-xy-surface border border-xy-border rounded-xl text-sm text-xy-text-primary placeholder-xy-text-muted focus:outline-none focus:ring-2 focus:ring-xy-brand-200" />
          <FieldHint>留空时自动使用内置服务端</FieldHint>
        </div>
        <div>
          <FieldLabel>UUID</FieldLabel>
          <input type="text" value={data.cookiecloud.cookie_cloud_uuid} onChange={e => update('cookie_cloud_uuid', e.target.value)}
            placeholder="在浏览器扩展中生成"
            className="w-full px-3 py-2 bg-xy-surface border border-xy-border rounded-xl text-sm text-xy-text-primary placeholder-xy-text-muted focus:outline-none focus:ring-2 focus:ring-xy-brand-200" />
        </div>
        <div>
          <FieldLabel>密码</FieldLabel>
          <input type="password" value={data.cookiecloud.cookie_cloud_password} onChange={e => update('cookie_cloud_password', e.target.value)}
            placeholder="扩展中的加密密码"
            className="w-full px-3 py-2 bg-xy-surface border border-xy-border rounded-xl text-sm text-xy-text-primary placeholder-xy-text-muted focus:outline-none focus:ring-2 focus:ring-xy-brand-200" />
        </div>
      </div>
    </div>
  );
}

function StepNotify({ data, setData }: StepProps) {
  const update = (key: string, value: any) => {
    setData(d => ({ ...d, notifications: { ...d.notifications, [key]: value } }));
  };

  return (
    <div>
      <SectionTitle>第 5 步：告警通知（可选）</SectionTitle>
      <SectionDesc>配置飞书或企业微信群机器人，接收 Cookie 过期、订单异常等重要事件推送。</SectionDesc>

      <div className="space-y-6">
        {/* Feishu */}
        <div className="bg-xy-gray-50 rounded-xl p-5">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-sm font-bold text-xy-text-primary">飞书机器人</h3>
            <label className="relative inline-flex items-center cursor-pointer">
              <input type="checkbox" checked={data.notifications.feishu_enabled}
                onChange={e => update('feishu_enabled', e.target.checked)} className="sr-only peer" />
              <div className="w-9 h-5 bg-xy-gray-200 peer-focus:ring-2 peer-focus:ring-xy-brand-200 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-xy-brand-500"></div>
            </label>
          </div>
          {data.notifications.feishu_enabled && (
            <div>
              <FieldLabel>Webhook URL</FieldLabel>
              <input type="text" value={data.notifications.feishu_webhook}
                onChange={e => update('feishu_webhook', e.target.value)}
                placeholder="https://open.feishu.cn/open-apis/bot/v2/hook/xxx"
                className="w-full px-3 py-2 bg-xy-surface border border-xy-border rounded-xl text-sm text-xy-text-primary placeholder-xy-text-muted focus:outline-none focus:ring-2 focus:ring-xy-brand-200" />
            </div>
          )}
        </div>

        {/* WeChat Work */}
        <div className="bg-xy-gray-50 rounded-xl p-5">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-sm font-bold text-xy-text-primary">企业微信机器人</h3>
            <label className="relative inline-flex items-center cursor-pointer">
              <input type="checkbox" checked={data.notifications.wechat_enabled}
                onChange={e => update('wechat_enabled', e.target.checked)} className="sr-only peer" />
              <div className="w-9 h-5 bg-xy-gray-200 peer-focus:ring-2 peer-focus:ring-xy-brand-200 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-xy-brand-500"></div>
            </label>
          </div>
          {data.notifications.wechat_enabled && (
            <div>
              <FieldLabel>Webhook URL</FieldLabel>
              <input type="text" value={data.notifications.wechat_webhook}
                onChange={e => update('wechat_webhook', e.target.value)}
                placeholder="https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=xxx"
                className="w-full px-3 py-2 bg-xy-surface border border-xy-border rounded-xl text-sm text-xy-text-primary placeholder-xy-text-muted focus:outline-none focus:ring-2 focus:ring-xy-brand-200" />
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function StepCategory({ data, setData }: StepProps) {
  return (
    <div>
      <SectionTitle>第 6 步：选择店铺品类</SectionTitle>
      <SectionDesc>选择你的主营品类，系统将据此调整商品管理和上架模板。可随时在顶部导航切换。</SectionDesc>

      <div className="grid grid-cols-2 gap-3">
        {Object.entries(CATEGORY_META).map(([key, meta]) => (
          <button
            key={key}
            onClick={() => setData(d => ({ ...d, storeCategory: key }))}
            className={`flex items-start gap-3 p-4 rounded-xl border text-left transition-colors ${
              data.storeCategory === key
                ? 'border-xy-brand-300 bg-xy-brand-50 ring-1 ring-xy-brand-200'
                : 'border-xy-border bg-xy-surface hover:border-xy-brand-200'
            }`}
          >
            <span className="text-2xl mt-0.5">{meta.icon}</span>
            <div>
              <p className={`font-medium ${data.storeCategory === key ? 'text-xy-brand-600' : 'text-xy-text-primary'}`}>{meta.label}</p>
              <p className="text-xs text-xy-text-muted mt-0.5">{meta.desc}</p>
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}
