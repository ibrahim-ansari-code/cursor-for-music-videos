import React from 'react';
import PropTypes from 'prop-types';
import { SkeletonLine, SkeletonCircle, SkeletonPill, SkeletonBlock } from './SkeletonPrimitives';

/**
 * Integration card skeleton that matches the QuickBooksCard layout
 */
const IntegrationCardSkeleton = ({ className = '' }) => (
  <article className={`bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 mb-6 overflow-hidden transition-colors ${className}`}>
    <div className="p-6 flex items-center justify-between">
      <div className="flex items-center space-x-6">
        {/* Logo skeleton */}
        <SkeletonBlock width="3.5rem" height="3.5rem" rounded="lg" />
        
        <div>
          {/* Title */}
          <SkeletonLine width="10rem" height="1.125rem" className="mb-2" />
          {/* Description */}
          <SkeletonLine width="16rem" height="0.75rem" />
        </div>
      </div>
      
      <div className="flex items-center space-x-6">
        {/* Status badge */}
        <div className="min-w-[120px] flex justify-center">
          <SkeletonPill width="7rem" height="2rem" />
        </div>
        
        {/* Action buttons */}
        <div className="flex items-center space-x-3">
          <SkeletonPill width="7rem" height="2.25rem" />
          <SkeletonPill width="7rem" height="2.25rem" />
        </div>
      </div>
    </div>
  </article>
);

IntegrationCardSkeleton.propTypes = {
  className: PropTypes.string,
};

/**
 * Placeholder card skeleton that matches the "Coming Soon" card
 */
const PlaceholderCardSkeleton = ({ className = '' }) => (
  <section className={`bg-white dark:bg-gray-800 rounded-lg border-2 border-dashed border-gray-300 dark:border-gray-600 transition-colors ${className}`}>
    <div className="p-12 text-center">
      {/* Icon */}
      <div className="w-16 h-16 bg-gray-100 dark:bg-gray-700 rounded-lg flex items-center justify-center mx-auto mb-4 transition-colors">
        <SkeletonCircle size="2rem" />
      </div>
      
      {/* Title */}
      <SkeletonLine width="12rem" height="1.125rem" className="mb-2 mx-auto" />
      
      {/* Description */}
      <div className="max-w-md mx-auto space-y-2">
        <SkeletonLine width="20rem" height="1rem" className="mx-auto" />
        <SkeletonLine width="16rem" height="1rem" className="mx-auto" />
      </div>
    </div>
  </section>
);

PlaceholderCardSkeleton.propTypes = {
  className: PropTypes.string,
};

/**
 * Full integrations page skeleton
 */
const IntegrationsSkeleton = ({ 
  className = '',
  showPlaceholder = true,
  ...props 
}) => (
  <main className={`p-4 sm:p-6 lg:p-8 ${className}`} role="main" {...props}>
    <div className="max-w-5xl mx-auto">
      {/* Header */}
      <header className="mb-8">
        <SkeletonLine width="15rem" height="2.25rem" className="mb-2" />
        <SkeletonLine width="25rem" height="1rem" />
      </header>

      {/* Integration cards */}
      <div role="region" aria-label="Integration status and actions">
        {/* Main integration card (QuickBooks) */}
        <IntegrationCardSkeleton />

        {/* Placeholder "Coming Soon" card */}
        {showPlaceholder && <PlaceholderCardSkeleton />}
      </div>
    </div>
  </main>
);

IntegrationsSkeleton.propTypes = {
  className: PropTypes.string,
  showPlaceholder: PropTypes.bool,
};

export { IntegrationCardSkeleton, PlaceholderCardSkeleton };
export default IntegrationsSkeleton;