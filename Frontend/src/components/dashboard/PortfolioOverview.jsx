import React from "react";
import { clampPercent } from "../../utils/formatters";

const PortfolioOverview = ({ summary, occupancy, tenantCount, tenantsLoading, isLoading = false }) => {
  if (isLoading) {
    return (
      <div className="dashboard-card h-full flex flex-col animate-pulse">
        <div className="h-6 w-36 bg-gray-200 rounded mb-4" />
        <div className="grid grid-cols-3 gap-4 mb-4">
          {[0,1,2].map((i) => (
            <div key={i} className="bg-white rounded-lg p-4 border border-gray-100 shadow-sm flex flex-col items-center justify-center">
              <div className="w-12 h-12 rounded-full bg-gray-200 mb-3" />
              <div className="h-6 w-6 bg-gray-200 rounded mb-1" />
              <div className="h-4 w-16 bg-gray-200 rounded" />
            </div>
          ))}
        </div>
        <div className="space-y-2">
          <div className="flex justify-between items-center">
            <div className="h-4 w-28 bg-gray-200 rounded" />
            <div className="h-4 w-10 bg-gray-200 rounded" />
          </div>
          <div className="w-full bg-gray-200 rounded-full h-2" />
          <div className="flex justify-between">
            <div className="h-3 w-20 bg-gray-200 rounded" />
            <div className="h-3 w-20 bg-gray-200 rounded" />
          </div>
        </div>
      </div>
    );
  }
  return (
    <div className="dashboard-card h-full flex flex-col">
      <h2 className="text-lg font-medium text-gray-900 mb-4">Portfolio Overview</h2>

      <div className="flex-1 flex flex-col justify-around">
        <div className="grid grid-cols-3 gap-4">
          <div className="bg-white rounded-lg p-4 border border-gray-100 shadow-sm flex flex-col items-center justify-center">
            <div className="w-12 h-12 rounded-full bg-blue-100 flex items-center justify-center mb-3">
              <i className="fas fa-building text-blue-500 text-lg"></i>
            </div>
            <p className="text-xl font-semibold">{summary?.total_properties || 0}</p>
            <p className="text-sm text-gray-500">Properties</p>
          </div>

          <div className="bg-white rounded-lg p-4 border border-gray-100 shadow-sm flex flex-col items-center justify-center">
            <div className="w-12 h-12 rounded-full bg-green-100 flex items-center justify-center mb-3">
              <i className="fas fa-home text-green-500 text-lg"></i>
            </div>
            <p className="text-xl font-semibold">{summary?.total_units || 0}</p>
            <p className="text-sm text-gray-500">Units</p>
          </div>

          <div className="bg-white rounded-lg p-4 border border-gray-100 shadow-sm flex flex-col items-center justify-center">
            <div className="w-12 h-12 rounded-full bg-purple-100 flex items-center justify-center mb-3">
              <i className="fas fa-users text-purple-500 text-lg"></i>
            </div>
            {tenantsLoading ? (
              <div className="animate-pulse h-8 w-8 rounded-full bg-gray-200 mb-2"></div>
            ) : (
              <p className="text-xl font-semibold">{tenantCount}</p>
            )}
            <p className="text-sm text-gray-500">Tenants</p>
          </div>
        </div>

        <div>
          {(() => {
            const occupancyPercent = Math.round(clampPercent(occupancy?.occupancy_rate));
            return (
              <>
                <div className="flex justify-between items-center mb-2">
                  <span className="text-sm font-medium text-gray-500">Occupancy Rate</span>
                  <span className="text-sm font-medium text-gray-900">{occupancyPercent}%</span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-2">
                  <div
                    className="bg-blue-500 h-2 rounded-full"
                    style={{ width: `${occupancyPercent}%` }}
                  ></div>
                </div>
              </>
            );
          })()}
          <div className="flex justify-between text-xs text-gray-500 mt-1">
            <span>{occupancy?.occupied_units || 0} occupied</span>
            <span>{occupancy?.vacant_units || 0} vacant</span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default PortfolioOverview;
