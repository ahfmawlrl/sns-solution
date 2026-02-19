import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { publishingApi } from '@/api/publishing';
import { PageHeader } from '@/components/common/PageHeader';
import { LoadingSpinner } from '@/components/feedback/LoadingSpinner';
import type { PublishingStatus } from '@/types';

const STATUS_COLORS: Record<PublishingStatus, string> = {
  pending: 'bg-yellow-100 text-yellow-700',
  publishing: 'bg-blue-100 text-blue-700',
  success: 'bg-green-100 text-green-700',
  failed: 'bg-red-100 text-red-700',
  cancelled: 'bg-gray-100 text-gray-700',
};

export function PublishingPage() {
  const [tab, setTab] = useState<'queue' | 'history'>('queue');

  const { data: queue, isLoading: queueLoading } = useQuery({
    queryKey: ['publishing', 'queue'],
    queryFn: async () => { const res = await publishingApi.getQueue(); return res.data; },
    enabled: tab === 'queue',
  });

  const { data: history, isLoading: historyLoading } = useQuery({
    queryKey: ['publishing', 'history'],
    queryFn: async () => { const res = await publishingApi.getHistory(); return res.data; },
    enabled: tab === 'history',
  });

  const items = tab === 'queue' ? queue?.data : history?.data;
  const loading = tab === 'queue' ? queueLoading : historyLoading;

  return (
    <div>
      <PageHeader title="Publishing" description="Schedule and manage your posts" />

      <div className="mb-4 flex gap-2">
        {(['queue', 'history'] as const).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`rounded-md px-4 py-1.5 text-sm font-medium ${
              tab === t ? 'bg-primary text-primary-foreground' : 'bg-muted text-muted-foreground hover:bg-accent'
            }`}
          >
            {t === 'queue' ? 'Queue' : 'History'}
          </button>
        ))}
      </div>

      {loading ? (
        <LoadingSpinner />
      ) : (
        <div className="space-y-2">
          {items?.map((log) => (
            <div key={log.id} className="flex items-center justify-between rounded-lg border bg-card p-4">
              <div>
                <p className="text-sm font-medium">Content: {log.content_id.slice(0, 8)}...</p>
                <p className="text-xs text-muted-foreground">
                  {log.scheduled_at ? `Scheduled: ${new Date(log.scheduled_at).toLocaleString()}` : 'Immediate'}
                </p>
              </div>
              <span className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${STATUS_COLORS[log.status]}`}>
                {log.status}
              </span>
            </div>
          ))}
          {items?.length === 0 && (
            <p className="py-12 text-center text-sm text-muted-foreground">No publishing logs</p>
          )}
        </div>
      )}
    </div>
  );
}
