import React, { useId } from "react";
import PropTypes from "prop-types";

const LoadingSpinner = ({ 
  message = "Loading...", 
  size = "large", 
  center = true 
}) => {
  const uniqueId = useId();
  const descriptionId = `loading-text-${uniqueId}`;

  const sizeClasses = {
    small: "h-4 w-4",
    medium: "h-8 w-8", 
    large: "h-12 w-12"
  };

  const containerClasses = center 
    ? "flex justify-center items-center h-full p-8"
    : "p-4";

  const spinnerSizeClass = sizeClasses[size] || sizeClasses.large;

  return (
    <output 
      className={containerClasses}
      aria-live="polite"
      aria-label={`Loading: ${message}`}
      aria-describedby={descriptionId}
    >
      <div className={center ? "text-center" : ""}>
        <div 
          className={`animate-spin rounded-full border-b-2 border-blue-500 dark:border-blue-400 mx-auto transition-colors ${spinnerSizeClass}`}
          aria-hidden="true"
        />
        <p className="mt-3 text-gray-600 dark:text-gray-400 transition-colors" id={descriptionId}>
          {message}
        </p>
      </div>
    </output>
  );
};

LoadingSpinner.propTypes = {
  message: PropTypes.string,
  size: PropTypes.oneOf(['small', 'medium', 'large']),
  center: PropTypes.bool,
};

export default LoadingSpinner;
