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

export const uploadBrandAsset = (file: File, name: string, category: string): Promise<AxiosResponse<{ ok: boolean; asset: BrandAsset }>> => {
  const form = new FormData();
  form.append('file', file);
  form.append('name', name);
  form.append('category', category);
  return api.post('/brand-assets/upload', form, { headers: { 'Content-Type': 'multipart/form-data' } });
};

export const deleteBrandAsset = (id: string): Promise<AxiosResponse<{ ok: boolean }>> =>
  api.delete(`/brand-assets/${id}`);
