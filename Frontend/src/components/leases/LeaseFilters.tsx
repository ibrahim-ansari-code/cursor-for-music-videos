import React from 'react';
import * as Sentry from '@sentry/react';
import type { LeaseFiltersProps } from '../../types/lease';

const LeaseFilters: React.FC<LeaseFiltersProps> = ({
  statusFilter,
  onStatusFilterChange,
  onNewLease,
}) => {
  return (
    <div className="flex flex-col sm:flex-row sm:items-center sm:justify-end mb-6">
      <div className="mt-3 sm:mt-0 flex flex-col sm:flex-row space-y-2 sm:space-y-0 sm:space-x-3">
        <div className="relative">
          <select
            className="dark-input block w-full pr-10 py-2 text-base focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
            value={statusFilter}
            onChange={(e) => {
              Sentry.logger.debug('Status filter dropdown changed', {
                newValue: e.target.value,
                previousValue: statusFilter,
              });
              onStatusFilterChange(e.target.value);
            }}
          >
            <option value="all">All Statuses</option>
            <option value="DRAFT">Draft</option>
            <option value="PENDING">Pending</option>
            <option value="ACTIVE">Active</option>
            <option value="EXPIRED">Expired</option>
            <option value="TERMINATED">Terminated</option>
            <option value="RENEWED">Renewed</option>
          </select>
        </div>

        <button
          onClick={() => {
            Sentry.logger.debug('New Lease button clicked from filters');
            onNewLease();
          }}
          className="inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
        >
          <i className="fas fa-plus mr-2"></i>
          New Lease
        </button>
      </div>
    </div>
  );
};

export default LeaseFilters;

