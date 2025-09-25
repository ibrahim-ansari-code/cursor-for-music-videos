import React from "react";
import UnitStatusBadge from "./UnitStatusBadge";

const UnitTable = ({
  units,
  loading,
  error,
  onEdit,
  onDelete,
  onAssign,
  onViewLease,
  selectedUnits = [],
  onUnitSelect,
  onSelectAll,
  showSelection = false,
  bulkMode = false
}) => {
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

    // Handle company tenants first
    if (tenant?.tenant_type === "COMPANY" && tenant?.company_name) {
      return tenant.company_name;
    }

    // Handle individual tenants
    const name = [tenant?.first_name, tenant?.last_name]
      .filter(Boolean)
      .join(" ");

    // Fallback to company name if individual names are not available
    if (!name && tenant?.company_name) {
      return tenant.company_name;
    }

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

  const isUnitSelected = (unitId) => {
    return selectedUnits.includes(unitId);
  };

  const isAllSelected = () => {
    if (!units || units.length === 0) return false;
    // Only consider vacant units for "select all" state
    const vacantUnits = units.filter(unit => !unit.is_rented);
    return vacantUnits.length > 0 && vacantUnits.every(unit => selectedUnits.includes(unit.id));
  };

  const isPartiallySelected = () => {
    if (!units || units.length === 0) return false;
    const vacantUnits = units.filter(unit => !unit.is_rented);
    const selectedVacantUnits = vacantUnits.filter(unit => selectedUnits.includes(unit.id));
    return selectedVacantUnits.length > 0 && selectedVacantUnits.length < vacantUnits.length;
  };

  const handleSelectUnit = (unitId) => {
    if (onUnitSelect) {
      onUnitSelect(unitId);
    }
  };

  const handleSelectAll = () => {
    if (onSelectAll) {
      onSelectAll();
    }
  };

  if (loading)
    return (
      <div className="p-8 text-center bg-white dark:bg-gray-800">
        <div className="inline-block animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-blue-500 mb-2"></div>
        <p className="text-gray-600 dark:text-gray-400">Loading units...</p>
      </div>
    );

  if (error)
    return (
      <div className="p-8 text-center text-red-600 dark:text-red-400 bg-white dark:bg-gray-800">
        Error loading units: {error}
      </div>
    );

  return (
    <div className="overflow-x-auto">
      <table className="data-table min-w-full">
        <thead>
          <tr>
            {showSelection && (
              <th scope="col" className="text-center">
                <div className="flex items-center justify-center">
                  <input
                    type="checkbox"
                    className="h-4 w-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
                    checked={isAllSelected()}
                    ref={(input) => {
                      if (input) {
                        input.indeterminate = isPartiallySelected();
                      }
                    }}
                    onChange={handleSelectAll}
                    title="Select all vacant units"
                  />
                </div>
              </th>
            )}
            <th scope="col" className="text-center">Unit Number</th>
            <th scope="col" className="text-center">Floor</th>
            <th scope="col" className="text-center">Rent</th>
            <th scope="col" className="text-center">Tenant</th>
            <th scope="col" className="text-center">Lease Ends</th>
            <th scope="col" className="text-center">Status</th>
            {!bulkMode && (
              <th scope="col" className="text-center">Actions</th>
            )}
          </tr>
        </thead>
        <tbody>
          {units && units.length > 0 ? (
            units.map((unit, index) => (
              <tr
                key={unit.id}
                className={`data-table-row transition-colors ${
                  isUnitSelected(unit.id)
                    ? "bg-blue-50 dark:bg-blue-900/20 border-blue-200 dark:border-blue-700"
                    : unit.is_rented && showSelection
                    ? "bg-gray-50 dark:bg-gray-700/50 opacity-75"
                    : "hover:bg-gray-50 dark:hover:bg-gray-700/50"
                  }`}
              >
                {showSelection && (
                  <td className="px-6 py-4 whitespace-nowrap text-center">
                    <div className="flex flex-col items-center">
                      <input
                        type="checkbox"
                        className={`h-4 w-4 border-gray-300 dark:border-gray-600 rounded focus:ring-blue-500 transition-colors duration-300 ${
                          unit.is_rented 
                            ? 'opacity-50 cursor-not-allowed bg-gray-100 dark:bg-gray-600' 
                            : 'text-blue-600 cursor-pointer dark:bg-gray-700'
                        }`}
                        checked={isUnitSelected(unit.id)}
                        disabled={unit.is_rented}
                        onChange={() => !unit.is_rented && handleSelectUnit(unit.id)}
                        title={unit.is_rented ? "Unit is occupied - cannot assign new tenant" : "Select for bulk assignment"}
                      />
                      {unit.is_rented && (
                        <span className="text-xs text-gray-500 dark:text-gray-400 mt-1 transition-colors duration-300">Occupied</span>
                      )}
                    </div>
                  </td>
                )}
                <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900 dark:text-gray-100 text-center transition-colors duration-300">
                  {unit.name || unit.id}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400 text-center transition-colors duration-300">
                  {unit.floor ?? "N/A"}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400 text-center transition-colors duration-300">
                  {formatCurrency(unit.monthly_rent)}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400 text-center transition-colors duration-300">
                  <div className="truncate max-w-xs">
                    {getTenantName(unit)}
                  </div>
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400 text-center transition-colors duration-300">
                  {getLeaseEndDate(unit)}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-center">
                  <UnitStatusBadge
                    isRented={unit.is_rented}
                    size="small"
                  />
                </td>
                {!bulkMode && (
                  <td className="px-6 py-4 whitespace-nowrap text-center text-sm font-medium">
                    <div className="flex justify-center space-x-3">
                      {!unit.is_rented && onAssign && (
                        <button
                          onClick={() => onAssign(unit)}
                          className="text-green-600 hover:text-green-900 dark:text-green-400 dark:hover:text-green-300 disabled:opacity-50 transition-colors duration-300"
                        >
                          Assign
                        </button>
                      )}
                      {unit.is_rented && onViewLease && (
                        <button
                          onClick={() => onViewLease(unit.id)}
                          className="text-purple-600 hover:text-purple-900 dark:text-purple-400 dark:hover:text-purple-300 disabled:opacity-50 transition-colors duration-300"
                        >
                          View Lease
                        </button>
                      )}
                      <button
                        onClick={() => onEdit && onEdit(unit.id)}
                        className="text-blue-600 hover:text-blue-900 dark:text-blue-400 dark:hover:text-blue-300 disabled:opacity-50 transition-colors duration-300"
                      >
                        Edit
                      </button>
                      <button
                        onClick={() => onDelete && onDelete(unit.id)}
                        className="text-red-600 hover:text-red-900 dark:text-red-400 dark:hover:text-red-300 disabled:opacity-50 transition-colors duration-300"
                      >
                        Delete
                      </button>
                    </div>
                  </td>
                )}
              </tr>
            ))
          ) : (
            <tr>
              <td
                colSpan={(() => {
                  let cols = 6; // Base columns: Unit Number, Floor, Rent, Tenant, Lease Ends, Status
                  return cols;
                })()}
                className="px-6 py-4 text-center text-sm text-gray-500 dark:text-gray-400 transition-colors duration-300"
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
