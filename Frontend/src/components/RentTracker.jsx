import React, { useEffect, useState, useMemo } from "react";
import { toast } from "react-toastify";
import { 
  fetchRentTracker, 
  fetchRentTrackerSummary,
  formatCurrency
} from "../utils/api/rentTracker";
import { fetchProperties } from "../utils/api/properties";
import { sanitizeTenantName, sanitizePropertyName } from "../utils/sanitization";
import { RentTrackerSkeleton } from "./ui/skeletons";
import NewPaymentModal from "./accounting/modals/NewPaymentModal";
import RentTrackerVirtualTable from "./RentTrackerVirtualTable";
import ErrorBoundary from "./ui/ErrorBoundary";

const RentTracker = ({ onDataLoaded }) => {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [rentData, setRentData] = useState([]);
  const [summary, setSummary] = useState(null);
  const [properties, setProperties] = useState([]);
  const [propertiesMap, setPropertiesMap] = useState(new Map());
  
  // Filters
  const [searchTerm, setSearchTerm] = useState("");
  const [currentMonth, setCurrentMonth] = useState(new Date().getMonth() + 1);
  const [currentYear, setCurrentYear] = useState(new Date().getFullYear());
  const [selectedProperty, setSelectedProperty] = useState("");
  const [selectedStatus, setSelectedStatus] = useState("");
  const [showSummary, setShowSummary] = useState(true);
  
  // Payment Modal State
  const [showPaymentModal, setShowPaymentModal] = useState(false);
  const [paymentInitialData, setPaymentInitialData] = useState({});

  // Load properties for filter dropdown and create lookup map
  useEffect(() => {
    const loadProperties = async () => {
      try {
        const data = await fetchProperties();
        const propertiesArray = Array.isArray(data) ? data : [];
        setProperties(propertiesArray);
        
        // Create Map for O(1) property lookup by name
        const propMap = new Map();
        propertiesArray.forEach(property => {
          propMap.set(property.name, property);
        });
        setPropertiesMap(propMap);
      } catch (err) {
        console.error("Error loading properties:", err);
      }
    };
    loadProperties();
  }, []);

  // Function to load rent tracker data
  const loadRentTrackerData = async () => {
    try {
      setLoading(true);
      
      // Build query parameters
      const params = {
        month: currentMonth,
        year: currentYear,
      };
      
      if (selectedProperty) {
        params.property_id = selectedProperty;
      }
      
      if (selectedStatus) {
        params.rent_status = selectedStatus;
      }

      // Fetch both data and summary
      const [data, summaryData] = await Promise.all([
        fetchRentTracker(params),
        fetchRentTrackerSummary(params)
      ]);
      
      setRentData(Array.isArray(data) ? data : []);
      setSummary(summaryData);
      
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

  // Load data when filters change
  useEffect(() => {
    loadRentTrackerData();
    setSearchTerm(""); // Clear search when filters change
  }, [currentMonth, currentYear, selectedProperty, selectedStatus]);

  // Month options for dropdown
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

  // Year options
  const currentYearNum = new Date().getFullYear();
  const yearOptions = [
    currentYearNum - 2,
    currentYearNum - 1,
    currentYearNum,
    currentYearNum + 1,
    currentYearNum + 2,
  ];

  // Status options
  const statusOptions = [
    { value: "", label: "All Statuses" },
    { value: "PAID", label: "Paid" },
    { value: "PARTIAL", label: "Partial" },
    { value: "DUE", label: "Due" },
    { value: "OVERDUE", label: "Overdue" },
  ];

  // Filter and sort rent data
  const filteredRentData = useMemo(() => {
    let filtered = rentData;
    
    if (searchTerm) {
      const searchLower = searchTerm.toLowerCase();
      filtered = filtered.filter((rent) => 
        rent.tenant_name?.toLowerCase().includes(searchLower) ||
        rent.property_name?.toLowerCase().includes(searchLower) ||
        rent.unit_name?.toLowerCase().includes(searchLower)
      );
    }
    
    return filtered;
  }, [rentData, searchTerm]);

  // Format date for display
  const formatDate = (dateString) => {
    if (!dateString) return "N/A";
    const date = new Date(dateString);
    return date.toLocaleDateString("en-US", { 
      month: "short", 
      day: "numeric", 
      year: "numeric" 
    });
  };
  
  // Handle Record Payment button click
  const handleRecordPayment = (rent) => {
    // Use Map for O(1) property lookup
    const property = propertiesMap.get(rent.property_name);
    
    // Safely coerce numeric fields to prevent NaN
    const remainingDueNum = Number.parseFloat(rent?.remaining_due ?? 0);
    const monthlyRentNum = Number.parseFloat(rent?.monthly_rent ?? 0);
    const amountVal = remainingDueNum > 0 ? remainingDueNum : monthlyRentNum;
    
    // Guard against out-of-range currentMonth to prevent accessing undefined
    const monthIndex = Math.min(Math.max(currentMonth - 1, 0), monthOptions.length - 1);
    
    setPaymentInitialData({
      property_id: property?.id || "",
      property_name: rent.property_name || "",
      tenant_id: rent.tenant_id || "",
      tenant_name: rent.tenant_name || "",
      amount: Number.isFinite(amountVal) ? amountVal.toString() : "0",
      lease_id: rent.lease_id || "",
      notes: `Rent payment for ${monthOptions[monthIndex].label} ${currentYear}`,
      payment_date: new Date().toISOString().split("T")[0],
      status: "Paid",
      payment_method: "Other"
    });
    setShowPaymentModal(true);
  };
  
  // Handle payment success
  const handlePaymentSuccess = () => {
    setShowPaymentModal(false);
    setPaymentInitialData({});
    loadRentTrackerData(); // Reload data to reflect the new payment
    toast.success("Payment recorded successfully");
  };

  if (loading) {
    return <RentTrackerSkeleton rowCount={6} />;
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

      {/* Summary Cards */}
      {showSummary && summary && (
        <div className="grid gap-4" style={{gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))"}}>
          <div className="bg-white p-4 rounded-lg shadow-sm">
            <div className="text-sm text-gray-500">Total Expected</div>
            <div className="text-xl mt-1 font-bold text-gray-900">
              {formatCurrency(summary.total_expected)}
            </div>
          </div>
          
          <div className="bg-white p-4 rounded-lg shadow-sm">
            <div className="text-sm text-gray-500">Total Collected</div>
            <div className="text-xl mt-1 font-bold text-green-600">
              {formatCurrency(summary.total_collected)}
            </div>
          </div>
          
          <div className="bg-white p-4 rounded-lg shadow-sm">
            <div className="text-sm text-gray-500">Outstanding</div>
            <div className="text-xl mt-1 font-bold text-red-600">
              {formatCurrency(summary.total_outstanding)}
            </div>
          </div>
          
          <div className="bg-white p-4 rounded-lg shadow-sm">
            <div className="text-sm text-gray-500">Collection Rate</div>
            <div className="text-xl mt-1 font-bold text-blue-600">
              {summary.collection_rate}%
            </div>
          </div>
          
          <div className="bg-white p-4 rounded-lg shadow-sm">
            <div className="text-sm text-gray-500 mb-2">Status Breakdown</div>
            <div className="flex gap-2 mt-1">
              <div className="flex-1 text-center">
                <span className="inline-block w-full text-xs font-medium bg-green-100 text-green-800 px-2 py-2 rounded whitespace-nowrap">
                  {summary.units_paid} Paid
                </span>
              </div>
              <div className="flex-1 text-center">
                <span className="inline-block w-full text-xs font-medium bg-yellow-100 text-yellow-800 px-2 py-2 rounded whitespace-nowrap">
                  {summary.units_partial} Partial
                </span>
              </div>
              <div className="flex-1 text-center">
                <span className="inline-block w-full text-xs font-medium bg-red-100 text-red-800 px-2 py-2 rounded whitespace-nowrap">
                  {summary.units_overdue} Overdue
                </span>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Filters */}
      <div className="bg-white p-4 rounded-lg shadow-sm">
        {/* Action Buttons */}
        <div className="flex justify-between items-center mb-4">
          <button
            onClick={() => setShowSummary(!showSummary)}
            className="text-sm text-blue-600 hover:text-blue-800"
          >
            {showSummary ? "Hide" : "Show"} Summary
          </button>
          
          <div className="space-x-3">
            <button
              onClick={() => toast.info("Export feature coming soon!")}
              className="inline-flex items-center px-4 py-2 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
            >
              <i className="fas fa-download mr-2"></i>
              Export CSV
            </button>
            <button
              onClick={() => toast.info("PDF export coming soon!")}
              className="inline-flex items-center px-4 py-2 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
            >
              <i className="fas fa-file-pdf mr-2"></i>
              Export PDF
            </button>
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-6 gap-4">
          {/* Month Filter */}
          <div>
            <label htmlFor="month-filter" className="block text-sm font-medium text-gray-700 mb-1">
              Month
            </label>
            <select
              id="month-filter"
              className="block w-full rounded-md border-gray-300 shadow-sm focus:ring-blue-500 focus:border-blue-500 text-sm"
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

          {/* Year Filter */}
          <div>
            <label htmlFor="year-filter" className="block text-sm font-medium text-gray-700 mb-1">
              Year
            </label>
            <select
              id="year-filter"
              className="block w-full rounded-md border-gray-300 shadow-sm focus:ring-blue-500 focus:border-blue-500 text-sm"
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

          {/* Property Filter */}
          <div>
            <label htmlFor="property-filter" className="block text-sm font-medium text-gray-700 mb-1">
              Property
            </label>
            <select
              id="property-filter"
              className="block w-full rounded-md border-gray-300 shadow-sm focus:ring-blue-500 focus:border-blue-500 text-sm"
              value={selectedProperty}
              onChange={(e) => setSelectedProperty(e.target.value)}
            >
              <option value="">All Properties</option>
              {properties.map((property) => (
                <option key={property.id} value={property.id}>
                  {property.name}
                </option>
              ))}
            </select>
          </div>

          {/* Status Filter */}
          <div>
            <label htmlFor="status-filter" className="block text-sm font-medium text-gray-700 mb-1">
              Status
            </label>
            <select
              id="status-filter"
              className="block w-full rounded-md border-gray-300 shadow-sm focus:ring-blue-500 focus:border-blue-500 text-sm"
              value={selectedStatus}
              onChange={(e) => setSelectedStatus(e.target.value)}
            >
              {statusOptions.map((status) => (
                <option key={status.value} value={status.value}>
                  {status.label}
                </option>
              ))}
            </select>
          </div>

          {/* Search */}
          <div className="sm:col-span-2 lg:col-span-2 xl:col-span-2">
            <label htmlFor="search" className="block text-sm font-medium text-gray-700 mb-1">
              Search
            </label>
            <div className="relative">
              <input
                type="search"
                id="search"
                placeholder="Search tenants, properties, units..."
                value={searchTerm}
                onChange={(e) => {
                  // Sanitize search input to prevent XSS
                  const sanitizedValue = e.target.value.replace(/[<>]/g, '');
                  setSearchTerm(sanitizedValue);
                }}
                className="block w-full rounded-md border-gray-300 shadow-sm pl-10 focus:ring-blue-500 focus:border-blue-500 text-sm"
              />
              <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                <i className="fas fa-search text-gray-400"></i>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Rent Tracker Table with Virtual Scrolling */}
      <ErrorBoundary
        title="Table Display Error"
        message="There was an issue displaying the rent tracker table. Please try refreshing or contact support if the issue persists."
        onError={(error, errorInfo) => {
          console.error("RentTrackerVirtualTable error:", error, errorInfo);
        }}
        onReset={() => {
          // Optionally reload data on reset
          loadRentTrackerData();
        }}
      >
        <RentTrackerVirtualTable
          rentData={filteredRentData}
          formatDate={formatDate}
          handleRecordPayment={handleRecordPayment}
          searchTerm={searchTerm}
        />
      </ErrorBoundary>
      
      {/* Payment Modal */}
      <NewPaymentModal
        isOpen={showPaymentModal}
        onClose={() => {
          setShowPaymentModal(false);
          setPaymentInitialData({});
        }}
        onSuccess={handlePaymentSuccess}
        initialData={paymentInitialData}
      />
    </div>
  );
};

export default RentTracker;