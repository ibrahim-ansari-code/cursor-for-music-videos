import React from 'react';
import * as Sentry from '@sentry/react';
import { useTenantDashboard } from '@/hooks/useTenantDashboard';
import { useAuth } from '@/hooks/useAuth';
import {
  DashboardSkeleton,
  MyUnitCard,
  MonthlyRentCard,
  NextPaymentCard,
  MaintenanceCard,
  RecentPaymentsTable,
  PaymentQuickAction,
  MaintenanceQuickAction,
  DocumentsQuickAction,
} from '@/components/dashboard';

/**
 * DashboardContent Component
 * Main dashboard orchestrator that composes all dashboard components
 * Wrapped with Sentry error boundary for error tracking
 */
const DashboardContent: React.FC = React.memo(() => {
  const { user } = useAuth();
  const { data, loading, error } = useTenantDashboard();

  // Get user's first name for welcome message
  const firstName = user?.first_name || 'Tenant';

  if (loading) {
    return <DashboardSkeleton />;
  }

  if (error || !data) {
    return (
      <div className="p-6 bg-red-50 border border-red-200 rounded-xl text-red-700">
        <h3 className="font-semibold">Failed to load dashboard</h3>
        <p className="mt-1">{error?.message || 'Unknown error'}</p>
      </div>
    );
  }

  const { my_unit: myUnit, monthly_rent: monthlyRent, next_payment: nextPayment, maintenance } = data;

  return (
    <div className="bg-white rounded-lg shadow border border-gray-200">
      <div className="p-6">
        {/* Page Header */}
        <div className="mb-6">
          <h1 className="text-2xl font-semibold text-gray-800">
            Welcome to your Tenant Dashboard, {firstName}
          </h1>
        </div>

        {/* Dashboard cards */}
        <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-4">
          <MyUnitCard data={myUnit} />
          <MonthlyRentCard data={monthlyRent} />
          <NextPaymentCard data={nextPayment} />
          <MaintenanceCard data={maintenance} />
        </div>

        {/* Recent Payments Table */}
        <RecentPaymentsTable />

        {/* Quick Actions */}
        <div className="mt-8 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          <PaymentQuickAction />
          <MaintenanceQuickAction />
          <DocumentsQuickAction />
        </div>
      </div>
    </div>
  );
});

DashboardContent.displayName = 'DashboardContent';

// Error fallback component for Sentry error boundary
function DashboardErrorFallback({ error }: { error: unknown }): React.ReactElement {
  const errorMessage = error instanceof Error ? error.message : 'An unexpected error occurred';
  return (
    <div className="p-6 bg-red-50 border border-red-200 rounded-xl">
      <h3 className="font-semibold text-red-800">Dashboard Error</h3>
      <p className="mt-1 text-red-700">{errorMessage}</p>
      <button
        onClick={() => window.location.reload()}
        className="mt-4 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors"
      >
        Reload Page
      </button>
    </div>
  );
}

// Wrap with Sentry error boundary for error tracking
const DashboardContentWithErrorBoundary = Sentry.withErrorBoundary(DashboardContent, {
  fallback: DashboardErrorFallback,
});

export default DashboardContentWithErrorBoundary;
