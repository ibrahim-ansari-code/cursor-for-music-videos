import React, { useState } from 'react';
import { useOutletContext } from 'react-router-dom';
import { EnrichedTenant, MaintenanceStatus, MaintenancePriority } from '../../../../types/tenant';
import { formatDate } from '../../../../utils/tenantUtils';

interface OutletContext {
  tenant: EnrichedTenant;
  refetch: () => void;
  openMaintenanceModal: (initialData: any) => void;
}

const MaintenanceTab: React.FC = () => {
  const context = useOutletContext<OutletContext>();
  const [statusFilter, setStatusFilter] = useState<MaintenanceStatus | 'ALL'>('ALL');

  // Guard: Handle undefined context gracefully (occurs during refetch or initial load)
  if (!context || !context.tenant) {
    return (
      <div className="flex items-center justify-center py-16">
        <div className="flex flex-col items-center gap-4">
          <div className="w-12 h-12 border-4 border-blue-200 dark:border-blue-800 border-t-blue-600 dark:border-t-blue-400 rounded-full animate-spin" />
          <p className="text-sm text-gray-500 dark:text-gray-400">Loading maintenance requests...</p>
        </div>
      </div>
    );
  }

  const { tenant, openMaintenanceModal } = context;

  // Handle creating new maintenance request
  const handleNewRequest = () => {
    // Get active lease to extract property and unit info
    const activeLease = tenant.leases?.find(lease => lease.status === 'ACTIVE');
    
    // Ensure all IDs are strings (modal expects strings for select inputs)
    const propertyId = activeLease?.property_id || tenant.current_property_id;
    const unitId = activeLease?.unit_id || tenant.unit?.id;
    
    const initialData = {
      tenant_id: tenant.id,
      property_id: propertyId ? String(propertyId) : '',
      unit_id: unitId ? String(unitId) : '',
      priority: MaintenancePriority.MEDIUM,  // Uses enum for type safety
      status: MaintenanceStatus.PENDING,     // Uses enum for type safety
    };

    openMaintenanceModal(initialData);
  };

  const maintenanceRequests = tenant.maintenance_requests || [];

  const filteredRequests = statusFilter === 'ALL'
    ? maintenanceRequests
    : maintenanceRequests.filter(req => req.status === statusFilter);

  const getStatusBadge = (status: MaintenanceStatus) => {
    const baseClasses = 'inline-flex items-center px-2 py-1 rounded-full text-xs font-semibold';

    switch (status) {
      case MaintenanceStatus.PENDING:
        return `${baseClasses} bg-yellow-100 dark:bg-yellow-900/30 text-yellow-800 dark:text-yellow-200`;
      case MaintenanceStatus.IN_PROGRESS:
        return `${baseClasses} bg-blue-100 dark:bg-blue-900/30 text-blue-800 dark:text-blue-200`;
      case MaintenanceStatus.COMPLETED:
        return `${baseClasses} bg-green-100 dark:bg-green-900/30 text-green-800 dark:text-green-200`;
      case MaintenanceStatus.CANCELLED:
        return `${baseClasses} bg-gray-100 dark:bg-gray-900/30 text-gray-800 dark:text-gray-200`;
      default:
        return `${baseClasses} bg-gray-100 dark:bg-gray-900/30 text-gray-800 dark:text-gray-200`;
    }
  };

  const getPriorityBadge = (priority: MaintenancePriority) => {
    switch (priority) {
      case MaintenancePriority.URGENT:
        return (
          <span className="inline-flex items-center gap-1 text-xs font-medium text-red-600 dark:text-red-400">
            <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
            </svg>
            Urgent
          </span>
        );
      case MaintenancePriority.HIGH:
        return <span className="text-xs font-medium text-orange-600 dark:text-orange-400">High</span>;
      case MaintenancePriority.MEDIUM:
        return <span className="text-xs font-medium text-yellow-600 dark:text-yellow-400">Medium</span>;
      case MaintenancePriority.LOW:
        return <span className="text-xs font-medium text-gray-600 dark:text-gray-400">Low</span>;
      default:
        return <span className="text-xs font-medium text-gray-600 dark:text-gray-400">{priority}</span>;
    }
  };

  const formatStatusDisplay = (status: MaintenanceStatus): string => {
    return status.replace('_', ' ');
  };

  return (
    <div className="space-y-6">
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700">
        <div className="p-6 border-b border-gray-200 dark:border-gray-700">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">Maintenance Requests</h3>
              <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
                {filteredRequests.length} request{filteredRequests.length !== 1 ? 's' : ''}
              </p>
            </div>
            <div className="flex items-center gap-3">
              {maintenanceRequests.length > 0 && (
                <select
                  value={statusFilter}
                  onChange={(e) => setStatusFilter(e.target.value as MaintenanceStatus | 'ALL')}
                  className="px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-blue-500/30 focus:border-blue-500 dark:focus:border-blue-400"
                >
                  <option value="ALL">All Status</option>
                  <option value="PENDING">Pending</option>
                  <option value="IN_PROGRESS">In Progress</option>
                  <option value="COMPLETED">Completed</option>
                  <option value="CANCELLED">Cancelled</option>
                </select>
              )}
              <button
                onClick={handleNewRequest}
                className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
              >
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                </svg>
                New Request
              </button>
            </div>
          </div>
        </div>

        {filteredRequests.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
              <thead className="bg-gray-50 dark:bg-gray-900/50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-semibold text-gray-700 dark:text-gray-300 uppercase">Issue</th>
                  <th className="px-6 py-3 text-left text-xs font-semibold text-gray-700 dark:text-gray-300 uppercase">Property/Unit</th>
                  <th className="px-6 py-3 text-center text-xs font-semibold text-gray-700 dark:text-gray-300 uppercase">Priority</th>
                  <th className="px-6 py-3 text-center text-xs font-semibold text-gray-700 dark:text-gray-300 uppercase">Status</th>
                  <th className="px-6 py-3 text-left text-xs font-semibold text-gray-700 dark:text-gray-300 uppercase">Date</th>
                </tr>
              </thead>
              <tbody className="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
                {filteredRequests.map((request) => (
                  <tr key={request.id} className="hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors">
                    <td className="px-6 py-4">
                      <div className="text-sm font-medium text-gray-900 dark:text-gray-100">
                        {request.issue_title}
                      </div>
                      {request.description && (
                        <div className="text-xs text-gray-500 dark:text-gray-400 mt-0.5 line-clamp-1">
                          {request.description}
                        </div>
                      )}
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-600 dark:text-gray-400">
                      <div className="flex flex-col">
                        <span>{request.property?.name || 'N/A'}</span>
                        {request.unit && (
                          <span className="text-xs text-gray-500 dark:text-gray-500">
                            Unit: {request.unit.name}
                          </span>
                        )}
                      </div>
                    </td>
                    <td className="px-6 py-4 text-center">
                      {getPriorityBadge(request.priority)}
                    </td>
                    <td className="px-6 py-4 text-center">
                      <span className={getStatusBadge(request.status)}>
                        {formatStatusDisplay(request.status)}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-600 dark:text-gray-400">
                      <div className="flex flex-col">
                        <span>{formatDate(request.request_date)}</span>
                        {request.completed_date && (
                          <span className="text-xs text-green-600 dark:text-green-400">
                            Completed: {formatDate(request.completed_date)}
                          </span>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="p-12 text-center">
            <div className="mx-auto w-16 h-16 bg-gray-100 dark:bg-gray-700 rounded-full flex items-center justify-center mb-4">
              <svg className="w-8 h-8 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
              </svg>
            </div>
            <p className="text-gray-600 dark:text-gray-400 mb-2">
              {statusFilter === 'ALL' ? 'No maintenance requests' : `No ${statusFilter.toLowerCase().replace('_', ' ')} requests`}
            </p>
            <p className="text-sm text-gray-500 dark:text-gray-500">
              Maintenance requests from this tenant will appear here
            </p>
          </div>
        )}
      </div>
    </div>
  );
};

export default MaintenanceTab;
