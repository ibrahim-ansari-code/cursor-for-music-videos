import React, { useState, useContext } from "react";
import { NavLink } from "react-router-dom";
import { AuthContext } from "../App";
import InviteModal from "./InviteModal";
import AskAIModal from "./AskAIModal";
import "../styles/ui-feedback.css";

const Sidebar = () => {
  const { user } = useContext(AuthContext);
  const [collapsed, setCollapsed] = useState(false);
  const [showInviteModal, setShowInviteModal] = useState(false);
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
    { name: "Reports", path: "/reports", icon: "fa-chart-pie" },
    { name: "Maintenance", path: "/maintenance", icon: "fa-wrench" },
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
          `${
            isActive
              ? "bg-gray-100 text-gray-900"
              : "text-gray-600 hover:bg-gray-50 hover:text-gray-900"
          } 
          group flex items-center py-2.5 px-3 text-sm font-medium rounded-md transition-colors`
        }
      >
        <div className="flex items-center w-full">
          <div className={`${collapsed ? "mx-auto" : "w-6 text-center"}`}>
            <i
              className={`fas ${item.icon} text-gray-400 group-hover:text-gray-500`}
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
      return <div className="border-t border-gray-200 my-2"></div>;
    }
    return (
      <h3 className="px-3 text-xs font-medium text-gray-400 uppercase tracking-wider mb-3 mt-3">
        {title}
      </h3>
    );
  };

  return (
    <>
      <aside
        className={`bg-white border-r border-gray-200 transition-all duration-300 ease-in-out h-full ${
          collapsed ? "w-16" : "w-64"
        }`}
      >
        <div className="h-full flex flex-col">
          {/* Logo */}
          <div className="flex items-center justify-between h-16 px-4 border-b border-gray-200">
            <div
              className={`flex items-center ${
                collapsed
                  ? "w-full justify-center"
                  : "flex-1 justify-start pl-0"
              }`}
            >
              <div className="flex items-center justify-center h-12">
                {!collapsed && (
                  <NavLink key={"Logo-Dashboard"} to={"/dashboard"}>
                    <img
                      src="BrikliLogoSidebar.png"
                      alt="Brikli Logo"
                      className="h-9 w-auto mx-auto my-4"
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
                className={`fas ${
                  collapsed ? "fa-angles-right" : "fa-angles-left"
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

          {/* Footer with two buttons */}
          <div className="p-4 border-t border-gray-200">
            {!collapsed ? (
              <div className="flex space-x-2">
                <button
                  type="button"
                  onClick={() => setShowInviteModal(true)}
                  className="animation-parent box-shadow-animation w-1/2 flex items-center justify-center px-3 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 transition-colors"
                  style={{ boxShadow: "0 0 10px  #3182ce" }}
                >
                  <i className="color-fade fas fa-user-plus mr-2" />
                  <p className="color-scroll l-to-r" data-hover="Invite">
                    Invite
                  </p>
                </button>
                <button
                  type="button"
                  onClick={() => setShowAskModal(true)}
                  className="animation-parent box-shadow-animation w-1/2 flex items-center justify-center px-3 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-green-600 hover:bg-green-700 transition-colors"
                  style={{ boxShadow: "0 0 10px  #38a169" }}
                >
                  <i className="color-fade fas fa-robot mr-2" />
                  <p className="color-scroll l-to-r" data-hover="Ask">
                    Ask
                  </p>
                </button>
              </div>
            ) : (
              <div className="flex flex-col space-y-2">
                <button
                  type="button"
                  onClick={() => setShowInviteModal(true)}
                  className="w-full flex items-center justify-center p-2 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 transition-colors"
                  aria-label="Invite"
                >
                  <i className="fas fa-user-plus" />
                </button>
                <button
                  type="button"
                  onClick={() => setShowAskModal(true)}
                  className="w-full flex items-center justify-center p-2 border border-transparent text-sm font-medium rounded-md text-white bg-green-600 hover:bg-green-700 transition-colors"
                  aria-label="Ask AI"
                >
                  <i className="fas fa-robot" />
                </button>
              </div>
            )}
          </div>
        </div>
      </aside>

      {/* Modals */}
      <InviteModal
        isOpen={showInviteModal}
        onClose={() => setShowInviteModal(false)}
      />
      <AskAIModal
        isOpen={showAskModal}
        onClose={() => setShowAskModal(false)}
      />
    </>
  );
};

export default Sidebar;
