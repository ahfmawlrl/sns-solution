import { useParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { clientsApi } from '@/api/clients';
import { PageHeader } from '@/components/common/PageHeader';
import { LoadingSpinner } from '@/components/feedback/LoadingSpinner';

export function ClientDetailPage() {
  const { id } = useParams<{ id: string }>();

  const { data: client, isLoading } = useQuery({
    queryKey: ['client', id],
    queryFn: async () => { const res = await clientsApi.get(id!); return res.data.data; },
    enabled: !!id,
  });

  const { data: accounts } = useQuery({
    queryKey: ['client', id, 'accounts'],
    queryFn: async () => { const res = await clientsApi.listAccounts(id!); return res.data.data; },
    enabled: !!id,
  });

  if (isLoading) return <LoadingSpinner />;
  if (!client) return <p className="text-center text-muted-foreground">Client not found</p>;

  return (
    <div>
      <PageHeader title={client.name} description={client.industry || ''} />

      <div className="grid gap-6 lg:grid-cols-3">
        {/* Client info */}
        <div className="lg:col-span-2 space-y-4">
          <div className="rounded-lg border bg-card p-6">
            <h3 className="mb-4 font-semibold">Basic Info</h3>
            <dl className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <dt className="text-muted-foreground">Status</dt>
                <dd className="mt-1">
                  <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${
                    client.status === 'active' ? 'bg-green-100 text-green-700' :
                    client.status === 'paused' ? 'bg-yellow-100 text-yellow-700' :
                    'bg-gray-100 text-gray-700'
                  }`}>
                    {client.status}
                  </span>
                </dd>
              </div>
              <div>
                <dt className="text-muted-foreground">Industry</dt>
                <dd className="mt-1">{client.industry || '-'}</dd>
              </div>
              <div>
                <dt className="text-muted-foreground">Contract Start</dt>
                <dd className="mt-1">{client.contract_start ? new Date(client.contract_start).toLocaleDateString() : '-'}</dd>
              </div>
              <div>
                <dt className="text-muted-foreground">Contract End</dt>
                <dd className="mt-1">{client.contract_end ? new Date(client.contract_end).toLocaleDateString() : '-'}</dd>
              </div>
            </dl>
          </div>

          {client.brand_guidelines && (
            <div className="rounded-lg border bg-card p-6">
              <h3 className="mb-4 font-semibold">Brand Guidelines</h3>
              <pre className="whitespace-pre-wrap text-sm text-muted-foreground">
                {JSON.stringify(client.brand_guidelines, null, 2)}
              </pre>
            </div>
          )}
        </div>

        {/* Platform accounts */}
        <div className="space-y-4">
          <div className="rounded-lg border bg-card p-4">
            <h3 className="mb-3 font-semibold text-sm">Platform Accounts</h3>
            {accounts && accounts.length > 0 ? (
              <div className="space-y-2">
                {accounts.map((acc) => (
                  <div key={acc.id} className="flex items-center justify-between rounded border p-2">
                    <div>
                      <p className="text-sm font-medium capitalize">{acc.platform}</p>
                      <p className="text-xs text-muted-foreground">{acc.account_name}</p>
                    </div>
                    <span className={`rounded-full px-2 py-0.5 text-xs ${
                      acc.is_connected ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-700'
                    }`}>
                      {acc.is_connected ? 'Connected' : 'Disconnected'}
                    </span>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-xs text-muted-foreground">No platform accounts linked</p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
