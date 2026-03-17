import React, { useState, useEffect } from 'react';
import { api } from '../api/index';
import { ArrowUpCircle, X, ExternalLink } from 'lucide-react';

const CACHE_KEY = 'xianyu_update_check';
const CACHE_TTL = 24 * 60 * 60 * 1000;
const DISMISS_KEY = 'xianyu_update_dismissed';

interface VersionInfo {
  current: string;
  latest: string | null;
  hasUpdate: boolean;
  releasesUrl: string;
  checkedAt: number;
}

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

  useEffect(() => {
    checkForUpdate();
  }, []);

  const checkForUpdate = async () => {
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

    try {
      const res = await api.get('/version');
      const currentVersion = res.data?.version || '0.0.0';
      const releasesUrl = res.data?.releases_url || '';

      let latestVersion: string | null = null;
      try {
        const ghRes = await api.get('/version/latest');
        latestVersion = ghRes.data?.latest || null;
      } catch { /* GitHub check failed, non-critical */ }

      const result: VersionInfo = {
        current: currentVersion,
        latest: latestVersion,
        hasUpdate: latestVersion ? compareVersions(currentVersion, latestVersion) < 0 : false,
        releasesUrl,
        checkedAt: Date.now(),
      };

      localStorage.setItem(CACHE_KEY, JSON.stringify(result));
      setInfo(result);
    } catch { /* version endpoint unavailable */ }
  };

  const handleDismiss = () => {
    setDismissed(true);
    if (info?.latest) {
      localStorage.setItem(DISMISS_KEY, info.latest);
    }
  };

  if (!info?.hasUpdate || dismissed) return null;

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
      {info.releasesUrl && (
        <a
          href={info.releasesUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center gap-1 text-sm font-medium text-blue-600 hover:text-blue-700 shrink-0"
        >
          查看更新 <ExternalLink className="w-3.5 h-3.5" />
        </a>
      )}
      <button onClick={handleDismiss} className="text-blue-400 hover:text-blue-600 shrink-0" aria-label="关闭">
        <X className="w-4 h-4" />
      </button>
    </div>
  );
}
