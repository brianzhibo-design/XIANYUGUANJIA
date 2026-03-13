import React, { useState, useEffect, useRef, useCallback } from 'react';
import { api } from '../../api/index';
import {
  Store, Settings, Power, PowerOff, ShieldAlert, RefreshCw, Zap, Loader2,
  CheckCircle, CheckCircle2, XCircle, Monitor, ClipboardPaste, Timer, Activity,
  ChevronDown, ChevronUp, Download, Plug, Upload, Filter, Info, AlertCircle,
  Shield, ShieldCheck, Save,
} from 'lucide-react';
import toast from 'react-hot-toast';
import { useNavigate } from 'react-router-dom';

const GRAB_STAGE_CONFIG: Record<string, { color: string; label: string }> = {
  idle: { color: 'text-xy-gray-500', label: '就绪' },
  reading_db: { color: 'text-blue-600', label: '方式一：读取浏览器数据库' },
  reading_profile: { color: 'text-blue-600', label: '方式二：读取 Chrome 登录态' },
  validating: { color: 'text-blue-600', label: '验证有效性' },
  login_required: { color: 'text-orange-600', label: '方式三：扫码登录' },
  waiting_login: { color: 'text-orange-600', label: '等待扫码登录' },
  saving: { color: 'text-blue-600', label: '保存中' },
  success: { color: 'text-green-600', label: '获取成功' },
  failed: { color: 'text-red-600', label: '获取失败' },
  cancelled: { color: 'text-xy-gray-500', label: '已取消' },
};

const RISK_LEVEL_CONFIG: Record<string, any> = {
  normal:  { label: '正常',     icon: ShieldCheck, bg: 'bg-green-50', border: 'border-green-200', text: 'text-green-800' },
  warning: { label: '风险预警', icon: Shield,      bg: 'bg-amber-50', border: 'border-amber-200', text: 'text-amber-800' },
  blocked: { label: '疑似封控', icon: ShieldAlert,  bg: 'bg-red-50',   border: 'border-red-200',   text: 'text-red-800' },
  unknown: { label: '未检测',   icon: Shield,      bg: 'bg-gray-50',  border: 'border-gray-200',  text: 'text-gray-600' },
};

const RECOVERY_STAGE_LABELS: Record<string, string> = {
  monitoring: '监控中',
  healthy: '健康',
  recover_triggered: '恢复已触发',
  waiting_reconnect: '等待重连',
  waiting_cookie_update: '等待 Cookie 更新',
  inactive: '服务未运行',
  token_error: 'Token 异常',
};

function getRecoveryGuide(riskLevel: string, recoveryStage: string, cookieCloudConfigured: boolean = false, sliderAutoSolve: boolean = false) {
  if (riskLevel === 'normal') return null;
  if (riskLevel === 'warning') {
    return {
      severity: 'warning',
      title: '风险预警',
      steps: [
        '系统检测到异常信号，建议密切观察',
        '提前准备新的 Cookie，以防需要更换',
        '如果自动回复功能正常，可暂时观察',
      ],
    };
  }
  if (riskLevel === 'blocked') {
    if (recoveryStage === 'recover_triggered' || recoveryStage === 'waiting_reconnect') {
      return {
        severity: 'info',
        title: '正在恢复中',
        steps: [
          '系统已自动触发恢复流程，请等待 20-30 秒',
          '如果超过 1 分钟仍未恢复，请尝试更新 Cookie',
          '更新后系统会自动再次尝试恢复连接',
        ],
      };
    }
    if (sliderAutoSolve) {
      return {
        severity: 'warning',
        title: '自动滑块恢复中',
        steps: [
          '系统正在自动尝试滑块验证，请稍候...',
          '如自动验证失败，会弹出浏览器窗口，请手动完成滑块拖动',
          ...(cookieCloudConfigured
            ? ['CookieCloud 即时同步已启用，验证后秒级自动恢复']
            : ['验证后请手动复制 Cookie 粘贴保存']),
        ],
      };
    }
    if (cookieCloudConfigured) {
      return {
        severity: 'error',
        title: '完成滑块验证即可恢复',
        steps: [
          '在浏览器打开 goofish.com/im（闲鱼消息页）',
          '完成页面上的滑块验证',
          '在 CookieCloud 扩展中点「手动同步」立即生效',
          '系统将秒级自动恢复（CookieCloud 即时同步已启用）',
          '提示：在「系统设置 → 集成服务 → 风控滑块自动验证」中开启可实现全自动恢复',
        ],
      };
    }
    return {
      severity: 'error',
      title: '需要手动干预',
      steps: [
        '在浏览器打开 goofish.com/im 完成滑块验证',
        '手动复制 Cookie（F12 → Network → 复制 Cookie）并粘贴保存',
        '系统会自动尝试恢复连接',
        '提示：配置 CookieCloud 可实现滑块验证后秒级自动恢复，无需手动复制',
        '提示：在「系统设置 → 集成服务 → 风控滑块自动验证」中开启可实现全自动恢复',
      ],
    };
  }
  return null;
}

function CollapsibleSection({ title, defaultOpen = true, children, icon, badge }: {
  title: string;
  defaultOpen?: boolean;
  children: React.ReactNode;
  icon?: React.ReactNode;
  badge?: React.ReactNode;
}) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div className="border border-xy-border rounded-xl overflow-hidden">
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center justify-between px-5 py-4 bg-xy-gray-50 hover:bg-xy-gray-100 transition-colors text-left"
        type="button"
      >
        <div className="flex items-center gap-2">
          {icon}
          <span className="font-bold text-xy-text-primary text-sm">{title}</span>
          {badge}
        </div>
        {open ? <ChevronUp className="w-4 h-4 text-xy-text-muted" /> : <ChevronDown className="w-4 h-4 text-xy-text-muted" />}
      </button>
      {open && <div className="px-5 py-5">{children}</div>}
    </div>
  );
}

export default function AccountList() {
  const navigate = useNavigate();

  const [loading, setLoading] = useState(true);
  const [accounts, setAccounts] = useState<any[]>([]);

  // Cookie management state
  const [cookieText, setCookieText] = useState('');
  const [cookieValidating, setCookieValidating] = useState(false);
  const [cookieResult, setCookieResult] = useState<any>(null);
  const [currentCookieHealth, setCurrentCookieHealth] = useState<any>(null);
  const [riskStatus, setRiskStatus] = useState<any>(null);
  const [saving, setSaving] = useState(false);

  // Auto grab
  const [grabbing, setGrabbing] = useState(false);
  const [grabProgress, setGrabProgress] = useState<any>(null);
  const eventSourceRef = useRef<EventSource | null>(null);

  // File upload
  const [cookieFileUploading, setCookieFileUploading] = useState(false);
  const [cookieFileResult, setCookieFileResult] = useState<any>(null);
  const [isDragging, setIsDragging] = useState(false);
  const cookieFileRef = useRef<HTMLInputElement>(null);

  // Plugin
  const [pluginGuideOpen, setPluginGuideOpen] = useState(false);
  const [pluginImporting, setPluginImporting] = useState(false);
  const pluginFileRef = useRef<HTMLInputElement>(null);

  // Auto refresh
  const [autoRefresh, setAutoRefresh] = useState<any>(null);
  const refreshTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const fetchAutoRefreshStatus = useCallback(async () => {
    try {
      const res = await api.get('/cookie/auto-refresh/status');
      setAutoRefresh(res.data);
    } catch { setAutoRefresh(null); }
  }, []);

  useEffect(() => {
    fetchAll();
    fetchAutoRefreshStatus();
    refreshTimerRef.current = setInterval(fetchAutoRefreshStatus, 30000);
    return () => {
      if (eventSourceRef.current) eventSourceRef.current.close();
      if (refreshTimerRef.current) clearInterval(refreshTimerRef.current);
    };
  }, [fetchAutoRefreshStatus]);

  const fetchAll = async () => {
    setLoading(true);
    try {
      const [cfgRes, healthRes, statusRes] = await Promise.all([
        api.get('/config'),
        api.get('/health/check').catch(() => null),
        api.get('/service-status').catch(() => null),
      ]);

      const cfg = cfgRes.data?.config || {};
      const xgj = cfg.xianguanjia || {};
      const configured = !!(xgj.app_key && xgj.app_secret && !String(xgj.app_key).includes('****'));
      setAccounts([{ id: 'default', name: '默认店铺', enabled: true, configured }]);

      if (healthRes?.data?.cookie) {
        setCurrentCookieHealth(healthRes.data.cookie);
      }
      if (statusRes?.data) {
        setRiskStatus({
          risk_control: statusRes.data.risk_control,
          recovery: statusRes.data.recovery,
          recovery_stage: statusRes.data.recovery_stage,
          token_error: statusRes.data.token_error,
          service_status: statusRes.data.service_status,
        });
      }
    } catch {
      setAccounts([{ id: 'default', name: '默认店铺', enabled: true, configured: false }]);
    } finally {
      setLoading(false);
    }
  };

  const toggleAutomation = async (currentStatus: boolean) => {
    try {
      const action = currentStatus ? 'stop' : 'start';
      await api.post('/module/control', { action, target: 'presales' });
      toast.success(`已${currentStatus ? '停用' : '启用'}自动化服务`);
      fetchAll();
    } catch { toast.error('操作失败'); }
  };

  // ─── Cookie handlers ───

  const handleCookieValidate = useCallback(async () => {
    if (!cookieText.trim()) { toast.error('请先粘贴 Cookie'); return; }
    setCookieValidating(true);
    setCookieResult(null);
    try {
      const res = await api.post('/cookie/validate', { cookie: cookieText });
      setCookieResult(res.data);
    } catch (err: any) {
      setCookieResult({ ok: false, grade: 'F', message: err?.response?.data?.message || '验证失败' });
    } finally { setCookieValidating(false); }
  }, [cookieText]);

  const handleCookieSave = useCallback(async () => {
    if (!cookieText.trim()) return;
    setSaving(true);
    try {
      const res = await api.post('/update-cookie', { cookie: cookieText });
      if (res.data?.success) {
        toast.success('Cookie 更新成功');
        setCookieResult({ ok: true, grade: res.data.cookie_grade || 'A', message: 'Cookie 已保存并生效' });
        setCurrentCookieHealth({ ok: true, message: '刚刚更新' });
      } else {
        toast.error(res.data?.error || '保存失败');
      }
    } catch { toast.error('保存出错'); }
    finally { setSaving(false); }
  }, [cookieText]);

  const handleAutoGrab = useCallback(async () => {
    setGrabbing(true);
    setGrabProgress({ stage: 'reading_db', message: '正在启动...', hint: '', progress: 0 });
    try {
      await api.post('/cookie/auto-grab');
    } catch (err: any) {
      if (err?.response?.status === 409) {
        toast.error('已有获取任务在运行');
      } else {
        toast.error('启动失败：' + (err.message || '未知错误'));
        setGrabbing(false);
        setGrabProgress(null);
        return;
      }
    }
    const es = new EventSource('/api/cookie/auto-grab/status');
    eventSourceRef.current = es;
    es.onmessage = (evt) => {
      try {
        const data = JSON.parse(evt.data);
        setGrabProgress(data);
        if (data.stage === 'done' || data.stage === 'success') {
          toast.success('Cookie 自动获取成功');
          setGrabbing(false);
          es.close();
          eventSourceRef.current = null;
          fetchAll();
        } else if (data.stage === 'error' || data.stage === 'failed' || data.stage === 'cancelled') {
          es.close();
          eventSourceRef.current = null;
          setGrabbing(false);
          if (data.stage === 'failed' || data.stage === 'error') {
            toast.error(`自动获取失败: ${data.error || data.message || ''}`);
          }
        }
      } catch {}
    };
    es.onerror = () => { es.close(); eventSourceRef.current = null; setGrabbing(false); };
  }, []);

  const handleCancelAutoGrab = useCallback(async () => {
    try { await api.post('/cookie/auto-grab/cancel'); } catch {}
    if (eventSourceRef.current) { eventSourceRef.current.close(); eventSourceRef.current = null; }
    setGrabbing(false);
    setGrabProgress(null);
    toast.success('已取消自动获取');
  }, []);

  const handleDownloadPlugin = useCallback(() => {
    window.open('/api/download-cookie-plugin', '_blank');
  }, []);

  const handlePluginFileImport = useCallback(async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files?.length) return;
    setPluginImporting(true);
    const formData = new FormData();
    Array.from(files).forEach(f => formData.append('file', f));
    try {
      const res = await api.post('/import-cookie-plugin', formData, { headers: { 'Content-Type': 'multipart/form-data' } });
      if (res.data?.success) {
        toast.success('Cookie 导入成功');
        setCurrentCookieHealth({ ok: true, message: '插件导入更新' });
        fetchAll();
      } else { toast.error(res.data?.error || '导入失败'); }
    } catch (err: any) {
      toast.error('导入失败: ' + (err?.response?.data?.error || err.message));
    } finally {
      setPluginImporting(false);
      if (pluginFileRef.current) pluginFileRef.current.value = '';
    }
  }, []);

  const handleCookieFileUpload = useCallback(async (fileList: FileList | null) => {
    if (!fileList?.length) return;
    setCookieFileUploading(true);
    setCookieFileResult(null);
    setCookieResult(null);
    const formData = new FormData();
    Array.from(fileList).forEach(f => formData.append('file', f));
    try {
      const res = await api.post('/import-cookie-plugin', formData, { headers: { 'Content-Type': 'multipart/form-data' } });
      const data = res.data || {};
      setCookieFileResult(data);
      if (data.success) {
        toast.success(`Cookie 导入成功（提取 ${data.cookie_items || 0} 项闲鱼 Cookie）`);
        setCurrentCookieHealth({ ok: true, message: '文件导入更新' });
        fetchAll();
      } else { toast.error(data.error || data.hint || '导入失败'); }
    } catch (err: any) {
      const msg = err?.response?.data?.error || err.message;
      setCookieFileResult({ success: false, error: msg });
      toast.error('导入失败: ' + msg);
    } finally {
      setCookieFileUploading(false);
      if (cookieFileRef.current) cookieFileRef.current.value = '';
    }
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault(); e.stopPropagation(); setIsDragging(false);
    handleCookieFileUpload(e.dataTransfer.files);
  }, [handleCookieFileUpload]);

  const handleDragOver = useCallback((e: React.DragEvent) => { e.preventDefault(); e.stopPropagation(); setIsDragging(true); }, []);
  const handleDragLeave = useCallback((e: React.DragEvent) => { e.preventDefault(); e.stopPropagation(); setIsDragging(false); }, []);

  // ─── Derived state ───

  const riskLevel = riskStatus?.risk_control?.level || 'unknown';
  const riskCfg = RISK_LEVEL_CONFIG[riskLevel] || RISK_LEVEL_CONFIG.unknown;
  const recoveryStage = riskStatus?.recovery_stage || 'monitoring';
  const cookieCloudConfigured = riskStatus?.cookie_cloud_configured || false;
  const sliderAutoSolve = riskStatus?.slider_auto_solve_enabled || false;
  const recoveryGuide = getRecoveryGuide(riskLevel, recoveryStage, cookieCloudConfigured, sliderAutoSolve);
  const RiskIcon = riskCfg.icon;

  if (loading) {
    return (
      <div className="xy-page xy-enter max-w-5xl">
        <div className="flex justify-between mb-6">
          <div className="w-1/3">
            <div className="h-8 bg-xy-gray-200 rounded-lg w-1/2 mb-2 animate-pulse" />
            <div className="h-4 bg-xy-gray-200 rounded w-2/3 animate-pulse" />
          </div>
        </div>
        <div className="space-y-4">
          {[1, 2, 3].map(i => <div key={i} className="xy-card p-5 h-32 bg-xy-gray-50 animate-pulse border-none" />)}
        </div>
      </div>
    );
  }

  const acc = accounts[0] || { id: 'default', name: '默认店铺', enabled: true, configured: false };

  return (
    <div className="xy-page xy-enter max-w-5xl">
      <div className="flex flex-col md:flex-row justify-between md:items-end gap-4 mb-6">
        <div>
          <h1 className="xy-title flex items-center gap-2">
            <Store className="w-6 h-6 text-xy-brand-500" /> 账户管理
          </h1>
          <p className="xy-subtitle mt-1">管理闲鱼账号、Cookie 凭证与自动化服务</p>
        </div>
      </div>

      {/* 店铺卡片 */}
      <div className="xy-card p-5 mb-6">
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-3">
            <div className="p-3 rounded-xl bg-orange-50">
              <Store className="w-6 h-6 text-xy-brand-500" />
            </div>
            <div>
              <h3 className="font-bold text-xy-text-primary">{acc.name}</h3>
              <div className="flex items-center gap-3 mt-1">
                <div className="flex items-center gap-1.5">
                  <div className={`w-2 h-2 rounded-full ${acc.enabled ? 'bg-green-500' : 'bg-xy-gray-300'}`} />
                  <span className="text-xs text-xy-text-secondary">{acc.enabled ? '运行中' : '已停用'}</span>
                </div>
                <span className={`text-xs font-medium ${acc.configured ? 'text-green-600' : 'text-red-500'}`}>
                  闲管家{acc.configured ? '已配置' : '未配置'}
                </span>
              </div>
            </div>
          </div>
          <div className="flex gap-2">
            <button
              onClick={() => navigate('/config?tab=integrations')}
              className="py-2 px-3 text-sm font-medium rounded-lg bg-xy-surface border border-xy-border hover:bg-xy-gray-50 flex items-center gap-1.5"
            >
              <Settings className="w-4 h-4" /> 系统配置
            </button>
            <button
              onClick={() => toggleAutomation(acc.enabled)}
              className={`p-2 border rounded-lg transition-colors ${acc.enabled ? 'border-xy-border text-red-500 hover:bg-red-50' : 'border-xy-border text-green-600 hover:bg-green-50'}`}
              title={acc.enabled ? '停用自动化' : '启用自动化'}
            >
              {acc.enabled ? <PowerOff className="w-4 h-4" /> : <Power className="w-4 h-4" />}
            </button>
          </div>
        </div>
      </div>

      {/* Cookie 管理 - 3 个可折叠区块 */}
      <div className="space-y-4">
        {/* 区块 1: 状态总览 */}
        <CollapsibleSection
          title="状态总览"
          defaultOpen={true}
          icon={<ShieldCheck className="w-4 h-4 text-green-500" />}
          badge={
            <span className={`ml-2 text-xs font-medium px-2 py-0.5 rounded-full ${
              currentCookieHealth?.ok ? 'bg-green-100 text-green-700' : 'bg-amber-100 text-amber-700'
            }`}>
              {currentCookieHealth?.ok ? '正常' : '需关注'}
            </span>
          }
        >
          <div className="space-y-4">
            {/* Cookie 健康状态 */}
            <div className={`flex items-center gap-3 px-4 py-3 rounded-lg border ${
              currentCookieHealth?.ok
                ? 'bg-green-50 border-green-200 text-green-800'
                : 'bg-amber-50 border-amber-200 text-amber-800'
            }`}>
              {currentCookieHealth?.ok
                ? <CheckCircle2 className="w-5 h-5 text-green-600" />
                : <AlertCircle className="w-5 h-5 text-amber-600" />}
              <div>
                <span className="font-medium">Cookie 状态：</span>
                {currentCookieHealth?.ok ? '正常' : (currentCookieHealth?.message || '未配置或已过期')}
              </div>
            </div>

            {/* 风控状态 */}
            {riskStatus?.risk_control && (
              <div className={`px-4 py-3 rounded-lg border ${riskCfg.bg} ${riskCfg.border} ${riskCfg.text}`}>
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <RiskIcon className="w-5 h-5" />
                    <span className="font-medium">风控状态：{riskCfg.label}</span>
                  </div>
                  {riskStatus.risk_control.updated_at && (
                    <span className="text-xs opacity-70">
                      {new Date(riskStatus.risk_control.updated_at).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                    </span>
                  )}
                </div>
                {riskStatus.risk_control.signals?.length > 0 && riskLevel !== 'normal' && (
                  <div className="text-sm mb-2"><span className="font-medium">信号：</span>{riskStatus.risk_control.signals.join('、')}</div>
                )}
                {typeof riskStatus.risk_control.score === 'number' && riskLevel !== 'normal' && (
                  <div className="flex items-center gap-2 text-sm">
                    <span className="font-medium">风险分：</span>
                    <div className="flex-1 h-2 bg-white/60 rounded-full overflow-hidden">
                      <div className={`h-full rounded-full transition-all ${riskLevel === 'blocked' ? 'bg-red-500' : 'bg-amber-500'}`} style={{ width: `${Math.min(riskStatus.risk_control.score, 100)}%` }} />
                    </div>
                    <span className="text-xs font-mono">{riskStatus.risk_control.score}/100</span>
                  </div>
                )}
              </div>
            )}

            {/* 恢复状态 */}
            {riskStatus?.recovery && riskLevel !== 'normal' && riskLevel !== 'unknown' && (
              <div className="px-4 py-3 rounded-lg border border-indigo-200 bg-indigo-50 text-indigo-800 text-sm">
                <div className="flex items-center gap-2 mb-1">
                  <RefreshCw className={`w-4 h-4 ${recoveryStage === 'recover_triggered' ? 'animate-spin' : ''}`} />
                  <span className="font-medium">恢复状态：{RECOVERY_STAGE_LABELS[recoveryStage] || recoveryStage}</span>
                </div>
                {riskStatus.recovery.advice && <p className="ml-6 text-indigo-700">{riskStatus.recovery.advice}</p>}
                <div className="ml-6 mt-1 flex gap-4 text-xs text-indigo-600">
                  {riskStatus.recovery.last_auto_recover_at && (
                    <span>上次恢复: {new Date(riskStatus.recovery.last_auto_recover_at).toLocaleTimeString('zh-CN')}</span>
                  )}
                  {riskStatus.recovery.auto_recover_triggered && <span className="font-medium text-indigo-800">已自动触发恢复</span>}
                </div>
              </div>
            )}

            {/* 恢复操作指南 */}
            {recoveryGuide && (
              <div className={`px-4 py-3 rounded-lg border text-sm ${
                recoveryGuide.severity === 'error' ? 'border-red-200 bg-red-50 text-red-800'
                : recoveryGuide.severity === 'warning' ? 'border-amber-200 bg-amber-50 text-amber-800'
                : 'border-blue-200 bg-blue-50 text-blue-800'
              }`}>
                <p className="font-medium mb-2 flex items-center gap-2">
                  <AlertCircle className="w-4 h-4" /> {recoveryGuide.title}
                </p>
                <ol className="list-decimal list-inside space-y-1 ml-2">
                  {recoveryGuide.steps.map((step, i) => <li key={i}>{step}</li>)}
                </ol>
              </div>
            )}
          </div>
        </CollapsibleSection>

        {/* 区块 2: 获取与更新 */}
        <CollapsibleSection
          title="获取与更新"
          defaultOpen={true}
          icon={<Upload className="w-4 h-4 text-blue-500" />}
        >
          <div className="space-y-5">
            {/* 文件上传 */}
            <div
              className={`relative rounded-lg border-2 border-dashed transition-colors ${
                isDragging ? 'border-xy-brand-400 bg-xy-brand-50' : 'border-xy-gray-300 hover:border-xy-brand-300 bg-xy-gray-50'
              }`}
              onDrop={handleDrop}
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
            >
              <input ref={cookieFileRef} type="file" accept=".txt,.json,.log,.cookies,.csv,.tsv,.har,.zip" onChange={e => handleCookieFileUpload(e.target.files)} className="hidden" id="cookie-file-upload" />
              <label htmlFor="cookie-file-upload" className="flex flex-col items-center gap-2 px-6 py-5 cursor-pointer">
                {cookieFileUploading
                  ? <RefreshCw className="w-8 h-8 text-xy-brand-400 animate-spin" />
                  : <Upload className="w-8 h-8 text-xy-gray-400" />}
                <div className="text-center">
                  <span className="text-sm font-medium text-xy-text-primary">
                    {cookieFileUploading ? '正在导入...' : '点击上传 Cookie 文件，或拖拽到此处'}
                  </span>
                  <p className="text-xs text-xy-text-secondary mt-1">支持 cookies.txt / JSON / .zip 格式，系统自动过滤并提取闲鱼域名 Cookie</p>
                </div>
              </label>
              <div className="px-4 pb-3">
                <div className="flex items-start gap-2 px-3 py-2 rounded-md bg-blue-50 border border-blue-100 text-xs text-blue-700">
                  <Filter className="w-3.5 h-3.5 mt-0.5 flex-shrink-0" />
                  <p>插件导出的 Cookie 文件通常包含所有网站的 Cookie，系统会自动过滤，只保留 goofish.com 域名下的闲鱼 Cookie。</p>
                </div>
              </div>
            </div>

            {/* 文件上传结果 */}
            {cookieFileResult && (
              <div className={`px-4 py-3 rounded-lg border text-sm ${cookieFileResult.success ? 'bg-green-50 border-green-200 text-green-800' : 'bg-red-50 border-red-200 text-red-800'}`}>
                <div className="flex items-center gap-2 mb-1">
                  {cookieFileResult.success ? <CheckCircle2 className="w-4 h-4" /> : <XCircle className="w-4 h-4" />}
                  <span className="font-medium">
                    {cookieFileResult.success
                      ? `导入成功 — 提取 ${cookieFileResult.cookie_items || 0} 项 Cookie（评级: ${cookieFileResult.cookie_grade || '未知'}）`
                      : '导入失败'}
                  </span>
                </div>
                {cookieFileResult.success && cookieFileResult.source_file && (
                  <p className="ml-6 text-xs">来源: {cookieFileResult.source_file} | 格式: {cookieFileResult.detected_format}</p>
                )}
                {cookieFileResult.error && <p className="ml-6">{cookieFileResult.error}</p>}
                {cookieFileResult.hint && <p className="ml-6 text-orange-700">{cookieFileResult.hint}</p>}
                {cookieFileResult.missing_required?.length > 0 && (
                  <p className="ml-6 mt-1 text-xs">缺少字段: {cookieFileResult.missing_required.join(', ')}</p>
                )}
              </div>
            )}

            {/* 手动粘贴 */}
            <div>
              <label className="xy-label">手动粘贴 Cookie</label>
              <textarea
                className="xy-input px-3 py-2 h-28 font-mono text-xs"
                placeholder={'支持多种格式粘贴（系统自动过滤非闲鱼域名）：\n1. HTTP Header: cookie2=xxx; sgcookie=yyy; ...\n2. JSON: [{"name":"cookie2","value":"xxx"}, ...]\n3. Netscape cookies.txt（支持全站导出，自动过滤）\n4. DevTools 表格复制'}
                value={cookieText}
                onChange={e => { setCookieText(e.target.value); setCookieResult(null); }}
              />
            </div>

            {/* 操作按钮 */}
            <div className="flex flex-wrap gap-3">
              <button onClick={handleCookieValidate} disabled={cookieValidating || !cookieText.trim()} className="flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-lg border border-xy-brand-300 text-xy-brand-700 bg-xy-brand-50 hover:bg-xy-brand-100 transition-colors disabled:opacity-50">
                {cookieValidating ? <RefreshCw className="w-4 h-4 animate-spin" /> : <CheckCircle2 className="w-4 h-4" />}
                验证 Cookie
              </button>
              <button onClick={handleCookieSave} disabled={saving || !cookieText.trim()} className="xy-btn-primary flex items-center gap-2">
                {saving ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
                保存并生效
              </button>
              {!grabbing ? (
                <div className="relative group">
                  <button onClick={handleAutoGrab} className="flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-lg border border-emerald-300 text-emerald-700 bg-emerald-50 hover:bg-emerald-100 transition-colors">
                    <Download className="w-4 h-4" /> 自动获取
                  </button>
                  <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-3 py-1.5 bg-gray-800 text-white text-xs rounded-lg whitespace-nowrap opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none z-10">
                    读取浏览器磁盘数据库，滑块验证后可能有延迟
                    <div className="absolute top-full left-1/2 -translate-x-1/2 border-4 border-transparent border-t-gray-800" />
                  </div>
                </div>
              ) : (
                <button onClick={handleCancelAutoGrab} className="flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-lg border border-red-300 text-red-700 bg-red-50 hover:bg-red-100 transition-colors">
                  <XCircle className="w-4 h-4" /> 取消获取
                </button>
              )}
              <button
                onClick={() => setPluginGuideOpen(v => !v)}
                className={`flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-lg border transition-colors ${
                  pluginGuideOpen ? 'border-purple-400 text-purple-800 bg-purple-100' : 'border-purple-300 text-purple-700 bg-purple-50 hover:bg-purple-100'
                }`}
              >
                <Plug className="w-4 h-4" /> Cookie 插件
                {pluginGuideOpen ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
              </button>
            </div>

            {/* 插件引导面板 */}
            {pluginGuideOpen && (
              <div className="px-5 py-4 rounded-lg border border-purple-200 bg-gradient-to-b from-purple-50 to-white text-sm space-y-4">
                <h4 className="font-bold text-purple-900 flex items-center gap-2"><Plug className="w-4 h-4" /> Cookie 插件获取引导</h4>
                <div className="space-y-3">
                  {[
                    { step: '1', title: '下载插件包', desc: '系统内置 Get cookies.txt LOCALLY 插件（开源安全，不会外传数据）', action: <button onClick={handleDownloadPlugin} className="mt-2 flex items-center gap-2 px-3 py-1.5 text-xs font-medium rounded-md border border-purple-300 text-purple-700 bg-white hover:bg-purple-50 transition-colors"><Download className="w-3.5 h-3.5" /> 下载插件包 (.zip)</button> },
                    { step: '2', title: '安装到浏览器', desc: null, list: ['解压下载的 zip 文件', '打开 Chrome，地址栏输入 chrome://extensions', '右上角打开「开发者模式」开关', '点击「加载已解压的扩展程序」，选择解压后的 src 文件夹'] },
                    { step: '3', title: '导出 Cookie', desc: null, list: ['打开闲鱼网页版并登录账号', '点击浏览器工具栏中的插件图标', '选择导出格式（Netscape 或 JSON 均可），点击「Export」下载文件'] },
                  ].map(item => (
                    <div key={item.step} className="flex gap-3">
                      <span className="flex-shrink-0 w-6 h-6 rounded-full bg-purple-600 text-white text-xs font-bold flex items-center justify-center">{item.step}</span>
                      <div className="flex-1">
                        <p className="font-medium text-purple-900">{item.title}</p>
                        {item.desc && <p className="text-purple-700 mt-0.5">{item.desc}</p>}
                        {item.list && (
                          <ol className="text-purple-700 mt-0.5 list-decimal list-inside space-y-0.5">
                            {item.list.map((li, i) => <li key={i}>{li}</li>)}
                          </ol>
                        )}
                        {item.action}
                      </div>
                    </div>
                  ))}
                  <div className="flex gap-3">
                    <span className="flex-shrink-0 w-6 h-6 rounded-full bg-purple-600 text-white text-xs font-bold flex items-center justify-center">4</span>
                    <div className="flex-1">
                      <p className="font-medium text-purple-900">导入到系统</p>
                      <p className="text-purple-700 mt-0.5">选择导出的文件，系统自动解析并更新 Cookie</p>
                      <div className="mt-2 flex items-center gap-3">
                        <input ref={pluginFileRef} type="file" accept=".txt,.json,.log,.cookies,.csv,.tsv,.har,.zip" onChange={handlePluginFileImport} className="hidden" id="plugin-cookie-file" />
                        <label htmlFor="plugin-cookie-file" className={`flex items-center gap-2 px-3 py-1.5 text-xs font-medium rounded-md border cursor-pointer transition-colors ${pluginImporting ? 'border-gray-300 text-gray-400 bg-gray-50 cursor-not-allowed' : 'border-purple-300 text-purple-700 bg-white hover:bg-purple-50'}`}>
                          {pluginImporting ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <Download className="w-3.5 h-3.5" />}
                          {pluginImporting ? '导入中...' : '选择文件并导入'}
                        </label>
                      </div>
                    </div>
                  </div>
                </div>
                <p className="text-xs text-purple-500 border-t border-purple-100 pt-2">
                  也可从 <a href="https://chromewebstore.google.com/detail/get-cookiestxt-locally/cclelndahbckbenkjhflpdbgdldlbecc" target="_blank" rel="noreferrer" className="underline">Chrome 应用商店</a> 直接安装。
                </p>
              </div>
            )}

            {/* 自动获取进度 */}
            {grabbing && grabProgress && (
              <div className="px-4 py-4 rounded-lg border border-emerald-200 bg-emerald-50 text-emerald-800 text-sm space-y-3">
                <div className="flex items-center gap-3">
                  {grabProgress.stage === 'success' || grabProgress.stage === 'done' ? (
                    <CheckCircle className="w-6 h-6 text-green-500 shrink-0" />
                  ) : grabProgress.stage === 'failed' || grabProgress.stage === 'cancelled' ? (
                    <XCircle className="w-6 h-6 text-red-500 shrink-0" />
                  ) : (
                    <Loader2 className="w-6 h-6 text-xy-brand-500 animate-spin shrink-0" />
                  )}
                  <div>
                    <p className={`font-semibold ${GRAB_STAGE_CONFIG[grabProgress.stage]?.color || 'text-xy-text-primary'}`}>
                      {grabProgress.message || GRAB_STAGE_CONFIG[grabProgress.stage]?.label || grabProgress.stage}
                    </p>
                    {grabProgress.hint && <p className="text-sm text-emerald-700 mt-0.5">{grabProgress.hint}</p>}
                  </div>
                </div>
                {grabProgress.progress > 0 && !['success', 'done', 'failed'].includes(grabProgress.stage) && (
                  <div className="w-full bg-emerald-200 rounded-full h-2">
                    <div className="bg-emerald-500 h-2 rounded-full transition-all" style={{ width: `${Math.min(grabProgress.progress, 100)}%` }} />
                  </div>
                )}
                {grabProgress.stage === 'waiting_login' && (
                  <div className="p-3 bg-orange-50 rounded-lg border border-orange-200">
                    <div className="flex items-start gap-2">
                      <Monitor className="w-5 h-5 text-orange-600 mt-0.5 shrink-0" />
                      <div className="text-sm">
                        <p className="font-medium text-orange-800">操作步骤：</p>
                        <ol className="list-decimal list-inside mt-1 space-y-1 text-orange-700">
                          <li>查看已打开的 Chrome 浏览器窗口</li>
                          <li>打开手机闲鱼 APP</li>
                          <li>扫描浏览器中的二维码登录</li>
                          <li>登录成功后系统会自动获取 Cookie</li>
                        </ol>
                      </div>
                    </div>
                  </div>
                )}
                {grabProgress.stage === 'reading_db' && (
                  <div className="p-3 bg-blue-50 rounded-lg border border-blue-200 text-sm text-blue-700">
                    <strong>方式一</strong> — 直接读取浏览器 Cookie 数据库。如果弹出"钥匙串访问"弹窗，请点击"允许"。
                  </div>
                )}
                {grabProgress.stage === 'reading_profile' && (
                  <div className="p-3 bg-blue-50 rounded-lg border border-blue-200 text-sm text-blue-700">
                    <strong>方式二</strong> — 读取 Chrome 已有登录态。如果你之前在 Chrome 中登录过闲鱼，系统将静默提取 Cookie。
                  </div>
                )}
              </div>
            )}

            {/* 验证结果 */}
            {cookieResult && (
              <div className={`px-4 py-3 rounded-lg border text-sm ${cookieResult.ok ? 'bg-green-50 border-green-200 text-green-800' : 'bg-red-50 border-red-200 text-red-800'}`}>
                <div className="flex items-center gap-2 mb-1">
                  {cookieResult.ok ? <CheckCircle2 className="w-4 h-4" /> : <XCircle className="w-4 h-4" />}
                  <span className="font-medium">
                    评级: {cookieResult.grade} — {cookieResult.ok ? 'Cookie 有效' : 'Cookie 无效'}
                    {cookieResult.cookie_items > 0 && ` (${cookieResult.cookie_items} 项)`}
                  </span>
                </div>
                {cookieResult.message && <p className="ml-6">{cookieResult.message}</p>}
                {cookieResult.domain_filter && cookieResult.domain_filter.rejected > 0 && (
                  <p className="ml-6 mt-1 text-xs flex items-center gap-1">
                    <Filter className="w-3 h-3" />
                    域名过滤：已过滤 {cookieResult.domain_filter.rejected} 条非闲鱼域名
                  </p>
                )}
                {cookieResult.actions?.length > 0 && (
                  <ul className="ml-6 mt-1 list-disc list-inside">{cookieResult.actions.map((a: string, i: number) => <li key={i}>{a}</li>)}</ul>
                )}
                {cookieResult.required_missing?.length > 0 && (
                  <p className="ml-6 mt-1">缺少字段：{cookieResult.required_missing.join(', ')}</p>
                )}
              </div>
            )}

            {/* 获取指南 */}
            <div className="bg-blue-50 border border-blue-200 p-4 rounded-lg text-blue-800 text-sm">
              <div className="flex items-start gap-3">
                <Info className="w-5 h-5 flex-shrink-0 mt-0.5 text-blue-600" />
                <div>
                  <p className="font-medium mb-2">Cookie 获取指南</p>

                  <p className="text-blue-700 mb-1 font-medium">方式一：CookieCloud 自动同步 <span className="text-xs font-normal bg-green-100 text-green-700 px-1.5 py-0.5 rounded">最推荐</span></p>
                  <p className="text-blue-700 mb-2">实时读取浏览器内存，无延迟。在「系统设置 → 集成服务 → CookieCloud」中配置后全自动同步，风控恢复后无需手动操作。</p>

                  <p className="text-blue-700 mb-1 font-medium">方式二：手动获取 <span className="text-xs font-normal bg-blue-100 text-blue-700 px-1.5 py-0.5 rounded">紧急恢复</span></p>
                  <ol className="list-decimal list-inside space-y-1 text-blue-700 mb-2">
                    <li>使用 Chrome 浏览器打开 <a href="https://www.goofish.com" target="_blank" rel="noreferrer" className="underline">闲鱼网页版</a> 并登录</li>
                    <li>按 F12 打开开发者工具，切换到「Network / 网络」标签</li>
                    <li>刷新页面，选择任意请求，在 Headers 中找到 Cookie 字段</li>
                    <li>右键「Copy value」，粘贴到上方输入框</li>
                  </ol>

                  <p className="text-blue-700 mb-1 font-medium">方式三：自动获取 <span className="text-xs font-normal bg-gray-100 text-gray-600 px-1.5 py-0.5 rounded">首次配置</span></p>
                  <p className="text-blue-700">读取浏览器<strong>磁盘数据库</strong>，适合首次配置。<span className="text-amber-700">风控恢复（滑块验证后）可能因磁盘写入延迟读到旧 Cookie，此场景建议使用方式一或方式二。</span></p>
                </div>
              </div>
            </div>
          </div>
        </CollapsibleSection>

        {/* 区块 3: 自动维护 */}
        <CollapsibleSection
          title="自动维护"
          defaultOpen={false}
          icon={<Activity className="w-4 h-4 text-purple-500" />}
          badge={autoRefresh?.enabled
            ? <span className="ml-2 inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-700"><span className="w-1.5 h-1.5 rounded-full bg-green-500" /> 已启用</span>
            : undefined}
        >
          {autoRefresh ? (
            autoRefresh.enabled ? (
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-sm">
                <div className="p-3 bg-xy-gray-50 rounded-lg">
                  <p className="text-xy-text-secondary text-xs mb-1">检查间隔</p>
                  <p className="font-medium text-xy-text-primary">每 {autoRefresh.interval_minutes} 分钟</p>
                </div>
                <div className="p-3 bg-xy-gray-50 rounded-lg">
                  <p className="text-xy-text-secondary text-xs mb-1">上次检查</p>
                  <p className="font-medium text-xy-text-primary">
                    {autoRefresh.last_check_at > 0 ? new Date(autoRefresh.last_check_at * 1000).toLocaleTimeString() : '尚未检查'}
                  </p>
                  {autoRefresh.last_check_ok !== null && (
                    <p className={`text-xs mt-0.5 ${autoRefresh.last_check_ok ? 'text-green-600' : 'text-orange-600'}`}>
                      {autoRefresh.last_check_message || (autoRefresh.last_check_ok ? '健康' : '异常')}
                    </p>
                  )}
                </div>
                <div className="p-3 bg-xy-gray-50 rounded-lg">
                  <p className="text-xy-text-secondary text-xs mb-1">下次检查</p>
                  <p className="font-medium text-xy-text-primary flex items-center gap-1">
                    <Timer className="w-3.5 h-3.5" />
                    {autoRefresh.next_check_in_seconds > 0 ? `${Math.ceil(autoRefresh.next_check_in_seconds / 60)} 分钟后` : '即将执行'}
                  </p>
                </div>
                {autoRefresh.total_refreshes > 0 && (
                  <div className="sm:col-span-3 p-3 bg-green-50 rounded-lg border border-green-200">
                    <p className="text-sm text-green-700">
                      <strong>上次静默刷新：</strong>
                      {new Date(autoRefresh.last_refresh_at * 1000).toLocaleString()}
                      {' — '}{autoRefresh.last_refresh_ok ? '成功' : '失败'}
                      {autoRefresh.total_refreshes > 1 && ` (累计 ${autoRefresh.total_refreshes} 次)`}
                    </p>
                  </div>
                )}
              </div>
            ) : (
              <p className="text-sm text-xy-text-secondary">
                {autoRefresh.message || '设置环境变量 COOKIE_AUTO_REFRESH=true 可启用自动刷新，系统将定期检查 Cookie 有效性并在失效时自动从浏览器获取新 Cookie。'}
              </p>
            )
          ) : (
            <p className="text-sm text-xy-text-secondary">无法获取自动刷新状态</p>
          )}
        </CollapsibleSection>
      </div>
    </div>
  );
}
