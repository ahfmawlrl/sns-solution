import api from './client';
import type { APIResponse, NotificationPreferences, WorkflowSettings } from '@/types';

export const settingsApi = {
  getPlatformConnections: () =>
    api.get<APIResponse<{ platform: string; account_name: string; is_connected: boolean }[]>>(
      '/settings/platform-connections',
    ),

  testConnection: (platform_account_id: string) =>
    api.post<APIResponse>('/settings/platform-connections/test', { platform_account_id }),

  getWorkflows: () =>
    api.get<APIResponse<WorkflowSettings>>('/settings/workflows'),

  updateWorkflows: (data: WorkflowSettings) =>
    api.put<APIResponse<WorkflowSettings>>('/settings/workflows', data),

  getNotificationPrefs: () =>
    api.get<APIResponse<NotificationPreferences>>('/settings/notification-preferences'),

  updateNotificationPrefs: (data: NotificationPreferences) =>
    api.put<APIResponse<NotificationPreferences>>('/settings/notification-preferences', data),

  getAuditLogs: (params?: Record<string, string>) =>
    api.get<APIResponse<Record<string, unknown>[]>>('/settings/audit-logs', { params }),
};
