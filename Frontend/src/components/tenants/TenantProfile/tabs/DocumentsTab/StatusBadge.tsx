/**
 * Status Badge Component
 * 
 * Displays document status with color-coded visual indicator.
 * Supports: Pending, Verified, Rejected, Expired
 */

import React from 'react';
import { DocumentStatus, STATUS_LABELS } from '../../../../../types/tenantDocument';

interface StatusBadgeProps {
  status: DocumentStatus;
  className?: string;
}

const StatusBadge: React.FC<StatusBadgeProps> = ({ status, className = '' }) => {
  // Determine color classes based on status
  const getStatusClasses = (): string => {
    switch (status) {
      case DocumentStatus.VERIFIED:
        return 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400';
      case DocumentStatus.PENDING:
        return 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400';
      case DocumentStatus.REJECTED:
        return 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400';
      case DocumentStatus.EXPIRED:
        return 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-400';
      default:
        return 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-400';
    }
  };

  return (
    <span
      className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getStatusClasses()} ${className}`}
    >
      {STATUS_LABELS[status]}
    </span>
  );
};

export default StatusBadge;


