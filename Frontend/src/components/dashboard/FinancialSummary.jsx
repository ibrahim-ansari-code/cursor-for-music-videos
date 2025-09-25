import React from "react";
import { formatCurrency } from "../../utils/formatters";
import { FinancialCardSkeleton } from "../ui/skeletons";

const FinancialSummary = ({
  summary,
  timePeriod,
  periodLabel,
  revenueDelta,
  expensesDelta,
  maintenanceDelta,
  isLoading = false,
}) => {
  if (isLoading) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {[0, 1, 2].map((i) => (
          <FinancialCardSkeleton key={i} />
        ))}
      </div>
    );
  }
  const showRevenueDelta = revenueDelta?.show;
  const showExpensesDelta = expensesDelta?.show;
  const showMaintenanceDelta = maintenanceDelta?.show;

  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
      <div className="dashboard-card">
        <h2 className="text-sm font-medium text-gray-500 dark:text-gray-400 mb-1">Revenue</h2>
        <div className="flex items-baseline">
          <p className="text-2xl font-semibold text-gray-900 dark:text-gray-100">{formatCurrency(summary?.monthly_revenue)}</p>
          {showRevenueDelta && (
            <span
              title={`Current: ${formatCurrency(summary?.monthly_revenue)} | Previous: ${formatCurrency(summary?.monthly_revenue - (revenueDelta?.absolute ?? 0))}`}
              className={`ml-2 text-xs font-medium ${revenueDelta?.colorClass}`}
            >
              <i
                className={`fas fa-${revenueDelta?.iconName} mr-0.5`}
              ></i>
              {revenueDelta?.direction === "new" ? (
                <>New</>
              ) : (
                <>
                  {formatCurrency(Math.abs(revenueDelta?.absolute || 0))}
                  {" "}
                  <span className="text-gray-500">(</span>
                  {Math.abs(revenueDelta?.percent || 0).toFixed(1)}%
                  <span className="text-gray-500">)</span>
                </>
              )}
            </span>
          )}
        </div>
        <div className="text-xs text-gray-500 dark:text-gray-400 mt-1">
          Compared to previous {periodLabel || timePeriod}
        </div>
      </div>

      <div className="dashboard-card">
        <h2 className="text-sm font-medium text-gray-500 dark:text-gray-400 mb-1">Expenses</h2>
        <div className="flex items-baseline">
          <p className="text-2xl font-semibold text-gray-900 dark:text-gray-100">{formatCurrency(summary?.monthly_expenses)}</p>
          {showExpensesDelta && (
            <span
              title={`Current: ${formatCurrency(summary?.monthly_expenses)} | Previous: ${formatCurrency(summary?.monthly_expenses - (expensesDelta?.absolute ?? 0))}`}
              className={`ml-2 text-xs font-medium ${expensesDelta?.colorClass}`}
            >
              <i
                className={`fas fa-${expensesDelta?.iconName} mr-0.5`}
              ></i>
              {expensesDelta?.direction === "new" ? (
                <>New</>
              ) : (
                <>
                  {formatCurrency(Math.abs(expensesDelta?.absolute || 0))}
                  {" "}
                  <span className="text-gray-500">(</span>
                  {Math.abs(expensesDelta?.percent || 0).toFixed(1)}%
                  <span className="text-gray-500">)</span>
                </>
              )}
            </span>
          )}
        </div>
        <div className="text-xs text-gray-500 dark:text-gray-400 mt-1">All monthly expenses</div>
      </div>

      <div className="dashboard-card">
        <h2 className="text-sm font-medium text-gray-500 dark:text-gray-400 mb-1">Spent on maintenance</h2>
        <div className="flex items-baseline">
          <p className="text-2xl font-semibold text-gray-900 dark:text-gray-100">{formatCurrency(summary?.maintenance_expenses)}</p>
          {showMaintenanceDelta && (
            <span
              title={`Current: ${formatCurrency(summary?.maintenance_expenses)} | Previous: ${formatCurrency(summary?.maintenance_expenses - (maintenanceDelta?.absolute ?? 0))}`}
              className={`ml-2 text-xs font-medium ${maintenanceDelta?.colorClass}`}
            >
              <i
                className={`fas fa-${maintenanceDelta?.iconName} mr-0.5`}
              ></i>
              {formatCurrency(Math.abs(maintenanceDelta?.absolute || 0))}
              {" "}
              <span className="text-gray-500">(</span>
              {Math.abs(maintenanceDelta?.percent || 0).toFixed(1)}%
              <span className="text-gray-500">)</span>
            </span>
          )}
        </div>
        <div className="text-xs text-gray-500 dark:text-gray-400 mt-1">
          From {summary?.total_properties || 0} properties
        </div>
      </div>
    </div>
  );
};

export default FinancialSummary;
