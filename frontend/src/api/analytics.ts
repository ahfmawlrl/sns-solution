import api from './client';
import type { APIResponse, DashboardKPI, TrendPoint } from '@/types';

export const analyticsApi = {
  getDashboard: (params?: Record<string, string>) =>
    api.get<APIResponse<DashboardKPI>>('/analytics/dashboard', { params }),

  getTrends: (params?: Record<string, string>) =>
    api.get<APIResponse<TrendPoint[]>>('/analytics/trends', { params }),

  getContentPerf: (params?: Record<string, string>) =>
    api.get<APIResponse<{ content_type: string; count: number; avg_engagement_rate: number; total_reach: number }[]>>(
      '/analytics/content-perf', { params },
    ),

  createReport: (client_id: string, period?: string) =>
    api.post<APIResponse<{ id: string; status: string }>>('/analytics/report', { client_id, period }),

  getReport: (id: string) =>
    api.get<APIResponse<{ id: string; status: string; summary?: string }>>(`/analytics/report/${id}`),
};
