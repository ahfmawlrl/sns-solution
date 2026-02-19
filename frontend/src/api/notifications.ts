import api from './client';
import type { APIResponse, Notification } from '@/types';

export const notificationsApi = {
  list: (params?: Record<string, string>) =>
    api.get<APIResponse<Notification[]>>('/notifications', { params }),

  getUnreadCount: () =>
    api.get<APIResponse<{ count: number }>>('/notifications/unread-count'),

  markRead: (id: string) =>
    api.patch<APIResponse<Notification>>(`/notifications/${id}/read`),

  markAllRead: () =>
    api.patch<APIResponse<{ updated_count: number }>>('/notifications/read-all'),
};
