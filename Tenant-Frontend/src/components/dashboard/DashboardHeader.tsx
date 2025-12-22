import React from 'react';
import type { DashboardHeaderProps } from './types';

/**
 * DashboardHeader Component
 * Displays welcome message with user's first name
 */
const DashboardHeader: React.FC<DashboardHeaderProps> = ({ firstName }) => {
  return (
    <div className="mb-8">
      <h2 className="text-3xl font-bold text-gray-900">
        Welcome back, {firstName}!
      </h2>
      <p className="mt-1 text-lg text-gray-600">
        Here's an overview of your apartment and upcoming payments.
      </p>
    </div>
  );
};

export default DashboardHeader;
