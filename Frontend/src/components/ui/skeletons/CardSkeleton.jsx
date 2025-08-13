import React from 'react';
import PropTypes from 'prop-types';
import { SkeletonLine, SkeletonCircle, SkeletonBlock } from './SkeletonPrimitives';

/**
 * Card skeleton components for dashboard layouts
 * Ensures consistent loading states across different card types
 */

/**
 * Generic card skeleton
 */
const CardSkeleton = ({ 
  className = '',
  children,
  ...props 
}) => (
  <div className={`dashboard-card ${className}`} {...props}>
    {children}
  </div>
);

CardSkeleton.propTypes = {
  className: PropTypes.string,
  children: PropTypes.node,
};

/**
 * Financial summary card skeleton (matches FinancialSummary layout)
 */
export const FinancialCardSkeleton = ({ className = '' }) => (
  <CardSkeleton className={className}>
    <SkeletonLine width="60%" height="1rem" className="mb-3" />
    <div className="flex items-baseline">
      <SkeletonLine width="7rem" height="1.75rem" className="mr-2" />
      <SkeletonLine width="2.5rem" height="0.75rem" />
    </div>
    <SkeletonLine width="80%" height="0.75rem" className="mt-2" />
  </CardSkeleton>
);

FinancialCardSkeleton.propTypes = {
  className: PropTypes.string,
};

/**
 * Portfolio overview card skeleton (matches PortfolioOverview layout)
 */
export const PortfolioCardSkeleton = ({ className = '' }) => (
  <CardSkeleton className={`h-full flex flex-col ${className}`}>
    <SkeletonLine width="9rem" height="1.5rem" className="mb-4" />
    
    {/* Stats grid */}
    <div className="grid grid-cols-3 gap-4 mb-4">
      {[0, 1, 2].map((i) => (
        <div key={i} className="bg-white rounded-lg p-4 border border-gray-100 shadow-sm flex flex-col items-center justify-center">
          <SkeletonCircle size="3rem" className="mb-3" />
          <SkeletonLine width="1.5rem" height="1.5rem" className="mb-1" />
          <SkeletonLine width="4rem" height="0.875rem" />
        </div>
      ))}
    </div>
    
    {/* Occupancy section */}
    <div className="space-y-2">
      <div className="flex justify-between items-center">
        <SkeletonLine width="7rem" height="0.875rem" />
        <SkeletonLine width="2.5rem" height="0.875rem" />
      </div>
      <SkeletonLine width="100%" height="0.5rem" className="rounded-full" />
      <div className="flex justify-between">
        <SkeletonLine width="5rem" height="0.75rem" />
        <SkeletonLine width="5rem" height="0.75rem" />
      </div>
    </div>
  </CardSkeleton>
);

PortfolioCardSkeleton.propTypes = {
  className: PropTypes.string,
};

/**
 * Due panel card skeleton (matches DuePanel layout)
 */
export const DuePanelSkeleton = ({ className = '' }) => (
  <CardSkeleton className={className}>
    <SkeletonLine width="3rem" height="1.5rem" className="mb-3" />
    
    {/* Tabs */}
    <div className="flex space-x-6 mb-2">
      <SkeletonLine width="2rem" height="1.25rem" />
      <SkeletonLine width="4rem" height="1.25rem" />
    </div>
    
    {/* Table content */}
    <div className="space-y-2 mt-4">
      {[0, 1, 2, 3].map((i) => (
        <div key={i} className="flex items-center py-2">
          <SkeletonCircle size="2rem" className="mr-3" />
          <div className="flex-1">
            <SkeletonLine width="70%" height="0.875rem" className="mb-1" />
            <SkeletonLine width="50%" height="0.75rem" />
          </div>
          <SkeletonLine width="4rem" height="0.875rem" />
        </div>
      ))}
    </div>
  </CardSkeleton>
);

DuePanelSkeleton.propTypes = {
  className: PropTypes.string,
};

/**
 * Status card skeleton (for Properties page status cards)
 */
export const StatusCardSkeleton = ({ className = '' }) => (
  <div className="bg-white overflow-hidden shadow rounded-lg">
    <div className="px-4 py-5 sm:p-6">
      <div className="flex items-center">
        <SkeletonCircle size="3rem" className="mr-5" />
        <div className="flex-1">
          <SkeletonLine width="5rem" height="0.875rem" className="mb-2" />
          <SkeletonLine width="2rem" height="1.5rem" />
        </div>
      </div>
    </div>
  </div>
);

StatusCardSkeleton.propTypes = {
  className: PropTypes.string,
};

/**
 * Chart skeleton (matches RevenueChart layout)
 */
export const ChartSkeleton = ({ 
  height = '300px',
  className = '',
  barCount = 6 
}) => (
  <div className={className} style={{ height }}>
    <div className="flex items-end justify-between h-full pb-8">
      {Array.from({ length: barCount }, (_, index) => (
        <div key={index} className="flex flex-col items-center space-y-2 flex-1 mx-1">
          <SkeletonBlock 
            width="100%" 
            height={`${((index + 1) * 10) % 60 + 20}%`}
            rounded="sm"
          />
          <SkeletonLine width="3rem" height="1rem" />
        </div>
      ))}
    </div>
    
    {/* Legend */}
    <div className="flex justify-center mt-4 space-x-6">
      <div className="flex items-center space-x-2">
        <SkeletonCircle size="0.75rem" />
        <SkeletonLine width="4rem" height="0.75rem" />
      </div>
      <div className="flex items-center space-x-2">
        <SkeletonCircle size="0.75rem" />
        <SkeletonLine width="4rem" height="0.75rem" />
      </div>
    </div>
  </div>
);

ChartSkeleton.propTypes = {
  height: PropTypes.string,
  className: PropTypes.string,
  barCount: PropTypes.number,
};

export default CardSkeleton;
