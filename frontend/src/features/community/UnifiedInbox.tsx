import { useState, useRef, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { format } from 'date-fns';
import {
  Instagram,
  Facebook,
  Youtube,
  Send,
  Filter,
  RefreshCw,
} from 'lucide-react';
import { communityApi } from '@/api/community';
import type { Comment, Platform, Sentiment } from '@/types';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { PageHeader } from '@/components/common/PageHeader';
import { cn } from '@/utils/cn';

const SENTIMENT_CONFIG: Record<
  Sentiment,
  { label: string; badgeClass: string; dotClass: string }
> = {
  positive: {
    label: 'Positive',
    badgeClass: 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400',
    dotClass: 'bg-green-500',
  },
  neutral: {
    label: 'Neutral',
    badgeClass: 'bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400',
    dotClass: 'bg-gray-400',
  },
  negative: {
    label: 'Negative',
    badgeClass: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400',
    dotClass: 'bg-red-500',
  },
  crisis: {
    label: 'CRISIS',
    badgeClass: 'bg-red-600 text-white font-bold dark:bg-red-700',
    dotClass: 'bg-red-600 animate-pulse',
  },
};

const PLATFORM_ICONS: Record<Platform, React.ReactNode> = {
  instagram: <Instagram className="h-3.5 w-3.5 text-pink-500" />,
  facebook: <Facebook className="h-3.5 w-3.5 text-blue-600" />,
  youtube: <Youtube className="h-3.5 w-3.5 text-red-500" />,
};

interface FilterState {
  platform: Platform | 'all';
  sentiment: Sentiment | 'all';
  status: string;
}

interface CommentItemProps {
  comment: Comment;
  isSelected: boolean;
  onSelect: () => void;
}

function CommentItem({ comment, isSelected, onSelect }: CommentItemProps) {
  const sentiment = comment.sentiment ?? 'neutral';
  const cfg = SENTIMENT_CONFIG[sentiment];

  return (
    <button
      type="button"
      onClick={onSelect}
      className={cn(
        'w-full rounded-lg border p-3 text-left transition-colors',
        isSelected
          ? 'border-primary bg-primary/5'
          : 'border-border bg-card hover:bg-accent/50'
      )}
    >
      <div className="flex items-start gap-2">
        <span className={cn('mt-1.5 h-2 w-2 flex-shrink-0 rounded-full', cfg.dotClass)} />
        <div className="flex-1 overflow-hidden">
          <div className="flex items-center gap-2 mb-0.5">
            <span className="text-xs font-semibold text-foreground truncate">
              {comment.author_name}
            </span>
            {comment.platform_account_id && (
              <span className="flex-shrink-0">
                {PLATFORM_ICONS['instagram']}
              </span>
            )}
          </div>
          <p
            className={cn(
              'text-xs text-foreground/80 line-clamp-2',
              sentiment === 'crisis' && 'font-semibold text-red-600 dark:text-red-400'
            )}
          >
            {comment.message}
          </p>
          <div className="mt-1 flex items-center gap-2">
            <span className={cn('rounded-full px-1.5 py-0.5 text-xs', cfg.badgeClass)}>
              {cfg.label}
            </span>
            <span className="text-xs text-muted-foreground">
              {format(new Date(comment.commented_at), 'MMM d, HH:mm')}
            </span>
          </div>
        </div>
      </div>
    </button>
  );
}

export function UnifiedInbox() {
  const queryClient = useQueryClient();
  const [filters, setFilters] = useState<FilterState>({
    platform: 'all',
    sentiment: 'all',
    status: 'all',
  });
  const [selectedComment, setSelectedComment] = useState<Comment | null>(null);
  const [replyText, setReplyText] = useState('');
  const [showFilters, setShowFilters] = useState(false);
  const streamRef = useRef<HTMLDivElement>(null);

  const queryParams: Record<string, string> = { per_page: '50' };
  if (filters.platform !== 'all') queryParams.platform = filters.platform;
  if (filters.sentiment !== 'all') queryParams.sentiment = filters.sentiment;
  if (filters.status !== 'all') queryParams.status = filters.status;

  const { data: comments = [], isLoading, refetch } = useQuery({
    queryKey: ['community', 'inbox', filters],
    queryFn: async () => {
      const res = await communityApi.listInbox(queryParams);
      return res.data.data;
    },
    refetchInterval: 30_000,
  });

  const replyMutation = useMutation({
    mutationFn: ({ id, message }: { id: string; message: string }) =>
      communityApi.reply(id, message),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['community', 'inbox'] });
      setReplyText('');
    },
  });

  const handleSendReply = () => {
    if (!selectedComment || !replyText.trim()) return;
    replyMutation.mutate({ id: selectedComment.id, message: replyText.trim() });
  };

  // Scroll to bottom of comment stream when new data arrives
  useEffect(() => {
    if (streamRef.current) {
      streamRef.current.scrollTop = 0;
    }
  }, [comments]);

  const crisisComments = comments.filter((c) => c.sentiment === 'crisis');

  return (
    <div className="flex flex-col gap-4 h-full">
      <PageHeader
        title="Unified Inbox"
        description="Monitor and respond to comments across all platforms"
        actions={
          <div className="flex gap-2">
            {crisisComments.length > 0 && (
              <Badge className="bg-red-600 text-white animate-pulse">
                {crisisComments.length} Crisis
              </Badge>
            )}
            <Button
              variant="outline"
              size="sm"
              onClick={() => setShowFilters((v) => !v)}
            >
              <Filter className="h-4 w-4" />
              Filters
            </Button>
            <Button
              variant="outline"
              size="icon"
              onClick={() => void refetch()}
              aria-label="Refresh"
            >
              <RefreshCw className={cn('h-4 w-4', isLoading && 'animate-spin')} />
            </Button>
          </div>
        }
      />

      {/* Filter bar */}
      {showFilters && (
        <div className="flex flex-wrap gap-3 rounded-lg border border-border bg-card p-3">
          <div className="flex items-center gap-2">
            <span className="text-xs font-medium text-muted-foreground">Platform:</span>
            {(['all', 'instagram', 'facebook', 'youtube'] as const).map((p) => (
              <button
                key={p}
                type="button"
                onClick={() => setFilters((f) => ({ ...f, platform: p }))}
                className={cn(
                  'rounded px-2 py-0.5 text-xs transition-colors',
                  filters.platform === p
                    ? 'bg-primary text-primary-foreground'
                    : 'bg-muted text-muted-foreground hover:bg-accent'
                )}
              >
                {p === 'all' ? 'All' : p.charAt(0).toUpperCase() + p.slice(1)}
              </button>
            ))}
          </div>
          <div className="flex items-center gap-2">
            <span className="text-xs font-medium text-muted-foreground">Sentiment:</span>
            {(['all', 'positive', 'neutral', 'negative', 'crisis'] as const).map((s) => (
              <button
                key={s}
                type="button"
                onClick={() => setFilters((f) => ({ ...f, sentiment: s }))}
                className={cn(
                  'rounded px-2 py-0.5 text-xs transition-colors',
                  filters.sentiment === s
                    ? 'bg-primary text-primary-foreground'
                    : 'bg-muted text-muted-foreground hover:bg-accent'
                )}
              >
                {s === 'all' ? 'All' : s.charAt(0).toUpperCase() + s.slice(1)}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Three-panel layout */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-[280px_1fr_300px] min-h-[500px]">
        {/* Left: Filter sidebar — platform platform quick access */}
        <div className="rounded-lg border border-border bg-card p-3">
          <p className="mb-3 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
            Quick Filters
          </p>
          <div className="space-y-1">
            {[
              { label: 'All Comments', value: 'all', count: comments.length },
              {
                label: 'Crisis Alerts',
                value: 'crisis',
                count: comments.filter((c) => c.sentiment === 'crisis').length,
              },
              {
                label: 'Negative',
                value: 'negative',
                count: comments.filter((c) => c.sentiment === 'negative').length,
              },
              {
                label: 'Pending Reply',
                value: 'pending',
                count: comments.filter((c) => c.status === 'pending').length,
              },
            ].map((item) => (
              <button
                key={item.value}
                type="button"
                onClick={() => {
                  if (item.value === 'pending') {
                    setFilters((f) => ({ ...f, status: 'pending', sentiment: 'all' }));
                  } else if (item.value === 'all') {
                    setFilters({ platform: 'all', sentiment: 'all', status: 'all' });
                  } else {
                    setFilters((f) => ({
                      ...f,
                      sentiment: item.value as Sentiment,
                      status: 'all',
                    }));
                  }
                }}
                className="flex w-full items-center justify-between rounded px-2 py-1.5 text-sm hover:bg-accent transition-colors"
              >
                <span
                  className={cn(
                    item.value === 'crisis' && 'font-semibold text-red-600'
                  )}
                >
                  {item.label}
                </span>
                <Badge variant="secondary" className="text-xs">
                  {item.count}
                </Badge>
              </button>
            ))}
          </div>

          <p className="mt-4 mb-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
            Platforms
          </p>
          <div className="space-y-1">
            {(['instagram', 'facebook', 'youtube'] as const).map((platform) => (
              <button
                key={platform}
                type="button"
                onClick={() => setFilters((f) => ({ ...f, platform }))}
                className={cn(
                  'flex w-full items-center gap-2 rounded px-2 py-1.5 text-sm hover:bg-accent transition-colors',
                  filters.platform === platform && 'bg-accent font-medium'
                )}
              >
                {PLATFORM_ICONS[platform]}
                <span className="capitalize">{platform}</span>
              </button>
            ))}
          </div>
        </div>

        {/* Center: Comment stream */}
        <div className="flex flex-col rounded-lg border border-border bg-muted/20">
          <div className="flex items-center justify-between border-b border-border px-3 py-2">
            <span className="text-sm font-medium">
              {comments.length} comments
            </span>
            {isLoading && (
              <RefreshCw className="h-3.5 w-3.5 animate-spin text-muted-foreground" />
            )}
          </div>
          <div
            ref={streamRef}
            className="flex-1 overflow-y-auto p-2 space-y-2 max-h-[500px]"
          >
            {comments.length === 0 && !isLoading && (
              <div className="flex h-40 items-center justify-center text-sm text-muted-foreground">
                No comments found
              </div>
            )}
            {comments.map((comment) => (
              <CommentItem
                key={comment.id}
                comment={comment}
                isSelected={selectedComment?.id === comment.id}
                onSelect={() => {
                  setSelectedComment(comment);
                  setReplyText(comment.ai_reply_draft ?? '');
                }}
              />
            ))}
          </div>
        </div>

        {/* Right: Reply panel */}
        <div className="flex flex-col rounded-lg border border-border bg-card">
          {selectedComment ? (
            <>
              <div className="border-b border-border p-3">
                <div className="flex items-center gap-2 mb-2">
                  <span
                    className={cn(
                      'h-2 w-2 rounded-full',
                      SENTIMENT_CONFIG[selectedComment.sentiment ?? 'neutral'].dotClass
                    )}
                  />
                  <span className="text-sm font-semibold text-foreground">
                    {selectedComment.author_name}
                  </span>
                </div>
                <p className="text-xs text-muted-foreground leading-relaxed">
                  {selectedComment.message}
                </p>
                <p className="mt-1 text-xs text-muted-foreground">
                  {format(new Date(selectedComment.commented_at), 'PPp')}
                </p>
                {selectedComment.sentiment && (
                  <div className="mt-2">
                    <span
                      className={cn(
                        'rounded-full px-2 py-0.5 text-xs',
                        SENTIMENT_CONFIG[selectedComment.sentiment].badgeClass
                      )}
                    >
                      {SENTIMENT_CONFIG[selectedComment.sentiment].label}
                    </span>
                  </div>
                )}
              </div>
              <div className="flex flex-1 flex-col p-3 gap-2">
                <p className="text-xs font-medium text-muted-foreground">Reply</p>
                {selectedComment.ai_reply_draft && (
                  <div className="rounded bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 p-2">
                    <p className="text-xs text-blue-700 dark:text-blue-300 font-medium mb-1">
                      AI Draft
                    </p>
                    <p className="text-xs text-blue-800 dark:text-blue-200">
                      {selectedComment.ai_reply_draft}
                    </p>
                    <button
                      type="button"
                      onClick={() => setReplyText(selectedComment.ai_reply_draft!)}
                      className="mt-1 text-xs text-blue-600 hover:underline"
                    >
                      Use this draft
                    </button>
                  </div>
                )}
                <textarea
                  value={replyText}
                  onChange={(e) => setReplyText(e.target.value)}
                  placeholder="Type your reply..."
                  rows={5}
                  className="flex-1 resize-none rounded-md border border-input bg-background px-3 py-2 text-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                />
                <Button
                  onClick={handleSendReply}
                  disabled={replyMutation.isPending || !replyText.trim()}
                  className="w-full"
                >
                  <Send className="h-4 w-4" />
                  {replyMutation.isPending ? 'Sending...' : 'Send Reply'}
                </Button>
              </div>
            </>
          ) : (
            <div className="flex flex-1 items-center justify-center text-sm text-muted-foreground p-4 text-center">
              Select a comment to view details and reply
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
