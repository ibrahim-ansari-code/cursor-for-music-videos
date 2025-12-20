import React, { useRef, useEffect, useState } from "react";
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
      case "new":
        return "badge-new";
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
  selectedRequests,
  onSelectedRequestsChange,
}) => {
  const selectAllCheckboxRef = useRef<HTMLInputElement>(null);
  const [openDropdownId, setOpenDropdownId] = useState<number | null>(null);
  const dropdownRefs = useRef<{ [key: number]: HTMLDivElement | null }>({});

  useEffect(() => {
    if (selectAllCheckboxRef.current) {
      const isIndeterminate =
        selectedRequests.length > 0 &&
        selectedRequests.length < requests.length;
      selectAllCheckboxRef.current.indeterminate = isIndeterminate;
    }
  }, [selectedRequests, requests.length]);

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      const target = event.target as Node;
      const isClickedInsideDropdown = openDropdownId !== null && 
        dropdownRefs.current[openDropdownId]?.contains(target);
      
      if (!isClickedInsideDropdown && openDropdownId !== null) {
        setOpenDropdownId(null);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [openDropdownId]);

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
          {requests.map((request: MaintenanceRequest) => {
            const isNew = request.status?.toLowerCase() === "new";
            const baseRowClassName = isNew
              ? "relative bg-gradient-to-r from-blue-50 via-blue-50/50 to-transparent dark:from-blue-900/20 dark:via-blue-900/10 dark:to-transparent border-l-4 border-blue-500"
              : selectedRequests.includes(request.id)
              ? "bg-blue-50 dark:bg-blue-900/10"
              : "";
            
            const rowClassName = `${baseRowClassName} cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors duration-150`;
            
            const handleRowClick = (e: React.MouseEvent) => {
              // Don't trigger row click if clicking checkbox or action button
              const target = e.target as HTMLElement;
              if (
                target.closest('input[type="checkbox"]') || 
                target.closest('button') ||
                target.closest('.dropdown-menu')
              ) {
                return;
              }
              
              // NEW requests open in edit mode for triage, others open in view mode
              if (isNew) {
                onEdit(request);
              } else {
                onView(request);
              }
            };
            
            return (
            <tr
              key={request.id}
              className={rowClassName}
              onClick={handleRowClick}
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
                  {request.unit?.name || "N/A"}
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
                <div className="relative inline-block text-left" ref={(el) => {
                  if (el) dropdownRefs.current[request.id] = el;
                }}>
                  <button
                    type="button"
                    onClick={() => setOpenDropdownId(openDropdownId === request.id ? null : request.id)}
                    className="inline-flex items-center justify-center w-8 h-8 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 rounded-full hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors duration-150 cursor-pointer"
                    aria-label="Open actions menu"
                  >
                    <svg className="w-5 h-5" viewBox="0 0 20 20" fill="currentColor">
                      <path d="M10 6a2 2 0 110-4 2 2 0 010 4zM10 12a2 2 0 110-4 2 2 0 010 4zM10 18a2 2 0 110-4 2 2 0 010 4z" />
                    </svg>
                  </button>

                  {openDropdownId === request.id && (
                    <div className="dropdown-menu origin-top-right absolute right-0 mt-2 w-48 rounded-md shadow-lg bg-white dark:bg-gray-800 ring-1 ring-black ring-opacity-5 z-50">
                      <div className="py-1" role="menu" aria-orientation="vertical" aria-labelledby="options-menu">
                        <button
                          onClick={() => {
                            onView(request);
                            setOpenDropdownId(null);
                          }}
                          className="w-full text-left px-4 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 hover:text-gray-900 dark:hover:text-white transition-colors duration-150 flex items-center cursor-pointer"
                          role="menuitem"
                        >
                          <svg className="mr-3 h-4 w-4 text-indigo-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                          </svg>
                          View
                        </button>
                        <button
                          onClick={() => {
                            onEdit(request);
                            setOpenDropdownId(null);
                          }}
                          className="w-full text-left px-4 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 hover:text-gray-900 dark:hover:text-white transition-colors duration-150 flex items-center cursor-pointer"
                          role="menuitem"
                        >
                          <svg className="mr-3 h-4 w-4 text-blue-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                          </svg>
                          Edit
                        </button>
                        <button
                          onClick={() => {
                            onDelete(request.id);
                            setOpenDropdownId(null);
                          }}
                          className="w-full text-left px-4 py-2 text-sm text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 hover:text-red-700 dark:hover:text-red-300 transition-colors duration-150 flex items-center cursor-pointer"
                          role="menuitem"
                        >
                          <svg className="mr-3 h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                          </svg>
                          Delete
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              </td>
            </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
};

export default MaintenanceTable;
