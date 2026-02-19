import { useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Building2, ChevronDown } from 'lucide-react';
import { useClientStore } from '@/stores/clientStore';
import { clientsApi } from '@/api/clients';
import { cn } from '@/utils/cn';

export function ClientSwitcher() {
  const { selectedClient, setSelectedClient, clients, setClients } = useClientStore();

  const { data } = useQuery({
    queryKey: ['clients', 'list'],
    queryFn: async () => {
      const res = await clientsApi.list();
      return res.data.data;
    },
    staleTime: 60_000,
  });

  useEffect(() => {
    if (data && data.length > 0) {
      setClients(data);
      if (!selectedClient && data[0]) {
        setSelectedClient(data[0]);
      }
    }
  }, [data, selectedClient, setClients, setSelectedClient]);

  if (!clients.length) return null;

  return (
    <div className="relative">
      <details className="group">
        <summary className="flex cursor-pointer items-center gap-2 rounded-lg border px-3 py-2 text-sm hover:bg-accent list-none">
          <Building2 className="h-4 w-4 text-muted-foreground" />
          <span className="max-w-[140px] truncate font-medium">
            {selectedClient?.name ?? 'Select client'}
          </span>
          <ChevronDown className="ml-auto h-3 w-3 text-muted-foreground transition-transform group-open:rotate-180" />
        </summary>
        <div className="absolute left-0 top-full z-50 mt-1 w-56 rounded-lg border bg-popover p-1 shadow-md">
          {clients.map((client) => (
            <button
              key={client.id}
              className={cn(
                'flex w-full items-center gap-2 rounded-md px-3 py-2 text-sm hover:bg-accent',
                selectedClient?.id === client.id && 'bg-accent font-medium',
              )}
              onClick={() => {
                setSelectedClient(client);
                // Close the details
                const details = document.querySelector('details.group[open]');
                if (details) (details as HTMLDetailsElement).open = false;
              }}
            >
              <Building2 className="h-3 w-3 text-muted-foreground" />
              <span className="truncate">{client.name}</span>
              {client.status === 'paused' && (
                <span className="ml-auto text-xs text-yellow-500">paused</span>
              )}
            </button>
          ))}
        </div>
      </details>
    </div>
  );
}
