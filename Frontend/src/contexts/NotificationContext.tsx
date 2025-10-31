import React, { createContext, useContext, useState, useEffect, useCallback, ReactNode } from 'react';
import * as Sentry from "@sentry/react";
import {
  getNotifications,
  getUnreadCount,
  markAsRead,
  markAllAsRead,
  dismissNotification,
  type Notification
} from '../utils/api/notifications';
import { AuthContext } from './AuthContext';

interface NotificationContextValue {
  notifications: Notification[];
  unreadCount: number;
  isLoading: boolean;
  error: string | null;
  fetchNotifications: () => Promise<void>;
  fetchUnreadCount: () => Promise<void>;
  markNotificationAsRead: (notificationId: string) => Promise<void>;
  markAllNotificationsAsRead: () => Promise<void>;
  dismissNotification: (notificationId: string) => Promise<void>;
}

const NotificationContext = createContext<NotificationContextValue | null>(null);

export const useNotifications = (): NotificationContextValue => {
  const context = useContext(NotificationContext);
  if (!context) {
    throw new Error('useNotifications must be used within a NotificationProvider');
  }
  return context;
};

interface NotificationProviderProps {
  children: ReactNode;
}

export const NotificationProvider: React.FC<NotificationProviderProps> = ({ children }) => {
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [unreadCount, setUnreadCount] = useState<number>(0);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  
  const authContext = useContext(AuthContext);
  const isAuthenticated = !!authContext?.user;

  // Fetch notifications
  const fetchNotifications = useCallback(async () => {
    if (!isAuthenticated) return;
    
    setIsLoading(true);
    setError(null);
    
    try {
      const data = await getNotifications({ limit: 20, offset: 0 });
      setNotifications(data.notifications);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to fetch notifications';
      setError(errorMessage);
      Sentry.captureException(err, {
        tags: {
          component: 'NotificationContext',
          action: 'fetch_notifications',
        },
      });
    } finally {
      setIsLoading(false);
    }
  }, [isAuthenticated]);

  // Fetch unread count
  const fetchUnreadCount = useCallback(async () => {
    if (!isAuthenticated) return;
    
    try {
      const data = await getUnreadCount();
      setUnreadCount(data.unread_count);
    } catch (err) {
      Sentry.captureException(err, {
        tags: {
          component: 'NotificationContext',
          action: 'fetch_unread_count',
        },
      });
    }
  }, [isAuthenticated]);

  // Mark single notification as read
  const markNotificationAsRead = useCallback(async (notificationId: string) => {
    try {
      await markAsRead([notificationId]);
      
      // Update local state
      setNotifications((prev) =>
        prev.map((notif) =>
          notif.id === notificationId ? { ...notif, is_read: true, read_at: new Date().toISOString() } : notif
        )
      );
      
      // Update unread count
      setUnreadCount((prev) => Math.max(0, prev - 1));
    } catch (err) {
      Sentry.captureException(err, {
        tags: {
          component: 'NotificationContext',
          action: 'mark_as_read',
          notificationId,
        },
      });
      throw err;
    }
  }, []);

  // Mark all notifications as read
  const markAllNotificationsAsRead = useCallback(async () => {
    try {
      await markAllAsRead();
      
      // Update local state
      setNotifications((prev) =>
        prev.map((notif) => ({ ...notif, is_read: true, read_at: new Date().toISOString() }))
      );
      
      setUnreadCount(0);
    } catch (err) {
      Sentry.captureException(err, {
        tags: {
          component: 'NotificationContext',
          action: 'mark_all_as_read',
        },
      });
      throw err;
    }
  }, []);

  // Dismiss (archive) a notification
  const dismissNotificationLocal = useCallback(async (notificationId: string) => {
    try {
      await dismissNotification(notificationId);
      
      // Remove from local state
      setNotifications((prev) => prev.filter((notif) => notif.id !== notificationId));
      
      // Update unread count if notification was unread
      const notification = notifications.find((n) => n.id === notificationId);
      if (notification && !notification.is_read) {
        setUnreadCount((prev) => Math.max(0, prev - 1));
      }
    } catch (err) {
      Sentry.captureException(err, {
        tags: {
          component: 'NotificationContext',
          action: 'dismiss_notification',
          notificationId,
        },
      });
      throw err;
    }
  }, [notifications]);

  // Fetch notifications and unread count on mount and auth change
  useEffect(() => {
    if (isAuthenticated) {
      fetchNotifications();
      fetchUnreadCount();
      
      // Poll for new notifications every 30 seconds
      const interval = setInterval(() => {
        fetchUnreadCount();
      }, 30000);
      
      return () => clearInterval(interval);
    }
  }, [isAuthenticated, fetchNotifications, fetchUnreadCount]);

  const value: NotificationContextValue = {
    notifications,
    unreadCount,
    isLoading,
    error,
    fetchNotifications,
    fetchUnreadCount,
    markNotificationAsRead,
    markAllNotificationsAsRead,
    dismissNotification: dismissNotificationLocal,
  };

  return (
    <NotificationContext.Provider value={value}>
      {children}
    </NotificationContext.Provider>
  );
};

