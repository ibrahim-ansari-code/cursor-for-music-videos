import React from "react";
import { getInitials, formatDate, getStatusBadgeClass } from "../../utils/tenantUtils";

const TenantTable = ({ tenants, onEditTenant, onDeleteTenant, onAddTenant, isLoading }) => {
  // Helper function to get tenant display name
  const getTenantDisplayName = (tenant) => {
    if (tenant.tenant_type === "Company") {
      return tenant.company_name || "Company Tenant";
    } else {
      return `${tenant.first_name || ""} ${tenant.last_name || ""}`.trim() || "Individual Tenant";
    }
  };

  // Helper function to get tenant subtitle (for companies, show contact person)
  const getTenantSubtitle = (tenant) => {
    if (tenant.tenant_type === "Company" && tenant.contact_person) {
      return `Contact: ${tenant.contact_person}`;
    }
    return null;
  };

  // Helper function to get lease duration display
  const getLeaseDuration = (tenant) => {
    if (!tenant.leases || tenant.leases.length === 0) {
      return "--";
    }

    // Find the most recent active lease
    const today = new Date();
    const activeLease = tenant.leases.find(lease => {
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
      const validLeases = tenant.leases.filter(lease => 
        lease.start_date && !isNaN(new Date(lease.start_date).getTime())
      );
      if (validLeases.length > 0) {
        targetLease = validLeases.reduce((latest, current) => {
          return new Date(current.start_date) > new Date(latest.start_date) ? current : latest;
        });
      }
    }

    if (!targetLease) {
      return "--";
    }

    const startDate = formatDate(targetLease.start_date);
    const endDate = formatDate(targetLease.end_date);
    const isActive = targetLease.status?.toUpperCase() === "ACTIVE";
    
    return (
      <div className="text-center">
        <div className="text-sm text-gray-900">
          {startDate} - {endDate}
        </div>
        <div className={`text-xs font-medium ${isActive ? 'text-green-600' : 'text-gray-500'}`}>
          {isActive ? 'Active' : 'Inactive'}
        </div>
      </div>
    );
  };

  if (isLoading) {
    return (
      <div className="bg-white shadow overflow-hidden sm:rounded-lg">
        <div className="p-8 text-center">
          <div className="animate-pulse">
            <div className="h-8 bg-gray-200 rounded mb-4"></div>
            <div className="space-y-3">
              {[...Array(3)].map((_, i) => (
                <div key={i} className="h-12 bg-gray-100 rounded"></div>
              ))}
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (!tenants || tenants.length === 0) {
    return (
      <div className="bg-white shadow-lg rounded-lg p-8 text-center border border-gray-100">
        <div className="mx-auto w-24 h-24 bg-blue-50 rounded-full flex items-center justify-center mb-4">
          <svg
            className="h-12 w-12 text-blue-500"
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
        <h3 className="text-lg font-medium text-gray-900 mb-2">
          No tenants found
        </h3>
        <p className="text-gray-500 mb-6">
          Try adjusting your search criteria or add new tenants.
        </p>
        {onAddTenant && (
          <button
            type="button"
            onClick={onAddTenant}
            className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
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
    <div className="bg-white shadow overflow-hidden sm:rounded-lg">
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th
                scope="col"
                className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
              >
                Tenant
              </th>
              <th
                scope="col"
                className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider"
              >
                Property
              </th>
              <th
                scope="col"
                className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider"
              >
                Unit
              </th>
              <th
                scope="col"
                className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider"
              >
                Email
              </th>
              <th
                scope="col"
                className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider"
              >
                Phone
              </th>
              <th
                scope="col"
                className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider"
              >
                Lease Duration
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
            {tenants.map((tenant) => {
              const leaseDuration = getLeaseDuration(tenant);
              const displayName = getTenantDisplayName(tenant);
              const subtitle = getTenantSubtitle(tenant);

              return (
                <tr
                  key={tenant.id}
                  className="hover:bg-gray-50 transition-colors duration-150"
                >
                  <td className="px-6 py-4 whitespace-nowrap text-left">
                    <div className="flex items-center justify-left">
                      <div className="flex-shrink-0 h-10 w-10">
                        <div className="h-10 w-10 rounded-full bg-gray-200 flex items-center justify-center">
                          <span className="text-gray-700 font-medium text-sm">
                            {getInitials(tenant)}
                          </span>
                        </div>
                      </div>
                      <div className="ml-4 text-left">
                        <div className="text-sm font-medium text-gray-900">
                          {displayName}
                        </div>
                        {subtitle && (
                          <div className="text-xs text-gray-500">
                            {subtitle}
                          </div>
                        )}
                        {tenant.tenant_type === "Company" && (
                          <div className="text-xs text-blue-600 font-medium">
                            Company
                          </div>
                        )}
                      </div>
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="text-sm text-gray-900 text-center">
                      {tenant.property?.name ??
                        tenant.unit?.property?.name ??
                        "--"}
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="text-sm text-gray-900 text-center">
                      {tenant.unit ? tenant.unit.name : "--"}
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="text-sm text-gray-900 text-center">
                      {tenant.email || "--"}
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="text-sm text-gray-900 text-center">
                      {tenant.phone || "--"}
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    {leaseDuration}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-center">
                    <span
                      className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${getStatusBadgeClass(
                        tenant.status
                      )}`}
                    >
                      {tenant.status || "Unknown"}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-center text-sm font-medium">
                    <div className="flex justify-center space-x-3">
                      <button
                        onClick={() => onEditTenant(tenant)}
                        className="text-blue-600 hover:text-blue-900 focus:outline-none transition-colors duration-150"
                      >
                        Edit
                      </button>
                      <button
                        onClick={() => onDeleteTenant(tenant.id)}
                        className="text-red-600 hover:text-red-900 focus:outline-none transition-colors duration-150"
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
