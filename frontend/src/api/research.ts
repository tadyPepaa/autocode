import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import api from './client';

export interface ResearchSession {
  id: number;
  user_id: number;
  agent_id: number;
  name: string;
  slug: string;
  status: string;
  tmux_session: string;
  workspace_path: string;
  created_at: string;
  updated_at: string;
}

export function useResearchSessions(agentId: number) {
  return useQuery<ResearchSession[]>({
    queryKey: ['research-sessions', agentId],
    queryFn: () => api.get(`/agents/${agentId}/research`).then(r => r.data),
    enabled: !!agentId,
  });
}

export function useResearchSession(sessionId: number) {
  return useQuery<ResearchSession>({
    queryKey: ['research-session', sessionId],
    queryFn: () => api.get(`/research/${sessionId}`).then(r => r.data),
    enabled: !!sessionId,
  });
}

export function useCreateResearch(agentId: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: { name: string }) =>
      api.post(`/agents/${agentId}/research`, data).then(r => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['research-sessions', agentId] }),
  });
}

export function useUpdateResearch() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, name }: { id: number; name: string }) =>
      api.put(`/research/${id}`, { name }).then(r => r.data),
    onSuccess: (_, { id }) => {
      qc.invalidateQueries({ queryKey: ['research-session', id] });
      qc.invalidateQueries({ queryKey: ['research-sessions'] });
    },
  });
}

export function useDeleteResearch() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => api.delete(`/research/${id}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['research-sessions'] }),
  });
}

export function useSendMessage() {
  return useMutation({
    mutationFn: ({ sessionId, content }: { sessionId: number; content: string }) =>
      api.post(`/research/${sessionId}/message`, { content }).then(r => r.data),
  });
}

export function useResearchAction() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, action }: { id: number; action: 'resume' | 'stop' }) =>
      api.post(`/research/${id}/${action}`).then(r => r.data),
    onSuccess: (_, { id }) => qc.invalidateQueries({ queryKey: ['research-session', id] }),
  });
}
