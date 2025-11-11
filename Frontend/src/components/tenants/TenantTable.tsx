import React from "react";
import { useNavigate } from "react-router-dom";
import { getInitials, formatDate } from "../../utils/tenantUtils";
import { TenantTableProps, EnrichedTenant } from "../../types/tenant";

const TenantTable: React.FC<TenantTableProps> = ({
  tenants,
  onEditTenant,
  onDeleteTenant,
  onAddTenant,
  isLoading,
  selectedTenants,
  onToggleSelectAll,
  onToggleSelect,
}) => {
  const navigate = useNavigate();
  const selectAllRef = React.useRef<HTMLInputElement>(null);

  React.useEffect(() => {
    if (selectAllRef.current) {
      selectAllRef.current.indeterminate =
        selectedTenants.length > 0 && selectedTenants.length < tenants.length;
    }
  }, [selectedTenants.length, tenants.length]);

  // Helper function to get tenant display name
  const getTenantDisplayName = (tenant: EnrichedTenant): string => {
    if (tenant.tenant_type === "Company") {
      return tenant.company_name || "Company Tenant";
    } else {
      return (
        `${tenant.first_name || ""} ${tenant.last_name || ""}`.trim() ||
        "Individual Tenant"
      );
    }
  };

  // Helper function to get tenant subtitle (for companies, show contact person)
  const getTenantSubtitle = (tenant: EnrichedTenant): string | null => {
    if (tenant.tenant_type === "Company" && tenant.contact_person) {
      return `Contact: ${tenant.contact_person}`;
    }
    return null;
  };

  // Helper function to get lease duration display (returns string for combined column)
  const getLeaseDuration = (tenant: EnrichedTenant): string | null => {
    if (!tenant.leases || tenant.leases.length === 0) {
      return null; // Return null so we don't display anything
    }

    // Find the most recent active lease
    const today = new Date();
    const activeLease = tenant.leases.find((lease) => {
      // Validate dates before comparison
      if (!lease.start_date || !lease.end_date) return false;
      const startDate = new Date(lease.start_date);
      const endDate = new Date(lease.end_date);
      // Check if dates are valid
      if (isNaN(startDate.getTime()) || isNaN(endDate.getTime())) return false;
      return (
        lease.status?.toUpperCase() === "ACTIVE" &&
        startDate <= today &&
        endDate >= today
      );
    });

    let targetLease = activeLease;

    // If no active lease, use the most recent lease
    if (!targetLease && tenant.leases.length > 0) {
      // Filter leases with valid start_date before reduce operation
      const validLeases = tenant.leases.filter(
        (lease) =>
          lease.start_date && !isNaN(new Date(lease.start_date).getTime())
      );
      if (validLeases.length > 0) {
        targetLease = validLeases.reduce((latest, current) => {
          return new Date(current.start_date) > new Date(latest.start_date)
            ? current
            : latest;
        });
      }
    }

    if (!targetLease) {
      return null; // Return null so we don't display anything
    }

    const startDate = formatDate(targetLease.start_date);
    const endDate = formatDate(targetLease.end_date);

    return `${startDate} - ${endDate}`;
  };

  if (isLoading) {
    return (
      <div className="bg-white dark:bg-gray-800 shadow overflow-hidden sm:rounded-lg">
        <div className="p-8 text-center">
          <div className="animate-pulse">
            <div className="h-8 bg-gray-200 dark:bg-gray-700 rounded mb-4"></div>
            <div className="space-y-3">
              {[...Array(3)].map((_, i) => (
                <div
                  key={i}
                  className="h-12 bg-gray-100 dark:bg-gray-600 rounded"
                ></div>
              ))}
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (!tenants || tenants.length === 0) {
    return (
      <div className="bg-white dark:bg-gray-800 shadow-lg rounded-lg p-8 text-center border border-gray-100 dark:border-gray-700">
        <div className="mx-auto w-24 h-24 bg-blue-50 dark:bg-blue-900/20 rounded-full flex items-center justify-center mb-4">
          <svg
            className="h-12 w-12 text-blue-500 dark:text-blue-400"
            xmlns="http://www.w3.org/2000/svg"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={1.5}
              d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z"
            />
          </svg>
        </div>
        <h3 className="text-lg font-medium text-gray-900 dark:text-gray-100 mb-2">
          No tenants found
        </h3>
        <p className="text-gray-500 dark:text-gray-400 mb-6">
          Try adjusting your search criteria or add new tenants.
        </p>
        {onAddTenant && (
          <button
            type="button"
            onClick={onAddTenant}
            className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-blue-600 dark:bg-blue-700 hover:bg-blue-700 dark:hover:bg-blue-600 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 dark:focus:ring-offset-gray-800"
          >
            <svg
              className="-ml-1 mr-2 h-5 w-5"
              xmlns="http://www.w3.org/2000/svg"
              viewBox="0 0 20 20"
              fill="currentColor"
            >
              <path
                fillRule="evenodd"
                d="M10 5a1 1 0 011 1v3h3a1 1 0 110 2h-3v3a1 1 0 11-2 0v-3H6a1 1 0 110-2h3V6a1 1 0 011-1z"
                clipRule="evenodd"
              />
            </svg>
            Add Tenant
          </button>
        )}
      </div>
    );
  }

  return (
    <div className="overflow-hidden rounded-lg">
      <div className="overflow-x-auto">
        <table className="data-table min-w-full">
          <thead>
            <tr>
              <th
                scope="col"
                className="px-6 py-4 text-left font-semibold text-gray-700 dark:text-gray-300 bg-gray-50 dark:bg-gray-800"
              >
                <input
                  type="checkbox"
                  ref={selectAllRef}
                  className="h-4 w-4 rounded border-gray-300 text-indigo-600 focus:ring-indigo-500"
                  onChange={onToggleSelectAll}
                  checked={
                    tenants.length > 0 &&
                    tenants.every((tenant) =>
                      selectedTenants.includes(tenant.id)
                    )
                  }
                />
              </th>
              <th
                scope="col"
                className="px-6 py-4 text-left font-semibold text-gray-700 dark:text-gray-300 bg-gray-50 dark:bg-gray-800"
              >
                Tenant
              </th>
              <th
                scope="col"
                className="px-6 py-4 text-left font-semibold text-gray-700 dark:text-gray-300 bg-gray-50 dark:bg-gray-800"
              >
                Property
              </th>
              <th
                scope="col"
                className="px-6 py-4 text-left font-semibold text-gray-700 dark:text-gray-300 bg-gray-50 dark:bg-gray-800"
              >
                Unit
              </th>
              <th
                scope="col"
                className="px-6 py-4 text-left font-semibold text-gray-700 dark:text-gray-300 bg-gray-50 dark:bg-gray-800"
              >
                Email
              </th>
              <th
                scope="col"
                className="px-6 py-4 text-left font-semibold text-gray-700 dark:text-gray-300 bg-gray-50 dark:bg-gray-800"
              >
                Phone
              </th>
              <th
                scope="col"
                className="px-6 py-4 text-center font-semibold text-gray-700 dark:text-gray-300 bg-gray-50 dark:bg-gray-800"
              >
                Lease & Status
              </th>
              <th
                scope="col"
                className="px-6 py-4 text-center font-semibold text-gray-700 dark:text-gray-300 bg-gray-50 dark:bg-gray-800"
              >
                Actions
              </th>
            </tr>
          </thead>
          <tbody>
            {tenants.map((tenant) => {
              const leaseDuration = getLeaseDuration(tenant);
              const displayName = getTenantDisplayName(tenant);
              const subtitle = getTenantSubtitle(tenant);

              // data-table CSS now handles zebra striping
              return (
                <tr
                  key={tenant.id}
                  onClick={() => navigate(`/tenants/${tenant.id}`)}
                  className="cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors"
                >
                  <td
                    className="px-6 py-4 whitespace-nowrap"
                    onClick={(e) => e.stopPropagation()}
                  >
                    <input
                      type="checkbox"
                      className="h-4 w-4 rounded border-gray-300 text-indigo-600 focus:ring-indigo-500"
                      checked={selectedTenants.includes(tenant.id)}
                      onChange={() => onToggleSelect(tenant.id)}
                    />
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="flex items-center">
                      <div className="flex-shrink-0 h-10 w-10">
                        <div className="h-10 w-10 rounded-full bg-gray-200 dark:bg-gray-600 flex items-center justify-center">
                          <span className="text-gray-700 dark:text-gray-300 font-medium text-sm">
                            {getInitials(tenant)}
                          </span>
                        </div>
                      </div>
                      <div className="ml-4">
                        <div className="text-sm font-medium text-gray-900 dark:text-gray-100">
                          {displayName}
                        </div>
                        {subtitle && (
                          <div className="text-xs text-gray-500 dark:text-gray-400">
                            {subtitle}
                          </div>
                        )}
                        {tenant.tenant_type === "Company" && (
                          <div className="text-xs text-blue-600 dark:text-blue-400 font-medium">
                            Company
                          </div>
                        )}
                      </div>
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400 text-left">
                    {tenant.property?.name ??
                      tenant.unit?.property?.name ??
                      "--"}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400 text-left">
                    {tenant.unit ? tenant.unit.name : "--"}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-left">
                    {tenant.email ? (
                      <a href={`mailto:${tenant.email}`} className="email-link">
                        {tenant.email}
                      </a>
                    ) : (
                      <span className="text-gray-500 dark:text-gray-400">
                        --
                      </span>
                    )}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-left">
                    {tenant.phone ? (
                      <a href={`tel:${tenant.phone}`} className="phone-link">
                        {tenant.phone}
                      </a>
                    ) : (
                      <span className="text-gray-500 dark:text-gray-400">
                        --
                      </span>
                    )}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-center">
                    <div className="flex flex-col items-center space-y-1">
                      {leaseDuration && (
                        <div className="text-xs text-gray-500 dark:text-gray-400 text-center">
                          {leaseDuration}
                        </div>
                      )}
                      <span
                        className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${
                          tenant.status?.toLowerCase() === "active"
                            ? "bg-green-100 dark:bg-green-900/30 text-green-800 dark:text-green-200"
                            : tenant.status?.toLowerCase() === "pending"
                            ? "bg-yellow-100 dark:bg-yellow-900/30 text-yellow-800 dark:text-yellow-200"
                            : tenant.status?.toLowerCase() === "overdue"
                            ? "bg-red-100 dark:bg-red-900/30 text-red-800 dark:text-red-200"
                            : "bg-gray-100 dark:bg-gray-900/30 text-gray-800 dark:text-gray-200"
                        }`}
                      >
                        {tenant.status || "Unknown"}
                      </span>
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-center text-sm font-medium">
                    <div className="inline-flex space-x-3">
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          onEditTenant(tenant);
                        }}
                        className="text-blue-600 dark:text-blue-400 hover:text-blue-900 dark:hover:text-blue-300 focus:outline-none transition-colors duration-150"
                      >
                        Edit
                      </button>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          onDeleteTenant(tenant.id);
                        }}
                        className="text-red-600 dark:text-red-400 hover:text-red-900 dark:hover:text-red-300 focus:outline-none transition-colors duration-150"
                      >
                        Delete
                      </button>
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default TenantTable;
