import React from 'react';
import LeaseActions from './LeaseActions';
import type { LeaseRowProps } from '../../types/lease';
import { getTenantDisplayName, getTenantInitials } from '../../utils/tenantUtils';

interface LeaseRowWithSelectionProps extends LeaseRowProps {
  isSelected: boolean;
  onSelect: (selected: boolean) => void;
}

const LeaseRow: React.FC<LeaseRowWithSelectionProps> = ({
  lease,
  actionHandlers,
  isSelected,
  onSelect,
}) => {
  // Get tenant name with fallback
  const tenantName = getTenantDisplayName(lease.tenant, 'No tenant assigned');
  
  // Get tenant initials
  const tenantInitials = getTenantInitials(lease.tenant);

  // Helper: Get status badge class
  const getStatusClass = () => {
    const status = lease.status.toLowerCase();
    if (status === "active") return "status-pill-active";
    if (status === "pending") return "status-pill-pending";
    if (status === "expired" || status === "terminated")
      return "status-pill-overdue";
    return "status-pill-inactive";
  };

  // Helper: Calculate lease duration in months
  const calculateDurationMonths = () => {
    return Math.round(
      (new Date(lease.end_date).getTime() -
        new Date(lease.start_date).getTime()) /
        (1000 * 60 * 60 * 24 * 30)
    );
  };

  return (
    <tr className="hover:bg-blue-50 dark:hover:bg-blue-900/20 transition-colors duration-150">
      {/* Checkbox */}
      <td className="px-6 py-4 whitespace-nowrap text-left w-12">
        <input
          type="checkbox"
          checked={isSelected}
          onChange={(e) => onSelect(e.target.checked)}
          className="rounded border-gray-300 text-blue-600 focus:ring-blue-500 dark:border-gray-600 dark:bg-gray-700"
          onClick={(e) => e.stopPropagation()}
        />
      </td>
      {/* Tenant */}
      <td className="px-6 py-4 whitespace-nowrap text-left">
        <div className="flex items-center">
          <div className="flex-shrink-0 h-10 w-10 rounded-full dark-input flex items-center justify-center text-gray-600 dark:text-gray-300">
            {tenantInitials}
          </div>
          <div className="ml-4">
            <div className="text-sm font-medium text-gray-900 dark:text-gray-100">
              {tenantName}
            </div>
            <div className="text-sm text-gray-500 dark:text-gray-400">
              {lease.tenant?.email ? (
                <a href={`mailto:${lease.tenant.email}`} className="email-link">
                  {lease.tenant.email}
                </a>
              ) : (
                "No email"
              )}
            </div>
          </div>
        </div>
      </td>

      {/* Property */}
      <td className="px-6 py-4 whitespace-nowrap text-left">
        <div className="text-sm text-gray-900 dark:text-gray-100">
          {lease.property?.name || `Property #${lease.property_id}`}
        </div>
        <div className="text-sm text-gray-500 dark:text-gray-400">
          Unit: {lease.unit?.name || 'N/A'}
        </div>
      </td>

      {/* Dates */}
      <td className="px-6 py-4 whitespace-nowrap text-left">
        <div className="text-sm text-gray-900 dark:text-gray-100">
          {new Date(lease.start_date).toLocaleDateString()} -{" "}
          {new Date(lease.end_date).toLocaleDateString()}
        </div>
        <div className="text-sm text-gray-500 dark:text-gray-400">
          {calculateDurationMonths()} months
        </div>
      </td>

      {/* Rent */}
      <td className="px-6 py-4 whitespace-nowrap text-left">
        <div className="text-sm text-gray-900 dark:text-gray-100">
          ${Number(lease.monthly_rent).toFixed(2)}/month
        </div>
        <div className="text-sm text-gray-500 dark:text-gray-400">
          Due: Day {lease.rent_due_day}
        </div>
      </td>

      {/* Status */}
      <td className="px-6 py-4 whitespace-nowrap">
        <div className="flex items-center justify-center">
          <span className={`status-pill ${getStatusClass()}`}>
            {lease.status.charAt(0).toUpperCase() +
              lease.status.slice(1).toLowerCase()}
          </span>
        </div>
      </td>

      {/* Actions */}
      <td className="px-6 py-4 whitespace-nowrap text-center text-sm font-medium">
        <LeaseActions
          lease={lease}
          onEdit={actionHandlers.onEdit}
          onDelete={actionHandlers.onDelete}
          onStatusChange={actionHandlers.onStatusChange}
          onDocumentUpload={actionHandlers.onDocumentUpload}
          onDocumentPreview={actionHandlers.onDocumentPreview}
        />
      </td>
    </tr>
  );
};

export default LeaseRow;
