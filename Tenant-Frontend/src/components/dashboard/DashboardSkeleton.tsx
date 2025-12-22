import React from 'react';
import { CardSkeleton } from '@/components/ui/LoadingSkeleton';
import LoadingSkeleton from '@/components/ui/LoadingSkeleton';

/**
 * DashboardSkeleton Component
 * Loading state skeleton for the entire dashboard
 * Matches the actual DashboardContent layout
 */
const DashboardSkeleton: React.FC = () => (
  <div className="pt-6 animate-fade-in">
    {/* Dashboard cards skeleton */}
    <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-4">
      {Array.from({ length: 4 }, (_, i) => (
        <CardSkeleton key={i} />
      ))}
    </div>

    {/* Recent Payments Table skeleton - matches RecentPaymentsTable */}
    <div className="mt-6">
      <div className="bg-white rounded-xl shadow-sm border border-gray-200">
        <div className="px-4 py-3 border-b border-gray-200 flex items-center justify-between">
          <LoadingSkeleton width="120px" height="1.25rem" />
          <LoadingSkeleton width="60px" height="1rem" />
        </div>
        <div className="divide-y divide-gray-100">
          {[1, 2, 3].map((i) => (
            <div key={i} className="px-4 py-3 flex items-center justify-between">
              <div className="flex-1">
                <div className="flex items-center gap-2 mb-1">
                  <LoadingSkeleton width="50px" height="1rem" />
                  <LoadingSkeleton width="40px" height="1.25rem" rounded="rounded-full" />
                </div>
                <LoadingSkeleton width="100px" height="0.75rem" />
              </div>
              <div className="flex items-center gap-2">
                <LoadingSkeleton width="70px" height="1rem" />
                <LoadingSkeleton width="24px" height="24px" rounded="rounded" />
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>

    {/* Quick Actions skeleton */}
    <div className="mt-8 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
      {Array.from({ length: 3 }, (_, i) => (
        <div key={i} className="bg-white p-6 rounded-xl shadow-sm border border-gray-200">
          <div className="flex items-center">
            <div className="shrink-0 p-3 bg-gray-100 rounded-lg">
              <LoadingSkeleton width="1.5rem" height="1.5rem" rounded="rounded-none" />
            </div>
            <div className="ml-4 flex-1">
              <LoadingSkeleton width="120px" height="1.25rem" className="mb-1" />
              <LoadingSkeleton width="150px" height="0.875rem" />
            </div>
            <LoadingSkeleton width="1rem" height="1rem" rounded="rounded-none" />
          </div>
        </div>
      ))}
    </div>
  </div>
);

export default DashboardSkeleton;
