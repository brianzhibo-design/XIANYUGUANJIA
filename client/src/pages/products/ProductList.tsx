import React, { useState, useEffect, useMemo, useCallback } from 'react';
import { getProducts, unpublishProduct, publishProduct } from '../../api/xianguanjia';
import { api } from '../../api/index';
import { useStoreCategory } from '../../contexts/StoreCategoryContext';
import toast from 'react-hot-toast';
import {
  Package, Search, Plus, RefreshCw, PowerOff, Play, ExternalLink,
  MapPin, DollarSign, Upload, Download, Save, Trash2, AlertTriangle, FileSpreadsheet,
} from 'lucide-react';
import { PieChart, Pie, Cell, BarChart, Bar, XAxis, YAxis, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { Link } from 'react-router-dom';
import Pagination from '../../components/Pagination';

const CHART_COLORS = ['#6366f1', '#f59e0b', '#10b981', '#ef4444', '#8b5cf6', '#ec4899', '#14b8a6', '#f97316'];

const SERVICE_CATEGORIES = [
  '线上快递', '线下快递', '线上快运', '线下快运',
  '同城寄', '电动车', '分销', '商家寄件',
];

const EXPRESS_COURIERS = ['圆通', '韵达', '中通', '申通', '菜鸟裹裹', '极兔', '德邦', '顺丰', '京东', '邮政'];
const FREIGHT_COURIERS = ['百世快运', '跨越速运', '壹米滴答', '顺心捷达', '中通快运', '德邦快运', '安能'];

const CATEGORY_DEFAULT_COURIERS: Record<string, string[]> = {
  '线上快递': EXPRESS_COURIERS,
  '线下快递': EXPRESS_COURIERS,
  '线上快运': FREIGHT_COURIERS,
  '线下快运': FREIGHT_COURIERS,
};

const DEFAULT_MARKUP: Record<string, CategoryMarkup> = {
  '线上快递': {
    default: { first_add: 0.90, extra_add: 0.70 },
    '圆通': { first_add: 0.90, extra_add: 0.70 },
    '韵达': { first_add: 1.20, extra_add: 0.70 },
    '中通': { first_add: 1.20, extra_add: 0.70 },
    '申通': { first_add: 1.20, extra_add: 0.70 },
    '菜鸟裹裹': { first_add: 0.90, extra_add: 0.70 },
    '极兔': { first_add: 0.90, extra_add: 0.70 },
    '德邦': { first_add: 1.20, extra_add: 0.70 },
    '顺丰': { first_add: 1.20, extra_add: 0.70 },
    '京东': { first_add: 1.20, extra_add: 0.70 },
    '邮政': { first_add: 0.60, extra_add: 0.70 },
  },
  '线下快递': { default: { first_add: 0, extra_add: 0 } },
  '线上快运': {
    default: { first_add: 8.00, extra_add: 0.45 },
    '百世快运': { first_add: 8.00, extra_add: 0.45 },
    '跨越速运': { first_add: 8.00, extra_add: 0.45 },
    '壹米滴答': { first_add: 8.00, extra_add: 0.45 },
    '顺心捷达': { first_add: 8.00, extra_add: 0.45 },
    '中通快运': { first_add: 8.00, extra_add: 0.45 },
    '德邦快运': { first_add: 9.00, extra_add: 0.45 },
    '安能': { first_add: 8.00, extra_add: 0.45 },
  },
  '线下快运': { default: { first_add: 0, extra_add: 0 } },
  '同城寄': { default: { first_add: 0, extra_add: 0 } },
  '电动车': { default: { first_add: 0, extra_add: 0 } },
  '分销': { default: { first_add: 0, extra_add: 0 } },
  '商家寄件': { default: { first_add: 0, extra_add: 0 } },
};

interface CourierSummary {
  courier: string;
  service_type: string;
  base_weight: number;
  route_count: number;
  cheapest_first: number;
  cheapest_extra: number;
  cheapest_route: string;
}

interface CategoryMarkup {
  [courier: string]: { first_add: number; extra_add: number };
}

interface CategoryDiscount {
  [courier: string]: { first_discount: number; extra_discount: number };
}

const PRODUCT_TABS = [
  { key: 'list', label: '商品列表', visible: () => true },
  { key: 'routes', label: '路线数据', visible: (cat: string) => cat === 'express' || cat === 'freight' },
  { key: 'pricing', label: '三层定价', visible: () => true },
];

export default function ProductList() {
  const { category } = useStoreCategory();
  const [activeTab, setActiveTab] = useState('list');
  const [products, setProducts] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [searchQuery, setSearchQuery] = useState('');

  const [routeStats, setRouteStats] = useState<any>(null);
  const [routeLoading, setRouteLoading] = useState(false);

  // 三层定价 state
  const [pricingCategory, setPricingCategory] = useState(SERVICE_CATEGORIES[0]);
  const [markupCategories, setMarkupCategories] = useState<Record<string, CategoryMarkup>>({});
  const [xianyuDiscount, setXianyuDiscount] = useState<Record<string, CategoryDiscount>>({});
  const [costSummary, setCostSummary] = useState<CourierSummary[]>([]);
  const [pricingLoading, setPricingLoading] = useState(false);
  const [pricingSaving, setPricingSaving] = useState(false);

  // 路线查询 state
  const [queryOrigin, setQueryOrigin] = useState('');
  const [queryDestination, setQueryDestination] = useState('');
  const [routeCostSummary, setRouteCostSummary] = useState<CourierSummary[] | null>(null);
  const [routeQuerying, setRouteQuerying] = useState(false);

  const visibleTabs = useMemo(() => PRODUCT_TABS.filter(t => t.visible(category)), [category]);

  useEffect(() => { fetchProducts(); }, [page]);
  useEffect(() => {
    if (activeTab === 'routes') fetchRouteStats();
    if (activeTab === 'pricing') fetchPricingData();
  }, [activeTab]);

  const fetchProducts = async () => {
    setLoading(true);
    try {
      const res = await getProducts(page, 20);
      if (res.data?.ok) setProducts(res.data.data?.data?.list || []);
      else toast.error(res.data?.error || '无法获取商品列表');
    } catch { toast.error('加载失败'); }
    finally { setLoading(false); }
  };

  const fetchRouteStats = async () => {
    setRouteLoading(true);
    try {
      const res = await api.get('/route-stats');
      setRouteStats(res.data?.stats || res.data);
    } catch { toast.error('加载路线数据失败'); }
    finally { setRouteLoading(false); }
  };

  const handleClearRoutes = async () => {
    if (!window.confirm('确定清空所有路线数据吗？此操作不可恢复，清空后需重新导入成本表。')) return;
    try {
      toast.loading('正在清空...', { id: 'clear_routes' });
      const res = await api.post('/reset-database', { type: 'routes' });
      if (res.data?.success) {
        toast.success('路线数据已清空', { id: 'clear_routes' });
        setRouteStats(null);
        fetchRouteStats();
      } else {
        toast.error(res.data?.error || '清空失败', { id: 'clear_routes' });
      }
    } catch { toast.error('清空路线失败', { id: 'clear_routes' }); }
  };

  const handleImportRoutes = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const fd = new FormData();
    fd.append('file', file);
    try {
      const res = await api.post('/import-routes', fd, { headers: { 'Content-Type': 'multipart/form-data' } });
      if (res.data?.success || res.data?.ok) { toast.success(`导入成功：${res.data.saved_files?.length || res.data.count || 0} 个文件`); fetchRouteStats(); }
      else toast.error(res.data?.error || '导入失败');
    } catch { toast.error('导入路线失败'); }
    e.target.value = '';
  };

  // ---- 三层定价 ----
  const fetchPricingData = useCallback(async () => {
    setPricingLoading(true);
    try {
      const [configRes, costRes] = await Promise.all([
        api.get('/get-pricing-config'),
        api.get('/get-cost-summary'),
      ]);
      const savedMarkup = configRes.data?.markup_categories || {};
      const merged: Record<string, CategoryMarkup> = {};
      for (const cat of SERVICE_CATEGORIES) {
        merged[cat] = { ...(DEFAULT_MARKUP[cat] || {}), ...(savedMarkup[cat] || {}) };
      }
      setMarkupCategories(merged);
      if (configRes.data?.xianyu_discount) setXianyuDiscount(configRes.data.xianyu_discount);
      if (costRes.data?.couriers) setCostSummary(costRes.data.couriers);
    } catch { toast.error('加载定价配置失败'); }
    finally { setPricingLoading(false); }
  }, []);

  const handleSavePricing = async () => {
    setPricingSaving(true);
    try {
      const res = await api.post('/save-pricing-config', {
        markup_categories: markupCategories,
        xianyu_discount: xianyuDiscount,
      });
      if (res.data?.success) toast.success('定价配置已保存');
      else toast.error(res.data?.error || '保存失败');
    } catch (e: any) { toast.error(e.message || '保存失败'); }
    finally { setPricingSaving(false); }
  };

  const handleQueryRouteCost = async () => {
    if (!queryOrigin.trim() || !queryDestination.trim()) {
      toast.error('请输入始发地和目的地');
      return;
    }
    setRouteQuerying(true);
    try {
      const res = await api.get('/query-route-cost', { params: { origin: queryOrigin.trim(), destination: queryDestination.trim() } });
      if (res.data?.success) {
        setRouteCostSummary(res.data.couriers || []);
        if (!res.data.couriers?.length) toast('该路线暂无成本数据', { icon: '⚠️' });
      } else {
        toast.error(res.data?.error || '查询失败');
      }
    } catch { toast.error('查询路线成本失败'); }
    finally { setRouteQuerying(false); }
  };

  const handleClearRouteQuery = () => {
    setRouteCostSummary(null);
    setQueryOrigin('');
    setQueryDestination('');
  };

  const updateCategoryMarkup = (category: string, courier: string, field: 'first_add' | 'extra_add', value: string) => {
    setMarkupCategories(prev => {
      const cat = { ...(prev[category] || {}) };
      cat[courier] = { ...(cat[courier] || { first_add: 0, extra_add: 0 }), [field]: value === '' ? 0 : Number(value) };
      return { ...prev, [category]: cat };
    });
  };

  const updateCategoryDiscount = (category: string, courier: string, field: 'first_discount' | 'extra_discount', value: string) => {
    setXianyuDiscount(prev => {
      const cat = { ...(prev[category] || {}) };
      cat[courier] = {
        ...(cat[courier] || { first_discount: 0, extra_discount: 0 }),
        [field]: value === '' ? 0 : Number(value),
      };
      return { ...prev, [category]: cat };
    });
  };

  const isFreightCategory = ['线上快运', '线下快运'].includes(pricingCategory);
  const categoryBaseWeight = isFreightCategory ? 30 : 1;

  // 当前类别下的运力列表（预设名单 + 成本表 + 配置合并，保持预设顺序在前）
  const currentCategoryCouriers = useMemo(() => {
    const preset = CATEGORY_DEFAULT_COURIERS[pricingCategory] || [];
    const costCouriers = costSummary
      .filter(c => isFreightCategory ? c.service_type === 'freight' : c.service_type === 'express')
      .map(c => c.courier);
    const markupCouriers = Object.keys(markupCategories[pricingCategory] || {}).filter(k => k !== 'default');
    const discountCouriers = Object.keys(xianyuDiscount[pricingCategory] || {}).filter(k => k !== 'default');
    const extra = new Set([...costCouriers, ...markupCouriers, ...discountCouriers]);
    extra.delete('default');
    preset.forEach(c => extra.delete(c));
    return ['default', ...preset, ...Array.from(extra).sort()];
  }, [pricingCategory, costSummary, markupCategories, xianyuDiscount, isFreightCategory]);

  const filteredProducts = useMemo(() => {
    if (!searchQuery.trim()) return products;
    const q = searchQuery.toLowerCase();
    return products.filter(p =>
      (p.title && p.title.toLowerCase().includes(q)) ||
      (p.product_id && String(p.product_id).toLowerCase().includes(q))
    );
  }, [products, searchQuery]);

  const toggleStatus = async (product: any) => {
    const isOnline = product.product_status === 22 || product.product_status === '22';
    const actionStr = isOnline ? '下架' : '重新上架';
    try {
      toast.loading(`正在${actionStr}...`, { id: 'status_toggle' });
      const res = isOnline ? await unpublishProduct(product.product_id) : await publishProduct(product.product_id);
      if (res.data?.ok) { toast.success(`${actionStr}成功`, { id: 'status_toggle' }); fetchProducts(); }
      else toast.error(res.data?.error || `${actionStr}失败`, { id: 'status_toggle' });
    } catch { toast.error(`${actionStr}出错`, { id: 'status_toggle' }); }
  };

  const formatPrice = (price: any) => {
    const num = Number(price);
    if (!num || isNaN(num)) return '¥0.00';
    return `¥${(num / 100).toFixed(2)}`;
  };

  const addPricingCourier = () => {
    const name = window.prompt('请输入运力名称（如：圆通、中通、百世快运）');
    if (!name?.trim()) return;
    const key = name.trim();
    const existing = currentCategoryCouriers.includes(key);
    if (existing) { toast.error('该运力已存在'); return; }
    setMarkupCategories(prev => {
      const cat = { ...(prev[pricingCategory] || {}) };
      cat[key] = { first_add: 0, extra_add: 0 };
      return { ...prev, [pricingCategory]: cat };
    });
    setXianyuDiscount(prev => {
      const cat = { ...(prev[pricingCategory] || {}) };
      cat[key] = { first_discount: 0, extra_discount: 0 };
      return { ...prev, [pricingCategory]: cat };
    });
  };

  const removePricingCourier = (courier: string) => {
    if (courier === 'default') return;
    setMarkupCategories(prev => {
      const cat = { ...(prev[pricingCategory] || {}) };
      delete cat[courier];
      return { ...prev, [pricingCategory]: cat };
    });
    setXianyuDiscount(prev => {
      const cat = { ...(prev[pricingCategory] || {}) };
      delete cat[courier];
      return { ...prev, [pricingCategory]: cat };
    });
  };

  const activeCostData = routeCostSummary ?? costSummary;

  const getCheapestCost = (courier: string): { firstCost: number | null; extraCost: number | null } => {
    const match = activeCostData.find(
      c => c.courier === courier && (isFreightCategory ? c.service_type === 'freight' : c.service_type === 'express')
    );
    if (!match) return { firstCost: null, extraCost: null };
    return { firstCost: match.cheapest_first, extraCost: match.cheapest_extra };
  };

  const filteredCostSummary = activeCostData.filter(c =>
    isFreightCategory ? c.service_type === 'freight' : c.service_type === 'express'
  );

  return (
    <div className="xy-page xy-enter">
      <div className="flex flex-col md:flex-row justify-between md:items-end gap-4 mb-6">
        <div>
          <h1 className="xy-title">商品管理</h1>
          <p className="xy-subtitle mt-1">管理闲鱼在售商品，或使用 AI 辅助发布新商品</p>
        </div>
        <div className="flex gap-3">
          <button onClick={() => { if (activeTab === 'list') fetchProducts(); else if (activeTab === 'routes') fetchRouteStats(); else if (activeTab === 'pricing') fetchPricingData(); }} className="xy-btn-secondary px-3" aria-label="刷新">
            <RefreshCw className="w-4 h-4" />
          </button>
          <Link to="/products/auto-publish" className="xy-btn-primary flex items-center gap-2">
            <Plus className="w-4 h-4" /> 自动上架
          </Link>
        </div>
      </div>

      {visibleTabs.length > 1 && (
        <div className="flex bg-xy-gray-100 p-1 rounded-xl mb-6 w-fit">
          {visibleTabs.map(t => (
            <button key={t.key} onClick={() => setActiveTab(t.key)}
              aria-selected={activeTab === t.key}
              role="tab"
              className={`px-5 py-2 text-sm font-medium rounded-lg transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-xy-brand-500 focus-visible:ring-offset-2 ${activeTab === t.key ? 'bg-white shadow-sm text-xy-text-primary' : 'text-xy-text-secondary hover:text-xy-text-primary'}`}>
              {t.label}
            </button>
          ))}
        </div>
      )}

      {activeTab === 'list' && (
        <div className="xy-card overflow-hidden">
          <div className="border-b border-xy-border px-4 py-3 bg-xy-gray-50 flex items-center gap-2">
            <div className="relative flex-1 max-w-sm">
              <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-xy-text-muted" />
              <input type="text" placeholder="搜索商品标题或 ID" className="xy-input pl-9 pr-3 py-1.5 text-sm" value={searchQuery} onChange={e => setSearchQuery(e.target.value)} />
            </div>
          </div>

          {loading ? (
            <div className="p-5 space-y-4">
              {[1, 2, 3, 4].map(i => (
                <div key={i} className="flex flex-col md:flex-row gap-5 p-4 border border-transparent rounded-xl animate-pulse">
                  <div className="w-24 h-24 bg-xy-gray-100 rounded-lg flex-shrink-0"></div>
                  <div className="flex-1 space-y-3 py-1">
                    <div className="h-5 bg-xy-gray-100 rounded w-2/3"></div>
                    <div className="flex gap-4 mt-4">
                      <div className="h-6 bg-xy-gray-100 rounded w-16"></div>
                      <div className="h-5 bg-xy-gray-100 rounded w-16 mt-0.5"></div>
                    </div>
                    <div className="h-3 bg-xy-gray-100 rounded w-24 mt-2"></div>
                  </div>
                  <div className="flex flex-col items-end gap-2 flex-shrink-0 py-1">
                    <div className="h-8 bg-xy-gray-100 rounded w-16"></div>
                    <div className="h-4 bg-xy-gray-100 rounded w-20 mt-1"></div>
                  </div>
                </div>
              ))}
            </div>
          ) : filteredProducts.length === 0 ? (
            <div className="p-16 text-center">
              <div className="w-16 h-16 bg-xy-gray-50 rounded-full flex items-center justify-center mx-auto mb-4"><Package className="w-8 h-8 text-xy-gray-400" /></div>
              <h3 className="text-lg font-medium text-xy-text-primary mb-1">{searchQuery ? '未找到匹配商品' : '还没有商品'}</h3>
              <p className="text-xy-text-secondary mb-6">{searchQuery ? '请尝试其他搜索关键词' : '点击右上角按钮开始 AI 智能上架'}</p>
              {!searchQuery && <Link to="/products/auto-publish" className="xy-btn-primary">去发布商品</Link>}
            </div>
          ) : (
            <>
            <div className="divide-y divide-xy-border">
              {filteredProducts.slice((page - 1) * 20, page * 20).map(p => {
                const isOnline = p.product_status === 22 || p.product_status === '22';
                return (
                  <div key={p.product_id} className="p-5 hover:bg-xy-gray-50 transition-colors flex flex-col md:flex-row gap-5">
                    <div className="w-24 h-24 bg-xy-gray-100 rounded-lg overflow-hidden border border-xy-border flex-shrink-0 relative">
                      {(p.pic_url || (Array.isArray(p.images) && p.images[0])) ? (
                        <img
                          src={p.pic_url || (Array.isArray(p.images) && p.images[0]) || ''}
                          alt={p.title || ''}
                          className="w-full h-full object-cover"
                          onError={(e) => { (e.target as HTMLImageElement).style.display = 'none'; }}
                        />
                      ) : (
                        <div className="w-full h-full flex items-center justify-center text-xy-text-tertiary">
                          <svg className="w-8 h-8" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" /></svg>
                        </div>
                      )}
                      {!isOnline && <div className="absolute inset-0 bg-black/40 flex items-center justify-center"><span className="text-white text-xs font-bold px-2 py-1 bg-black/50 rounded">已下架</span></div>}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-start justify-between gap-4">
                        <div>
                          <h3 className="text-base font-medium text-xy-text-primary mb-2 line-clamp-2 leading-snug">{p.title}</h3>
                          <div className="flex flex-wrap items-center gap-4 text-sm text-xy-text-secondary mb-2">
                            <span className="text-lg font-bold text-xy-brand-500">{formatPrice(p.price)}</span>
                            <span className="bg-xy-gray-100 px-2 py-0.5 rounded text-xs">库存: {p.stock ?? 1}</span>
                            {p.view_count != null && <span>浏览 {p.view_count}</span>}
                            {p.want_count != null && <span>想要 {p.want_count}</span>}
                          </div>
                          <p className="text-xs text-xy-text-muted">ID: {p.product_id}</p>
                        </div>
                        <div className="flex flex-col items-end gap-2 flex-shrink-0">
                          {isOnline ? (
                            <button onClick={() => toggleStatus(p)} className="xy-btn-secondary text-xs px-3 py-1.5 flex items-center gap-1.5 text-red-600 hover:bg-red-50 hover:border-red-200">
                              <PowerOff className="w-3.5 h-3.5" /> 下架
                            </button>
                          ) : (
                            <button onClick={() => toggleStatus(p)} className="xy-btn-secondary text-xs px-3 py-1.5 flex items-center gap-1.5 text-green-600 hover:bg-green-50 hover:border-green-200">
                              <Play className="w-3.5 h-3.5" /> 上架
                            </button>
                          )}
                          <a href={`https://h5.m.goofish.com/app/idleFish-F2e/fish-mini-item/pages/detail?id=${p.product_id}`} target="_blank" rel="noreferrer" className="text-xs text-blue-500 hover:text-blue-600 flex items-center gap-1 mt-1">
                            查看闲鱼详情 <ExternalLink className="w-3 h-3" />
                          </a>
                        </div>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
            <Pagination current={page} total={filteredProducts.length} pageSize={20} onChange={setPage} />
            </>
          )}
        </div>
      )}

      {activeTab === 'routes' && (
        <div className="space-y-6 animate-in fade-in slide-in-from-right-4">
          <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3">
            <h2 className="text-lg font-bold text-xy-text-primary flex items-center gap-2"><MapPin className="w-5 h-5 text-green-500" /> 快递路线数据</h2>
            <div className="flex flex-wrap gap-2">
              <label className="xy-btn-secondary text-sm px-3 py-1.5 flex items-center gap-1.5 cursor-pointer">
                <Upload className="w-4 h-4" /> 导入路线
                <input type="file" accept=".csv,.xlsx,.zip" className="hidden" onChange={handleImportRoutes} />
              </label>
              <a href="/api/export-routes" download className="xy-btn-secondary text-sm px-3 py-1.5 flex items-center gap-1.5">
                <Download className="w-4 h-4" /> 导出路线
              </a>
              {routeStats && (routeStats.routes > 0 || routeStats.tables > 0) && (
                <button onClick={handleClearRoutes} className="xy-btn-secondary text-sm px-3 py-1.5 flex items-center gap-1.5 text-red-600 hover:bg-red-50 hover:border-red-200">
                  <Trash2 className="w-4 h-4" /> 清空路线
                </button>
              )}
            </div>
          </div>

          {routeLoading ? (
            <div className="xy-card p-12 text-center"><RefreshCw className="w-6 h-6 animate-spin text-xy-brand-500 mx-auto" /></div>
          ) : routeStats ? (
            <>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                {[
                  { label: '总路线数', value: (routeStats.routes ?? 0).toLocaleString() },
                  { label: '快递公司', value: routeStats.couriers ?? 0 },
                  { label: '成本表文件', value: routeStats.tables ?? 0 },
                  { label: '最后更新', value: routeStats.last_updated ?? '-' },
                ].map(s => (
                  <div key={s.label} className="xy-card p-5 text-center">
                    <p className="text-2xl font-bold text-xy-text-primary">{s.value}</p>
                    <p className="text-sm text-xy-text-secondary mt-1">{s.label}</p>
                  </div>
                ))}
              </div>

              {routeStats.courier_details && Object.keys(routeStats.courier_details).length > 0 && (() => {
                const chartData = Object.entries(routeStats.courier_details)
                  .map(([name, count]) => ({ name, count: Number(count) }))
                  .sort((a, b) => b.count - a.count);
                const totalRoutes = chartData.reduce((sum, d) => sum + d.count, 0);
                return (
                  <>
                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                      <div className="xy-card p-5">
                        <h3 className="text-sm font-semibold text-xy-text-secondary mb-4">快递公司路线分布</h3>
                        <ResponsiveContainer width="100%" height={280}>
                          <PieChart>
                            <Pie data={chartData} dataKey="count" nameKey="name" cx="50%" cy="50%" outerRadius={100} label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`} labelLine={false}>
                              {chartData.map((_, i) => <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />)}
                            </Pie>
                            <Tooltip formatter={(v: number) => v.toLocaleString()} />
                            <Legend />
                          </PieChart>
                        </ResponsiveContainer>
                      </div>

                      <div className="xy-card p-5">
                        <h3 className="text-sm font-semibold text-xy-text-secondary mb-4">各公司路线数对比</h3>
                        <ResponsiveContainer width="100%" height={280}>
                          <BarChart data={chartData} margin={{ top: 5, right: 20, bottom: 5, left: 0 }}>
                            <XAxis dataKey="name" tick={{ fontSize: 12 }} />
                            <YAxis tick={{ fontSize: 12 }} tickFormatter={(v: number) => v >= 1000 ? `${(v / 1000).toFixed(0)}k` : String(v)} />
                            <Tooltip formatter={(v: number) => v.toLocaleString()} />
                            <Bar dataKey="count" name="路线数" radius={[4, 4, 0, 0]}>
                              {chartData.map((_, i) => <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />)}
                            </Bar>
                          </BarChart>
                        </ResponsiveContainer>
                      </div>
                    </div>

                    <div className="xy-card overflow-hidden">
                      <div className="px-4 py-3 border-b border-xy-border bg-xy-gray-50">
                        <h3 className="text-sm font-semibold text-xy-text-secondary">快递公司明细</h3>
                      </div>
                      <div className="divide-y divide-xy-border">
                        {chartData.map((item, i) => {
                          const pct = totalRoutes > 0 ? ((item.count / totalRoutes) * 100).toFixed(1) : 0;
                          return (
                            <div key={item.name} className="px-4 py-3 flex items-center gap-4">
                              <div className="w-3 h-3 rounded-full flex-shrink-0" style={{ backgroundColor: CHART_COLORS[i % CHART_COLORS.length] }} />
                              <span className="text-sm font-medium text-xy-text-primary w-20">{item.name}</span>
                              <div className="flex-1">
                                <div className="w-full bg-xy-gray-100 rounded-full h-2">
                                  <div className="h-2 rounded-full transition-all" style={{ width: `${pct}%`, backgroundColor: CHART_COLORS[i % CHART_COLORS.length] }} />
                                </div>
                              </div>
                              <span className="text-sm text-xy-text-secondary w-24 text-right">{item.count.toLocaleString()} 条</span>
                              <span className="text-sm text-xy-text-muted w-14 text-right">{pct}%</span>
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  </>
                );
              })()}

              {routeStats.files && routeStats.files.length > 0 && (
                <div className="xy-card p-5">
                  <h3 className="text-sm font-semibold text-xy-text-secondary mb-3 flex items-center gap-2">
                    <FileSpreadsheet className="w-4 h-4" /> 已导入文件 ({routeStats.files.length})
                  </h3>
                  <div className="flex flex-wrap gap-2">
                    {routeStats.files.map((f: string) => (
                      <span key={f} className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-xy-gray-50 border border-xy-border rounded-lg text-xs text-xy-text-secondary">
                        <FileSpreadsheet className="w-3.5 h-3.5 text-green-500" />
                        {f}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {routeStats.parse_error && (
                <div className="xy-card p-4 border-amber-200 bg-amber-50 flex items-start gap-3">
                  <AlertTriangle className="w-5 h-5 text-amber-500 flex-shrink-0 mt-0.5" />
                  <div>
                    <p className="text-sm font-medium text-amber-800">部分文件解析出错</p>
                    <p className="text-xs text-amber-600 mt-1">{routeStats.parse_error}</p>
                  </div>
                </div>
              )}
            </>
          ) : (
            <div className="xy-card p-12 text-center text-xy-text-muted">
              <MapPin className="w-12 h-12 mx-auto mb-3 text-xy-gray-300" />
              <p>暂无路线数据，请先导入路线文件</p>
            </div>
          )}
        </div>
      )}

      {activeTab === 'pricing' && (
        <div className="space-y-6 animate-in fade-in slide-in-from-right-4">
          <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3">
            <h2 className="text-lg font-bold text-xy-text-primary flex items-center gap-2">
              <DollarSign className="w-5 h-5 text-amber-500" /> 三层定价管理
            </h2>
            <div className="flex gap-2">
              <button onClick={fetchPricingData} className="xy-btn-secondary text-sm px-3 py-1.5 flex items-center gap-1.5">
                <RefreshCw className="w-4 h-4" /> 刷新
              </button>
              <button onClick={handleSavePricing} disabled={pricingSaving} className="xy-btn-primary text-sm px-4 py-1.5 flex items-center gap-1.5">
                {pricingSaving ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
                保存
              </button>
            </div>
          </div>

          {/* 服务类别 tabs */}
          <div className="flex flex-wrap bg-xy-gray-100 p-1 rounded-xl gap-1">
            {SERVICE_CATEGORIES.map(cat => (
              <button key={cat} onClick={() => setPricingCategory(cat)}
                className={`px-4 py-1.5 text-xs font-medium rounded-lg transition-colors ${pricingCategory === cat ? 'bg-white shadow-sm text-xy-text-primary' : 'text-xy-text-secondary hover:text-xy-text-primary'}`}>
                {cat}
              </button>
            ))}
          </div>

          {pricingLoading ? (
            <div className="xy-card p-12 text-center"><RefreshCw className="w-6 h-6 animate-spin text-xy-brand-500 mx-auto" /></div>
          ) : (
            <div className="space-y-4">
              {/* 公式说明 */}
              <div className="xy-card p-4 bg-blue-50 border-blue-200 text-sm text-blue-800">
                <p className="font-medium mb-1">三层定价公式 — {pricingCategory}
                  {isFreightCategory && <span className="ml-2 px-2 py-0.5 bg-blue-100 rounded text-xs font-bold">首重 {categoryBaseWeight}kg 起</span>}
                </p>
                <p>小程序价首重 = 成本首重 + 首重加价 | 小程序价续重 = 成本续重 + 续重加价</p>
                <p>闲鱼价首重 = 小程序价首重 - 首重让利 | 闲鱼价续重 = 小程序价续重 - 续重让利</p>
                <p className="text-blue-600 mt-1">闲鱼最终价 = 闲鱼首重价 + max(0, 计费重 - {categoryBaseWeight}kg) × 闲鱼续重价</p>
              </div>

              {/* 路线查询 + 成本表 */}
              <div className="xy-card overflow-hidden">
                <div className="px-4 py-3 border-b border-xy-border bg-xy-gray-50 space-y-2">
                  <div className="flex items-center justify-between">
                    <h3 className="text-sm font-semibold text-xy-text-secondary">
                      {routeCostSummary
                        ? <>指定路线成本：<span className="text-xy-brand-600">{queryOrigin} → {queryDestination}</span></>
                        : '成本表（只读，来自 xlsx）'}
                      {isFreightCategory
                        ? <span className="ml-2 text-xs px-1.5 py-0.5 bg-amber-100 text-amber-700 rounded">大件/快运 首重30kg</span>
                        : <span className="ml-2 text-xs px-1.5 py-0.5 bg-blue-100 text-blue-700 rounded">快递 首重1kg</span>}
                    </h3>
                  </div>
                  <div className="flex items-center gap-2 flex-wrap">
                    <input type="text" placeholder="始发地（如：江西）" className="xy-input px-2.5 py-1 text-sm w-32"
                      value={queryOrigin} onChange={e => setQueryOrigin(e.target.value)}
                      onKeyDown={e => e.key === 'Enter' && handleQueryRouteCost()} />
                    <span className="text-xy-text-muted text-sm">→</span>
                    <input type="text" placeholder="目的地（如：广东）" className="xy-input px-2.5 py-1 text-sm w-32"
                      value={queryDestination} onChange={e => setQueryDestination(e.target.value)}
                      onKeyDown={e => e.key === 'Enter' && handleQueryRouteCost()} />
                    <button onClick={handleQueryRouteCost} disabled={routeQuerying}
                      className="xy-btn-primary text-xs px-3 py-1.5 flex items-center gap-1">
                      {routeQuerying ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <Search className="w-3.5 h-3.5" />}
                      查询
                    </button>
                    {routeCostSummary && (
                      <button onClick={handleClearRouteQuery} className="xy-btn-secondary text-xs px-3 py-1.5 flex items-center gap-1">
                        <Trash2 className="w-3.5 h-3.5" /> 清除
                      </button>
                    )}
                  </div>
                </div>
                <div className="overflow-x-auto">
                  <table className="w-full text-sm whitespace-nowrap">
                    <thead>
                      <tr className="bg-xy-gray-50 border-b border-xy-border">
                        <th className="text-left px-4 py-2 font-medium text-xy-text-secondary">运力</th>
                        <th className="text-left px-4 py-2 font-medium text-xy-text-secondary">首重(kg)</th>
                        <th className="text-left px-4 py-2 font-medium text-xy-text-secondary">{routeCostSummary ? '首重成本' : '最低首重成本'}</th>
                        <th className="text-left px-4 py-2 font-medium text-xy-text-secondary">{routeCostSummary ? '续重成本' : '最低续重成本'}</th>
                        <th className="text-left px-4 py-2 font-medium text-xy-text-secondary">{routeCostSummary ? '匹配路线' : '最低路线'}</th>
                        <th className="text-left px-4 py-2 font-medium text-xy-text-secondary">{routeCostSummary ? '匹配数' : '路线数'}</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-xy-border">
                      {filteredCostSummary.map(c => (
                        <tr key={c.courier} className="hover:bg-xy-gray-50">
                          <td className="px-4 py-2 font-medium text-xy-text-primary">{c.courier}</td>
                          <td className="px-4 py-2 text-xy-text-secondary">{c.base_weight}</td>
                          <td className="px-4 py-2 text-xy-text-secondary font-mono">{c.cheapest_first != null ? c.cheapest_first.toFixed(2) : '-'}</td>
                          <td className="px-4 py-2 text-xy-text-secondary font-mono">{c.cheapest_extra != null ? c.cheapest_extra.toFixed(2) : '-'}</td>
                          <td className="px-4 py-2 text-xy-text-muted text-xs">{c.cheapest_route || '-'}</td>
                          <td className="px-4 py-2 text-xy-text-secondary">{c.route_count}</td>
                        </tr>
                      ))}
                      {filteredCostSummary.length === 0 && (
                        <tr><td colSpan={6} className="px-4 py-6 text-center text-xy-text-muted">暂无该类别的成本数据</td></tr>
                      )}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* 加价表（可编辑） */}
              <div className="xy-card overflow-hidden">
                <div className="px-4 py-3 border-b border-xy-border bg-xy-gray-50 flex justify-between items-center">
                  <h3 className="text-sm font-semibold text-xy-text-secondary">
                    加价表（可编辑）— {pricingCategory}
                    {isFreightCategory && <span className="ml-2 text-xs px-1.5 py-0.5 bg-amber-100 text-amber-700 rounded">首重{categoryBaseWeight}kg起</span>}
                    {routeCostSummary && <span className="ml-2 text-xs px-1.5 py-0.5 bg-green-100 text-green-700 rounded">基于 {queryOrigin}→{queryDestination} 路线</span>}
                  </h3>
                  <button onClick={addPricingCourier} className="xy-btn-secondary text-xs px-2.5 py-1 flex items-center gap-1">
                    <Plus className="w-3.5 h-3.5" /> 添加运力
                  </button>
                </div>
                <div className="overflow-x-auto">
                  <table className="w-full text-sm whitespace-nowrap">
                    <thead>
                      <tr className="bg-xy-gray-50 border-b border-xy-border">
                        <th className="text-left px-4 py-2 font-medium text-xy-text-secondary">运力</th>
                        <th className="text-left px-4 py-2 font-medium text-xy-text-secondary">
                          首重加价{isFreightCategory ? <span className="text-xs text-amber-600 ml-1">(元/{categoryBaseWeight}kg起)</span> : <span className="text-xs text-xy-text-muted ml-1">(元)</span>}
                        </th>
                        <th className="text-left px-4 py-2 font-medium text-xy-text-secondary">
                          续重加价<span className="text-xs text-xy-text-muted ml-1">(元/kg)</span>
                        </th>
                        <th className="text-left px-4 py-2 font-medium text-xy-text-secondary text-green-600">小程序首重价</th>
                        <th className="text-left px-4 py-2 font-medium text-xy-text-secondary text-green-600">小程序续重价</th>
                        <th className="text-right px-4 py-2 font-medium text-xy-text-secondary">操作</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-xy-border">
                      {currentCategoryCouriers.map(courier => {
                        const rule = (markupCategories[pricingCategory] || {})[courier] || { first_add: 0, extra_add: 0 };
                        const { firstCost, extraCost } = courier === 'default' ? { firstCost: null, extraCost: null } : getCheapestCost(courier);
                        const miniFirst = firstCost != null ? (firstCost + (rule.first_add ?? 0)).toFixed(2) : '-';
                        const miniExtra = extraCost != null ? (extraCost + (rule.extra_add ?? 0)).toFixed(2) : '-';
                        return (
                          <tr key={courier} className="hover:bg-xy-gray-50">
                            <td className="px-4 py-2">
                              <span className={`text-sm font-medium ${courier === 'default' ? 'text-xy-brand-600' : 'text-xy-text-primary'}`}>
                                {courier === 'default' ? '默认' : courier}
                              </span>
                            </td>
                            <td className="px-4 py-2">
                              <input type="number" step="0.01" className="xy-input px-2 py-1 text-sm w-24"
                                value={rule.first_add ?? 0}
                                onChange={e => updateCategoryMarkup(pricingCategory, courier, 'first_add', e.target.value)} />
                            </td>
                            <td className="px-4 py-2">
                              <input type="number" step="0.01" className="xy-input px-2 py-1 text-sm w-24"
                                value={rule.extra_add ?? 0}
                                onChange={e => updateCategoryMarkup(pricingCategory, courier, 'extra_add', e.target.value)} />
                            </td>
                            <td className="px-4 py-2 text-green-700 font-mono text-xs">{miniFirst}</td>
                            <td className="px-4 py-2 text-green-700 font-mono text-xs">{miniExtra}</td>
                            <td className="px-4 py-2 text-right">
                              {courier !== 'default' && (
                                <button onClick={() => removePricingCourier(courier)} className="p-1 text-red-500 hover:bg-red-50 rounded" title="删除">
                                  <Trash2 className="w-3.5 h-3.5" />
                                </button>
                              )}
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* 让利表（可编辑） */}
              <div className="xy-card overflow-hidden">
                <div className="px-4 py-3 border-b border-xy-border bg-xy-gray-50">
                  <h3 className="text-sm font-semibold text-xy-text-secondary">
                    闲鱼让利表（可编辑）— {pricingCategory}
                    {routeCostSummary && <span className="ml-2 text-xs px-1.5 py-0.5 bg-orange-100 text-orange-700 rounded">基于 {queryOrigin}→{queryDestination} 路线</span>}
                  </h3>
                </div>
                <div className="overflow-x-auto">
                  <table className="w-full text-sm whitespace-nowrap">
                    <thead>
                      <tr className="bg-xy-gray-50 border-b border-xy-border">
                        <th className="text-left px-4 py-2 font-medium text-xy-text-secondary">运力</th>
                        <th className="text-left px-4 py-2 font-medium text-xy-text-secondary">首重让利</th>
                        <th className="text-left px-4 py-2 font-medium text-xy-text-secondary">续重让利</th>
                        <th className="text-left px-4 py-2 font-medium text-xy-text-secondary text-orange-600">闲鱼首重价</th>
                        <th className="text-left px-4 py-2 font-medium text-xy-text-secondary text-orange-600">闲鱼续重价</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-xy-border">
                      {currentCategoryCouriers.map(courier => {
                        const discountRule = (xianyuDiscount[pricingCategory] || {})[courier] || { first_discount: 0, extra_discount: 0 };
                        const markupRule = (markupCategories[pricingCategory] || {})[courier] || { first_add: 0, extra_add: 0 };
                        const { firstCost, extraCost } = courier === 'default' ? { firstCost: null, extraCost: null } : getCheapestCost(courier);
                        const miniFirst = firstCost != null ? firstCost + (markupRule.first_add ?? 0) : null;
                        const miniExtra = extraCost != null ? extraCost + (markupRule.extra_add ?? 0) : null;
                        const xyFirst = miniFirst != null ? Math.max(0, miniFirst - (discountRule.first_discount ?? 0)).toFixed(2) : '-';
                        const xyExtra = miniExtra != null ? Math.max(0, miniExtra - (discountRule.extra_discount ?? 0)).toFixed(2) : '-';
                        return (
                          <tr key={courier} className="hover:bg-xy-gray-50">
                            <td className="px-4 py-2">
                              <span className={`text-sm font-medium ${courier === 'default' ? 'text-xy-brand-600' : 'text-xy-text-primary'}`}>
                                {courier === 'default' ? '默认' : courier}
                              </span>
                            </td>
                            <td className="px-4 py-2">
                              <input type="number" step="0.01" className="xy-input px-2 py-1 text-sm w-24"
                                value={discountRule.first_discount ?? 0}
                                onChange={e => updateCategoryDiscount(pricingCategory, courier, 'first_discount', e.target.value)} />
                            </td>
                            <td className="px-4 py-2">
                              <input type="number" step="0.01" className="xy-input px-2 py-1 text-sm w-24"
                                value={discountRule.extra_discount ?? 0}
                                onChange={e => updateCategoryDiscount(pricingCategory, courier, 'extra_discount', e.target.value)} />
                            </td>
                            <td className="px-4 py-2 text-orange-700 font-mono text-xs">{xyFirst}</td>
                            <td className="px-4 py-2 text-orange-700 font-mono text-xs">{xyExtra}</td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}
        </div>
      )}

    </div>
  );
}
