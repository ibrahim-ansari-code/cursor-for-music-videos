import React from 'react';
import { useNavigate } from 'react-router-dom';
import type { Notification } from '../../utils/api/notifications';

interface NotificationItemProps {
  notification: Notification;
  onMarkAsRead: (id: string) => Promise<void>;
  onDismiss: (id: string) => Promise<void>;
  onNavigate?: () => void;
}

const NotificationItem: React.FC<NotificationItemProps> = ({
  notification,
  onMarkAsRead,
  onDismiss,
  onNavigate,
}) => {
  const navigate = useNavigate();

  const handleClick = () => {
    // Mark as read (fire and forget - don't block navigation)
    if (!notification.is_read) {
      onMarkAsRead(notification.id).catch((error) => {
        console.error('Failed to mark notification as read:', error);
      });
    }

    // Navigate if link exists
    if (notification.link) {
      navigate(notification.link);
      onNavigate?.();
    }
  };

  const handleDismiss = async (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    try {
      await onDismiss(notification.id);
    } catch (error) {
      console.error('Failed to dismiss notification:', error);
    }
  };

  const getNotificationIcon = () => {
    switch (notification.type) {
      case 'rent_reminder':
        return 'fa-money-bill-wave text-yellow-500';
      case 'payment_received':
        return 'fa-check-circle text-green-500';
      case 'lease_expiring':
        return 'fa-calendar-times text-orange-500';
      case 'maintenance_update':
        return 'fa-wrench text-blue-500';
      case 'maintenance_request_new':
        return 'fa-tools text-red-500';
      case 'new_application':
        return 'fa-file-alt text-purple-500';
      case 'system_update':
        return 'fa-info-circle text-gray-500';
      default:
        return 'fa-bell text-gray-500';
    }
  };

  const getPriorityClass = () => {
    switch (notification.priority) {
      case 'urgent':
        return 'border-l-4 border-red-500';
      case 'high':
        return 'border-l-4 border-orange-500';
      default:
        return '';
    }
  };

  const formatTimeAgo = (dateString: string) => {
    const date = new Date(dateString);
    const now = new Date();
    const seconds = Math.floor((now.getTime() - date.getTime()) / 1000);

    if (seconds < 60) return 'just now';
    if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
    if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
    if (seconds < 604800) return `${Math.floor(seconds / 86400)}d ago`;
    return date.toLocaleDateString();
  };

  const content = (
    <div
      className={`
        group relative flex gap-3 p-4 hover:bg-gray-50 dark:hover:bg-gray-700 
        transition-colors duration-150 cursor-pointer
        ${!notification.is_read ? 'bg-blue-50 dark:bg-blue-900/20' : ''}
        ${getPriorityClass()}
      `}
      onClick={handleClick}
    >
      {/* Icon */}
      <div className="flex-shrink-0 mt-1">
        <i className={`fas ${getNotificationIcon()} text-lg`} />
      </div>

      {/* Content */}
      <div className="flex-1 min-w-0">
        <div className="flex items-start justify-between gap-2">
          <div className="flex-1">
            <p className="text-sm font-medium text-gray-900 dark:text-gray-100">
              {notification.title}
            </p>
            <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
              {notification.message}
            </p>
          </div>
          
          {/* Unread indicator */}
          {!notification.is_read && (
            <div className="flex-shrink-0">
              <div className="w-2 h-2 bg-blue-500 rounded-full" />
            </div>
          )}
        </div>

        {/* Meta info */}
        <div className="flex items-center gap-2 mt-2 text-xs text-gray-500 dark:text-gray-400">
          <span>{formatTimeAgo(notification.created_at)}</span>
          {notification.actor_name && (
            <>
              <span>•</span>
              <span>{notification.actor_name}</span>
            </>
          )}
        </div>
      </div>

      {/* Dismiss button */}
      <button
        onClick={handleDismiss}
        className="
          absolute top-2 right-2 opacity-0 group-hover:opacity-100
          transition-opacity duration-150 p-1 rounded hover:bg-gray-200 
          dark:hover:bg-gray-600
        "
        aria-label="Dismiss notification"
      >
        <i className="fas fa-times text-gray-400 dark:text-gray-500 text-xs" />
      </button>
    </div>
  );

  return content;
};

export default NotificationItem;

