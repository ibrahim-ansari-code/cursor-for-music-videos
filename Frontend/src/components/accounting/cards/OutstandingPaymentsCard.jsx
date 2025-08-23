import React from "react";
import { FiDollarSign } from "react-icons/fi";

const OutstandingPaymentsCard = ({
  outstandingAmount = 0,
  totalTenants = 0,
  pendingPayments = 0,
}) => {
  const formattedAmount = new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(outstandingAmount);

  return (
    <div className="flex flex-col h-full p-4 bg-white rounded-lg shadow-sm">
      <div className="flex items-center mb-4">
        <h3 className="text-base font-medium text-gray-800">
          Outstanding Payments
        </h3>
      </div>

      <div className="flex-1 flex flex-col justify-center">
        <div className="flex items-center justify-center mb-4">
          <div className="p-3 rounded-full bg-red-50">
            <FiDollarSign className="text-red-500 w-8 h-8" />
          </div>
          <div className="ml-4">
            <div className="text-3xl font-semibold text-gray-800">
              {formattedAmount}
            </div>
            <div className="text-sm text-gray-500">
              Total outstanding amount
            </div>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-4 mt-2">
          <div className="flex flex-col items-center p-3 bg-gray-50 rounded-md">
            <span className="text-sm text-gray-500">Pending Payments</span>
            <span className="text-lg font-medium text-gray-700 mt-1">
              {pendingPayments}
            </span>
          </div>

          <div className="flex flex-col items-center p-3 bg-gray-50 rounded-md">
            <span className="text-sm text-gray-500">Total Tenants</span>
            <span className="text-lg font-medium text-gray-700 mt-1">
              {totalTenants}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default OutstandingPaymentsCard;
