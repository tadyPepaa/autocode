import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import api from './client';

export interface Project {
  id: number;
  user_id: number;
  agent_id: number;
  name: string;
  slug: string;
  description: string;
  architecture: string;
  implementation_plan: string;
  status: string;
  current_step: number;
  tmux_session: string;
  workspace_path: string;
  created_at: string;
  updated_at: string;
}

export function useProjects(agentId: number) {
  return useQuery<Project[]>({
    queryKey: ['projects', agentId],
    queryFn: () => api.get(`/agents/${agentId}/projects`).then(r => r.data),
    enabled: !!agentId,
  });
}

export function useProject(id: number) {
  return useQuery<Project>({
    queryKey: ['project', id],
    queryFn: () => api.get(`/projects/${id}`).then(r => r.data),
    enabled: !!id,
  });
}

export function useCreateProject(agentId: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: { name: string; description: string; architecture?: string }) =>
      api.post(`/agents/${agentId}/projects`, data).then(r => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['projects', agentId] }),
  });
}

interface UpdateProjectVars {
  id: number;
  description?: string;
  architecture?: string;
}

export function useUpdateProject() {
  const qc = useQueryClient();
  return useMutation<unknown, Error, UpdateProjectVars>({
    mutationFn: ({ id, ...data }) =>
      api.put(`/projects/${id}`, data).then(r => r.data),
    onSuccess: (_, { id }) => qc.invalidateQueries({ queryKey: ['project', id] }),
  });
}

interface ProjectActionVars {
  id: number;
  action: 'start' | 'stop' | 'restart';
}

export function useProjectAction() {
  const qc = useQueryClient();
  return useMutation<unknown, Error, ProjectActionVars>({
    mutationFn: ({ id, action }) =>
      api.post(`/projects/${id}/${action}`).then(r => r.data),
    onSuccess: (_, { id }) => qc.invalidateQueries({ queryKey: ['project', id] }),
  });
}
