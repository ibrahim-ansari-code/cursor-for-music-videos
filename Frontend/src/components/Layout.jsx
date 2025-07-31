import React, { useContext } from "react";
import { Outlet, useLocation, Link } from "react-router-dom";
import Sidebar from "./Sidebar";
import { AuthContext } from "../contexts/AuthContext";

const Layout = () => {
  const { user, signOut } = useContext(AuthContext);
  const location = useLocation();

  // Map routes to page titles
  const getPageTitle = (pathname) => {
    const routes = {
      "/dashboard": "Dashboard",
      "/properties": "Properties",
      "/leases": "Leases",
      "/vendors": "Vendors",
      "/accounting": "Accounting",
      "/messages": "Messages",
      "/applications": "Applications",
      "/tenants": "Tenants",
      "/maintenance": "Maintenance",
      "/reports": "Reports",
      "/settings": "Settings",
      "/integrations": "Integrations",
    };

    // Handle nested routes (e.g., /properties/:id)
    const basePath = "/" + pathname.split("/")[1];
    return routes[basePath] || "Dashboard";
  };

  const getInitials = (firstName, lastName) => {
    return `${firstName?.charAt(0) || ""}${
      lastName?.charAt(0) || ""
    }`.toUpperCase();
  };

  return (
    <div className="flex h-screen bg-gray-50">
      {/* Sidebar */}
      <Sidebar />

      {/* Main Content */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Header */}
        <header className="bg-white border-b border-gray-200 z-10 h-16">
          <div className="px-6 h-full flex justify-between items-center">
            <h1 className="text-2xl font-bold text-gray-900">
              {getPageTitle(location.pathname)}
            </h1>

            {/* User dropdown area */}
            <div className="flex items-center space-x-3">
              {/* Link the avatar and name to settings */}
              <Link
                to="/settings"
                className="flex items-center space-x-3 cursor-pointer group"
              >
                <div className="h-8 w-8 rounded-full bg-teal-100 flex items-center justify-center text-teal-700 overflow-hidden group-hover:ring-2 group-hover:ring-teal-500 group-hover:ring-offset-2 transition-all">
                  {user?.profile_image_url ? (
                    <img
                      key={user.profile_image_url}
                      src={user.profile_image_url}
                      alt="User Avatar"
                      className="h-full w-full object-cover"
                      onError={(e) => {
                        e.target.onerror = null;
                        if (import.meta.env.MODE === 'development') {
                          console.warn(
                            "Header avatar failed to load:",
                            user.profile_image_url
                          );
                        }
                        e.target.style.display = "none";
                      }}
                    />
                  ) : (
                    <span className="text-xs font-medium">
                      {getInitials(user?.first_name, user?.last_name)}
                    </span>
                  )}
                </div>
                <div className="hidden md:block">
                  <p className="text-sm font-medium text-gray-900 group-hover:text-teal-600 transition-colors">
                    {user?.first_name} {user?.last_name}
                  </p>
                  <p className="text-xs text-gray-500 capitalize">
                    {user?.user_type}
                  </p>
                </div>
              </Link>
              {/* Logout Button */}
              <button
                className="text-sm text-gray-700 hover:text-red-600 px-3 py-2 rounded-lg hover:bg-gray-100 transition-colors flex items-center"
                onClick={signOut}
              >
                <i className="fas fa-sign-out-alt mr-2"></i> Logout
              </button>
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
