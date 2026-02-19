import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { notificationsApi } from '@/api/notifications';
import { PageHeader } from '@/components/common/PageHeader';
import { LoadingSpinner } from '@/components/feedback/LoadingSpinner';

export function NotificationsPage() {
  const queryClient = useQueryClient();

  const { data, isLoading } = useQuery({
    queryKey: ['notifications'],
    queryFn: async () => { const res = await notificationsApi.list(); return res.data; },
  });

  const markAllRead = useMutation({
    mutationFn: () => notificationsApi.markAllRead(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['notifications'] });
    },
  });

  const markRead = useMutation({
    mutationFn: (id: string) => notificationsApi.markRead(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['notifications'] });
    },
  });

  return (
    <div>
      <PageHeader
        title="Notifications"
        description="Stay updated with your activities"
        actions={
          <button
            onClick={() => markAllRead.mutate()}
            className="rounded-md bg-primary px-3 py-1.5 text-xs font-medium text-primary-foreground"
          >
            Mark all read
          </button>
        }
      />

      {isLoading ? (
        <LoadingSpinner />
      ) : (
        <div className="space-y-2">
          {data?.data?.map((notif) => (
            <div
              key={notif.id}
              className={`flex items-start justify-between rounded-lg border p-4 ${
                notif.is_read ? 'bg-card' : 'bg-accent/30'
              }`}
            >
              <div className="flex-1">
                <p className="text-sm font-medium">{notif.title}</p>
                <p className="mt-1 text-xs text-muted-foreground">{notif.message}</p>
                <p className="mt-2 text-xs text-muted-foreground">
                  {new Date(notif.created_at).toLocaleString()}
                </p>
              </div>
              {!notif.is_read && (
                <button
                  onClick={() => markRead.mutate(notif.id)}
                  className="ml-2 shrink-0 rounded px-2 py-1 text-xs text-primary hover:bg-accent"
                >
                  Mark read
                </button>
              )}
            </div>
          ))}
          {data?.data?.length === 0 && (
            <p className="py-12 text-center text-sm text-muted-foreground">No notifications</p>
          )}
        </div>
      )}
    </div>
  );
}
