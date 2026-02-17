import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import api from './client';

// Types

export interface SocialAccount {
  id: number;
  platform: 'instagram' | 'facebook';
  account_name: string;
  created_at: string;
}

export interface FeedItem {
  id: string;
  platform: 'instagram' | 'facebook';
  caption?: string;
  message?: string;
  media_url?: string;
  timestamp: string;
  like_count?: number;
  comments_count?: number;
}

export interface Story {
  id: string;
  media_url: string;
  timestamp: string;
}

export interface Comment {
  id: string;
  text?: string;
  message?: string;
  timestamp: string;
  username?: string;
}

export interface DmConversation {
  id: string;
  participants: string[];
  messages: { id: string; text: string; timestamp: string; from?: string }[];
}

// Hooks

export function useSocialAccounts() {
  return useQuery<SocialAccount[]>({
    queryKey: ['social-accounts'],
    queryFn: () => api.get('/social/accounts').then(r => r.data),
  });
}

export function useConnectInstagram() {
  return useMutation({
    mutationFn: () =>
      api.post('/social/connect/instagram').then(r => r.data as { auth_url: string; state: string }),
  });
}

export function useConnectFacebook() {
  return useMutation({
    mutationFn: () =>
      api.post('/social/connect/facebook').then(r => r.data as { auth_url: string; state: string }),
  });
}

export function useDisconnectAccount() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => api.delete(`/social/accounts/${id}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['social-accounts'] }),
  });
}

export function useSocialFeed() {
  return useQuery<FeedItem[]>({
    queryKey: ['social-feed'],
    queryFn: () => api.get('/social/feed').then(r => r.data.items as FeedItem[]),
  });
}

export function useSocialStories() {
  return useQuery<Story[]>({
    queryKey: ['social-stories'],
    queryFn: () => api.get('/social/stories').then(r => r.data.stories as Story[]),
  });
}

export function usePublishPost() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: { platform: 'instagram' | 'facebook' | 'both'; caption: string; image_url?: string }) =>
      api.post('/social/posts', data).then(r => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['social-feed'] }),
  });
}

export function usePostComments(postId: string, platform: string) {
  return useQuery<Comment[]>({
    queryKey: ['social-comments', postId, platform],
    queryFn: () =>
      api.get(`/social/comments/${postId}`, { params: { platform } }).then(r => r.data.comments as Comment[]),
    enabled: !!postId,
  });
}

export function useReplyComment() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ commentId, message, platform }: { commentId: string; message: string; platform: string }) =>
      api.post(`/social/comments/${commentId}/reply`, { message, platform }).then(r => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['social-comments'] }),
  });
}

export function useSocialDms() {
  return useQuery<DmConversation[]>({
    queryKey: ['social-dms'],
    queryFn: () => api.get('/social/dms').then(r => r.data.conversations as DmConversation[]),
  });
}

export function useReplyDm() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ threadId, message }: { threadId: string; message: string }) =>
      api.post(`/social/dms/${threadId}/reply`, { message }).then(r => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['social-dms'] }),
  });
}

export function useSocialAiChat() {
  return useMutation({
    mutationFn: (message: string) =>
      api.post('/social/ai/chat', { message }).then(r => r.data.response as string),
  });
}
