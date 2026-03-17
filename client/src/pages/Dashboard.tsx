import React, { useState, useEffect, useRef, useCallback } from 'react'
import { Link } from 'react-router-dom'
import { getDashboardSummary, getRecentOperations, getSystemStatus, getTrendData, getTopProducts, getSliderStats, type SliderStats } from '../api/dashboard'
import { Store, ShoppingBag, MessageCircle, FileText, AlertCircle, RefreshCw, Settings, Zap, Bot, BarChart3, Clock, Package, TrendingUp, Calendar, Send, Shield, ShieldCheck, ShieldAlert, ShieldX } from 'lucide-react'
import toast from 'react-hot-toast'
import SetupGuide from '../components/SetupGuide'
import SetupWizard from '../components/SetupWizard'
import UpdateBanner from '../components/UpdateBanner'
import ApiStatusPanel from '../components/ApiStatusPanel'
import { useStoreCategory } from '../contexts/StoreCategoryContext'
import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, CartesianGrid } from 'recharts'

import { getPublishQueue } from '../api/listing';

const POLL_INTERVAL = 60_000;
const AGO_TICK = 10_000;

function formatTimeAgo(ts: number): string {
  const diff = Math.max(0, Math.floor((Date.now() - ts) / 1000));
  if (diff < 5) return '刚刚';
  if (diff < 60) return `${diff} 秒前`;
  const mins = Math.floor(diff / 60);
  if (mins < 60) return `${mins} 分钟前`;
  return `${Math.floor(mins / 60)} 小时前`;
}

function PublishQueueCard() {
  const [count, setCount] = useState(0);
  useEffect(() => {
    const today = new Date().toISOString().split('T')[0];
    getPublishQueue(today)
      .then(res => {
        if (res.data?.ok) {
          const pending = (res.data.items || []).filter(
            (it: any) => it.status === 'draft' || it.status === 'ready'
          );
          setCount(pending.length);
        }
      })
      .catch(() => {});
  }, []);

  return (
    <Link to="/products/auto-publish?tab=queue" className="flex items-center justify-between p-3 rounded-xl border border-xy-border hover:border-emerald-500 hover:bg-emerald-50 transition-colors group">
      <div className="flex items-center gap-3">
        <div className="bg-emerald-100 p-2 rounded-lg group-hover:bg-emerald-200 transition-colors"><Send className="w-5 h-5 text-emerald-600" /></div>
        <div>
          <span className="font-medium text-xy-text-primary">今日待发布</span>
          {count > 0 && <span className="ml-2 px-1.5 py-0.5 rounded-full bg-emerald-100 text-emerald-700 text-[11px] font-medium">{count} 条</span>}
        </div>
      </div>
      <span className="text-emerald-500">&rarr;</span>
    </Link>
  );
}

function SliderStatsCard() {
  const [stats, setStats] = useState<SliderStats | null>(null);
  const [hours, setHours] = useState(24);

  useEffect(() => {
    getSliderStats(hours)
      .then(res => { if (res.data?.ok) setStats(res.data); })
      .catch(() => {});
  }, [hours]);

  if (!stats || stats.total_triggers === 0) return null;

  const rateColor = (rate: number) =>
    rate >= 80 ? 'text-green-600' : rate >= 50 ? 'text-yellow-600' : 'text-red-600';
  const rateBg = (rate: number) =>
    rate >= 80 ? 'bg-green-100' : rate >= 50 ? 'bg-yellow-100' : 'bg-red-100';

  const ttlText = stats.avg_cookie_ttl_seconds != null
    ? stats.avg_cookie_ttl_seconds > 3600
      ? `${(stats.avg_cookie_ttl_seconds / 3600).toFixed(1)}h`
      : `${Math.round(stats.avg_cookie_ttl_seconds / 60)}min`
    : '--';

  return (
    <div className="xy-card p-5">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-base font-semibold text-xy-text-primary flex items-center gap-2">
          <Shield className="w-4 h-4 text-blue-500" /> 滑块验证
        </h3>
        <select
          className="text-xs border border-xy-border rounded-lg px-2 py-1 bg-white"
          value={hours}
          onChange={e => setHours(Number(e.target.value))}
        >
          <option value={6}>6h</option>
          <option value={24}>24h</option>
          <option value={72}>3天</option>
          <option value={168}>7天</option>
        </select>
      </div>

      <div className="grid grid-cols-3 gap-3 mb-4">
        <div className="text-center">
          <div className={`text-xl font-bold ${rateColor(stats.success_rate)}`}>
            {stats.success_rate}%
          </div>
          <div className="text-[11px] text-xy-text-secondary">总成功率</div>
        </div>
        <div className="text-center">
          <div className="text-xl font-bold text-xy-text-primary">{stats.total_triggers}</div>
          <div className="text-[11px] text-xy-text-secondary">触发次数</div>
        </div>
        <div className="text-center">
          <div className="text-xl font-bold text-xy-text-primary">{ttlText}</div>
          <div className="text-[11px] text-xy-text-secondary">Cookie均寿</div>
        </div>
      </div>

      <div className="space-y-2">
        {stats.nc_attempts > 0 && (
          <div className="flex items-center justify-between text-sm">
            <span className="flex items-center gap-1.5">
              {stats.nc_success_rate >= 50
                ? <ShieldCheck className="w-3.5 h-3.5 text-green-500" />
                : <ShieldAlert className="w-3.5 h-3.5 text-yellow-500" />}
              NC 滑块
            </span>
            <span>
              <span className={`font-medium ${rateColor(stats.nc_success_rate)}`}>
                {stats.nc_passed}/{stats.nc_attempts}
              </span>
              <span className={`ml-1 px-1.5 py-0.5 rounded text-[10px] font-medium ${rateBg(stats.nc_success_rate)} ${rateColor(stats.nc_success_rate)}`}>
                {stats.nc_success_rate}%
              </span>
            </span>
          </div>
        )}
        {stats.puzzle_attempts > 0 && (
          <div className="flex items-center justify-between text-sm">
            <span className="flex items-center gap-1.5">
              {stats.puzzle_success_rate >= 50
                ? <ShieldCheck className="w-3.5 h-3.5 text-green-500" />
                : <ShieldX className="w-3.5 h-3.5 text-red-500" />}
              拼图滑块
            </span>
            <span>
              <span className={`font-medium ${rateColor(stats.puzzle_success_rate)}`}>
                {stats.puzzle_passed}/{stats.puzzle_attempts}
              </span>
              <span className={`ml-1 px-1.5 py-0.5 rounded text-[10px] font-medium ${rateBg(stats.puzzle_success_rate)} ${rateColor(stats.puzzle_success_rate)}`}>
                {stats.puzzle_success_rate}%
              </span>
            </span>
          </div>
        )}
      </div>

      {stats.screenshots.length > 0 && (
        <details className="mt-3">
          <summary className="text-xs text-xy-text-secondary cursor-pointer hover:text-xy-text-primary">
            查看失败截图 ({stats.screenshots.length})
          </summary>
          <div className="mt-2 grid grid-cols-2 gap-2">
            {stats.screenshots.slice(0, 4).map((s, i) => (
              <div key={i} className="relative group">
                <img
                  src={`/api/slider/screenshot/${s.path.split('/').pop()}`}
                  alt={`${s.type} ${s.result}`}
                  className="w-full h-20 object-cover rounded border border-xy-border"
                  loading="lazy"
                />
                <div className="absolute bottom-0 left-0 right-0 bg-black/60 text-white text-[10px] px-1 py-0.5 rounded-b">
                  {s.type} · {s.result}
                </div>
              </div>
            ))}
          </div>
        </details>
      )}
    </div>
  );
}

const TABS = [
  { key: 'overview', label: '概览' },
  { key: 'analytics', label: '数据分析' },
];

const Dashboard = () => {
  const { category, meta } = useStoreCategory();
  const [activeTab, setActiveTab] = useState('overview');
  const [stats, setStats] = useState({ products: 0, orders: 0, sales: 0, totalOrders: 0 });
  const [dataSource, setDataSource] = useState<string>('');
  const [recentOps, setRecentOps] = useState([]);
  const [sysStatus, setSysStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [lastUpdated, setLastUpdated] = useState<number>(0);
  const [agoText, setAgoText] = useState('');

  const [metric, setMetric] = useState('orders');
  const [days, setDays] = useState(30);
  const [trendData, setTrendData] = useState([]);
  const [topProducts, setTopProducts] = useState([]);
  const [analyticsLoading, setAnalyticsLoading] = useState(false);

  const activeTabRef = useRef(activeTab);
  activeTabRef.current = activeTab;
  const metricRef = useRef(metric);
  metricRef.current = metric;
  const daysRef = useRef(days);
  daysRef.current = days;

  const applyDashboardResults = useCallback((results: PromiseSettledResult<any>[]) => {
    const [summaryRes, opsRes, statusRes] = results.map(r => r.status === 'fulfilled' ? r.value : null);

    if (summaryRes?.data) {
      const raw = summaryRes.data.data || summaryRes.data;
      setDataSource(raw.source || 'local_db');
      setStats({
        products: raw.active_products ?? 0,
        orders: raw.pending_orders ?? raw.today_operations ?? 0,
        sales: raw.total_sales ?? 0,
        totalOrders: raw.total_orders ?? raw.total_operations ?? 0,
      });
    }
    if (opsRes?.data) {
      const ops = Array.isArray(opsRes.data) ? opsRes.data : (opsRes.data.operations || []);
      setRecentOps(ops.map((op: any) => ({
        action: op.operation_type || op.action || '未知操作',
        success: op.status === 'success' || op.status === 'completed',
        timestamp: op.timestamp || '',
        message: op.message || `商品 ${op.product_id || ''}`
      })));
    }
    if (statusRes?.data) setSysStatus(statusRes.data);
    setLastUpdated(Date.now());
  }, []);

  const fetchDashboardData = useCallback(async () => {
    try {
      setLoading(true);
      const results = await Promise.allSettled([
        getDashboardSummary(), getRecentOperations(10), getSystemStatus()
      ]);
      if (results.every(r => r.status === 'rejected')) throw new Error('所有接口均请求失败');
      applyDashboardResults(results);
    } catch (error) {
      console.error('Dashboard fetch failed:', error);
      toast.error('获取仪表盘数据失败');
    } finally {
      setLoading(false);
    }
  }, [applyDashboardResults]);

  const silentRefreshDashboard = useCallback(async () => {
    if (refreshing) return;
    setRefreshing(true);
    try {
      const results = await Promise.allSettled([
        getDashboardSummary(), getRecentOperations(10), getSystemStatus()
      ]);
      if (!results.every(r => r.status === 'rejected')) {
        applyDashboardResults(results);
      }
    } catch { /* silent */ }
    finally { setRefreshing(false); }
  }, [refreshing, applyDashboardResults]);

  const applyAnalyticsResults = useCallback((trendRes: any, topRes: any) => {
    if (trendRes?.data) {
      const td = trendRes.data.data || trendRes.data;
      setTrendData(Array.isArray(td) ? td : (td.trend || []));
    }
    if (topRes?.data) {
      const tp = topRes.data.data || topRes.data;
      setTopProducts(Array.isArray(tp) ? tp : (tp.products || []));
    }
  }, []);

  const fetchAnalyticsData = useCallback(async (silent = false) => {
    if (!silent) setAnalyticsLoading(true);
    try {
      const [trendRes, topRes] = await Promise.all([
        getTrendData(silent ? metricRef.current : metric, silent ? daysRef.current : days),
        getTopProducts(10),
      ]);
      applyAnalyticsResults(trendRes, topRes);
      if (silent) setLastUpdated(Date.now());
    } catch { if (!silent) toast.error('加载分析数据失败'); }
    finally { if (!silent) setAnalyticsLoading(false); }
  }, [metric, days, applyAnalyticsResults]);

  // Initial load
  useEffect(() => { fetchDashboardData() }, []);

  // Analytics tab data fetch on metric/days change
  useEffect(() => {
    if (activeTab === 'analytics') fetchAnalyticsData();
  }, [activeTab, metric, days]);

  // 60s auto-polling with visibility check
  useEffect(() => {
    const poll = () => {
      if (document.visibilityState !== 'visible') return;
      silentRefreshDashboard();
      if (activeTabRef.current === 'analytics') fetchAnalyticsData(true);
    };
    const id = setInterval(poll, POLL_INTERVAL);
    return () => clearInterval(id);
  }, [silentRefreshDashboard, fetchAnalyticsData]);

  // "X seconds ago" ticker
  useEffect(() => {
    if (!lastUpdated) return;
    setAgoText(formatTimeAgo(lastUpdated));
    const id = setInterval(() => setAgoText(formatTimeAgo(lastUpdated)), AGO_TICK);
    return () => clearInterval(id);
  }, [lastUpdated]);

  const handleManualRefresh = useCallback(() => {
    silentRefreshDashboard();
    if (activeTabRef.current === 'analytics') fetchAnalyticsData(true);
  }, [silentRefreshDashboard, fetchAnalyticsData]);

  if (loading) {
    return (
      <div className="xy-page p-6 xy-enter">
        <div className="flex justify-between mb-6">
          <div className="w-1/3">
            <div className="h-8 bg-xy-gray-200 rounded-lg w-1/2 mb-3 animate-pulse"></div>
            <div className="h-4 bg-xy-gray-200 rounded w-1/3 animate-pulse"></div>
          </div>
          <div className="flex gap-3">
            <div className="h-10 bg-xy-gray-200 rounded-xl w-32 animate-pulse"></div>
            <div className="h-10 bg-xy-gray-200 rounded-xl w-10 animate-pulse"></div>
          </div>
        </div>
        <div className="h-10 bg-xy-gray-200 rounded-xl w-48 mb-6 animate-pulse"></div>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 md:gap-6 mb-8">
          {[1, 2, 3, 4].map(i => (
            <div key={i} className="xy-card p-6 h-32 bg-xy-gray-100 animate-pulse border-none"></div>
          ))}
        </div>
        <div className="grid md:grid-cols-3 gap-8">
          <div className="md:col-span-2 xy-card h-96 bg-xy-gray-100 animate-pulse border-none"></div>
          <div className="space-y-6">
            <div className="xy-card h-64 bg-xy-gray-100 animate-pulse border-none"></div>
            <div className="xy-card h-32 bg-xy-gray-100 animate-pulse border-none"></div>
          </div>
        </div>
      </div>
    );
  }

  const ckh = sysStatus?.cookie_health || {};
  const cookieHealth = {
    health_score: ckh.score ?? 100,
    status: ckh.healthy === false ? 'warning' : 'good',
  };

  return (
    <div className="xy-page xy-enter">
      <SetupWizard />
      <div className="flex flex-col md:flex-row md:items-end justify-between mb-6 gap-4">
        <div>
          <h1 className="text-2xl font-bold text-xy-text-primary">工作台</h1>
          <p className="mt-1 text-xy-text-secondary flex items-center gap-2">
            <span>{meta.icon} {meta.label}</span>
            <span className="text-xy-gray-300">|</span>
            闲鱼自动化运营概览
          </p>
        </div>
        <div className="flex gap-3">
          <div className="flex items-center gap-2 bg-xy-surface px-4 py-2 rounded-xl border border-xy-border shadow-sm">
            <div className={`w-2 h-2 rounded-full ${cookieHealth.status === 'good' ? 'bg-green-500' : 'bg-yellow-500'}`}></div>
            <span className="text-sm font-medium">Cookie: {cookieHealth.health_score ?? 100}分</span>
          </div>
          <button
            onClick={handleManualRefresh}
            disabled={refreshing}
            className="p-2 bg-xy-surface border border-xy-border rounded-xl shadow-sm hover:bg-xy-gray-50 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            aria-label="刷新数据"
          >
            <RefreshCw className={`w-5 h-5 text-xy-text-secondary transition-transform ${refreshing ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      <UpdateBanner />
      <SetupGuide />

      {/* Tabs */}
      <div className="flex bg-xy-gray-100 p-1 rounded-xl mb-6 w-fit">
        {TABS.map(t => (
          <button
            key={t.key}
            onClick={() => setActiveTab(t.key)}
            className={`px-5 py-2 text-sm font-medium rounded-lg transition-colors ${
              activeTab === t.key ? 'bg-white shadow-sm text-xy-text-primary' : 'text-xy-text-secondary hover:text-xy-text-primary'
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {activeTab === 'overview' && (
        <>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 md:gap-6 mb-8">
            {[
              { label: '在售商品', value: stats.products, icon: ShoppingBag, color: 'bg-xy-brand-50', iconColor: 'text-xy-brand-500' },
              { label: '待付款订单', value: stats.orders, icon: Clock, color: 'bg-orange-50', iconColor: 'text-orange-500' },
              { label: '总销量', value: stats.sales, icon: TrendingUp, color: 'bg-blue-50', iconColor: 'text-blue-500' },
              { label: '总订单数', value: stats.totalOrders, icon: FileText, color: 'bg-green-50', iconColor: 'text-green-500' },
            ].map(card => (
              <div key={card.label} className="xy-card p-6">
                <div className="flex items-center justify-between mb-4">
                  <div className={`p-3 ${card.color} rounded-xl`}>
                    <card.icon className={`h-6 w-6 ${card.iconColor}`} />
                  </div>
                </div>
                <p className="text-sm font-medium text-xy-text-secondary mb-1">{card.label}</p>
                <p className="text-2xl md:text-3xl font-bold text-xy-text-primary">{card.value}</p>
              </div>
            ))}
          </div>
          {dataSource && (
            <p className="text-xs text-xy-text-muted mb-4 -mt-4">
              数据来源：{dataSource === 'xianguanjia_api' ? '闲管家 API（实时）' : '本地数据库（离线）'}
              {agoText && <span className="ml-1">· {agoText}更新</span>}
            </p>
          )}

          <div className="grid md:grid-cols-3 gap-8">
            <div className="md:col-span-2 xy-card overflow-hidden">
              <div className="px-6 py-4 border-b border-xy-border bg-xy-gray-50 flex justify-between items-center">
                <h2 className="text-base font-semibold text-xy-text-primary">近期自动化操作</h2>
                <button onClick={() => setActiveTab('analytics')} className="text-sm text-xy-brand-500 hover:text-xy-brand-600 font-medium">查看数据分析 &rarr;</button>
              </div>
              <div className="divide-y divide-xy-border">
                {recentOps.length === 0 ? (
                  <div className="p-12 flex flex-col items-center justify-center text-center">
                    <div className="w-16 h-16 bg-xy-gray-50 rounded-full flex items-center justify-center mb-4">
                      <Clock className="w-8 h-8 text-xy-gray-400" />
                    </div>
                    <p className="text-base font-medium text-xy-text-primary mb-1">暂无近期操作</p>
                    <p className="text-sm text-xy-text-secondary">系统自动执行的操作会显示在这里</p>
                  </div>
                ) : (
                  recentOps.map((op, idx) => (
                    <div key={idx} className="p-4 hover:bg-xy-gray-50 transition flex items-start gap-4">
                      <div className={`mt-0.5 flex-shrink-0 w-2 h-2 rounded-full ${op.success ? 'bg-green-500' : 'bg-red-500'}`}></div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center justify-between mb-1">
                          <span className="text-sm font-medium text-xy-text-primary">{op.action}</span>
                          <span className="text-xs text-xy-text-secondary">{op.timestamp}</span>
                        </div>
                        <p className="text-sm text-xy-text-secondary truncate">{op.message}</p>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>

            <div className="space-y-6">
              <div className="xy-card p-6">
                <h3 className="text-base font-semibold text-xy-text-primary mb-4">快捷操作</h3>
                <div className="space-y-3">
                  <PublishQueueCard />
                  <Link to="/products/auto-publish" className="flex items-center justify-between p-3 rounded-xl border border-xy-border hover:border-xy-brand-500 hover:bg-xy-brand-50 transition-colors group">
                    <div className="flex items-center gap-3">
                      <div className="bg-orange-100 p-2 rounded-lg group-hover:bg-orange-200 transition-colors"><Store className="w-5 h-5 text-xy-brand-600" /></div>
                      <span className="font-medium text-xy-text-primary">自动上架</span>
                    </div>
                    <span className="text-xy-brand-500">&rarr;</span>
                  </Link>
                  <Link to="/messages" className="flex items-center justify-between p-3 rounded-xl border border-xy-border hover:border-blue-500 hover:bg-blue-50 transition-colors group">
                    <div className="flex items-center gap-3">
                      <div className="bg-blue-100 p-2 rounded-lg group-hover:bg-blue-200 transition-colors"><MessageCircle className="w-5 h-5 text-blue-600" /></div>
                      <span className="font-medium text-xy-text-primary">消息中心</span>
                    </div>
                    <span className="text-blue-500">&rarr;</span>
                  </Link>
                  <Link to="/config" className="flex items-center justify-between p-3 rounded-xl border border-xy-border hover:border-green-500 hover:bg-green-50 transition-colors group">
                    <div className="flex items-center gap-3">
                      <div className="bg-green-100 p-2 rounded-lg group-hover:bg-green-200 transition-colors"><Settings className="w-5 h-5 text-green-600" /></div>
                      <span className="font-medium text-xy-text-primary">系统配置</span>
                    </div>
                    <span className="text-green-500">&rarr;</span>
                  </Link>
                </div>
              </div>
              <ApiStatusPanel />
              <SliderStatsCard />
            </div>
          </div>
        </>
      )}

      {activeTab === 'analytics' && (
        <div className="space-y-6">
          <div className="flex justify-between items-center">
            <h2 className="text-lg font-bold text-xy-text-primary flex items-center gap-2"><BarChart3 className="w-5 h-5 text-xy-brand-500" /> 数据分析</h2>
            <div className="flex gap-2">
              <select className="xy-input py-1.5 px-3 text-sm bg-white" value={days} onChange={e => setDays(Number(e.target.value))}>
                <option value={7}>过去 7 天</option>
                <option value={30}>过去 30 天</option>
                <option value={90}>过去 90 天</option>
              </select>
            </div>
          </div>

          <div className="grid md:grid-cols-3 gap-6">
            <div className="md:col-span-2 xy-card p-6">
              <div className="flex justify-between items-center mb-6">
                <h3 className="font-bold text-xy-text-primary">核心指标趋势</h3>
                <div className="flex bg-xy-gray-100 p-1 rounded-lg">
                  {[{ id: 'orders', label: '订单量' }, { id: 'completed', label: '成交量' }, { id: 'sales', label: '累计销量' }].map(m => (
                    <button key={m.id} onClick={() => setMetric(m.id)} className={`px-3 py-1 text-sm font-medium rounded-md transition-colors ${metric === m.id ? 'bg-white shadow-sm text-xy-text-primary' : 'text-xy-text-secondary hover:text-xy-text-primary'}`}>
                      {m.label}
                    </button>
                  ))}
                </div>
              </div>
              <div className="h-64 mt-4 relative">
                {analyticsLoading ? (
                  <div className="absolute inset-0 z-10 flex items-end gap-2 p-4 bg-white/80">
                    {[...Array(7)].map((_, i) => (
                      <div key={i} className="flex-1 bg-xy-gray-100 rounded-t-md animate-pulse" style={{ height: `${Math.max(20, Math.random() * 100)}%` }}></div>
                    ))}
                  </div>
                ) : trendData.length > 0 ? (
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={trendData} margin={{ top: 5, right: 10, left: -10, bottom: 0 }}>
                      <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f0f0f0" />
                      <XAxis dataKey="date" tickFormatter={v => v.slice(5)} tick={{ fontSize: 11, fill: '#9ca3af' }} axisLine={false} tickLine={false} />
                      <YAxis allowDecimals={false} tick={{ fontSize: 11, fill: '#9ca3af' }} axisLine={false} tickLine={false} />
                      <Tooltip labelFormatter={v => `日期: ${v}`} contentStyle={{ borderRadius: 8, border: '1px solid #e5e7eb', fontSize: 13 }} />
                      <Bar dataKey="value" fill="#f97316" radius={[4, 4, 0, 0]} name={metric === 'orders' ? '订单量' : metric === 'completed' ? '成交量' : '累计销量'} />
                    </BarChart>
                  </ResponsiveContainer>
                ) : (
                  <div className="w-full h-full flex flex-col items-center justify-center text-center">
                    <div className="w-12 h-12 bg-xy-gray-50 rounded-full flex items-center justify-center mb-3">
                      <Calendar className="w-6 h-6 text-xy-gray-400" />
                    </div>
                    <p className="text-sm font-medium text-xy-text-primary mb-1">暂无趋势数据</p>
                    <p className="text-xs text-xy-text-secondary">当前所选时间段内没有记录</p>
                  </div>
                )}
              </div>
            </div>

            <div className="xy-card p-0 overflow-hidden flex flex-col">
              <div className="px-6 py-4 border-b border-xy-border bg-xy-gray-50 flex items-center gap-2">
                <TrendingUp className="w-5 h-5 text-green-500" />
                <h3 className="font-bold text-xy-text-primary">近期爆款商品</h3>
              </div>
              <div className="flex-1 overflow-y-auto p-4 space-y-4">
                {analyticsLoading ? (
                  <div className="text-center py-8 text-xy-text-muted">加载中...</div>
                ) : topProducts.length > 0 ? (
                  topProducts.map((p, idx) => (
                    <div key={idx} className="flex gap-3 items-center">
                      <div className="w-6 h-6 rounded-full bg-xy-gray-100 flex items-center justify-center text-xs font-bold text-xy-text-secondary flex-shrink-0">{idx + 1}</div>
                      <div className="w-12 h-12 bg-xy-gray-200 rounded border border-xy-border overflow-hidden flex-shrink-0 flex items-center justify-center">
                        {p.pic_url ? <img src={p.pic_url} className="w-full h-full object-cover" alt="" /> : <Package className="w-5 h-5 text-xy-gray-400" />}
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium text-xy-text-primary truncate">{p.title}</p>
                        <p className="text-xs text-xy-text-secondary mt-0.5">
                          已售: {p.sold ?? p.sales ?? 0} | 库存: {p.stock ?? 0} | 价格: ¥{((p.price ?? 0) / 100).toFixed(2)}
                        </p>
                      </div>
                    </div>
                  ))
                ) : (
                  <div className="flex flex-col items-center justify-center py-12 text-center">
                    <div className="w-12 h-12 bg-xy-gray-50 rounded-full flex items-center justify-center mb-3">
                      <Package className="w-6 h-6 text-xy-gray-400" />
                    </div>
                    <p className="text-sm font-medium text-xy-text-primary mb-1">暂无商品数据</p>
                    <p className="text-xs text-xy-text-secondary">暂时没有产生数据的爆款商品</p>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default Dashboard
