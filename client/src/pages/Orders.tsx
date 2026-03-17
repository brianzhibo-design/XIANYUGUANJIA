import React, { useState, useEffect, useMemo } from 'react';
import { getOrders, proxyXgjApi } from '../api/xianguanjia';
import { api } from '../api/index';
import { useStoreCategory } from '../contexts/StoreCategoryContext';
import toast from 'react-hot-toast';
import {
  Receipt, Search, RefreshCw, Tag, BellRing, Truck,
  RotateCcw, Eye, X, ChevronDown, ChevronUp,
} from 'lucide-react';
import Pagination from '../components/Pagination';

const ORDER_STATUS_MAP: Record<number, { label: string; color: string }> = {
  11: { label: '待付款', color: 'bg-orange-100 text-orange-700' },
  12: { label: '待发货', color: 'bg-blue-100 text-blue-700' },
  21: { label: '已发货', color: 'bg-cyan-100 text-cyan-700' },
  22: { label: '已完成', color: 'bg-green-100 text-green-700' },
  23: { label: '已退款', color: 'bg-red-100 text-red-700' },
  24: { label: '已关闭', color: 'bg-xy-gray-100 text-xy-text-secondary' },
};

const TABS = [
  { id: 'ALL', label: '全部订单', status: undefined },
  { id: 'WAIT_PAY', label: '待付款', status: 11 },
  { id: 'WAIT_SHIP', label: '待发货', status: 12 },
  { id: 'SHIPPED', label: '已发货', status: 21 },
  { id: 'DONE', label: '已完成', status: 22 },
];

function formatTimestamp(ts: number | string | undefined): string {
  if (!ts) return '';
  const num = Number(ts);
  if (isNaN(num) || num <= 0) return '';
  const d = new Date(num * 1000);
  return d.toLocaleString('zh-CN', { year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' });
}

export default function Orders() {
  const { category } = useStoreCategory();
  const [orders, setOrders] = useState([]);
  const [loading, setLoading] = useState(true);
  const [tab, setTab] = useState('ALL');
  const [searchQuery, setSearchQuery] = useState('');
  const [actionLoading, setActionLoading] = useState({});
  const [currentPage, setCurrentPage] = useState(1);
  const PAGE_SIZE = 20;
  const [expandedOrder, setExpandedOrder] = useState(null);
  const [orderDetail, setOrderDetail] = useState(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [priceEditOrder, setPriceEditOrder] = useState(null);
  const [priceEditValue, setPriceEditValue] = useState('');

  useEffect(() => { setCurrentPage(1); fetchOrders(); }, [tab]);

  const fetchOrders = async () => {
    setLoading(true);
    try {
      const activeTab = TABS.find(t => t.id === tab);
      const payload: Record<string, any> = { page_no: 1, page_size: 50 };
      if (activeTab?.status) payload.order_status = activeTab.status;

      const res = await getOrders(payload);
      if (res.data?.ok) {
        const d = res.data.data;
        const list = Array.isArray(d) ? d : (d?.data?.list || d?.list || []);
        setOrders(list);
      }
      else toast.error(res.data?.error || '无法获取订单');
    } catch { toast.error('加载订单失败'); }
    finally { setLoading(false); }
  };

  const filteredOrders = useMemo(() => {
    if (!searchQuery.trim()) return orders;
    const q = searchQuery.toLowerCase();
    return orders.filter(o => {
      const no = o.order_no || o.order_id || '';
      const nick = o.buyer_nick || o.buyer_name || '';
      const t = o.goods?.title || o.title || '';
      return (
        (no && String(no).toLowerCase().includes(q)) ||
        (nick && nick.toLowerCase().includes(q)) ||
        (t && t.toLowerCase().includes(q))
      );
    });
  }, [orders, searchQuery]);

  const handleAdjustPrice = async (orderNo: string) => {
    if (!priceEditValue || isNaN(Number(priceEditValue))) { toast.error('请输入有效价格'); return; }
    const priceInCents = Math.round(Number(priceEditValue) * 100);
    setActionLoading(prev => ({ ...prev, [orderNo]: 'price' }));
    try {
      const res = await proxyXgjApi('/api/open/order/modify/price', { order_no: orderNo, order_price: priceInCents, express_fee: 0 });
      if (res.data?.ok) { toast.success('改价成功'); setPriceEditOrder(null); setPriceEditValue(''); fetchOrders(); }
      else toast.error(res.data?.data?.msg || res.data?.error || '改价失败');
    } catch { toast.error('改价请求失败'); }
    finally { setActionLoading(prev => ({ ...prev, [orderNo]: null })); }
  };

  const handleShip = async (orderNo: string) => {
    setActionLoading(prev => ({ ...prev, [orderNo]: 'ship' }));
    try {
      const res = await proxyXgjApi('/api/open/order/ship', { order_no: orderNo });
      if (res.data?.ok) { toast.success('发货成功'); fetchOrders(); }
      else toast.error(res.data?.data?.msg || res.data?.error || '发货失败');
    } catch { toast.error('发货请求失败'); }
    finally { setActionLoading(prev => ({ ...prev, [orderNo]: null })); }
  };

  const handleRetry = async (orderNo: string) => {
    setActionLoading(prev => ({ ...prev, [orderNo]: 'retry' }));
    try {
      const res = await api.post('/orders/retry', { order_no: orderNo });
      if (res.data?.ok || res.data?.success) { toast.success('重试发货已触发'); fetchOrders(); }
      else toast.error(res.data?.error || '重试失败');
    } catch { toast.error('重试请求失败'); }
    finally { setActionLoading(prev => ({ ...prev, [orderNo]: null })); }
  };

  const [remindStatus, setRemindStatus] = useState<Record<string, string>>({});

  const handleRemind = async (orderNo: string) => {
    setActionLoading(prev => ({ ...prev, [orderNo]: 'remind' }));
    try {
      const res = await api.post('/orders/remind', { order_no: orderNo });
      const d = res.data;
      if (d?.ok && d?.eligible) {
        if (d.message_sent) {
          toast.success('催单消息已发送');
          setRemindStatus(prev => ({ ...prev, [orderNo]: 'sent' }));
        } else {
          toast('催单已记录，下次该买家发消息时将自动发送', { icon: '📋' });
          setRemindStatus(prev => ({ ...prev, [orderNo]: 'pending' }));
        }
      } else if (d?.ok && !d?.eligible) {
        const reason = d.reason || '';
        const msg = reason.includes('silent') ? '当前处于静默时段，稍后自动发送'
          : reason.includes('cooldown') ? `催单冷却中，请${d.next_eligible || '稍后'}再试`
          : reason.includes('max') ? '今日催单次数已达上限'
          : reason.includes('dnd') ? '该买家在免打扰名单中'
          : `暂不可催单：${reason}`;
        toast(msg, { icon: '⏳' });
        setRemindStatus(prev => ({ ...prev, [orderNo]: 'cooldown' }));
      } else {
        toast.error(d?.error || '催单失败');
      }
    } catch {
      toast.error('催单请求失败');
    } finally {
      setActionLoading(prev => ({ ...prev, [orderNo]: null }));
    }
  };

  const toggleDetail = async (orderNo: string) => {
    if (expandedOrder === orderNo) {
      setExpandedOrder(null);
      setOrderDetail(null);
      return;
    }
    setExpandedOrder(orderNo);
    setDetailLoading(true);
    try {
      const res = await proxyXgjApi('/api/open/order/detail', { order_no: orderNo });
      const detail = res.data?.ok ? (res.data.data?.data || res.data.data || null) : null;
      setOrderDetail(detail);
    } catch { setOrderDetail(null); }
    finally { setDetailLoading(false); }
  };

  const formatPrice = (fee: number | string) => {
    const num = Number(fee);
    if (!num || isNaN(num)) return '¥0.00';
    return `¥${(num / 100).toFixed(2)}`;
  };

  const getStatusInfo = (status: number) => ORDER_STATUS_MAP[status] || { label: `状态${status}`, color: 'bg-xy-gray-100 text-xy-text-secondary' };

  const isVirtual = category === 'exchange' || category === 'virtual';

  return (
    <div className="xy-page xy-enter">
      <div className="flex flex-col md:flex-row justify-between md:items-end gap-4 mb-6">
        <div>
          <h1 className="xy-title">订单中心</h1>
          <p className="xy-subtitle mt-1">管理店铺订单与改价、催单操作{isVirtual ? '、虚拟品发货重试' : ''}</p>
        </div>
        <button onClick={fetchOrders} className="xy-btn-secondary px-3" aria-label="刷新订单">
          <RefreshCw className="w-4 h-4" />
        </button>
      </div>

      <div className="xy-card overflow-hidden">
        <div className="border-b border-xy-border px-4 flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="flex gap-6 overflow-x-auto whitespace-nowrap">
            {TABS.map(t => (
              <button key={t.id} onClick={() => setTab(t.id)}
                aria-selected={tab === t.id}
                role="tab"
                className={`py-4 text-sm font-medium border-b-2 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-xy-brand-500 focus-visible:ring-offset-2 ${tab === t.id ? 'border-xy-brand-500 text-xy-brand-600' : 'border-transparent text-xy-text-secondary hover:text-xy-text-primary'}`}>
                {t.label}
              </button>
            ))}
          </div>
          <div className="py-3 flex items-center gap-2 min-w-[240px]">
            <div className="relative flex-1">
              <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-xy-text-muted" />
              <input type="text" placeholder="搜索订单号/买家/商品" className="xy-input pl-9 pr-3 py-1.5 text-sm" value={searchQuery} onChange={e => setSearchQuery(e.target.value)} />
            </div>
          </div>
        </div>

        {loading ? (
          <div className="p-6 space-y-4">
            {[1, 2, 3].map(i => (
              <div key={i} className="bg-white border border-xy-border rounded-xl p-5 animate-pulse">
                <div className="flex justify-between mb-4">
                  <div className="h-5 bg-xy-gray-200 rounded w-48"></div>
                  <div className="h-5 bg-xy-gray-200 rounded w-16"></div>
                </div>
                <div className="flex gap-4">
                  <div className="w-20 h-20 bg-xy-gray-200 rounded-lg"></div>
                  <div className="flex-1 space-y-2">
                    <div className="h-5 bg-xy-gray-200 rounded w-3/4 mt-1"></div>
                    <div className="h-4 bg-xy-gray-200 rounded w-1/4 mt-3"></div>
                    <div className="h-6 bg-xy-gray-200 rounded w-24 mt-2"></div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        ) : filteredOrders.length === 0 ? (
          <div className="p-16 text-center">
            <div className="w-16 h-16 bg-xy-gray-50 rounded-full flex items-center justify-center mx-auto mb-4"><Receipt className="w-8 h-8 text-xy-gray-400" /></div>
            <h3 className="text-lg font-medium text-xy-text-primary mb-1">{searchQuery ? '未找到匹配订单' : '暂无订单'}</h3>
            <p className="text-xy-text-secondary">{searchQuery ? '请尝试其他搜索关键词' : '当前状态下没有查询到订单'}</p>
          </div>
        ) : (
          <>
          <div className="divide-y divide-xy-border">
            {filteredOrders.slice((currentPage - 1) * PAGE_SIZE, currentPage * PAGE_SIZE).map((order, idx) => {
              const statusInfo = getStatusInfo(order.order_status);
              const orderNo = order.order_no || order.order_id || `order-${(currentPage - 1) * PAGE_SIZE + idx}-${order.order_time || ''}`;
              const picUrl = order.goods?.images?.[0] || order.pic_url || '';
              const title = order.goods?.title || order.title || '未知商品';

              return (
              <div key={orderNo}>
                <div className="p-5 hover:bg-xy-gray-50 transition-colors">
                  <div className="flex flex-wrap items-center justify-between gap-4 mb-3">
                    <div className="flex items-center gap-3">
                      <span className="text-sm font-medium">订单号: {orderNo}</span>
                      <span className="text-xs text-xy-text-muted">{formatTimestamp(order.order_time)}</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className={`px-2.5 py-1 text-xs font-medium rounded-full ${statusInfo.color}`}>{statusInfo.label}</span>
                      <button onClick={() => toggleDetail(orderNo)} className="p-1 hover:bg-xy-gray-100 rounded text-xy-text-muted" title="查看详情">
                        {expandedOrder === orderNo ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                      </button>
                    </div>
                  </div>

                  <div className="flex gap-4">
                    <div className="w-20 h-20 bg-xy-gray-100 rounded-lg overflow-hidden border border-xy-border flex-shrink-0">
                      {picUrl ? (
                        <img src={picUrl} alt={title} className="w-full h-full object-cover" />
                      ) : (
                        <div className="w-full h-full flex items-center justify-center text-xy-gray-300"><Receipt className="w-8 h-8" /></div>
                      )}
                    </div>
                    <div className="flex-1 min-w-0">
                      <h3 className="text-base font-medium text-xy-text-primary truncate mb-1">{title}</h3>
                      <p className="text-sm text-xy-text-secondary mb-2">买家: {order.buyer_nick || order.buyer_name || '未知'}</p>
                      <div className="text-lg font-bold text-xy-brand-500">{formatPrice(order.total_amount ?? order.total_fee)}</div>
                    </div>

                    <div className="flex flex-col gap-2 justify-end">
                      {order.order_status === 11 && (
                        <>
                          <button
                            onClick={() => handleRemind(orderNo)}
                            disabled={actionLoading[orderNo] === 'remind'}
                            className={`xy-btn-secondary text-xs px-3 py-1.5 flex items-center gap-1.5 disabled:opacity-50 disabled:cursor-not-allowed transition-colors ${
                              remindStatus[orderNo] === 'sent' ? 'text-green-600 border-green-200' :
                              remindStatus[orderNo] === 'cooldown' ? 'text-orange-500 border-orange-200' :
                              'hover:text-blue-600 hover:border-blue-200'
                            }`}
                          >
                            <BellRing className="w-3.5 h-3.5" />
                            {actionLoading[orderNo] === 'remind' ? '催单中...' :
                             remindStatus[orderNo] === 'sent' ? '已催' :
                             remindStatus[orderNo] === 'cooldown' ? '冷却中' : '催单'}
                          </button>
                          {priceEditOrder === orderNo ? (
                            <div className="flex items-center gap-1.5">
                              <input
                                type="number" step="0.01" min="0" placeholder="元"
                                className="xy-input px-2 py-1 text-xs w-20"
                                value={priceEditValue}
                                onChange={e => setPriceEditValue(e.target.value)}
                                onKeyDown={e => { if (e.key === 'Enter') handleAdjustPrice(orderNo); if (e.key === 'Escape') { setPriceEditOrder(null); setPriceEditValue(''); } }}
                                autoFocus
                              />
                              <button onClick={() => handleAdjustPrice(orderNo)} disabled={actionLoading[orderNo] === 'price'}
                                className="px-2 py-1 text-xs font-medium rounded bg-orange-500 text-white hover:bg-orange-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors">
                                {actionLoading[orderNo] === 'price' ? '处理中...' : '确认'}
                              </button>
                              <button onClick={() => { setPriceEditOrder(null); setPriceEditValue(''); }}
                                className="p-1 text-xy-text-muted hover:text-red-500">
                                <X className="w-3.5 h-3.5" />
                              </button>
                            </div>
                          ) : (
                            <button onClick={() => { setPriceEditOrder(orderNo); setPriceEditValue(''); }}
                              className="xy-btn-secondary text-xs px-3 py-1.5 flex items-center gap-1.5 hover:text-orange-600 hover:border-orange-200">
                              <Tag className="w-3.5 h-3.5" /> 改价
                            </button>
                          )}
                        </>
                      )}
                      {order.order_status === 12 && (
                        <>
                          <button onClick={() => handleShip(orderNo)} disabled={actionLoading[orderNo] === 'ship'}
                            className="xy-btn-primary text-xs px-4 py-1.5 flex items-center gap-1.5 disabled:opacity-50 disabled:cursor-not-allowed transition-colors">
                            <Truck className="w-3.5 h-3.5" /> {actionLoading[orderNo] === 'ship' ? '发货中...' : '发货'}
                          </button>
                          {isVirtual && (
                            <button onClick={() => handleRetry(orderNo)} disabled={actionLoading[orderNo] === 'retry'}
                              className="xy-btn-secondary text-xs px-3 py-1.5 flex items-center gap-1.5 text-purple-600 hover:bg-purple-50 hover:border-purple-200 disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:bg-transparent disabled:hover:border-xy-border transition-colors">
                              <RotateCcw className="w-3.5 h-3.5" /> {actionLoading[orderNo] === 'retry' ? '重试中...' : '重试发货'}
                            </button>
                          )}
                        </>
                      )}
                    </div>
                  </div>
                </div>

                {expandedOrder === orderNo && (
                  <div className="px-5 pb-5 animate-in fade-in slide-in-from-top-2">
                    <div className="bg-xy-gray-50 rounded-xl border border-xy-border p-4">
                      {detailLoading ? (
                        <div className="text-center py-4"><RefreshCw className="w-5 h-5 animate-spin text-xy-brand-500 mx-auto" /></div>
                      ) : orderDetail ? (
                        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                          {orderDetail.buyer_nick && <div><p className="text-xy-text-muted text-xs">买家昵称</p><p className="font-medium">{orderDetail.buyer_nick}</p></div>}
                          {orderDetail.receiver_mobile && <div><p className="text-xy-text-muted text-xs">联系电话</p><p className="font-medium">{orderDetail.receiver_mobile}</p></div>}
                          {(orderDetail.prov_name || orderDetail.city_name || orderDetail.address) && (
                            <div className="col-span-2"><p className="text-xy-text-muted text-xs">收货地址</p><p className="font-medium">{[orderDetail.prov_name, orderDetail.city_name, orderDetail.area_name, orderDetail.town_name, orderDetail.address].filter(Boolean).join(' ')}</p></div>
                          )}
                          {orderDetail.waybill_no && <div><p className="text-xy-text-muted text-xs">物流单号</p><p className="font-medium">{orderDetail.waybill_no}</p></div>}
                          {orderDetail.pay_time && <div><p className="text-xy-text-muted text-xs">付款时间</p><p className="font-medium">{formatTimestamp(orderDetail.pay_time)}</p></div>}
                          {orderDetail.seller_remark && <div className="col-span-2"><p className="text-xy-text-muted text-xs">卖家备注</p><p className="font-medium">{orderDetail.seller_remark}</p></div>}
                          {orderDetail.total_amount != null && <div><p className="text-xy-text-muted text-xs">订单金额</p><p className="font-medium">{formatPrice(orderDetail.total_amount)}</p></div>}
                          {orderDetail.pay_amount != null && <div><p className="text-xy-text-muted text-xs">实付金额</p><p className="font-medium">{formatPrice(orderDetail.pay_amount)}</p></div>}
                        </div>
                      ) : (
                        <p className="text-center text-xy-text-muted py-4">暂无详细信息（需配置闲管家）</p>
                      )}
                    </div>
                  </div>
                )}
              </div>
              );
            })}
          </div>
          <Pagination current={currentPage} total={filteredOrders.length} pageSize={PAGE_SIZE} onChange={setCurrentPage} />
          </>
        )}
      </div>
    </div>
  );
}
