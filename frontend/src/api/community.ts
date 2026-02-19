import api from './client';
import type { APIResponse, Comment, FilterRule, SentimentStats } from '@/types';

export const communityApi = {
  listInbox: (params?: Record<string, string>) =>
    api.get<APIResponse<Comment[]>>('/community/inbox', { params }),

  reply: (id: string, message: string, use_ai_draft?: boolean) =>
    api.post<APIResponse<Comment>>(`/community/${id}/reply`, { message, use_ai_draft }),

  updateStatus: (id: string, status: string) =>
    api.patch<APIResponse<Comment>>(`/community/${id}/status`, { status }),

  getSentiment: (client_id?: string) =>
    api.get<APIResponse<SentimentStats>>('/community/sentiment', { params: { client_id } }),

  listFilterRules: (client_id?: string) =>
    api.get<APIResponse<FilterRule[]>>('/community/filter-rules', { params: { client_id } }),

  createFilterRule: (data: { client_id: string; rule_type: string; value: string; action: string }) =>
    api.post<APIResponse<FilterRule>>('/community/filter-rules', data),

  updateFilterRule: (id: string, data: Partial<FilterRule>) =>
    api.put<APIResponse<FilterRule>>(`/community/filter-rules/${id}`, data),

  deleteFilterRule: (id: string) =>
    api.delete<APIResponse>(`/community/filter-rules/${id}`),
};
