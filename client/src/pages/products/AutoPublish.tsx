import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useSearchParams } from 'react-router-dom';
import { api } from '../../api/index';
import {
  getBrandAssets, getBrandAssetsGrouped, uploadBrandAsset, deleteBrandAsset,
  getPublishQueue, generateDailyQueue, updateQueueItem, deleteQueueItem,
  regenerateQueueImages, publishQueueItem, publishQueueBatch,
  type BrandAsset, type QueueItem,
} from '../../api/listing';
import toast from 'react-hot-toast';
import {
  Calendar, RefreshCw, Upload, Trash2, Image as ImageIcon,
  ChevronUp, Edit3, Clock,
  CheckCircle2, XCircle, AlertTriangle, Package, Send,
} from 'lucide-react';

// ─── Scheduler Panel ─────────────────────────────
function SchedulerPanel() {
  const [status, setStatus] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.get('/auto-publish/status')
      .then(res => { if (res.data?.ok) setStatus(res.data); })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="xy-card p-6 mb-4"><div className="h-16 bg-xy-gray-100 rounded-xl animate-pulse" /></div>;
  if (!status) return null;

  const { schedule, state, today_plan } = status;
  const actionLabels: Record<string, string> = {
    cold_start: '冷启动 — 新建链接',
    steady_replace: '稳定运营 — 替换最差链接',
    skip: '今日已执行',
  };

  return (
    <div className="xy-card p-5 mb-4 animate-in fade-in slide-in-from-top-2">
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-sm font-bold text-xy-text-primary flex items-center gap-2">
          <Calendar className="w-4 h-4 text-emerald-500" /> 自动上架调度
        </h2>
        <span className="text-[11px] px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-700 font-medium">全品类统一策略</span>
      </div>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
        <div className="bg-xy-gray-50 rounded-lg p-2.5 text-center border border-xy-border">
          <p className="text-[11px] text-xy-text-muted">运营天数</p>
          <p className="text-lg font-bold text-xy-text-primary">{state.total_days_active}</p>
        </div>
        <div className="bg-xy-gray-50 rounded-lg p-2.5 text-center border border-xy-border">
          <p className="text-[11px] text-xy-text-muted">活跃链接</p>
          <p className="text-lg font-bold text-emerald-600">{state.active_listings}/{schedule.max_active_listings}</p>
        </div>
        <div className="bg-xy-gray-50 rounded-lg p-2.5 text-center border border-xy-border">
          <p className="text-[11px] text-xy-text-muted">今日计划</p>
          <p className="text-xs font-medium text-xy-brand-600 mt-0.5">{actionLabels[today_plan?.action] || '无'}</p>
        </div>
        <div className="bg-xy-gray-50 rounded-lg p-2.5 text-center border border-xy-border">
          <p className="text-[11px] text-xy-text-muted">上次执行</p>
          <p className="text-xs font-medium text-xy-text-primary mt-0.5">{state.last_run_date || '从未'}</p>
        </div>
      </div>
    </div>
  );
}

// ─── Brand Assets Tab ─────────────────────────────
const ASSET_CATS = [
  { key: 'express', label: '快递品牌', icon: '📦', placeholder: '如：圆通、中通、韵达' },
  { key: 'freight', label: '快运品牌', icon: '🚛', placeholder: '如：德邦快运、安能、百世快运' },
] as const;

function BrandAssetsTab() {
  const [assetCat, setAssetCat] = useState<string>('express');
  const [brands, setBrands] = useState<Record<string, BrandAsset[]>>({});
  const [allAssets, setAllAssets] = useState<BrandAsset[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [newName, setNewName] = useState('');
  const fileRef = useRef<HTMLInputElement>(null);

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const [groupedRes, assetsRes] = await Promise.all([
        getBrandAssetsGrouped(assetCat),
        getBrandAssets(assetCat),
      ]);
      if (groupedRes.data?.ok) setBrands(groupedRes.data.brands || {});
      if (assetsRes.data?.ok) setAllAssets(assetsRes.data.assets || []);
    } catch {}
    setLoading(false);
  }, [assetCat]);

  useEffect(() => { fetchData(); }, [fetchData]);

  const currentCatMeta = ASSET_CATS.find(c => c.key === assetCat) || ASSET_CATS[0];

  const handleUpload = async () => {
    const file = fileRef.current?.files?.[0];
    if (!file) { toast.error('请选择图片文件'); return; }
    if (!newName.trim()) { toast.error('请输入品牌名称'); return; }
    setUploading(true);
    try {
      const res = await uploadBrandAsset(file, newName.trim(), assetCat);
      if (res.data?.ok) {
        toast.success(`已上传「${newName.trim()}」`);
        setNewName('');
        if (fileRef.current) fileRef.current.value = '';
        fetchData();
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
        fetchData();
      }
    } catch { toast.error('删除失败'); }
  };

  const brandNames = Object.keys(brands);

  return (
    <div className="space-y-6 animate-in fade-in">
      {/* Category Switcher */}
      <div className="flex gap-1 bg-xy-gray-50 p-1 rounded-xl">
        {ASSET_CATS.map(c => (
          <button key={c.key} onClick={() => setAssetCat(c.key)} className={`flex-1 flex items-center justify-center gap-1.5 py-2 px-3 rounded-lg text-sm font-medium transition-colors ${
            assetCat === c.key ? 'bg-white text-xy-brand-600 shadow-sm' : 'text-xy-text-muted hover:text-xy-text-primary'
          }`}>
            {c.icon} {c.label}
          </button>
        ))}
      </div>

      {/* Upload */}
      <div className="xy-card p-5">
        <h3 className="text-sm font-bold text-xy-text-primary mb-3 flex items-center gap-2">
          <Upload className="w-4 h-4 text-violet-500" /> 上传品牌图片
        </h3>
        <p className="text-xs text-xy-text-secondary mb-3">
          上传 {currentCatMeta.icon} {currentCatMeta.label} 的 Logo 图片，同一品牌可上传多张不同样式
        </p>
        <div className="flex items-end gap-3">
          <div className="flex-1 max-w-xs">
            <label className="xy-label text-xs">品牌名称</label>
            <input type="text" className="xy-input px-3 py-2 text-sm" placeholder={currentCatMeta.placeholder} value={newName} onChange={e => setNewName(e.target.value)} list="brand-names" />
            <datalist id="brand-names">
              {brandNames.map(n => <option key={n} value={n} />)}
            </datalist>
          </div>
          <div className="flex-1 max-w-xs">
            <label className="xy-label text-xs">Logo 图片</label>
            <input ref={fileRef} type="file" accept="image/png,image/jpeg,image/webp,image/svg+xml" className="xy-input px-3 py-1.5 text-sm file:mr-3 file:py-1 file:px-3 file:rounded-lg file:border-0 file:bg-violet-50 file:text-violet-600 file:font-medium file:text-xs" />
          </div>
          <button onClick={handleUpload} disabled={uploading} className="flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-lg bg-violet-50 border border-violet-300 text-violet-700 hover:bg-violet-100 transition-colors disabled:opacity-50">
            {uploading ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Upload className="w-4 h-4" />} 上传
          </button>
        </div>
      </div>

      {/* Grouped Brand Display */}
      <div className="xy-card p-5">
        <h3 className="text-sm font-bold text-xy-text-primary mb-3 flex items-center gap-2">
          <ImageIcon className="w-4 h-4 text-violet-500" /> {currentCatMeta.icon} {currentCatMeta.label} 素材库
          <span className="text-[11px] font-normal text-xy-text-muted">({allAssets.length} 张)</span>
        </h3>
        {loading ? (
          <div className="grid grid-cols-3 gap-3">{[1,2,3].map(i => <div key={i} className="h-24 bg-xy-gray-100 rounded-xl animate-pulse" />)}</div>
        ) : brandNames.length === 0 ? (
          <div className="text-center py-8 text-xy-text-muted text-sm border-2 border-dashed border-xy-border rounded-xl">
            暂无{currentCatMeta.label}素材，请上传品牌 Logo
          </div>
        ) : (
          <div className="space-y-4">
            {brandNames.map(brandName => (
              <div key={brandName} className="border border-xy-border rounded-xl p-3">
                <h4 className="text-sm font-medium text-xy-text-primary mb-2">{brandName} <span className="text-[11px] text-xy-text-muted">({brands[brandName].length} 张)</span></h4>
                <div className="flex flex-wrap gap-3">
                  {brands[brandName].map(asset => (
                    <div key={asset.id} className="group relative w-20 h-20 rounded-xl overflow-hidden border border-xy-border bg-white">
                      <img src={`/api/brand-assets/file/${asset.filename}`} alt={asset.name} className="w-full h-full object-contain p-1" onError={e => { (e.target as HTMLImageElement).style.display = 'none'; }} />
                      <button onClick={() => handleDelete(asset.id, asset.name)} className="absolute top-0.5 right-0.5 p-0.5 bg-white/80 rounded opacity-0 group-hover:opacity-100 transition-opacity hover:bg-red-50">
                        <Trash2 className="w-3 h-3 text-red-500" />
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

    </div>
  );
}

// ─── Queue Tab ──────────────────────────────────
const STATUS_LABELS: Record<string, { label: string; color: string; icon: React.ReactNode }> = {
  draft: { label: '草稿', color: 'bg-gray-100 text-gray-600', icon: <Edit3 className="w-3 h-3" /> },
  ready: { label: '就绪', color: 'bg-blue-100 text-blue-700', icon: <CheckCircle2 className="w-3 h-3" /> },
  publishing: { label: '发布中', color: 'bg-amber-100 text-amber-700', icon: <RefreshCw className="w-3 h-3 animate-spin" /> },
  published: { label: '已发布', color: 'bg-green-100 text-green-700', icon: <CheckCircle2 className="w-3 h-3" /> },
  failed: { label: '失败', color: 'bg-red-100 text-red-700', icon: <XCircle className="w-3 h-3" /> },
};

const CAT_BADGE: Record<string, { label: string; icon: string; cls: string }> = {
  express: { label: '快递', icon: '📦', cls: 'bg-red-50 text-red-700' },
  freight: { label: '快运', icon: '🚛', cls: 'bg-blue-50 text-blue-700' },
};

function QueueTab() {
  const [items, setItems] = useState<QueueItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [batchInterval, setBatchInterval] = useState(30);
  const [publishing, setPublishing] = useState(false);
  const [catFilter, setCatFilter] = useState<string>('all');

  const today = new Date().toLocaleDateString('en-CA');

  const fetchQueue = useCallback(async () => {
    try {
      const res = await getPublishQueue(today);
      if (res.data?.ok) setItems(res.data.items || []);
    } catch {}
    setLoading(false);
  }, [today]);

  useEffect(() => {
    fetchQueue();
  }, [fetchQueue]);

  const handleGenerate = async () => {
    setGenerating(true);
    try {
      const res = await generateDailyQueue();
      if (res.data?.ok) {
        setItems(res.data.items || []);
        toast.success(`已生成 ${res.data.items?.length || 0} 条待发布内容（快递 + 快运）`);
      }
    } catch (err: any) {
      toast.error('生成失败: ' + (err?.response?.data?.error || err.message));
    }
    setGenerating(false);
  };

  const filteredItems = catFilter === 'all' ? items : items.filter(it => it.category === catFilter);

  const handlePublishOne = async (id: string) => {
    try {
      const res = await publishQueueItem(id);
      if (res.data?.ok) {
        toast.success('发布成功');
      } else {
        toast.error('发布失败: ' + (res.data?.error || '未知错误'));
      }
      fetchQueue();
    } catch (err: any) {
      const serverError = err?.response?.data?.error || err?.message || '未知错误';
      toast.error('发布失败: ' + serverError);
      fetchQueue();
    }
  };

  const handlePublishBatch = async () => {
    const readyItems = items.filter(it => it.status === 'draft' || it.status === 'ready');
    if (readyItems.length === 0) { toast.error('没有可发布的内容'); return; }
    setPublishing(true);
    try {
      const result = await publishQueueBatch(
        readyItems.map(it => it.id),
        batchInterval,
        (done, total) => toast(`发布进度：${done}/${total}`, { id: 'batch-progress' }),
      );
      if (result.failures.length === 0) {
        toast.success(`全部 ${result.successes.length} 条发布成功`);
      } else {
        const firstError = result.failures[0]?.error || '未知错误';
        toast.error(`${result.successes.length} 成功，${result.failures.length} 失败: ${firstError}`);
      }
      fetchQueue();
    } catch (err: any) {
      const serverError = err?.response?.data?.error || err?.message || '未知错误';
      toast.error('批量发布失败: ' + serverError);
    }
    setPublishing(false);
  };

  const handleDeleteItem = async (id: string) => {
    try {
      await deleteQueueItem(id);
      toast.success('已删除');
      fetchQueue();
    } catch { toast.error('删除失败'); }
  };

  const handleRegenerate = async (id: string) => {
    try {
      const res = await regenerateQueueImages(id);
      if (res.data?.ok) {
        toast.success('图片已重新生成');
        fetchQueue();
      }
    } catch { toast.error('重新生成失败'); }
  };

  const pendingCount = filteredItems.filter(it => it.status === 'draft' || it.status === 'ready').length;
  const expressCount = items.filter(it => it.category === 'express').length;
  const freightCount = items.filter(it => it.category === 'freight').length;

  return (
    <div className="space-y-4 animate-in fade-in">
      {/* Generate or empty state */}
      {loading ? (
        <div className="xy-card p-6"><div className="h-32 bg-xy-gray-100 rounded-xl animate-pulse" /></div>
      ) : items.length === 0 ? (
        <div className="xy-card p-8 text-center">
          <Package className="w-12 h-12 text-xy-text-muted mx-auto mb-3 opacity-50" />
          <p className="text-xy-text-secondary mb-4">今日暂无待发布内容</p>
          <button onClick={handleGenerate} disabled={generating} className="xy-btn-primary px-6 py-2.5 text-sm">
            {generating ? <><RefreshCw className="w-4 h-4 animate-spin mr-2" /> 生成中...</> : '生成今日发布任务（快递 + 快运）'}
          </button>
        </div>
      ) : (
        <>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <p className="text-sm text-xy-text-secondary">
                今日 {items.length} 条，{pendingCount} 条待发布
              </p>
              <div className="flex gap-1">
                {(['all', 'express', 'freight'] as const).map(f => (
                  <button key={f} onClick={() => setCatFilter(f)} className={`px-2 py-0.5 text-[11px] rounded-md transition-colors ${
                    catFilter === f ? 'bg-xy-brand-50 text-xy-brand-600 font-medium border border-xy-brand-300' : 'text-xy-text-muted hover:bg-xy-gray-50 border border-transparent'
                  }`}>
                    {f === 'all' ? `全部 (${items.length})` : f === 'express' ? `📦 快递 (${expressCount})` : `🚛 快运 (${freightCount})`}
                  </button>
                ))}
              </div>
            </div>
            <button onClick={fetchQueue} className="text-xs text-xy-brand-600 hover:underline flex items-center gap-1">
              <RefreshCw className="w-3 h-3" /> 刷新
            </button>
          </div>

          {/* Queue Items */}
          <div className="space-y-3">
            {filteredItems.map(item => {
              const st = STATUS_LABELS[item.status] || STATUS_LABELS.draft;
              const badge = CAT_BADGE[item.category];
              const isExpanded = expandedId === item.id;
              return (
                <div key={item.id} className="xy-card overflow-hidden">
                  <div className="p-4 flex items-start gap-4">
                    {/* Thumbnail */}
                    <div className="w-20 h-20 flex-shrink-0 rounded-lg overflow-hidden bg-xy-gray-50 border border-xy-border">
                      {item.generated_images?.[0] ? (
                        <img src={`/api/generated-image?path=${encodeURIComponent(item.generated_images[0])}`} alt="" className="w-full h-full object-cover" />
                      ) : (
                        <div className="w-full h-full flex items-center justify-center text-xy-text-muted">
                          <ImageIcon className="w-6 h-6 opacity-30" />
                        </div>
                      )}
                    </div>

                    {/* Info */}
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <span className={`inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-medium ${st.color}`}>
                          {st.icon} {st.label}
                        </span>
                        {badge && (
                          <span className={`px-1.5 py-0.5 rounded text-[10px] font-medium ${badge.cls}`}>
                            {badge.icon} {badge.label}
                          </span>
                        )}
                        {item.action === 'steady_replace' && (
                          <span className="px-1.5 py-0.5 rounded bg-amber-50 text-amber-600 text-[10px]">替换</span>
                        )}
                      </div>
                      <p className="text-sm font-medium text-xy-text-primary truncate">{item.title || '未命名'}</p>
                      <p className="text-[11px] text-xy-text-muted mt-0.5">
                        {item.brand_asset_ids?.length || 0} 张品牌图
                        {item.scheduled_time && <span className="ml-2 text-indigo-500 font-medium">⏰ {item.scheduled_time}</span>}
                      </p>
                    </div>

                    {/* Actions */}
                    <div className="flex items-center gap-1.5 flex-shrink-0">
                      <button onClick={() => setExpandedId(isExpanded ? null : item.id)} className="p-1.5 rounded-lg hover:bg-xy-gray-50 text-xy-text-muted" title="编辑">
                        {isExpanded ? <ChevronUp className="w-4 h-4" /> : <Edit3 className="w-4 h-4" />}
                      </button>
                      <button onClick={() => handleRegenerate(item.id)} className="p-1.5 rounded-lg hover:bg-xy-gray-50 text-xy-text-muted" title="重新生图">
                        <RefreshCw className="w-4 h-4" />
                      </button>
                      {(item.status === 'draft' || item.status === 'ready') && (
                        <button onClick={() => handlePublishOne(item.id)} className="p-1.5 rounded-lg hover:bg-emerald-50 text-emerald-600" title="发布">
                          <Send className="w-4 h-4" />
                        </button>
                      )}
                      <button onClick={() => handleDeleteItem(item.id)} className="p-1.5 rounded-lg hover:bg-red-50 text-red-400" title="删除">
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </div>

                  {/* Expanded Editor */}
                  {isExpanded && (
                    <QueueItemEditor item={item} onSave={fetchQueue} category={item.category} />
                  )}

                  {item.error && (
                    <div className="px-4 pb-3">
                      <p className="text-xs text-red-500 flex items-center gap-1">
                        <AlertTriangle className="w-3 h-3" /> {item.error}
                      </p>
                    </div>
                  )}
                </div>
              );
            })}
          </div>

          {/* Batch Publish */}
          {pendingCount > 0 && (
            <div className="xy-card p-4 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <span className="text-sm text-xy-text-primary font-medium">一键发布全部 ({pendingCount} 条)</span>
                <div className="flex items-center gap-1.5">
                  <Clock className="w-3.5 h-3.5 text-xy-text-muted" />
                  <input type="number" min={5} max={300} className="xy-input px-2 py-1 w-16 text-sm text-center" value={batchInterval} onChange={e => setBatchInterval(Math.max(5, Number(e.target.value)))} />
                  <span className="text-[11px] text-xy-text-muted">秒间隔</span>
                </div>
              </div>
              <button onClick={handlePublishBatch} disabled={publishing} className="xy-btn-primary px-5 py-2 text-sm">
                {publishing ? <><RefreshCw className="w-4 h-4 animate-spin mr-1" /> 发布中...</> : '开始发布'}
              </button>
            </div>
          )}
        </>
      )}
    </div>
  );
}

function QueueItemEditor({ item, onSave, category }: { item: QueueItem; onSave: () => void; category: string }) {
  const [title, setTitle] = useState(item.title);
  const [desc, setDesc] = useState(item.description);
  const [price, setPrice] = useState(item.price ?? '');
  const [saving, setSaving] = useState(false);
  const [allAssets, setAllAssets] = useState<BrandAsset[]>([]);
  const [selectedAssetIds, setSelectedAssetIds] = useState<Set<string>>(new Set(item.brand_asset_ids || []));
  const [assetsChanged, setAssetsChanged] = useState(false);
  const [regenerating, setRegenerating] = useState(false);

  useEffect(() => {
    getBrandAssets(category).then(res => {
      if (res.data?.ok) setAllAssets(res.data.assets || []);
    }).catch(() => {});
  }, [category]);

  const selectAllAssets = () => {
    setSelectedAssetIds(new Set(allAssets.map(a => a.id)));
    setAssetsChanged(true);
  };

  const deselectAllAssets = () => {
    setSelectedAssetIds(new Set());
    setAssetsChanged(true);
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      const updates: Record<string, any> = { title, description: desc, price: price || null };
      if (assetsChanged) updates.brand_asset_ids = Array.from(selectedAssetIds);
      await updateQueueItem(item.id, updates);
      toast.success('已保存');
      setAssetsChanged(false);
      onSave();
    } catch { toast.error('保存失败'); }
    setSaving(false);
  };

  const handleRegenWithAssets = async () => {
    setRegenerating(true);
    try {
      await updateQueueItem(item.id, { brand_asset_ids: Array.from(selectedAssetIds) });
      await regenerateQueueImages(item.id);
      toast.success('素材已更新并重新生成图片');
      setAssetsChanged(false);
      onSave();
    } catch { toast.error('重新生成失败'); }
    setRegenerating(false);
  };

  const groupedAssets = allAssets.reduce<Record<string, BrandAsset[]>>((acc, a) => {
    (acc[a.name] = acc[a.name] || []).push(a);
    return acc;
  }, {});

  return (
    <div className="border-t border-xy-border p-4 bg-xy-gray-50 space-y-4">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <label className="xy-label text-xs">标题</label>
          <input type="text" className="xy-input px-3 py-2 text-sm" value={title} onChange={e => setTitle(e.target.value)} />
        </div>
        <div>
          <label className="xy-label text-xs">价格</label>
          <input type="number" step="0.01" className="xy-input px-3 py-2 text-sm" placeholder="留空自动" value={price} onChange={e => setPrice(e.target.value ? Number(e.target.value) : '')} />
        </div>
      </div>
      <div>
        <label className="xy-label text-xs">描述</label>
        <textarea className="xy-input px-3 py-2 text-sm h-20 resize-none" value={desc} onChange={e => setDesc(e.target.value)} />
      </div>

      {/* Brand Asset Selector */}
      <div>
        <div className="flex items-center justify-between mb-1.5">
          <label className="xy-label text-xs">品牌素材（勾选参与图片生成的品牌）</label>
          <div className="flex gap-2">
            <button onClick={selectAllAssets} className="text-[11px] text-xy-brand-600 hover:underline">全选</button>
            <button onClick={deselectAllAssets} className="text-[11px] text-red-500 hover:underline">全不选</button>
          </div>
        </div>
        {Object.keys(groupedAssets).length === 0 ? (
          <p className="text-xs text-xy-text-muted py-2">暂无品牌素材，请先在「素材管理」中上传</p>
        ) : (
          <div className="flex flex-wrap gap-2">
            {Object.entries(groupedAssets).map(([brandName, assets]) => {
              const allSelected = assets.every(a => selectedAssetIds.has(a.id));
              const someSelected = assets.some(a => selectedAssetIds.has(a.id));
              return (
                <button
                  key={brandName}
                  onClick={() => {
                    const ids = assets.map(a => a.id);
                    setSelectedAssetIds(prev => {
                      const next = new Set(prev);
                      if (allSelected) ids.forEach(id => next.delete(id));
                      else ids.forEach(id => next.add(id));
                      return next;
                    });
                    setAssetsChanged(true);
                  }}
                  className={`flex items-center gap-1.5 px-3 py-1.5 text-xs rounded-lg border transition-colors ${
                    allSelected
                      ? 'border-emerald-500 bg-emerald-50 text-emerald-700 font-medium'
                      : someSelected
                        ? 'border-amber-400 bg-amber-50 text-amber-700'
                        : 'border-xy-border text-xy-text-muted hover:border-xy-brand-300'
                  }`}
                >
                  <span className={`w-3.5 h-3.5 rounded border flex items-center justify-center text-[10px] ${
                    allSelected ? 'bg-emerald-500 border-emerald-500 text-white' : someSelected ? 'bg-amber-400 border-amber-400 text-white' : 'border-gray-300'
                  }`}>
                    {allSelected ? '✓' : someSelected ? '−' : ''}
                  </span>
                  {brandName}
                  <span className="text-[10px] opacity-60">({assets.length})</span>
                </button>
              );
            })}
          </div>
        )}
        {assetsChanged && (
          <div className="mt-2 flex items-center gap-2">
            <button
              onClick={handleRegenWithAssets}
              disabled={regenerating || selectedAssetIds.size === 0}
              className="flex items-center gap-1.5 px-3 py-1.5 text-xs rounded-lg bg-violet-50 border border-violet-300 text-violet-700 hover:bg-violet-100 transition-colors disabled:opacity-50"
            >
              {regenerating ? <RefreshCw className="w-3 h-3 animate-spin" /> : <RefreshCw className="w-3 h-3" />}
              更新素材并重新生成图片
            </button>
            <span className="text-[11px] text-xy-text-muted">已选 {selectedAssetIds.size} / {allAssets.length} 张</span>
          </div>
        )}
      </div>

      {/* Current Image */}
      {item.generated_images?.[0] && (
        <div>
          <label className="xy-label text-xs">当前图片</label>
          <img src={`/api/generated-image?path=${encodeURIComponent(item.generated_images[0])}`} alt="preview" className="w-60 h-60 object-cover rounded-xl border border-xy-border mt-1" />
        </div>
      )}

      <div className="flex justify-end gap-2">
        <button onClick={handleSave} disabled={saving} className="xy-btn-primary px-4 py-2 text-sm">
          {saving ? '保存中...' : '保存修改'}
        </button>
      </div>
    </div>
  );
}

// ─── History Tab ─────────────────────────────────
function HistoryTab() {
  const [items, setItems] = useState<QueueItem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getPublishQueue()
      .then(res => {
        if (res.data?.ok) {
          const all = res.data.items || [];
          setItems(all.filter(it => it.status === 'published' || it.status === 'failed').reverse());
        }
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="xy-card p-6"><div className="h-32 bg-xy-gray-100 rounded-xl animate-pulse" /></div>;

  if (items.length === 0) {
    return (
      <div className="xy-card p-8 text-center text-xy-text-muted text-sm">
        暂无发布记录
      </div>
    );
  }

  return (
    <div className="space-y-2 animate-in fade-in">
      {items.map(item => {
        const ok = item.status === 'published';
        const badge = CAT_BADGE[item.category];
        return (
          <div key={item.id} className="xy-card p-4 flex items-center gap-4">
            <div className="w-12 h-12 rounded-lg overflow-hidden bg-xy-gray-50 flex-shrink-0">
              {item.generated_images?.[0] ? (
                <img src={`/api/generated-image?path=${encodeURIComponent(item.generated_images[0])}`} alt="" className="w-full h-full object-cover" />
              ) : <div className="w-full h-full" />}
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-1.5 mb-0.5">
                <p className="text-sm font-medium text-xy-text-primary truncate">{item.title}</p>
              </div>
              <p className="text-[11px] text-xy-text-muted flex items-center gap-1.5">
                {badge && <span className={`px-1 py-0.5 rounded text-[10px] font-medium ${badge.cls}`}>{badge.icon} {badge.label}</span>}
                {item.scheduled_date}
              </p>
            </div>
            <span className={`px-2 py-0.5 rounded text-[10px] font-medium ${ok ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}`}>
              {ok ? '已发布' : '失败'}
            </span>
          </div>
        );
      })}
    </div>
  );
}

// ─── Main Page ──────────────────────────────────
const TABS = [
  { key: 'queue', label: '今日待发布', icon: <Send className="w-4 h-4" /> },
  { key: 'assets', label: '素材管理', icon: <ImageIcon className="w-4 h-4" /> },
  { key: 'history', label: '发布历史', icon: <Clock className="w-4 h-4" /> },
] as const;

type TabKey = typeof TABS[number]['key'];

export default function AutoPublish() {
  const [searchParams, setSearchParams] = useSearchParams();
  const initialTab = (searchParams.get('tab') as TabKey) || 'queue';
  const [activeTab, setActiveTab] = useState<TabKey>(initialTab);

  const handleTabChange = (tab: TabKey) => {
    setActiveTab(tab);
    setSearchParams({ tab });
  };

  return (
    <div className="max-w-4xl mx-auto px-4 py-6">
      <div className="mb-4">
        <h1 className="text-xl font-bold text-xy-text-primary flex items-center gap-2">
          <Package className="w-6 h-6" /> 自动上架
        </h1>
        <p className="text-sm text-xy-text-secondary mt-1">
          管理 📦 快递 + 🚛 大件快运的品牌素材、图片模板和发布计划
        </p>
      </div>

      <SchedulerPanel />

      {/* Tabs */}
      <div className="flex gap-1 mb-4 bg-xy-gray-50 p-1 rounded-xl">
        {TABS.map(tab => (
          <button key={tab.key} onClick={() => handleTabChange(tab.key)} className={`flex-1 flex items-center justify-center gap-1.5 py-2 px-3 rounded-lg text-sm font-medium transition-colors ${
            activeTab === tab.key ? 'bg-white text-xy-brand-600 shadow-sm' : 'text-xy-text-muted hover:text-xy-text-primary'
          }`}>
            {tab.icon} {tab.label}
          </button>
        ))}
      </div>

      {activeTab === 'queue' && <QueueTab />}
      {activeTab === 'assets' && <BrandAssetsTab />}
      {activeTab === 'history' && <HistoryTab />}
    </div>
  );
}
