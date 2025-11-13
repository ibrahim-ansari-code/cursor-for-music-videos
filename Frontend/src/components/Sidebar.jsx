import React, { useState } from "react";
import { NavLink } from "react-router-dom";
import AskAIModal from "./AskAIModal";
import "../styles/ui-feedback.css";
import { Bot } from 'lucide-react';

const Sidebar = () => {
  const [collapsed, setCollapsed] = useState(false);
  const [showAskModal, setShowAskModal] = useState(false);

  // Navigation items organized by section
  const overviewItems = [
    { name: "Dashboard", path: "/dashboard", icon: "fa-gauge-high" },
    { name: "Properties", path: "/properties", icon: "fa-building" },
    { name: "Tenants", path: "/tenants", icon: "fa-users" },
    { name: "Leases", path: "/leases", icon: "fa-file-signature" },
  ];

  // Management section - reordered as requested
  const managementItems = [
    { name: "Accounting", path: "/accounting", icon: "fa-calculator" },
    { name: "Calendar", path: "/calendar", icon: "fa-calendar" },
    { name: "Maintenance", path: "/maintenance", icon: "fa-wrench" },
    { name: "Vendors", path: "/vendors", icon: "fa-address-book" },
  ];

  // Configuration section
  const configItems = [
    { name: "Integrations", path: "/integrations", icon: "fa-plug" },
    { name: "Settings", path: "/settings", icon: "fa-gear" },
  ];

  // Function to render nav items
  const renderNavItems = (items) => {
    return items.map((item) => (
      <NavLink
        key={item.path}
        to={item.path}
        onMouseEnter={() => {
          if (item.path.startsWith('/accounting') && typeof window !== 'undefined') {
            Promise.resolve().then(() => {
              import('../pages/Accounting');
              import('../components/accounting/OverviewTab');
              import('../components/accounting/PaymentsTab');
              import('../components/accounting/ExpensesTab');
              import('../components/accounting/InvoicesTab');
              import('../components/accounting/RentTrackerTab');
            });
          }
        }}
        className={({ isActive }) =>
          `${isActive
            ? "bg-green-50 dark:bg-green-900/50 text-green-700 dark:text-green-300 border-r-2 border-green-600 dark:border-green-400 dark-shadow"
            : "text-gray-600 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700 hover:text-gray-900 dark:hover:text-white"
          } 
          group flex items-center py-3 px-3 text-sm font-medium rounded-lg transition-all duration-200`
        }
      >
        <div className="flex items-center w-full">
          <div className={`${collapsed ? "mx-auto" : "w-6 text-center"}`}>
            <i
              className={`fas ${item.icon} text-gray-400 dark:text-gray-500 group-hover:text-gray-600 dark:group-hover:text-gray-300 transition-colors`}
            ></i>
          </div>
          {!collapsed && <span className="ml-3">{item.name}</span>}
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
      <h3 className="px-3 text-xs font-medium text-gray-400 dark:text-gray-500 uppercase tracking-wider mb-3 mt-3">
        {title}
      </h3>
    );
  };

  return (
    <>
      <aside
        className={`dark-panel transition-all duration-300 ease-in-out h-full dark-divider border-r dark-shadow ${collapsed ? "w-16" : "w-64"
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
                    <img
                      src="/brikli-logo-green-transparent.png"
                      alt="Brikli"
                      className="h-8 w-auto dark:[filter:invert(1)_grayscale(1)_brightness(2)]"
                    />
                  </NavLink>
                )}
              </div>
            </div>
            <button
              onClick={() => setCollapsed(!collapsed)}
              className="p-1.5 rounded-md text-gray-400 dark:text-gray-500 hover:text-gray-500 dark:hover:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 focus:outline-none flex-shrink-0 transition-colors duration-300"
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

              {/* Management section */}
              <div className="mb-6">
                {renderSectionHeader("MANAGEMENT")}
                <div className="space-y-1.5">
                  {renderNavItems(managementItems)}
                </div>
              </div>

              {/* Configuration section */}
              <div className="mb-6">
                {renderSectionHeader("CONFIGURATION")}
                <div className="space-y-1.5">{renderNavItems(configItems)}</div>
              </div>
            </nav>
          </div>

          {/* Footer with Ask AI button */}
          <div className="p-4">
            {!collapsed ? (
              <button
                type="button"
                onClick={() => setShowAskModal(true)}
                className="animation-parent box-shadow-animation w-full flex items-center justify-center px-3 py-3 border border-transparent text-sm font-medium rounded-lg text-white bg-green-600 hover:bg-green-700 dark-shadow hover:shadow-xl transition-all duration-200"
              >
                <Bot className="color-fade mr-2 w-4 h-4" />
                <p className="color-scroll l-to-r" data-hover="Assistant">
                  Assistant
                </p>
              </button>
            ) : (
              <button
                type="button"
                onClick={() => setShowAskModal(true)}
                className="w-8 h-8 mx-auto flex items-center justify-center border border-transparent rounded-lg text-white bg-green-600 hover:bg-green-700 dark-shadow hover:shadow-xl transition-all duration-200"
                aria-label="Assistant"
              >
                <Bot className="w-4 h-4 flex-shrink-0" />
              </button>
            )}
          </div>
        </div>
      </aside>

      <AskAIModal
        isOpen={showAskModal}
        onClose={() => setShowAskModal(false)}
      />
    </>
  );
};

export default Sidebar;
