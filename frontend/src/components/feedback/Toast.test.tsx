import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, act } from '@testing-library/react';
import { ToastContainer, toast } from './Toast';

describe('Toast', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  it('renders nothing initially', () => {
    const { container } = render(<ToastContainer />);
    expect(container.querySelector('[role="alert"]')).toBeNull();
  });

  it('shows toast when triggered', () => {
    render(<ToastContainer />);
    act(() => {
      toast('Hello!', 'default');
    });
    expect(screen.getByText('Hello!')).toBeInTheDocument();
  });

  it('shows success variant', () => {
    render(<ToastContainer />);
    act(() => {
      toast('Success!', 'success');
    });
    expect(screen.getByText('Success!')).toBeInTheDocument();
  });

  it('auto-dismisses after duration', () => {
    render(<ToastContainer />);
    act(() => {
      toast('Temporary', 'default', 3000);
    });
    expect(screen.getByText('Temporary')).toBeInTheDocument();

    act(() => {
      vi.advanceTimersByTime(3500);
    });
    expect(screen.queryByText('Temporary')).toBeNull();
  });

  it('has aria region for accessibility', () => {
    render(<ToastContainer />);
    expect(screen.getByRole('region')).toHaveAttribute('aria-label', 'Notifications');
  });

  vi.useRealTimers();
});
