import React from "react";
import { useNavigate } from "react-router-dom";
import { clampPercent } from "../../utils/formatters";
import { PortfolioCardSkeleton } from "../ui/skeletons";
import type { DashboardSummary, OccupancyData } from "../../utils/api/dashboard";

interface PortfolioOverviewProps {
  summary?: DashboardSummary;
  occupancy?: OccupancyData;
  tenantCount: number;
  tenantsLoading: boolean;
  isLoading?: boolean;
}

const PortfolioOverview: React.FC<PortfolioOverviewProps> = ({
  summary,
  occupancy,
  tenantCount,
  tenantsLoading,
  isLoading = false
}) => {
  const navigate = useNavigate();

  if (isLoading) {
    return <PortfolioCardSkeleton />;
  }
  return (
    <div className="kpi-card h-full flex flex-col">
      <h2 className="text-lg font-medium text-gray-900 dark:text-gray-100 mb-4">Portfolio Overview</h2>

      <div className="flex-1 flex flex-col justify-around">
        <div className="grid grid-cols-3 gap-4">
          <button 
            onClick={() => navigate('/properties')}
            className="dark-panel rounded-xl p-4 dark-divider border dark-shadow flex flex-col items-center justify-center hover:scale-105 transition-transform duration-200 cursor-pointer"
          >
            <div className="w-12 h-12 rounded-full bg-blue-100 dark:bg-blue-900/50 flex items-center justify-center mb-3">
              <i className="fas fa-building text-blue-500 dark:text-blue-400 text-lg"></i>
            </div>
            <p className="kpi-number text-lg">{summary?.total_properties || 0}</p>
            <p className="text-sm text-gray-500 dark:text-gray-400">Properties</p>
          </button>

          <div className="dark-panel rounded-xl p-4 dark-divider border dark-shadow flex flex-col items-center justify-center hover:scale-105 transition-transform duration-200">
            <div className="w-12 h-12 rounded-full bg-green-100 dark:bg-green-900/50 flex items-center justify-center mb-3">
              <i className="fas fa-home text-green-500 dark:text-green-400 text-lg"></i>
            </div>
            <p className="kpi-number text-lg">{summary?.total_units || 0}</p>
            <p className="text-sm text-gray-500 dark:text-gray-400">Units</p>
          </div>

          <button
            onClick={() => navigate('/tenants')}
            className="dark-panel rounded-xl p-4 dark-divider border dark-shadow flex flex-col items-center justify-center hover:scale-105 transition-transform duration-200 cursor-pointer"
          >
            <div className="w-12 h-12 rounded-full bg-purple-100 dark:bg-purple-900/50 flex items-center justify-center mb-3">
              <i className="fas fa-users text-purple-500 dark:text-purple-400 text-lg"></i>
            </div>
            {tenantsLoading ? (
              <div className="animate-pulse h-8 w-8 rounded-full bg-gray-200 dark:bg-gray-700 mb-2"></div>
            ) : (
              <p className="kpi-number text-lg">{tenantCount}</p>
            )}
            <p className="text-sm text-gray-500 dark:text-gray-400">Tenants</p>
          </button>
        </div>

        {/* Add spacing between grid and occupancy rate */}
        <div className="mt-6">
          {(() => {
            const occupancyPercent = Math.round(clampPercent(occupancy?.occupancy_rate));
            return (
              <>
                <div className="flex justify-between items-center mb-2">
                  <span className="text-sm font-medium text-gray-500 dark:text-gray-400">Occupancy Rate</span>
                  <span className="text-sm font-medium text-gray-900 dark:text-gray-100">{occupancyPercent}%</span>
                </div>
                <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
                  <div
                    className="bg-blue-500 h-2 rounded-full"
                    style={{ width: `${occupancyPercent}%` }}
                  ></div>
                </div>
              </>
            );
          })()}
          <div className="flex justify-between text-xs text-gray-500 dark:text-gray-400 mt-1">
            <span>{occupancy?.occupied_units || 0} occupied</span>
            <span>{occupancy?.vacant_units || 0} vacant</span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default PortfolioOverview;

