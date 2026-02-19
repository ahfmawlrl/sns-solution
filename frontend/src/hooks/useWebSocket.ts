import { useEffect, useRef, useCallback } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { useAuthStore } from '@/stores/authStore';
import { useNotificationStore } from '@/stores/notificationStore';

/** WebSocket event types pushed by the server. */
export type WSEventType =
  | 'notification'
  | 'crisis_alert'
  | 'publish_result'
  | 'approval_request'
  | 'new_comment'
  | 'chat_stream'
  | 'pong';

interface WSMessage {
  type: WSEventType;
  [key: string]: unknown;
}

const WS_HEARTBEAT_INTERVAL = 30_000; // 30s
const MAX_RECONNECT_DELAY = 30_000;

function backoff(attempt: number): number {
  return Math.min(1000 * 2 ** attempt, MAX_RECONNECT_DELAY);
}

export function useWebSocket() {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  const addNotification = useNotificationStore((s) => s.addNotification);
  const queryClient = useQueryClient();

  const wsRef = useRef<WebSocket | null>(null);
  const heartbeatRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const retryCountRef = useRef(0);
  const mountedRef = useRef(true);

  const connect = useCallback(() => {
    if (!mountedRef.current) return;

    const token = localStorage.getItem('access_token');
    if (!token) return;

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.host;
    const url = `${protocol}//${host}/ws?token=${token}`;

    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onopen = () => {
      retryCountRef.current = 0;

      // Start heartbeat
      heartbeatRef.current = setInterval(() => {
        if (ws.readyState === WebSocket.OPEN) {
          ws.send(JSON.stringify({ type: 'ping' }));
        }
      }, WS_HEARTBEAT_INTERVAL);
    };

    ws.onmessage = (event) => {
      try {
        const data: WSMessage = JSON.parse(event.data);

        switch (data.type) {
          case 'notification':
            addNotification(data as never);
            break;

          case 'crisis_alert':
            addNotification(data as never);
            break;

          case 'publish_result':
            queryClient.invalidateQueries({ queryKey: ['publishing'] });
            queryClient.invalidateQueries({ queryKey: ['content'] });
            break;

          case 'approval_request':
            queryClient.invalidateQueries({ queryKey: ['content'] });
            addNotification(data as never);
            break;

          case 'new_comment':
            queryClient.invalidateQueries({ queryKey: ['community', 'inbox'] });
            break;

          case 'pong':
            // heartbeat acknowledged
            break;
        }
      } catch {
        // ignore parse errors
      }
    };

    ws.onclose = (event) => {
      if (heartbeatRef.current) {
        clearInterval(heartbeatRef.current);
        heartbeatRef.current = null;
      }

      if (!mountedRef.current) return;

      if (event.code === 4001) {
        // Token invalid/expired — don't reconnect (auth will handle it)
        return;
      }

      // Auto-reconnect with exponential backoff
      const delay = backoff(retryCountRef.current);
      retryCountRef.current += 1;
      setTimeout(connect, delay);
    };

    ws.onerror = () => {
      // onclose will fire after onerror, handling reconnection
    };
  }, [addNotification, queryClient]);

  useEffect(() => {
    mountedRef.current = true;

    if (isAuthenticated) {
      connect();
    }

    return () => {
      mountedRef.current = false;
      if (heartbeatRef.current) {
        clearInterval(heartbeatRef.current);
      }
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
    };
  }, [isAuthenticated, connect]);
}
