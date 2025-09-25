import React from "react";
import CountUp from "react-countup";

const SnapshotCard = ({ data }) => {
  const {
    occupancyRate = 0,
    paidRent = 0,
    totalRent = 0,
    avgRent = 0,
  } = data || {};

  return (
    <div className="kpi-card group h-full flex flex-col">
      <div className="flex items-center mb-4">
        <h2 className="text-base font-medium text-gray-800 dark:text-gray-200 whitespace-nowrap">Snapshot</h2>
        <div className="kpi-sparkline bg-gradient-to-r from-purple-200 to-purple-300 dark:from-purple-800"></div>
      </div>

      <div className="space-y-4 flex-grow">
        <div className="text-center">
          <p className="text-xs font-medium text-gray-600 dark:text-gray-400 uppercase tracking-wider mb-1">
            Occupancy Rate
          </p>
          <p className="kpi-number text-blue-600 dark:text-blue-400 tabular-nums">
            <CountUp
              end={occupancyRate}
              duration={1.5}
              decimals={1}
              separator=","
              preserveValue={true}
            />
            %
          </p>
        </div>

        <div className="text-center dark-divider border-t pt-4">
          <p className="text-xs font-medium text-gray-600 dark:text-gray-400 uppercase tracking-wider mb-1">
            Paid Rent
          </p>
          <p className="kpi-number text-green-600 dark:text-green-400 tabular-nums whitespace-nowrap overflow-x-auto">
            <CountUp 
              end={paidRent} 
              duration={1.5} 
              decimals={0} 
              separator="," 
              preserveValue={true}
            />
            <span className="text-gray-500 dark:text-gray-400">
              /<CountUp
                end={totalRent}
                duration={1.5}
                decimals={0}
                separator=","
                preserveValue={true}
              />
            </span>
          </p>
        </div>

        <div className="text-center dark-divider border-t pt-4">
          <p className="text-xs font-medium text-gray-600 dark:text-gray-400 uppercase tracking-wider mb-1">
            Avg Rent
          </p>
          <p className="kpi-number tabular-nums">
            $<CountUp 
              end={avgRent} 
              duration={1.5} 
              decimals={2} 
              separator="," 
              preserveValue={true}
            />
          </p>
        </div>
      </div>
    </div>
  );
};

export default SnapshotCard;