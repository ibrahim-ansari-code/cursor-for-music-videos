import React from "react";

const UnitStatusBadge = ({ isRented, tenantName = null, size = "default" }) => {
  // Size classes
  const sizeClasses = {
    small: "px-2 py-0.5 text-xs",
    default: "px-2.5 py-1 text-sm",
    large: "px-3 py-1.5 text-base",
  };

  // Status configurations
  const statusConfig = isRented
    ? {
        bgColor: "bg-green-100",
        textColor: "text-green-800",
        borderColor: "border-green-200",
        icon: (
          <svg
            className={`${size === "small" ? "h-3 w-3" : "h-4 w-4"} mr-1`}
            fill="currentColor"
            viewBox="0 0 20 20"
          >
            <path
              fillRule="evenodd"
              d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"
              clipRule="evenodd"
            />
          </svg>
        ),
        label: tenantName ? `Rented to ${tenantName}` : "Rented",
      }
    : {
        bgColor: "bg-yellow-100",
        textColor: "text-yellow-800",
        borderColor: "border-yellow-200",
        icon: (
          <svg
            className={`${size === "small" ? "h-3 w-3" : "h-4 w-4"} mr-1`}
            fill="currentColor"
            viewBox="0 0 20 20"
          >
            <path
              fillRule="evenodd"
              d="M18 8a6 6 0 01-7.743 5.743L10 14l-1 1-1 1H6v2H2v-4l4.257-4.257A6 6 0 1118 8zm-6-4a1 1 0 100 2 2 2 0 012 2 1 1 0 102 0 4 4 0 00-4-4z"
              clipRule="evenodd"
            />
          </svg>
        ),
        label: "Vacant",
      };

  const getStatusStyle = () => {
    switch (status) {
      case 'rented':
        return 'bg-red-100 dark:bg-red-900/30 text-red-800 dark:text-red-200 border-red-200 dark:border-red-700';
      case 'vacant':
        return 'bg-green-100 dark:bg-green-900/30 text-green-800 dark:text-green-200 border-green-200 dark:border-green-700';
      default:
        return 'bg-gray-100 dark:bg-gray-700 text-gray-800 dark:text-gray-200 border-gray-200 dark:border-gray-600';
    }
  };

  return (
    <span
      className={`
        inline-flex items-center font-medium rounded-full border
        ${statusConfig.bgColor} 
        ${statusConfig.textColor} 
        ${statusConfig.borderColor}
        ${sizeClasses[size]}
      `}
    >
      {statusConfig.icon}
      {statusConfig.label}
    </span>
  );
};

export default UnitStatusBadge;