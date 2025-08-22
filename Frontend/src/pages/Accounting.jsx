import React, { useState } from "react";
import { Outlet, useNavigate, useLocation } from "react-router-dom";
import { AccountingProvider } from "../components/accounting/AccountingContext";
import SharedFilePreviewModal from "../components/accounting/shared/SharedFilePreviewModal";

const Accounting = () => {
  const navigate = useNavigate();
  const location = useLocation();
  
  // Determine the current active tab from the URL
  const getCurrentTab = () => {
    const path = location.pathname.split('/').pop();
    return path === 'accounting' ? 'overview' : path;
  };
  
  const activeTab = getCurrentTab();

  const handleTabChange = (tabName) => {
    navigate(`/accounting/${tabName}`);
  };

  return (
    <AccountingProvider>
      <div>
        <div className="border-b border-gray-200">
          <nav className="-mb-px flex space-x-8">
            <button
              onClick={() => handleTabChange("overview")}
              className={`${
                activeTab === "overview"
                  ? "border-blue-500 text-blue-600"
                  : "border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300"
              } whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm`}
            >
              Overview
            </button>
            <button
              onClick={() => handleTabChange("invoices")}
              className={`${
                activeTab === "invoices"
                  ? "border-blue-500 text-blue-600"
                  : "border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300"
              } whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm`}
            >
              Invoices
            </button>
            <button
              onClick={() => handleTabChange("expenses")}
              className={`${
                activeTab === "expenses"
                  ? "border-blue-500 text-blue-600"
                  : "border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300"
              } whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm`}
            >
              Expenses
            </button>
            <button
              onClick={() => handleTabChange("payments")}
              className={`${
                activeTab === "payments"
                  ? "border-blue-500 text-blue-600"
                  : "border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300"
              } whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm`}
            >
              Payments
            </button>
            <button
              onClick={() => handleTabChange("rent-tracker")}
              className={`${
                activeTab === "rent-tracker"
                  ? "border-blue-500 text-blue-600"
                  : "border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300"
              } whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm`}
            >
              Rent Tracker
            </button>
          </nav>
        </div>

        {/* Tab content rendered by React Router */}
        <div className="mt-6">
          <Outlet />
        </div>

        {/* Shared file preview modal */}
        <SharedFilePreviewModal />
      </div>
    </AccountingProvider>
  );
};

export default Accounting;