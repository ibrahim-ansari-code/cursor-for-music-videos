import React, { useState, useEffect } from "react";
import RevenueChart from "./RevenueChart";
import {
  fetchDashboardData,
  fetchRentTracker,
  fetchTenants,
  fetchTenantsByProperty,
} from "../utils/api";
import LoadingSpinner from "./LoadingSpinner";

const Dashboard = () => {
  const [loading, setLoading] = useState(true);
  const [dashboardData, setDashboardData] = useState(null);
  const [prevPeriodData, setPrevPeriodData] = useState(null);
  const [rentData, setRentData] = useState([]);
  const [rentLoading, setRentLoading] = useState(true);
  const [selectedProperty, setSelectedProperty] = useState("all");
  const [timePeriod, setTimePeriod] = useState("month");
  const [properties, setProperties] = useState([]);
  const [error, setError] = useState(null);
  const [activeTab, setActiveTab] = useState("rent"); // 'rent' or 'invoices'
  const [tenantCount, setTenantCount] = useState(0);
  const [tenantsLoading, setTenantsLoading] = useState(true);

  //  Fetch list of properties for the dropdown
  useEffect(() => {
    const fetchProperties = async () => {
      try {
        const response = await fetch(
          `${import.meta.env.VITE_API_URL}/api/properties`,
          {
            headers: {
              Authorization: `Bearer ${localStorage.getItem("token")}`,
            },
          }
        );
        if (response.ok) {
          const data = await response.json();
          setProperties(data);
        }
      } catch (err) {
        console.error("Error fetching properties:", err);
      }
    };

    fetchProperties();
  }, []);

  // Calculate date range for previous period (for comparison)
  const getPreviousPeriodParams = () => {
    const today = new Date();
    let prevStartDate, prevEndDate;

    if (timePeriod === "month") {
      // Previous month
      const prevMonth = new Date(today.getFullYear(), today.getMonth() - 1);
      return {
        time_period: "month",
        property_id: selectedProperty !== "all" ? selectedProperty : undefined,
        prev_month: true,
      };
    } else if (timePeriod === "quarter") {
      // Previous quarter
      return {
        time_period: "quarter",
        property_id: selectedProperty !== "all" ? selectedProperty : undefined,
        prev_quarter: true,
      };
    } else if (timePeriod === "year") {
      // Previous year
      return {
        time_period: "year",
        property_id: selectedProperty !== "all" ? selectedProperty : undefined,
        prev_year: true,
      };
    }

    return {
      time_period: timePeriod,
      property_id: selectedProperty !== "all" ? selectedProperty : undefined,
      prev_period: true,
    };
  };

  // Calculate percentage change
  const calculatePercentChange = (current, previous) => {
    const currentNum = parseFloat(current);
    const previousNum = parseFloat(previous);

    if (isNaN(currentNum) || isNaN(previousNum)) {
      return 0;
    }

    if (previousNum === 0) {
      return currentNum > 0 ? 100 : currentNum < 0 ? -100 : 0;
    }

    return ((currentNum - previousNum) / previousNum) * 100;
  };

  // Fetch tenant count based on property selection
  useEffect(() => {
    const loadTenantData = async () => {
      try {
        setTenantsLoading(true);
        let count = 0;

        if (selectedProperty === "all") {
          // Fetch all tenants across properties
          const allTenants = await fetchTenants();
          count = allTenants.length;
        } else {
          // Fetch tenants for the selected property
          const propertyTenants = await fetchTenantsByProperty(
            selectedProperty
          );
          count = propertyTenants.length;
        }

        setTenantCount(count);
      } catch (err) {
        console.error("Error loading tenant data:", err);
        // Fallback to occupancy data if tenant fetch fails
        if (dashboardData?.occupancy) {
          setTenantCount(dashboardData.occupancy.occupied_units || 0);
        }
      } finally {
        setTenantsLoading(false);
      }
    };

    loadTenantData();
  }, [selectedProperty, dashboardData]);

  useEffect(() => {
    const loadDashboardData = async () => {
      try {
        setLoading(true);

        // Fetch current period data
        const data = await fetchDashboardData({
          property_id:
            selectedProperty !== "all" ? selectedProperty : undefined,
          time_period: timePeriod,
        });

        // Fetch previous period data for comparison
        const prevPeriodParams = getPreviousPeriodParams();
        const prevData = await fetchDashboardData(prevPeriodParams);

        setDashboardData(data);
        setPrevPeriodData(prevData);
        setError(null);
      } catch (err) {
        console.error("Error loading dashboard data:", err);
        setError(
          err.message || "Failed to load dashboard data. Please try again."
        );
        if (err.response) {
          console.error("Response:", await err.response.text());
        }
      } finally {
        setLoading(false);
      }
    };

    const loadRentTrackerData = async () => {
      try {
        setRentLoading(true);
        const currentDate = new Date();
        const data = await fetchRentTracker({
          month: currentDate.getMonth() + 1, // JavaScript months are 0-indexed
          year: currentDate.getFullYear(),
        });

        // Filter to only include entries with status 'DUE' or 'PARTIAL'
        const unpaidRents = data.filter(
          (rent) => rent.status === "DUE" || rent.status === "PARTIAL"
        );

        setRentData(unpaidRents);
      } catch (err) {
        console.error("Error loading rent tracker data:", err);
      } finally {
        setRentLoading(false);
      }
    };

    loadDashboardData();
    loadRentTrackerData();
  }, [selectedProperty, timePeriod]);

  // Format date function for the Due table
  const formatDueDate = (dueDay) => {
    const today = new Date();
    const dueDate = new Date(today.getFullYear(), today.getMonth(), dueDay);

    // If the due date has passed, format accordingly
    if (today.getDate() === dueDay) {
      return "Today";
    } else if (today.getDate() === dueDay + 1) {
      return "Yesterday";
    } else {
      return dueDate.toLocaleDateString("en-US", {
        month: "numeric",
        day: "numeric",
        year: "numeric",
      });
    }
  };

  // Get tenant initials
  const getTenantInitials = (name) => {
    if (!name) return "";
    return name
      .split(" ")
      .map((n) => n[0])
      .join("")
      .toUpperCase();
  };

  // Get avatar background color based on the first letter of tenant name
  const getAvatarColor = (name) => {
    if (!name) return "bg-gray-300";

    const colors = [
      "bg-green-500",
      "bg-blue-500",
      "bg-purple-500",
      "bg-indigo-500",
      "bg-pink-500",
      "bg-yellow-500",
      "bg-red-500",
      "bg-teal-500",
    ];

    const index = name.charCodeAt(0) % colors.length;
    return colors[index];
  };

  // Get percentage change for financial metrics
  const getRevenueChange = () => {
    if (!dashboardData?.summary || !prevPeriodData?.summary) return 0;
    return calculatePercentChange(
      dashboardData.summary.monthly_revenue,
      prevPeriodData.summary.monthly_revenue
    );
  };

  const getMaintenanceChange = () => {
    if (!dashboardData?.summary || !prevPeriodData?.summary) return 0;
    return calculatePercentChange(
      dashboardData.summary.maintenance_expenses,
      prevPeriodData.summary.maintenance_expenses
    );
  };

  if (loading && !dashboardData) {
    return <LoadingSpinner message="Loading dashboard data..." />;
  }

  if (error) {
    return (
      <div className="p-4">
        <div
          className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded relative"
          role="alert"
        >
          <strong className="font-bold">Error: </strong>
          <span className="block sm:inline">{error}</span>
          <button
            onClick={() => window.location.reload()}
            className="mt-2 bg-red-500 hover:bg-red-700 text-white font-bold py-1 px-2 rounded text-sm"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  // Calculate percentage changes
  const revenueChange = getRevenueChange();
  const maintenanceChange = getMaintenanceChange();

  return (
    <div className="space-y-6">
      <div className="flex flex-col md:flex-row md:items-center md:justify-between">
        <div className="mt-3 md:mt-0 flex space-x-3">
          <select
            className="border border-gray-300 rounded-md py-1.5 pl-3 pr-10 text-sm focus:outline-none focus:ring-1 focus:ring-blue-500"
            value={selectedProperty}
            onChange={(e) => setSelectedProperty(e.target.value)}
          >
            <option value="all">All Properties</option>
            {properties.map((property) => (
              <option key={property.id} value={property.id}>
                {property.name}
              </option>
            ))}
          </select>

          <select
            className="border border-gray-300 rounded-md py-1.5 pl-3 pr-10 text-sm focus:outline-none focus:ring-1 focus:ring-blue-500"
            value={timePeriod}
            onChange={(e) => setTimePeriod(e.target.value)}
          >
            <option value="month">This Month</option>
            <option value="quarter">This Quarter</option>
            <option value="year">This Year</option>
          </select>

          <button className="flex items-center px-3 py-1.5 bg-white border border-gray-300 rounded-md text-sm text-gray-700 hover:bg-gray-50">
            <i className="fas fa-cog mr-1.5"></i>
            Customize
          </button>
        </div>
      </div>

      {/* Financial Summary */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="dashboard-card">
          <h2 className="text-sm font-medium text-gray-500 mb-1">Revenue</h2>
          <div className="flex items-baseline">
            <p className="text-2xl font-semibold">
              $
              {dashboardData?.summary?.monthly_revenue?.toLocaleString() || "0"}
            </p>
            <span
              className={`ml-2 text-xs font-medium ${
                revenueChange >= 0 ? "text-green-600" : "text-red-600"
              }`}
            >
              <i
                className={`fas fa-arrow-${
                  revenueChange >= 0 ? "up" : "down"
                } mr-0.5`}
              ></i>
              {Math.abs(revenueChange).toFixed(1)}%
            </span>
          </div>
          <div className="text-xs text-gray-500 mt-1">
            Compared to previous {timePeriod}
          </div>
        </div>

        <div className="dashboard-card">
          <h2 className="text-sm font-medium text-gray-500 mb-1">
            Earned from Rent
          </h2>
          <div className="flex items-baseline">
            <p className="text-2xl font-semibold">
              $
              {dashboardData?.summary?.monthly_revenue?.toLocaleString() || "0"}
            </p>
            <span
              className={`ml-2 text-xs font-medium ${
                revenueChange >= 0 ? "text-green-600" : "text-red-600"
              }`}
            >
              <i
                className={`fas fa-arrow-${
                  revenueChange >= 0 ? "up" : "down"
                } mr-0.5`}
              ></i>
              {Math.abs(revenueChange).toFixed(1)}%
            </span>
          </div>
          <div className="text-xs text-gray-500 mt-1">
            Monthly recurring revenue
          </div>
        </div>

        <div className="dashboard-card">
          <h2 className="text-sm font-medium text-gray-500 mb-1">
            Spent on maintenance
          </h2>
          <div className="flex items-baseline">
            <p className="text-2xl font-semibold">
              $
              {dashboardData?.summary?.maintenance_expenses?.toLocaleString() ||
                "0"}
            </p>
            <span
              className={`ml-2 text-xs font-medium ${
                maintenanceChange <= 0 ? "text-green-600" : "text-orange-600"
              }`}
            >
              <i
                className={`fas fa-arrow-${
                  maintenanceChange <= 0 ? "down" : "up"
                } mr-0.5`}
              ></i>
              {Math.abs(maintenanceChange).toFixed(1)}%
            </span>
          </div>
          <div className="text-xs text-gray-500 mt-1">
            {selectedProperty === "all"
              ? `From ${
                  dashboardData?.summary?.total_properties || 0
                } properties`
              : "Current selection"}
          </div>
        </div>
      </div>

      {/* Stats & Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Payments Due */}
        <div className="dashboard-card">
          <h2 className="text-lg font-medium text-gray-900 mb-3">Due</h2>

          <div className="border-b border-gray-200">
            <nav className="-mb-px flex space-x-6">
              <button
                className={`py-2 px-1 border-b-2 ${
                  activeTab === "rent"
                    ? "border-blue-500 font-medium text-sm text-blue-600"
                    : "border-transparent font-medium text-sm text-gray-500 hover:text-gray-700 hover:border-gray-300"
                }`}
                onClick={() => setActiveTab("rent")}
              >
                Rent
              </button>
              <button
                className={`py-2 px-1 border-b-2 ${
                  activeTab === "invoices"
                    ? "border-blue-500 font-medium text-sm text-blue-600"
                    : "border-transparent font-medium text-sm text-gray-500 hover:text-gray-700 hover:border-gray-300"
                }`}
                onClick={() => setActiveTab("invoices")}
              >
                Invoices
              </button>
            </nav>
          </div>

          <div className="mt-3 overflow-hidden">
            <table className="min-w-full divide-y divide-gray-200">
              <thead>
                <tr>
                  <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Tenant
                  </th>
                  <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Amount
                  </th>
                  <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Date
                  </th>
                  <th className="px-4 py-2 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Reminder
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {activeTab === "rent" ? (
                  rentLoading ? (
                    <tr>
                      <td
                        colSpan="4"
                        className="px-4 py-4 text-center text-sm text-gray-500"
                      >
                        <div className="spinner block mx-auto mb-2 w-5 h-5" />
                        <p>Loading...</p>
                      </td>
                    </tr>
                  ) : rentData.length > 0 ? (
                    rentData.slice(0, 4).map((rent) => (
                      <tr key={rent.lease_id}>
                        <td className="px-4 py-3 whitespace-nowrap">
                          <div className="flex items-center justify-start">
                            <div
                              className={`flex-shrink-0 h-8 w-8 rounded-full ${getAvatarColor(
                                rent.tenant_name
                              )} flex items-center justify-center text-white font-medium`}
                            >
                              {getTenantInitials(rent.tenant_name)}
                            </div>
                            <div className="ml-3">
                              <p className="text-sm font-medium text-gray-900">
                                {rent.tenant_name}
                              </p>
                            </div>
                          </div>
                        </td>
                        <td className="px-4 py-3 whitespace-nowrap text-sm font-medium text-gray-900">
                          $
                          {rent.remaining_due > 0
                            ? rent.remaining_due.toLocaleString(undefined, {
                                minimumFractionDigits: 0,
                                maximumFractionDigits: 0,
                              })
                            : "0"}
                        </td>
                        <td className="px-4 py-3 whitespace-nowrap text-sm">
                          {rent.status === "DUE" ? (
                            <span className="text-gray-900">Today</span>
                          ) : (
                            <span className="text-red-600">Yesterday</span>
                          )}
                        </td>
                        <td className="px-4 py-3 whitespace-nowrap text-center">
                          <button className="h-8 w-8 rounded-full bg-gray-100 flex items-center justify-center text-gray-400 hover:text-gray-500 hover:bg-gray-200 transition-colors mx-auto">
                            <i className="far fa-bell"></i>
                          </button>
                        </td>
                      </tr>
                    ))
                  ) : (
                    <tr>
                      <td
                        colSpan="4"
                        className="px-4 py-4 text-center text-sm text-gray-500"
                      >
                        No pending payments
                      </td>
                    </tr>
                  )
                ) : (
                  <tr>
                    <td
                      colSpan="4"
                      className="px-4 py-4 text-center text-sm text-gray-500"
                    >
                      No pending invoices
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* Portfolio Overview */}
        <div className="dashboard-card">
          <h2 className="text-lg font-medium text-gray-900 mb-4">
            Portfolio Overview
          </h2>

          <div className="grid grid-cols-1 gap-6">
            <div className="grid grid-cols-3 gap-4">
              {/* Properties */}
              <div className="bg-white rounded-lg p-4 border border-gray-100 shadow-sm flex flex-col items-center justify-center">
                <div className="w-12 h-12 rounded-full bg-blue-100 flex items-center justify-center mb-3">
                  <i className="fas fa-building text-blue-500 text-lg"></i>
                </div>
                <p className="text-xl font-semibold">
                  {dashboardData?.summary?.total_properties || 0}
                </p>
                <p className="text-sm text-gray-500">Properties</p>
              </div>

              {/* Units */}
              <div className="bg-white rounded-lg p-4 border border-gray-100 shadow-sm flex flex-col items-center justify-center">
                <div className="w-12 h-12 rounded-full bg-green-100 flex items-center justify-center mb-3">
                  <i className="fas fa-home text-green-500 text-lg"></i>
                </div>
                <p className="text-xl font-semibold">
                  {dashboardData?.summary?.total_units || 0}
                </p>
                <p className="text-sm text-gray-500">Units</p>
              </div>

              {/* Tenants */}
              <div className="bg-white rounded-lg p-4 border border-gray-100 shadow-sm flex flex-col items-center justify-center">
                <div className="w-12 h-12 rounded-full bg-purple-100 flex items-center justify-center mb-3">
                  <i className="fas fa-users text-purple-500 text-lg"></i>
                </div>
                {tenantsLoading ? (
                  <div className="animate-pulse h-8 w-8 rounded-full bg-gray-200 mb-2"></div>
                ) : (
                  <p className="text-xl font-semibold">{tenantCount}</p>
                )}
                <p className="text-sm text-gray-500">Tenants</p>
              </div>
            </div>

            <div className="mt-2">
              <div className="flex justify-between items-center mb-2">
                <span className="text-sm font-medium text-gray-500">
                  Occupancy Rate
                </span>
                <span className="text-sm font-medium text-gray-900">
                  {Math.round(dashboardData?.occupancy?.occupancy_rate || 0)}%
                </span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-2">
                <div
                  className="bg-blue-500 h-2 rounded-full"
                  style={{
                    width: `${dashboardData?.occupancy?.occupancy_rate || 0}%`,
                  }}
                ></div>
              </div>
              <div className="flex justify-between text-xs text-gray-500 mt-1">
                <span>
                  {dashboardData?.occupancy?.occupied_units || 0} occupied
                </span>
                <span>
                  {dashboardData?.occupancy?.vacant_units || 0} vacant
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Revenue Chart */}
      <div className="dashboard-card">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-lg font-medium text-gray-900">Revenue Trends</h2>
          <div className="flex space-x-2">
            <div className="flex items-center">
              <div className="w-3 h-3 rounded-full bg-blue-500 mr-1"></div>
              <span className="text-xs text-gray-600">Revenue</span>
            </div>
            <div className="flex items-center">
              <div className="w-3 h-3 rounded-full bg-green-500 mr-1"></div>
              <span className="text-xs text-gray-600">Expenses</span>
            </div>
            <div className="flex items-center">
              <div className="w-3 h-3 rounded-full bg-purple-500 mr-1"></div>
              <span className="text-xs text-gray-600">Net Income</span>
            </div>
          </div>
        </div>

        <RevenueChart data={dashboardData?.revenue} />
      </div>
    </div>
  );
};

export default Dashboard;
