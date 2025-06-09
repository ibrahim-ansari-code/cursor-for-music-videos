import React from "react";
import PropTypes from "prop-types";

const colorClasses = {
  blue: { ring: "ring-blue-500", bg: "bg-blue-100", text: "text-blue-600" },
  green: { ring: "ring-green-500", bg: "bg-green-100", text: "text-green-600" },
  yellow: {
    ring: "ring-yellow-500",
    bg: "bg-yellow-100",
    text: "text-yellow-600",
  },
  red: { ring: "ring-red-500", bg: "bg-red-100", text: "text-red-600" },
};

const StatusCard = ({ title, count, icon, color, onClick, active }) => (
   <button
     className={`bg-white shadow rounded-lg p-4 cursor-pointer transition-all duration-300 w-full text-left ${
      active ? `ring-2 ${colorClasses[color]?.ring || 'ring-gray-500'}` : "hover:shadow-md"
     }`}
     onClick={onClick}
     aria-label={`${title}: ${count} items`}
    disabled={!onClick}
   >
     <div className="flex items-center">
       <div
        className={`flex-shrink-0 ${colorClasses[color]?.bg || 'bg-gray-100'} rounded-md p-3`}
       >
        <i className={`fas ${icon} fa-lg ${colorClasses[color]?.text || 'text-gray-600'}`} />
       </div>
      <div className="ml-4">
        <p className="text-sm font-medium text-gray-500">{title}</p>
        <p className="text-2xl font-bold text-gray-800">{count}</p>
      </div>
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
