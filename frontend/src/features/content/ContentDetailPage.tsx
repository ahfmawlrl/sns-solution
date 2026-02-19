import { useParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { contentsApi } from '@/api/contents';
import { PageHeader } from '@/components/common/PageHeader';
import { LoadingSpinner } from '@/components/feedback/LoadingSpinner';
import { ApprovalTimeline } from './ApprovalTimeline';
import type { ContentStatus } from '@/types';

const STATUS_COLORS: Record<ContentStatus, string> = {
  draft: 'bg-gray-100 text-gray-700',
  review: 'bg-yellow-100 text-yellow-700',
  client_review: 'bg-orange-100 text-orange-700',
  approved: 'bg-green-100 text-green-700',
  published: 'bg-blue-100 text-blue-700',
  rejected: 'bg-red-100 text-red-700',
};

export function ContentDetailPage() {
  const { id } = useParams<{ id: string }>();

  const { data: content, isLoading } = useQuery({
    queryKey: ['content', id],
    queryFn: async () => {
      const res = await contentsApi.get(id!);
      return res.data.data;
    },
    enabled: !!id,
  });

  if (isLoading) return <LoadingSpinner />;
  if (!content) return <p className="text-center text-muted-foreground">Content not found</p>;

  return (
    <div>
      <PageHeader title={content.title} />

      <div className="grid gap-6 lg:grid-cols-3">
        {/* Main content */}
        <div className="lg:col-span-2 space-y-4">
          <div className="rounded-lg border bg-card p-6">
            <div className="flex items-center gap-2 mb-4">
              <span className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${STATUS_COLORS[content.status]}`}>
                {content.status}
              </span>
              <span className="text-xs text-muted-foreground">{content.content_type}</span>
              <span className="text-xs text-muted-foreground">{content.target_platforms.join(', ')}</span>
            </div>
            {content.body && <p className="whitespace-pre-wrap text-sm">{content.body}</p>}
            {content.hashtags && content.hashtags.length > 0 && (
              <div className="mt-4 flex flex-wrap gap-1">
                {content.hashtags.map((tag) => (
                  <span key={tag} className="rounded bg-muted px-2 py-0.5 text-xs text-muted-foreground">
                    {tag}
                  </span>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Sidebar: approval timeline */}
        <div className="space-y-4">
          <ApprovalTimeline contentId={id!} />
        </div>
      </div>
    </div>
  );
}
