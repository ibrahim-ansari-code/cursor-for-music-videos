import React, { useState, useEffect, useCallback } from "react";
import { 
  getAccountingOverview, 
  fetchProperties, 
  fetchOutstandingPayments, 
  fetchRentTracker, 
  fetchReportSummary,
  fetchExpenses 
} from "../../utils/api";

import MonthlyMetricsCard from "../MonthlyMetricsCard";
import YTDCard from "../YTDCard";
import SnapshotCard from "../SnapshotCard";
import RevenueChart from "../RevenueChart";
import ExpenseBreakdownChart from "../ExpenseBreakdownChart";
import IncomeByPropertyCard from "../IncomeByPropertyCard";
import LoadingSpinner from "../LoadingSpinner";
import { useAccounting } from "./AccountingContext";

const OverviewTab = () => {
  const {
    overviewData,
    setOverviewData,
    accountingData,
    setAccountingData,
    incomeByPropertyData,
    setIncomeByPropertyData,
    loading,
    setLoading,
    error,
    setError,
    currentMonth,
    currentYear,
  } = useAccounting();

  // Local state for overview-specific data
  const [rentTrackerData, setRentTrackerData] = useState([]);
  const [selectedProperty, setSelectedProperty] = useState("all");
  const [properties, setProperties] = useState([]);
  const [currentExpenses, setCurrentExpenses] = useState([]);

  // Get overdue payments from rent tracker data
  const overduePayments = rentTrackerData.filter(
    (rent) => rent.status === "DUE" || rent.status === "PARTIAL"
  );

  const loadOverviewData = useCallback(async () => {
    try {
      const params = {};
      // Add property filter if selected
      if (selectedProperty !== "all") {
        params.property_id = selectedProperty;
      }
      
      const data = await getAccountingOverview(params);
      setOverviewData(data);

      // Update accounting data directly from backend response
      const newAccountingData = {
        monthly: {
          revenue: data.monthly_revenue,
          expenses: data.monthly_expenses,
          netIncome: data.monthly_net_income,
        },
        ytd: {
          revenue: data.ytd_revenue,
          expenses: data.ytd_expenses,
          netIncome: data.ytd_net_income,
        },
        snapshot: {
          occupancyRate: data.occupancy_rate,
          paidRent: accountingData.snapshot.paidRent, // This will be updated by rent tracker
          totalRent: accountingData.snapshot.totalRent, // This will be updated by rent tracker
          avgRent: data.average_rent,
        },
      };
      
      setAccountingData(newAccountingData);

      setError(null);
    } catch (err) {
      console.error("Error loading overview data:", err);
      // Check if it's a 404 error (no properties found for new users)
      if (
        err.status === 404 ||
        (err.data &&
          err.data.detail &&
          err.data.detail.includes("No accessible properties"))
      ) {
        // For new users with no properties, set default values
        setOverviewData({
          monthly_revenue: 0,
          monthly_expenses: 0,
          monthly_net_income: 0,
          ytd_revenue: 0,
          ytd_expenses: 0,
          ytd_net_income: 0,
          occupancy_rate: 0,
          average_rent: 0,
          revenue_trends: [],
        });

        setAccountingData({
          monthly: { revenue: 0, expenses: 0, netIncome: 0 },
          ytd: { revenue: 0, expenses: 0, netIncome: 0 },
          snapshot: { occupancyRate: 0, paidRent: 0, totalRent: 0, avgRent: 0 },
        });

        setError(null); // Clear error for new users
      } else {
        // Rethrow error to be handled by Promise.all
        throw err;
      }
    }
  }, [selectedProperty, setOverviewData, setAccountingData, setError]);

  const loadRentTrackerData = useCallback(async () => {
    try {
      const params = {
        month: currentMonth,
        year: currentYear,
      };
      
      // Add property filter if selected
      if (selectedProperty !== "all") {
        params.property_id = selectedProperty;
      }
      
      const data = await fetchRentTracker(params);
      setRentTrackerData(data);

      // Calculate paid and total rent
      const totalRent = data.length;
      const paidRent = data.filter((rent) => rent.status === "PAID").length;

      // Update accounting data with rent tracking information
      const updatedSnapshot = {
        paidRent,
        totalRent,
      };
      
      setAccountingData((prevData) => ({
        ...prevData,
        snapshot: {
          ...prevData.snapshot,
          ...updatedSnapshot,
        },
      }));
    } catch (err) {
      console.error("Error loading rent tracker data:", err);
      throw err;
    }
  }, [currentMonth, currentYear, selectedProperty, setAccountingData]);

  const loadOutstandingPayments = useCallback(async () => {
    try {
      const params = {};
      // Add property filter if selected
      if (selectedProperty !== "all") {
        params.property_id = selectedProperty;
      }
      
      const data = await fetchOutstandingPayments(params);
      // Data is used directly in overduePayments calculation, no need to store in state
    } catch (err) {
      console.error("Error loading outstanding payments:", err);
      throw err;
    }
  }, [selectedProperty]);

  const loadExpensesData = useCallback(async () => {
    try {
      const params = {};
      const today = new Date();
      const monthAgo = new Date(today);
      monthAgo.setMonth(monthAgo.getMonth() - 1);
      // Handle edge case where previous month has fewer days
      if (monthAgo.getDate() !== today.getDate()) {
        monthAgo.setDate(0); // Set to last day of previous month
      }
      params.start_date = monthAgo.toISOString().split("T")[0];
      params.end_date = today.toISOString().split("T")[0];

      // Add property filter if selected
      if (selectedProperty !== "all") {
        params.property_id = selectedProperty;
      }

      const data = await fetchExpenses(params);

      // Try to fetch property data for names, but don't fail if user has no properties
      let propertyMap = {};
      try {
        const propertiesData = await fetchProperties();
        // Set properties for the dropdown
        setProperties(propertiesData);
        // Map property IDs to names
        propertyMap = propertiesData.reduce((map, property) => {
          map[property.id] = property.name;
          return map;
        }, {});
      } catch (propErr) {
        console.log("No properties found, using property IDs instead of names");
        // Continue without property names
      }

      // Enhance expense data with property names and return for direct use
      const enhancedExpenses = data.map((expense) => ({
        ...expense,
        property_name:
          propertyMap[expense.property_id] ||
          `Property #${expense.property_id}`,
      }));

      return enhancedExpenses;
    } catch (err) {
      console.error("Error loading expenses data:", err);
      throw err;
    }
  }, [selectedProperty]);

  const loadIncomeByProperty = useCallback(async () => {
    try {
      // Always fetch current month data
      const reportParams = { date_range: "Current Month" };
      
      // Add property filter if selected
      if (selectedProperty !== "all") {
        reportParams.property_ids = [selectedProperty];
      }
      
      const reportData = await fetchReportSummary(reportParams);

      // Map the data to the format expected by IncomeByPropertyCard
      const mappedData = reportData.income_by_property.map((item) => ({
        id: item.property_id, // Use property_id as key
        name: item.property,
        monthlyIncome: item.monthly_income,
        occupancyRate: item.occupancy_rate,
      }));

      // Backend handles filtering, so directly set the data
      setIncomeByPropertyData(mappedData);
    } catch (err) {
      console.error("Error loading income by property data:", err);
      // Don't show error toast for new users who have no properties yet
      // Just set empty data silently
      setIncomeByPropertyData([]);
    }
  }, [selectedProperty, setIncomeByPropertyData]);

  // Load data on component mount and when property filter changes
  useEffect(() => {
    const loadAllData = async () => {
      try {
        setLoading(true);
        const [, , , expenses, ] = await Promise.all([
          loadOverviewData(),
          loadOutstandingPayments(),
          loadRentTrackerData(), 
          loadExpensesData(),
          loadIncomeByProperty()
        ]);
        // Store expenses in component state for chart usage
        setCurrentExpenses(expenses || []);
      } catch (err) {
        console.error("Error loading data:", err);
        setError("Failed to load accounting data. Please try refreshing.");
      } finally {
        setLoading(false);
      }
    };

    loadAllData();
  }, [selectedProperty]); // Re-run whenever selectedProperty changes

  if (loading) {
    return <LoadingSpinner message="Loading accounting data..." />;
  }

  return (
    <div className="space-y-6">
      {error && (
        <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded">
          <p>{error}</p>
          <button
            onClick={() => window.location.reload()}
            className="mt-2 bg-red-500 hover:bg-red-700 text-white font-bold py-1 px-2 rounded text-sm"
          >
            Retry
          </button>
        </div>
      )}

      {/* Property Filter Selector */}
      <div className="bg-white rounded-lg shadow-sm p-4">
        <div className="flex items-center space-x-4">
          <label htmlFor="propertyFilter" className="text-sm font-medium text-gray-700">
            Filter by Property:
          </label>
          <select
            id="propertyFilter"
            value={selectedProperty}
            onChange={(e) => setSelectedProperty(e.target.value)}
            className="block rounded-md border-gray-300 py-2 pl-3 pr-10 text-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
          >
            <option value="all">All Properties</option>
            {properties.map((property) => (
              <option key={property.id} value={property.id}>
                {property.name}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Financial Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <MonthlyMetricsCard data={accountingData.monthly} />
        <YTDCard data={accountingData.ytd} />
        <SnapshotCard data={accountingData.snapshot} />
      </div>

      {/* Charts Section */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Revenue Chart */}
        <div className="bg-white rounded-lg shadow-sm p-6 h-full">
          <div className="flex items-center mb-4">
            <h2 className="text-lg font-medium text-gray-800">
              Revenue Breakdown
              {selectedProperty !== "all" && (
                <span className="text-sm font-normal text-gray-500 ml-2">
                  ({properties.find(p => p.id.toString() === selectedProperty)?.name || "Selected Property"})
                </span>
              )}
            </h2>
          </div>
          <RevenueChart
            data={
              overviewData?.revenue_trends
                ? {
                    months: overviewData.revenue_trends.map(
                      (month) => month.period
                    ),
                    revenue: overviewData.revenue_trends.map(
                      (month) => month.revenue
                    ),
                    expenses: overviewData.revenue_trends.map(
                      (month) => month.expenses
                    ),
                    net_income: overviewData.revenue_trends.map(
                      (month) => month.net_income
                    ),
                  }
                : null
            }
          />
        </div>

        {/* Expense Breakdown Chart */}
        <div className="bg-white rounded-lg shadow-sm p-6 h-full">
          <div className="flex items-center mb-4">
            <h2 className="text-lg font-medium text-gray-800">
              Expense Breakdown
              {selectedProperty !== "all" && (
                <span className="text-sm font-normal text-gray-500 ml-2">
                  ({properties.find(p => p.id.toString() === selectedProperty)?.name || "Selected Property"})
                </span>
              )}
            </h2>
          </div>
          <ExpenseBreakdownChart expenses={currentExpenses} />
        </div>
      </div>

      {/* Occupancy & Outstanding Payments */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <IncomeByPropertyCard properties={incomeByPropertyData} />

        {/* Outstanding Payments Card */}
        <div className="bg-white rounded-lg shadow-sm p-6 h-full">
          <div className="flex items-center mb-4">
            <h2 className="text-lg font-medium text-gray-800">
              Outstanding Payments
              {selectedProperty !== "all" && (
                <span className="text-sm font-normal text-gray-500 ml-2">
                  ({properties.find(p => p.id.toString() === selectedProperty)?.name || "Selected Property"})
                </span>
              )}
            </h2>
            {overduePayments.length > 0 && (
              <span className="ml-2 bg-red-100 text-red-800 text-xs font-medium px-2 py-0.5 rounded-full">
                {overduePayments.length}
              </span>
            )}
          </div>

          {overduePayments.length > 0 ? (
            <div>
              <div className="border-b border-gray-200 mb-2">
                <div className="grid grid-cols-2 text-sm">
                  <div className="py-3 text-gray-500 font-medium uppercase tracking-wider">
                    Tenant
                  </div>
                  <div className="py-3 text-gray-500 font-medium uppercase tracking-wider text-right">
                    Amount Due
                  </div>
                </div>
              </div>
              <div className="space-y-1">
                {overduePayments.map((payment) => (
                  <div
                    key={payment.lease_id}
                    className="grid grid-cols-2 py-4 border-b border-gray-100 hover:bg-gray-50"
                  >
                    <div className="text-sm font-medium text-gray-900">
                      {payment.tenant_name}
                    </div>
                    <div className="text-sm font-medium text-gray-900 text-right">
                      ${Number.parseFloat(payment.remaining_due).toFixed(2)}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <div className="flex items-center justify-center h-40">
              <div className="text-center text-gray-500">
                <div className="text-3xl font-bold text-green-600">0</div>
                <p className="text-sm mt-2">All payments are up to date</p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default OverviewTab;