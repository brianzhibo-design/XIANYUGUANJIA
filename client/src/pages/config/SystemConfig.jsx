import React, { useState, useEffect, useCallback } from 'react';
import { getSystemConfig, getConfigSections, saveSystemConfig } from '../../api/config';
import { pyApi } from '../../api/index';
import toast from 'react-hot-toast';
import { Settings, Save, AlertCircle, RefreshCw, Send, Bell, Cookie, CheckCircle2, XCircle, ExternalLink, Info } from 'lucide-react';

const AI_PROVIDER_GUIDES = {
  qwen: {
    name: '百炼千问 (Qwen)',
    baseUrl: 'https://dashscope.aliyuncs.com/compatible-mode/v1',
    model: 'qwen-plus-latest',
    applyUrl: 'https://bailian.console.aliyun.com/',
    tip: '推荐。中文语境和电商营销文案表现最稳定，免费额度充足。',
  },
  glm: {
    name: '智谱 GLM',
    baseUrl: 'https://open.bigmodel.cn/api/paas/v4',
    model: 'glm-4-flash',
    applyUrl: 'https://open.bigmodel.cn/',
    tip: '免费版 GLM-4-Flash 速度快，适合轻量级自动回复。',
  },
  deepseek: {
    name: 'DeepSeek',
    baseUrl: 'https://api.deepseek.com/v1',
    model: 'deepseek-chat',
    applyUrl: 'https://platform.deepseek.com/',
    tip: '性价比高，长文本能力强，适合复杂商品描述场景。',
  },
  openai: {
    name: 'OpenAI',
    baseUrl: 'https://api.openai.com/v1',
    model: 'gpt-4o-mini',
    applyUrl: 'https://platform.openai.com/',
    tip: '需海外网络，英文能力最强，中文电商场景建议搭配 System Prompt 优化。',
  },
  moonshot: {
    name: 'Moonshot (Kimi)',
    baseUrl: 'https://api.moonshot.cn/v1',
    model: 'moonshot-v1-8k',
    applyUrl: 'https://platform.moonshot.cn/',
    tip: '国产 Kimi 模型，长文本理解能力好，适合商品详情分析。',
  },
  yi: {
    name: '零一万物 (Yi)',
    baseUrl: 'https://api.lingyiwanwu.com/v1',
    model: 'yi-lightning',
    applyUrl: 'https://platform.lingyiwanwu.com/',
    tip: 'Yi-Lightning 响应速度极快，电商场景性价比高。',
  },
};

export default function SystemConfig() {
  const [sections, setSections] = useState([]);
  const [config, setConfig] = useState({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [activeTab, setActiveTab] = useState('');

  const [cookieText, setCookieText] = useState('');
  const [cookieValidating, setCookieValidating] = useState(false);
  const [cookieResult, setCookieResult] = useState(null);
  const [currentCookieHealth, setCurrentCookieHealth] = useState(null);

  useEffect(() => {
    fetchConfig();
  }, []);

  const fetchConfig = async () => {
    setLoading(true);
    try {
      const [secRes, cfgRes] = await Promise.all([
        getConfigSections(),
        getSystemConfig()
      ]);
      
      if (secRes.data?.ok) {
        const secs = secRes.data.sections || [];
        const cookieSection = { key: 'cookie', name: 'Cookie 配置' };
        setSections([cookieSection, ...secs]);
        setActiveTab('cookie');
      }
      
      if (cfgRes.data?.ok) {
        setConfig(cfgRes.data.config || {});
      }

      try {
        const healthRes = await pyApi.get('/api/health/check');
        if (healthRes.data?.cookie) {
          setCurrentCookieHealth(healthRes.data.cookie);
        }
      } catch (_) {}
    } catch (e) {
      toast.error('加载配置失败');
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      const res = await saveSystemConfig(config);
      if (res.data?.ok) {
        toast.success('配置保存成功');
        setConfig(res.data.config || config);
      } else {
        toast.error(res.data?.error || '保存失败');
      }
    } catch (e) {
      toast.error('保存出错');
    } finally {
      setSaving(false);
    }
  };

  const [testingSend, setTestingSend] = useState(null);

  const handleChange = (sectionKey, fieldKey, value) => {
    setConfig(prev => ({
      ...prev,
      [sectionKey]: {
        ...(prev[sectionKey] || {}),
        [fieldKey]: value
      }
    }));
  };

  const handleTestNotification = async (channel) => {
    const notifyCfg = config.notifications || {};
    const webhookKey = channel === 'feishu' ? 'feishu_webhook' : 'wechat_webhook';
    const webhookUrl = notifyCfg[webhookKey] || '';
    if (!webhookUrl || webhookUrl.includes('****')) {
      toast.error('请先填写并保存 Webhook URL');
      return;
    }
    setTestingSend(channel);
    try {
      const res = await pyApi.post('/api/notifications/test', { channel, webhook_url: webhookUrl });
      if (res.data?.ok) {
        toast.success(channel === 'feishu' ? '飞书测试消息发送成功' : '企业微信测试消息发送成功');
      } else {
        toast.error(res.data?.error || '发送失败');
      }
    } catch (err) {
      toast.error('发送失败: ' + (err?.response?.data?.error || err.message));
    } finally {
      setTestingSend(null);
    }
  };

  const handleCookieValidate = useCallback(async () => {
    if (!cookieText.trim()) {
      toast.error('请先粘贴 Cookie');
      return;
    }
    setCookieValidating(true);
    setCookieResult(null);
    try {
      const res = await pyApi.post('/api/cookie/validate', { cookie: cookieText });
      setCookieResult(res.data);
    } catch (err) {
      setCookieResult({ ok: false, grade: 'F', message: err?.response?.data?.message || '验证失败' });
    } finally {
      setCookieValidating(false);
    }
  }, [cookieText]);

  const handleCookieSave = useCallback(async () => {
    if (!cookieText.trim()) return;
    setSaving(true);
    try {
      const res = await pyApi.post('/api/update-cookie', { cookie: cookieText });
      if (res.data?.success) {
        toast.success('Cookie 更新成功');
        setCookieResult({ ok: true, grade: res.data.cookie_grade || 'A', message: 'Cookie 已保存并生效' });
        setCurrentCookieHealth({ ok: true, message: '刚刚更新' });
      } else {
        toast.error(res.data?.error || '保存失败');
      }
    } catch (err) {
      toast.error('保存出错');
    } finally {
      setSaving(false);
    }
  }, [cookieText]);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[50vh]">
        <RefreshCw className="w-8 h-8 animate-spin text-xy-brand-500" />
      </div>
    );
  }

  const currentSection = sections.find(s => s.key === activeTab);
  const selectedProvider = config.ai?.provider || 'qwen';
  const providerGuide = AI_PROVIDER_GUIDES[selectedProvider];

  const renderCookieSection = () => (
    <div className="xy-card p-6 animate-in fade-in slide-in-from-right-4">
      <h2 className="text-lg font-bold text-xy-text-primary mb-6 pb-4 border-b border-xy-border">
        Cookie 配置
      </h2>

      <div className="space-y-6 max-w-2xl">
        <div className={`flex items-center gap-3 px-4 py-3 rounded-lg border ${
          currentCookieHealth?.ok 
            ? 'bg-green-50 border-green-200 text-green-800' 
            : 'bg-amber-50 border-amber-200 text-amber-800'
        }`}>
          {currentCookieHealth?.ok 
            ? <CheckCircle2 className="w-5 h-5 text-green-600" /> 
            : <AlertCircle className="w-5 h-5 text-amber-600" />}
          <div>
            <span className="font-medium">当前状态：</span>
            {currentCookieHealth?.ok ? '正常' : (currentCookieHealth?.message || '未配置或已过期')}
          </div>
        </div>

        <div>
          <label className="xy-label">粘贴 Cookie</label>
          <textarea
            className="xy-input px-3 py-2 h-32 font-mono text-xs"
            placeholder={'支持以下格式：\n1. HTTP Header: cookie2=xxx; sgcookie=yyy; ...\n2. JSON: [{"name":"cookie2","value":"xxx"}, ...]\n3. Netscape cookies.txt\n4. DevTools 表格复制'}
            value={cookieText}
            onChange={e => { setCookieText(e.target.value); setCookieResult(null); }}
          />
        </div>

        <div className="flex gap-3">
          <button
            onClick={handleCookieValidate}
            disabled={cookieValidating || !cookieText.trim()}
            className="flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-lg border border-xy-brand-300 text-xy-brand-700 bg-xy-brand-50 hover:bg-xy-brand-100 transition-colors disabled:opacity-50"
          >
            {cookieValidating ? <RefreshCw className="w-4 h-4 animate-spin" /> : <CheckCircle2 className="w-4 h-4" />}
            验证 Cookie
          </button>
          <button
            onClick={handleCookieSave}
            disabled={saving || !cookieText.trim()}
            className="xy-btn-primary flex items-center gap-2"
          >
            {saving ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
            保存并生效
          </button>
        </div>

        {cookieResult && (
          <div className={`px-4 py-3 rounded-lg border text-sm ${
            cookieResult.ok 
              ? 'bg-green-50 border-green-200 text-green-800' 
              : 'bg-red-50 border-red-200 text-red-800'
          }`}>
            <div className="flex items-center gap-2 mb-1">
              {cookieResult.ok ? <CheckCircle2 className="w-4 h-4" /> : <XCircle className="w-4 h-4" />}
              <span className="font-medium">
                评级: {cookieResult.grade} — {cookieResult.ok ? 'Cookie 有效' : 'Cookie 无效'}
              </span>
            </div>
            {cookieResult.message && <p className="ml-6">{cookieResult.message}</p>}
            {cookieResult.actions?.length > 0 && (
              <ul className="ml-6 mt-1 list-disc list-inside">
                {cookieResult.actions.map((a, i) => <li key={i}>{a}</li>)}
              </ul>
            )}
            {cookieResult.required_missing?.length > 0 && (
              <p className="ml-6 mt-1">缺少字段：{cookieResult.required_missing.join(', ')}</p>
            )}
          </div>
        )}
      </div>

      <div className="mt-8 bg-blue-50 border border-blue-200 p-4 rounded-lg text-blue-800 text-sm">
        <div className="flex items-start gap-3">
          <Info className="w-5 h-5 flex-shrink-0 mt-0.5 text-blue-600" />
          <div>
            <p className="font-medium mb-2">Cookie 获取指南</p>
            <ol className="list-decimal list-inside space-y-1 text-blue-700">
              <li>使用 Chrome 浏览器打开 <a href="https://www.goofish.com" target="_blank" rel="noreferrer" className="underline">闲鱼网页版</a> 并登录</li>
              <li>按 F12 打开开发者工具，切换到「Network / 网络」标签</li>
              <li>刷新页面，选择任意请求，在 Headers 中找到 Cookie 字段</li>
              <li>右键「Copy value」，粘贴到上方输入框</li>
            </ol>
            <p className="mt-2">也可在「账号管理」页面使用「自动获取」功能，系统支持浏览器数据库直读和扫码登录两种方式。</p>
          </div>
        </div>
      </div>
    </div>
  );

  return (
    <div className="xy-page max-w-5xl xy-enter">
      <div className="flex flex-col md:flex-row justify-between md:items-end gap-4 mb-6">
        <div>
          <h1 className="xy-title flex items-center gap-2">
            <Settings className="w-6 h-6 text-xy-brand-500" /> 系统与店铺配置
          </h1>
          <p className="xy-subtitle mt-1">管理 Cookie、AI 提供商、告警通知以及自动化核心设置</p>
        </div>
        {activeTab !== 'cookie' && (
          <button 
            onClick={handleSave} 
            disabled={saving}
            className="xy-btn-primary flex items-center gap-2"
          >
            {saving ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
            保存设置
          </button>
        )}
      </div>

      <div className="flex flex-col md:flex-row gap-6">
        <div className="md:w-64 flex-shrink-0">
          <div className="xy-card overflow-hidden">
            <div className="flex flex-col">
              {sections.map(sec => (
                <button
                  key={sec.key}
                  onClick={() => setActiveTab(sec.key)}
                  className={`text-left px-5 py-4 text-sm font-medium transition-colors border-l-4 ${
                    activeTab === sec.key 
                      ? 'border-l-xy-brand-500 bg-xy-brand-50 text-xy-brand-600' 
                      : 'border-l-transparent text-xy-text-secondary hover:bg-xy-gray-50'
                  }`}
                >
                  {sec.key === 'cookie' && <Cookie className="w-4 h-4 inline mr-2" />}
                  {sec.name}
                </button>
              ))}
            </div>
          </div>
        </div>

        <div className="flex-1">
          {activeTab === 'cookie' && renderCookieSection()}

          {currentSection && currentSection.key !== 'cookie' && (
            <div className="xy-card p-6 animate-in fade-in slide-in-from-right-4">
              <h2 className="text-lg font-bold text-xy-text-primary mb-6 pb-4 border-b border-xy-border">
                {currentSection.name}
              </h2>
              
              <div className="space-y-6 max-w-2xl">
                {currentSection.fields?.map(field => {
                  const sectionData = config[currentSection.key] || {};
                  const value = sectionData[field.key] !== undefined ? sectionData[field.key] : (field.default || '');

                  return (
                    <div key={field.key}>
                      <label className="xy-label flex items-center justify-between">
                        <span>
                          {field.label}
                          {field.required && <span className="text-red-500 ml-1">*</span>}
                        </span>
                      </label>
                      
                      {field.type === 'textarea' ? (
                        <textarea
                          className="xy-input px-3 py-2 h-24"
                          value={value}
                          placeholder={field.placeholder || ''}
                          onChange={(e) => handleChange(currentSection.key, field.key, e.target.value)}
                        />
                      ) : field.type === 'select' ? (
                        <select
                          className="xy-input px-3 py-2"
                          value={value}
                          onChange={(e) => handleChange(currentSection.key, field.key, e.target.value)}
                        >
                          {field.options?.map(opt => (
                            <option key={opt} value={opt}>{opt}</option>
                          ))}
                        </select>
                      ) : field.type === 'toggle' ? (
                        <button
                          className={`w-12 h-6 rounded-full transition-colors relative ${value ? 'bg-green-500' : 'bg-gray-300'}`}
                          onClick={() => handleChange(currentSection.key, field.key, !value)}
                        >
                          <div className={`absolute top-1 bg-white w-4 h-4 rounded-full transition-transform ${value ? 'left-7' : 'left-1'}`}></div>
                        </button>
                      ) : (
                        <input
                          type={field.type || 'text'}
                          className="xy-input px-3 py-2"
                          value={value}
                          placeholder={field.placeholder || ''}
                          onChange={(e) => handleChange(currentSection.key, field.key, e.target.value)}
                        />
                      )}
                    </div>
                  );
                })}
              </div>
              
              {currentSection.key === 'ai' && providerGuide && (
                <div className="mt-8 space-y-4">
                  <div className="bg-gradient-to-r from-blue-50 to-indigo-50 border border-blue-200 p-5 rounded-lg text-sm">
                    <h3 className="font-bold text-blue-900 mb-3 flex items-center gap-2">
                      <Info className="w-4 h-4" />
                      {providerGuide.name} 配置指南
                    </h3>
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
                    <a
                      href={providerGuide.applyUrl}
                      target="_blank"
                      rel="noreferrer"
                      className="inline-flex items-center gap-1 mt-3 text-blue-600 hover:text-blue-800 font-medium underline text-xs"
                    >
                      前往申请 API Key <ExternalLink className="w-3 h-3" />
                    </a>
                  </div>
                </div>
              )}

              {currentSection.key === 'notifications' && (
                <div className="mt-8 space-y-4">
                  <div className="bg-blue-50 border border-blue-200 p-4 rounded-lg flex items-start gap-3 text-blue-800 text-sm">
                    <Bell className="w-5 h-5 flex-shrink-0 mt-0.5 text-blue-600" />
                    <div>
                      <p className="font-medium mb-1">告警通知说明</p>
                      <p>配置后，以下事件将自动推送通知：Cookie 过期、Cookie 刷新、售后介入、发货失败、虚拟商品发码失败、人工接管等。</p>
                      <p className="mt-1">飞书：使用<strong>自定义机器人</strong>的 Webhook 地址。企业微信：使用<strong>群机器人</strong>的 Webhook 地址。</p>
                    </div>
                  </div>

                  <div className="flex gap-3">
                    {(config.notifications?.feishu_enabled) && (
                      <button
                        onClick={() => handleTestNotification('feishu')}
                        disabled={testingSend === 'feishu'}
                        className="flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-lg border border-blue-300 text-blue-700 bg-blue-50 hover:bg-blue-100 transition-colors disabled:opacity-50"
                      >
                        {testingSend === 'feishu' ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
                        测试飞书通知
                      </button>
                    )}
                    {(config.notifications?.wechat_enabled) && (
                      <button
                        onClick={() => handleTestNotification('wechat')}
                        disabled={testingSend === 'wechat'}
                        className="flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-lg border border-green-300 text-green-700 bg-green-50 hover:bg-green-100 transition-colors disabled:opacity-50"
                      >
                        {testingSend === 'wechat' ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
                        测试企业微信通知
                      </button>
                    )}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
