import React from "react";
import RevenueChart from "../charts/RevenueChart";
import { ChartSkeleton } from "../ui/skeletons";

const RevenueTrendsCard = ({ data, isLoading }) => {
  return (
    <div className="dashboard-card">
      <h2 className="text-lg font-medium text-gray-900 mb-4">Revenue Trends</h2>
      {isLoading ? (
        <ChartSkeleton height="256px" />
      ) : (
        <RevenueChart data={data} />
      )}
    </div>
  );
};

export default RevenueTrendsCard;
