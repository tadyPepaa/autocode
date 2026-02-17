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

export interface ResearchMessage {
  id: number;
  user_id: number;
  session_type: string;
  session_id: number;
  role: string;
  content: string;
  created_at: string;
}

export interface ResearchFile {
  name: string;
  path: string;
  size: number;
  modified_at: number;
}

export interface ResearchFileContent {
  name: string;
  path: string;
  content: string;
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
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ sessionId, content }: { sessionId: number; content: string }) =>
      api.post(`/research/${sessionId}/message`, { content }).then(r => r.data),
    onSuccess: (_, { sessionId }) => {
      qc.invalidateQueries({ queryKey: ['research-messages', sessionId] });
      qc.invalidateQueries({ queryKey: ['research-session', sessionId] });
    },
  });
}

export function useResearchMessages(sessionId: number) {
  return useQuery<ResearchMessage[]>({
    queryKey: ['research-messages', sessionId],
    queryFn: () => api.get(`/research/${sessionId}/messages`).then(r => r.data),
    enabled: !!sessionId,
    refetchInterval: 2000,
  });
}

export function useResearchFiles(sessionId: number) {
  return useQuery<ResearchFile[]>({
    queryKey: ['research-files', sessionId],
    queryFn: () => api.get(`/research/${sessionId}/files`).then(r => r.data),
    enabled: !!sessionId,
    refetchInterval: 3000,
  });
}

export function useResearchFileContent(sessionId: number, path: string | null) {
  return useQuery<ResearchFileContent>({
    queryKey: ['research-file-content', sessionId, path],
    queryFn: () => api.get(`/research/${sessionId}/file-content`, { params: { path } }).then(r => r.data),
    enabled: !!sessionId && !!path,
    refetchInterval: 3000,
  });
}

export function useCancelResearch() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) =>
      api.post(`/research/${id}/cancel`).then(r => r.data),
    onSuccess: (_, id) => qc.invalidateQueries({ queryKey: ['research-session', id] }),
  });
}
