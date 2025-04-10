import React, { useContext } from 'react';
import { Outlet, useLocation } from 'react-router-dom';
import Sidebar from './Sidebar';
import { AuthContext } from '../App';

const Layout = () => {
  const { user, logout } = useContext(AuthContext);
  const location = useLocation();

  // Map routes to page titles
  const getPageTitle = (pathname) => {
    const routes = {
      '/dashboard': 'Dashboard',
      '/properties': 'Properties',
      '/leases': 'Leases',
      '/vendors': 'Vendors',
      '/accounting': 'Accounting',
      '/messages': 'Messages',
      '/applications': 'Applications',
      '/tenants': 'Tenants'
    };

    // Handle nested routes (e.g., /properties/:id)
    const basePath = '/' + pathname.split('/')[1];
    return routes[basePath] || 'Dashboard';
  };

  return (
    <div className="flex h-screen bg-gray-50">
      {/* Sidebar */}
      <Sidebar />
      
      {/* Main Content */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Header */}
        <header className="bg-white shadow-sm z-10">
          <div className="px-4 py-2 flex justify-between items-center">
            <h1 className="text-xl font-semibold text-gray-900">{getPageTitle(location.pathname)}</h1>
            
            {/* User dropdown */}
            <div className="relative">
              <div className="flex items-center space-x-3 cursor-pointer">
                <div className="h-8 w-8 rounded-full bg-gray-200 flex items-center justify-center text-gray-700">
                  {user?.first_name?.charAt(0)}{user?.last_name?.charAt(0)}
                </div>
                <div className="hidden md:block">
                  <p className="text-sm font-medium text-gray-900">{user?.first_name} {user?.last_name}</p>
                  <p className="text-xs text-gray-500 capitalize">{user?.user_type}</p>
                </div>
                <button 
                  className="text-sm text-gray-700 hover:text-gray-900 px-3 py-1 rounded hover:bg-gray-100"
                  onClick={logout}
                >
                  <i className="fas fa-sign-out-alt mr-1"></i> Logout
                </button>
              </div>
            </div>
          </div>
        </header>
        
        {/* Page content */}
        <main className="flex-1 overflow-auto bg-gray-50 p-4">
          <Outlet />
        </main>
      </div>
    </div>
  );
};

export default Layout;
