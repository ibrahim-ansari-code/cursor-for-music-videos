import React, { useState, useMemo, useEffect } from "react";
import { toast } from "react-toastify";
import * as Sentry from "@sentry/react";
import TenantModal from "../components/tenants/TenantModal";
import UpdateTenantModal from "../components/tenants/UpdateTenantModal";
import TenantTable from "../components/tenants/TenantTable";
import { TenantsTableSkeleton } from "../components/ui/skeletons";
import useDebounce from "../hooks/useDebounce";
import useFilteredTenants from "../hooks/useFilteredTenants";
import {
  countActiveLeases,
  getExpiringLeases,
  getInitials,
  formatDate,
} from "../utils/tenantUtils";
import {
  useTenants,
  useDeleteTenant,
  useBulkDeleteTenants,
} from "../hooks/useTenants";
import { useLeases } from "../hooks/useLeasesQueries";
import useDashboardData from "../hooks/useDashboardData";
import { useOutstandingPayments } from "../hooks/useAccountingQueries";
import { EnrichedTenant } from "../types/tenant";
import type { FetchTenantsParams } from "../utils/api/tenants";

type ActiveFilter = null | "active_leases" | "expiring" | "overdue";

interface Notification {
  type: "success" | "error";
  message: string;
}

const Tenants: React.FC = () => {
  // Local UI state
  const [searchTerm, setSearchTerm] = useState<string>("");
  const debouncedSearchTerm = useDebounce(searchTerm, 500);
  const [isModalOpen, setIsModalOpen] = useState<boolean>(false);
  const [isUpdateModalOpen, setIsUpdateModalOpen] = useState<boolean>(false);
  const [selectedTenant, setSelectedTenant] = useState<EnrichedTenant | null>(
    null
  );
  const [selectedTenants, setSelectedTenants] = useState<Set<number>>(
    new Set()
  );
  const [notification, setNotification] = useState<Notification | null>(null);
  const [activeFilter, setActiveFilter] = useState<ActiveFilter>(null); // null, 'active_leases', 'expiring', 'overdue'

  // Build query parameters
  const tenantParams = useMemo<FetchTenantsParams>(() => {
    const params: FetchTenantsParams = {};
    if (debouncedSearchTerm) {
      params.search = debouncedSearchTerm;
    }
    return params;
  }, [debouncedSearchTerm]);

  // TanStack Query hooks
  const {
    data: tenants = [],
    isLoading: tenantsLoading,
    error: tenantsError,
  } = useTenants(tenantParams);
  const {
    data: allLeases = [],
    isLoading: leasesLoading,
    error: leasesError,
  } = useLeases();
  const {
    data: dashData,
    loading: dashLoading,
    error: dashError,
  } = useDashboardData({
    propertyId: undefined,
    timePeriod: undefined,
    startDate: undefined,
    endDate: undefined,
  });
  const {
    data: outstandingPayments = [],
    isLoading: paymentsLoading,
    error: paymentsError,
  } = useOutstandingPayments();
  const deleteTenantMutation = useDeleteTenant();
  const bulkDeleteMutation = useBulkDeleteTenants();

  // Combine tenant and lease data
  const tenantsWithLeases = useMemo(() => {
    return tenants.map((tenant) => {
      const tenantLeases = allLeases.filter(
        (lease) => lease.tenant_id === tenant.id
      );
      // Map leases to match EnrichedTenant's expected Lease type
      const mappedLeases = tenantLeases.map((lease) => ({
        ...lease,
        monthly_rent:
          typeof lease.monthly_rent === "string"
            ? parseFloat(lease.monthly_rent) || 0
            : lease.monthly_rent,
        security_deposit:
          typeof lease.security_deposit === "string"
            ? parseFloat(lease.security_deposit) || 0
            : lease.security_deposit,
      }));
      return {
        ...tenant,
        leases: mappedLeases as any, // Type assertion needed due to type mismatch between lease types
      };
    });
  }, [tenants, allLeases]);

  // Calculate dashboard metrics
  const dashboardData = useMemo(() => {
    const activeLeaseCount = countActiveLeases(tenantsWithLeases);
    const expiringLeasesList = getExpiringLeases(tenantsWithLeases);

    return {
      totalTenants: tenants.length || 0,
      activeLeases: activeLeaseCount,
      expiringSoon: expiringLeasesList.length,
      overduePayments:
        outstandingPayments?.length || dashData?.payments_due?.length || 0,
    };
  }, [dashData, tenants, tenantsWithLeases, outstandingPayments]);

  const expiringLeases = useMemo(
    () => getExpiringLeases(tenantsWithLeases),
    [tenantsWithLeases]
  );

  // Filter tenants based on active filter using custom hook
  const filteredTenants = useFilteredTenants(
    tenantsWithLeases,
    activeFilter,
    expiringLeases,
    outstandingPayments
  );

  // Combined loading and error states
  const isLoading =
    tenantsLoading || leasesLoading || dashLoading || paymentsLoading;
  const error = tenantsError || leasesError || dashError || paymentsError;

  // Clear selection when filtered tenants change (e.g., after filter changes or deletion)
  useEffect(() => {
    const currentTenantIds = new Set(filteredTenants.map((t) => t.id));
    setSelectedTenants((prev) => {
      const filtered = Array.from(prev).filter((id) => currentTenantIds.has(id));
      return filtered.length !== prev.size ? new Set(filtered) : prev;
    });
  }, [filteredTenants]);

  const handleToggleSelectAll = () => {
    const allVisibleSelected =
      filteredTenants.length > 0 &&
      filteredTenants.every((tenant) => selectedTenants.has(tenant.id));

    if (allVisibleSelected) {
      setSelectedTenants(new Set());
    } else {
      setSelectedTenants(new Set(filteredTenants.map((t) => t.id)));
    }
  };

  const handleToggleSelect = (tenantId: number) => {
    setSelectedTenants((prev) => {
      const newSet = new Set(prev);
      if (newSet.has(tenantId)) {
        newSet.delete(tenantId);
      } else {
        newSet.add(tenantId);
      }
      return newSet;
    });
  };

  const handleBulkDelete = async () => {
    if (selectedTenants.size === 0) return;

    const tenantIdsArray = Array.from(selectedTenants);

    if (
      window.confirm(
        `Are you sure you want to delete ${tenantIdsArray.length} selected tenant${tenantIdsArray.length !== 1 ? "s" : ""}?`
      )
    ) {
      await Sentry.startSpan(
        {
          op: "ui.click",
          name: "Bulk Delete Tenants",
        },
        async (span) => {
          span.setAttribute("tenantCount", tenantIdsArray.length);
          span.setAttribute("tenantIds", tenantIdsArray.join(","));

          try {
            Sentry.logger.info("Bulk deleting tenants after confirmation", {
              tenantCount: tenantIdsArray.length,
              tenantIds: tenantIdsArray,
            });

            await bulkDeleteMutation.mutateAsync(tenantIdsArray);

            toast.success(
              `${tenantIdsArray.length} tenant${tenantIdsArray.length !== 1 ? "s" : ""} deleted successfully.`
            );

            Sentry.logger.info("Tenants bulk deleted successfully", {
              tenantCount: tenantIdsArray.length,
            });

            setSelectedTenants(new Set());
          } catch (err: any) {
            const errorMessage =
              err?.response?.data?.detail ||
              err?.message ||
              "Failed to delete selected tenants. They may have active leases or other associated data.";

            toast.error(errorMessage);

            Sentry.captureException(err, {
              tags: {
                component: "Tenants",
                action: "bulk_delete_tenants",
                feature: "tenants",
                operation: "bulk_delete",
              },
              contexts: {
                bulkDelete: {
                  tenantCount: tenantIdsArray.length,
                  tenantIds: tenantIdsArray,
                },
              },
            });

            throw err;
          }
        }
      );
    }
  };

  // Handle sending renewal email via email client
  const handleSendRenewal = (
    tenantName: string,
    tenantEmail: string | undefined,
    expiryDate: string,
    unitInfo: string
  ) => {
    if (!tenantEmail) {
      setNotification({
        type: "error",
        message: "This tenant doesn't have an email address.",
      });
      setTimeout(() => setNotification(null), 3000);
      return;
    }

    const formattedDate = new Date(expiryDate).toLocaleDateString();
    const subject = `Lease Renewal - ${unitInfo}`;
    const body = `Dear ${tenantName},\n\nYour lease for ${unitInfo} is set to expire on ${formattedDate}.\n\nWe wanted to reach out to discuss your renewal options. Please let us know if you would like to renew your lease.\n\nBest regards,\nProperty Management`;

    // Open email client with prefilled data
    window.location.href = `mailto:${tenantEmail}?subject=${encodeURIComponent(
      subject
    )}&body=${encodeURIComponent(body)}`;
  };

  // Handle adding a tenant
  const handleAddTenant = () => {
    setSelectedTenant(null);
    setIsModalOpen(true);
  };

  // Handle editing a tenant
  const handleEditTenant = (tenant: EnrichedTenant) => {
    setSelectedTenant(tenant);
    setIsUpdateModalOpen(true);
  };

  // Handle tenant save (create/update) - TanStack Query will auto-refresh
  const handleSaveTenant = async () => {
    // Close modals
    setIsModalOpen(false);
    setIsUpdateModalOpen(false);
    setSelectedTenant(null);
  };

  // Handle tenant deletion
  const handleDeleteTenant = async (tenantId: number) => {
    if (window.confirm("Are you sure you want to delete this tenant?")) {
      try {
        await deleteTenantMutation.mutateAsync(tenantId);
        toast.success("Tenant deleted successfully.");
      } catch (err: any) {
        const errorMessage =
          err?.response?.data?.detail ||
          err?.message ||
          "Failed to delete tenant. The tenant may have active leases or other associated data.";
        toast.error(errorMessage);
        console.error("Failed to delete tenant:", err);
      }
    }
  };

  // Handle search input
  const handleSearchChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setSearchTerm(e.target.value);
  };

  // Handle filter card clicks
  const handleFilterClick = (filterType: ActiveFilter) => {
    if (activeFilter === filterType) {
      setActiveFilter(null); // Clear filter if clicking the same one
    } else {
      setActiveFilter(filterType);
    }
  };

  return (
    <div className="p-6">
      {/* Summary Cards */}
      <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4 mb-6">
        {/* Total Tenants */}
        <div
          className="kpi-card cursor-pointer"
          onClick={() => setActiveFilter(null)}
        >
          <div className="flex items-center">
            <div
              className={`flex-shrink-0 ${
                activeFilter === null
                  ? "bg-indigo-100 dark:bg-indigo-900"
                  : "bg-indigo-50 dark:bg-indigo-900/50"
              } rounded-md p-3`}
            >
              <svg
                className="h-6 w-6 text-indigo-600 dark:text-indigo-400"
                xmlns="http://www.w3.org/2000/svg"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z"
                />
              </svg>
            </div>
            <div className="ml-5 w-0 flex-1">
              <dl>
                <dt className="text-sm font-medium text-gray-500 dark:text-gray-400 truncate">
                  Total Tenants
                </dt>
                <dd>
                  {isLoading ? (
                    <div className="animate-pulse h-6 w-8 bg-gray-200 dark:bg-gray-700 rounded transition-colors"></div>
                  ) : (
                    <div className="kpi-number">
                      {dashboardData.totalTenants}
                    </div>
                  )}
                </dd>
              </dl>
            </div>
          </div>
          {/* Tiny sparkline placeholder */}
          <div className="kpi-sparkline bg-gradient-to-r from-indigo-200 to-indigo-300 dark:from-indigo-800 rounded opacity-30 mt-3"></div>
        </div>

        {/* Active Leases */}
        <div
          className="kpi-card cursor-pointer"
          onClick={() => handleFilterClick("active_leases")}
        >
          <div className="flex items-center">
            <div
              className={`flex-shrink-0 ${
                activeFilter === "active_leases"
                  ? "bg-green-100 dark:bg-green-900"
                  : "bg-green-50 dark:bg-green-900/50"
              } rounded-md p-3`}
            >
              <svg
                className="h-6 w-6 text-green-600 dark:text-green-400"
                xmlns="http://www.w3.org/2000/svg"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
                />
              </svg>
            </div>
            <div className="ml-5 w-0 flex-1">
              <dl>
                <dt className="text-sm font-medium text-gray-500 dark:text-gray-400 truncate">
                  Active Leases
                </dt>
                <dd>
                  {isLoading ? (
                    <div className="animate-pulse h-6 w-8 bg-gray-200 dark:bg-gray-700 rounded transition-colors"></div>
                  ) : (
                    <div className="kpi-number">
                      {dashboardData.activeLeases}
                    </div>
                  )}
                </dd>
              </dl>
            </div>
          </div>
          {/* Tiny sparkline placeholder */}
          <div className="kpi-sparkline bg-gradient-to-r from-green-200 to-green-300 dark:from-green-800 rounded opacity-30 mt-3"></div>
        </div>

        {/* Expiring Soon */}
        <div
          className="kpi-card cursor-pointer"
          onClick={() => handleFilterClick("expiring")}
        >
          <div className="flex items-center">
            <div
              className={`flex-shrink-0 ${
                activeFilter === "expiring"
                  ? "bg-yellow-100 dark:bg-yellow-900"
                  : "bg-yellow-50 dark:bg-yellow-900/50"
              } rounded-md p-3`}
            >
              <svg
                className="h-6 w-6 text-yellow-600 dark:text-yellow-400"
                xmlns="http://www.w3.org/2000/svg"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
                />
              </svg>
            </div>
            <div className="ml-5 w-0 flex-1">
              <dl>
                <dt className="text-sm font-medium text-gray-500 dark:text-gray-400 truncate">
                  Expiring in 30 Days
                </dt>
                <dd>
                  {isLoading ? (
                    <div className="animate-pulse h-6 w-8 bg-gray-200 dark:bg-gray-700 rounded transition-colors"></div>
                  ) : (
                    <div className="kpi-number">
                      {dashboardData.expiringSoon}
                    </div>
                  )}
                </dd>
              </dl>
            </div>
          </div>
          {/* Tiny sparkline placeholder */}
          <div className="kpi-sparkline bg-gradient-to-r from-yellow-200 to-yellow-300 dark:from-yellow-800 rounded opacity-30 mt-3"></div>
        </div>

        {/* Overdue Payments */}
        <div
          className="kpi-card cursor-pointer"
          onClick={() => handleFilterClick("overdue")}
        >
          <div className="flex items-center">
            <div
              className={`flex-shrink-0 ${
                activeFilter === "overdue"
                  ? "bg-red-100 dark:bg-red-900"
                  : "bg-red-50 dark:bg-red-900/50"
              } rounded-md p-3`}
            >
              <svg
                className="h-6 w-6 text-red-600 dark:text-red-400"
                xmlns="http://www.w3.org/2000/svg"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                />
              </svg>
            </div>
            <div className="ml-5 w-0 flex-1">
              <dl>
                <dt className="text-sm font-medium text-gray-500 dark:text-gray-400 truncate">
                  Overdue Payments
                </dt>
                <dd>
                  {isLoading ? (
                    <div className="animate-pulse h-6 w-8 bg-gray-200 dark:bg-gray-700 rounded transition-colors"></div>
                  ) : (
                    <div className="kpi-number">
                      {dashboardData.overduePayments}
                    </div>
                  )}
                </dd>
              </dl>
            </div>
          </div>
          {/* Tiny sparkline placeholder */}
          <div className="kpi-sparkline bg-gradient-to-r from-red-200 to-red-300 dark:from-red-800 rounded opacity-30 mt-3"></div>
        </div>
      </div>

      {/* Notification */}
      {notification && (
        <div
          className={`mb-6 p-4 rounded-lg ${
            notification.type === "success"
              ? "bg-green-50 border border-green-200 text-green-700"
              : "bg-red-50 border border-red-200 text-red-700"
          }`}
        >
          <div className="flex items-center">
            <div className="flex-shrink-0">
              {notification.type === "success" ? (
                <svg
                  className="h-5 w-5 text-green-400"
                  viewBox="0 0 20 20"
                  fill="currentColor"
                  role="img"
                  aria-label="Success notification icon"
                >
                  <title>Success icon</title>
                  <path
                    fillRule="evenodd"
                    d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"
                    clipRule="evenodd"
                  />
                </svg>
              ) : (
                <svg
                  className="h-5 w-5 text-red-400"
                  viewBox="0 0 20 20"
                  fill="currentColor"
                  role="img"
                  aria-label="Error notification icon"
                >
                  <title>Error icon</title>
                  <path
                    fillRule="evenodd"
                    d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"
                    clipRule="evenodd"
                  />
                </svg>
              )}
            </div>
            <div className="ml-3">
              <p className="text-sm font-medium">{notification.message}</p>
            </div>
          </div>
        </div>
      )}

      {/* Tenant Directory - Moved section title directly above table */}
      <div className="mb-6">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-lg font-medium text-gray-900 dark:text-gray-100">
            Tenant Directory
          </h2>
          <div className="flex items-center gap-3">
            {selectedTenants.size > 0 && (
              <button
                type="button"
                onClick={handleBulkDelete}
                disabled={selectedTenants.size === 0}
                className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-red-600 hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500"
              >
                <svg
                  className="-ml-1 mr-2 h-5 w-5"
                  xmlns="http://www.w3.org/2000/svg"
                  viewBox="0 0 20 20"
                  fill="currentColor"
                >
                  <path
                    fillRule="evenodd"
                    d="M9 2a1 1 0 00-.894.553L7.382 4H4a1 1 0 000 2v10a2 2 0 002 2h8a2 2 0 002-2V6a1 1 0 100-2h-3.382l-.724-1.447A1 1 0 0011 2H9zM7 8a1 1 0 012 0v6a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v6a1 1 0 102 0V8a1 1 0 00-1-1z"
                    clipRule="evenodd"
                  />
                </svg>
                Delete Selected ({selectedTenants.size})
              </button>
            )}
            <button
              type="button"
              onClick={handleAddTenant}
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
            <div className="relative flex-1 min-w-[240px]">
              <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                <svg
                  className="h-5 w-5 text-gray-400 dark:text-gray-500"
                  xmlns="http://www.w3.org/2000/svg"
                  viewBox="0 0 20 20"
                  fill="currentColor"
                >
                  <path
                    fillRule="evenodd"
                    d="M8 4a4 4 0 100 8 4 4 0 000-8zM2 8a6 6 0 1110.89 3.476l4.817 4.817a1 1 0 01-1.414 1.414l-4.816-4.816A6 6 0 012 8z"
                    clipRule="evenodd"
                  />
                </svg>
              </div>
              <input
                type="text"
                placeholder="Search tenants..."
                value={searchTerm}
                onChange={handleSearchChange}
                className="block w-full pl-10 pr-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md leading-5 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 placeholder-gray-500 dark:placeholder-gray-400 focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
              />
            </div>
          </div>
        </div>

        {/* Error State */}
        {!isLoading && error && (
          <div className="bg-white dark:bg-gray-800 shadow overflow-hidden sm:rounded-lg">
            <div className="p-6 text-center">
              <div className="rounded-full bg-red-100 dark:bg-red-900 h-12 w-12 flex items-center justify-center mx-auto mb-4">
                <svg
                  className="h-6 w-6 text-red-600 dark:text-red-400"
                  xmlns="http://www.w3.org/2000/svg"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
                  />
                </svg>
              </div>
              <p className="text-red-600 dark:text-red-400">
                {error instanceof Error ? error.message : String(error)}
              </p>
            </div>
          </div>
        )}

        {/* Tenant Table Component */}
        {isLoading ? (
          <TenantsTableSkeleton rowCount={8} />
        ) : (
          <TenantTable
            tenants={filteredTenants}
            selectedTenants={Array.from(selectedTenants)}
            onToggleSelectAll={handleToggleSelectAll}
            onToggleSelect={handleToggleSelect}
            onEditTenant={handleEditTenant}
            onDeleteTenant={handleDeleteTenant}
            onAddTenant={handleAddTenant}
            isLoading={false}
          />
        )}
      </div>

      {/* Lease Expiry Warning */}
      {dashboardData.expiringSoon > 0 && (
        <div className="mt-6">
          <h2 className="text-lg font-medium text-gray-900 dark:text-gray-100 mb-4">
            Leases Expiring Soon
          </h2>
          <div className="bg-white dark:bg-gray-800 shadow overflow-hidden sm:rounded-lg mb-4">
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
                <thead className="bg-gray-50 dark:bg-gray-700">
                  <tr>
                    <th
                      scope="col"
                      className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider"
                    >
                      Tenant
                    </th>
                    <th
                      scope="col"
                      className="px-6 py-3 text-center text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider"
                    >
                      Unit
                    </th>
                    <th
                      scope="col"
                      className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider"
                    >
                      Expiry Date
                    </th>
                    <th
                      scope="col"
                      className="px-6 py-3 text-center text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider"
                    >
                      Days Remaining
                    </th>
                    <th
                      scope="col"
                      className="px-6 py-3 text-center text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider"
                    >
                      Actions
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
                  {expiringLeases.map((lease) => (
                    <tr
                      key={lease.leaseId}
                      className="hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors duration-150"
                    >
                      <td className="px-6 py-4 whitespace-nowrap text-left">
                        <div className="flex items-center">
                          <div className="flex-shrink-0 h-10 w-10">
                            <div className="h-10 w-10 rounded-full bg-gray-200 dark:bg-gray-600 flex items-center justify-center">
                              <span className="text-gray-700 dark:text-gray-200 font-medium">
                                {getInitials({ full_name: lease.tenantName })}
                              </span>
                            </div>
                          </div>
                          <div className="ml-4">
                            <div className="text-sm font-medium text-gray-900 dark:text-gray-100">
                              {lease.tenantName}
                            </div>
                          </div>
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="text-sm text-gray-900 dark:text-gray-100 text-center">
                          {lease.unitInfo || "--"}
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="text-sm text-gray-900 dark:text-gray-100 text-left">
                          {formatDate(lease.expiryDate)}
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-center">
                        <span
                          className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${
                            lease.daysRemaining <= 7
                              ? "bg-red-100 dark:bg-red-900 text-red-800 dark:text-red-200"
                              : lease.daysRemaining <= 14
                              ? "bg-yellow-100 dark:bg-yellow-900 text-yellow-800 dark:text-yellow-200"
                              : "bg-green-100 dark:bg-green-900 text-green-800 dark:text-green-200"
                          }`}
                        >
                          {lease.daysRemaining} days
                        </span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-center text-sm font-medium">
                        <div className="flex justify-center">
                          <button
                            onClick={() => {
                              // Find tenant from tenants list
                              const tenant = tenants.find(
                                (t) => t.id === lease.tenantId
                              );
                              const tenantEmail = tenant?.email;
                              handleSendRenewal(
                                lease.tenantName,
                                tenantEmail,
                                lease.expiryDate,
                                lease.unitInfo
                              );
                            }}
                            className="inline-flex items-center px-3 py-1.5 border border-transparent text-xs font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
                          >
                            <svg
                              className="h-4 w-4 mr-1"
                              fill="none"
                              viewBox="0 0 24 24"
                              stroke="currentColor"
                            >
                              <path
                                strokeLinecap="round"
                                strokeLinejoin="round"
                                strokeWidth={2}
                                d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"
                              />
                            </svg>
                            Send Reminder Email
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* Add Tenant Modal */}
      <TenantModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        onSave={handleSaveTenant}
        source="tenantsPage"
      />

      {/* Edit Tenant Modal */}
      <UpdateTenantModal
        isOpen={isUpdateModalOpen}
        onClose={() => setIsUpdateModalOpen(false)}
        tenant={selectedTenant}
        onSave={handleSaveTenant}
      />
    </div>
  );
};

export default Tenants;
