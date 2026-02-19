import { create } from 'zustand';
import type { Client } from '@/types';

interface ClientState {
  selectedClient: Client | null;
  clients: Client[];
  setSelectedClient: (client: Client | null) => void;
  setClients: (clients: Client[]) => void;
}

export const useClientStore = create<ClientState>((set) => ({
  selectedClient: null,
  clients: [],
  setSelectedClient: (client) => set({ selectedClient: client }),
  setClients: (clients) => set({ clients }),
}));
