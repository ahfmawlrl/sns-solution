import api from './client';
import type { APIResponse, LoginRequest, TokenResponse, UserInfo } from '@/types';

export const authApi = {
  login: (data: LoginRequest) =>
    api.post<APIResponse<TokenResponse>>('/auth/login', data),

  refresh: (refresh_token: string) =>
    api.post<APIResponse<TokenResponse>>('/auth/refresh', { refresh_token }),

  logout: () =>
    api.post<APIResponse>('/auth/logout'),

  me: () =>
    api.get<APIResponse<UserInfo>>('/auth/me'),
};
