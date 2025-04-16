import React from 'react';
import CountUp from 'react-countup';

const SnapshotCard = ({ data }) => {
  const { occupancyRate = 0, outstandingPayments = 0, avgRent = 0 } = data || {};
  
  return (
    <div className="bg-white p-6 rounded-lg shadow-sm h-full flex flex-col">
      <h2 className="text-lg font-medium text-gray-800 mb-5">Snapshot</h2>
      
      <div className="grid grid-cols-3 gap-4 flex-grow">
        <div className="border-r border-gray-200 pr-4 flex flex-col justify-center">
          <p className="text-sm font-medium text-gray-500 mb-2">Occupancy Rate</p>
          <p className="text-xl font-semibold text-blue-600">
            <CountUp end={occupancyRate} duration={1.5} decimals={1} separator="," />%
          </p>
        </div>
        
        <div className="border-r border-gray-200 px-4 flex flex-col justify-center">
          <p className="text-sm font-medium text-gray-500 mb-2">Outstanding</p>
          <p className="text-xl font-semibold text-red-600">
            <CountUp end={outstandingPayments} duration={1.5} separator="," />
          </p>
        </div>
        
        <div className="pl-4 flex flex-col justify-center">
          <p className="text-sm font-medium text-gray-500 mb-2">Avg Rent</p>
          <p className="text-xl font-semibold text-gray-900">
            $<CountUp end={avgRent} duration={1.5} decimals={2} separator="," />
          </p>
        </div>
      </div>
    </div>
  );
};

export default SnapshotCard; 