import React, { useState } from 'react';
import { NavLink } from 'react-router-dom';
import LazyImage from '@/components/ui/LazyImage';
import { 
  FaTachometerAlt, 
  FaCreditCard, 
  FaFileSignature, 
  FaWrench, 
  FaBell, 
  FaCog,
  FaAngleDoubleLeft,
  FaAngleDoubleRight
} from 'react-icons/fa';
import type { IconType } from 'react-icons';

interface NavItem {
  name: string;
  path: string;
  icon: IconType;
}

const Sidebar: React.FC = React.memo(() => {
  const [collapsed, setCollapsed] = useState<boolean>(false);

  // Navigation items organized by section
  const overviewItems: NavItem[] = [
    { name: "Dashboard", path: "/dashboard", icon: FaTachometerAlt },
    { name: "Rent & Payments", path: "/payments", icon: FaCreditCard },
    { name: "Lease Documents", path: "/documents", icon: FaFileSignature },
    { name: "Maintenance", path: "/maintenance", icon: FaWrench },
    { name: "Notifications", path: "/notifications", icon: FaBell },
  ];

  // Configuration section
  const configItems: NavItem[] = [
    { name: "Settings", path: "/settings", icon: FaCog },
  ];

  // Function to render nav items
  const renderNavItems = (items: NavItem[]) => {
    return items.map((item) => (
      <NavLink
        key={item.path}
        to={item.path}
        className={({ isActive }) =>
          `${isActive
            ? "bg-teal-50 text-teal-700 border-r-2 border-teal-600"
            : "text-gray-600 hover:bg-gray-50 hover:text-gray-900"
          } 
          group flex items-center py-3 px-3 text-sm font-medium rounded-lg transition-all duration-200`
        }
      >
        <div className="flex items-center w-full">
          <div className={`${collapsed ? "mx-auto" : "w-6 text-center"}`}>
            <item.icon 
              className="text-gray-400 group-hover:text-gray-600 transition-colors" 
              aria-hidden="true"
            />
          </div>
          {!collapsed && (
            <span className="ml-3">{item.name}</span>
          )}
          {collapsed && (
            <span className="sr-only">{item.name}</span>
          )}
        </div>
      </NavLink>
    ));
  };

  // Function to render section headers
  const renderSectionHeader = (title: string) => {
    if (collapsed) {
      return <div className="my-2"></div>;
    }
    return (
      <h3 className="px-3 text-xs font-medium text-gray-400 uppercase tracking-wider mb-3 mt-3">
        {title}
      </h3>
    );
  };

  return (
    <aside
      className={`bg-white transition-all duration-300 ease-in-out h-full ${collapsed ? "w-16" : "w-64"
        }`}
    >
      <div className="h-full flex flex-col">
        {/* Logo */}
        <div className="flex items-center justify-between h-16 px-4">
          <div
            className={`flex items-center ${collapsed
              ? "w-full justify-center"
              : "flex-1 justify-start pl-0"
              }`}
          >
            <div className="flex items-center justify-center h-12">
              {!collapsed && (
                <NavLink key={"Logo-Dashboard"} to={"/dashboard"}>
                  <LazyImage
                    src="/brikli-logo-green-transparent.png"
                    alt="Brikli"
                    className="h-9 w-auto mx-auto my-4"
                    placeholder={
                      <div className="h-9 w-24 bg-gray-200 rounded animate-pulse"></div>
                    }
                  />
                </NavLink>
              )}
            </div>
          </div>
          <button
            onClick={() => setCollapsed(!collapsed)}
            className="p-1.5 rounded-md text-gray-400 hover:text-gray-500 hover:bg-gray-100 focus:outline-none shrink-0"
            aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
          >
            {collapsed ? (
              <FaAngleDoubleRight />
            ) : (
              <FaAngleDoubleLeft />
            )}
          </button>
        </div>

        {/* Navigation */}
        <div className="flex-1 overflow-y-auto">
          <nav className="space-y-2 px-2">
            {/* Overview section */}
            <div className="mb-6">
              {renderSectionHeader("OVERVIEW")}
              <div className="space-y-1.5">
                {renderNavItems(overviewItems)}
              </div>
            </div>

            {/* Configuration section */}
            <div className="mb-6">
              {renderSectionHeader("CONFIGURATION")}
              <div className="space-y-1.5">{renderNavItems(configItems)}</div>
            </div>
          </nav>
        </div>
      </div>
    </aside>
  );
});

Sidebar.displayName = 'Sidebar';

export default Sidebar;

