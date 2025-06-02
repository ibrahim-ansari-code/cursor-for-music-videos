import React from "react";

const StatCard = ({
  title,
  value,
  icon,
  bgColor = "bg-gray-100",
  textColor = "text-gray-900",
  onClick,
}) => (
  <div
    className={`bg-white overflow-hidden shadow rounded-lg ${
      onClick ? "cursor-pointer hover:shadow-md transition-shadow" : ""
    }`}
    onClick={onClick}
  >
    <div className="px-4 py-5 sm:p-6">
      <div className="flex items-center">
        <div className={`flex-shrink-0 ${bgColor} rounded-md p-3`}>
          {icon
            ? React.cloneElement(icon, { className: "h-6 w-6 " + textColor })
            : null}
        </div>
        <div className="ml-5 w-0 flex-1">
          <dl>
            <dt className="text-sm font-medium text-gray-500 truncate">
              {title}
            </dt>
            <dd>
              <div className={`text-lg font-medium ${textColor}`}>{value}</div>
            </dd>
          </dl>
        </div>
      </div>
    </div>
  </div>
);

export default StatCard;
