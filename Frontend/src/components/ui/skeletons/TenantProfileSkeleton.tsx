import React from 'react';
import { SkeletonLine, SkeletonCircle, SkeletonBlock, SkeletonPill } from './SkeletonPrimitives';

/**
 * Tenant profile page skeleton that matches the layout structure
 * Includes header with avatar, tabs navigation, and content area
 */
const TenantProfileSkeleton: React.FC<{ className?: string }> = ({ className = '' }) => (
  <div className={`min-h-screen bg-gray-50 dark:bg-gray-900 transition-colors duration-300 ${className}`}>
    {/* Header Skeleton */}
    <div className="bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 px-6 py-6">
      <div className="flex items-start justify-between gap-6">
        {/* Left: Avatar and Info */}
        <div className="flex items-center gap-4 flex-1">
          {/* Avatar */}
          <SkeletonCircle size="5rem" />

          {/* Name, Contact, and Property Info */}
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-3 mb-3">
              <SkeletonLine width="14rem" height="2rem" />
              <SkeletonPill width="4.5rem" height="1.5rem" />
              <SkeletonPill width="5.5rem" height="1.5rem" />
            </div>

            <div className="flex flex-wrap items-center gap-x-6 gap-y-2">
              <SkeletonLine width="10rem" height="1rem" />
              <SkeletonLine width="8rem" height="1rem" />
              <SkeletonLine width="12rem" height="1rem" />
            </div>
          </div>
        </div>

        {/* Right: Action Buttons */}
        <div className="flex items-center gap-2 flex-shrink-0">
          <SkeletonBlock width="5rem" height="2rem" rounded="md" />
          <SkeletonBlock width="6rem" height="2rem" rounded="md" />
          <SkeletonBlock width="5.5rem" height="2rem" rounded="md" />
          <SkeletonBlock width="2rem" height="2rem" rounded="md" />
        </div>
      </div>
    </div>

    {/* Fetching Indicator Placeholder */}
    <div className="h-1" />

    {/* Tab Navigation Skeleton */}
    <div className="bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700">
      <div className="px-6">
        <nav className="flex space-x-8" aria-label="Tabs">
          {Array.from({ length: 9 }, (_, i) => (
            <div key={i} className="py-4">
              <SkeletonLine
                width={['4rem', '3.5rem', '5rem', '6rem', '4.5rem', '5.5rem', '5rem', '3.5rem', '4rem'][i]}
                height="1rem"
              />
            </div>
          ))}
        </nav>
      </div>
    </div>

    {/* Main Content Skeleton */}
    <div className="p-6 max-w-[1600px] mx-auto">
      {/* Overview Cards Row */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
        <OverviewCardSkeleton />
        <OverviewCardSkeleton />
        <OverviewCardSkeleton />
      </div>

      {/* Main Content Area */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column - 2/3 width */}
        <div className="lg:col-span-2 space-y-6">
          <ContentCardSkeleton title lines={4} />
          <ContentCardSkeleton title lines={3} />
        </div>

        {/* Right Column - 1/3 width */}
        <div className="space-y-6">
          <ContentCardSkeleton title lines={5} />
          <ContentCardSkeleton title lines={3} />
        </div>
      </div>
    </div>
  </div>
);

/**
 * Overview metric card skeleton
 */
const OverviewCardSkeleton: React.FC = () => (
  <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-5">
    <div className="flex items-center justify-between mb-3">
      <SkeletonLine width="6rem" height="0.875rem" />
      <SkeletonCircle size="2rem" />
    </div>
    <SkeletonLine width="5rem" height="1.75rem" className="mb-1" />
    <SkeletonLine width="8rem" height="0.75rem" />
  </div>
);

/**
 * Generic content card skeleton with title and lines
 */
const ContentCardSkeleton: React.FC<{ title?: boolean; lines?: number }> = ({
  title = true,
  lines = 3
}) => (
  <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-6">
    {title && (
      <div className="flex items-center justify-between mb-4 pb-4 border-b border-gray-200 dark:border-gray-700">
        <SkeletonLine width="8rem" height="1.25rem" />
        <SkeletonBlock width="4rem" height="1.75rem" rounded="md" />
      </div>
    )}
    <div className="space-y-3">
      {Array.from({ length: lines }, (_, i) => (
        <div key={i} className="flex items-center gap-3">
          <SkeletonCircle size="2rem" />
          <div className="flex-1">
            <SkeletonLine width={i === lines - 1 ? '60%' : '80%'} height="0.875rem" className="mb-1" />
            <SkeletonLine width="40%" height="0.75rem" />
          </div>
        </div>
      ))}
    </div>
  </div>
);

export default TenantProfileSkeleton;
