import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { Plus } from 'lucide-react';
import { contentsApi } from '@/api/contents';
import { PageHeader } from '@/components/common/PageHeader';
import { LoadingSpinner } from '@/components/feedback/LoadingSpinner';
import type { ContentStatus } from '@/types';

const STATUS_COLORS: Record<ContentStatus, string> = {
  draft: 'bg-gray-100 text-gray-700',
  review: 'bg-yellow-100 text-yellow-700',
  client_review: 'bg-orange-100 text-orange-700',
  approved: 'bg-green-100 text-green-700',
  published: 'bg-blue-100 text-blue-700',
  rejected: 'bg-red-100 text-red-700',
};

export function ContentListPage() {
  const [statusFilter, setStatusFilter] = useState<string>('');
  const navigate = useNavigate();

  const { data, isLoading } = useQuery({
    queryKey: ['contents', statusFilter],
    queryFn: async () => {
      const params: Record<string, string> = {};
      if (statusFilter) params.status = statusFilter;
      const res = await contentsApi.list(params);
      return res.data;
    },
  });

  return (
    <div>
      <PageHeader
        title="Content Management"
        description="Manage your content across all platforms"
        actions={
          <button
            onClick={() => navigate('/content/create')}
            className="flex items-center gap-2 rounded-md bg-primary px-4 py-2 text-sm text-primary-foreground hover:bg-primary/90"
          >
            <Plus className="h-4 w-4" /> New Content
          </button>
        }
      />

      {/* Filter */}
      <div className="mb-4 flex gap-2">
        {['', 'draft', 'review', 'client_review', 'approved', 'published', 'rejected'].map((s) => (
          <button
            key={s}
            onClick={() => setStatusFilter(s)}
            className={`rounded-md px-3 py-1.5 text-xs font-medium transition-colors ${
              statusFilter === s ? 'bg-primary text-primary-foreground' : 'bg-muted text-muted-foreground hover:bg-accent'
            }`}
          >
            {s || 'All'}
          </button>
        ))}
      </div>

      {isLoading ? (
        <LoadingSpinner />
      ) : (
        <div className="space-y-2">
          {data?.data?.map((content) => (
            <Link
              key={content.id}
              to={`/content/${content.id}`}
              className="flex items-center justify-between rounded-lg border bg-card p-4 transition-colors hover:bg-accent/50"
            >
              <div>
                <p className="font-medium">{content.title}</p>
                <p className="mt-1 text-xs text-muted-foreground">
                  {content.content_type} &middot; {content.target_platforms.join(', ')}
                </p>
              </div>
              <span className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${STATUS_COLORS[content.status]}`}>
                {content.status}
              </span>
            </Link>
          ))}
          {data?.data?.length === 0 && (
            <p className="py-12 text-center text-sm text-muted-foreground">No content found</p>
          )}
        </div>
      )}
    </div>
  );
}
