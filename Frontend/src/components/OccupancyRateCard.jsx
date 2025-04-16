import React from 'react';
import { AiOutlineHome } from 'react-icons/ai';

const OccupancyRateCard = ({ occupancyRate = 0, totalUnits = 0 }) => {
  const occupiedUnits = Math.round(totalUnits * (occupancyRate / 100));
  const vacantUnits = totalUnits - occupiedUnits;
  
  // Function to determine the status color based on occupancy rate
  const getOccupancyStatusColor = (rate) => {
    if (rate >= 90) return 'bg-green-100 text-green-800'; // Excellent
    if (rate >= 80) return 'bg-teal-100 text-teal-800';   // Good
    if (rate >= 70) return 'bg-blue-100 text-blue-800';   // Moderate
    if (rate >= 60) return 'bg-yellow-100 text-yellow-800'; // Needs Attention
    return 'bg-red-100 text-red-800'; // Critical
  };

  const statusColorClass = getOccupancyStatusColor(occupancyRate);

  return (
    <div className="flex flex-col h-full p-4 bg-white rounded-lg shadow-sm">
      <div className="flex items-center mb-4">
        <h3 className="text-base font-medium text-gray-800">Occupancy Rate</h3>
      </div>
      
      <div className="flex-1 flex flex-col justify-center items-center">
        <div className="relative mb-4">
          <svg width="120" height="120" viewBox="0 0 120 120">
            {/* Background circle */}
            <circle 
              cx="60" 
              cy="60" 
              r="54"
              fill="none"
              stroke="#f0f0f0"
              strokeWidth="12"
            />
            
            {/* Progress arc - calculate the correct arc based on percentage */}
            <circle
              cx="60"
              cy="60"
              r="54"
              fill="none"
              stroke="#4285F4"
              strokeWidth="12"
              strokeLinecap="round"
              strokeDasharray={`${occupancyRate * 3.39} 339`}
              strokeDashoffset="84.75"
              transform="rotate(-90 60 60)"
            />
            
            {/* Center text */}
            <text 
              x="60" 
              y="55" 
              textAnchor="middle" 
              dominantBaseline="middle"
              className="fill-gray-700 text-2xl font-medium"
              style={{ fontSize: '24px' }}
            >
              {occupancyRate}%
            </text>
            <text 
              x="60" 
              y="75" 
              textAnchor="middle" 
              dominantBaseline="middle"
              className="fill-gray-500"
              style={{ fontSize: '12px' }}
            >
              Occupancy
            </text>
          </svg>
        </div>
        
        <div className="grid grid-cols-2 w-full gap-4 mt-2">
          <div className="flex flex-col items-center p-3 rounded-md bg-blue-50">
            <span className="text-sm text-gray-500">Occupied</span>
            <div className="flex items-center mt-1">
              <AiOutlineHome className="text-blue-500 mr-1" />
              <span className="text-lg font-medium text-gray-700">{occupiedUnits}</span>
            </div>
          </div>
          
          <div className="flex flex-col items-center p-3 rounded-md bg-gray-50">
            <span className="text-sm text-gray-500">Vacant</span>
            <div className="flex items-center mt-1">
              <AiOutlineHome className="text-gray-400 mr-1" />
              <span className="text-lg font-medium text-gray-700">{vacantUnits}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default OccupancyRateCard; 