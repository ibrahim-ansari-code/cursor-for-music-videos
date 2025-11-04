import React from "react";
import * as Select from '@radix-ui/react-select';
import { ChevronDown, CheckCircle } from 'lucide-react';

interface Property {
  id: string;
  name: string;
}

interface ControlsBarProps {
  properties?: Property[];
  selectedProperty: string;
  onChangeProperty: (value: string) => void;
  timePeriod: string;
  onChangeTimePeriod: (value: string) => void;
  onCustomize?: () => void;
  isLoading?: boolean;
  onSetCustomRange?: (range: { start: string; end: string }) => void;
  currentRange?: { start: string; end: string };
}

const TIME_PERIODS = [
  { value: 'this_month', label: 'This Month' },
  { value: 'last_month', label: 'Last Month' },
  { value: 'this_quarter', label: 'This Quarter' },
  { value: 'last_quarter', label: 'Last Quarter' },
  { value: 'ytd', label: 'Year to Date' },
  { value: 'last_year', label: 'Last Year' },
  { value: 'custom', label: 'Custom Range' },
];

const ControlsBar: React.FC<ControlsBarProps> = ({
  properties = [],
  selectedProperty,
  onChangeProperty,
  timePeriod,
  onChangeTimePeriod,
  isLoading = false,
  onSetCustomRange,
  currentRange,
}) => {
  if (isLoading) {
    return (
      <div className="flex flex-col md:flex-row md:items-center md:justify-between">
        <div className="mt-3 md:mt-0 flex space-x-3 animate-pulse">
          <div className="h-9 w-48 bg-gray-200 dark:bg-gray-700 rounded" />
          <div className="h-9 w-44 bg-gray-200 dark:bg-gray-700 rounded" />
          <div className="h-9 w-28 bg-gray-200 dark:bg-gray-700 rounded" />
        </div>
      </div>
    );
  }

  // Get display label for selected property
  const selectedPropertyLabel = properties.find(p => p.id === selectedProperty)?.name || 'All Properties';
  
  // Get display label for selected time period
  const selectedTimePeriodLabel = TIME_PERIODS.find(p => p.value === timePeriod)?.label || 'This Month';

  return (
    <div className="flex flex-col md:flex-row md:items-center md:justify-between">
      <div className="mt-3 md:mt-0 flex flex-wrap items-center gap-3">
        {/* Property Selector */}
        <Select.Root 
          value={selectedProperty}
          onValueChange={onChangeProperty}
        >
          <Select.Trigger 
            className="w-48 px-3 py-1.5 pr-9 border border-gray-300 dark:border-gray-600 rounded-md focus:outline-none focus:ring-1 focus:ring-blue-500 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 flex items-center text-sm hover:border-gray-400 dark:hover:border-gray-500 transition-colors relative"
          >
            <Select.Value asChild>
              <span className="truncate block flex-1 text-left">{selectedPropertyLabel}</span>
            </Select.Value>
            <Select.Icon className="absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none">
              <ChevronDown className="h-4 w-4 text-gray-500 dark:text-gray-400" />
            </Select.Icon>
          </Select.Trigger>
          <Select.Portal>
            <Select.Content 
              className="overflow-hidden bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-600 shadow-lg z-[100] max-h-[300px]"
              position="popper"
              side="bottom"
              align="start"
              sideOffset={4}
            >
              <Select.Viewport className="p-1">
                {properties.map((property) => (
                  <Select.Item
                    key={property.id}
                    value={property.id}
                    className="relative flex items-center px-8 py-2 text-sm text-gray-900 dark:text-gray-100 rounded cursor-pointer hover:bg-blue-50 dark:hover:bg-blue-900/20 focus:bg-blue-50 dark:focus:bg-blue-900/20 outline-none select-none data-[state=checked]:bg-blue-50 dark:data-[state=checked]:bg-blue-900/30"
                  >
                    <Select.ItemText>
                      <span className="truncate block max-w-[180px]">{property.name}</span>
                    </Select.ItemText>
                    <Select.ItemIndicator className="absolute left-2 inline-flex items-center">
                      <CheckCircle className="h-4 w-4 text-blue-600 dark:text-blue-400" />
                    </Select.ItemIndicator>
                  </Select.Item>
                ))}
              </Select.Viewport>
            </Select.Content>
          </Select.Portal>
        </Select.Root>

        {/* Time Period Selector */}
        <Select.Root 
          value={timePeriod}
          onValueChange={onChangeTimePeriod}
        >
          <Select.Trigger 
            className="w-44 px-3 py-1.5 pr-9 border border-gray-300 dark:border-gray-600 rounded-md focus:outline-none focus:ring-1 focus:ring-blue-500 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 flex items-center text-sm hover:border-gray-400 dark:hover:border-gray-500 transition-colors relative"
          >
            <Select.Value asChild>
              <span className="truncate block flex-1 text-left">{selectedTimePeriodLabel}</span>
            </Select.Value>
            <Select.Icon className="absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none">
              <ChevronDown className="h-4 w-4 text-gray-500 dark:text-gray-400" />
            </Select.Icon>
          </Select.Trigger>
          <Select.Portal>
            <Select.Content 
              className="overflow-hidden bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-600 shadow-lg z-[100]"
              position="popper"
              side="bottom"
              align="start"
              sideOffset={4}
            >
              <Select.Viewport className="p-1">
                {TIME_PERIODS.map((period) => (
                  <Select.Item
                    key={period.value}
                    value={period.value}
                    className="relative flex items-center px-8 py-2 text-sm text-gray-900 dark:text-gray-100 rounded cursor-pointer hover:bg-blue-50 dark:hover:bg-blue-900/20 focus:bg-blue-50 dark:focus:bg-blue-900/20 outline-none select-none data-[state=checked]:bg-blue-50 dark:data-[state=checked]:bg-blue-900/30"
                  >
                    <Select.ItemText>{period.label}</Select.ItemText>
                    <Select.ItemIndicator className="absolute left-2 inline-flex items-center">
                      <CheckCircle className="h-4 w-4 text-blue-600 dark:text-blue-400" />
                    </Select.ItemIndicator>
                  </Select.Item>
                ))}
              </Select.Viewport>
            </Select.Content>
          </Select.Portal>
        </Select.Root>

        {/* Custom Date Range Inputs */}
        {timePeriod === "custom" && (
          <div className="flex items-center space-x-2">
            <input
              type="date"
              className="border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 rounded-md py-1.5 px-2 text-sm focus:outline-none focus:ring-1 focus:ring-blue-500 dark:[color-scheme:dark]"
              value={currentRange?.start || ""}
              onChange={(e) => onSetCustomRange?.({ start: e.target.value, end: currentRange?.end || "" })}
            />
            <span className="text-gray-400 dark:text-gray-500">to</span>
            <input
              type="date"
              className="border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 rounded-md py-1.5 px-2 text-sm focus:outline-none focus:ring-1 focus:ring-blue-500 dark:[color-scheme:dark]"
              value={currentRange?.end || ""}
              onChange={(e) => onSetCustomRange?.({ start: currentRange?.start || "", end: e.target.value })}
            />
          </div>
        )}
      </div>
    </div>
  );
};

export default ControlsBar;

