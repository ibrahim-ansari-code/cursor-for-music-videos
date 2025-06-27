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
    <div className="bg-white p-4 rounded-lg shadow-sm hover:shadow-md transition-shadow duration-200 h-full flex flex-col">
      <h2 className="text-base font-medium text-gray-800 mb-4">Snapshot</h2>

      <div className="space-y-4 flex-grow">
        <div className="text-center">
          <p className="text-xs font-medium text-gray-600 uppercase tracking-wider mb-1">
            Occupancy Rate
          </p>
          <p className="text-2xl font-semibold text-blue-600 tabular-nums">
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

        <div className="text-center border-t border-gray-100 pt-4">
          <p className="text-xs font-medium text-gray-600 uppercase tracking-wider mb-1">
            Paid Rent
          </p>
          <p className="text-2xl font-semibold text-green-600 tabular-nums whitespace-nowrap overflow-x-auto">
            <CountUp 
              end={paidRent} 
              duration={1.5} 
              decimals={0} 
              separator="," 
              preserveValue={true}
            />
            <span className="text-gray-500">
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

        <div className="text-center border-t border-gray-100 pt-4">
          <p className="text-xs font-medium text-gray-600 uppercase tracking-wider mb-1">
            Avg Rent
          </p>
          <p className="text-2xl font-semibold text-gray-900 tabular-nums">
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
