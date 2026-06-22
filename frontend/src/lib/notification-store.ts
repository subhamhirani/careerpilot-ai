// ============================================================
// CareerPilot - Notification Zustand Store
// ============================================================

import { create } from 'zustand';
import type { Notification } from '@/types';
import { notificationApi } from './notification-api';

interface NotificationState {
  notifications: Notification[];
  unreadCount: number;
  loading: boolean;
  fetchNotifications: (unreadOnly?: boolean) => Promise<void>;
  fetchUnreadCount: () => Promise<void>;
  markAsRead: (id: string) => Promise<void>;
  markAllAsRead: () => Promise<void>;
  deleteNotification: (id: string) => Promise<void>;
  addNotification: (n: Notification) => void;
}

export const useNotificationStore = create<NotificationState>((set, get) => ({
  notifications: [],
  unreadCount: 0,
  loading: false,

  fetchNotifications: async (unreadOnly = false) => {
    set({ loading: true });
    try {
      const data = await notificationApi.getAll(unreadOnly);
      set({
        notifications: data.notifications || [],
        unreadCount: data.unread_count || 0,
      });
    } catch {
      // silent
    } finally {
      set({ loading: false });
    }
  },

  fetchUnreadCount: async () => {
    try {
      const data = await notificationApi.getUnreadCount();
      set({ unreadCount: data.unread_count || 0 });
    } catch {
      // silent
    }
  },

  markAsRead: async (id: string) => {
    try {
      await notificationApi.markAsRead(id);
      set((state) => ({
        notifications: state.notifications.map((n) =>
          n.id === id ? { ...n, is_read: true } : n
        ),
        unreadCount: Math.max(0, state.unreadCount - 1),
      }));
    } catch {
      // silent
    }
  },

  markAllAsRead: async () => {
    try {
      await notificationApi.markAllAsRead();
      set((state) => ({
        notifications: state.notifications.map((n) => ({ ...n, is_read: true })),
        unreadCount: 0,
      }));
    } catch {
      // silent
    }
  },

  deleteNotification: async (id: string) => {
    try {
      await notificationApi.delete(id);
      set((state) => {
        const n = state.notifications.find((x) => x.id === id);
        return {
          notifications: state.notifications.filter((x) => x.id !== id),
          unreadCount: n && !n.is_read ? Math.max(0, state.unreadCount - 1) : state.unreadCount,
        };
      });
    } catch {
      // silent
    }
  },

  addNotification: (n: Notification) => {
    set((state) => ({
      notifications: [n, ...state.notifications],
      unreadCount: state.unreadCount + 1,
    }));
  },
}));
