import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook } from '@testing-library/react';

// Mock the auth store
const mockSetUser = vi.fn();
const mockLogout = vi.fn();
const mockStore = {
  user: null as { id: string; email: string; name: string; role: string } | null,
  isAuthenticated: false,
  setUser: mockSetUser,
  logout: mockLogout,
  hasRole: vi.fn(() => false),
};

vi.mock('@/stores/authStore', () => ({
  useAuthStore: vi.fn((selector?: (state: typeof mockStore) => unknown) => {
    if (typeof selector === 'function') return selector(mockStore);
    return mockStore;
  }),
}));

// Mock the auth API
vi.mock('@/api/auth', () => ({
  authApi: {
    me: vi.fn().mockResolvedValue({
      data: {
        data: {
          id: '123',
          email: 'test@example.com',
          name: 'Test User',
          role: 'admin',
        },
      },
    }),
  },
}));

// Mock react-query to avoid needing a full provider
vi.mock('@tanstack/react-query', () => ({
  useQuery: vi.fn(() => ({
    data: null,
    isLoading: false,
  })),
}));

// Import useAuth after all mocks are set up
import { useAuth } from './useAuth';

describe('useAuth', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockStore.user = null;
    mockStore.isAuthenticated = false;
  });

  it('returns user, isAuthenticated, isLoading, and logout', () => {
    const { result } = renderHook(() => useAuth());

    expect(result.current).toHaveProperty('user');
    expect(result.current).toHaveProperty('isAuthenticated');
    expect(result.current).toHaveProperty('isLoading');
    expect(result.current).toHaveProperty('logout');
  });

  it('returns null user when not authenticated', () => {
    mockStore.user = null;
    mockStore.isAuthenticated = false;

    const { result } = renderHook(() => useAuth());

    expect(result.current.user).toBeNull();
    expect(result.current.isAuthenticated).toBe(false);
  });

  it('returns user data when authenticated', () => {
    mockStore.user = {
      id: '123',
      email: 'test@example.com',
      name: 'Test User',
      role: 'admin',
    };
    mockStore.isAuthenticated = true;

    const { result } = renderHook(() => useAuth());

    expect(result.current.user).toEqual({
      id: '123',
      email: 'test@example.com',
      name: 'Test User',
      role: 'admin',
    });
    expect(result.current.isAuthenticated).toBe(true);
  });

  it('provides logout function from the store', () => {
    const { result } = renderHook(() => useAuth());

    expect(result.current.logout).toBe(mockLogout);
  });

  it('returns isLoading false when query is not loading', () => {
    const { result } = renderHook(() => useAuth());

    expect(result.current.isLoading).toBe(false);
  });
});
