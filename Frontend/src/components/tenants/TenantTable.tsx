import React from "react";
import { useNavigate } from "react-router-dom";
import { getInitials, formatDate } from "../../utils/tenantUtils";
import { TenantTableProps, EnrichedTenant, PortalStatus } from "../../types/tenant";

// Types for lease-based status
type LeaseStatus = 'active' | 'expiring' | 'expired' | 'no_lease';

interface LeaseStatusInfo {
  status: LeaseStatus;
  label: string;
  bgClass: string;
  textClass: string;
  daysRemaining?: number;
}

const TenantTable: React.FC<TenantTableProps> = ({
  tenants,
  onAddTenant,
  isLoading,
  selectedTenants,
  onToggleSelectAll,
  onToggleSelect,
  overdueTenantIds = [],
}) => {
  const navigate = useNavigate();
  const selectAllRef = React.useRef<HTMLInputElement>(null);

  // Convert overdueTenantIds to Set for O(1) lookup
  const overdueSet = React.useMemo(() => new Set(overdueTenantIds), [overdueTenantIds]);

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

  // Helper function to determine lease-based status (replaces tenant.status)
  const getLeaseStatus = (tenant: EnrichedTenant): LeaseStatusInfo => {
    const today = new Date();
    today.setHours(0, 0, 0, 0);

    // No leases at all
    if (!tenant.leases || tenant.leases.length === 0) {
      return {
        status: 'no_lease',
        label: 'No Lease',
        bgClass: 'bg-gray-100 dark:bg-gray-900/30',
        textClass: 'text-gray-800 dark:text-gray-200',
      };
    }

    // Find current active lease (status = ACTIVE and within date range)
    const activeLease = tenant.leases.find((lease) => {
      if (!lease.start_date || !lease.end_date) return false;
      const startDate = new Date(lease.start_date);
      const endDate = new Date(lease.end_date);
      endDate.setHours(23, 59, 59, 999);
      if (isNaN(startDate.getTime()) || isNaN(endDate.getTime())) return false;
      return (
        lease.status?.toUpperCase() === "ACTIVE" &&
        startDate <= today &&
        endDate >= today
      );
    });

    if (activeLease) {
      // Check if lease is expiring within 30 days
      const endDate = new Date(activeLease.end_date);
      endDate.setHours(23, 59, 59, 999);
      const daysRemaining = Math.ceil((endDate.getTime() - today.getTime()) / (1000 * 60 * 60 * 24));

      if (daysRemaining <= 30) {
        return {
          status: 'expiring',
          label: 'Expiring',
          bgClass: 'bg-orange-100 dark:bg-orange-900/30',
          textClass: 'text-orange-800 dark:text-orange-200',
          daysRemaining,
        };
      }

      return {
        status: 'active',
        label: 'Active',
        bgClass: 'bg-green-100 dark:bg-green-900/30',
        textClass: 'text-green-800 dark:text-green-200',
      };
    }

    // No active lease - check if all leases are expired
    const allExpired = tenant.leases.every((lease) => {
      if (!lease.end_date) return false;
      const endDate = new Date(lease.end_date);
      endDate.setHours(23, 59, 59, 999);
      return endDate < today || lease.status?.toUpperCase() === "EXPIRED";
    });

    if (allExpired) {
      return {
        status: 'expired',
        label: 'Expired',
        bgClass: 'bg-red-100 dark:bg-red-900/30',
        textClass: 'text-red-800 dark:text-red-200',
      };
    }

    // Default: has leases but none are currently active (e.g., future lease)
    return {
      status: 'no_lease',
      label: 'Inactive',
      bgClass: 'bg-gray-100 dark:bg-gray-900/30',
      textClass: 'text-gray-800 dark:text-gray-200',
    };
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
                className="px-4 py-4 text-center font-semibold text-gray-700 dark:text-gray-300 bg-gray-50 dark:bg-gray-800"
              >
                Portal
              </th>
              <th
                scope="col"
                className="px-6 py-4 text-center font-semibold text-gray-700 dark:text-gray-300 bg-gray-50 dark:bg-gray-800"
              >
                Lease & Status
              </th>
            </tr>
          </thead>
          <tbody>
            {tenants.map((tenant) => {
              const leaseDuration = getLeaseDuration(tenant);
              const displayName = getTenantDisplayName(tenant);
              const subtitle = getTenantSubtitle(tenant);
              const leaseStatus = getLeaseStatus(tenant);
              const isOverdue = overdueSet.has(tenant.id);

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
                  <td className="px-4 py-4 whitespace-nowrap text-center">
                    {tenant.portal_status === PortalStatus.ACTIVE ? (
                      <span className="inline-flex items-center px-2 py-0.5 text-xs font-medium rounded-full bg-green-100 dark:bg-green-900/30 text-green-800 dark:text-green-200">
                        <svg className="w-3 h-3 mr-1" fill="currentColor" viewBox="0 0 20 20">
                          <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                        </svg>
                        Active
                      </span>
                    ) : tenant.portal_status === PortalStatus.INVITED ? (
                      <span className="inline-flex items-center px-2 py-0.5 text-xs font-medium rounded-full bg-blue-100 dark:bg-blue-900/30 text-blue-800 dark:text-blue-200">
                        <svg className="w-3 h-3 mr-1" fill="currentColor" viewBox="0 0 20 20">
                          <path d="M2.003 5.884L10 9.882l7.997-3.998A2 2 0 0016 4H4a2 2 0 00-1.997 1.884z" />
                          <path d="M18 8.118l-8 4-8-4V14a2 2 0 002 2h12a2 2 0 002-2V8.118z" />
                        </svg>
                        Invited
                      </span>
                    ) : tenant.portal_status === PortalStatus.REVOKED ? (
                      <span className="inline-flex items-center px-2 py-0.5 text-xs font-medium rounded-full bg-red-100 dark:bg-red-900/30 text-red-800 dark:text-red-200">
                        <svg className="w-3 h-3 mr-1" fill="currentColor" viewBox="0 0 20 20">
                          <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                        </svg>
                        Revoked
                      </span>
                    ) : (
                      <span className="text-gray-400 dark:text-gray-500 text-xs">--</span>
                    )}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-center">
                    <div className="flex flex-col items-center space-y-1">
                      {/* Overdue indicator - shown first (top priority) */}
                      {isOverdue && (
                        <span className="inline-flex items-center px-2 py-0.5 text-xs font-medium rounded-full bg-red-100 dark:bg-red-900/30 text-red-800 dark:text-red-200">
                          <svg className="w-3 h-3 mr-1" fill="currentColor" viewBox="0 0 20 20">
                            <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
                          </svg>
                          Overdue
                        </span>
                      )}
                      {/* Lease-based status badge */}
                      <span
                        className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${leaseStatus.bgClass} ${leaseStatus.textClass}`}
                      >
                        {leaseStatus.label}
                        {leaseStatus.daysRemaining !== undefined && (
                          <span className="ml-1">({leaseStatus.daysRemaining}d)</span>
                        )}
                      </span>
                      {leaseDuration && (
                        <div className="text-xs text-gray-500 dark:text-gray-400 text-center">
                          {leaseDuration}
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
    </div>
  );
};

export default TenantTable;
