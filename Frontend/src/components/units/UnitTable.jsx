import React from "react";
import UnitStatusBadge from "./UnitStatusBadge";

const UnitTable = ({ units, loading, error, onEdit, onDelete, onAssign, onViewLease }) => {
  const formatCurrency = (amount) => {
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: "USD",
    }).format(amount || 0);
  };

  const getTenantName = (unit) => {
    if (!unit || typeof unit !== "object") return "Not assigned";
    const tenant = unit?.tenant;
    if (!tenant || typeof tenant !== "object") return "Not assigned";

    const name = [tenant.first_name, tenant.last_name]
      .filter(Boolean)
      .join(" ");
    return name || "Not assigned";
  };

  const formatDate = (dateString) => {
    if (!dateString) return "N/A";
    const date = new Date(dateString);
    return date.toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
    });
  };

  const getLeaseEndDate = (unit) => {
    // If unit has lease info attached, use it
    if (unit?.lease?.end_date) {
      return formatDate(unit.lease.end_date);
    }
    // If unit is rented but no lease data yet, show loading or placeholder
    if (unit.is_rented) {
      return unit.lease === undefined ? "Loading..." : "No end date";
    }
    // Not rented
    return "N/A";
  };

  const getLeaseDuration = (unit) => {
    // Show both start and end dates if available
    if (unit?.lease?.start_date && unit?.lease?.end_date) {
      return `${formatDate(unit.lease.start_date)} - ${formatDate(unit.lease.end_date)}`;
    }
    return getLeaseEndDate(unit);
  };

  if (loading)
    return (
      <div className="p-8 text-center">
        <div className="inline-block animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-blue-500 mb-2"></div>
        <p className="text-gray-600">Loading units...</p>
      </div>
    );

  if (error)
    return (
      <div className="p-8 text-center text-red-600">
        Error loading units: {error}
      </div>
    );

  return (
    <div className="overflow-x-auto">
      <table className="min-w-full divide-y divide-gray-200">
        <thead className="bg-gray-50">
          <tr>
            <th
              scope="col"
              className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider"
            >
              Unit Number
            </th>
            <th
              scope="col"
              className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider"
            >
              Floor
            </th>
            <th
              scope="col"
              className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider"
            >
              Rent
            </th>
            <th
              scope="col"
              className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider"
            >
              Tenant
            </th>
            <th
              scope="col"
              className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider"
            >
              Lease Ends
            </th>
            <th
              scope="col"
              className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider"
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
          {units && units.length > 0 ? (
            units.map((unit) => (
              <tr key={unit.id} className="hover:bg-gray-50 transition-colors">
                <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900 text-center">
                  {unit.name || unit.id}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 text-center">
                  {unit.floor ?? "N/A"}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 text-center">
                  {formatCurrency(unit.monthly_rent)}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 text-center">
                  <div className="truncate max-w-xs">
                    {getTenantName(unit)}
                  </div>
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 text-center">
                  {getLeaseEndDate(unit)}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-center">
                  <UnitStatusBadge 
                    isRented={unit.is_rented} 
                    size="small"
                  />
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-center text-sm font-medium">
                  <div className="flex justify-center space-x-3">
                    {!unit.is_rented && onAssign && (
                      <button
                        onClick={() => onAssign(unit)}
                        className="text-green-600 hover:text-green-900 disabled:opacity-50"
                      >
                        Assign
                      </button>
                    )}
                    {unit.is_rented && onViewLease && (
                      <button
                        onClick={() => onViewLease(unit.id)}
                        className="text-purple-600 hover:text-purple-900 disabled:opacity-50"
                      >
                        View Lease
                      </button>
                    )}
                    <button
                      onClick={() => onEdit && onEdit(unit.id)}
                      className="text-blue-600 hover:text-blue-900 disabled:opacity-50"
                    >
                      Edit
                    </button>
                    <button
                      onClick={() => onDelete && onDelete(unit.id)}
                      className="text-red-600 hover:text-red-900 disabled:opacity-50"
                    >
                      Delete
                    </button>
                  </div>
                </td>
              </tr>
            ))
          ) : (
            <tr>
              <td
                colSpan="7"
                className="px-6 py-4 text-center text-sm text-gray-500"
              >
                No units found for this property.
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
};

export default UnitTable;
