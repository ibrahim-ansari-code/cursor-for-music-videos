import React, { useState, useEffect, useCallback, ReactNode } from 'react';
import * as Sentry from "@sentry/react";
import { supabase } from '../utils/supabaseClient';
import {
  getNotifications,
  getUnreadCount,
  markAsRead,
  markAllAsRead,
  dismissNotification,
  type Notification,
} from '../utils/api/notifications';
import { useAuth } from '../hooks/useAuth';
import { NotificationContext, type NotificationContextValue } from './notificationContextTypes';

interface NotificationProviderProps {
  children: ReactNode;
}

export const NotificationProvider: React.FC<NotificationProviderProps> = ({ children }) => {
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [unreadCount, setUnreadCount] = useState<number>(0);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  
  const { user } = useAuth();
  const isAuthenticated = !!user;

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
          portal: 'tenant',
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
          portal: 'tenant',
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
          portal: 'tenant',
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
          portal: 'tenant',
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
          portal: 'tenant',
          notificationId,
        },
      });
      throw err;
    }
  }, [notifications]);

  // Fetch notifications and unread count on mount and auth change
  useEffect(() => {
    if (!isAuthenticated || !user?.id) {
      return;
    }

    const userId = user.id;
    let pollingInterval: NodeJS.Timeout | null = null;
    
    // Initial fetch
    fetchNotifications();
    fetchUnreadCount();
    
    // Set up Supabase Realtime subscription for notifications
    const channel = supabase
      .channel('tenant-notifications-realtime')
      .on(
        'postgres_changes',
        {
          event: 'INSERT',
          schema: 'public',
          table: 'notifications',
          filter: `user_id=eq.${userId}`
        },
        (payload) => {
          console.log('New notification received (tenant):', payload);

          // Re-fetch notifications to get properly formatted data from API
          // This ensures field names match (metadata_ vs metadata) and data is fresh
          fetchNotifications();
          fetchUnreadCount();

          // Report to Sentry for monitoring
          const newNotification = payload.new as Partial<Notification>;
          Sentry.captureMessage('Real-time notification received (tenant)', {
            level: 'info',
            tags: {
              component: 'NotificationContext',
              action: 'realtime_insert',
              portal: 'tenant',
              notification_type: newNotification.type || 'unknown',
            },
          });
        }
      )
      .on(
        'postgres_changes',
        {
          event: 'UPDATE',
          schema: 'public',
          table: 'notifications',
          filter: `user_id=eq.${userId}`
        },
        (payload) => {
          console.log('Notification updated (tenant):', payload);

          // Re-fetch to get properly formatted data from API
          fetchNotifications();
          fetchUnreadCount();
        }
      )
      .on(
        'postgres_changes',
        {
          event: 'DELETE',
          schema: 'public',
          table: 'notifications',
          filter: `user_id=eq.${userId}`
        },
        (payload) => {
          console.log('Notification deleted (tenant):', payload);

          // Re-fetch to get updated list and count
          fetchNotifications();
          fetchUnreadCount();
        }
      )
      .subscribe((status) => {
        console.log('Notification subscription status (tenant):', status);
        
        if (status === 'SUBSCRIBED') {
          // Clear polling interval if it exists (realtime is working)
          if (pollingInterval) {
            clearInterval(pollingInterval);
            pollingInterval = null;
          }
          
          Sentry.captureMessage('Notification realtime subscription active (tenant)', {
            level: 'info',
            tags: {
              component: 'NotificationContext',
              action: 'realtime_subscribed',
              portal: 'tenant',
            },
          });
        } else if (status === 'CHANNEL_ERROR' || status === 'TIMED_OUT' || status === 'CLOSED') {
          // Fallback to polling on subscription failure
          console.warn('Realtime subscription failed (tenant), falling back to polling');
          
          if (!pollingInterval) {
            pollingInterval = setInterval(() => {
              fetchUnreadCount();
            }, 30000); // Poll every 30 seconds
          }
          
          Sentry.captureException(new Error(`Notification realtime subscription ${status} (tenant)`), {
            tags: {
              component: 'NotificationContext',
              action: 'realtime_fallback_polling',
              portal: 'tenant',
              status,
            },
          });
        }
      });
    
    // Cleanup subscription and polling on unmount
    return () => {
      console.log('Unsubscribing from notification realtime channel (tenant)');
      supabase.removeChannel(channel);
      if (pollingInterval) {
        clearInterval(pollingInterval);
      }
    };
  }, [isAuthenticated, user?.id, fetchNotifications, fetchUnreadCount]);

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

