import React, { useState, useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { useNavigate, Link } from 'react-router-dom';
import { 
  Home, CreditCard, FileText, Wrench, Bell, Settings, 
  Calendar, AlertCircle,
  ChevronRight, Menu, X, LogOut, User
} from 'lucide-react';
import { cn } from '../utils/classNames';

/**
 * Dashboard Component
 * Main landing page for authenticated tenants
 * Follows modern SaaS dashboard patterns with card-based layout
 */
const Dashboard = () => {
  const { user, signOut } = useAuth();
  const navigate = useNavigate();
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [loading, setLoading] = useState(true);

  // Dashboard data will be loaded from API in future implementation
  // const [dashboardData, setDashboardData] = useState(null);

  useEffect(() => {
    // TODO: Load dashboard data from API
    setLoading(false);
  }, []);

  const handleSignOut = async () => {
    await signOut();
    navigate('/login');
  };

  const navigation = [
    { name: 'Dashboard', icon: Home, href: '/dashboard', current: true },
    { name: 'Rent & Payments', icon: CreditCard, href: '/payments', current: false },
    { name: 'Lease Documents', icon: FileText, href: '/documents', current: false },
    { name: 'Maintenance', icon: Wrench, href: '/maintenance', current: false },
    { name: 'Notifications', icon: Bell, href: '/notifications', current: false, badge: 3 },
  ];

  const InfoCard = ({ title, value, subtitle, icon: Icon, status, action }) => (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 hover:shadow-md transition-shadow">
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <p className="text-sm font-medium text-gray-600">{title}</p>
          <p className="mt-2 text-2xl font-bold text-gray-900">{value}</p>
          {subtitle && (
            <p className="mt-1 text-sm text-gray-500">{subtitle}</p>
          )}
        </div>
        {Icon && (
          <div className={cn(
            "p-3 rounded-lg",
            status === 'active' ? "bg-green-100" : 
            status === 'warning' ? "bg-yellow-100" : 
            status === 'paid' ? "bg-brand-teal/10" :
            "bg-gray-100"
          )}>
            <Icon className={cn(
              "h-6 w-6",
              status === 'active' ? "text-green-600" : 
              status === 'warning' ? "text-yellow-600" : 
              status === 'paid' ? "text-brand-teal" :
              "text-gray-600"
            )} />
          </div>
        )}
      </div>
      {action && (
        <button 
          onClick={action.onClick}
          className="mt-4 text-sm font-medium text-brand-teal hover:text-brand-green transition-colors flex items-center"
        >
          {action.label}
          <ChevronRight className="ml-1 h-4 w-4" />
        </button>
      )}
    </div>
  );

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-brand-teal"></div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 flex">
      {/* Mobile sidebar backdrop */}
      {sidebarOpen && (
        <div 
          className="fixed inset-0 bg-gray-900 bg-opacity-50 z-40 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Sidebar */}
      <div className={cn(
        "fixed inset-y-0 left-0 z-50 w-72 bg-white shadow-xl transform transition-transform duration-300 lg:relative lg:translate-x-0",
        sidebarOpen ? "translate-x-0" : "-translate-x-full"
      )}>
        <div className="flex h-full flex-col">
          {/* Logo */}
          <div className="flex h-16 items-center px-6">
            <img src="/BrikliTransparent.png" alt="Brikli" className="h-8 w-auto" />
            <button
              onClick={() => setSidebarOpen(false)}
              className="ml-auto lg:hidden"
            >
              <X className="h-6 w-6 text-gray-400" />
            </button>
          </div>

          {/* Navigation */}
          <nav className="flex-1 space-y-1 px-3 py-4">
            <div className="space-y-1">
              <p className="px-3 text-xs font-semibold text-gray-400 uppercase tracking-wider">
                Overview
              </p>
              {navigation.map((item) => (
                <Link
                  key={item.name}
                  to={item.href}
                  className={cn(
                    "group flex items-center px-3 py-2 text-sm font-medium rounded-lg transition-colors",
                    item.current
                      ? "bg-teal-50 text-teal-700"
                      : "text-gray-700 hover:bg-gray-100"
                  )}
                >
                  <item.icon className="mr-3 h-5 w-5 flex-shrink-0" />
                  {item.name}
                  {item.badge && (
                    <span className="ml-auto inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-800">
                      {item.badge}
                    </span>
                  )}
                </Link>
              ))}
            </div>

            <div className="mt-8">
              <p className="px-3 text-xs font-semibold text-gray-400 uppercase tracking-wider">
                Configuration
              </p>
              <Link
                to="/settings"
                className="mt-1 group flex items-center px-3 py-2 text-sm font-medium text-gray-700 rounded-lg hover:bg-gray-100 transition-colors"
              >
                <Settings className="mr-3 h-5 w-5 flex-shrink-0" />
                Settings
              </Link>
            </div>
          </nav>

        </div>
      </div>

      {/* Main content */}
      <div className="flex-1 flex flex-col lg:ml-0">
        {/* Top bar */}
        <header className="sticky top-0 z-30 bg-white border-b border-gray-200">
          <div className="flex items-center justify-between h-16 px-4 sm:px-6 lg:px-8">
            <div className="flex items-center">
              <button
                onClick={() => setSidebarOpen(true)}
                className="lg:hidden"
              >
                <Menu className="h-6 w-6 text-gray-600" />
              </button>
              <h1 className="ml-3 lg:ml-0 text-2xl font-bold text-gray-900">Dashboard</h1>
            </div>
            
            {/* User menu */}
            <div className="flex items-center space-x-4">
              <button className="relative p-2 text-gray-600 hover:text-gray-900">
                <Bell className="h-6 w-6" />
                <span className="absolute top-0 right-0 block h-2 w-2 rounded-full bg-red-400 ring-2 ring-white" />
              </button>
              
              <div className="relative group">
                <button className="flex items-center space-x-3 p-2 rounded-lg hover:bg-gray-100 transition-colors">
                  <div className="h-8 w-8 rounded-full bg-teal-100 flex items-center justify-center">
                    <User className="h-5 w-5 text-teal-700" />
                  </div>
                  <span className="hidden sm:block text-sm font-medium text-gray-700">
                    {user?.tenant?.first_name || 'John'} {user?.tenant?.last_name || 'Doe'}
                  </span>
                </button>
                
                {/* Dropdown menu */}
                <div className="absolute right-0 mt-2 w-48 rounded-lg bg-white shadow-lg border border-gray-200 opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all">
                  <Link to="/settings" className="block px-4 py-2 text-sm text-gray-700 hover:bg-gray-100">
                    Settings
                  </Link>
                  <button 
                    onClick={handleSignOut}
                    className="w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 flex items-center"
                  >
                    <LogOut className="mr-2 h-4 w-4" />
                    Logout
                  </button>
                </div>
              </div>
            </div>
          </div>
        </header>

        {/* Page content */}
        <main className="p-4 sm:p-6 lg:p-8">
          {/* Welcome section */}
          <div className="mb-8">
            <h2 className="text-3xl font-bold text-gray-900">
              Welcome back, {user?.tenant?.first_name || 'Tenant'}!
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
              icon={Home}
              action={{
                label: "View Lease",
                onClick: () => navigate('/documents')
              }}
            />
            
            <InfoCard
              title="Monthly Rent"
              value="Loading..."
              subtitle="Rent information will be loaded"
              icon={CreditCard}
              action={{
                label: "Pay Now",
                onClick: () => navigate('/payments')
              }}
            />
            
            <InfoCard
              title="Next Payment"
              value="Loading..."
              subtitle="Payment information will be loaded"
              icon={Calendar}
            />
            
            <InfoCard
              title="Maintenance Requests"
              value="Loading..."
              subtitle="Maintenance data will be loaded"
              icon={Wrench}
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
            <Link
              to="/payments"
              className="relative group bg-white p-6 rounded-xl shadow-sm border border-gray-200 hover:shadow-md transition-all"
            >
              <div className="flex items-center">
                <div className="flex-shrink-0">
                  <CreditCard className="h-8 w-8 text-brand-teal" />
                </div>
                <div className="ml-4">
                  <h3 className="text-lg font-medium text-gray-900">Make a Payment</h3>
                  <p className="mt-1 text-sm text-gray-500">Pay rent or other charges</p>
                </div>
                <ChevronRight className="ml-auto h-5 w-5 text-gray-400 group-hover:text-gray-600" />
              </div>
            </Link>

            <Link
              to="/maintenance"
              className="relative group bg-white p-6 rounded-xl shadow-sm border border-gray-200 hover:shadow-md transition-all"
            >
              <div className="flex items-center">
                <div className="flex-shrink-0">
                  <Wrench className="h-8 w-8 text-brand-teal" />
                </div>
                <div className="ml-4">
                  <h3 className="text-lg font-medium text-gray-900">Request Maintenance</h3>
                  <p className="mt-1 text-sm text-gray-500">Submit a new maintenance request</p>
                </div>
                <ChevronRight className="ml-auto h-5 w-5 text-gray-400 group-hover:text-gray-600" />
              </div>
            </Link>

            <Link
              to="/documents"
              className="relative group bg-white p-6 rounded-xl shadow-sm border border-gray-200 hover:shadow-md transition-all"
            >
              <div className="flex items-center">
                <div className="flex-shrink-0">
                  <FileText className="h-8 w-8 text-brand-teal" />
                </div>
                <div className="ml-4">
                  <h3 className="text-lg font-medium text-gray-900">View Documents</h3>
                  <p className="mt-1 text-sm text-gray-500">Access lease and other documents</p>
                </div>
                <ChevronRight className="ml-auto h-5 w-5 text-gray-400 group-hover:text-gray-600" />
              </div>
            </Link>
          </div>
        </main>
      </div>
    </div>
  );
};

export default Dashboard; 