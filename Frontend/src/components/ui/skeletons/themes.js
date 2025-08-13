/**
 * Centralized skeleton theming configuration
 * Ensures consistency across both react-loading-skeleton and custom implementations
 */

export const SKELETON_THEME = {
  // Base colors matching global SkeletonTheme in App.jsx
  baseColor: '#e5e7eb',      // gray-200
  highlightColor: '#f3f4f6', // gray-100
  
  // Animation timing
  animationDuration: '1.5s',
  
  // Common radius values
  borderRadius: {
    sm: '0.25rem',   // rounded
    md: '0.375rem',  // rounded-md  
    lg: '0.5rem',    // rounded-lg
    xl: '0.75rem',   // rounded-xl
    full: '9999px',  // rounded-full
  },
  
  // Standard spacing
  spacing: {
    xs: '0.125rem', // 2px
    sm: '0.25rem',  // 4px
    md: '0.5rem',   // 8px
    lg: '1rem',     // 16px
    xl: '1.5rem',   // 24px
  }
};

const ROUNDED_CLASS_MAP = {
  sm: 'rounded',
  md: 'rounded-md',
  lg: 'rounded-lg',
  xl: 'rounded-xl',
  full: 'rounded-full',
};

/**
 * Generate consistent CSS classes for skeleton elements
 */
export const getSkeletonClasses = (options = {}) => {
  const {
    rounded = 'md',
    spacing = 'md',
    customClasses = ''
  } = options;
  
  const roundedClass = ROUNDED_CLASS_MAP[rounded] || ROUNDED_CLASS_MAP.md;
  return `animate-pulse bg-gray-200 ${roundedClass} ${customClasses}`.trim();
};

/**
 * Generate inline styles for precise dimension control
 */
export const getSkeletonStyles = (width, height) => ({
  width: typeof width === 'string' ? width : `${width}px`,
  height: typeof height === 'string' ? height : `${height}px`,
  backgroundColor: SKELETON_THEME.baseColor,
  backgroundImage: `linear-gradient(90deg, ${SKELETON_THEME.baseColor} 25%, ${SKELETON_THEME.highlightColor} 50%, ${SKELETON_THEME.baseColor} 75%)`,
  backgroundSize: '200% 100%',
  animation: `skeleton-shimmer ${SKELETON_THEME.animationDuration} infinite linear`,
});
