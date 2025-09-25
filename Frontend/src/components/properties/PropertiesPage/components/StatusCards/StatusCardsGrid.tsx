import React from 'react';
import { StatusCard } from './StatusCard';
import { StatusCounts } from '../../utils/statusCounts';

interface StatusCardsGridProps {
  statusCounts: StatusCounts;
  statusFilter: string | null;
  onStatusCardClick: (status: string) => void;
  onClearFilters: () => void;
  isLoading: boolean;
  hasProperties: boolean;
}

export const StatusCardsGrid: React.FC<StatusCardsGridProps> = ({
  statusCounts,
  statusFilter,
  onStatusCardClick,
  onClearFilters,
  isLoading,
  hasProperties,
}) => (
  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
    <StatusCard
      title="Active"
      count={statusCounts.ACTIVE}
      iconBgColor={statusFilter === 'ACTIVE' ? 'bg-green-100 dark:bg-green-900' : 'bg-green-50 dark:bg-green-900/50'}
      textColor="text-green-600 dark:text-green-400"
      onClick={() => onStatusCardClick('ACTIVE')}
      isLoading={isLoading && !hasProperties}
      icon={
        <svg
          className="h-6 w-6 text-green-600 dark:text-green-400"
          xmlns="http://www.w3.org/2000/svg"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
          />
        </svg>
      }
    />
    <StatusCard
      title="Inactive"
      count={statusCounts.INACTIVE}
      iconBgColor={
        statusFilter === 'INACTIVE' ? 'bg-orange-100 dark:bg-orange-900' : 'bg-orange-50 dark:bg-orange-900/50'
      }
      textColor="text-orange-600 dark:text-orange-400"
      onClick={() => onStatusCardClick('INACTIVE')}
      isLoading={isLoading && !hasProperties}
      icon={
        <svg
          className="h-6 w-6 text-orange-600 dark:text-orange-400"
          xmlns="http://www.w3.org/2000/svg"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
          />
        </svg>
      }
    />
    <StatusCard
      title="Vacant"
      count={statusCounts.VACANT}
      iconBgColor={statusFilter === 'VACANT' ? 'bg-yellow-100 dark:bg-yellow-900' : 'bg-yellow-50 dark:bg-yellow-900/50'}
      textColor="text-yellow-600 dark:text-yellow-400"
      onClick={() => onStatusCardClick('VACANT')}
      isLoading={isLoading && !hasProperties}
      icon={
        <svg
          className="h-6 w-6 text-yellow-600 dark:text-yellow-400"
          xmlns="http://www.w3.org/2000/svg"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
          />
        </svg>
      }
    />
    <StatusCard
      title="Total"
      count={statusCounts.total}
      iconBgColor={statusFilter === null ? 'bg-indigo-100 dark:bg-indigo-900' : 'bg-indigo-50 dark:bg-indigo-900/50'}
      textColor="text-indigo-600 dark:text-indigo-400"
      onClick={onClearFilters}
      isLoading={isLoading && !hasProperties}
      icon={
        <svg
          className="h-6 w-6 text-indigo-600 dark:text-indigo-400"
          xmlns="http://www.w3.org/2000/svg"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z"
          />
        </svg>
      }
    />
  </div>
);