import React, { useEffect } from "react";
import * as Sentry from "@sentry/react";
import LeaseRow from "./LeaseRow";
import type { LeasesTableProps } from "../../types/lease";

interface LeasesTableWithSelectionProps extends LeasesTableProps {
  selectedLeaseIds: Set<number>;
  onSelectLease: (leaseId: number, selected: boolean) => void;
  onSelectAll: (selected: boolean) => void;
}

const LeasesTable: React.FC<LeasesTableWithSelectionProps> = ({
  leases,
  isLoading,
  actionHandlers,
  selectedLeaseIds,
  onSelectLease,
  onSelectAll,
}) => {
  // Track table rendering performance
  useEffect(() => {
    if (!isLoading && leases.length > 0) {
      Sentry.startSpan(
        {
          op: "ui.render",
          name: "Leases Table Render",
        },
        (span) => {
          span.setAttribute("leaseCount", leases.length);
          span.setAttribute(
            "hasDocuments",
            leases.some((l) => l.documents?.length > 0)
          );

          Sentry.logger.trace("Leases table rendered", {
            leaseCount: leases.length,
            leasesWithDocuments: leases.filter((l) => l.documents?.length > 0)
              .length,
          });
        }
      );
    }
  }, [leases.length, isLoading]);

  if (isLoading && leases.length === 0) {
    return (
      <div className="dark-panel dark-shadow rounded-lg overflow-hidden relative">
        <div className="overflow-x-auto overflow-y-auto max-h-[calc(100vh-300px)] sm:max-h-[calc(100vh-250px)] lg:max-h-[calc(100vh-200px)] scrollbar-thin">
          <table className="data-table min-w-full divide-y dark-divider">
            <thead className="dark-input">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider w-12">
                  <input
                    type="checkbox"
                    checked={
                      leases.length > 0 &&
                      leases.every((lease) => selectedLeaseIds.has(lease.id))
                    }
                    onChange={(e) => onSelectAll(e.target.checked)}
                    disabled={isLoading || leases.length === 0}
                    className="rounded border-gray-300 text-blue-600 focus:ring-blue-500 dark:border-gray-600 dark:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed"
                  />
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                  Tenant
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                  Property
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                  Dates
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                  Rent
                </th>
                <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                  Status
                </th>
                <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="dark-panel divide-y dark-divider">
              {[...Array(5)].map((_, i) => (
                <tr key={i}>
                  <td className="px-6 py-4 whitespace-nowrap" colSpan={7}>
                    <div className="animate-pulse h-12 dark-input rounded transition-colors"></div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    );
  }

  return (
    <div className="dark-panel dark-shadow rounded-lg overflow-hidden relative">
      <div className="overflow-x-auto overflow-y-auto max-h-[calc(100vh-300px)] sm:max-h-[calc(100vh-250px)] lg:max-h-[calc(100vh-200px)] scrollbar-thin">
        <table className="data-table min-w-full divide-y dark-divider">
          <thead className="dark-input">
            <tr>
              <th
                scope="col"
                className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider w-12"
              >
                <input
                  type="checkbox"
                  checked={
                    leases.length > 0 &&
                    leases.every((lease) => selectedLeaseIds.has(lease.id))
                  }
                  onChange={(e) => onSelectAll(e.target.checked)}
                  disabled={isLoading || leases.length === 0}
                  className="rounded border-gray-300 text-blue-600 focus:ring-blue-500 dark:border-gray-600 dark:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed"
                  aria-label="Select all leases"
                />
              </th>
              <th
                scope="col"
                className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider"
              >
                Tenant
              </th>
              <th
                scope="col"
                className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider"
              >
                Property
              </th>
              <th
                scope="col"
                className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider"
              >
                Dates
              </th>
              <th
                scope="col"
                className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider"
              >
                Rent
              </th>
              <th
                scope="col"
                className="px-6 py-3 text-center text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider"
              >
                Status
              </th>
              <th
                scope="col"
                className="px-6 py-3 text-center text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider"
              >
                Actions
              </th>
            </tr>
          </thead>
          <tbody className="dark-panel divide-y dark-divider">
            {leases.length > 0 ? (
              leases.map((lease, index) => (
                <LeaseRow
                  key={lease.id}
                  lease={lease}
                  index={index}
                  actionHandlers={actionHandlers}
                  isSelected={selectedLeaseIds.has(lease.id)}
                  onSelect={(selected) => onSelectLease(lease.id, selected)}
                />
              ))
            ) : (
              <tr>
                <td
                  colSpan={7}
                  className="px-6 py-4 text-center text-sm text-gray-500 dark:text-gray-400"
                >
                  No leases found
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default LeasesTable;
