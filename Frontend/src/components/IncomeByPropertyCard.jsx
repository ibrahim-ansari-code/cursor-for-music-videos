import React from "react";

const IncomeByPropertyCard = ({ properties = [] }) => {
  return (
    <div className="flex flex-col h-full p-4 bg-white rounded-lg shadow-sm">
      <div className="flex items-center mb-4">
        <h3 className="text-base font-medium text-gray-800">
          Income by Property
        </h3>
      </div>

      <div className="flex-1">
        <div className="h-64 w-full relative">
          {/* Legend */}
          <div className="absolute top-0 right-0 flex items-center gap-4">
            <div className="flex items-center">
              <div className="w-3 h-3 bg-blue-500 rounded-sm mr-1.5"></div>
              <span className="text-xs text-gray-600">Monthly Income</span>
            </div>
            <div className="flex items-center">
              <div className="w-3 h-3 bg-green-400 rounded-sm mr-1.5"></div>
              <span className="text-xs text-gray-600">Occupancy Rate</span>
            </div>
          </div>

          {/* Y-axis labels */}
          <div className="absolute left-0 top-4 bottom-8 flex flex-col justify-between text-xs text-gray-500 w-14">
            <div>$6,000</div>
            <div>$4,000</div>
            <div>$2,000</div>
            <div>$0</div>
          </div>

          {/* Y-axis (right) labels */}
          <div className="absolute right-0 top-4 bottom-8 flex flex-col justify-between text-xs text-gray-500 w-10">
            <div>100%</div>
            <div>50%</div>
            <div>0%</div>
          </div>

          {properties.length > 0 ? (
            <>
              {/* Chart area */}
              <div className="ml-14 mr-10 mt-4 h-52 flex items-end justify-between">
                {properties.map((property, index) => (
                  <div
                    key={property.id || index}
                    className="flex flex-col items-center relative"
                    style={{
                      width: `${100 / properties.length}%`,
                      maxWidth: "120px",
                    }}
                  >
                    <div
                      className="w-16 bg-blue-500 rounded-t-sm"
                      style={{
                        height: `${Math.min(
                          (property.monthlyIncome / 6000) * 100,
                          100
                        )}%`,
                        maxHeight: "100%",
                      }}
                    ></div>
                    <div className="mt-2 text-xs text-gray-600 text-center w-full truncate px-1">
                      {property.name}
                    </div>

                    {/* Occupancy dot */}
                    <div
                      className="absolute h-2 w-2 bg-green-400 rounded-full left-1/2 transform -translate-x-1/2"
                      style={{
                        top: `${100 - (property.occupancyRate || 0)}%`,
                      }}
                    ></div>
                  </div>
                ))}
              </div>

              {/* Occupancy Line */}
              <svg
                className="absolute inset-0 ml-14 mr-10 mt-4 h-52 pointer-events-none"
                preserveAspectRatio="none"
              >
                <path
                  d={properties
                    .map((property, index) => {
                      const x = (index / (properties.length - 1)) * 100;
                      const y = 100 - (property.occupancyRate || 0);
                      return (index === 0 ? "M" : "L") + `${x},${y}`;
                    })
                    .join(" ")}
                  fill="none"
                  stroke="#10b981"
                  strokeWidth="2"
                />
              </svg>
            </>
          ) : (
            <div className="ml-14 mr-10 mt-4 h-52 flex items-center justify-center">
              <p className="text-gray-500 text-sm">No data available</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default IncomeByPropertyCard;
