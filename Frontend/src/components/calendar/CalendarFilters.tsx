/**
 * CalendarFilters Component
 * 
 * Filter sidebar for calendar view with:
 * - Date range selection
 * - Property/Unit/Tenant filters
 * - Event type filters
 * - Status filters
 */

import React from 'react';
import { CalendarEventType, CalendarEventStatus, CalendarFilters as ICalendarFilters } from '../../utils/api/calendar';
import { XIcon } from 'lucide-react';

interface CalendarFiltersProps {
  filters: ICalendarFilters;
  onFilterChange: (filters: Partial<ICalendarFilters>) => void;
  onClose?: () => void;
}

export const CalendarFilters: React.FC<CalendarFiltersProps> = ({
  filters,
  onFilterChange,
  onClose,
}) => {
  const eventTypes = [
    { value: CalendarEventType.INVOICE_DUE, label: 'Invoice Due' },
    { value: CalendarEventType.LEASE_START, label: 'Lease Start' },
    { value: CalendarEventType.LEASE_EXPIRING, label: 'Lease Expiring' },
    { value: CalendarEventType.MAINTENANCE_SCHEDULED, label: 'Maintenance' },
    { value: CalendarEventType.INSURANCE_EXPIRY, label: 'Insurance Expiry' },
    { value: CalendarEventType.MORTGAGE_RENEWAL, label: 'Mortgage Renewal' },
    { value: CalendarEventType.CUSTOM_REMINDER, label: 'Custom Reminder' },
  ];

  const statuses = [
    { value: CalendarEventStatus.UPCOMING, label: 'Upcoming', color: 'bg-blue-100 text-blue-800' },
    { value: CalendarEventStatus.DUE, label: 'Due Today', color: 'bg-amber-100 text-amber-800' },
    { value: CalendarEventStatus.OVERDUE, label: 'Overdue', color: 'bg-red-100 text-red-800' },
    { value: CalendarEventStatus.COMPLETED, label: 'Completed', color: 'bg-green-100 text-green-800' },
  ];

  const clearFilters = () => {
    onFilterChange({
      property_id: undefined,
      unit_id: undefined,
      tenant_id: undefined,
      event_type: undefined,
      status: undefined,
    });
  };

  const hasActiveFilters = filters.property_id || filters.unit_id || filters.tenant_id || filters.event_type || filters.status;

  return (
    <div className="h-full overflow-y-auto p-4">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-base font-semibold text-gray-900">Filters</h2>
        <div className="flex items-center space-x-2">
          {hasActiveFilters && (
            <button
              onClick={clearFilters}
              className="text-sm text-blue-600 hover:text-blue-700"
            >
              Clear All
            </button>
          )}
          {onClose && (
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-gray-600 lg:hidden"
            >
              <XIcon className="w-5 h-5" />
            </button>
          )}
        </div>
      </div>

      {/* Date Range */}
      <div className="mb-4">
        <label className="block text-xs font-medium text-gray-700 mb-1.5">
          Date Range
        </label>
        <div className="space-y-1.5">
          <input
            type="date"
            value={filters.from_date}
            onChange={(e) => onFilterChange({ from_date: e.target.value })}
            className="w-full px-2 py-1.5 text-sm border border-gray-300 rounded-md focus:ring-1 focus:ring-blue-500 focus:border-transparent"
          />
          <span className="block text-xs text-gray-500 text-center">to</span>
          <input
            type="date"
            value={filters.to_date}
            onChange={(e) => onFilterChange({ to_date: e.target.value })}
            className="w-full px-2 py-1.5 text-sm border border-gray-300 rounded-md focus:ring-1 focus:ring-blue-500 focus:border-transparent"
          />
        </div>
      </div>

      {/* Event Type */}
      <div className="mb-4">
        <label className="block text-xs font-medium text-gray-700 mb-2">
          Event Type
        </label>
        <div className="space-y-1.5">
          {eventTypes.map((type) => (
            <label key={type.value} className="flex items-center space-x-2 cursor-pointer">
              <input
                type="radio"
                name="event_type"
                checked={filters.event_type === type.value}
                onChange={() => onFilterChange({ event_type: type.value })}
                className="w-3.5 h-3.5 text-blue-600 focus:ring-blue-500"
              />
              <span className="text-xs text-gray-700">{type.label}</span>
            </label>
          ))}
          <label className="flex items-center space-x-2 cursor-pointer">
            <input
              type="radio"
              name="event_type"
              checked={!filters.event_type}
              onChange={() => onFilterChange({ event_type: undefined })}
              className="w-3.5 h-3.5 text-blue-600 focus:ring-blue-500"
            />
            <span className="text-xs text-gray-700">All Types</span>
          </label>
        </div>
      </div>

      {/* Status */}
      <div className="mb-4">
        <label className="block text-xs font-medium text-gray-700 mb-2">
          Status
        </label>
        <div className="space-y-1.5">
          {statuses.map((status) => (
            <label key={status.value} className="flex items-center space-x-2 cursor-pointer">
              <input
                type="radio"
                name="status"
                checked={filters.status === status.value}
                onChange={() => onFilterChange({ status: status.value })}
                className="w-3.5 h-3.5 text-blue-600 focus:ring-blue-500"
              />
              <span className={`px-1.5 py-0.5 text-xs font-semibold rounded-full ${status.color}`}>
                {status.label}
              </span>
            </label>
          ))}
          <label className="flex items-center space-x-2 cursor-pointer">
            <input
              type="radio"
              name="status"
              checked={!filters.status}
              onChange={() => onFilterChange({ status: undefined })}
              className="w-3.5 h-3.5 text-blue-600 focus:ring-blue-500"
            />
            <span className="text-xs text-gray-700">All Statuses</span>
          </label>
        </div>
      </div>
    </div>
  );
};

