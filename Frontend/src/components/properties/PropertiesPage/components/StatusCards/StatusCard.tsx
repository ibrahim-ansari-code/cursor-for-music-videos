import React from 'react';

export interface StatusCardProps {
  title: string;
  count: number;
  iconBgColor?: string;
  textColor?: string;
  onClick: () => void;
  icon: React.ReactNode;
  isLoading?: boolean;
  sparklineColor?: string;
}

export const StatusCard: React.FC<StatusCardProps> = ({
  title,
  count,
  iconBgColor = 'bg-white',
  onClick,
  icon,
  isLoading = false,
  sparklineColor = 'from-gray-200 to-gray-300 dark:from-gray-800',
}) => (
  <div
    className="kpi-card cursor-pointer"
    onClick={onClick}
  >
    <div className="flex items-center">
      <div className={`flex-shrink-0 ${iconBgColor} rounded-md p-3`}>{icon}</div>
      <div className="ml-5 w-0 flex-1">
        <dl>
          <dt className="text-sm font-medium text-gray-500 dark:text-gray-400 truncate">
            {title}
          </dt>
          <dd>
            {isLoading ? (
              <div className="animate-pulse h-6 w-8 bg-gray-200 dark:bg-gray-700 rounded transition-colors"></div>
            ) : (
              <div className="kpi-number">{count}</div>
            )}
          </dd>
        </dl>
      </div>
    </div>
    {/* Tiny sparkline placeholder */}
    <div className={`kpi-sparkline bg-gradient-to-r ${sparklineColor} rounded opacity-30 mt-3`}></div>
  </div>
);