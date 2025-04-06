import React, { useState, useContext } from 'react';
import { NavLink } from 'react-router-dom';
import { AuthContext } from '../App';

const Sidebar = () => {
  const { user } = useContext(AuthContext);
  const [collapsed, setCollapsed] = useState(false);

  // Navigation items
  const navigation = [
    { name: 'Dashboard', path: '/dashboard', icon: 'fa-gauge-high' },
    { name: 'Landlords', path: '/landlords', icon: 'fa-user-tie' },
    { name: 'Tenants', path: '/tenants', icon: 'fa-users' },
    { name: 'Properties', path: '/properties', icon: 'fa-building' },
    { name: 'Leases', path: '/leases', icon: 'fa-file-contract' },
    { name: 'Contracts', path: '/contracts', icon: 'fa-file-signature' },
    { name: 'Accounting', path: '/accounting', icon: 'fa-chart-line' },
    { name: 'Reports', path: '/reports', icon: 'fa-file-lines' },
    { name: 'Maintenance', path: '/maintenance', icon: 'fa-screwdriver-wrench' },
    { name: 'Messages', path: '/messages', icon: 'fa-envelope' },
    { name: 'Settings', path: '/settings', icon: 'fa-gear' },
  ];

  // Management section
  const managementSection = [
    { name: 'Accounting', path: '/accounting', icon: 'fa-calculator' },
    { name: 'Reports', path: '/reports', icon: 'fa-chart-pie' },
    { name: 'Maintenance', path: '/maintenance', icon: 'fa-wrench' },
  ];

  // Configuration section
  const configSection = [
    { name: 'Settings', path: '/settings', icon: 'fa-gear' },
    { name: 'Integrations', path: '/integrations', icon: 'fa-plug' },
  ];

  return (
    <aside className={`bg-white border-r border-gray-200 transition-all duration-300 ${collapsed ? 'w-16' : 'w-64'}`}>
      <div className="h-full flex flex-col">
        {/* Logo */}
        <div className={`flex items-center h-16 px-3 ${collapsed ? 'justify-center' : 'justify-between'}`}>
          {!collapsed && (
            <div className="flex-1 flex items-center justify-start pr-2">
              <img 
                src="/brandmark-design.svg" 
                alt="Brikli Logo" 
                title="Brikli"
                className="h-8 w-48 object-contain object-left"
              />
            </div>
          )}
          {collapsed && (
            <img 
              src="/brandmark-design.svg" 
              alt="Brikli Logo" 
              title="Brikli"
              className="h-10 w-10 object-contain"
            />
          )}
          
          <button
            onClick={() => setCollapsed(!collapsed)}
            className="text-gray-500 hover:text-gray-800 p-1"
          >
            <i className={`fas ${collapsed ? 'fa-angles-right' : 'fa-angles-left'}`}></i>
          </button>
        </div>

        {/* Navigation */}
        <div className="flex-1 overflow-y-auto py-2">
          <nav className="px-2 space-y-1">
            {/* Overview section */}
            <div className={`${collapsed ? 'px-0' : 'px-3'} mb-2`}>
              {!collapsed && <p className="text-xs font-medium text-gray-400 uppercase tracking-wider">OVERVIEW</p>}
              {collapsed && <div className="border-t border-gray-200 my-2"></div>}
            </div>
            
            {/* Dashboard link */}
            <NavLink
              to="/dashboard"
              className={({ isActive }) => 
                `${isActive ? 'bg-gray-100 text-gray-900' : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'} 
                group flex items-center px-2 py-2 text-sm font-medium rounded-md`
              }
            >
              <i className={`fas fa-gauge-high mr-3 text-gray-400 group-hover:text-gray-500 ${collapsed ? 'ml-1.5' : ''}`}></i>
              {!collapsed && <span>Dashboard</span>}
            </NavLink>
            
            {/* Applications link */}
            <NavLink
              to="/applications"
              className={({ isActive }) => 
                `${isActive ? 'bg-gray-100 text-gray-900' : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'} 
                group flex items-center px-2 py-2 text-sm font-medium rounded-md`
              }
            >
              <i className={`fas fa-window-restore mr-3 text-gray-400 group-hover:text-gray-500 ${collapsed ? 'ml-1.5' : ''}`}></i>
              {!collapsed && <span>Applications</span>}
            </NavLink>
            
            {/* Core links */}
            {[
              { path: '/landlords', icon: 'fa-user-tie', label: 'Landlords' },
              { path: '/tenants', icon: 'fa-users', label: 'Tenants' },
              { path: '/properties', icon: 'fa-building', label: 'Properties' },
              { path: '/contracts', icon: 'fa-file-signature', label: 'Contracts' },
            ].map((item) => (
              <NavLink
                key={item.path}
                to={item.path}
                className={({ isActive }) => 
                  `${isActive ? 'bg-gray-100 text-gray-900' : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'} 
                  group flex items-center px-2 py-2 text-sm font-medium rounded-md`
                }
              >
                <i className={`fas ${item.icon} mr-3 text-gray-400 group-hover:text-gray-500 ${collapsed ? 'ml-1.5' : ''}`}></i>
                {!collapsed && <span>{item.label}</span>}
              </NavLink>
            ))}
            
            {/* Management section */}
            <div className={`${collapsed ? 'px-0' : 'px-3'} mt-4 mb-2`}>
              {!collapsed && <p className="text-xs font-medium text-gray-400 uppercase tracking-wider">MANAGEMENT</p>}
              {collapsed && <div className="border-t border-gray-200 my-2"></div>}
            </div>
            
            {/* Management links */}
            {managementSection.map((item) => (
              <NavLink
                key={item.path}
                to={item.path}
                className={({ isActive }) => 
                  `${isActive ? 'bg-gray-100 text-gray-900' : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'} 
                  group flex items-center px-2 py-2 text-sm font-medium rounded-md`
                }
              >
                <i className={`fas ${item.icon} mr-3 text-gray-400 group-hover:text-gray-500 ${collapsed ? 'ml-1.5' : ''}`}></i>
                {!collapsed && <span>{item.name}</span>}
              </NavLink>
            ))}
            
            {/* Configuration section */}
            <div className={`${collapsed ? 'px-0' : 'px-3'} mt-4 mb-2`}>
              {!collapsed && <p className="text-xs font-medium text-gray-400 uppercase tracking-wider">CONFIGURATION</p>}
              {collapsed && <div className="border-t border-gray-200 my-2"></div>}
            </div>
            
            {/* Configuration links */}
            {configSection.map((item) => (
              <NavLink
                key={item.path}
                to={item.path}
                className={({ isActive }) => 
                  `${isActive ? 'bg-gray-100 text-gray-900' : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'} 
                  group flex items-center px-2 py-2 text-sm font-medium rounded-md`
                }
              >
                <i className={`fas ${item.icon} mr-3 text-gray-400 group-hover:text-gray-500 ${collapsed ? 'ml-1.5' : ''}`}></i>
                {!collapsed && <span>{item.name}</span>}
              </NavLink>
            ))}
          </nav>
        </div>
        
        {/* Footer */}
        <div className="p-4 border-t border-gray-200">
          {!collapsed ? (
            <button
              className="w-full flex items-center justify-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700"
            >
              <i className="fas fa-user-plus mr-2"></i>
              Invite
            </button>
          ) : (
            <button
              className="w-full flex items-center justify-center p-2 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700"
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
