import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import api from './client';

export interface Subject {
  id: number;
  user_id: number;
  agent_id: number;
  name: string;
  slug: string;
  workspace_path: string;
  created_at: string;
}

export interface Course {
  id: number;
  user_id: number;
  subject_id: number;
  name: string;
  slug: string;
  instructions: string;
  workspace_path: string;
  created_at: string;
  updated_at: string;
}

export interface ChatMessage {
  id: number;
  role: string;
  content: string;
  created_at: string;
}

export function useSubjects(agentId: number) {
  return useQuery<Subject[]>({
    queryKey: ['subjects', agentId],
    queryFn: () => api.get(`/agents/${agentId}/subjects`).then(r => r.data),
    enabled: !!agentId,
  });
}

export function useSubject(subjectId: number) {
  return useQuery<Subject>({
    queryKey: ['subject', subjectId],
    queryFn: () => api.get(`/subjects/${subjectId}`).then(r => r.data),
    enabled: !!subjectId,
  });
}

export function useCreateSubject(agentId: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: { name: string }) =>
      api.post(`/agents/${agentId}/subjects`, data).then(r => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['subjects', agentId] }),
  });
}

export function useDeleteSubject() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => api.delete(`/subjects/${id}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['subjects'] }),
  });
}

export function useCourses(subjectId: number) {
  return useQuery<Course[]>({
    queryKey: ['courses', subjectId],
    queryFn: () => api.get(`/subjects/${subjectId}/courses`).then(r => r.data),
    enabled: !!subjectId,
  });
}

export function useCourse(courseId: number) {
  return useQuery<Course>({
    queryKey: ['course', courseId],
    queryFn: () => api.get(`/courses/${courseId}`).then(r => r.data),
    enabled: !!courseId,
  });
}

export function useCreateCourse(subjectId: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: { name: string; instructions: string }) =>
      api.post(`/subjects/${subjectId}/courses`, data).then(r => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['courses', subjectId] }),
  });
}

export function useDeleteCourse() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => api.delete(`/courses/${id}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['courses'] }),
  });
}

export function useCourseMessages(courseId: number) {
  return useQuery<ChatMessage[]>({
    queryKey: ['course-messages', courseId],
    queryFn: () => api.get(`/courses/${courseId}/messages`).then(r => r.data),
    enabled: !!courseId,
  });
}

export function useSendCourseMessage() {
  return useMutation({
    mutationFn: ({ courseId, content }: { courseId: number; content: string }) =>
      api.post(`/courses/${courseId}/message`, { content }).then(r => r.data),
  });
}
