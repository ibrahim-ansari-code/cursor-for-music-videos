import React from 'react';
import { useNavigate } from 'react-router-dom';
import { FaWrench, FaChevronRight } from 'react-icons/fa';

/**
 * MaintenanceQuickAction Component
 * Quick action card for submitting maintenance requests
 */
const MaintenanceQuickAction: React.FC = () => {
  const navigate = useNavigate();

  return (
    <button
      onClick={() => navigate('/maintenance')}
      className="relative group bg-white p-6 rounded-xl shadow-sm border border-gray-200 hover:shadow-md transition-all text-left w-full cursor-pointer"
    >
      <div className="flex items-center">
        <div className="shrink-0">
          <FaWrench className="text-2xl text-gray-700" />
        </div>
        <div className="ml-4">
          <h3 className="text-lg font-medium text-gray-900">Request Maintenance</h3>
          <p className="mt-1 text-sm text-gray-500">Submit a new maintenance request</p>
        </div>
        <FaChevronRight className="ml-auto text-gray-400 group-hover:text-gray-600" />
      </div>
    </button>
  );
};

export default MaintenanceQuickAction;
