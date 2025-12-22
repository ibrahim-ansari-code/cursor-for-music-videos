import React from 'react';
import type { LoadingSkeletonProps, TextSkeletonProps, ButtonSkeletonProps } from '@/types';

/**
 * Generic loading skeleton component for better UX
 */
const LoadingSkeleton: React.FC<LoadingSkeletonProps> = ({
  className = '',
  width = '100%',
  height = '1rem',
  rounded = 'rounded'
}) => (
  <div
    className={`animate-pulse bg-gray-200 ${rounded} ${className}`}
    style={{ width, height }}
  />
);

/**
 * Card skeleton for dashboard cards
 */
export const CardSkeleton: React.FC = () => (
  <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 min-h-[180px]">
    <div className="flex items-start justify-between">
      <div className="flex-1 space-y-2">
        <LoadingSkeleton width="60%" height="0.875rem" />
        <LoadingSkeleton width="80%" height="2rem" />
        <LoadingSkeleton width="40%" height="0.75rem" />
      </div>
      <div className="p-3 rounded-lg bg-gray-100">
        <LoadingSkeleton width="1.25rem" height="1.25rem" rounded="rounded-none" />
      </div>
    </div>
  </div>
);

/**
 * Text skeleton for various text elements
 */
export const TextSkeleton: React.FC<TextSkeletonProps> = ({ lines = 1, className = '' }) => (
  <div className={`space-y-2 ${className}`}>
    {Array.from({ length: lines }, (_, i) => (
      <LoadingSkeleton 
        key={i}
        width={i === lines - 1 ? '75%' : '100%'} 
        height="1rem"
      />
    ))}
  </div>
);

/**
 * Button skeleton
 */
export const ButtonSkeleton: React.FC<ButtonSkeletonProps> = ({ className = '' }) => (
  <LoadingSkeleton 
    className={`${className}`}
    width="120px" 
    height="2.5rem" 
    rounded="rounded-lg" 
  />
);

/**
 * Dashboard loading skeleton with full layout
 */
export const DashboardSkeleton: React.FC = () => (
  <div className="animate-fade-in">
    {/* Welcome section skeleton */}
    <div className="mb-8">
      <LoadingSkeleton width="300px" height="2.25rem" className="mb-2" />
      <LoadingSkeleton width="450px" height="1.5rem" />
    </div>

    {/* Dashboard cards skeleton */}
    <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-4 mb-8">
      {Array.from({ length: 4 }, (_, i) => (
        <CardSkeleton key={i} />
      ))}
    </div>

    {/* Recent Payments Table skeleton */}
    <div className="bg-white rounded-xl shadow-sm border border-gray-200 mb-8">
      <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between">
        <LoadingSkeleton width="150px" height="1.5rem" />
        <LoadingSkeleton width="80px" height="1rem" />
      </div>

      <div className="p-8 text-center">
        <LoadingSkeleton width="250px" height="1rem" className="mx-auto" />
      </div>
    </div>

    {/* Quick Actions skeleton */}
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
      {Array.from({ length: 3 }, (_, i) => (
        <div key={i} className="bg-white p-6 rounded-xl shadow-sm border border-gray-200">
          <div className="flex items-center">
            <div className="shrink-0 p-3 bg-gray-100 rounded-lg">
              <LoadingSkeleton width="2rem" height="2rem" rounded="rounded-none" />
            </div>
            <div className="ml-4 flex-1">
              <LoadingSkeleton width="120px" height="1.5rem" className="mb-2" />
              <LoadingSkeleton width="160px" height="0.875rem" />
            </div>
            <LoadingSkeleton width="1rem" height="1rem" rounded="rounded-none" />
          </div>
        </div>
      ))}
    </div>
  </div>
);

export default LoadingSkeleton;

