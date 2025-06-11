import React, { useEffect, useState } from "react";
import { toast } from "react-toastify";
import { fetchRentTracker } from "../utils/api";
import LoadingSpinner from "./LoadingSpinner";

const RentTracker = ({ onDataLoaded }) => {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [rentData, setRentData] = useState([]);
  const [searchTerm, setSearchTerm] = useState("");
  const [currentMonth, setCurrentMonth] = useState(new Date().getMonth() + 1); // JavaScript months are 0-indexed
  const [currentYear, setCurrentYear] = useState(new Date().getFullYear());

  // Function to load rent tracker data
  const loadRentTrackerData = async () => {
    try {
      setLoading(true);
      const data = await fetchRentTracker({
        month: currentMonth,
        year: currentYear,
      });
      setRentData(data);
      // Call the onDataLoaded callback if provided
      if (onDataLoaded && typeof onDataLoaded === "function") {
        onDataLoaded(data);
      }
      setError(null);
    } catch (err) {
      console.error("Error loading rent tracker data:", err);
      setError("Failed to load rent tracker data. Please try again.");
      toast.error("Failed to load rent tracker data");
    } finally {
      setLoading(false);
    }
  };

  // Load data on component mount and when month/year changes
  useEffect(() => {
    loadRentTrackerData();
    setSearchTerm(""); // Clear search when date changes
  }, [currentMonth, currentYear]);

  // Get proper CSS class for status badge
  const getStatusBadgeClass = (status) => {
    switch (status) {
      case "PAID":
        return "bg-green-100 text-green-800";
      case "PARTIAL":
        return "bg-yellow-100 text-yellow-800";
      case "DUE":
        return "bg-red-100 text-red-800";
      default:
        return "bg-gray-100 text-gray-800";
    }
  };

  // Generate month options for the dropdown
  const monthOptions = [
    { value: 1, label: "January" },
    { value: 2, label: "February" },
    { value: 3, label: "March" },
    { value: 4, label: "April" },
    { value: 5, label: "May" },
    { value: 6, label: "June" },
    { value: 7, label: "July" },
    { value: 8, label: "August" },
    { value: 9, label: "September" },
    { value: 10, label: "October" },
    { value: 11, label: "November" },
    { value: 12, label: "December" },
  ];

  // Generate year options (current year and 2 years back/forward)
  const currentYearNum = new Date().getFullYear();
  const yearOptions = [
    currentYearNum - 2,
    currentYearNum - 1,
    currentYearNum,
    currentYearNum + 1,
    currentYearNum + 2,
  ];

  // Filter rent data based on search term
  const filteredRentData = rentData.filter((rent) => {
    if (!searchTerm) return true;

    const searchLower = searchTerm.toLowerCase();
    return (
      rent.tenant_name?.toLowerCase().includes(searchLower) ||
      rent.property_name?.toLowerCase().includes(searchLower)
    );
  });

  if (loading) {
    return <LoadingSpinner message="Loading rent tracker..." />;
  }

  return (
    <div className="space-y-4">
      {/* Error message */}
      {error && (
        <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded">
          <p>{error}</p>
          <button
            onClick={loadRentTrackerData}
            className="mt-2 bg-red-500 hover:bg-red-700 text-white font-bold py-1 px-2 rounded text-sm"
          >
            Retry
          </button>
        </div>
      )}

      {/* Month and Year filters */}
      <div className="bg-white p-4 rounded-lg shadow-sm flex flex-col sm:flex-row sm:items-center sm:justify-between space-y-2 sm:space-y-0">
        <div className="flex flex-col sm:flex-row sm:space-x-4 space-y-2 sm:space-y-0">
          <div>
            <label
              htmlFor="month-filter"
              className="block text-sm font-medium text-gray-700 mb-1"
            >
              Month
            </label>
            <select
              id="month-filter"
              className="block w-full rounded-md border-gray-300 py-2 pl-3 pr-10 text-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
              value={currentMonth}
              onChange={(e) => setCurrentMonth(parseInt(e.target.value))}
            >
              {monthOptions.map((month) => (
                <option key={month.value} value={month.value}>
                  {month.label}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label
              htmlFor="year-filter"
              className="block text-sm font-medium text-gray-700 mb-1"
            >
              Year
            </label>
            <select
              id="year-filter"
              className="block w-full rounded-md border-gray-300 py-2 pl-3 pr-10 text-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
              value={currentYear}
              onChange={(e) => setCurrentYear(parseInt(e.target.value))}
            >
              {yearOptions.map((year) => (
                <option key={year} value={year}>
                  {year}
                </option>
              ))}
            </select>
          </div>
        </div>

        <div className="flex items-center">
          <div className="relative rounded-md shadow-sm">
            <input
              type="search"
              placeholder="Search tenants..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="focus:ring-blue-500 focus:border-blue-500 block w-full pl-10 pr-3 py-2 border-gray-300 rounded-md text-sm"
            />
            <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
              <i className="fas fa-search text-gray-400"></i>
            </div>
          </div>
        </div>
      </div>

      {/* Rent Tracker Table */}
      <div className="bg-white shadow rounded-lg overflow-hidden">
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
                  className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
                >
                  Property
                </th>
                <th
                  scope="col"
                  className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider"
                >
                  Monthly Rent
                </th>
                <th
                  scope="col"
                  className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider"
                >
                  Paid This Month
                </th>
                <th
                  scope="col"
                  className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider"
                >
                  Amount Due
                </th>
                <th
                  scope="col"
                  className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider"
                >
                  Status
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {filteredRentData.length > 0 ? (
                filteredRentData.map((rent) => (
                  <tr key={rent.lease_id} className="hover:bg-gray-50">
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="text-sm font-medium text-gray-900">
                        {rent.tenant_name}
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap max-w-xs">
                      <div
                        className="text-sm text-gray-900 truncate"
                        title={rent.property_name}
                      >
                        {rent.property_name?.length > 30
                          ? `${rent.property_name.substring(0, 30)}...`
                          : rent.property_name || "N/A"}
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-center">
                      <div className="text-sm text-gray-900">
                        ${Number.parseFloat(rent.monthly_rent || 0).toFixed(2)}
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-center">
                      <div className="text-sm text-gray-900">
                        ${Number.parseFloat(rent.amount_paid || 0).toFixed(2)}
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-center">
                      <div
                        className={`text-sm ${
                          Number.parseFloat(rent.remaining_due || 0) > 0
                            ? "text-red-600"
                            : "text-gray-500"
                        }`}
                      >
                        $
                        {Number.parseFloat(rent.remaining_due || 0) > 0
                          ? Number.parseFloat(rent.remaining_due).toFixed(2)
                          : "0.00"}
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-center">
                      <span
                        className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getStatusBadgeClass(
                          rent.status
                        )}`}
                      >
                        {rent.status}
                      </span>
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td
                    colSpan="6"
                    className="px-6 py-4 text-center text-sm text-gray-500"
                  >
                    {searchTerm
                      ? `No results found for "${searchTerm}"`
                      : "No rent tracking entries found"}
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

export default RentTracker;
