import React, { useState, useContext } from 'react';
import { NavLink } from 'react-router-dom';
import { AuthContext } from '../App';

const Sidebar = () => {
  const { user } = useContext(AuthContext);
  const [collapsed, setCollapsed] = useState(false);

  // Navigation items organized by section
  const overviewItems = [
    { name: 'Dashboard', path: '/dashboard', icon: 'fa-gauge-high' },
    { name: 'Properties', path: '/properties', icon: 'fa-building' },
    { name: 'Leases', path: '/leases', icon: 'fa-file-contract' },
    { name: 'Landlords', path: '/landlords', icon: 'fa-user-tie' },
    { name: 'Tenants', path: '/tenants', icon: 'fa-users' },
    { name: 'Contracts', path: '/contracts', icon: 'fa-file-signature' },
  ];

  // Management section
  const managementItems = [
    { name: 'Accounting', path: '/accounting', icon: 'fa-calculator' },
    { name: 'Reports', path: '/reports', icon: 'fa-chart-pie' },
    { name: 'Maintenance', path: '/maintenance', icon: 'fa-wrench' },
  ];

  // Configuration section
  const configItems = [
    { name: 'Settings', path: '/settings', icon: 'fa-gear' },
    { name: 'Integrations', path: '/integrations', icon: 'fa-plug' },
  ];

  // Function to render nav items
  const renderNavItems = (items) => {
    return items.map((item) => (
      <NavLink
        key={item.path}
        to={item.path}
        className={({ isActive }) => 
          `${isActive ? 'bg-gray-100 text-gray-900' : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'} 
          group flex items-center py-2 px-3 text-sm font-medium rounded-md transition-colors`
        }
      >
        <div className="flex items-center w-full">
          <div className={`${collapsed ? 'mx-auto' : 'w-6 text-center'}`}>
            <i className={`fas ${item.icon} text-gray-400 group-hover:text-gray-500`}></i>
          </div>
          {!collapsed && <span className="ml-3">{item.name}</span>}
        </div>
      </NavLink>
    ));
  };

  // Function to render section headers
  const renderSectionHeader = (title) => {
    if (collapsed) {
      return <div className="border-t border-gray-200 my-2"></div>;
    }
    return (
      <h3 className="px-3 text-xs font-medium text-gray-400 uppercase tracking-wider mb-2">
        {title}
      </h3>
    );
  };

  return (
    <aside className={`bg-white border-r border-gray-200 transition-all duration-300 ease-in-out h-full ${collapsed ? 'w-16' : 'w-64'}`}>
      <div className="h-full flex flex-col">
        {/* Logo */}
        <div className="flex items-center h-16 px-4 border-b border-gray-200">
          <div className="flex items-center">
            <img 
              src="/brikliLogo.svg" 
              alt="Brikli Logo" 
              className="h-8 w-auto"
            />
            {!collapsed && (
              <span className="ml-2 text-lg font-medium text-gray-900">Brikli</span>
            )}
          </div>
          <div className="flex-grow"></div>
          <button
            onClick={() => setCollapsed(!collapsed)}
            className="p-1.5 rounded-md text-gray-400 hover:text-gray-500 hover:bg-gray-100 focus:outline-none"
            aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
          >
            <i className={`fas ${collapsed ? 'fa-angles-right' : 'fa-angles-left'}`}></i>
          </button>
        </div>

        {/* Navigation */}
        <div className="flex-1 overflow-y-auto py-4">
          <nav className="space-y-1 px-2">
            {/* Overview section */}
            <div className="mb-6">
              {renderSectionHeader('OVERVIEW')}
              <div className="space-y-1">
                {renderNavItems(overviewItems)}
              </div>
            </div>
            
            {/* Management section */}
            <div className="mb-6">
              {renderSectionHeader('MANAGEMENT')}
              <div className="space-y-1">
                {renderNavItems(managementItems)}
              </div>
            </div>
            
            {/* Configuration section */}
            <div className="mb-6">
              {renderSectionHeader('CONFIGURATION')}
              <div className="space-y-1">
                {renderNavItems(configItems)}
              </div>
            </div>
          </nav>
        </div>
        
        {/* Footer */}
        <div className="p-4 border-t border-gray-200">
          {!collapsed ? (
            <button
              className="w-full flex items-center justify-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 transition-colors"
            >
              <i className="fas fa-user-plus mr-2"></i>
              Invite
            </button>
          ) : (
            <button
              className="w-full flex items-center justify-center p-2 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 transition-colors"
              aria-label="Invite"
            >
              <i className="fas fa-user-plus"></i>
            </button>
          )}
        </div>
      </div>
    </aside>
  );
};

export default Sidebar;
