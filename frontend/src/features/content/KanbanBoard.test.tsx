import { describe, it, expect, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { KanbanBoard } from './KanbanBoard';

// Mock the contents API
vi.mock('@/api/contents', () => ({
  contentsApi: {
    list: vi.fn().mockResolvedValue({
      data: {
        data: [
          {
            id: 'c-1',
            title: 'Draft Post',
            status: 'draft',
            content_type: 'feed',
            target_platforms: ['instagram'],
            created_at: '2025-01-15T10:00:00Z',
          },
          {
            id: 'c-2',
            title: 'Under Review',
            status: 'review',
            content_type: 'feed',
            target_platforms: ['facebook'],
            created_at: '2025-01-16T10:00:00Z',
          },
          {
            id: 'c-3',
            title: 'Client Checking',
            status: 'client_review',
            content_type: 'reel',
            target_platforms: ['instagram', 'youtube'],
            created_at: '2025-01-17T10:00:00Z',
          },
          {
            id: 'c-4',
            title: 'Ready to Publish',
            status: 'approved',
            content_type: 'feed',
            target_platforms: ['facebook'],
            created_at: '2025-01-18T10:00:00Z',
          },
        ],
      },
    }),
    changeStatus: vi.fn().mockResolvedValue({ data: { data: {} } }),
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

describe('KanbanBoard', () => {
  it('renders all four columns after loading', async () => {
    render(<KanbanBoard />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText('Draft')).toBeInTheDocument();
    });
    expect(screen.getByText('Review')).toBeInTheDocument();
    expect(screen.getByText('Client Review')).toBeInTheDocument();
    expect(screen.getByText('Approved')).toBeInTheDocument();
  });

  it('renders page header with title', async () => {
    render(<KanbanBoard />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText('Content Board')).toBeInTheDocument();
    });
    expect(screen.getByText('Drag and drop to move content through the workflow')).toBeInTheDocument();
  });

  it('displays content cards in their respective columns', async () => {
    render(<KanbanBoard />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText('Draft Post')).toBeInTheDocument();
    });
    expect(screen.getByText('Under Review')).toBeInTheDocument();
    expect(screen.getByText('Client Checking')).toBeInTheDocument();
    expect(screen.getByText('Ready to Publish')).toBeInTheDocument();
  });

  it('shows content count badges per column', async () => {
    render(<KanbanBoard />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText('Draft Post')).toBeInTheDocument();
    });

    // Each column should show count of 1 in our mock data
    const badges = screen.getAllByText('1');
    expect(badges.length).toBeGreaterThanOrEqual(4);
  });

  it('renders platform labels on cards', async () => {
    render(<KanbanBoard />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText('Draft Post')).toBeInTheDocument();
    });

    // Platform names should appear on cards
    const instagramLabels = screen.getAllByText('instagram');
    expect(instagramLabels.length).toBeGreaterThanOrEqual(1);
  });

  it('shows loading state initially', () => {
    render(<KanbanBoard />, { wrapper: createWrapper() });
    expect(screen.getByText('Loading board...')).toBeInTheDocument();
  });

  it('renders drag handles on cards', async () => {
    render(<KanbanBoard />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText('Draft Post')).toBeInTheDocument();
    });

    const dragHandles = screen.getAllByLabelText('Drag handle');
    expect(dragHandles.length).toBeGreaterThanOrEqual(4);
  });
});
