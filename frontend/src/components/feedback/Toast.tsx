import { useEffect, useState, useCallback } from 'react';
import { cn } from '@/utils/cn';

export type ToastVariant = 'default' | 'success' | 'error' | 'warning';

interface ToastItem {
  id: string;
  message: string;
  variant: ToastVariant;
  duration?: number;
}

let toastCounter = 0;
let addToastFn: ((toast: Omit<ToastItem, 'id'>) => void) | null = null;

export function toast(message: string, variant: ToastVariant = 'default', duration = 5000) {
  addToastFn?.({ message, variant, duration });
}

const VARIANT_STYLES: Record<ToastVariant, string> = {
  default: 'bg-background border-border text-foreground',
  success: 'bg-green-50 border-green-200 text-green-800 dark:bg-green-950 dark:border-green-800 dark:text-green-200',
  error: 'bg-red-50 border-red-200 text-red-800 dark:bg-red-950 dark:border-red-800 dark:text-red-200',
  warning: 'bg-yellow-50 border-yellow-200 text-yellow-800 dark:bg-yellow-950 dark:border-yellow-800 dark:text-yellow-200',
};

const VARIANT_ICONS: Record<ToastVariant, string> = {
  default: '',
  success: 'check_circle',
  error: 'error',
  warning: 'warning',
};

export function ToastContainer() {
  const [toasts, setToasts] = useState<ToastItem[]>([]);

  const addToast = useCallback((toast: Omit<ToastItem, 'id'>) => {
    const id = `toast-${++toastCounter}`;
    setToasts((prev) => [...prev, { ...toast, id }]);
  }, []);

  const removeToast = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  useEffect(() => {
    addToastFn = addToast;
    return () => { addToastFn = null; };
  }, [addToast]);

  return (
    <div
      className="fixed bottom-4 right-4 z-50 flex flex-col gap-2"
      role="region"
      aria-label="Notifications"
      aria-live="polite"
    >
      {toasts.map((t) => (
        <ToastMessage key={t.id} toast={t} onClose={() => removeToast(t.id)} />
      ))}
    </div>
  );
}

function ToastMessage({ toast: t, onClose }: { toast: ToastItem; onClose: () => void }) {
  useEffect(() => {
    const timer = setTimeout(onClose, t.duration ?? 5000);
    return () => clearTimeout(timer);
  }, [t.duration, onClose]);

  return (
    <div
      className={cn(
        'flex items-center gap-3 rounded-lg border px-4 py-3 shadow-lg',
        'animate-in slide-in-from-right-5 fade-in duration-300',
        'min-w-[300px] max-w-[420px]',
        VARIANT_STYLES[t.variant],
      )}
      role="alert"
    >
      {VARIANT_ICONS[t.variant] && (
        <span className="text-lg" aria-hidden="true">
          {t.variant === 'success' ? '\u2713' : t.variant === 'error' ? '\u2717' : '\u26A0'}
        </span>
      )}
      <p className="flex-1 text-sm">{t.message}</p>
      <button
        onClick={onClose}
        className="ml-2 text-muted-foreground hover:text-foreground"
        aria-label="Close notification"
      >
        \u00D7
      </button>
    </div>
  );
}
