import { Calendar, Clock, AlertCircle, CheckCircle, XCircle, Wrench } from 'lucide-react';
import type { MaintenanceRequest, MaintenanceStatus } from '@/utils/api/maintenance/types';

interface MaintenanceTableProps {
  requests: MaintenanceRequest[];
  onViewDetails: (request: MaintenanceRequest) => void;
  onCreateRequest: () => void;
}

/**
 * MaintenanceTable Component
 * Displays maintenance requests table or helpful empty state
 */
const MaintenanceTable = ({ 
  requests, 
  onViewDetails,
  onCreateRequest,
}: MaintenanceTableProps) => {
  const getStatusBadge = (status: MaintenanceStatus) => {
    const statusConfig = {
      new: {
        label: "Submitted",
        icon: <Clock className="w-3.5 h-3.5" />,
        className: "bg-blue-100 text-blue-800",
      },
      pending: {
        label: "Awaiting response",
        icon: <Clock className="w-3.5 h-3.5" />,
        className: "bg-yellow-100 text-yellow-800",
      },
      in_progress: {
        label: "In progress",
        icon: <AlertCircle className="w-3.5 h-3.5" />,
        className: "bg-blue-100 text-blue-800",
      },
      scheduled: {
        label: "Scheduled",
        icon: <Calendar className="w-3.5 h-3.5" />,
        className: "bg-purple-100 text-purple-800",
      },
      completed: {
        label: "Completed",
        icon: <CheckCircle className="w-3.5 h-3.5" />,
        className: "bg-green-100 text-green-800",
      },
      cancelled: {
        label: "Cancelled",
        icon: <XCircle className="w-3.5 h-3.5" />,
        className: "bg-red-100 text-red-800",
      },
    };

    const statusKey = status.toLowerCase() as keyof typeof statusConfig;
    const config = statusConfig[statusKey] || {
      label: status,
      icon: null,
      className: "bg-gray-100 text-gray-800",
    };

    return (
      <span className={`inline-flex items-center px-2 py-1 text-xs font-semibold rounded-full ${config.className}`}>
        {config.icon && <span className="mr-1">{config.icon}</span>}
        {config.label}
      </span>
    );
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    if (isNaN(date.getTime())) {
      return "Invalid Date";
    }
    return date.toLocaleDateString("en-US", {
      year: "numeric",
      month: "short",
      day: "numeric",
    });
  };

  const formatPreferredTime = (timeString: string | null | undefined) => {
    if (!timeString) return null;
    
    // Try to parse as date first
    const date = new Date(timeString);
    if (!isNaN(date.getTime())) {
      return date.toLocaleDateString("en-US", {
        year: "numeric",
        month: "short",
        day: "numeric",
      });
    }
    // Otherwise return as-is
    return timeString;
  };

  const EmptyState = () => (
    <div className="text-center py-12">
      <div className="mx-auto flex items-center justify-center h-12 w-12 rounded-full bg-gray-100 mb-3">
        <Wrench className="h-6 w-6 text-gray-400" />
      </div>
      <h3 className="text-base font-medium text-gray-900 mb-2">
        No Maintenance Requests Yet
      </h3>
      <p className="text-sm text-gray-500 mb-4 max-w-sm mx-auto">
        Your maintenance request history is empty. Submit your first request to get started.
      </p>
      <button
        onClick={onCreateRequest}
        className="inline-flex items-center bg-gray-900 text-white px-4 py-2 rounded-md hover:bg-gray-800 transition-all duration-200 font-medium text-sm cursor-pointer"
      >
        <Wrench className="w-4 h-4 mr-2" />
        Submit Your First Request
      </button>
    </div>
  );

  const RequestTable = () => (
    <div className="overflow-x-auto">
      <table className="w-full">
        <thead className="bg-gray-50">
          <tr>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Issue
            </th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Submitted
            </th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Preferred Time
            </th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Status
            </th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Actions
            </th>
          </tr>
        </thead>
        <tbody className="bg-white divide-y divide-gray-200">
          {requests.map((request) => (
            <tr key={request.id} className="hover:bg-gray-50 transition-colors duration-150">
              {/* Issue */}
              <td className="px-6 py-4">
                <div className="flex flex-col">
                  <div className="text-sm font-medium text-gray-900">
                    {request.issue_title}
                  </div>
                  {request.description && (
                    <div className="text-sm text-gray-500 line-clamp-1 mt-1">
                      {request.description}
                    </div>
                  )}
                </div>
              </td>

              {/* Submitted Date */}
              <td className="px-6 py-4 whitespace-nowrap">
                <div className="flex items-center text-sm text-gray-900">
                  <Calendar className="w-4 h-4 mr-2 text-gray-400" />
                  {formatDate(request.request_date)}
                </div>
              </td>

              {/* Preferred Time */}
              <td className="px-6 py-4 whitespace-nowrap">
                {request.preferred_time ? (
                  <div className="flex items-center text-sm text-gray-900">
                    <Clock className="w-4 h-4 mr-2 text-gray-400" />
                    {formatPreferredTime(request.preferred_time)}
                  </div>
                ) : (
                  <span className="text-sm text-gray-400">—</span>
                )}
              </td>

              {/* Status */}
              <td className="px-6 py-4 whitespace-nowrap">
                {getStatusBadge(request.status)}
              </td>

              {/* Actions */}
              <td className="px-6 py-4 whitespace-nowrap">
                <button
                  onClick={() => onViewDetails(request)}
                  className="text-sm font-medium text-gray-900 hover:text-teal-600 transition-colors cursor-pointer"
                >
                  View Details
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );

  return (
    <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
      <div className="px-6 py-4 bg-gray-50 border-b border-gray-200">
        <h2 className="text-lg font-semibold text-gray-800">Request History</h2>
      </div>
      
      {requests.length > 0 ? <RequestTable /> : <EmptyState />}
    </div>
  );
};

export default MaintenanceTable;

