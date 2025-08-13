import React, { useState, useEffect } from 'react';
import PropTypes from 'prop-types';
import { useAuth } from '../hooks/useAuth';
import { useNavigate } from 'react-router-dom';
import { DashboardSkeleton } from './ui/LoadingSkeleton';
import { 
  FaHome, 
  FaCreditCard, 
  FaCalendar, 
  FaWrench, 
  FaChevronRight, 
  FaFileSignature 
} from 'react-icons/fa';

/**
 * DashboardContent Component
 * Main dashboard content extracted from the original Dashboard component
 */
const DashboardContent = React.memo(() => {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);

  const getUserFirstName = () => {
    return user?.first_name || 'Tenant';
  };

  // Dashboard data will be loaded from API in future implementation
  // const [dashboardData, setDashboardData] = useState(null);

  useEffect(() => {
    // TODO: Load dashboard data from API
    setLoading(false);
  }, []);

  const InfoCard = ({ title, value, subtitle, icon, status, action }) => (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 hover:shadow-md transition-shadow">
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <p className="text-sm font-medium text-gray-600">{title}</p>
          <p className="mt-2 text-2xl font-bold text-gray-900">{value}</p>
          {subtitle && (
            <p className="mt-1 text-sm text-gray-500">{subtitle}</p>
          )}
        </div>
        {icon && (
          <div className={`p-3 rounded-lg ${
            status === 'active' ? "bg-green-100" : 
            status === 'warning' ? "bg-yellow-100" : 
            status === 'paid' ? "bg-brand-teal/10" :
            "bg-gray-100"
          }`}>
            <icon.component className={`text-lg ${
              status === 'active' ? "text-green-600" : 
              status === 'warning' ? "text-yellow-600" : 
              status === 'paid' ? "text-brand-teal" :
              "text-gray-600"
            }`} />
          </div>
        )}
      </div>
      {action && (
        <button 
          onClick={action.onClick}
          className="mt-4 text-sm font-medium text-brand-teal hover:text-brand-green transition-colors flex items-center"
        >
          {action.label}
          <FaChevronRight className="ml-1" />
        </button>
      )}
    </div>
  );

  InfoCard.propTypes = {
    title: PropTypes.string.isRequired,
    value: PropTypes.string.isRequired,
    subtitle: PropTypes.string,
    icon: PropTypes.shape({
      component: PropTypes.elementType.isRequired
    }),
    status: PropTypes.oneOf(['active', 'warning', 'paid']),
    action: PropTypes.shape({
      label: PropTypes.string.isRequired,
      onClick: PropTypes.func.isRequired
    })
  };

  if (loading) {
    return <DashboardSkeleton />;
  }

  return (
    <>
      {/* Welcome section */}
      <div className="mb-8">
        <h2 className="text-3xl font-bold text-gray-900">
          Welcome back, {getUserFirstName()}!
        </h2>
        <p className="mt-1 text-lg text-gray-600">
          Here's an overview of your apartment and upcoming payments.
        </p>
      </div>

      {/* Placeholder for announcements - will be implemented later */}

      {/* Dashboard cards - data will be loaded from API */}
      <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-4">
        <InfoCard
          title="My Unit"
          value="Loading..."
          subtitle="Unit information will be loaded"
          icon={{ component: FaHome }}
          action={{
            label: "View Lease",
            onClick: () => navigate('/documents')
          }}
        />
        
        <InfoCard
          title="Monthly Rent"
          value="Loading..."
          subtitle="Rent information will be loaded"
          icon={{ component: FaCreditCard }}
          action={{
            label: "Pay Now",
            onClick: () => navigate('/payments')
          }}
        />
        
        <InfoCard
          title="Next Payment"
          value="Loading..."
          subtitle="Payment information will be loaded"
          icon={{ component: FaCalendar }}
        />
        
        <InfoCard
          title="Maintenance Requests"
          value="Loading..."
          subtitle="Maintenance data will be loaded"
          icon={{ component: FaWrench }}
          action={{
            label: "New Request",
            onClick: () => navigate('/maintenance')
          }}
        />
      </div>

      {/* Recent Payments Table - will be implemented with API data */}
      <div className="mt-8">
        <div className="bg-white rounded-xl shadow-sm border border-gray-200">
          <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between">
            <h3 className="text-lg font-semibold text-gray-900">Recent Payments</h3>
            <button 
              onClick={() => navigate('/payments')}
              className="text-sm font-medium text-brand-teal hover:text-brand-green transition-colors"
            >
              View All
            </button>
          </div>
          
          <div className="p-8 text-center text-gray-500">
            <p>Payment history will be loaded from your account</p>
          </div>
        </div>
      </div>

      {/* Quick Actions */}
      <div className="mt-8 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <button
          onClick={() => navigate('/payments')}
          className="relative group bg-white p-6 rounded-xl shadow-sm border border-gray-200 hover:shadow-md transition-all text-left"
        >
          <div className="flex items-center">
            <div className="flex-shrink-0">
              <FaCreditCard className="text-2xl text-brand-teal" />
            </div>
            <div className="ml-4">
              <h3 className="text-lg font-medium text-gray-900">Make a Payment</h3>
              <p className="mt-1 text-sm text-gray-500">Pay rent or other charges</p>
            </div>
            <FaChevronRight className="ml-auto text-gray-400 group-hover:text-gray-600" />
          </div>
        </button>

        <button
          onClick={() => navigate('/maintenance')}
          className="relative group bg-white p-6 rounded-xl shadow-sm border border-gray-200 hover:shadow-md transition-all text-left"
        >
          <div className="flex items-center">
            <div className="flex-shrink-0">
              <FaWrench className="text-2xl text-brand-teal" />
            </div>
            <div className="ml-4">
              <h3 className="text-lg font-medium text-gray-900">Request Maintenance</h3>
              <p className="mt-1 text-sm text-gray-500">Submit a new maintenance request</p>
            </div>
            <FaChevronRight className="ml-auto text-gray-400 group-hover:text-gray-600" />
          </div>
        </button>

        <button
          onClick={() => navigate('/documents')}
          className="relative group bg-white p-6 rounded-xl shadow-sm border border-gray-200 hover:shadow-md transition-all text-left"
        >
          <div className="flex items-center">
            <div className="flex-shrink-0">
              <FaFileSignature className="text-2xl text-brand-teal" />
            </div>
            <div className="ml-4">
              <h3 className="text-lg font-medium text-gray-900">View Documents</h3>
              <p className="mt-1 text-sm text-gray-500">Access lease and other documents</p>
            </div>
            <FaChevronRight className="ml-auto text-gray-400 group-hover:text-gray-600" />
          </div>
        </button>
      </div>
    </>
  );
});

DashboardContent.displayName = 'DashboardContent';

export default DashboardContent;