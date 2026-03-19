import { api } from './index';
import type { AxiosResponse } from 'axios';
import type { ApiResponse } from './index';

export interface DashboardSummary {
  active_products: number;
  pending_orders: number;
  total_sales: number;
  total_orders: number;
  source?: string;
  // 询盘与成交
  inquiries?: number;
  total_replied?: number;
  reply_rate_pct?: number;
  paid_order_count?: number | null;
  conversion_rate_pct?: number | null;
  // legacy fallback fields
  total_operations?: number;
  today_operations?: number;
  sold_products?: number;
  total_views?: number;
  total_wants?: number;
}

export interface TrendPoint {
  date: string;
  value: number;
}

export interface TopProduct {
  product_id: string;
  title: string;
  sold: number;
  price: number;
  stock: number;
  pic_url?: string;
  // legacy fallback
  status?: string;
  views?: number;
  wants?: number;
  sales?: number;
}

export const getSystemStatus = (): Promise<AxiosResponse> => api.get('/status');

export const getDashboardSummary = (): Promise<AxiosResponse<ApiResponse<DashboardSummary>>> =>
  api.get('/summary');

export const getTrendData = (metric: string, days = 30): Promise<AxiosResponse<ApiResponse<TrendPoint[]> & { trend?: TrendPoint[] }>> =>
  api.get(`/trend?metric=${metric}&days=${days}`);

export const getTopProducts = (limit = 12): Promise<AxiosResponse<ApiResponse<TopProduct[]> & { products?: TopProduct[] }>> =>
  api.get(`/top-products?limit=${limit}`);

export const getRecentOperations = (limit = 20): Promise<AxiosResponse> =>
  api.get(`/recent-operations?limit=${limit}`);

export interface UnmatchedStats {
  ok: boolean;
  total_count: number;
  top_keywords: Array<{ word: string; count: number }>;
  daily_counts: Array<{ date: string; count: number }>;
}

export const getUnmatchedStats = (): Promise<AxiosResponse<ApiResponse<UnmatchedStats>>> =>
  api.get('/unmatched-stats').catch(() => ({ data: { ok: true, total_count: 0, top_keywords: [], daily_counts: [] } }) as any);

export const serviceControl = (action: string): Promise<AxiosResponse> =>
  api.post('/service/control', { action });

export const moduleControl = (action: string, target: string): Promise<AxiosResponse> =>
  api.post('/module/control', { action, target });

export interface SliderStats {
  ok: boolean;
  total_triggers: number;
  total_attempts: number;
  passed: number;
  failed: number;
  success_rate: number;
  nc_attempts: number;
  nc_passed: number;
  nc_success_rate: number;
  puzzle_attempts: number;
  puzzle_passed: number;
  puzzle_success_rate: number;
  avg_cookie_ttl_seconds: number | null;
  screenshots: Array<{ path: string; ts: string; type: string; result: string }>;
}

export interface SliderEvent {
  id: number;
  trigger_ts: string;
  trigger_source: string;
  attempt_num: number;
  slider_type: string;
  result: string;
  fail_reason: string | null;
  screenshot_path: string | null;
  cookie_ttl_seconds: number | null;
  browser_strategy: string;
  total_duration_ms: number | null;
  nc_track_width: number | null;
  nc_drag_distance: number | null;
  puzzle_bg_found: boolean;
  puzzle_slice_found: boolean;
}

export interface RuleSuggestion {
  name: string;
  keywords: string[];
  reply: string;
  priority: number;
  reason: string;
}

export const generateRuleSuggestions = (): Promise<AxiosResponse<{ ok: boolean; suggestions: RuleSuggestion[]; analyzed_count?: number; message?: string }>> =>
  api.post('/rule-suggestions/generate');

export const applyRuleSuggestion = (rule: Omit<RuleSuggestion, 'reason'>): Promise<AxiosResponse<{ ok: boolean; message: string; rule: any }>> =>
  api.post('/rule-suggestions/apply', { rule });

export const getSliderStats = (hours = 24): Promise<AxiosResponse<SliderStats>> =>
  api.get(`/slider/stats?hours=${hours}`);

export const getSliderEvents = (limit = 50): Promise<AxiosResponse<{ ok: boolean; events: SliderEvent[] }>> =>
  api.get(`/slider/events?limit=${limit}`);
