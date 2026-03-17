import React, { useState, useEffect, useRef, useCallback } from 'react';
import { api } from '../api/index';
import { ArrowUpCircle, X, ExternalLink, Download, Loader2, CheckCircle, AlertCircle, RefreshCw } from 'lucide-react';

const CACHE_KEY = 'xianyu_update_check';
const CACHE_TTL = 24 * 60 * 60 * 1000;
const DISMISS_KEY = 'xianyu_update_dismissed';

interface VersionInfo {
  current: string;
  latest: string | null;
  hasUpdate: boolean;
  releasesUrl: string;
  checkedAt: number;
  releaseNotes?: string;
}

type UpdatePhase = 'idle' | 'confirming' | 'checking' | 'downloading' | 'backing_up' | 'stopping'
  | 'extracting' | 'installing_deps' | 'restarting' | 'done' | 'error' | 'rolling_back'
  | 'reconnecting';

const PHASE_LABELS: Record<string, string> = {
  idle: '',
  confirming: '确认更新',
  checking: '检查版本...',
  downloading: '下载更新包...',
  backing_up: '备份当前版本...',
  stopping: '停止服务...',
  extracting: '解压安装...',
  installing_deps: '安装依赖...',
  restarting: '重启服务...',
  reconnecting: '等待服务重启...',
  done: '更新完成',
  error: '更新失败',
  rolling_back: '正在回滚...',
};

function compareVersions(a: string, b: string): number {
  const pa = a.replace(/^v/, '').split('.').map(Number);
  const pb = b.replace(/^v/, '').split('.').map(Number);
  for (let i = 0; i < Math.max(pa.length, pb.length); i++) {
    const na = pa[i] || 0;
    const nb = pb[i] || 0;
    if (na !== nb) return na - nb;
  }
  return 0;
}

export default function UpdateBanner() {
  const [info, setInfo] = useState<VersionInfo | null>(null);
  const [dismissed, setDismissed] = useState(false);
  const [phase, setPhase] = useState<UpdatePhase>('idle');
  const [errorMsg, setErrorMsg] = useState('');
  const [manualChecking, setManualChecking] = useState(false);
  const [upToDate, setUpToDate] = useState(false);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const reconnectRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const upToDateTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    checkForUpdate(false);
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
      if (reconnectRef.current) clearInterval(reconnectRef.current);
      if (upToDateTimer.current) clearTimeout(upToDateTimer.current);
    };
  }, []);

  const checkForUpdate = async (force: boolean) => {
    if (!force) {
      const cached = localStorage.getItem(CACHE_KEY);
      if (cached) {
        try {
          const parsed: VersionInfo = JSON.parse(cached);
          if (Date.now() - parsed.checkedAt < CACHE_TTL) {
            const dismissedVersion = localStorage.getItem(DISMISS_KEY);
            if (parsed.hasUpdate && dismissedVersion === parsed.latest) {
              setDismissed(true);
            }
            setInfo(parsed);
            return;
          }
        } catch { /* stale cache */ }
      }
    }

    try {
      const res = await api.get('/version');
      const currentVersion = res.data?.version || '0.0.0';
      const releasesUrl = res.data?.releases_url || '';

      let latestVersion: string | null = null;
      let releaseNotes = '';
      try {
        const ghRes = await api.get('/version/latest');
        latestVersion = ghRes.data?.latest || null;
        releaseNotes = ghRes.data?.body || '';
      } catch { /* GitHub check failed */ }

      const result: VersionInfo = {
        current: currentVersion,
        latest: latestVersion,
        hasUpdate: latestVersion ? compareVersions(currentVersion, latestVersion) < 0 : false,
        releasesUrl,
        checkedAt: Date.now(),
        releaseNotes,
      };

      localStorage.setItem(CACHE_KEY, JSON.stringify(result));
      if (result.hasUpdate) setDismissed(false);
      setInfo(result);
    } catch { /* version endpoint unavailable */ }
  };

  const latestInfoRef = useRef(info);
  latestInfoRef.current = info;

  const handleManualCheck = async () => {
    setManualChecking(true);
    setUpToDate(false);
    localStorage.removeItem(CACHE_KEY);
    await checkForUpdate(true);
    setManualChecking(false);
    setTimeout(() => {
      if (!latestInfoRef.current?.hasUpdate) {
        setUpToDate(true);
        if (upToDateTimer.current) clearTimeout(upToDateTimer.current);
        upToDateTimer.current = setTimeout(() => setUpToDate(false), 3000);
      }
    }, 0);
  };

  const handleDismiss = () => {
    setDismissed(true);
    if (info?.latest) {
      localStorage.setItem(DISMISS_KEY, info.latest);
    }
  };

  const reconnectAttemptsRef = useRef(0);

  const startReconnecting = useCallback(() => {
    if (reconnectRef.current) clearInterval(reconnectRef.current);
    reconnectAttemptsRef.current = 0;
    reconnectRef.current = setInterval(async () => {
      reconnectAttemptsRef.current++;
      try {
        await api.get('/healthz');
        if (reconnectRef.current) clearInterval(reconnectRef.current);
        setPhase('done');
        localStorage.removeItem(CACHE_KEY);
        setTimeout(() => window.location.reload(), 1500);
      } catch {
        if (reconnectAttemptsRef.current > 30) {
          if (reconnectRef.current) clearInterval(reconnectRef.current);
          setPhase('error');
          setErrorMsg('服务重启超时，请手动刷新页面');
        }
      }
    }, 2000);
  }, []);

  const startPollingStatus = useCallback(() => {
    if (pollRef.current) clearInterval(pollRef.current);
    pollRef.current = setInterval(async () => {
      try {
        const res = await api.get('/update/status');
        const status = res.data?.status || 'idle';
        if (status === 'done') {
          if (pollRef.current) clearInterval(pollRef.current);
          setPhase('done');
          localStorage.removeItem(CACHE_KEY);
          setTimeout(() => window.location.reload(), 2000);
        } else if (status === 'error') {
          if (pollRef.current) clearInterval(pollRef.current);
          setPhase('error');
          setErrorMsg(res.data?.message || '未知错误');
        } else {
          setPhase(status as UpdatePhase);
        }
      } catch {
        setPhase('reconnecting');
        if (pollRef.current) clearInterval(pollRef.current);
        startReconnecting();
      }
    }, 2000);
  }, [startReconnecting]);

  const handleUpdate = async () => {
    setPhase('checking');
    setErrorMsg('');
    try {
      const res = await api.post('/update/apply');
      if (res.data?.success) {
        setPhase('downloading');
        startPollingStatus();
      } else {
        setPhase('error');
        setErrorMsg(res.data?.error || '更新失败');
      }
    } catch (err: any) {
      setPhase('error');
      setErrorMsg(err?.response?.data?.error || err?.message || '请求失败');
    }
  };

  const isUpdating = phase !== 'idle' && phase !== 'confirming' && phase !== 'error';

  if (phase === 'confirming') {
    return (
      <div className="mb-4 px-4 py-4 bg-blue-50 border border-blue-200 rounded-xl text-sm">
        <div className="flex items-center gap-3 mb-3">
          <ArrowUpCircle className="w-5 h-5 text-blue-500 shrink-0" />
          <div className="flex-1">
            <span className="font-medium text-blue-700">
              确认更新到 v{info?.latest}？
            </span>
            <span className="text-blue-600 ml-2">(当前: v{info?.current})</span>
          </div>
        </div>
        <p className="text-blue-600 mb-3 ml-8">
          更新将自动备份当前版本，替换源码后重启服务。配置文件和数据不会受影响。
        </p>
        <div className="flex gap-2 ml-8">
          <button
            onClick={handleUpdate}
            className="px-4 py-1.5 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 transition-colors"
          >
            确认更新
          </button>
          <button
            onClick={() => setPhase('idle')}
            className="px-4 py-1.5 bg-white text-blue-600 border border-blue-300 rounded-lg text-sm font-medium hover:bg-blue-50 transition-colors"
          >
            取消
          </button>
        </div>
      </div>
    );
  }

  if (isUpdating || phase === 'done') {
    return (
      <div className="mb-4 px-4 py-3 bg-blue-50 border border-blue-200 rounded-xl text-sm">
        <div className="flex items-center gap-3">
          {phase === 'done' ? (
            <CheckCircle className="w-5 h-5 text-green-500 shrink-0" />
          ) : (
            <Loader2 className="w-5 h-5 text-blue-500 shrink-0 animate-spin" />
          )}
          <div className="flex-1">
            <span className={`font-medium ${phase === 'done' ? 'text-green-700' : 'text-blue-700'}`}>
              {PHASE_LABELS[phase] || phase}
            </span>
            {phase === 'done' && (
              <span className="text-green-600 ml-2">页面即将刷新...</span>
            )}
          </div>
        </div>
        {isUpdating && (
          <div className="mt-2 ml-8">
            <div className="w-full bg-blue-100 rounded-full h-1.5">
              <div
                className="bg-blue-500 h-1.5 rounded-full transition-all duration-500"
                style={{ width: `${getProgressPercent(phase)}%` }}
              />
            </div>
          </div>
        )}
      </div>
    );
  }

  if (phase === 'error') {
    return (
      <div className="mb-4 flex items-center gap-3 px-4 py-3 bg-red-50 border border-red-200 rounded-xl text-sm">
        <AlertCircle className="w-5 h-5 text-red-500 shrink-0" />
        <div className="flex-1">
          <span className="font-medium text-red-700">更新失败</span>
          <span className="text-red-600 ml-2">{errorMsg}</span>
        </div>
        <button
          onClick={() => { setPhase('idle'); setErrorMsg(''); }}
          className="text-red-400 hover:text-red-600 shrink-0"
        >
          <X className="w-4 h-4" />
        </button>
      </div>
    );
  }

  if (!info?.hasUpdate || dismissed) {
    return (
      <div className="mb-4 flex items-center gap-3 px-4 py-2.5 bg-xy-gray-50 border border-xy-border rounded-xl text-sm">
        <span className="text-xy-text-secondary">
          当前版本: <span className="font-medium text-xy-text-primary">v{info?.current || '...'}</span>
        </span>
        {upToDate && (
          <span className="flex items-center gap-1 text-green-600">
            <CheckCircle className="w-3.5 h-3.5" /> 已是最新版本
          </span>
        )}
        <div className="flex-1" />
        <button
          onClick={handleManualCheck}
          disabled={manualChecking}
          className="flex items-center gap-1.5 px-3 py-1 text-sm font-medium text-xy-text-secondary hover:text-xy-brand-600 hover:bg-xy-brand-50 rounded-lg transition-colors disabled:opacity-50"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${manualChecking ? 'animate-spin' : ''}`} />
          {manualChecking ? '检查中...' : '检查更新'}
        </button>
      </div>
    );
  }

  return (
    <div className="mb-4 flex items-center gap-3 px-4 py-3 bg-blue-50 border border-blue-200 rounded-xl text-sm">
      <ArrowUpCircle className="w-5 h-5 text-blue-500 shrink-0" />
      <div className="flex-1">
        <span className="font-medium text-blue-700">
          新版本可用: v{info.latest}
        </span>
        <span className="text-blue-600 ml-2">
          (当前: v{info.current})
        </span>
      </div>
      <button
        onClick={() => setPhase('confirming')}
        className="flex items-center gap-1.5 px-3 py-1.5 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 transition-colors shrink-0"
      >
        <Download className="w-3.5 h-3.5" />
        一键更新
      </button>
      {info.releasesUrl && (
        <a
          href={info.releasesUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center gap-1 text-sm font-medium text-blue-600 hover:text-blue-700 shrink-0"
        >
          详情 <ExternalLink className="w-3.5 h-3.5" />
        </a>
      )}
      <button onClick={handleDismiss} className="text-blue-400 hover:text-blue-600 shrink-0" aria-label="关闭">
        <X className="w-4 h-4" />
      </button>
    </div>
  );
}

function getProgressPercent(phase: UpdatePhase): number {
  const map: Record<string, number> = {
    checking: 5,
    downloading: 20,
    backing_up: 35,
    stopping: 45,
    extracting: 60,
    installing_deps: 75,
    restarting: 90,
    reconnecting: 95,
    done: 100,
  };
  return map[phase] || 0;
}
