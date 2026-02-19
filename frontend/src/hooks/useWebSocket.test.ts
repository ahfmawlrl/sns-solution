import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook } from '@testing-library/react';

// Track WebSocket instances for assertions
let mockWsInstances: MockWebSocket[] = [];

class MockWebSocket {
  static CONNECTING = 0;
  static OPEN = 1;
  static CLOSING = 2;
  static CLOSED = 3;

  url: string;
  readyState = MockWebSocket.OPEN;
  onopen: ((event: Event) => void) | null = null;
  onmessage: ((event: MessageEvent) => void) | null = null;
  onclose: ((event: CloseEvent) => void) | null = null;
  onerror: ((event: Event) => void) | null = null;

  send = vi.fn();
  close = vi.fn(() => {
    this.readyState = MockWebSocket.CLOSED;
  });

  constructor(url: string) {
    this.url = url;
    mockWsInstances.push(this);
    // Simulate async open
    setTimeout(() => {
      if (this.onopen) {
        this.onopen(new Event('open'));
      }
    }, 0);
  }
}

// Set up global WebSocket mock
vi.stubGlobal('WebSocket', MockWebSocket);

// Mock dependencies
const mockAddNotification = vi.fn();
const mockInvalidateQueries = vi.fn();

vi.mock('@/stores/authStore', () => ({
  useAuthStore: vi.fn((selector?: (state: { isAuthenticated: boolean }) => unknown) => {
    if (typeof selector === 'function') {
      return selector({ isAuthenticated: true });
    }
    return { isAuthenticated: true };
  }),
}));

vi.mock('@/stores/notificationStore', () => ({
  useNotificationStore: vi.fn((selector?: (state: { addNotification: typeof mockAddNotification }) => unknown) => {
    if (typeof selector === 'function') {
      return selector({ addNotification: mockAddNotification });
    }
    return { addNotification: mockAddNotification };
  }),
}));

vi.mock('@tanstack/react-query', () => ({
  useQueryClient: vi.fn(() => ({
    invalidateQueries: mockInvalidateQueries,
  })),
}));

// Import after mocks
import { useWebSocket } from './useWebSocket';

describe('useWebSocket', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.useFakeTimers({ shouldAdvanceTime: true });
    mockWsInstances = [];
    localStorage.setItem('access_token', 'test-token-123');
  });

  afterEach(() => {
    vi.useRealTimers();
    localStorage.clear();
  });

  it('creates a WebSocket connection when authenticated', () => {
    renderHook(() => useWebSocket());

    expect(mockWsInstances.length).toBe(1);
    expect(mockWsInstances[0]!.url).toContain('token=test-token-123');
  });

  it('uses ws protocol for http connections', () => {
    renderHook(() => useWebSocket());

    expect(mockWsInstances.length).toBe(1);
    expect(mockWsInstances[0]!.url).toMatch(/^ws:/);
  });

  it('does not connect when no access token is in localStorage', () => {
    localStorage.removeItem('access_token');

    renderHook(() => useWebSocket());

    expect(mockWsInstances.length).toBe(0);
  });

  it('starts heartbeat on connection open', async () => {
    renderHook(() => useWebSocket());

    // Trigger onopen
    await vi.advanceTimersByTimeAsync(10);

    expect(mockWsInstances.length).toBe(1);
    const ws = mockWsInstances[0]!;

    // Advance by heartbeat interval (30 seconds)
    vi.advanceTimersByTime(30_000);

    expect(ws.send).toHaveBeenCalledWith(JSON.stringify({ type: 'ping' }));
  });

  it('handles pong messages without error', async () => {
    renderHook(() => useWebSocket());

    await vi.advanceTimersByTimeAsync(10);

    const ws = mockWsInstances[0]!;

    // Simulate pong response
    if (ws.onmessage) {
      ws.onmessage(new MessageEvent('message', {
        data: JSON.stringify({ type: 'pong' }),
      }));
    }

    // Should not throw or call addNotification
    expect(mockAddNotification).not.toHaveBeenCalled();
  });

  it('processes notification events', async () => {
    renderHook(() => useWebSocket());

    await vi.advanceTimersByTimeAsync(10);

    const ws = mockWsInstances[0]!;

    if (ws.onmessage) {
      ws.onmessage(new MessageEvent('message', {
        data: JSON.stringify({ type: 'notification', title: 'Test' }),
      }));
    }

    expect(mockAddNotification).toHaveBeenCalledTimes(1);
  });

  it('processes crisis_alert events', async () => {
    renderHook(() => useWebSocket());

    await vi.advanceTimersByTimeAsync(10);

    const ws = mockWsInstances[0]!;

    if (ws.onmessage) {
      ws.onmessage(new MessageEvent('message', {
        data: JSON.stringify({ type: 'crisis_alert', level: 'high' }),
      }));
    }

    expect(mockAddNotification).toHaveBeenCalledTimes(1);
  });

  it('invalidates publishing queries on publish_result event', async () => {
    renderHook(() => useWebSocket());

    await vi.advanceTimersByTimeAsync(10);

    const ws = mockWsInstances[0]!;

    if (ws.onmessage) {
      ws.onmessage(new MessageEvent('message', {
        data: JSON.stringify({ type: 'publish_result', success: true }),
      }));
    }

    expect(mockInvalidateQueries).toHaveBeenCalledWith({ queryKey: ['publishing'] });
    expect(mockInvalidateQueries).toHaveBeenCalledWith({ queryKey: ['content'] });
  });

  it('invalidates community inbox queries on new_comment event', async () => {
    renderHook(() => useWebSocket());

    await vi.advanceTimersByTimeAsync(10);

    const ws = mockWsInstances[0]!;

    if (ws.onmessage) {
      ws.onmessage(new MessageEvent('message', {
        data: JSON.stringify({ type: 'new_comment', comment_id: 'c-1' }),
      }));
    }

    expect(mockInvalidateQueries).toHaveBeenCalledWith({ queryKey: ['community', 'inbox'] });
  });

  it('closes WebSocket on unmount', async () => {
    const { unmount } = renderHook(() => useWebSocket());

    await vi.advanceTimersByTimeAsync(10);

    const ws = mockWsInstances[0]!;
    unmount();

    expect(ws.close).toHaveBeenCalled();
  });

  it('ignores malformed JSON messages', async () => {
    renderHook(() => useWebSocket());

    await vi.advanceTimersByTimeAsync(10);

    const ws = mockWsInstances[0]!;

    // Send invalid JSON - should not throw
    if (ws.onmessage) {
      expect(() => {
        ws.onmessage!(new MessageEvent('message', {
          data: 'not valid json {{{',
        }));
      }).not.toThrow();
    }

    expect(mockAddNotification).not.toHaveBeenCalled();
  });
});
