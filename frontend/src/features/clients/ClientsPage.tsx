import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { clientsApi } from '@/api/clients';
import { PageHeader } from '@/components/common/PageHeader';
import { LoadingSpinner } from '@/components/feedback/LoadingSpinner';

export function ClientsPage() {
  const { data, isLoading } = useQuery({
    queryKey: ['clients'],
    queryFn: async () => { const res = await clientsApi.list(); return res.data; },
  });

  return (
    <div>
      <PageHeader title="Clients" description="Manage your client accounts" />

      {isLoading ? (
        <LoadingSpinner />
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {data?.data?.map((client) => (
            <Link
              key={client.id}
              to={`/clients/${client.id}`}
              className="rounded-lg border bg-card p-5 transition-colors hover:bg-accent/50"
            >
              <h3 className="font-semibold">{client.name}</h3>
              <p className="mt-1 text-xs text-muted-foreground">{client.industry || 'No industry'}</p>
              <div className="mt-3 flex items-center gap-2">
                <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${
                  client.status === 'active' ? 'bg-green-100 text-green-700' :
                  client.status === 'paused' ? 'bg-yellow-100 text-yellow-700' :
                  'bg-gray-100 text-gray-700'
                }`}>
                  {client.status}
                </span>
              </div>
            </Link>
          ))}
          {data?.data?.length === 0 && (
            <p className="col-span-full py-12 text-center text-sm text-muted-foreground">No clients found</p>
          )}
        </div>
      )}
    </div>
  );
}
