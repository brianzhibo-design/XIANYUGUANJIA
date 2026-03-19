import { useState, useEffect, useCallback } from 'react';
import { api } from '../api/index';
import { saveSystemConfig } from '../api/config';

interface IntentRule {
  name: string;
  keywords: string[];
  reply: string;
  patterns?: string[];
  priority: number;
  categories: string[];
  phase: string;
  needs_human?: boolean;
  human_reason?: string;
  skip_reply?: boolean;
  source: 'builtin' | 'custom' | 'keyword' | 'overridden';
}

const EMPTY_RULE: Omit<IntentRule, 'source'> = {
  name: '',
  keywords: [],
  reply: '',
  priority: 50,
  categories: [],
  phase: 'presale',
  needs_human: false,
  skip_reply: false,
};

const PHASE_OPTIONS = [
  { value: '', label: '无' },
  { value: 'presale', label: '售前' },
  { value: 'aftersale', label: '售后' },
  { value: 'checkout', label: '下单' },
  { value: 'system', label: '系统' },
];

const CATEGORY_OPTIONS = [
  { value: 'express', label: '快递' },
  { value: 'virtual_goods', label: '虚拟商品' },
  { value: 'ticketing', label: '票务' },
];

const SOURCE_LABELS: Record<string, { label: string; className: string }> = {
  builtin: { label: '内置', className: 'bg-blue-50 text-blue-600' },
  custom: { label: '自定义', className: 'bg-green-50 text-green-600' },
  keyword: { label: '简易', className: 'bg-amber-50 text-amber-600' },
  overridden: { label: '已覆盖', className: 'bg-gray-100 text-gray-400 line-through' },
};

const PHASE_LABELS: Record<string, { label: string; className: string }> = {
  presale: { label: '售前', className: 'bg-emerald-50 text-emerald-600' },
  aftersale: { label: '售后', className: 'bg-rose-50 text-rose-600' },
  checkout: { label: '下单', className: 'bg-violet-50 text-violet-600' },
  system: { label: '系统', className: 'bg-gray-50 text-gray-500' },
};

interface EditModalProps {
  rule: Omit<IntentRule, 'source'>;
  isNew: boolean;
  onSave: (rule: Omit<IntentRule, 'source'>) => void;
  onClose: () => void;
}

function EditModal({ rule, isNew, onSave, onClose }: EditModalProps) {
  const [form, setForm] = useState({ ...rule });
  const [keywordInput, setKeywordInput] = useState('');

  const addKeyword = () => {
    const kw = keywordInput.trim();
    if (kw && !form.keywords.includes(kw)) {
      setForm({ ...form, keywords: [...form.keywords, kw] });
    }
    setKeywordInput('');
  };

  const removeKeyword = (idx: number) => {
    setForm({ ...form, keywords: form.keywords.filter((_, i) => i !== idx) });
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.name.trim() || form.keywords.length === 0) return;
    onSave(form);
  };

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4" onClick={onClose}>
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-lg max-h-[90vh] overflow-y-auto" onClick={e => e.stopPropagation()}>
        <div className="px-6 py-4 border-b border-gray-100">
          <h3 className="text-lg font-semibold text-gray-900">{isNew ? '新增规则' : '编辑规则'}</h3>
        </div>
        <form onSubmit={handleSubmit} className="px-6 py-4 space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">规则名称</label>
            <input
              className="xy-input px-3 py-2 w-full text-sm"
              value={form.name}
              onChange={e => setForm({ ...form, name: e.target.value })}
              placeholder="如：express_my_rule"
              required
              disabled={!isNew}
            />
            {!isNew && <p className="text-[11px] text-gray-400 mt-1">规则名称不可修改（用于覆盖内置规则时需同名）</p>}
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">触发关键词</label>
            <div className="flex gap-2">
              <input
                className="xy-input px-3 py-2 flex-1 text-sm"
                value={keywordInput}
                onChange={e => setKeywordInput(e.target.value)}
                onKeyDown={e => { if (e.key === 'Enter') { e.preventDefault(); addKeyword(); } }}
                placeholder="输入关键词后回车"
              />
              <button type="button" onClick={addKeyword} className="px-3 py-2 bg-xy-primary text-white rounded-lg text-sm hover:opacity-90 transition-opacity">添加</button>
            </div>
            <div className="flex flex-wrap gap-1.5 mt-2">
              {form.keywords.map((kw, i) => (
                <span key={i} className="inline-flex items-center gap-1 px-2 py-0.5 bg-blue-50 text-blue-700 rounded-full text-xs">
                  {kw}
                  <button type="button" onClick={() => removeKeyword(i)} className="text-blue-400 hover:text-blue-600">&times;</button>
                </span>
              ))}
              {form.keywords.length === 0 && <span className="text-xs text-gray-400">至少添加一个关键词</span>}
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">回复内容</label>
            <textarea
              className="xy-input px-3 py-2 w-full h-24 resize-none text-sm"
              value={form.reply}
              onChange={e => setForm({ ...form, reply: e.target.value })}
              placeholder="买家触发关键词后的自动回复"
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">优先级</label>
              <input
                type="number"
                className="xy-input px-3 py-2 w-full text-sm"
                value={form.priority}
                onChange={e => setForm({ ...form, priority: Math.max(1, Math.min(100, parseInt(e.target.value) || 50)) })}
                min={1}
                max={100}
              />
              <p className="text-[11px] text-gray-400 mt-0.5">1-100，数字越小优先级越高</p>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">阶段</label>
              <select
                className="xy-input px-3 py-2 w-full text-sm"
                value={form.phase}
                onChange={e => setForm({ ...form, phase: e.target.value })}
              >
                {PHASE_OPTIONS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
              </select>
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">适用品类</label>
            <div className="flex gap-3">
              {CATEGORY_OPTIONS.map(o => (
                <label key={o.value} className="flex items-center gap-1.5 text-sm">
                  <input
                    type="checkbox"
                    checked={form.categories.includes(o.value)}
                    onChange={e => {
                      const cats = e.target.checked
                        ? [...form.categories, o.value]
                        : form.categories.filter(c => c !== o.value);
                      setForm({ ...form, categories: cats });
                    }}
                    className="rounded"
                  />
                  {o.label}
                </label>
              ))}
            </div>
            <p className="text-[11px] text-gray-400 mt-0.5">不选则对所有品类生效</p>
          </div>

          <div className="flex gap-6">
            <label className="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={form.needs_human || false}
                onChange={e => setForm({ ...form, needs_human: e.target.checked })}
                className="rounded"
              />
              需要转人工
            </label>
            <label className="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={form.skip_reply || false}
                onChange={e => setForm({ ...form, skip_reply: e.target.checked })}
                className="rounded"
              />
              静默跳过（不回复）
            </label>
          </div>

          <div className="flex justify-end gap-3 pt-2 border-t border-gray-100">
            <button type="button" onClick={onClose} className="px-4 py-2 text-sm text-gray-600 hover:bg-gray-50 rounded-lg transition-colors">取消</button>
            <button
              type="submit"
              disabled={!form.name.trim() || form.keywords.length === 0}
              className="px-4 py-2 text-sm bg-xy-primary text-white rounded-lg hover:opacity-90 transition-opacity disabled:opacity-40"
            >
              保存
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

interface SuggestedRule {
  name: string;
  keywords: string[];
  reply: string;
  priority: number;
  categories: string[];
  phase: string;
  _source_cluster_size?: number;
  _created_at?: number;
}

interface IntentRulesManagerProps {
  config: Record<string, any>;
  onConfigChange: (section: string, key: string, value: any) => void;
  onSave: () => Promise<void>;
}

export default function IntentRulesManager({ config, onConfigChange, onSave }: IntentRulesManagerProps) {
  const [rules, setRules] = useState<IntentRule[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [editingRule, setEditingRule] = useState<{ rule: Omit<IntentRule, 'source'>; isNew: boolean } | null>(null);
  const [saving, setSaving] = useState(false);
  const [filterSource, setFilterSource] = useState<string>('all');
  const [searchText, setSearchText] = useState('');
  const [testMessage, setTestMessage] = useState('');
  const [testResult, setTestResult] = useState<string>('');
  const [activeTab, setActiveTab] = useState<'rules' | 'suggestions'>('rules');
  const [suggestions, setSuggestions] = useState<SuggestedRule[]>([]);
  const [suggestionsLoading, setSuggestionsLoading] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);

  const fetchRules = useCallback(async () => {
    try {
      setLoading(true);
      const res = await api.get('/intent-rules');
      if (res.data?.ok && Array.isArray(res.data.rules)) {
        setRules(res.data.rules);
      }
    } catch (e: any) {
      setError(e.message || '加载规则失败');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchRules(); }, [fetchRules]);

  const fetchSuggestions = useCallback(async () => {
    setSuggestionsLoading(true);
    try {
      const res = await api.get('/intent-rules/suggestions');
      if (res.data?.ok) {
        setSuggestions(res.data.suggestions || []);
      }
    } catch {
      // ignore
    } finally {
      setSuggestionsLoading(false);
    }
  }, []);

  useEffect(() => {
    if (activeTab === 'suggestions') fetchSuggestions();
  }, [activeTab, fetchSuggestions]);

  const handleAnalyze = async () => {
    setAnalyzing(true);
    try {
      const res = await api.post('/intent-rules/analyze');
      if (res.data?.ok) {
        setSuggestions(res.data.suggestions || []);
      }
    } catch {
      setError('分析失败');
    } finally {
      setAnalyzing(false);
    }
  };

  const handleAdopt = async (name: string) => {
    if (!confirm(`采纳规则「${name}」？`)) return;
    try {
      await api.post(`/intent-rules/suggestions/${encodeURIComponent(name)}/adopt`);
      setSuggestions(prev => prev.filter(s => s.name !== name));
      await fetchRules();
    } catch {
      setError('采纳失败');
    }
  };

  const handleReject = async (name: string) => {
    try {
      await api.post(`/intent-rules/suggestions/${encodeURIComponent(name)}/reject`);
      setSuggestions(prev => prev.filter(s => s.name !== name));
    } catch {
      setError('拒绝失败');
    }
  };

  const customRules: Omit<IntentRule, 'source'>[] = (config.auto_reply?.custom_intent_rules || []);

  const handleSaveRule = async (rule: Omit<IntentRule, 'source'>) => {
    setSaving(true);
    try {
      const updated = [...customRules.filter(r => r.name !== rule.name), rule];
      onConfigChange('auto_reply', 'custom_intent_rules', updated);
      await saveSystemConfig({ auto_reply: { ...config.auto_reply, custom_intent_rules: updated } });
      setEditingRule(null);
      await fetchRules();
    } catch (e: any) {
      setError(e.message || '保存失败');
    } finally {
      setSaving(false);
    }
  };

  const handleDeleteRule = async (name: string) => {
    if (!confirm(`确定删除规则「${name}」？`)) return;
    setSaving(true);
    try {
      const updated = customRules.filter(r => r.name !== name);
      onConfigChange('auto_reply', 'custom_intent_rules', updated);
      await saveSystemConfig({ auto_reply: { ...config.auto_reply, custom_intent_rules: updated } });
      await fetchRules();
    } catch (e: any) {
      setError(e.message || '删除失败');
    } finally {
      setSaving(false);
    }
  };

  const handleOverrideBuiltin = (rule: IntentRule) => {
    setEditingRule({
      rule: {
        name: rule.name,
        keywords: [...(rule.keywords || [])],
        reply: rule.reply || '',
        priority: rule.priority || 50,
        categories: [...(rule.categories || [])],
        phase: rule.phase || '',
        needs_human: rule.needs_human,
        skip_reply: rule.skip_reply,
      },
      isNew: false,
    });
  };

  const handleTestMessage = async () => {
    if (!testMessage.trim()) return;
    try {
      const res = await api.post('/test-reply', { message: testMessage });
      const data = res.data;
      if (data.matched_rule) {
        setTestResult(`匹配规则: ${data.matched_rule}\n回复: ${data.reply || '(静默跳过)'}`);
      } else {
        setTestResult(`未匹配规则，走默认回复\n回复: ${data.reply || ''}`);
      }
    } catch {
      setTestResult('测试失败');
    }
  };

  const filtered = rules.filter(r => {
    if (filterSource !== 'all' && r.source !== filterSource) return false;
    if (searchText) {
      const q = searchText.toLowerCase();
      return (r.name || '').toLowerCase().includes(q)
        || (r.keywords || []).some(k => k.toLowerCase().includes(q))
        || (r.reply || '').toLowerCase().includes(q);
    }
    return true;
  });

  const sortedRules = [...filtered].sort((a, b) => a.priority - b.priority);

  if (loading) {
    return <div className="text-center py-8 text-sm text-gray-400">加载规则中...</div>;
  }

  return (
    <div className="space-y-4">
      {error && (
        <div className="p-3 bg-red-50 text-red-600 text-sm rounded-lg flex items-center justify-between">
          {error}
          <button onClick={() => setError('')} className="text-red-400 hover:text-red-600">&times;</button>
        </div>
      )}

      {/* Tab Switcher */}
      <div className="flex gap-1 bg-xy-gray-50 p-1 rounded-xl w-fit">
        <button
          onClick={() => setActiveTab('rules')}
          className={`px-4 py-1.5 rounded-lg text-sm transition-colors ${activeTab === 'rules' ? 'bg-white shadow-sm font-medium text-xy-primary' : 'text-gray-500 hover:text-gray-700'}`}
        >
          意图规则
        </button>
        <button
          onClick={() => setActiveTab('suggestions')}
          className={`px-4 py-1.5 rounded-lg text-sm transition-colors flex items-center gap-1.5 ${activeTab === 'suggestions' ? 'bg-white shadow-sm font-medium text-xy-primary' : 'text-gray-500 hover:text-gray-700'}`}
        >
          建议规则
          {suggestions.length > 0 && (
            <span className="px-1.5 py-0.5 bg-amber-100 text-amber-700 text-[10px] rounded-full">{suggestions.length}</span>
          )}
        </button>
      </div>

      {/* Rules Tab */}
      {activeTab === 'rules' && (
      <div className="flex flex-wrap items-center gap-3">
        <input
          className="xy-input px-3 py-1.5 text-sm flex-1 min-w-[200px]"
          placeholder="搜索规则名称/关键词/回复..."
          value={searchText}
          onChange={e => setSearchText(e.target.value)}
        />
        <select
          className="xy-input px-3 py-1.5 text-sm"
          value={filterSource}
          onChange={e => setFilterSource(e.target.value)}
        >
          <option value="all">全部来源</option>
          <option value="builtin">内置</option>
          <option value="custom">自定义</option>
          <option value="keyword">简易</option>
          <option value="overridden">已覆盖</option>
        </select>
        <button
          onClick={() => setEditingRule({ rule: { ...EMPTY_RULE }, isNew: true })}
          className="px-4 py-1.5 bg-xy-primary text-white rounded-lg text-sm hover:opacity-90 transition-opacity flex items-center gap-1"
        >
          <span className="text-lg leading-none">+</span> 新增规则
        </button>
      </div>

      {/* Stats */}
      <div className="flex gap-4 text-xs text-gray-500">
        <span>共 {rules.length} 条规则</span>
        <span>内置 {rules.filter(r => r.source === 'builtin').length}</span>
        <span>自定义 {rules.filter(r => r.source === 'custom').length}</span>
        <span>简易 {rules.filter(r => r.source === 'keyword').length}</span>
      </div>

      {/* Rules Table */}
      <div className="border border-xy-border rounded-xl overflow-hidden divide-y divide-xy-border">
        {sortedRules.length === 0 ? (
          <div className="p-6 text-center text-sm text-gray-400">没有匹配的规则</div>
        ) : (
          sortedRules.map((rule, i) => {
            const sourceInfo = SOURCE_LABELS[rule.source] || SOURCE_LABELS.builtin;
            const phaseInfo = rule.phase ? PHASE_LABELS[rule.phase] : null;
            const isCustom = rule.source === 'custom';
            const isBuiltin = rule.source === 'builtin';
            const isOverridden = rule.source === 'overridden';

            return (
              <div key={`${rule.name}-${i}`} className={`p-3.5 hover:bg-xy-gray-50 transition-colors ${isOverridden ? 'opacity-50' : ''}`}>
                <div className="flex items-start gap-3">
                  <div className="flex-shrink-0 flex flex-col items-start gap-1 w-24">
                    <span className={`px-2 py-0.5 rounded-full text-[11px] font-medium ${sourceInfo.className}`}>{sourceInfo.label}</span>
                    {phaseInfo && <span className={`px-1.5 py-0.5 rounded text-[10px] font-medium ${phaseInfo.className}`}>{phaseInfo.label}</span>}
                    <span className="text-[10px] text-gray-400">P{rule.priority}</span>
                    {rule.needs_human && <span className="px-1.5 py-0.5 rounded bg-rose-50 text-rose-600 text-[10px] font-medium">转人工</span>}
                    {rule.skip_reply && <span className="px-1.5 py-0.5 rounded bg-gray-100 text-gray-500 text-[10px] font-medium">静默</span>}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-xs font-mono text-gray-500 mb-1">{rule.name}</p>
                    <div className="flex flex-wrap gap-1 mb-1.5">
                      {(rule.keywords || []).map((kw, ki) => (
                        <span key={ki} className="px-1.5 py-0.5 bg-blue-50 text-blue-700 rounded text-[11px]">{kw}</span>
                      ))}
                    </div>
                    <p className="text-sm text-xy-text-primary line-clamp-2">{rule.reply || '(空回复)'}</p>
                    {(rule.categories || []).length > 0 && (
                      <div className="flex gap-1 mt-1">
                        {(rule.categories || []).map(c => (
                          <span key={c} className="px-1.5 py-0.5 bg-orange-50 text-orange-600 text-[10px] rounded">{c}</span>
                        ))}
                      </div>
                    )}
                  </div>
                  <div className="flex-shrink-0 flex flex-col gap-1">
                    {isCustom && (
                      <>
                        <button
                          onClick={() => setEditingRule({ rule: { ...rule }, isNew: false })}
                          className="px-2.5 py-1 text-[11px] text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
                        >
                          编辑
                        </button>
                        <button
                          onClick={() => handleDeleteRule(rule.name)}
                          className="px-2.5 py-1 text-[11px] text-red-500 hover:bg-red-50 rounded-lg transition-colors"
                          disabled={saving}
                        >
                          删除
                        </button>
                      </>
                    )}
                    {isBuiltin && (
                      <button
                        onClick={() => handleOverrideBuiltin(rule)}
                        className="px-2.5 py-1 text-[11px] text-amber-600 hover:bg-amber-50 rounded-lg transition-colors"
                      >
                        覆盖
                      </button>
                    )}
                    {isOverridden && (
                      <span className="px-2.5 py-1 text-[10px] text-gray-400">已被覆盖</span>
                    )}
                  </div>
                </div>
              </div>
            );
          })
        )}
      </div>

      {/* Test Area */}
      <div className="p-4 bg-xy-gray-50 rounded-xl space-y-2">
        <p className="text-sm font-medium text-gray-700">消息测试</p>
        <div className="flex gap-2">
          <input
            className="xy-input px-3 py-1.5 flex-1 text-sm"
            placeholder="输入买家消息测试匹配..."
            value={testMessage}
            onChange={e => setTestMessage(e.target.value)}
            onKeyDown={e => { if (e.key === 'Enter') handleTestMessage(); }}
          />
          <button
            onClick={handleTestMessage}
            className="px-4 py-1.5 bg-xy-primary text-white rounded-lg text-sm hover:opacity-90 transition-opacity"
          >
            测试
          </button>
        </div>
        {testResult && (
          <pre className="text-xs text-gray-600 bg-white p-3 rounded-lg whitespace-pre-wrap border border-gray-100">{testResult}</pre>
        )}
      </div>

      {/* Priority Guide */}
      <div className="p-3 bg-blue-50/60 rounded-lg border border-blue-200/50 text-xs text-blue-600 space-y-1">
        <p className="font-medium text-blue-700">优先级说明</p>
        <p>1. 简易快捷回复（优先级 30，最高）</p>
        <p>2. 自定义规则（按设置的优先级）</p>
        <p>3. 内置规则（优先级 45-100）</p>
        <p>4. 通用报价引导模板（兜底）</p>
        <p className="text-amber-600 mt-1">保存后自动生效，无需重启服务</p>
      </div>
      )}

      {/* Suggestions Tab */}
      {activeTab === 'suggestions' && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <p className="text-sm text-gray-500">
              {suggestions.length > 0
                ? `基于未匹配消息生成 ${suggestions.length} 条建议规则`
                : '暂无建议规则，请先分析未匹配消息'}
            </p>
            <button
              onClick={handleAnalyze}
              disabled={analyzing}
              className="px-4 py-1.5 bg-amber-500 text-white rounded-lg text-sm hover:bg-amber-600 transition-colors disabled:opacity-50 flex items-center gap-1.5"
            >
              {analyzing ? '分析中...' : '分析未匹配消息'}
            </button>
          </div>

          {suggestionsLoading ? (
            <div className="text-center py-8 text-sm text-gray-400">加载中...</div>
          ) : suggestions.length === 0 ? (
            <div className="p-6 text-center text-sm text-gray-400 border border-dashed border-gray-200 rounded-xl">
              暂无建议。点击「分析未匹配消息」从 data/unmatched_messages.jsonl 生成规则建议。
            </div>
          ) : (
            <div className="border border-xy-border rounded-xl overflow-hidden divide-y divide-xy-border">
              {suggestions.map((s, i) => (
                <div key={`${s.name}-${i}`} className="p-3.5 hover:bg-xy-gray-50 transition-colors">
                  <div className="flex items-start gap-3">
                    <div className="flex-1 min-w-0">
                      <p className="text-xs font-mono text-gray-500 mb-1">{s.name}</p>
                      <div className="flex flex-wrap gap-1 mb-1.5">
                        {(s.keywords || []).map((kw, ki) => (
                          <span key={ki} className="px-1.5 py-0.5 bg-blue-50 text-blue-700 rounded text-[11px]">{kw}</span>
                        ))}
                      </div>
                      <p className="text-sm text-xy-text-primary line-clamp-2">{s.reply || '(空回复)'}</p>
                      <div className="flex gap-2 mt-1.5 text-[10px] text-gray-400">
                        <span>优先级 {s.priority}</span>
                        {s._source_cluster_size && <span>聚类 {s._source_cluster_size} 条消息</span>}
                      </div>
                    </div>
                    <div className="flex-shrink-0 flex flex-col gap-1">
                      <button
                        onClick={() => handleAdopt(s.name)}
                        className="px-2.5 py-1 text-[11px] text-green-600 hover:bg-green-50 rounded-lg transition-colors"
                      >
                        采纳
                      </button>
                      <button
                        onClick={() => handleReject(s.name)}
                        className="px-2.5 py-1 text-[11px] text-gray-400 hover:bg-gray-100 rounded-lg transition-colors"
                      >
                        忽略
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {editingRule && (
        <EditModal
          rule={editingRule.rule}
          isNew={editingRule.isNew}
          onSave={handleSaveRule}
          onClose={() => setEditingRule(null)}
        />
      )}
    </div>
  );
}
