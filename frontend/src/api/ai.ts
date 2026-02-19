import api from './client';

export const aiApi = {
  chat: (data: { message: string; context: Record<string, unknown> }) =>
    api.post('/ai/chat', data),

  generateContent: (data: { prompt: string; content_type: string; platform: string }) =>
    api.post('/ai/generate-content', data),

  analyzeContent: (contentId: string) =>
    api.post(`/ai/analyze/${contentId}`),

  suggestReply: (commentId: string) =>
    api.post(`/ai/suggest-reply/${commentId}`),

  generateReport: (data: { client_id: string; period: string }) =>
    api.post('/ai/report', data),
};
