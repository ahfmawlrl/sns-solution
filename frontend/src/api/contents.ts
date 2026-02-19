import api from './client';
import type { APIResponse, Content, ContentApproval, ContentCreate, ContentStatus, PublishingLog } from '@/types';

export const contentsApi = {
  list: (params?: Record<string, string>) =>
    api.get<APIResponse<Content[]>>('/contents', { params }),

  create: (data: ContentCreate) =>
    api.post<APIResponse<Content>>('/contents', data),

  get: (id: string) =>
    api.get<APIResponse<Content>>(`/contents/${id}`),

  update: (id: string, data: Partial<ContentCreate>) =>
    api.put<APIResponse<Content>>(`/contents/${id}`, data),

  delete: (id: string) =>
    api.delete<APIResponse>(`/contents/${id}`),

  changeStatus: (id: string, to_status: ContentStatus, comment?: string, is_urgent?: boolean) =>
    api.patch<APIResponse<Content>>(`/contents/${id}/status`, { to_status, comment, is_urgent }),

  calendar: (start: string, end: string, client_id?: string) =>
    api.get<APIResponse<Content[]>>('/contents/calendar', { params: { start, end, client_id } }),

  getApprovals: (id: string) =>
    api.get<APIResponse<ContentApproval[]>>(`/contents/${id}/approvals`),

  getPublishingLogs: (id: string) =>
    api.get<APIResponse<PublishingLog[]>>(`/contents/${id}/publishing-logs`),

  getUploadUrl: (id: string, filename: string, content_type: string) =>
    api.post<APIResponse<{ upload_url: string; file_key: string }>>(`/contents/${id}/upload`, { filename, content_type }),
};
