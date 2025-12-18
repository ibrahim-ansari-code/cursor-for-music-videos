import React, { useState, useEffect } from 'react';
import { Outlet, useLocation, Link } from 'react-router-dom';
import Sidebar from '@/components/Sidebar';
import { useAuth } from '@/hooks/useAuth';
import LoadingSkeleton from '@/components/ui/LoadingSkeleton';
import { FaBell, FaSignOutAlt } from 'react-icons/fa';

const Layout: React.FC = React.memo(() => {
  const { user, signOut, loading } = useAuth();
  const location = useLocation();
  const [imageError, setImageError] = useState<boolean>(false);

  // Reset image error when user changes
  useEffect(() => {
    setImageError(false);
  }, [user?.profile_image_url]);

  // Show loading state while user data is being fetched
  if (loading) {
    return (
      <div className="flex h-screen bg-gray-50 dark:bg-gray-900">
        {/* Sidebar skeleton */}
        <div className="w-64 bg-white dark:bg-gray-800 border-r border-gray-200 dark:border-gray-700">
          <div className="p-4">
            <LoadingSkeleton width="150px" height="2.25rem" className="mb-4" />
          </div>
          <div className="px-2 space-y-2">
            {Array.from({ length: 5 }, (_, i) => (
              <LoadingSkeleton key={i} height="2.5rem" rounded="rounded-lg" />
            ))}
          </div>
        </div>
        {/* Main content skeleton */}
        <div className="flex-1 flex flex-col">
          {/* Header skeleton */}
          <div className="h-16 bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 px-6 flex items-center justify-between">
            <LoadingSkeleton width="200px" height="2rem" />
            <LoadingSkeleton width="120px" height="2rem" />
          </div>
          {/* Content skeleton */}
          <div className="flex-1 p-4">
            <LoadingSkeleton width="300px" height="2.25rem" className="mb-4" />
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
              {Array.from({ length: 4 }, (_, i) => (
                <LoadingSkeleton key={i} height="120px" rounded="rounded-xl" />
              ))}
            </div>
          </div>
        </div>
      </div>
    );
  }

  // Handle case where user is not loaded
  if (!user) {
    return (
      <div className="flex h-screen bg-gray-50 dark:bg-gray-900 items-center justify-center">
        <div className="text-center">
          <p className="text-gray-600 dark:text-gray-400">Unable to load user data</p>
          <button 
            onClick={signOut}
            className="mt-2 text-brand-teal hover:text-brand-green"
          >
            Return to Login
          </button>
        </div>
      </div>
    );
  }

  // Map routes to page titles
  const getPageTitle = (pathname: string): string => {
    const routes: Record<string, string> = {
      "/dashboard": "Dashboard",
      "/payments": "", 
      "/documents": "Lease Documents",
      "/maintenance": "Maintenance",
      "/notifications": "Notifications",
      "/settings": "Settings",
    };

    // Handle nested routes (e.g., /payments/:id)
    const basePath = "/" + pathname.split("/")[1];
    return basePath in routes ? routes[basePath] : "Dashboard";
  };

  const getInitials = (firstName: string | null | undefined, lastName: string | null | undefined): string => {
    if (!firstName && !lastName) return "?";
    return `${firstName?.charAt(0) || ""}${
      lastName?.charAt(0) || ""
    }`.toUpperCase();
  };

  const getUserDisplayName = (): string => {
    if (!user?.first_name && !user?.last_name) {
      return "User";
    }
    return `${user?.first_name || ""} ${user?.last_name || ""}`.trim();
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
              {/* Notifications bell - links to notifications page */}
              <Link 
                to="/notifications" 
                className="relative p-2 text-gray-600 hover:text-gray-900 rounded-lg hover:bg-gray-100 transition-colors"
                aria-label="View notifications"
              >
                <FaBell className="text-lg" aria-hidden="true" />
              </Link>

              {/* Link the avatar and name to settings */}
              <Link
                to="/settings"
                className="flex items-center space-x-3 cursor-pointer group"
                aria-label="Go to settings"
              >
                <div className="h-8 w-8 rounded-full bg-teal-100 flex items-center justify-center text-teal-700 overflow-hidden group-hover:ring-2 group-hover:ring-teal-500 group-hover:ring-offset-2 transition-all">
                  {user?.profile_image_url && !imageError ? (
                    <img
                      key={user.profile_image_url}
                      src={user.profile_image_url}
                      alt="User Avatar"
                      className="h-full w-full object-cover"
                      onError={() => {
                        if (import.meta.env.MODE === 'development') {
                          console.warn(
                            "Header avatar failed to load:",
                            user.profile_image_url
                          );
                        }
                        setImageError(true);
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
                    {getUserDisplayName()}
                  </p>
                  <p className="text-xs text-gray-500 capitalize">
                    Tenant
                  </p>
                </div>
              </Link>
              {/* Logout Button */}
              <button
                className="text-sm text-gray-700 hover:text-red-600 px-3 py-2 rounded-lg hover:bg-gray-100 transition-colors flex items-center"
                onClick={signOut}
                aria-label="Sign out of account"
              >
                <FaSignOutAlt className="mr-2" aria-hidden="true" /> Logout
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
});

Layout.displayName = 'Layout';

export default Layout;

