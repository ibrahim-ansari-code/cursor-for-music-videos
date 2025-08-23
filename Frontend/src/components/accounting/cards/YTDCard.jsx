import React from "react";
import CountUp from "react-countup";

const YTDCard = ({ data }) => {
  const { revenue = 0, expenses = 0, netIncome = 0 } = data || {};

  return (
    <div className="bg-white p-4 rounded-lg shadow-sm hover:shadow-md transition-shadow duration-200 h-full flex flex-col">
      <h2 className="text-base font-medium text-gray-800 mb-4">Year to Date</h2>

      <div className="space-y-4 flex-grow">
        {/* Revenue Section */}
        <div className="text-center">
          <p className="text-xs font-medium text-gray-600 uppercase tracking-wider mb-1">
            Revenue
          </p>
          <p className="text-2xl font-semibold text-gray-900 tabular-nums">
            $<CountUp 
              end={revenue} 
              duration={1.5} 
              decimals={2} 
              separator="," 
              preserveValue={true}
            />
          </p>
        </div>

        {/* Expenses Section */}
        <div className="text-center border-t border-gray-100 pt-4">
          <p className="text-xs font-medium text-gray-600 uppercase tracking-wider mb-1">
            Expenses
          </p>
          <p className="text-2xl font-semibold text-gray-900 tabular-nums">
            $<CountUp 
              end={expenses} 
              duration={1.5} 
              decimals={2} 
              separator="," 
              preserveValue={true}
            />
          </p>
        </div>

        {/* Net Income Section */}
        <div className="text-center border-t border-gray-100 pt-4">
          <p className="text-xs font-medium text-gray-600 uppercase tracking-wider mb-1">
            Net Income
          </p>
          <p
            className={`text-2xl font-semibold tabular-nums transition-colors duration-200 ${
              netIncome >= 0 ? "text-green-600" : "text-red-600"
            }`}
          >
            {netIncome >= 0 ? "+" : "-"}$<CountUp
              end={Math.abs(netIncome)}
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

export default YTDCard;
