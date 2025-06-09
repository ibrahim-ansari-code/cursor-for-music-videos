import React from "react";
import PropTypes from "prop-types";

const StatusBadge = ({ status }) => {
  const statusStyles = {
    "PENDING": "bg-yellow-100 text-yellow-800",
    "IN_PROGRESS": "bg-blue-100 text-blue-800", 
    "SCHEDULED": "bg-indigo-100 text-indigo-800",
    "COMPLETED": "bg-green-100 text-green-800",
    "CANCELLED": "bg-gray-100 text-gray-800",
    // Support title-case values as well for backward compatibility
    "Pending": "bg-yellow-100 text-yellow-800",
    "In Progress": "bg-blue-100 text-blue-800",
    "Scheduled": "bg-indigo-100 text-indigo-800", 
    "Completed": "bg-green-100 text-green-800",
    "Cancelled": "bg-gray-100 text-gray-800",
  };

  // Normalize status value to handle different cases
  const normalizedStatus = (status || "")
    .replace(/[-\s]/g, "_")   // unify separators
    .toUpperCase();
  const style = statusStyles[normalizedStatus] || statusStyles[normalizedStatus.toUpperCase()] || "bg-gray-100 text-gray-800";

  return (
    <span
      className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${style}`}
    >
      {status}
    </span>
  );
};

StatusBadge.propTypes = {
  status: PropTypes.string.isRequired,
};

const PriorityBadge = ({ priority }) => {
  const priorityStyles = {
    "HIGH": "bg-red-100 text-red-800",
    "MEDIUM": "bg-orange-100 text-orange-800", 
    "LOW": "bg-green-100 text-green-800",
    // Support title-case values as well for backward compatibility
    "High": "bg-red-100 text-red-800",
    "Medium": "bg-orange-100 text-orange-800",
    "Low": "bg-green-100 text-green-800",
  };

  // Normalize priority value to handle different cases
  const normalizedPriority = priority || "";
  const style = priorityStyles[normalizedPriority] || priorityStyles[normalizedPriority.toUpperCase()] || "bg-gray-100 text-gray-800";

  return (
    <span
      className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${style}`}
    >
      {priority}
    </span>
  );
};

PriorityBadge.propTypes = {
  priority: PropTypes.string.isRequired,
};

const MaintenanceTable = ({ requests, onEdit, onDelete, onView, currentPage = 1, pageSize = 20 }) => {
  if (!requests || requests.length === 0) {
    return (
      <div className="p-4 text-center text-gray-500">
        No maintenance requests for this filter.
      </div>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="min-w-full divide-y divide-gray-200">
        <thead className="bg-gray-50">
          <tr>
            <th
              scope="col"
              className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
            >
              #
            </th>
            <th
              scope="col"
              className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
            >
              Issue
            </th>
            <th
              scope="col"
              className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
            >
              Property / Unit
            </th>
            <th
              scope="col"
              className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
            >
              Tenant
            </th>
            <th
              scope="col"
              className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
            >
              Request Date
            </th>
            <th
              scope="col"
              className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
            >
              Priority
            </th>
            <th
              scope="col"
              className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
            >
              Assigned To
            </th>
            <th
              scope="col"
              className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
            >
              Status
            </th>
            <th
              scope="col"
              className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider"
            >
              Actions
            </th>
          </tr>
        </thead>
        <tbody className="bg-white divide-y divide-gray-200">
          {requests.map((request, index) => (
            <tr key={request.id} className="hover:bg-gray-50 transition-colors">
              <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                {(currentPage - 1) * pageSize + index + 1}
              </td>
              <td className="px-6 py-4 whitespace-nowrap">
                <div className="text-sm font-medium text-gray-900">
                  {request.issue_title}
                </div>
                <div
                  className="text-sm text-gray-500 truncate"
                  style={{ maxWidth: "250px" }}
                >
                  {request.description}
                </div>
              </td>
              <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                {request.property?.name || "N/A"} /{" "}
                {request.unit?.unit_number || request.unit?.name || "N/A"}
              </td>
              <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                {request.tenant?.name || "N/A"}
              </td>
              <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                {new Date(request.request_date).toLocaleDateString()}
              </td>
              <td className="px-6 py-4 whitespace-nowrap">
                <PriorityBadge priority={request.priority} />
              </td>
              <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                {request.assigned_to || "N/A"}
              </td>
              <td className="px-6 py-4 whitespace-nowrap">
                <StatusBadge status={request.status} />
              </td>
              <td className="px-6 py-4 whitespace-nowrap text-center text-sm font-medium">
                <div className="flex justify-center space-x-3">
                  <button
                    onClick={() => onView(request)}
                    className="text-indigo-600 hover:text-indigo-900"
                  >
                    View
                  </button>
                  <button
                    onClick={() => onEdit(request)}
                    className="text-blue-600 hover:text-blue-900"
                  >
                    Edit
                  </button>
                  <button
                    onClick={() => onDelete(request.id)}
                    className="text-red-600 hover:text-red-900"
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

MaintenanceTable.propTypes = {
  requests: PropTypes.arrayOf(
    PropTypes.shape({
      id: PropTypes.number.isRequired,
      issue_title: PropTypes.string.isRequired,
      description: PropTypes.string,
      property: PropTypes.shape({
        id: PropTypes.number,
        name: PropTypes.string,
      }),
      unit: PropTypes.shape({
        id: PropTypes.number,
        name: PropTypes.string,
        unit_number: PropTypes.string,
      }),
      tenant: PropTypes.shape({
        id: PropTypes.number,
        name: PropTypes.string,
      }),
      request_date: PropTypes.string.isRequired,
      priority: PropTypes.string.isRequired,
      status: PropTypes.string.isRequired,
      assigned_to: PropTypes.string,
    })
  ).isRequired,
  onEdit: PropTypes.func.isRequired,
  onDelete: PropTypes.func.isRequired,
  onView: PropTypes.func.isRequired,
  currentPage: PropTypes.number,
  pageSize: PropTypes.number,
};

MaintenanceTable.defaultProps = {
  currentPage: 1,
  pageSize: 20,
};

export default MaintenanceTable;
