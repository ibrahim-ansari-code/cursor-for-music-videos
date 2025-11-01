import React, { useRef, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useNotifications } from '../../contexts/NotificationContext';
import NotificationItem from './NotificationItem';

interface NotificationDropdownProps {
  isOpen: boolean;
  onClose: () => void;
  anchorRef: React.RefObject<HTMLButtonElement | null>;
}

const NotificationDropdown: React.FC<NotificationDropdownProps> = ({
  isOpen,
  onClose,
  anchorRef,
}) => {
  const navigate = useNavigate();
  const dropdownRef = useRef<HTMLDivElement>(null);
  const {
    notifications,
    isLoading,
    error,
    markNotificationAsRead,
    markAllNotificationsAsRead,
    dismissNotification,
  } = useNotifications();

  // Close dropdown when clicking outside
  useEffect(() => {
    if (!isOpen) return;

    const handleClickOutside = (event: MouseEvent) => {
      if (
        dropdownRef.current &&
        !dropdownRef.current.contains(event.target as Node) &&
        anchorRef.current &&
        !anchorRef.current.contains(event.target as Node)
      ) {
        onClose();
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [isOpen, onClose, anchorRef]);

  if (!isOpen) return null;

  return (
    <div
      ref={dropdownRef}
      className="
        absolute right-0 mt-2 w-96 max-h-[600px] bg-white dark:bg-gray-800 
        rounded-lg shadow-lg border border-gray-200 dark:border-gray-700
        overflow-hidden z-50 transition-colors duration-300
      "
      style={{ top: '100%' }}
    >
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-gray-200 dark:border-gray-700">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
          Notifications
        </h3>
        {notifications.length > 0 && (
          <button
            onClick={() => markAllNotificationsAsRead()}
            className="text-sm text-blue-600 dark:text-blue-400 hover:underline"
          >
            Mark all as read
          </button>
        )}
      </div>

      {/* Content */}
      <div className="max-h-[500px] overflow-y-auto">
        {isLoading && (
          <div className="flex items-center justify-center py-12">
            <div className="w-8 h-8 border-4 border-blue-200 dark:border-blue-800 border-t-blue-600 dark:border-t-blue-400 rounded-full animate-spin" />
          </div>
        )}

        {error && (
          <div className="p-4 text-center text-sm text-red-600 dark:text-red-400">
            {error}
          </div>
        )}

        {!isLoading && !error && notifications.length === 0 && (
          <div className="flex flex-col items-center justify-center py-12 px-4">
            <i className="fas fa-bell-slash text-4xl text-gray-400 dark:text-gray-500 mb-3" />
            <p className="text-sm text-gray-600 dark:text-gray-400">
              No notifications yet
            </p>
            <p className="text-xs text-gray-500 dark:text-gray-500 mt-1">
              We'll notify you when something new comes up
            </p>
          </div>
        )}

        {!isLoading && !error && notifications.length > 0 && (
          <div className="divide-y divide-gray-200 dark:divide-gray-700">
            {notifications.map((notification) => (
              <NotificationItem
                key={notification.id}
                notification={notification}
                onMarkAsRead={markNotificationAsRead}
                onDismiss={dismissNotification}
              />
            ))}
          </div>
        )}
      </div>

      {/* Footer */}
      {notifications.length > 0 && (
        <div className="border-t border-gray-200 dark:border-gray-700 px-4 py-3">
          <button
            onClick={() => {
              navigate('/settings?tab=notifications');
              onClose();
            }}
            className="text-sm text-blue-600 dark:text-blue-400 hover:underline block text-center w-full"
          >
            View Notification Settings
          </button>
        </div>
      )}
    </div>
  );
};

export default NotificationDropdown;

