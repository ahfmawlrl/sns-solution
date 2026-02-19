import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { communityApi } from '@/api/community';
import { PageHeader } from '@/components/common/PageHeader';
import { LoadingSpinner } from '@/components/feedback/LoadingSpinner';
import type { Sentiment } from '@/types';

const SENTIMENT_COLORS: Record<Sentiment, string> = {
  positive: 'bg-green-100 text-green-700',
  neutral: 'bg-gray-100 text-gray-700',
  negative: 'bg-red-100 text-red-700',
  crisis: 'bg-red-200 text-red-900',
};

export function CommunityPage() {
  const [sentimentFilter, setSentimentFilter] = useState<string>('');

  const { data, isLoading } = useQuery({
    queryKey: ['community', 'inbox', sentimentFilter],
    queryFn: async () => {
      const params: Record<string, string> = {};
      if (sentimentFilter) params.sentiment = sentimentFilter;
      const res = await communityApi.listInbox(params);
      return res.data;
    },
  });

  const { data: stats } = useQuery({
    queryKey: ['community', 'sentiment'],
    queryFn: async () => { const res = await communityApi.getSentiment(); return res.data.data; },
  });

  return (
    <div>
      <PageHeader title="Community" description="Unified inbox for all comments" />

      {/* Sentiment stats */}
      {stats && (
        <div className="mb-4 grid grid-cols-2 gap-2 sm:grid-cols-4">
          {(['positive', 'neutral', 'negative', 'crisis'] as const).map((s) => (
            <div key={s} className="rounded-lg border bg-card p-3 text-center">
              <p className="text-xs text-muted-foreground capitalize">{s}</p>
              <p className="text-xl font-bold">{stats[s]}</p>
            </div>
          ))}
        </div>
      )}

      {/* Filter */}
      <div className="mb-4 flex gap-2">
        {['', 'positive', 'neutral', 'negative', 'crisis'].map((s) => (
          <button
            key={s}
            onClick={() => setSentimentFilter(s)}
            className={`rounded-md px-3 py-1.5 text-xs font-medium ${
              sentimentFilter === s ? 'bg-primary text-primary-foreground' : 'bg-muted text-muted-foreground hover:bg-accent'
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
          {data?.data?.map((comment) => (
            <div key={comment.id} className="rounded-lg border bg-card p-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="font-medium text-sm">{comment.author_name}</span>
                  {comment.sentiment && (
                    <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${SENTIMENT_COLORS[comment.sentiment]}`}>
                      {comment.sentiment}
                    </span>
                  )}
                </div>
                <span className="text-xs text-muted-foreground">
                  {new Date(comment.commented_at).toLocaleString()}
                </span>
              </div>
              <p className="mt-2 text-sm">{comment.message}</p>
              <div className="mt-2 flex items-center gap-2">
                <span className={`rounded px-2 py-0.5 text-xs ${
                  comment.status === 'replied' ? 'bg-green-100 text-green-700' : 'bg-yellow-100 text-yellow-700'
                }`}>
                  {comment.status}
                </span>
              </div>
            </div>
          ))}
          {data?.data?.length === 0 && (
            <p className="py-12 text-center text-sm text-muted-foreground">No comments found</p>
          )}
        </div>
      )}
    </div>
  );
}
