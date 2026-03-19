import { api } from './index';
import type { AxiosResponse } from 'axios';

export const getTemplates = (): Promise<AxiosResponse> => api.get('/listing/templates');

export const previewListing = (data: Record<string, any>): Promise<AxiosResponse> =>
  api.post('/listing/preview', data);

export const publishListing = (data: Record<string, any>): Promise<AxiosResponse> =>
  api.post('/listing/publish', data);

export interface BrandAsset {
  id: string;
  name: string;
  category: string;
  filename: string;
  uploaded_at: string;
}

export const getBrandAssets = (category?: string): Promise<AxiosResponse<{ ok: boolean; assets: BrandAsset[] }>> =>
  api.get('/brand-assets', { params: category ? { category } : {} });

export const getBrandAssetsGrouped = (category?: string): Promise<AxiosResponse<{ ok: boolean; brands: Record<string, BrandAsset[]> }>> =>
  api.get('/brand-assets/grouped', { params: category ? { category } : {} });

export const uploadBrandAsset = (file: File, name: string, category: string): Promise<AxiosResponse<{ ok: boolean; asset: BrandAsset }>> => {
  const form = new FormData();
  form.append('file', file);
  form.append('name', name);
  form.append('category', category);
  return api.post('/brand-assets/upload', form, { headers: { 'Content-Type': 'multipart/form-data' } });
};

export const deleteBrandAsset = (id: string): Promise<AxiosResponse<{ ok: boolean }>> =>
  api.delete(`/brand-assets/${id}`);

// --- Publish Queue ---
export interface QueueItem {
  id: string;
  status: string;
  scheduled_date: string;
  category: string;
  title: string;
  description: string;
  price: number | null;
  frame_id: string;
  brand_asset_ids: string[];
  generated_images: string[];
  created_at: string;
  updated_at: string;
  error: string | null;
  action: string;
  replace_product_id: string | null;
  published_product_id: string | null;
  scheduled_time?: string;
  composition?: Record<string, string>;
}

export const getPublishQueue = (date?: string): Promise<AxiosResponse<{ ok: boolean; items: QueueItem[] }>> =>
  api.get('/publish-queue', { params: date ? { date } : {} });

export const generateDailyQueue = (categories?: string[]): Promise<AxiosResponse<{ ok: boolean; items: QueueItem[] }>> =>
  api.post('/publish-queue/generate', categories ? { categories } : {}, { timeout: 60000 });

export const updateQueueItem = (id: string, updates: Record<string, any>): Promise<AxiosResponse<{ ok: boolean; item: QueueItem }>> =>
  api.put(`/publish-queue/${id}`, updates);

export const deleteQueueItem = (id: string): Promise<AxiosResponse<{ ok: boolean }>> =>
  api.delete(`/publish-queue/${id}`);

export const regenerateQueueImages = (id: string): Promise<AxiosResponse<{ ok: boolean; item: QueueItem }>> =>
  api.post(`/publish-queue/${id}/regenerate`, {}, { timeout: 60000 });

export const publishQueueItem = (id: string): Promise<AxiosResponse> =>
  api.post(`/publish-queue/${id}/publish`, {}, { timeout: 60000 });

export const publishQueueBatch = async (
  itemIds: string[],
  intervalSeconds: number = 30,
  onProgress?: (done: number, total: number, itemId: string) => void,
): Promise<{ successes: string[]; failures: { id: string; error: string }[] }> => {
  const successes: string[] = [];
  const failures: { id: string; error: string }[] = [];
  for (let i = 0; i < itemIds.length; i++) {
    const id = itemIds[i];
    try {
      await publishQueueItem(id);
      successes.push(id);
    } catch (err: any) {
      failures.push({ id, error: err?.response?.data?.error || err?.message || String(err) });
    }
    onProgress?.(i + 1, itemIds.length, id);
    if (i < itemIds.length - 1) {
      await new Promise((r) => setTimeout(r, intervalSeconds * 1000));
    }
  }
  return { successes, failures };
};

// --- Frame Listing ---
export interface FrameMeta {
  id: string;
  name: string;
  desc: string;
  tags: string[];
}

export const getFrames = (): Promise<AxiosResponse<{ ok: boolean; frames: FrameMeta[] }>> =>
  api.get('/listing/frames');

export const previewFrame = (frameId: string, category: string, brandAssetIds?: string[]): Promise<AxiosResponse> => {
  const params: Record<string, string> = { frame_id: frameId, category };
  if (brandAssetIds && brandAssetIds.length > 0) {
    params.brand_asset_ids = brandAssetIds.join(',');
  }
  return api.get('/listing/preview-frame', { params });
};

