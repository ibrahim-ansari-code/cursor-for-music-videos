import React from "react";
import CountUp from "react-countup";

const YTDCard = ({ data }) => {
  const { revenue = 0, expenses = 0, netIncome = 0 } = data || {};

  return (
    <div className="kpi-card group h-full flex flex-col">
      <div className="flex items-center mb-4">
        <h2 className="text-base font-medium text-gray-800 dark:text-gray-200 whitespace-nowrap">Year to Date</h2>
        <div className="kpi-sparkline bg-gradient-to-r from-green-200 to-green-300 dark:from-green-800"></div>
      </div>

      <div className="space-y-4 flex-grow">
        {/* Revenue Section */}
        <div className="text-center">
          <p className="text-xs font-medium text-gray-600 dark:text-gray-400 uppercase tracking-wider mb-1">
            Revenue
          </p>
          <p className="kpi-number tabular-nums">
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
        <div className="text-center dark-divider border-t pt-4">
          <p className="text-xs font-medium text-gray-600 dark:text-gray-400 uppercase tracking-wider mb-1">
            Expenses
          </p>
          <p className="kpi-number tabular-nums">
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
        <div className="text-center dark-divider border-t pt-4">
          <p className="text-xs font-medium text-gray-600 dark:text-gray-400 uppercase tracking-wider mb-1">
            Net Income
          </p>
          <p
            className={`kpi-number tabular-nums transition-colors duration-200 ${
              netIncome >= 0 ? "text-green-600 dark:text-green-400" : "text-red-600 dark:text-red-400"
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