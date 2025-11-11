import React from 'react';
import * as Select from '@radix-ui/react-select';
import { ChevronDown, CheckCircle } from 'lucide-react';
import * as Sentry from '@sentry/react';
import type { LeaseFiltersProps } from '../../types/lease';

interface LeaseFiltersWithBulkDeleteProps extends LeaseFiltersProps {
  onBulkDelete?: () => void;
  selectedCount?: number;
}

const STATUS_OPTIONS = [
  { value: 'all', label: 'All Statuses' },
  { value: 'DRAFT', label: 'Draft' },
  { value: 'PENDING', label: 'Pending' },
  { value: 'ACTIVE', label: 'Active' },
  { value: 'EXPIRED', label: 'Expired' },
  { value: 'TERMINATED', label: 'Terminated' },
  { value: 'RENEWED', label: 'Renewed' },
];

const LeaseFilters: React.FC<LeaseFiltersWithBulkDeleteProps> = ({
  statusFilter,
  onStatusFilterChange,
  onNewLease,
  onBulkDelete,
  selectedCount = 0,
}) => {
  // Get display label for selected status
  const selectedStatusLabel = STATUS_OPTIONS.find(s => s.value === statusFilter)?.label || 'All Statuses';

  return (
    <div className="flex flex-col sm:flex-row sm:items-center sm:justify-end mb-6">
      <div className="mt-3 sm:mt-0 flex flex-col sm:flex-row space-y-2 sm:space-y-0 sm:space-x-3">
        {/* Status Filter Dropdown */}
        <Select.Root 
          value={statusFilter}
          onValueChange={(value) => {
            Sentry.logger.debug('Status filter dropdown changed', {
              newValue: value,
              previousValue: statusFilter,
            });
            onStatusFilterChange(value);
          }}
        >
          <Select.Trigger 
            className="w-48 px-3 py-1.5 pr-9 border border-gray-300 dark:border-gray-600 rounded-md focus:outline-none focus:ring-1 focus:ring-blue-500 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 flex items-center text-sm hover:border-gray-400 dark:hover:border-gray-500 transition-colors relative"
          >
            <Select.Value asChild>
              <span className="truncate block flex-1 text-left">{selectedStatusLabel}</span>
            </Select.Value>
            <Select.Icon className="absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none">
              <ChevronDown className="h-4 w-4 text-gray-500 dark:text-gray-400" />
            </Select.Icon>
          </Select.Trigger>
          <Select.Portal>
            <Select.Content 
              className="overflow-hidden bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-600 shadow-lg z-[100] max-h-[300px]"
              position="popper"
              side="bottom"
              align="start"
              sideOffset={4}
            >
              <Select.Viewport className="p-1">
                {STATUS_OPTIONS.map((status) => (
                  <Select.Item
                    key={status.value}
                    value={status.value}
                    className="relative flex items-center px-8 py-2 text-sm text-gray-900 dark:text-gray-100 rounded cursor-pointer hover:bg-blue-50 dark:hover:bg-blue-900/20 focus:bg-blue-50 dark:focus:bg-blue-900/20 outline-none select-none data-[state=checked]:bg-blue-50 dark:data-[state=checked]:bg-blue-900/30"
                  >
                    <Select.ItemText>{status.label}</Select.ItemText>
                    <Select.ItemIndicator className="absolute left-2 inline-flex items-center">
                      <CheckCircle className="h-4 w-4 text-blue-600 dark:text-blue-400" />
                    </Select.ItemIndicator>
                  </Select.Item>
                ))}
              </Select.Viewport>
            </Select.Content>
          </Select.Portal>
        </Select.Root>

        {/* Delete Selected Button */}
        {onBulkDelete && selectedCount > 0 && (
          <button
            onClick={() => {
              Sentry.logger.debug('Delete Selected button clicked', {
                selectedCount,
              });
              onBulkDelete();
            }}
            className="inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-red-600 hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <i className="fas fa-trash mr-2"></i>
            Delete Selected ({selectedCount})
          </button>
        )}

        {/* New Lease Button */}
        <button
          onClick={() => {
            Sentry.logger.debug('New Lease button clicked from filters');
            onNewLease();
          }}
          className="inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 dark:bg-blue-700 dark:hover:bg-blue-600 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 dark:focus:ring-offset-gray-800 transition-colors"
        >
          <i className="fas fa-plus mr-2"></i>
          New Lease
        </button>
      </div>
    </div>
  );
};

export default LeaseFilters;

