import React, { createContext, useContext, useState, useEffect, useCallback, ReactNode } from 'react';
import * as Sentry from "@sentry/react";
import { supabase } from '../supabaseClient';
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
    if (!isAuthenticated || !authContext?.user?.id) {
      return;
    }

    const userId = authContext.user.id;
    let pollingInterval: NodeJS.Timeout | null = null;
    let isUnsubscribing = false;

    // Initial fetch
    fetchNotifications();
    fetchUnreadCount();
    
    // Set up Supabase Realtime subscription for notifications
    const channel = supabase
      .channel('notifications-realtime')
      .on(
        'postgres_changes',
        {
          event: 'INSERT',
          schema: 'public',
          table: 'notifications',
          filter: `user_id=eq.${userId}`
        },
        (payload) => {
          console.log('New notification received:', payload);
          
          // Add new notification to the list
          const newNotification = payload.new as Notification;
          setNotifications((prev) => [newNotification, ...prev]);
          
          // Increment unread count if notification is unread
          if (!newNotification.is_read) {
            setUnreadCount((prev) => prev + 1);
          }
          
          // Report to Sentry for monitoring
          Sentry.captureMessage('Real-time notification received', {
            level: 'info',
            tags: {
              component: 'NotificationContext',
              action: 'realtime_insert',
              notification_type: newNotification.type,
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
          console.log('Notification updated:', payload);
          
          // Update the notification in the list
          const updatedNotification = payload.new as Notification;
          setNotifications((prev) =>
            prev.map((notif) =>
              notif.id === updatedNotification.id ? updatedNotification : notif
            )
          );
          
          // Update unread count based on is_read status change
          const oldNotification = payload.old as Partial<Notification>;
          // Ensure oldNotification.is_read is a boolean before comparing values
          // to prevent incorrect count updates if the database REPLICA IDENTITY is not FULL
          if (typeof oldNotification.is_read === 'boolean' && oldNotification.is_read !== updatedNotification.is_read) {
            if (updatedNotification.is_read) {
              // Notification was marked as read
              setUnreadCount((prev) => Math.max(0, prev - 1));
            } else {
              // Notification was marked as unread
              setUnreadCount((prev) => prev + 1);
            }
          }
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
          console.log('Notification deleted:', payload);
          
          // Remove notification from the list
          const deletedNotification = payload.old as Notification;
          setNotifications((prev) =>
            prev.filter((notif) => notif.id !== deletedNotification.id)
          );
          
          // Update unread count if deleted notification was unread
          if (!deletedNotification.is_read) {
            setUnreadCount((prev) => Math.max(0, prev - 1));
          }
        }
      )
      .subscribe((status) => {
        console.log('Notification subscription status:', status);
        
        if (status === 'SUBSCRIBED') {
          // Clear polling interval if it exists (realtime is working)
          if (pollingInterval) {
            clearInterval(pollingInterval);
            pollingInterval = null;
          }
          
          Sentry.captureMessage('Notification realtime subscription active', {
            level: 'info',
            tags: {
              component: 'NotificationContext',
              action: 'realtime_subscribed',
            },
          });
        } else if (status === 'CHANNEL_ERROR' || status === 'TIMED_OUT') {
          // Fallback to polling on subscription failure (not CLOSED - that's intentional cleanup)
          console.warn('Realtime subscription failed, falling back to polling');

          if (!pollingInterval) {
            pollingInterval = setInterval(() => {
              fetchUnreadCount();
            }, 30000); // Poll every 30 seconds
          }

          Sentry.captureException(new Error(`Notification realtime subscription ${status}`), {
            tags: {
              component: 'NotificationContext',
              action: 'realtime_fallback_polling',
              status,
            },
          });
        } else if (status === 'CLOSED' && !isUnsubscribing) {
          // Unexpected closure - set up polling
          console.warn('Realtime subscription closed unexpectedly, falling back to polling');
          if (!pollingInterval) {
            pollingInterval = setInterval(() => {
              fetchUnreadCount();
            }, 30000);
          }
        }
      });

    // Cleanup subscription and polling on unmount
    return () => {
      isUnsubscribing = true;
      console.log('Unsubscribing from notification realtime channel');
      supabase.removeChannel(channel);
      if (pollingInterval) {
        clearInterval(pollingInterval);
      }
    };
  }, [isAuthenticated, authContext?.user?.id, fetchNotifications, fetchUnreadCount]);

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

