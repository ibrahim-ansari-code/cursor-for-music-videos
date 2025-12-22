import React, { useState, useMemo, useContext } from 'react';
import { NotificationContext } from '@/contexts/notificationContextTypes';
import type { Notification } from '@/utils/api/notifications';
import { FiLoader, FiSettings } from 'react-icons/fi';
import NotificationSettingsModal from './NotificationSettingsModal';

// Notification type categories for filtering
type FilterType = 'all' | 'announcements' | 'maintenance' | 'payments';

// Map notification types to filter categories
const getFilterCategory = (type: string): FilterType => {
  const typeMap: Record<string, FilterType> = {
    // Announcements
    'announcement': 'announcements',
    'building_announcement': 'announcements',
    'system_update': 'announcements',
    // Maintenance
    'maintenance_update': 'maintenance',
    'maintenance_request_submitted': 'maintenance',
    'maintenance_scheduled': 'maintenance',
    // Payments
    'payment_received': 'payments',
    'payment_confirmation': 'payments',
    'rent_reminder': 'payments',
    'payment_failed': 'payments',
  };
  return typeMap[type.toLowerCase()] || 'announcements';
};

// Get icon and colors based on notification type
const getNotificationStyle = (type: string) => {
  const lowerType = type.toLowerCase();

  // Maintenance types - orange/yellow
  if (lowerType.includes('maintenance')) {
    return {
      bgColor: 'bg-orange-100',
      iconColor: 'text-orange-600',
      icon: (
        <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
        </svg>
      ),
    };
  }

  // Payment types - green
  if (lowerType.includes('payment') || lowerType.includes('rent')) {
    return {
      bgColor: 'bg-green-100',
      iconColor: 'text-green-600',
      icon: (
        <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
      ),
    };
  }

  // Announcement types - blue
  return {
    bgColor: 'bg-blue-100',
    iconColor: 'text-blue-600',
    icon: (
      <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5.882V19.24a1.76 1.76 0 01-3.417.592l-2.147-6.15M18 13a3 3 0 100-6M5.436 13.683A4.001 4.001 0 017 6h1.832c4.1 0 7.625-1.234 9.168-3v14c-1.543-1.766-5.067-3-9.168-3H7a3.988 3.988 0 01-1.564-.317z" />
      </svg>
    ),
  };
};

// Format date as "Dec 22, 2025"
const formatDate = (dateString: string): string => {
  const date = new Date(dateString);
  return date.toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  });
};

/**
 * NotificationListItem Component
 * Individual notification row for the full page view
 */
const NotificationListItem: React.FC<{
  notification: Notification;
  onMarkAsRead: (id: string) => Promise<void>;
}> = ({ notification, onMarkAsRead }) => {
  const style = getNotificationStyle(notification.type);

  const handleClick = async () => {
    if (!notification.is_read) {
      try {
        await onMarkAsRead(notification.id);
      } catch (error) {
        console.error('Failed to mark notification as read:', error);
      }
    }
  };

  return (
    <div
      onClick={handleClick}
      className={`flex items-start gap-4 py-4 px-2 border-b border-gray-100 last:border-b-0 cursor-pointer hover:bg-gray-50 transition-colors ${
        !notification.is_read ? 'bg-teal-50/30' : ''
      }`}
    >
      {/* Icon */}
      <div className={`shrink-0 w-10 h-10 rounded-full ${style.bgColor} ${style.iconColor} flex items-center justify-center`}>
        {style.icon}
      </div>

      {/* Content */}
      <div className="flex-1 min-w-0">
        <p className={`text-sm ${!notification.is_read ? 'font-semibold text-gray-900' : 'font-medium text-gray-800'}`}>
          {notification.title}
        </p>
        <p className="text-sm text-gray-600 mt-0.5">
          {notification.message}
        </p>
      </div>

      {/* Date */}
      <div className="shrink-0 text-sm text-gray-500">
        {formatDate(notification.created_at)}
      </div>
    </div>
  );
};

/**
 * NotificationsContent Component
 * Full notifications page with filtering and mark all as read
 */
const NotificationsContent: React.FC = () => {
  const notificationContext = useContext(NotificationContext);
  const [activeFilter, setActiveFilter] = useState<FilterType>('all');
  const [isMarkingAll, setIsMarkingAll] = useState(false);
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);

  // Filter notifications based on active filter - this must be called unconditionally
  const filteredNotifications = useMemo(() => {
    if (!notificationContext?.notifications) {
      return [];
    }
    if (activeFilter === 'all') {
      return notificationContext.notifications;
    }
    return notificationContext.notifications.filter((n) => getFilterCategory(n.type) === activeFilter);
  }, [notificationContext?.notifications, activeFilter]);

  if (!notificationContext) {
    return (
      <div className="bg-white rounded-lg shadow border border-gray-200 p-6">
        <p className="text-gray-500">Notification context not available</p>
      </div>
    );
  }

  const {
    notifications,
    isLoading,
    error,
    markNotificationAsRead,
    markAllNotificationsAsRead,
  } = notificationContext;

  // Handle mark all as read
  const handleMarkAllAsRead = async () => {
    setIsMarkingAll(true);
    try {
      await markAllNotificationsAsRead();
    } catch (error) {
      console.error('Failed to mark all as read:', error);
    } finally {
      setIsMarkingAll(false);
    }
  };

  // Check if there are any unread notifications
  const hasUnread = notifications.some((n) => !n.is_read);

  const filterTabs: { key: FilterType; label: string }[] = [
    { key: 'all', label: 'All' },
    { key: 'announcements', label: 'Announcements' },
    { key: 'maintenance', label: 'Maintenance' },
    { key: 'payments', label: 'Payments' },
  ];

  return (
    <div className="bg-white rounded-lg shadow border border-gray-200">
      <div className="p-6">
        {/* Page Header */}
        <div className="flex items-start justify-between mb-6">
          <div>
            <h1 className="text-2xl font-semibold text-gray-800">
              Notifications & Announcements
            </h1>
            <p className="text-gray-600">
              Stay updated with important information about your building and unit
            </p>
          </div>
          <button
            onClick={() => setIsSettingsOpen(true)}
            className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors cursor-pointer"
          >
            <FiSettings className="w-4 h-4" />
            Manage Preferences
          </button>
        </div>

        {/* Filter Tabs and Mark All Button */}
        <div className="flex items-center justify-between mb-6">
          {/* Filter Tabs */}
          <div className="flex gap-2">
            {filterTabs.map((tab) => (
              <button
                key={tab.key}
                onClick={() => setActiveFilter(tab.key)}
                className={`px-4 py-2 text-sm font-medium rounded-lg transition-colors cursor-pointer ${
                  activeFilter === tab.key
                    ? 'bg-gray-900 text-white'
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>

          {/* Mark All as Read Button */}
          <button
            onClick={handleMarkAllAsRead}
            disabled={isMarkingAll || !hasUnread}
            className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
          >
            {isMarkingAll && <FiLoader className="w-4 h-4 animate-spin" />}
            Mark All as Read
          </button>
        </div>

        {/* Notification List */}
        <div className="border border-gray-200 rounded-lg overflow-hidden">
          {isLoading ? (
            <div className="flex items-center justify-center py-12">
              <FiLoader className="w-6 h-6 animate-spin text-gray-400" />
              <span className="ml-2 text-gray-500">Loading notifications...</span>
            </div>
          ) : error ? (
            <div className="py-12 text-center">
              <p className="text-red-600">{error}</p>
            </div>
          ) : filteredNotifications.length === 0 ? (
            <div className="py-12 text-center">
              <p className="text-gray-500">
                {activeFilter === 'all'
                  ? 'No notifications yet'
                  : `No ${activeFilter} notifications`}
              </p>
            </div>
          ) : (
            <div className="divide-y divide-gray-100">
              {filteredNotifications.map((notification) => (
                <NotificationListItem
                  key={notification.id}
                  notification={notification}
                  onMarkAsRead={markNotificationAsRead}
                />
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Notification Settings Modal */}
      <NotificationSettingsModal
        isOpen={isSettingsOpen}
        onClose={() => setIsSettingsOpen(false)}
      />
    </div>
  );
};

export default NotificationsContent;
