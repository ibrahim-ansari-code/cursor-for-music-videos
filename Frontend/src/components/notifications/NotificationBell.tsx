import React, { useState, useRef } from 'react';
import { useNotifications } from '../../contexts/NotificationContext';
import NotificationDropdown from './NotificationDropdown';

const NotificationBell: React.FC = () => {
  const [isOpen, setIsOpen] = useState(false);
  const buttonRef = useRef<HTMLButtonElement | null>(null);
  const { unreadCount } = useNotifications();

  const toggleDropdown = () => {
    setIsOpen((prev) => !prev);
  };

  return (
    <div className="relative">
      <button
        ref={buttonRef}
        onClick={toggleDropdown}
        className="
          relative p-2 text-gray-600 dark:text-gray-300 
          hover:text-gray-900 dark:hover:text-white
          hover:bg-gray-100 dark:hover:bg-gray-700
          rounded-full transition-colors duration-150
        "
        aria-label="Notifications"
        aria-expanded={isOpen}
      >
        <i className="fas fa-bell text-xl" />
        
        {/* Unread badge */}
        {unreadCount > 0 && (
          <span
            className="
              absolute top-0 right-0 inline-flex items-center justify-center
              px-1.5 py-0.5 text-xs font-bold leading-none text-white
              transform translate-x-1/4 -translate-y-1/4
              bg-red-500 rounded-full min-w-[20px]
            "
          >
            {unreadCount > 99 ? '99+' : unreadCount}
          </span>
        )}
      </button>

      <NotificationDropdown
        isOpen={isOpen}
        onClose={() => setIsOpen(false)}
        anchorRef={buttonRef}
      />
    </div>
  );
};

export default NotificationBell;

