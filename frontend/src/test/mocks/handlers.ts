import { http, HttpResponse } from 'msw';

export const handlers = [
  // Auth
  http.post('/api/v1/auth/login', () =>
    HttpResponse.json({
      status: 'success',
      data: {
        access_token: 'mock-access-token',
        refresh_token: 'mock-refresh-token',
        expires_in: 1800,
      },
    }),
  ),

  http.get('/api/v1/auth/me', () =>
    HttpResponse.json({
      status: 'success',
      data: {
        id: '123',
        email: 'test@example.com',
        name: 'Test User',
        role: 'admin',
      },
    }),
  ),

  // Users
  http.get('/api/v1/users/me', () =>
    HttpResponse.json({
      status: 'success',
      data: {
        id: '123',
        email: 'test@example.com',
        name: 'Test User',
        role: 'admin',
      },
    }),
  ),

  // Contents
  http.get('/api/v1/contents', () =>
    HttpResponse.json({
      status: 'success',
      data: [
        {
          id: 'c-1',
          title: 'Test Content',
          status: 'draft',
          content_type: 'feed',
          platforms: ['instagram'],
          created_at: '2025-01-01T00:00:00Z',
        },
      ],
      pagination: { total: 1, page: 1, size: 20 },
    }),
  ),

  // Clients
  http.get('/api/v1/clients', () =>
    HttpResponse.json({
      status: 'success',
      data: [
        { id: 'cl-1', name: 'Brand A', industry: 'tech' },
        { id: 'cl-2', name: 'Brand B', industry: 'fashion' },
      ],
    }),
  ),

  // Analytics
  http.get('/api/v1/analytics/dashboard', () =>
    HttpResponse.json({
      status: 'success',
      data: {
        followers: 10000,
        engagement_rate: 3.5,
        total_posts: 150,
        total_comments: 500,
      },
    }),
  ),

  // Notifications
  http.get('/api/v1/notifications', () =>
    HttpResponse.json({
      status: 'success',
      data: [],
      pagination: { total: 0, page: 1, size: 20 },
    }),
  ),

  http.get('/api/v1/notifications/unread-count', () =>
    HttpResponse.json({ status: 'success', data: { count: 3 } }),
  ),
];
