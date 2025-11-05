import React, { useEffect, useState } from "react";
import { reportError } from '../utils/error-reporting';
import ControlsBar from "../components/dashboard/ControlsBar";
import FinancialSummary from "../components/dashboard/FinancialSummary";
import DuePanel from "../components/dashboard/DuePanel";
import PortfolioOverview from "../components/dashboard/PortfolioOverview";
import RevenueTrendsCard from "../components/dashboard/RevenueTrendsCard";
import usePreviousPeriodData from "../hooks/usePreviousPeriodData";
import { getPresetRange, toIsoDate } from "../utils/dateRanges";
import { getAvatarColor, getInitials, computeDelta, humanizePeriodLabel } from "../utils/formatters";
import useProperties from "../hooks/useProperties";
import useDashboardData from "../hooks/useDashboardData";
import useRentTracker from "../hooks/useRentTracker";
import useTenantsCount from "../hooks/useTenantsCount";
import useDueInvoices from "../hooks/useDueInvoices";
import type { DashboardResponse } from "../utils/api/dashboard";

interface RentData {
  lease_id: number | string;
  tenant_name: string;
  remaining_due: number;
  status: string;
}

interface CustomRange {
  start: string;
  end: string;
}

const DashboardPage: React.FC = () => {
  const [loading, setLoading] = useState<boolean>(true);
  const [dashboardData, setDashboardData] = useState<DashboardResponse | null>(null);
  const [prevPeriodData, setPrevPeriodData] = useState<DashboardResponse | null>(null);
  const [rentData, setRentData] = useState<RentData[]>([]);
  const [rentLoading, setRentLoading] = useState<boolean>(true);
  const [selectedProperty, setSelectedProperty] = useState<string>("all");
  const [timePeriod, setTimePeriod] = useState<string>("this_month");
  const [customRange, setCustomRange] = useState<CustomRange | null>(null);
  const { options: propertyOptions } = useProperties();
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<string>("rent");
  const [tenantCount, setTenantCount] = useState<number>(0);
  const [tenantsLoading, setTenantsLoading] = useState<boolean>(true);

  // Hook-powered data
  // Compute final start/end based on timePeriod or custom
  const computeActiveRange = (): CustomRange => {
    if (timePeriod === "custom" && customRange?.start && customRange?.end) {
      return { start: customRange.start, end: customRange.end };
    }
    const { start, end } = getPresetRange(timePeriod);
    return { start: toIsoDate(start), end: toIsoDate(end) };
  };

  const activeRange = computeActiveRange();

  const {
    data: hookDashboardData,
    loading: hookDashboardLoading,
    error: hookDashboardError,
  } = useDashboardData({
    propertyId: selectedProperty !== "all" ? selectedProperty : undefined,
    timePeriod,
    startDate: activeRange.start,
    endDate: activeRange.end,
  });

  const now = new Date();
  const { data: hookRentData, loading: hookRentLoading } = useRentTracker({
    month: now.getMonth() + 1,
    year: now.getFullYear(),
    propertyId: selectedProperty !== "all" ? selectedProperty : undefined,
  });

  const {
    count: hookTenantCount,
    loading: hookTenantsLoading,
  } = useTenantsCount(
    selectedProperty,
    hookDashboardData?.occupancy?.occupied_units || 0
  );

  // previous period via hook (keeps current server behavior)
  const { data: hookPrevData } = usePreviousPeriodData({
    propertyId: selectedProperty !== "all" ? selectedProperty : undefined,
    timePeriod,
    currentRange: activeRange,
  });

  // Due invoices (pending/overdue) scoped to property and period
  const { data: dueInvoices, loading: dueInvoicesLoading } = useDueInvoices({
    propertyId: selectedProperty !== "all" ? selectedProperty : undefined,
    startDate: activeRange.start,
    endDate: activeRange.end,
    limit: 5,
  });

  // Sync hook tenant count to local state
  useEffect(() => {
    setTenantsLoading(hookTenantsLoading);
    setTenantCount(hookTenantCount);
  }, [hookTenantCount, hookTenantsLoading]);

  // Sync hook dashboard + rent data into legacy state, and fetch previous period
  useEffect(() => {
    setLoading(hookDashboardLoading);
    if (hookDashboardData) setDashboardData(hookDashboardData);
    if (hookDashboardError) {
      const errorMessage = hookDashboardError.message || String(hookDashboardError);
      setError(errorMessage);
      
      // Report dashboard data loading failures
      reportError(hookDashboardError, {
        component: 'Dashboard',
        action: 'data_loading',
        tags: {
          dataType: 'dashboard_summary',
        },
        extra: {
          dashboard: {
            selectedProperty,
            timePeriod,
            dateRange: activeRange,
            error: errorMessage,
          }
        },
      }, 'error');
    }

    setRentLoading(hookRentLoading);
    if (hookRentData) setRentData(hookRentData);

    // Update previous period data from hook
    if (hookPrevData) setPrevPeriodData(hookPrevData);
  }, [selectedProperty, timePeriod, hookDashboardLoading, hookDashboardData, hookDashboardError, hookRentLoading, hookRentData, hookPrevData, activeRange]);

  const getTenantInitials = getInitials;

  // With component-level skeletons, never block on page-level loading

  if (error) {
    return (
      <div className="p-4">
        <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded relative" role="alert">
          <strong className="font-bold">Error: </strong>
          <span className="block sm:inline">{error}</span>
          <button onClick={() => window.location.reload()} className="mt-2 bg-red-500 hover:bg-red-700 text-white font-bold py-1 px-2 rounded text-sm">
            Retry
          </button>
        </div>
      </div>
    );
  }

  // Compute rich deltas for modern chips
  const revenueDelta = computeDelta({
    current: dashboardData?.summary?.monthly_revenue,
    previous: prevPeriodData?.summary?.monthly_revenue,
  });
  const expensesDelta = computeDelta({
    current: dashboardData?.summary?.monthly_expenses,
    previous: prevPeriodData?.summary?.monthly_expenses,
  });
  const maintenanceDelta = computeDelta({
    current: dashboardData?.summary?.maintenance_expenses,
    previous: prevPeriodData?.summary?.maintenance_expenses,
  });
  const periodLabel = humanizePeriodLabel(timePeriod, activeRange);

  return (
    <div className="space-y-6">
      <ControlsBar
        properties={propertyOptions}
        selectedProperty={selectedProperty}
        onChangeProperty={setSelectedProperty}
        timePeriod={timePeriod}
        onChangeTimePeriod={setTimePeriod}
        onCustomize={() => {}}
        isLoading={loading}
        onSetCustomRange={setCustomRange}
        currentRange={activeRange}
      />

      <FinancialSummary
        summary={dashboardData?.summary}
        timePeriod={timePeriod}
        periodLabel={periodLabel}
        revenueDelta={revenueDelta}
        expensesDelta={expensesDelta}
        maintenanceDelta={maintenanceDelta}
        isLoading={loading}
      />

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <DuePanel
          activeTab={activeTab}
          onChangeTab={setActiveTab}
          rentLoading={rentLoading}
          rentData={rentData}
          getAvatarColor={getAvatarColor}
          getTenantInitials={getTenantInitials}
          isLoading={loading}
          invoicesLoading={dueInvoicesLoading}
          invoicesData={dueInvoices}
        />

        <PortfolioOverview
          summary={dashboardData?.summary}
          occupancy={dashboardData?.occupancy}
          tenantCount={tenantCount}
          tenantsLoading={tenantsLoading}
          isLoading={loading}
        />
      </div>

      <RevenueTrendsCard data={dashboardData?.revenue} isLoading={loading} />
    </div>
  );
};

export default DashboardPage;

