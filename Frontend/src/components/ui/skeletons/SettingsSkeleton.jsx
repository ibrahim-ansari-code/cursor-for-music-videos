import React from 'react';
import PropTypes from 'prop-types';
import { SkeletonLine, SkeletonBlock } from './SkeletonPrimitives';

/**
 * Settings page skeleton that matches the settings layout
 * Includes profile card and settings sections
 */
const SettingsSkeleton = ({ 
  className = '',
  ...props 
}) => (
  <div className={`min-h-screen bg-gray-50 py-6 ${className}`} {...props}>
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
      {/* Page Header */}
      <div className="mb-8">
        <SkeletonLine width="8rem" height="2.25rem" className="mb-2" />
        <SkeletonLine width="20rem" height="1rem" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
        {/* Sidebar/Profile Card */}
        <div className="lg:col-span-4 xl:col-span-3">
          <ProfileCardSkeleton />
        </div>

        {/* Main Settings Content */}
        <div className="lg:col-span-8 xl:col-span-9">
          <div className="space-y-6">
            {/* Settings Section 1 */}
            <SettingsSectionSkeleton />
            
            {/* Settings Section 2 */}
            <SettingsSectionSkeleton />
            
            {/* Settings Section 3 */}
            <SettingsSectionSkeleton />
          </div>
        </div>
      </div>
    </div>
  </div>
);

SettingsSkeleton.propTypes = {
  className: PropTypes.string,
};

/**
 * Profile card skeleton component
 */
const ProfileCardSkeleton = () => (
  <div className="bg-white shadow rounded-lg p-6">
    {/* Avatar and name */}
    <div className="text-center mb-6">
      <SkeletonBlock width="5rem" height="5rem" rounded="full" className="mx-auto mb-4" />
      <SkeletonLine width="8rem" height="1.25rem" className="mb-2 mx-auto" />
      <SkeletonLine width="10rem" height="1rem" className="mx-auto" />
    </div>

    {/* Profile details */}
    <div className="space-y-4">
      <div>
        <SkeletonLine width="4rem" height="0.875rem" className="mb-2" />
        <SkeletonLine width="12rem" height="1rem" />
      </div>
      <div>
        <SkeletonLine width="3rem" height="0.875rem" className="mb-2" />
        <SkeletonLine width="8rem" height="1rem" />
      </div>
      <div>
        <SkeletonLine width="5rem" height="0.875rem" className="mb-2" />
        <SkeletonLine width="6rem" height="1rem" />
      </div>
    </div>

    {/* Action button */}
    <div className="mt-6">
      <SkeletonBlock width="100%" height="2.5rem" rounded="md" />
    </div>
  </div>
);

/**
 * Settings section skeleton component
 */
const SettingsSectionSkeleton = () => (
  <div className="bg-white shadow rounded-lg">
    {/* Section header */}
    <div className="px-6 py-4 border-b border-gray-200">
      <SkeletonLine width="8rem" height="1.25rem" className="mb-1" />
      <SkeletonLine width="16rem" height="0.875rem" />
    </div>

    {/* Section content */}
    <div className="px-6 py-4 space-y-4">
      {/* Setting item 1 */}
      <div className="flex items-center justify-between">
        <div className="flex-1">
          <SkeletonLine width="10rem" height="1rem" className="mb-1" />
          <SkeletonLine width="18rem" height="0.875rem" />
        </div>
        <SkeletonBlock width="3rem" height="1.5rem" rounded="full" />
      </div>

      {/* Setting item 2 */}
      <div className="flex items-center justify-between">
        <div className="flex-1">
          <SkeletonLine width="12rem" height="1rem" className="mb-1" />
          <SkeletonLine width="20rem" height="0.875rem" />
        </div>
        <SkeletonBlock width="6rem" height="2rem" rounded="md" />
      </div>

      {/* Setting item 3 */}
      <div>
        <SkeletonLine width="8rem" height="1rem" className="mb-2" />
        <SkeletonBlock width="100%" height="2.5rem" rounded="md" />
      </div>
    </div>
  </div>
);

export { ProfileCardSkeleton, SettingsSectionSkeleton };
export default SettingsSkeleton;