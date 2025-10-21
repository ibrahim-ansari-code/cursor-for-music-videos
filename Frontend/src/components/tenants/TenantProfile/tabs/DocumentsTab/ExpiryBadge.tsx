/**
 * Expiry Badge Component
 * 
 * Displays document expiry information with color-coded urgency indicator.
 * Shows different states: Expired, Expiring Soon, Normal, No Expiry
 */

import React from 'react';
import { TenantDocument, formatExpiryDisplay, getExpiryUrgency } from '../../../../../types/tenantDocument';

interface ExpiryBadgeProps {
  document: TenantDocument;
  className?: string;
}

const ExpiryBadge: React.FC<ExpiryBadgeProps> = ({ document, className = '' }) => {
  // No expiry date = no badge
  if (!document.expiry_date) {
    return (
      <span className={`text-xs text-gray-500 dark:text-gray-400 ${className}`}>
        No expiry
      </span>
    );
  }

  const urgency = getExpiryUrgency(document);
  const displayText = formatExpiryDisplay(document);

  // Determine color classes based on urgency
  const getUrgencyClasses = (): string => {
    switch (urgency) {
      case 'expired':
        return 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400 border-red-200 dark:border-red-800';
      case 'critical':
        return 'bg-orange-100 text-orange-800 dark:bg-orange-900/30 dark:text-orange-400 border-orange-200 dark:border-orange-800';
      case 'warning':
        return 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400 border-yellow-200 dark:border-yellow-800';
      case 'normal':
        return 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400 border-green-200 dark:border-green-800';
      default:
        return 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-400 border-gray-200 dark:border-gray-600';
    }
  };

  // Show icon for expired/critical states
  const showWarningIcon = urgency === 'expired' || urgency === 'critical';

  return (
    <span
      className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium border ${getUrgencyClasses()} ${className}`}
      title={document.expiry_date ? `Expiry date: ${document.expiry_date}` : undefined}
    >
      {showWarningIcon && (
        <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
        </svg>
      )}
      {displayText}
    </span>
  );
};

export default ExpiryBadge;


