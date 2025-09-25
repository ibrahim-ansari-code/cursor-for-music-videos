import React from "react";
import PropTypes from "prop-types";

const colorClasses = {
  blue: { ring: "ring-blue-500 dark:ring-blue-400", bg: "bg-blue-100 dark:bg-blue-900/20", text: "text-blue-600 dark:text-blue-400" },
  green: { ring: "ring-green-500 dark:ring-green-400", bg: "bg-green-100 dark:bg-green-900/20", text: "text-green-600 dark:text-green-400" },
  yellow: {
    ring: "ring-yellow-500 dark:ring-yellow-400",
    bg: "bg-yellow-100 dark:bg-yellow-900/20",
    text: "text-yellow-600 dark:text-yellow-400",
  },
  red: { ring: "ring-red-500 dark:ring-red-400", bg: "bg-red-100 dark:bg-red-900/20", text: "text-red-600 dark:text-red-400" },
};

const StatusCard = ({ title, count, icon, color, onClick, active }) => (
   <button
     className={`kpi-card group cursor-pointer transition-all duration-300 w-full text-left ${
      active ? `ring-2 ${colorClasses[color]?.ring || 'ring-gray-500 dark:ring-gray-400'}` : "hover:shadow-lg hover:-translate-y-1"
     }`}
     onClick={onClick}
     aria-label={`${title}: ${count} items`}
    disabled={!onClick}
   >
     <div className="flex items-center justify-between">
       <div className="flex items-center">
         <div
          className={`flex-shrink-0 ${colorClasses[color]?.bg || 'bg-gray-100 dark:bg-gray-700'} rounded-md p-3 mr-4`}
         >
          <i className={`fas ${icon} fa-lg ${colorClasses[color]?.text || 'text-gray-600 dark:text-gray-400'}`} />
         </div>
        <div>
          <p className="text-sm font-medium text-gray-500 dark:text-gray-400 mb-1">{title}</p>
          <p className="kpi-number">{count}</p>
        </div>
       </div>
       <div className="kpi-sparkline bg-gradient-to-r from-blue-200 to-blue-300 dark:from-blue-800 rounded opacity-30"></div>
     </div>
  </button>
);

StatusCard.propTypes = {
  title: PropTypes.string.isRequired,
  count: PropTypes.number.isRequired,
  icon: PropTypes.string.isRequired,
  color: PropTypes.string.isRequired,
  onClick: PropTypes.func.isRequired,
  active: PropTypes.bool.isRequired,
};

export default StatusCard;
