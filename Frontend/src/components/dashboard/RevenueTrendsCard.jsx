import React from "react";
import RevenueChart from "../charts/RevenueChart";

const RevenueTrendsCard = ({ data, isLoading }) => {
  return (
    <div className="dashboard-card">
      <h2 className="text-lg font-medium text-gray-900 mb-4">Revenue Trends</h2>
      {isLoading ? (
        <div className="h-64 w-full bg-gray-100 rounded animate-pulse" />
      ) : (
        <RevenueChart data={data} />
      )}
    </div>
  );
};

export default RevenueTrendsCard;
