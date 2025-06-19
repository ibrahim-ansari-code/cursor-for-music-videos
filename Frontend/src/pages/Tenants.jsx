import React, { useState, useEffect } from "react";
import {
  fetchTenants,
  deleteTenant,
  fetchDashboardData,
  fetchOutstandingPayments,
  fetchLeases,
} from "../utils/api";
import TenantModal from "../components/TenantModal";
import UpdateTenantModal from "../components/UpdateTenantModal";
import LoadingSpinner from "../components/LoadingSpinner";
import useDebounce from "../hooks/useDebounce";
import {
    countActiveLeases,
    getExpiringLeases,
    getInitials,
    formatDate,
    getStatusBadgeClass,
} from "../utils/tenantUtils";

const Tenants = () => {
  const [tenants, setTenants] = useState([]);
  const [allLeases, setAllLeases] = useState([]);
  const [dashboardData, setDashboardData] = useState({
    totalTenants: 0,
    activeLeases: 0,
    expiringSoon: 0,
    overduePayments: 0,
  });
  const [expiringLeases, setExpiringLeases] = useState([]);
  const [searchTerm, setSearchTerm] = useState("");
  const debouncedSearchTerm = useDebounce(searchTerm, 500);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isUpdateModalOpen, setIsUpdateModalOpen] = useState(false);
  const [selectedTenant, setSelectedTenant] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  const [notification, setNotification] = useState(null);
  const [actionMenuOpen, setActionMenuOpen] = useState(null);
  const [leasesLoaded, setLeasesLoaded] = useState(false);

  // Fetch all leases once on component mount
  useEffect(() => {
    const fetchAllLeases = async () => {
      try {
        const leasesData = await fetchLeases();
        setAllLeases(leasesData);
      } catch (err) {
        console.error("Failed to fetch leases:", err);
        setError((prevError) => prevError || "Failed to load lease data.");
      } finally {
        setLeasesLoaded(true);
      }
    };
    fetchAllLeases();
  }, []);

  // Fetch tenants and dashboard data
  useEffect(() => {
    if (!leasesLoaded) {
      return;
    }

    const fetchData = async () => {
      setIsLoading(true);
      setError(null);
      try {
        // Fetch tenants
        const tenantParams = {};
        if (debouncedSearchTerm) {
          tenantParams.search = debouncedSearchTerm;
        }

        const tenantsData = await fetchTenants(tenantParams);

        // Combine tenant and lease data
        const tenantsWithLeases = tenantsData.map((tenant) => {
          // Find all leases belonging to this tenant
          const tenantLeases = allLeases.filter(
            (lease) => lease.tenant_id === tenant.id
          );
          // Return a new tenant object with leases array
          return {
            ...tenant,
            leases: tenantLeases,
          };
        });

        setTenants(tenantsWithLeases);

        // Check active leases count based on tenant leases
        const activeLeaseCount = countActiveLeases(tenantsWithLeases);

        // Check expiring leases count and get the list
        const expiringLeasesList = getExpiringLeases(tenantsWithLeases);
        setExpiringLeases(expiringLeasesList);

        // Try to fetch dashboard data from API
        try {
          const dashData = await fetchDashboardData();

          // Try to fetch outstanding payments data
          let overduePayments = 0;
          try {
            const outstandingPayments = await fetchOutstandingPayments();
            overduePayments = outstandingPayments?.length || 0;
          } catch (paymentsError) {
            console.warn("Failed to fetch overdue payments:", paymentsError);
          }

          setDashboardData({
            totalTenants:
              dashData.summary?.total_tenants || tenantsData.length || 0,
            activeLeases: activeLeaseCount,
            expiringSoon: expiringLeasesList.length,
            overduePayments:
              overduePayments || dashData.payments_due?.length || 0,
          });
        } catch (dashError) {
          console.warn(
            "Failed to fetch dashboard data, using tenant data for counts:",
            dashError
          );

          // Try to fetch just the overdue payments if main dashboard failed
          let overduePayments = 0;
          try {
            const outstandingPayments = await fetchOutstandingPayments();
            overduePayments = outstandingPayments?.length || 0;
          } catch (paymentsError) {
            console.warn("Failed to fetch overdue payments:", paymentsError);
          }

          // Calculate dashboard data from tenant list if API call fails
          setDashboardData({
            totalTenants: tenantsData.length,
            activeLeases: activeLeaseCount,
            expiringSoon: expiringLeasesList.length,
            overduePayments: overduePayments,
          });
        }
      } catch (err) {
        console.error("Error fetching data:", err);
        console.error("Error details:", err.response || err.message || err);
        setError("Failed to load data. Please check console for details.");

        // Set empty data on error
        setTenants([]);
        setExpiringLeases([]);
        setDashboardData({
          totalTenants: 0,
          activeLeases: 0,
          expiringSoon: 0,
          overduePayments: 0,
        });
      } finally {
        setIsLoading(false);
      }
    };

    fetchData();
  }, [debouncedSearchTerm, leasesLoaded]);

  // Handle sending renewal email via email client
  const handleSendRenewal = (tenantName, tenantEmail, expiryDate, unitInfo) => {
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
  const handleEditTenant = (tenant) => {
    setSelectedTenant(tenant);
    setIsUpdateModalOpen(true);
  };

  // Handle tenant save (create/update)
  const handleSaveTenant = async (savedTenant) => {
    try {
      // Refresh tenants list
      const updatedTenants = await fetchTenants();
      setTenants(updatedTenants);

      // Update dashboard counts
      setDashboardData((prev) => ({
        ...prev,
        totalTenants: updatedTenants.length,
        activeLeases: countActiveLeases(updatedTenants),
        expiringSoon: getExpiringLeases(updatedTenants).length,
      }));

      // Close modals
      setIsModalOpen(false);
      setIsUpdateModalOpen(false);
      setSelectedTenant(null);
    } catch (err) {
      console.error("Failed to refresh tenant data:", err);
    }
  };

  // Handle tenant deletion
  const handleDeleteTenant = async (tenantId) => {
    if (window.confirm("Are you sure you want to delete this tenant?")) {
      try {
        await deleteTenant(tenantId);
        // Refresh tenants list
        const updatedTenants = await fetchTenants();
        setTenants(updatedTenants);

        // Update dashboard counts
        setDashboardData((prev) => ({
          ...prev,
          totalTenants: updatedTenants.length,
          activeLeases: countActiveLeases(updatedTenants),
          expiringSoon: getExpiringLeases(updatedTenants).length,
        }));
      } catch (err) {
        console.error("Failed to delete tenant:", err);
        // Display the specific error message from the backend if available
        if (err.data && err.data.detail) {
          setError(err.data.detail);
        } else {
          setError("Failed to delete tenant. Please try again.");
        }
      }
    }
    // Close action menu
    setActionMenuOpen(null);
  };

  // Handle search input
  const handleSearchChange = (e) => {
    setSearchTerm(e.target.value);
  };

  return (
    <div className="p-6">
      {/* Summary Cards */}
      <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4 mb-6">
        {/* Total Tenants */}
        <div className="bg-white overflow-hidden shadow rounded-lg">
          <div className="px-4 py-5 sm:p-6">
            <div className="flex items-center">
              <div className="flex-shrink-0 bg-indigo-100 rounded-md p-3">
                <svg
                  className="h-6 w-6 text-indigo-600"
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
                  <dt className="text-sm font-medium text-gray-500 truncate">
                    Total Tenants
                  </dt>
                  <dd>
                    <div className="text-lg font-medium text-gray-900">
                      {isLoading ? "..." : dashboardData.totalTenants}
                    </div>
                  </dd>
                </dl>
              </div>
            </div>
          </div>
        </div>

        {/* Active Leases */}
        <div className="bg-white overflow-hidden shadow rounded-lg">
          <div className="px-4 py-5 sm:p-6">
            <div className="flex items-center">
              <div className="flex-shrink-0 bg-green-100 rounded-md p-3">
                <svg
                  className="h-6 w-6 text-green-600"
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
                  <dt className="text-sm font-medium text-gray-500 truncate">
                    Active Leases
                  </dt>
                  <dd>
                    <div className="text-lg font-medium text-gray-900">
                      {isLoading ? "..." : dashboardData.activeLeases}
                    </div>
                  </dd>
                </dl>
              </div>
            </div>
          </div>
        </div>

        {/* Expiring Soon */}
        <div className="bg-white overflow-hidden shadow rounded-lg">
          <div className="px-4 py-5 sm:p-6">
            <div className="flex items-center">
              <div className="flex-shrink-0 bg-yellow-100 rounded-md p-3">
                <svg
                  className="h-6 w-6 text-yellow-600"
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
                  <dt className="text-sm font-medium text-gray-500 truncate">
                    Expiring in 30 Days
                  </dt>
                  <dd>
                    <div className="text-lg font-medium text-gray-900">
                      {isLoading ? "..." : dashboardData.expiringSoon}
                    </div>
                  </dd>
                </dl>
              </div>
            </div>
          </div>
        </div>

        {/* Overdue Payments */}
        <div className="bg-white overflow-hidden shadow rounded-lg">
          <div className="px-4 py-5 sm:p-6">
            <div className="flex items-center">
              <div className="flex-shrink-0 bg-red-100 rounded-md p-3">
                <svg
                  className="h-6 w-6 text-red-600"
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
                  <dt className="text-sm font-medium text-gray-500 truncate">
                    Overdue Payments
                  </dt>
                  <dd>
                    <div className="text-lg font-medium text-gray-900">
                      {isLoading ? "..." : dashboardData.overduePayments}
                    </div>
                  </dd>
                </dl>
              </div>
            </div>
          </div>
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
          <h2 className="text-lg font-medium text-gray-900">
            Tenant Directory
          </h2>
          <div className="flex items-center gap-3">
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
                  className="h-5 w-5 text-gray-400"
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
                className="block w-full pl-10 pr-3 py-2 border border-gray-300 rounded-md leading-5 bg-white placeholder-gray-500 focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
              />
            </div>
          </div>
        </div>

        {/* Loading State */}
        {isLoading && <LoadingSpinner message="Loading tenants..." />}

        {/* Error State */}
        {!isLoading && error && (
          <div className="bg-white shadow overflow-hidden sm:rounded-lg">
            <div className="p-6 text-center">
              <div className="rounded-full bg-red-100 h-12 w-12 flex items-center justify-center mx-auto mb-4">
                <svg
                  className="h-6 w-6 text-red-600"
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
              <p className="text-red-600">{error}</p>
            </div>
          </div>
        )}

        {/* Empty State - Only show when not loading, no error, and no tenants */}
        {!isLoading && !error && tenants.length === 0 && (
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
              No tenants yet
            </h3>
            <p className="text-gray-500 mb-6">
              Start by adding your first tenant.
            </p>
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
          </div>
        )}

        {/* Tenant Table - Only show when not loading, no error, and tenants exist */}
        {!isLoading && !error && tenants.length > 0 && (
          <div className="bg-white shadow overflow-hidden sm:rounded-lg">
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th
                      scope="col"
                      className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
                    >
                      Name
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
                  {tenants.map((tenant) => (
                    <tr
                      key={tenant.id}
                      className="hover:bg-gray-50 transition-colors duration-150"
                    >
                      <td className="px-6 py-4 whitespace-nowrap text-left">
                        <div className="flex items-center justify-left">
                          <div className="flex-shrink-0 h-10 w-10">
                            <div className="h-10 w-10 rounded-full bg-gray-200 flex items-center justify-center">
                              <span className="text-gray-700 font-medium">
                                {getInitials(tenant)}
                              </span>
                            </div>
                          </div>
                          <div className="ml-4 text-left">
                            <div className="text-sm font-medium text-gray-900">
                              {tenant.first_name} {tenant.last_name}
                            </div>
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
                            onClick={() => handleEditTenant(tenant)}
                            className="text-blue-600 hover:text-blue-900 focus:outline-none"
                          >
                            Edit
                          </button>
                          <button
                            onClick={() => handleDeleteTenant(tenant.id)}
                            className="text-red-600 hover:text-red-900 focus:outline-none"
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
          </div>
        )}
      </div>

      {/* Lease Expiry Warning */}
      {dashboardData.expiringSoon > 0 && (
        <div className="mt-6">
          <h2 className="text-lg font-medium text-gray-900 mb-4">
            Leases Expiring Soon
          </h2>
          <div className="bg-white shadow overflow-hidden sm:rounded-lg mb-4">
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
                      Unit
                    </th>
                    <th
                      scope="col"
                      className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
                    >
                      Expiry Date
                    </th>
                    <th
                      scope="col"
                      className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider"
                    >
                      Days Remaining
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
                  {expiringLeases.map((lease) => (
                    <tr
                      key={lease.leaseId}
                      className="hover:bg-gray-50 transition-colors duration-150"
                    >
                      <td className="px-6 py-4 whitespace-nowrap text-left">
                        <div className="flex items-center">
                          <div className="flex-shrink-0 h-10 w-10">
                            <div className="h-10 w-10 rounded-full bg-gray-200 flex items-center justify-center">
                              <span className="text-gray-700 font-medium">
                                {getInitials({ full_name: lease.tenantName })}
                              </span>
                            </div>
                          </div>
                          <div className="ml-4">
                            <div className="text-sm font-medium text-gray-900">
                              {lease.tenantName}
                            </div>
                          </div>
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="text-sm text-gray-900 text-center">
                          {lease.unitInfo || "--"}
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="text-sm text-gray-900 text-left">
                          {formatDate(lease.expiryDate)}
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-center">
                        <span
                          className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${
                            lease.daysRemaining <= 7
                              ? "bg-red-100 text-red-800"
                              : lease.daysRemaining <= 14
                              ? "bg-yellow-100 text-yellow-800"
                              : "bg-green-100 text-green-800"
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
