// ============================================================
// CareerPilot - Notification API methods
// ============================================================

import { api } from './api';
import type { Notification } from '@/types';

export const notificationApi = {
  getAll: (unreadOnly = false, limit = 50) =>
    api.get<{ notifications: Notification[]; unread_count: number; total: number }>(
      `/notifications?unread_only=${unreadOnly}&limit=${limit}`
    ),

  getUnreadCount: () =>
    api.get<{ unread_count: number }>('/notifications/unread-count'),

  markAsRead: (id: string) =>
    api.post(`/notifications/${id}/read`),

  markAllAsRead: () =>
    api.post('/notifications/read-all'),

  delete: (id: string) =>
    api.delete(`/notifications/${id}`),
};
