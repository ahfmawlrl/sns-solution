import api from './client';
import type { APIResponse, Client, ClientCreate, FaqGuideline, PlatformAccount } from '@/types';

export const clientsApi = {
  list: (params?: Record<string, string>) =>
    api.get<APIResponse<Client[]>>('/clients', { params }),

  create: (data: ClientCreate) =>
    api.post<APIResponse<Client>>('/clients', data),

  get: (id: string) =>
    api.get<APIResponse<Client>>(`/clients/${id}`),

  update: (id: string, data: Partial<ClientCreate>) =>
    api.put<APIResponse<Client>>(`/clients/${id}`, data),

  changeStatus: (id: string, status: string) =>
    api.patch<APIResponse<Client>>(`/clients/${id}/status`, { status }),

  updateBrandGuidelines: (id: string, data: Record<string, unknown>) =>
    api.put<APIResponse<Client>>(`/clients/${id}/brand-guidelines`, data),

  listAccounts: (id: string) =>
    api.get<APIResponse<PlatformAccount[]>>(`/clients/${id}/accounts`),

  addAccount: (id: string, data: { platform: string; account_name: string; access_token: string }) =>
    api.post<APIResponse<PlatformAccount>>(`/clients/${id}/accounts`, data),

  removeAccount: (clientId: string, accountId: string) =>
    api.delete<APIResponse>(`/clients/${clientId}/accounts/${accountId}`),

  listFaqs: (id: string) =>
    api.get<APIResponse<FaqGuideline[]>>(`/clients/${id}/faq-guidelines`),

  createFaq: (id: string, data: { category: string; title: string; content: string; tags?: string[]; priority?: number }) =>
    api.post<APIResponse<FaqGuideline>>(`/clients/${id}/faq-guidelines`, data),

  deleteFaq: (clientId: string, faqId: string) =>
    api.delete<APIResponse>(`/clients/${clientId}/faq-guidelines/${faqId}`),
};
