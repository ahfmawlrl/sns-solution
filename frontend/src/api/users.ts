import api from './client';
import type { APIResponse, User, UserCreate, UserRole } from '@/types';

export const usersApi = {
  list: (params?: Record<string, string>) =>
    api.get<APIResponse<User[]>>('/users', { params }),

  create: (data: UserCreate) =>
    api.post<APIResponse<User>>('/users', data),

  get: (id: string) =>
    api.get<APIResponse<User>>(`/users/${id}`),

  update: (id: string, data: { name?: string; avatar_url?: string }) =>
    api.put<APIResponse<User>>(`/users/${id}`, data),

  changeRole: (id: string, role: UserRole) =>
    api.patch<APIResponse<User>>(`/users/${id}/role`, { role }),

  toggleActive: (id: string, is_active: boolean) =>
    api.patch<APIResponse<User>>(`/users/${id}/active`, { is_active }),

  updateProfile: (data: { name?: string; avatar_url?: string }) =>
    api.put<APIResponse<User>>('/users/me/profile', data),

  changePassword: (current_password: string, new_password: string) =>
    api.put<APIResponse>('/users/me/password', { current_password, new_password }),
};
