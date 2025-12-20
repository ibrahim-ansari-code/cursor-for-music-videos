import { useContext } from 'react';
import { NotificationContext } from '../contexts/notificationContextTypes';

/**
 * Custom hook to access notification context
 * Must be used within NotificationProvider
 */
export const useNotifications = () => {
  const context = useContext(NotificationContext);
  if (!context) {
    throw new Error('useNotifications must be used within a NotificationProvider');
  }
  return context;
};

