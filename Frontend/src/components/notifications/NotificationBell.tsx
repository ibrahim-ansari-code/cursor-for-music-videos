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
              absolute top-0 left-0 inline-flex items-center justify-center
              px-1 py-1 text-[10px] font-bold leading-none text-white
              transform
              bg-red-500 rounded-full min-w-[16px]
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

