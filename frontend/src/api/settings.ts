import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import api from './client';

export interface ApiKeyEntry {
  id: number;
  provider: string;
  masked_key: string;
  created_at: string;
}

export function useApiKeys() {
  return useQuery<ApiKeyEntry[]>({
    queryKey: ['api-keys'],
    queryFn: () => api.get('/settings/api-keys').then(r => r.data),
  });
}

export function useAddApiKey() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: { provider: string; key: string }) =>
      api.post('/settings/api-keys', data).then(r => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['api-keys'] }),
  });
}

export function useDeleteApiKey() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => api.delete(`/settings/api-keys/${id}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['api-keys'] }),
  });
}
