import React from "react";

const ControlsBar = ({
  properties = [],
  selectedProperty,
  onChangeProperty,
  timePeriod,
  onChangeTimePeriod,
  onCustomize,
  isLoading = false,
  onSetCustomRange,
  currentRange,
}) => {
  if (isLoading) {
    return (
      <div className="flex flex-col md:flex-row md:items-center md:justify-between">
        <div className="mt-3 md:mt-0 flex space-x-3 animate-pulse">
          <div className="h-9 w-48 bg-gray-200 rounded" />
          <div className="h-9 w-44 bg-gray-200 rounded" />
          <div className="h-9 w-28 bg-gray-200 rounded" />
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col md:flex-row md:items-center md:justify-between">
      <div className="mt-3 md:mt-0 flex space-x-3">
        <select
          className="border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 rounded-md py-1.5 pl-3 pr-10 text-sm focus:outline-none focus:ring-1 focus:ring-blue-500 w-48 truncate"
          value={selectedProperty}
          onChange={(e) => onChangeProperty?.(e.target.value)}
        >
          {properties.map((property) => (
            <option key={property.id} value={property.id}>
              {property.name}
            </option>
          ))}
        </select>

        <select
          className="border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 rounded-md py-1.5 pl-3 pr-10 text-sm focus:outline-none focus:ring-1 focus:ring-blue-500 w-44"
          value={timePeriod}
          onChange={(e) => onChangeTimePeriod?.(e.target.value)}
        >
          <option value="this_month">This Month</option>
          <option value="last_month">Last Month</option>
          <option value="this_quarter">This Quarter</option>
          <option value="last_quarter">Last Quarter</option>
          <option value="ytd">Year to Date</option>
          <option value="last_year">Last Year</option>
          <option value="custom">Custom Range</option>
        </select>

        {timePeriod === "custom" && (
          <div className="flex items-center space-x-2">
            <input
              type="date"
              className="border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 rounded-md py-1.5 px-2 text-sm focus:outline-none focus:ring-1 focus:ring-blue-500 dark:[color-scheme:dark]"
              value={currentRange?.start || ""}
              onChange={(e) => onSetCustomRange?.({ ...currentRange, start: e.target.value })}
            />
            <span className="text-gray-400 dark:text-gray-500">to</span>
            <input
              type="date"
              className="border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 rounded-md py-1.5 px-2 text-sm focus:outline-none focus:ring-1 focus:ring-blue-500 dark:[color-scheme:dark]"
              value={currentRange?.end || ""}
              onChange={(e) => onSetCustomRange?.({ ...currentRange, end: e.target.value })}
            />
          </div>
        )}

        {/* Customize button removed per request */}
      </div>
    </div>
  );
};

export default ControlsBar;
