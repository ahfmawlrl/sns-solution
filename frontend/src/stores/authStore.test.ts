import { describe, it, expect, beforeEach } from 'vitest';
import { useAuthStore } from './authStore';
import type { UserInfo } from '@/types';

const mockUser: UserInfo = {
  id: '123',
  email: 'test@example.com',
  name: 'Test User',
  role: 'admin',
};

describe('authStore', () => {
  beforeEach(() => {
    // Reset store state
    useAuthStore.setState({ user: null, isAuthenticated: false });
    localStorage.clear();
  });

  it('should start unauthenticated', () => {
    const state = useAuthStore.getState();
    expect(state.user).toBeNull();
    expect(state.isAuthenticated).toBe(false);
  });

  it('should set user and authenticate', () => {
    useAuthStore.getState().setUser(mockUser);
    const state = useAuthStore.getState();
    expect(state.user).toEqual(mockUser);
    expect(state.isAuthenticated).toBe(true);
  });

  it('should logout and clear state', () => {
    localStorage.setItem('access_token', 'test');
    localStorage.setItem('refresh_token', 'test');
    useAuthStore.getState().setUser(mockUser);

    useAuthStore.getState().logout();
    const state = useAuthStore.getState();
    expect(state.user).toBeNull();
    expect(state.isAuthenticated).toBe(false);
    expect(localStorage.getItem('access_token')).toBeNull();
    expect(localStorage.getItem('refresh_token')).toBeNull();
  });

  it('should check roles correctly', () => {
    useAuthStore.getState().setUser(mockUser);
    expect(useAuthStore.getState().hasRole('admin')).toBe(true);
    expect(useAuthStore.getState().hasRole('operator')).toBe(false);
    expect(useAuthStore.getState().hasRole('admin', 'manager')).toBe(true);
  });

  it('should return false for hasRole when not authenticated', () => {
    expect(useAuthStore.getState().hasRole('admin')).toBe(false);
  });
});
