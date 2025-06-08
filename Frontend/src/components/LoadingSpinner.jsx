import React from "react";
import PropTypes from "prop-types";

const LoadingSpinner = ({ 
  message = "Loading...", 
  size = "large", 
  center = true 
}) => {
  const sizeClasses = {
    small: "h-4 w-4",
    medium: "h-8 w-8", 
    large: "h-12 w-12"
  };

  const containerClasses = center 
    ? "flex justify-center items-center h-full p-8"
    : "p-4";

  return (
    <div 
      className={containerClasses}
      role="status"
      aria-live="polite"
      aria-label={`Loading: ${message}`}
      aria-describedby="loading-text"
    >
      <div className={center ? "text-center" : ""}>
        <div 
          className={`animate-spin rounded-full border-b-2 border-blue-500 mx-auto ${sizeClasses[size]}`}
          aria-hidden="true"
        />
        <p className="mt-3 text-gray-600" id="loading-text">
          {message}
        </p>
      </div>
    </div>
  );
};

LoadingSpinner.propTypes = {
  message: PropTypes.string,
  size: PropTypes.oneOf(['small', 'medium', 'large']),
  center: PropTypes.bool,
};

export default LoadingSpinner;
