import React, { useState } from "react";
import { NavLink } from "react-router-dom";
import LazyImage from "./ui/LazyImage";

const Sidebar = React.memo(() => {
  const [collapsed, setCollapsed] = useState(false);

  // Navigation items organized by section
  const overviewItems = [
    { name: "Dashboard", path: "/dashboard", icon: "fa-gauge-high" },
    { name: "Rent & Payments", path: "/payments", icon: "fa-credit-card" },
    { name: "Lease Documents", path: "/documents", icon: "fa-file-signature" },
    { name: "Maintenance", path: "/maintenance", icon: "fa-wrench" },
    { name: "Notifications", path: "/notifications", icon: "fa-bell" },
  ];

  // Configuration section
  const configItems = [
    { name: "Settings", path: "/settings", icon: "fa-gear" },
  ];

  // Function to render nav items
  const renderNavItems = (items) => {
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
            <i
              className={`fas ${item.icon} text-gray-400 group-hover:text-gray-600 transition-colors`}
              aria-hidden="true"
            ></i>
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
  const renderSectionHeader = (title) => {
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
                    src="/BrikliTransparent.png"
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
            className="p-1.5 rounded-md text-gray-400 hover:text-gray-500 hover:bg-gray-100 focus:outline-none flex-shrink-0"
            aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
          >
            <i
              className={`fas ${collapsed ? "fa-angles-right" : "fa-angles-left"
                }`}
            ></i>
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