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
            onClick={() => onChangeTab("rent")}
          >
            Rent
          </button>
          <button
            className={`py-2 px-1 border-b-2 ${
              activeTab === "invoices"
                ? "border-blue-500 font-medium text-sm text-blue-600"
                : "border-transparent font-medium text-sm text-gray-500 hover:text-gray-700 hover:border-gray-300"
            }`}
            onClick={() => onChangeTab("invoices")}
          >
            Invoices
          </button>
        </nav>
      </div>

      <div className="mt-3 overflow-hidden">
        <table className="w-full divide-y divide-gray-200">
          <thead className="block w-full">
            <tr className="flex w-full">
              <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider w-5/12">
                Tenant
              </th>
              <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider w-3/12">
                Amount
              </th>
              <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider w-2/12">
                Date
              </th>
              <th className="px-4 py-2 text-center text-xs font-medium text-gray-500 uppercase tracking-wider w-2/12">
                Reminder
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200 h-48 block overflow-y-auto custom-scrollbar w-full">
            {activeTab === "rent" ? (
              rentLoading ? (
                <tr>
                  <td
                    colSpan="4"
                    className="px-4 py-4 text-center text-sm text-gray-500 w-full block"
                  >
                    <div className="spinner block mx-auto mb-2 w-5 h-5" />
                    <p>Loading...</p>
                  </td>
                </tr>
              ) : rentData?.length > 0 ? (
                rentData.map((rent) => (
                  <tr key={rent.lease_id} className="flex w-full items-center">
                    <td className="px-4 py-3 whitespace-nowrap w-5/12">
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
                    <td className="px-4 py-3 whitespace-nowrap text-sm font-medium text-gray-900 w-3/12">{formatCurrency(rent.remaining_due > 0 ? rent.remaining_due : 0)}</td>
                    <td className="px-4 py-3 whitespace-nowrap text-sm w-2/12">
                      {rent.status === "DUE" ? (
                        <span className="text-gray-900">Today</span>
                      ) : (
                        <span className="text-red-600">Yesterday</span>
                      )}
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap text-center w-2/12">
                      <button className="h-8 w-8 rounded-full bg-gray-100 flex items-center justify-center text-gray-400 hover:text-gray-500 hover:bg-gray-200 transition-colors mx-auto">
                        <i className="far fa-bell"></i>
                      </button>
                    </td>
                  </tr>
                ))
              ) : (
                <tr className="flex w-full">
                  <td colSpan="4" className="px-4 py-4 text-center text-sm text-gray-500 w-full">
                    No pending payments
                  </td>
                </tr>
              )
            ) : invoicesLoading ? (
              <tr>
                <td colSpan="4" className="px-4 py-4 text-center text-sm text-gray-500 w-full block">
                  <div className="spinner block mx-auto mb-2 w-5 h-5" />
                  <p>Loading...</p>
                </td>
              </tr>
            ) : invoicesData?.length > 0 ? (
              invoicesData.map((inv) => (
                <tr key={inv.id} className="flex w-full items-center">
                  <td className="px-4 py-3 whitespace-nowrap w-5/12">
                    <div className="flex items-center justify-start">
                      <div className={`flex-shrink-0 h-8 w-8 rounded-full ${getAvatarColor(inv.tenant?.full_name || inv.property?.name || "-")} flex items-center justify-center text-white font-medium`}>
                        {getTenantInitials(inv.tenant?.full_name || inv.property?.name || "-")}
                      </div>
                      <div className="ml-3">
                        <p className="text-sm font-medium text-gray-900">
                          {inv.tenant?.full_name || inv.property?.name || "Invoice"}
                        </p>
                        {inv.invoice_number && (
                          <p className="text-xs text-gray-500">#{inv.invoice_number}</p>
                        )}
                      </div>
                    </div>
                  </td>
                  <td className="px-4 py-3 whitespace-nowrap text-sm font-medium text-gray-900 w-3/12">{formatCurrency(inv.amount)}</td>
                  <td className="px-4 py-3 whitespace-nowrap text-sm w-2/12">{inv.due_date ? new Date(inv.due_date).toLocaleDateString() : "—"}</td>
                  <td className="px-4 py-3 whitespace-nowrap text-center w-2/12">
                    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                      (inv.status || "").toLowerCase() === "overdue" ? "bg-red-100 text-red-800" : "bg-yellow-100 text-yellow-800"
                    }`}>
                      {(inv.status || "Pending").toString()}
                    </span>
                  </td>
                </tr>
              ))
            ) : (
              <tr className="flex w-full">
                <td colSpan="4" className="px-4 py-4 text-center text-sm text-gray-500 w-full">
                  No pending invoices
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default DuePanel;
