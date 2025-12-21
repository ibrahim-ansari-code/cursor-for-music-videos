import React from "react";
import { MAINTENANCE_MESSAGE } from "../config/maintenanceMode";

const MaintenancePage: React.FC = () => {
  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-900 px-4">
      <div className="max-w-md w-full">
        <div className="rounded-lg bg-yellow-50 dark:bg-yellow-900/20 border-2 border-yellow-400 dark:border-yellow-600 p-8 shadow-xl">
          <div className="flex flex-col items-center text-center">
            <div className="flex-shrink-0 mb-4">
              <svg 
                className="h-16 w-16 text-yellow-600 dark:text-yellow-500" 
                xmlns="http://www.w3.org/2000/svg" 
                viewBox="0 0 20 20" 
                fill="currentColor"
              >
                <path 
                  fillRule="evenodd" 
                  d="M8.485 2.495c.673-1.167 2.357-1.167 3.03 0l6.28 10.875c.673 1.167-.17 2.625-1.516 2.625H3.72c-1.347 0-2.189-1.458-1.515-2.625L8.485 2.495zM10 5a.75.75 0 01.75.75v3.5a.75.75 0 01-1.5 0v-3.5A.75.75 0 0110 5zm0 9a1 1 0 100-2 1 1 0 000 2z" 
                  clipRule="evenodd" 
                />
              </svg>
            </div>
            <h2 className="text-2xl font-bold text-yellow-800 dark:text-yellow-300 mb-4">
              {MAINTENANCE_MESSAGE.title}
            </h2>
            <div className="text-sm text-yellow-700 dark:text-yellow-400 space-y-3">
              <p className="font-medium">
                {MAINTENANCE_MESSAGE.message}
              </p>
              <div className="bg-yellow-100 dark:bg-yellow-900/40 rounded-md p-4 mt-4">
                <p className="font-semibold text-yellow-900 dark:text-yellow-200">
                  Expected to resume:
                </p>
                <p className="text-lg font-bold text-yellow-800 dark:text-yellow-300 mt-1">
                  {MAINTENANCE_MESSAGE.expectedResume}
                </p>
              </div>
              <p className="text-xs mt-4">
                {MAINTENANCE_MESSAGE.apology}
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default MaintenancePage;

