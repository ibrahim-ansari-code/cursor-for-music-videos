import React, { useState, useEffect } from "react";
import { updateLeaseStatus } from "../../utils/api";

const UpdateLeaseStatusModal = ({ isOpen, onClose, lease, onUpdate }) => {
  const [error, setError] = useState(null);
  const [isUpdating, setIsUpdating] = useState(false);
  const [userType, setUserType] = useState(null);
  const [needsResolution, setNeedsResolution] = useState(false);
  const [statusToRetry, setStatusToRetry] = useState(null);

  useEffect(() => {
    // Get the user type from localStorage
    const storedUserType = localStorage.getItem("user_type");
    console.log("Current user type from localStorage:", storedUserType);
    setUserType(storedUserType);
  }, []);

  const resetState = () => {
    setError(null);
    setIsUpdating(false);
    setNeedsResolution(false);
    setStatusToRetry(null);
  };

  const handleClose = () => {
    resetState();
    onClose();
  };

  if (!isOpen || !lease) return null;

  const getStatusBadgeClass = (status) => {
    switch (status.toLowerCase()) {
      case "active":
        return "badge-success";
      case "pending":
        return "badge-warning";
      case "expired":
      case "terminated":
        return "badge-danger";
      case "draft":
        return "badge-info";
      default:
        return "badge-info";
    }
  };

  const handleStatusChange = async (newStatus) => {
    setIsUpdating(true);
    setError(null);
    setNeedsResolution(false);

    try {
      console.log(
        `Updating lease ${lease.id} status to ${newStatus} with user type ${userType}`
      );
      const response = await updateLeaseStatus(lease.id, newStatus);
      console.log("Lease status updated successfully:", response);

      if (onUpdate) {
        onUpdate();
      }
      handleClose();
    } catch (err) {
      console.error("Error updating lease status:", err);

      // Improved error handling for fetch/axios errors
      const isNetworkError =
        err.code === "ECONNABORTED" ||
        (!err.response &&
          ((err.message &&
            (err.message.includes("Failed to fetch") ||
              err.message.includes("NetworkError") ||
              err.message.includes("Network request failed"))) ||
            err instanceof TypeError));

      const httpStatus = err.response?.status || err.status;

      if (httpStatus === 403) {
        setError(
          "You do not have permission to update the lease status."
        );
      } else if (httpStatus === 500 || isNetworkError) {
        setError("An error occurred. Your change may have been applied.");
        setNeedsResolution(true);
        setStatusToRetry(newStatus);
      } else {
        setError(
          `Failed to update lease status: ${err.message || err.response?.data?.detail || "Unknown error"}`
        );
      }
    } finally {
      setIsUpdating(false);
    }
  };

  const handleCheckStatus = () => {
    if (onUpdate) {
      onUpdate();
    }
    handleClose();
  };

  if (userType && userType !== "LANDLORD" && userType !== "ADMIN") {
    return (
      <div className="fixed inset-0 overflow-y-auto z-50 flex items-center justify-center">
        <div className="fixed inset-0 bg-black bg-opacity-50"></div>
        <div className="relative bg-white dark:bg-gray-800 rounded-lg max-w-md w-full mx-auto p-6">
          <h3 className="text-lg font-medium text-gray-900 dark:text-gray-100">Update Lease Status</h3>
          <div className="mt-4 mb-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-700 text-red-700 dark:text-red-400 px-4 py-3 rounded">
            You do not have permission to update lease status.
          </div>
          <div className="mt-6 flex justify-end">
            <button
              type="button"
              onClick={handleClose}
              className="inline-flex justify-center px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm hover:bg-gray-50 dark:hover:bg-gray-600 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 dark:focus:ring-offset-gray-800"
            >
              Close
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="fixed inset-0 overflow-y-auto z-50 flex items-center justify-center">
      <div className="fixed inset-0 bg-black bg-opacity-50"></div>
      <div className="relative bg-white dark:bg-gray-800 rounded-lg max-w-md w-full mx-auto p-6">
        <div className="flex justify-between items-center mb-4">
          <h3 className="text-lg font-medium text-gray-900 dark:text-gray-100">Update Lease Status</h3>
          <button
            type="button"
            onClick={handleClose}
            className="text-gray-400 dark:text-gray-500 hover:text-gray-500 dark:hover:text-gray-300"
          >
            <i className="fas fa-times"></i>
          </button>
        </div>

        {error && (
          <div className="mb-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-700 text-red-700 dark:text-red-400 px-4 py-3 rounded relative">
            <div className="flex justify-between items-center">
              <span className="block sm:inline">{error}</span>
              <button
                type="button"
                onClick={() => setError(null)}
                className="p-1 rounded-full hover:bg-red-100 dark:hover:bg-red-800/30"
              >
                <i className="fas fa-times"></i>
              </button>
            </div>
            {needsResolution && (
              <div className="mt-3 flex space-x-2">
                <button
                  type="button"
                  className="bg-blue-500 dark:bg-blue-600 hover:bg-blue-700 dark:hover:bg-blue-500 text-white font-bold py-1 px-3 rounded text-sm"
                  onClick={() => handleStatusChange(statusToRetry)}
                  disabled={isUpdating}
                >
                  {isUpdating ? "Retrying..." : "Retry"}
                </button>
                <button
                  type="button"
                  className="bg-gray-500 dark:bg-gray-600 hover:bg-gray-700 dark:hover:bg-gray-500 text-white font-bold py-1 px-3 rounded text-sm"
                  onClick={handleCheckStatus}
                >
                  Check Status
                </button>
              </div>
            )}
          </div>
        )}

        <div className="mb-4">
          <p className="text-sm text-gray-500 dark:text-gray-400">
            Current Status:{" "}
            <span className={`badge ${getStatusBadgeClass(lease.status)}`}>
              {lease.status.charAt(0).toUpperCase() +
                lease.status.slice(1).toLowerCase()}
            </span>
          </p>
        </div>

        <div className="space-y-2">
          <p className="text-sm font-medium text-gray-700 dark:text-gray-300">Change status to:</p>
          <div className="grid grid-cols-2 gap-2">
            {[
              "DRAFT",
              "PENDING",
              "ACTIVE",
              "EXPIRED",
              "TERMINATED",
              "RENEWED",
            ].map((status) => (
              <button
                key={status}
                type="button"
                onClick={() => handleStatusChange(status)}
                disabled={isUpdating || lease.status.toUpperCase() === status}
                className={`px-4 py-2 text-sm font-medium rounded-md transition-colors ${
                  lease.status.toUpperCase() === status
                    ? "bg-gray-200 dark:bg-gray-600 text-gray-500 dark:text-gray-400 cursor-not-allowed"
                    : "bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-600 focus:outline-none focus:ring-2 focus:ring-blue-500"
                }`}
              >
                {status.charAt(0) + status.slice(1).toLowerCase()}
              </button>
            ))}
          </div>
        </div>

        <div className="mt-6 flex justify-end">
          <button
            type="button"
            onClick={handleClose}
            className="inline-flex justify-center px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm hover:bg-gray-50 dark:hover:bg-gray-600 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 dark:focus:ring-offset-gray-800"
          >
            Cancel
          </button>
        </div>
      </div>
    </div>
  );
};

export default UpdateLeaseStatusModal;
