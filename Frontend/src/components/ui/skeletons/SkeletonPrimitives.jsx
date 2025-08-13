import React from 'react';
import PropTypes from 'prop-types';
import { getSkeletonClasses } from './themes';

/**
 * Core skeleton primitives for building consistent loading states
 * Follows Web Core Vitals best practices to prevent layout shifts
 */

/**
 * Basic line skeleton for text content
 */
export const SkeletonLine = ({ 
  width = '100%', 
  height = '1rem',
  className = '',
  rounded = 'md',
  ...props 
}) => (
  <div 
    className={getSkeletonClasses({ rounded, customClasses: className })}
    style={{ 
      width: typeof width === 'string' ? width : `${width}px`,
      height: typeof height === 'string' ? height : `${height}px`
    }}
    aria-hidden="true"
    {...props}
  />
);

SkeletonLine.propTypes = {
  width: PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
  height: PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
  className: PropTypes.string,
  rounded: PropTypes.oneOf(['sm', 'md', 'lg', 'xl', 'full']),
};

/**
 * Circle skeleton for avatars and icons
 */
export const SkeletonCircle = ({ 
  size = '2.5rem',
  className = '',
  ...props 
}) => (
  <div 
    className={getSkeletonClasses({ rounded: 'full', customClasses: className })}
    style={{ 
      width: typeof size === 'string' ? size : `${size}px`,
      height: typeof size === 'string' ? size : `${size}px`,
      flexShrink: 0
    }}
    aria-hidden="true"
    {...props}
  />
);

SkeletonCircle.propTypes = {
  size: PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
  className: PropTypes.string,
};

/**
 * Pill skeleton for badges and status indicators
 */
export const SkeletonPill = ({ 
  width = '4rem',
  height = '1.5rem',
  className = '',
  ...props 
}) => (
  <div 
    className={getSkeletonClasses({ rounded: 'full', customClasses: className })}
    style={{ 
      width: typeof width === 'string' ? width : `${width}px`,
      height: typeof height === 'string' ? height : `${height}px`
    }}
    aria-hidden="true"
    {...props}
  />
);

SkeletonPill.propTypes = {
  width: PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
  height: PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
  className: PropTypes.string,
};

/**
 * Block skeleton for larger content areas
 */
export const SkeletonBlock = ({ 
  width = '100%',
  height = '8rem',
  className = '',
  rounded = 'lg',
  ...props 
}) => (
  <div 
    className={getSkeletonClasses({ rounded, customClasses: className })}
    style={{ 
      width: typeof width === 'string' ? width : `${width}px`,
      height: typeof height === 'string' ? height : `${height}px`
    }}
    aria-hidden="true"
    {...props}
  />
);

SkeletonBlock.propTypes = {
  width: PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
  height: PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
  className: PropTypes.string,
  rounded: PropTypes.oneOf(['sm', 'md', 'lg', 'xl']),
};

/**
 * Multi-line text skeleton
 */
export const SkeletonText = ({ 
  lines = 3,
  lineHeight = '1.25rem',
  spacing = '0.5rem',
  lastLineWidth = '75%',
  className = '',
  ...props 
}) => (
  <div 
    className={className} 
    style={{ display: 'flex', flexDirection: 'column', gap: spacing }}
    aria-hidden="true" 
    {...props}
  >
    {Array.from({ length: lines }, (_, i) => (
      <SkeletonLine
        key={i}
        width={i === lines - 1 ? lastLineWidth : '100%'}
        height={lineHeight}
      />
    ))}
  </div>
);

SkeletonText.propTypes = {
  lines: PropTypes.number,
  lineHeight: PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
  spacing: PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
  lastLineWidth: PropTypes.string,
  className: PropTypes.string,
};

export default SkeletonLine;
