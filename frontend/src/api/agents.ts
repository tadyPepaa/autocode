import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import api from './client';

export interface Agent {
  id: number;
  name: string;
  type: string;
  model: string;
  identity: string;
  tools: string;
  global_rules: string;
  created_at: string;
}

export function useAgents() {
  return useQuery<Agent[]>({
    queryKey: ['agents'],
    queryFn: () => api.get('/agents').then(r => r.data),
  });
}

export function useAgent(id: number) {
  return useQuery<Agent>({
    queryKey: ['agents', id],
    queryFn: () => api.get(`/agents/${id}`).then(r => r.data),
    enabled: !!id,
  });
}

export function useCreateAgent() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: Partial<Omit<Agent, 'id' | 'created_at'>>) =>
      api.post('/agents', data).then(r => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['agents'] }),
  });
}

export function useUpdateAgent() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, ...data }: Partial<Agent> & { id: number }) =>
      api.put(`/agents/${id}`, data).then(r => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['agents'] }),
  });
}

export function useDeleteAgent() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => api.delete(`/agents/${id}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['agents'] }),
  });
}
