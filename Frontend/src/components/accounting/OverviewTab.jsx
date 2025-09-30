import React, { useState, useEffect, useCallback, useMemo } from "react";
import MonthlyMetricsCard from "./cards/MonthlyMetricsCard";
import YTDCard from "./cards/YTDCard";
import SnapshotCard from "./cards/SnapshotCard";
import RevenueChart from "../charts/RevenueChart";
import ExpenseBreakdownChart from "../charts/ExpenseBreakdownChart";
import IncomeByPropertyChart from "../charts/IncomeByPropertyChart";
import { FinancialCardSkeleton, ChartSkeleton } from "../ui/skeletons";
import { SkeletonLine } from "../ui/skeletons/SkeletonPrimitives";
import { useAccounting } from "./AccountingContext";
import {
  useAccountingOverview,
  useOutstandingPayments,
  useExpenses,
  useReportSummary,
  useRentTracker,
} from "../../hooks/useAccountingQueries";
import useProperties from "../../hooks/useProperties";

const OverviewTab = () => {
  const {
    overviewData,
    setOverviewData,
    accountingData,
    setAccountingData,
    incomeByPropertyData,
    setIncomeByPropertyData,
    currentMonth,
    currentYear,
  } = useAccounting();

  // Local state
  const [selectedProperty, setSelectedProperty] = useState("all");

  // Query parameters based on selected property
  const queryParams = useMemo(() => {
    const params = {};
    if (selectedProperty !== "all") {
      params.property_id = selectedProperty;
    }
    return params;
  }, [selectedProperty]);

  // Expense query parameters (last month)
  const expenseParams = useMemo(() => {
    const params = { ...queryParams };
    const today = new Date();
    const monthAgo = new Date();
    monthAgo.setMonth(today.getMonth() - 1);
    params.start_date = monthAgo.toISOString().split("T")[0];
    params.end_date = today.toISOString().split("T")[0];
    return params;
  }, [queryParams]);

  // Report summary parameters
  const reportParams = useMemo(() => {
    const params = { date_range: "Current Month" };
    if (selectedProperty !== "all") {
      params.property_ids = [selectedProperty];
    }
    return params;
  }, [selectedProperty]);

  // Rent tracker parameters
  const rentTrackerParams = useMemo(() => {
    const params = {
      month: currentMonth,
      year: currentYear,
    };
    if (selectedProperty !== "all") {
      params.property_id = selectedProperty;
    }
    return params;
  }, [selectedProperty, currentMonth, currentYear]);

  // TanStack Query hooks
  const { data: overviewQueryData, isLoading: overviewLoading, error: overviewError } = useAccountingOverview(queryParams);
  const { data: outstandingPayments = [], isLoading: paymentsLoading, error: paymentsError } = useOutstandingPayments(queryParams);
  const { data: expensesResponse, isLoading: expensesLoading, error: expensesError } = useExpenses(expenseParams);
  const { properties, loading: propertiesLoading, error: propertiesError } = useProperties();
  const { data: reportData, isLoading: reportLoading, error: reportError } = useReportSummary(reportParams);
  const { data: rentTrackerData = [], isLoading: rentTrackerLoading, error: rentTrackerError } = useRentTracker(rentTrackerParams);

  // Extract expenses from paginated response and enhance with property names
  const expenses = useMemo(() => {
    const expensesList = expensesResponse?.items || [];
    
    // Create property map for names
    const propertyMap = (properties || []).reduce((map, property) => {
      map[property.id] = property.name;
      return map;
    }, {});

    // Enhance expense data with property names
    return expensesList.map((expense) => ({
      ...expense,
      property_name:
        propertyMap[expense.property_id] ||
        `Property #${expense.property_id}`,
    }));
  }, [expensesResponse, properties]);

  // Combine all loading states
  const loading = overviewLoading || paymentsLoading || expensesLoading || propertiesLoading || reportLoading || rentTrackerLoading;

  // Combine all error states  
  const error = overviewError || paymentsError || expensesError || propertiesError || reportError || rentTrackerError;

  // Memoize the total outstanding amount calculation
  const totalOutstandingAmount = useMemo(() => {
    return outstandingPayments
      .reduce((sum, payment) => sum + Number.parseFloat(payment.amount || 0), 0)
      .toFixed(2);
  }, [outstandingPayments]);

  // Memoize processed overview data to prevent unnecessary re-renders
  const processedOverviewData = useMemo(() => {
    if (!overviewQueryData) return null;
    return {
      monthly: {
        revenue: Number(overviewQueryData.monthly_revenue) || 0,
        expenses: Number(overviewQueryData.monthly_expenses) || 0,
        netIncome: Number(overviewQueryData.monthly_net_income) || 0,
      },
      ytd: {
        revenue: Number(overviewQueryData.ytd_revenue) || 0,
        expenses: Number(overviewQueryData.ytd_expenses) || 0,
        netIncome: Number(overviewQueryData.ytd_net_income) || 0,
      },
      snapshot: {
        occupancyRate: Number(overviewQueryData.occupancy_rate) || 0,
        avgRent: Number(overviewQueryData.average_rent) || 0,
      },
    };
  }, [overviewQueryData]);

  // Update context state when processed data changes
  useEffect(() => {
    if (processedOverviewData) {
      setOverviewData(overviewQueryData);

      // Update accounting data from processed data
      setAccountingData(prev => ({
        ...processedOverviewData,
        snapshot: {
          ...processedOverviewData.snapshot,
          paidRent: prev.snapshot.paidRent, // Keep existing value, will be updated by rent tracker
          totalRent: prev.snapshot.totalRent, // Keep existing value, will be updated by rent tracker
        },
      }));
    }
  }, [processedOverviewData, overviewQueryData]);

  // Update income by property data when report data changes
  useEffect(() => {
    if (reportData?.income_by_property) {
      const mappedData = reportData.income_by_property.map((item) => ({
        id: item.property_id,
        name: item.property,
        monthlyIncome: item.monthly_income,
        occupancyRate: item.occupancy_rate,
      }));
      setIncomeByPropertyData(mappedData);
    }
  }, [reportData, setIncomeByPropertyData]);

  // Memoize rent calculations to avoid unnecessary re-renders
  const rentStats = useMemo(() => {
    if (!rentTrackerData) return { totalRent: 0, paidRent: 0 };
    
    const totalRent = rentTrackerData.length;
    const paidRent = rentTrackerData.filter(
      (entry) => entry.status === "PAID" || entry.status === "PARTIAL"
    ).length;
    
    return { totalRent, paidRent };
  }, [rentTrackerData]);

  // Update snapshot with rent tracker data only when values actually change
  useEffect(() => {
    if (rentTrackerData && rentStats.totalRent > 0) {
      setAccountingData((prev) => {
        // Only update if values have actually changed
        if (prev.snapshot.paidRent !== rentStats.paidRent || 
            prev.snapshot.totalRent !== rentStats.totalRent) {
          return {
            ...prev,
            snapshot: {
              ...prev.snapshot,
              paidRent: rentStats.paidRent,
              totalRent: rentStats.totalRent,
            },
          };
        }
        return prev;
      });
    }
  }, [rentStats.paidRent, rentStats.totalRent]);

  if (loading) {
    return (
      <div className="space-y-6">
        {/* Property Filter Skeleton - Match actual component height */}
        <div className="dark-panel dark-shadow rounded-lg hover:shadow-md transition-shadow duration-200 p-4" style={{minHeight: "72px"}}>
          <div className="flex items-center space-x-4">
            <SkeletonLine width="120px" height="1rem" />
            <SkeletonLine width="200px" height="2.5rem" rounded="md" />
          </div>
        </div>

        {/* Financial Summary Cards Skeleton - Match actual card heights */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {/* Monthly Metrics Card */}
          <div className="dark-panel dark-shadow rounded-lg hover:shadow-md transition-shadow duration-200 p-6" style={{minHeight: "140px"}}>
            <div className="flex items-center justify-between mb-4">
              <SkeletonLine width="100px" height="1.25rem" />
              <SkeletonLine width="60px" height="1rem" rounded="full" />
            </div>
            <div className="grid grid-cols-3 gap-4">
              <div>
                <SkeletonLine width="60px" height="0.875rem" className="mb-2" />
                <SkeletonLine width="80px" height="1.5rem" />
              </div>
              <div>
                <SkeletonLine width="70px" height="0.875rem" className="mb-2" />
                <SkeletonLine width="80px" height="1.5rem" />
              </div>
              <div>
                <SkeletonLine width="80px" height="0.875rem" className="mb-2" />
                <SkeletonLine width="80px" height="1.5rem" />
              </div>
            </div>
          </div>
          
          {/* YTD Card */}
          <div className="dark-panel dark-shadow rounded-lg hover:shadow-md transition-shadow duration-200 p-6" style={{minHeight: "140px"}}>
            <div className="flex items-center justify-between mb-4">
              <SkeletonLine width="120px" height="1.25rem" />
              <SkeletonLine width="60px" height="1rem" rounded="full" />
            </div>
            <div className="grid grid-cols-3 gap-4">
              <div>
                <SkeletonLine width="60px" height="0.875rem" className="mb-2" />
                <SkeletonLine width="90px" height="1.5rem" />
              </div>
              <div>
                <SkeletonLine width="70px" height="0.875rem" className="mb-2" />
                <SkeletonLine width="80px" height="1.5rem" />
              </div>
              <div>
                <SkeletonLine width="80px" height="0.875rem" className="mb-2" />
                <SkeletonLine width="90px" height="1.5rem" />
              </div>
            </div>
          </div>
          
          {/* Snapshot Card */}
          <div className="dark-panel dark-shadow rounded-lg hover:shadow-md transition-shadow duration-200 p-6" style={{minHeight: "140px"}}>
            <div className="flex items-center justify-between mb-4">
              <SkeletonLine width="80px" height="1.25rem" />
              <SkeletonLine width="60px" height="1rem" rounded="full" />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <SkeletonLine width="100px" height="0.875rem" className="mb-2" />
                <SkeletonLine width="60px" height="1.5rem" />
              </div>
              <div>
                <SkeletonLine width="70px" height="0.875rem" className="mb-2" />
                <SkeletonLine width="50px" height="1.5rem" />
              </div>
            </div>
            <div className="mt-4">
              <SkeletonLine width="80px" height="0.875rem" className="mb-2" />
              <SkeletonLine width="120px" height="1.5rem" />
            </div>
          </div>
        </div>

        {/* Charts Section Skeleton */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Revenue Chart Skeleton */}
          <div className="dark-panel dark-shadow rounded-lg hover:shadow-md transition-shadow duration-200 p-6" style={{minHeight: "400px"}}>
            <div className="flex items-center mb-4">
              <SkeletonLine width="180px" height="1.5rem" />
            </div>
            <ChartSkeleton height="300px" barCount={6} />
          </div>

          {/* Expense Chart Skeleton */}
          <div className="dark-panel dark-shadow rounded-lg hover:shadow-md transition-shadow duration-200 p-6" style={{minHeight: "400px"}}>
            <div className="flex items-center mb-4">
              <SkeletonLine width="160px" height="1.5rem" />
            </div>
            <div className="h-[300px] flex items-center justify-center">
          <div className="w-48 h-48 rounded-full bg-gray-200 dark:bg-gray-700 animate-pulse"></div>
            </div>
          </div>
        </div>

        {/* Occupancy & Outstanding Payments Section Skeleton */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Income by Property Chart Skeleton */}
          <div className="dark-panel dark-shadow rounded-lg hover:shadow-md transition-shadow duration-200 p-6" style={{minHeight: "400px"}}>
            <div className="flex items-center mb-4">
              <SkeletonLine width="140px" height="1.5rem" />
            </div>
            <ChartSkeleton height="300px" barCount={4} />
          </div>

          {/* Outstanding Payments Card Skeleton */}
          <div className="dark-panel dark-shadow rounded-lg hover:shadow-md transition-shadow duration-200 p-6 flex flex-col" style={{minHeight: "400px"}}>
            <div className="flex items-center mb-4">
              <SkeletonLine width="180px" height="1.5rem" />
              <SkeletonLine width="24px" height="20px" rounded="full" className="ml-2" />
            </div>
            
            {/* Table Header Skeleton */}
            <div className="dark-divider border-b mb-2">
              <div className="grid grid-cols-12 text-sm">
                <div className="col-span-5 py-3">
                  <SkeletonLine width="60px" height="0.75rem" />
                </div>
                <div className="col-span-3 py-3">
                  <SkeletonLine width="50px" height="0.75rem" className="mx-auto" />
                </div>
                <div className="col-span-4 py-3">
                  <SkeletonLine width="80px" height="0.75rem" className="ml-auto" />
                </div>
              </div>
            </div>
            
            {/* Payment Rows Skeleton */}
            <div className="overflow-y-auto pr-1 custom-scrollbar min-h-[200px] max-h-[350px]">
              {[...Array(4)].map((_, i) => (
                <div key={i} className="grid grid-cols-12 py-3 dark-divider border-b hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors duration-150">
                  <div className="col-span-5">
                    <SkeletonLine width="85%" height="1rem" className="mb-1" />
                    <SkeletonLine width="65%" height="0.75rem" />
                  </div>
                  <div className="col-span-3 flex justify-center">
                    <SkeletonLine width="60px" height="1.25rem" rounded="full" />
                  </div>
                  <div className="col-span-4 text-right pr-2">
                    <SkeletonLine width="75px" height="1rem" className="ml-auto" />
                  </div>
                </div>
              ))}
            </div>
            
            {/* Total Outstanding Skeleton */}
            <div className="mt-4 pt-3 dark-divider border-t">
              <div className="grid grid-cols-12 items-center">
                <div className="col-span-5">
                  <SkeletonLine width="120px" height="1rem" />
                </div>
                <div className="col-span-3"></div>
                <div className="col-span-4 text-right pr-2">
                  <SkeletonLine width="90px" height="1.25rem" className="ml-auto" />
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {error && (
        <div className="bg-red-100 dark:bg-red-900/20 border border-red-400 dark:border-red-700 text-red-700 dark:text-red-400 px-4 py-3 rounded">
          <p>{error.message || error.toString() || 'An error occurred while loading data'}</p>
          <button
            onClick={() => window.location.reload()}
            className="mt-2 bg-red-500 dark:bg-red-600 hover:bg-red-700 dark:hover:bg-red-500 text-white font-bold py-1 px-2 rounded text-sm"
          >
            Retry
          </button>
        </div>
      )}

      {/* Property Filter Selector */}
      <div className="dark-panel dark-shadow rounded-lg hover:shadow-md transition-shadow duration-200 p-4">
        <div className="flex items-center space-x-4">
          <label
            htmlFor="propertyFilter"
            className="text-sm font-medium text-gray-700 dark:text-gray-300"
          >
            Filter by Property:
          </label>
          <select
            id="propertyFilter"
            value={selectedProperty}
            onChange={(e) => setSelectedProperty(e.target.value)}
            className="dark-input block rounded-md py-2 pl-3 pr-10 text-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
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
        <div className="dark-panel dark-shadow rounded-lg hover:shadow-md transition-shadow duration-200 p-6 h-full">
          <div className="flex items-center mb-4">
            <h2 className="text-lg font-medium text-gray-800 dark:text-gray-200">
              Revenue Breakdown
              {selectedProperty !== "all" && (
                <span className="text-sm font-normal text-gray-500 dark:text-gray-400 ml-2">
                  (
                  {properties.find((p) => p.id.toString() === selectedProperty)
                    ?.name || "Selected Property"}
                  )
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
                    (month) => Number(month.revenue) || 0
                  ),
                  expenses: overviewData.revenue_trends.map(
                    (month) => Number(month.expenses) || 0
                  ),
                }
                : null
            }
          />
        </div>

        {/* Expense Breakdown Chart */}
        <div className="dark-panel dark-shadow rounded-lg hover:shadow-md transition-shadow duration-200 p-6 h-full">
          <div className="flex items-center mb-4">
            <h2 className="text-lg font-medium text-gray-800 dark:text-gray-200">
              Expense Breakdown (Last 30 Days)
              {selectedProperty !== "all" && (
                <span className="text-sm font-normal text-gray-500 dark:text-gray-400 ml-2">
                  (
                  {properties.find((p) => p.id.toString() === selectedProperty)
                    ?.name || "Selected Property"}
                  )
                </span>
              )}
            </h2>
          </div>
          <ExpenseBreakdownChart expenses={expenses} />
        </div>
      </div>

      {/* Occupancy & Outstanding Payments */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Income by Property Chart */}
        <div className="dark-panel dark-shadow rounded-lg hover:shadow-md transition-shadow duration-200 p-6 h-full">
          <div className="flex items-center mb-4">
            <h2 className="text-lg font-medium text-gray-800 dark:text-gray-200">
              Income by Property
              {selectedProperty !== "all" && (
                <span className="text-sm font-normal text-gray-500 dark:text-gray-400 ml-2">
                  (
                  {properties.find((p) => p.id.toString() === selectedProperty)
                    ?.name || "Selected Property"}
                  )
                </span>
              )}
            </h2>
          </div>
          <IncomeByPropertyChart properties={incomeByPropertyData} />
        </div>

        {/* Outstanding Payments Card */}
        <div className="dark-panel dark-shadow rounded-lg hover:shadow-md transition-shadow duration-200 p-6 h-full flex flex-col">
          <div className="flex items-center mb-4">
            <h2 className="text-lg font-medium text-gray-800 dark:text-gray-200">
              Outstanding Payments
              {selectedProperty !== "all" && (
                <span className="text-sm font-normal text-gray-500 dark:text-gray-400 ml-2">
                  (
                  {properties.find((p) => p.id.toString() === selectedProperty)
                    ?.name || "Selected Property"}
                  )
                </span>
              )}
            </h2>
            {outstandingPayments.length > 0 && (
              <span className="ml-2 bg-red-100 dark:bg-red-900/20 text-red-800 dark:text-red-400 text-xs font-medium px-2 py-0.5 rounded-full">
                {outstandingPayments.length}
              </span>
            )}
          </div>

          {outstandingPayments.length > 0 ? (
            <div className="flex-1 flex flex-col">
              <div className="dark-divider border-b mb-2">
                <div className="grid grid-cols-12 text-sm">
                  <div className="col-span-5 py-3 text-gray-500 dark:text-gray-400 font-medium uppercase tracking-wider">
                    Tenant
                  </div>
                  <div className="col-span-3 py-3 text-gray-500 dark:text-gray-400 font-medium uppercase tracking-wider text-center">
                    Status
                  </div>
                  <div className="col-span-4 py-3 text-gray-500 dark:text-gray-400 font-medium uppercase tracking-wider text-right">
                    Amount Due
                  </div>
                </div>
              </div>
              <div className="overflow-y-auto pr-1 custom-scrollbar min-h-[200px] max-h-[350px]">
                {outstandingPayments.map((payment) => (
                  <div
                    key={payment.id}
                    className="grid grid-cols-12 py-3 dark-divider border-b hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors duration-150"
                  >
                    <div className="col-span-5 text-sm">
                      <div className="font-medium text-gray-900 dark:text-gray-100">
                        {payment.tenant_name}
                      </div>
                      <div className="text-gray-500 dark:text-gray-400 text-xs">
                        {payment.property_name}
                      </div>
                    </div>
                    <div className="col-span-3 flex items-center justify-center">
                      <span
                        className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                          payment.status === "Overdue"
                            ? "bg-red-100 dark:bg-red-900/20 text-red-800 dark:text-red-400"
                            : payment.status === "Partial"
                              ? "bg-yellow-100 dark:bg-yellow-900/20 text-yellow-800 dark:text-yellow-400"
                              : "bg-orange-100 dark:bg-orange-900/20 text-orange-800 dark:text-orange-400"
                        }`}
                      >
                        {payment.status}
                      </span>
                    </div>
                    <div className="col-span-4 text-sm font-medium text-gray-900 dark:text-gray-100 text-right pr-2">
                      ${Number.parseFloat(payment.amount).toLocaleString(undefined, {
                        minimumFractionDigits: 2,
                        maximumFractionDigits: 2
                      })}
                    </div>
                  </div>
                ))}
              </div>
              <div className="mt-4 pt-3 dark-divider border-t">
                <div className="grid grid-cols-12 items-center">
                  <div className="col-span-5">
                    <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                      Total Outstanding:
                    </span>
                  </div>
                  <div className="col-span-3"></div>
                  <div className="col-span-4 text-right pr-2">
                    <span className="text-lg font-semibold text-red-600 dark:text-red-400">
                      ${parseFloat(totalOutstandingAmount).toLocaleString(undefined, {
                        minimumFractionDigits: 2,
                        maximumFractionDigits: 2
                      })}
                    </span>
                  </div>
                </div>
              </div>
            </div>
          ) : (
            <div className="flex items-center justify-center" style={{ minHeight: "300px" }}>
              <div className="text-center text-gray-500 dark:text-gray-400">
                <div className="mb-4">
                  <svg className="w-16 h-16 mx-auto text-gray-300 dark:text-gray-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                </div>
                <div className="text-xl font-bold text-green-600 dark:text-green-400">All Paid</div>
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
