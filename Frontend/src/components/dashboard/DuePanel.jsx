import React from "react";
import { formatCurrency, getAvatarColor as utilAvatarColor, getInitials } from "../../utils/formatters";
import { DuePanelSkeleton } from "../ui/skeletons";

const DuePanel = ({
  activeTab,
  onChangeTab,
  rentLoading,
  rentData,
  getAvatarColor = utilAvatarColor,
  getTenantInitials = getInitials,
  isLoading = false,
  invoicesLoading = false,
  invoicesData = [],
}) => {
  if (isLoading) {
    return <DuePanelSkeleton />;
  }

  return (
    <div className="kpi-card h-full flex flex-col">
      <h2 className="text-lg font-medium text-gray-900 dark:text-gray-100 mb-3">Due</h2>

      <div className="dark-divider border-b">
        <nav className="-mb-px flex space-x-6">
          <button
            className={`py-2 px-1 border-b-2 transition-colors duration-200 ${
              activeTab === "rent"
                ? "border-blue-500 dark:border-blue-400 font-medium text-sm text-blue-600 dark:text-blue-400"
                : "border-transparent font-medium text-sm text-gray-500 hover:text-gray-700 hover:border-gray-300 dark:text-gray-400 dark:hover:text-gray-300 dark:hover:border-gray-600"
            }`}
            onClick={() => onChangeTab("rent")}
          >
            Rent
          </button>
          <button
            className={`py-2 px-1 border-b-2 transition-colors duration-200 ${
              activeTab === "invoices"
                ? "border-blue-500 dark:border-blue-400 font-medium text-sm text-blue-600 dark:text-blue-400"
                : "border-transparent font-medium text-sm text-gray-500 hover:text-gray-700 hover:border-gray-300 dark:text-gray-400 dark:hover:text-gray-300 dark:hover:border-gray-600"
            }`}
            onClick={() => onChangeTab("invoices")}
          >
            Invoices
          </button>
        </nav>
      </div>

      <div className="mt-3 overflow-hidden flex-1">
        <div className="max-h-48 overflow-y-auto scrollbar-thin">
          <table className="w-full">
            <thead className="sticky top-0 z-10">
              <tr>
                <th className="px-4 py-3 text-left font-semibold text-gray-700 dark:text-gray-300 bg-gray-50 dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700" style={{width: '40%'}}>
                  Tenant
                </th>
                <th className="px-4 py-3 text-right font-semibold text-gray-700 dark:text-gray-300 bg-gray-50 dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700" style={{width: '25%'}}>
                  Amount
                </th>
                <th className="px-4 py-3 text-left font-semibold text-gray-700 dark:text-gray-300 bg-gray-50 dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700" style={{width: '20%'}}>
                  Date
                </th>
                <th className="px-4 py-3 text-center font-semibold text-gray-700 dark:text-gray-300 bg-gray-50 dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700" style={{width: '15%'}}>
                  Action
                </th>
              </tr>
            </thead>
            <tbody>
              {activeTab === "rent" ? (
                rentLoading ? (
                  <tr>
                    <td
                      colSpan="4"
                      className="px-4 py-4 text-center text-sm text-gray-500 dark:text-gray-400"
                    >
                      <div className="spinner mx-auto mb-2 w-5 h-5" />
                      <p>Loading...</p>
                    </td>
                  </tr>
                ) : rentData?.length > 0 ? (
                  rentData.map((rent, index) => (
                    <tr key={rent.lease_id} className="border-b border-gray-100 dark:border-gray-800 hover:bg-gray-50 dark:hover:bg-gray-800/40">
                      <td className="px-4 py-3 whitespace-nowrap" style={{width: '40%'}}>
                        <div className="flex items-center">
                          <div
                            className={`flex-shrink-0 h-8 w-8 rounded-full ${getAvatarColor(
                              rent.tenant_name
                            )} flex items-center justify-center text-white font-medium`}
                          >
                            {getTenantInitials(rent.tenant_name)}
                          </div>
                          <div className="ml-3">
                            <p className="text-sm font-medium text-gray-900 dark:text-gray-100">
                              {rent.tenant_name}
                            </p>
                          </div>
                        </div>
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap text-sm font-medium text-gray-900 dark:text-gray-100 text-right" style={{width: '25%'}}>
                        {formatCurrency(rent.remaining_due > 0 ? rent.remaining_due : 0)}
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-900 dark:text-gray-100" style={{width: '20%'}}>
                        {rent.status === "DUE" ? (
                          <span className="text-gray-900 dark:text-gray-100">Today</span>
                        ) : (
                          <span className="text-red-600 dark:text-red-400">Yesterday</span>
                        )}
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap text-center" style={{width: '15%'}}>
                        <button className="h-8 w-8 rounded-full bg-gray-100 dark:bg-gray-700 flex items-center justify-center text-gray-400 dark:text-gray-500 hover:text-gray-500 dark:hover:text-gray-400 hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors mx-auto">
                          <i className="far fa-bell"></i>
                        </button>
                      </td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan="4" className="px-4 py-4 text-center text-sm text-gray-500 dark:text-gray-400">
                      No pending payments
                    </td>
                  </tr>
                )
              ) : invoicesLoading ? (
                <tr>
                  <td colSpan="4" className="px-4 py-4 text-center text-sm text-gray-500 dark:text-gray-400">
                    <div className="spinner mx-auto mb-2 w-5 h-5" />
                    <p>Loading...</p>
                  </td>
                </tr>
              ) : invoicesData?.length > 0 ? (
                invoicesData.map((inv, index) => (
                  <tr key={inv.id} className="border-b border-gray-100 dark:border-gray-800 hover:bg-gray-50 dark:hover:bg-gray-800/40">
                    <td className="px-4 py-3 whitespace-nowrap overflow-hidden" style={{width: '40%'}}>
                      <div className="flex items-center min-w-0">
                        <div className={`flex-shrink-0 h-8 w-8 rounded-full ${getAvatarColor(inv.tenant?.full_name || inv.property?.name || "-")} flex items-center justify-center text-white font-medium`}>
                          {getTenantInitials(inv.tenant?.full_name || inv.property?.name || "-")}
                        </div>
                        <div className="ml-3 min-w-0 flex-1">
                          <p className="text-sm font-medium text-gray-900 dark:text-gray-100 truncate">
                            {inv.tenant?.full_name || inv.property?.name || "Invoice"}
                          </p>
                          {inv.invoice_number && (
                            <p className="text-xs text-gray-500 dark:text-gray-400 truncate">#{inv.invoice_number}</p>
                          )}
                        </div>
                      </div>
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap text-sm font-medium text-gray-900 dark:text-gray-100 text-right overflow-hidden" style={{width: '25%'}}>
                      <span className="truncate block">{formatCurrency(inv.amount)}</span>
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-900 dark:text-gray-100 overflow-hidden" style={{width: '20%'}}>
                      <span className="truncate block">{inv.due_date ? new Date(inv.due_date).toLocaleDateString() : "—"}</span>
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap text-center" style={{width: '15%'}}>
                      <span className={`status-pill ${
                        (inv.status || "").toLowerCase() === "overdue" ? "status-pill-overdue" : "status-pill-pending"
                      }`}>
                        {(inv.status || "Pending").toString()}
                      </span>
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan="4" className="px-4 py-4 text-center text-sm text-gray-500 dark:text-gray-400">
                    No pending invoices
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

export default DuePanel;