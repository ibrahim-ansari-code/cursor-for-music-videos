import React from 'react';

export interface StatusCardProps {
  title: string;
  count: number;
  iconBgColor?: string;
  textColor?: string;
  onClick: () => void;
  icon: React.ReactNode;
  isLoading?: boolean;
}

export const StatusCard: React.FC<StatusCardProps> = ({
  title,
  count,
  iconBgColor = 'bg-white',
  textColor = 'text-gray-900',
  onClick,
  icon,
  isLoading = false,
}) => (
  <div
    className="bg-white overflow-hidden shadow rounded-lg cursor-pointer hover:shadow-md transition-shadow"
    onClick={onClick}
  >
    <div className="px-4 py-5 sm:p-6">
      <div className="flex items-center">
        <div className={`flex-shrink-0 ${iconBgColor} rounded-md p-3`}>{icon}</div>
        <div className="ml-5 w-0 flex-1">
          <dl>
            <dt className="text-sm font-medium text-gray-500 truncate">
              {title}
            </dt>
            <dd>
              {isLoading ? (
                <div className="animate-pulse h-6 w-8 bg-gray-200 rounded"></div>
              ) : (
                <div className={`text-lg font-medium ${textColor}`}>{count}</div>
              )}
            </dd>
          </dl>
        </div>
      </div>
    </div>
  </div>
);