import React from "react";

const LoadingSpinner = ({ message = "Loading..." }) => {
  return (
    <div className="p-8 text-center">
      <div className="inline-block animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-blue-500 mb-2" />
      <p className="text-gray-600">{message}</p>
    </div>
  );
};

export default LoadingSpinner;
