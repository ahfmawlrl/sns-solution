import { describe, it, expect, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { UnifiedInbox } from './UnifiedInbox';

// Mock the community API
vi.mock('@/api/community', () => ({
  communityApi: {
    listInbox: vi.fn().mockResolvedValue({
      data: {
        data: [
          {
            id: 'cm-1',
            author_name: 'User One',
            message: 'Great content!',
            sentiment: 'positive',
            status: 'pending',
            commented_at: '2025-01-15T10:00:00Z',
            platform_account_id: 'pa-1',
            ai_reply_draft: 'Thank you for your kind words!',
          },
          {
            id: 'cm-2',
            author_name: 'User Two',
            message: 'This is terrible service',
            sentiment: 'negative',
            status: 'pending',
            commented_at: '2025-01-15T11:00:00Z',
            platform_account_id: 'pa-2',
            ai_reply_draft: null,
          },
          {
            id: 'cm-3',
            author_name: 'Angry Person',
            message: 'URGENT COMPLAINT!!!',
            sentiment: 'crisis',
            status: 'pending',
            commented_at: '2025-01-15T12:00:00Z',
            platform_account_id: 'pa-1',
            ai_reply_draft: null,
          },
        ],
      },
    }),
    reply: vi.fn().mockResolvedValue({ data: { data: {} } }),
  },
}));

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return function Wrapper({ children }: { children: React.ReactNode }) {
    return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
  };
}

describe('UnifiedInbox', () => {
  it('renders inbox title', async () => {
    render(<UnifiedInbox />, { wrapper: createWrapper() });
    expect(screen.getByText('Unified Inbox')).toBeInTheDocument();
  });

  it('renders inbox description', () => {
    render(<UnifiedInbox />, { wrapper: createWrapper() });
    expect(screen.getByText('Monitor and respond to comments across all platforms')).toBeInTheDocument();
  });

  it('renders quick filter options', async () => {
    render(<UnifiedInbox />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText('All Comments')).toBeInTheDocument();
    });
    expect(screen.getByText('Crisis Alerts')).toBeInTheDocument();
    expect(screen.getByText('Negative')).toBeInTheDocument();
    expect(screen.getByText('Pending Reply')).toBeInTheDocument();
  });

  it('renders platform filter links in sidebar', async () => {
    render(<UnifiedInbox />, { wrapper: createWrapper() });

    // Platform names in the sidebar filter section (capitalized)
    await waitFor(() => {
      expect(screen.getByText('Quick Filters')).toBeInTheDocument();
    });
    expect(screen.getByText('Platforms')).toBeInTheDocument();
  });

  it('displays comment items after loading', async () => {
    render(<UnifiedInbox />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText('User One')).toBeInTheDocument();
    });
    expect(screen.getByText('Great content!')).toBeInTheDocument();
    expect(screen.getByText('User Two')).toBeInTheDocument();
    expect(screen.getByText('This is terrible service')).toBeInTheDocument();
  });

  it('shows comment count', async () => {
    render(<UnifiedInbox />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText('3 comments')).toBeInTheDocument();
    });
  });

  it('shows crisis alert badge when crisis comments exist', async () => {
    render(<UnifiedInbox />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText('1 Crisis')).toBeInTheDocument();
    });
  });

  it('shows reply panel placeholder when no comment is selected', () => {
    render(<UnifiedInbox />, { wrapper: createWrapper() });
    expect(screen.getByText('Select a comment to view details and reply')).toBeInTheDocument();
  });

  it('shows filter bar when Filters button is clicked', async () => {
    const user = userEvent.setup();
    render(<UnifiedInbox />, { wrapper: createWrapper() });

    const filtersBtn = screen.getByText('Filters');
    await user.click(filtersBtn);

    // Platform filter options should now be visible in the filter bar
    expect(screen.getByText('Platform:')).toBeInTheDocument();
    expect(screen.getByText('Sentiment:')).toBeInTheDocument();
  });

  it('shows filter bar platform options including All', async () => {
    const user = userEvent.setup();
    render(<UnifiedInbox />, { wrapper: createWrapper() });

    const filtersBtn = screen.getByText('Filters');
    await user.click(filtersBtn);

    // Filter bar shows All, Instagram, Facebook, YouTube
    expect(screen.getAllByText('All').length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText('Instagram')).toBeInTheDocument();
    expect(screen.getByText('Facebook')).toBeInTheDocument();
    expect(screen.getByText('Youtube')).toBeInTheDocument();
  });

  it('shows reply panel when a comment is selected', async () => {
    const user = userEvent.setup();
    render(<UnifiedInbox />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText('User One')).toBeInTheDocument();
    });

    // Click on the first comment
    const commentButton = screen.getByText('Great content!').closest('button');
    if (commentButton) {
      await user.click(commentButton);
    }

    // Reply panel should now show author name and message detail
    await waitFor(() => {
      expect(screen.getByText('Reply')).toBeInTheDocument();
    });
    expect(screen.getByPlaceholderText('Type your reply...')).toBeInTheDocument();
    expect(screen.getByText('Send Reply')).toBeInTheDocument();
  });

  it('renders refresh button', () => {
    render(<UnifiedInbox />, { wrapper: createWrapper() });
    expect(screen.getByLabelText('Refresh')).toBeInTheDocument();
  });
});
