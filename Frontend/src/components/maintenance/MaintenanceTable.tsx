import React, { useRef, useEffect } from "react";
import type {
  MaintenanceRequest,
  MaintenanceTableProps as OriginalProps,
  Tenant,
} from "../../types/tenant";

// Define the props for the component, extending the original props
type MaintenanceTableProps = OriginalProps & {
  selectedRequests: number[];
  onSelectedRequestsChange: (ids: number[]) => void;
};

// Badge components
const StatusBadge: React.FC<{ status: string }> = ({ status }) => {
  const getStatusClass = (status: string): string => {
    switch (status?.toLowerCase()) {
      case "completed":
        return "badge-success";
      case "pending":
        return "badge-warning";
      case "in_progress":
      case "in progress":
        return "badge-info";
      case "cancelled":
        return "badge-gray";
      default:
        return "badge-info";
    }
  };

  return <span className={`badge ${getStatusClass(status)}`}>{status}</span>;
};

const PriorityBadge: React.FC<{ priority: string }> = ({ priority }) => {
  const getPriorityClass = (priority: string): string => {
    switch (priority?.toLowerCase()) {
      case "high":
        return "badge-danger";
      case "medium":
        return "badge-warning";
      case "low":
        return "badge-success";
      default:
        return "badge-gray";
    }
  };

  return (
    <span className={`badge ${getPriorityClass(priority)}`}>{priority}</span>
  );
};

// Helper function to format tenant name
const getTenantName = (
  tenant?:
    | Tenant
    | {
        first_name?: string;
        last_name?: string;
        company_name?: string;
        tenant_type?: string;
      }
    | null
): string => {
  if (!tenant) return "N/A";
  if (tenant.company_name) return tenant.company_name;
  if (tenant.first_name || tenant.last_name)
    return `${tenant.first_name || ""} ${tenant.last_name || ""}`.trim();
  return "N/A";
};

const MaintenanceTable: React.FC<MaintenanceTableProps> = ({
  requests,
  onEdit,
  onDelete,
  onView,
  currentPage = 1,
  pageSize = 20,
  selectedRequests,
  onSelectedRequestsChange,
}) => {
  const selectAllCheckboxRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (selectAllCheckboxRef.current) {
      const isIndeterminate =
        selectedRequests.length > 0 &&
        selectedRequests.length < requests.length;
      selectAllCheckboxRef.current.indeterminate = isIndeterminate;
    }
  }, [selectedRequests, requests.length]);

  const handleSelectAll = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.checked) {
      onSelectedRequestsChange(requests.map((r) => r.id));
    } else {
      onSelectedRequestsChange([]);
    }
  };

  const handleSelectOne = (
    e: React.ChangeEvent<HTMLInputElement>,
    requestId: number
  ) => {
    if (e.target.checked) {
      if (!selectedRequests.includes(requestId)) {
        onSelectedRequestsChange([...selectedRequests, requestId]);
      }
    } else {
      onSelectedRequestsChange(
        selectedRequests.filter((id) => id !== requestId)
      );
    }
  };

  if (!requests || requests.length === 0) {
    return (
      <div className="dark-panel dark-shadow rounded-lg p-8 text-center dark-divider border">
        <div className="mx-auto w-24 h-24 bg-orange-50 dark:bg-orange-900/20 rounded-full flex items-center justify-center mb-4">
          <svg
            className="h-12 w-12 text-orange-500 dark:text-orange-400"
            xmlns="http://www.w3.org/2000/svg"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth="1.5"
              d="M11 4a2 2 0 114 0v1a1 1 0 001 1h3a1 1 0 011 1v3a1 1 0 01-1 1h-1a2 2 0 100 4h1a1 1 0 011 1v3a1 1 0 01-1 1h-3a1 1 0 01-1-1v-1a2 2 0 10-4 0v1a1 1 0 01-1 1H7a1 1 0 01-1-1v-3a1 1 0 011-1h1a2 2 0 100-4H7a1 1 0 01-1-1V7a1 1 0 011-1h3a1 1 0 001-1V4z"
            />
          </svg>
        </div>
        <h3 className="text-lg font-medium text-gray-900 dark:text-gray-100 mb-2">
          No maintenance requests found
        </h3>
        <p className="text-gray-500 dark:text-gray-400">
          No maintenance requests match the current filter.
        </p>
      </div>
    );
  }

  return (
    <div className="overflow-x-auto scrollbar-thin">
      <table className="data-table min-w-full divide-y dark-divider">
        <thead className="dark-input">
          <tr>
            <th scope="col" className="px-6 py-3">
              <input
                type="checkbox"
                ref={selectAllCheckboxRef}
                className="form-checkbox h-4 w-4 text-blue-600 dark:bg-gray-800 border-gray-300 dark:border-gray-600 rounded focus:ring-blue-500"
                onChange={handleSelectAll}
                checked={
                  requests.length > 0 &&
                  selectedRequests.length === requests.length
                }
                aria-label="Select all maintenance requests"
              />
            </th>
            <th
              scope="col"
              className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider transition-colors duration-300"
            >
              #
            </th>
            <th
              scope="col"
              className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider transition-colors duration-300"
            >
              Issue
            </th>
            <th
              scope="col"
              className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider transition-colors duration-300"
            >
              Property / Unit
            </th>
            <th
              scope="col"
              className="px-6 py-3 text-center text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider transition-colors duration-300"
            >
              Tenant
            </th>
            <th
              scope="col"
              className="px-6 py-3 text-center text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider transition-colors duration-300"
            >
              Request Date
            </th>
            <th
              scope="col"
              className="px-6 py-3 text-center text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider transition-colors duration-300"
            >
              Priority
            </th>
            <th
              scope="col"
              className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider transition-colors duration-300"
            >
              Assigned To
            </th>
            <th
              scope="col"
              className="px-6 py-3 text-center text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider transition-colors duration-300"
            >
              Status
            </th>
            <th
              scope="col"
              className="px-6 py-3 text-center text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider transition-colors duration-300"
            >
              Actions
            </th>
          </tr>
        </thead>
        <tbody className="dark-panel divide-y dark-divider">
          {requests.map((request: MaintenanceRequest, index: number) => (
            <tr
              key={request.id}
              className={
                selectedRequests.includes(request.id)
                  ? "bg-blue-50 dark:bg-blue-900/10"
                  : ""
              }
            >
              <td className="px-6 py-4 whitespace-nowrap">
                <input
                  type="checkbox"
                  className="form-checkbox h-4 w-4 text-blue-600 dark:bg-gray-800 border-gray-300 dark:border-gray-600 rounded focus:ring-blue-500"
                  checked={selectedRequests.includes(request.id)}
                  onChange={(e) => handleSelectOne(e, request.id)}
                  aria-label={`Select maintenance request for ${request.issue_title}`}
                />
              </td>
              <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400 transition-colors duration-300">
                {(currentPage - 1) * pageSize + index + 1}
              </td>
              <td className="px-6 py-4 whitespace-nowrap">
                <div className="text-sm font-medium text-gray-900 dark:text-gray-100">
                  {request.issue_title}
                </div>
                <div
                  className="text-sm text-gray-500 dark:text-gray-400 truncate"
                  style={{ maxWidth: "250px" }}
                >
                  {request.description}
                </div>
              </td>
              <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400 transition-colors duration-300">
                <div className="text-sm text-gray-900 dark:text-gray-100 transition-colors duration-300">
                  {request.property?.name || "N/A"}
                </div>
                <div className="text-xs text-gray-500 dark:text-gray-400">
                  {request.unit?.name || "Common Area"}
                </div>
              </td>
              <td className="px-6 py-4 whitespace-nowrap text-center">
                <div className="text-sm text-gray-900 dark:text-gray-100 transition-colors duration-300">
                  {getTenantName(request.tenant)}
                </div>
              </td>
              <td className="px-6 py-4 whitespace-nowrap text-center">
                <div className="text-sm text-gray-900 dark:text-gray-100 transition-colors duration-300">
                  {(() => {
                    try {
                      const date = new Date(request.request_date);
                      return isNaN(date.getTime())
                        ? "Invalid Date"
                        : date.toLocaleDateString();
                    } catch {
                      return "Invalid Date";
                    }
                  })()}
                </div>
              </td>
              <td className="px-6 py-4 whitespace-nowrap text-center">
                <PriorityBadge priority={request.priority} />
              </td>
              <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-gray-100 transition-colors duration-300">
                {request.vendor ? (
                  <div>
                    <div className="font-medium">{request.vendor.company_name}</div>
                    {request.vendor.contact_person && (
                      <div className="text-xs text-gray-500 dark:text-gray-400">
                        {request.vendor.contact_person}
                      </div>
                    )}
                  </div>
                ) : request.assigned_to ? (
                  request.assigned_to
                ) : (
                  "N/A"
                )}
              </td>
              <td className="px-6 py-4 whitespace-nowrap text-center">
                <StatusBadge status={request.status} />
              </td>
              <td className="px-6 py-4 whitespace-nowrap text-center text-sm font-medium">
                <div className="flex justify-center space-x-3">
                  <button
                    onClick={() => onView(request)}
                    className="text-indigo-600 dark:text-indigo-400 hover:text-indigo-900 dark:hover:text-indigo-300 focus:outline-none transition-colors duration-150"
                  >
                    View
                  </button>
                  <button
                    onClick={() => onEdit(request)}
                    className="text-blue-600 dark:text-blue-400 hover:text-blue-900 dark:hover:text-blue-300 focus:outline-none transition-colors duration-150"
                  >
                    Edit
                  </button>
                  <button
                    onClick={() => onDelete(request.id)}
                    className="text-red-600 dark:text-red-400 hover:text-red-900 dark:hover:text-red-300 focus:outline-none transition-colors duration-150"
                  >
                    Delete
                  </button>
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

export default MaintenanceTable;
