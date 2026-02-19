import { useQuery } from '@tanstack/react-query';
import { settingsApi } from '@/api/settings';
import { PageHeader } from '@/components/common/PageHeader';
import { LoadingSpinner } from '@/components/feedback/LoadingSpinner';

export function SettingsPage() {
  const { data: connections, isLoading } = useQuery({
    queryKey: ['settings', 'platform-connections'],
    queryFn: async () => { const res = await settingsApi.getPlatformConnections(); return res.data.data; },
  });

  const { data: prefs } = useQuery({
    queryKey: ['settings', 'notification-prefs'],
    queryFn: async () => { const res = await settingsApi.getNotificationPrefs(); return res.data.data; },
  });

  return (
    <div>
      <PageHeader title="Settings" description="Platform connections and preferences" />

      {isLoading ? (
        <LoadingSpinner />
      ) : (
        <div className="space-y-6">
          {/* Platform connections */}
          <div className="rounded-lg border bg-card p-6">
            <h3 className="mb-4 font-semibold">Platform Connections</h3>
            <div className="space-y-3">
              {connections?.map((conn) => (
                <div key={conn.platform} className="flex items-center justify-between rounded-lg border p-4">
                  <div>
                    <p className="text-sm font-medium capitalize">{conn.platform}</p>
                    {conn.account_name && (
                      <p className="text-xs text-muted-foreground">{conn.account_name}</p>
                    )}
                  </div>
                  <span className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${
                    conn.is_connected ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-700'
                  }`}>
                    {conn.is_connected ? 'Connected' : 'Not Connected'}
                  </span>
                </div>
              ))}
              {(!connections || connections.length === 0) && (
                <p className="text-sm text-muted-foreground">No platform connections configured</p>
              )}
            </div>
          </div>

          {/* Notification preferences */}
          <div className="rounded-lg border bg-card p-6">
            <h3 className="mb-4 font-semibold">Notification Preferences</h3>
            {prefs ? (
              <dl className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <dt className="text-muted-foreground">Email Notifications</dt>
                  <dd className="mt-1">{prefs.email_enabled ? 'Enabled' : 'Disabled'}</dd>
                </div>
                <div>
                  <dt className="text-muted-foreground">Kakao Notifications</dt>
                  <dd className="mt-1">{prefs.kakao_enabled ? 'Enabled' : 'Disabled'}</dd>
                </div>
                <div>
                  <dt className="text-muted-foreground">Crisis Alerts</dt>
                  <dd className="mt-1">{prefs.crisis_alert?.length ? prefs.crisis_alert.join(', ') : 'None'}</dd>
                </div>
              </dl>
            ) : (
              <p className="text-sm text-muted-foreground">No preferences configured</p>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
