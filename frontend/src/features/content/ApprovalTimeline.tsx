import { useQuery } from '@tanstack/react-query';
import { CheckCircle, XCircle, Clock, MessageSquare } from 'lucide-react';
import { contentsApi } from '@/api/contents';
import { cn } from '@/utils/cn';

interface ApprovalTimelineProps {
  contentId: string;
}

const ACTION_CONFIG = {
  approved: { icon: CheckCircle, color: 'text-green-500', bg: 'bg-green-100 dark:bg-green-900/30', label: 'Approved' },
  rejected: { icon: XCircle, color: 'text-red-500', bg: 'bg-red-100 dark:bg-red-900/30', label: 'Rejected' },
  reviewed: { icon: Clock, color: 'text-blue-500', bg: 'bg-blue-100 dark:bg-blue-900/30', label: 'Reviewed' },
  commented: { icon: MessageSquare, color: 'text-yellow-500', bg: 'bg-yellow-100 dark:bg-yellow-900/30', label: 'Commented' },
};

export function ApprovalTimeline({ contentId }: ApprovalTimelineProps) {
  const { data: approvals } = useQuery({
    queryKey: ['content-approvals', contentId],
    queryFn: async () => {
      const res = await contentsApi.getApprovals(contentId);
      return res.data.data;
    },
    enabled: !!contentId,
  });

  if (!approvals?.length) {
    return (
      <div className="rounded-lg border bg-card p-4">
        <h3 className="mb-2 text-sm font-semibold">Approval Timeline</h3>
        <p className="text-sm text-muted-foreground">No approval history yet.</p>
      </div>
    );
  }

  return (
    <div className="rounded-lg border bg-card p-4">
      <h3 className="mb-4 text-sm font-semibold">Approval Timeline</h3>
      <div className="relative ml-3 border-l border-border pl-6">
        {approvals.map((approval: any, idx: number) => {
          const config = ACTION_CONFIG[approval.action as keyof typeof ACTION_CONFIG] ?? ACTION_CONFIG.reviewed;
          const Icon = config.icon;
          return (
            <div key={idx} className="relative mb-4 last:mb-0">
              <div className={cn('absolute -left-[33px] flex h-6 w-6 items-center justify-center rounded-full', config.bg)}>
                <Icon className={cn('h-3.5 w-3.5', config.color)} />
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <span className="text-sm font-medium">{approval.user_name ?? 'System'}</span>
                  <span className={cn('text-xs font-medium', config.color)}>{config.label}</span>
                </div>
                {approval.comment && (
                  <p className="mt-1 text-sm text-muted-foreground">{approval.comment}</p>
                )}
                <time className="text-xs text-muted-foreground">
                  {new Date(approval.created_at).toLocaleString()}
                </time>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
