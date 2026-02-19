import api from './client';
import type { APIResponse, PublishingLog } from '@/types';

export const publishingApi = {
  schedule: (content_id: string, platform_account_ids: string[], scheduled_at: string) =>
    api.post<APIResponse<PublishingLog[]>>('/publishing/schedule', { content_id, platform_account_ids, scheduled_at }),

  publishNow: (content_id: string, platform_account_ids: string[]) =>
    api.post<APIResponse<PublishingLog[]>>('/publishing/now', { content_id, platform_account_ids }),

  getQueue: (params?: Record<string, string>) =>
    api.get<APIResponse<PublishingLog[]>>('/publishing/queue', { params }),

  cancel: (id: string) =>
    api.delete<APIResponse<PublishingLog>>(`/publishing/${id}/cancel`),

  getHistory: (params?: Record<string, string>) =>
    api.get<APIResponse<PublishingLog[]>>('/publishing/history', { params }),

  retry: (id: string) =>
    api.post<APIResponse<PublishingLog>>(`/publishing/${id}/retry`),
};
