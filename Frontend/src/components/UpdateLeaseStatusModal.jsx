import React, { useState, useEffect } from 'react';
import { updateLeaseStatus } from '../utils/api';

const UpdateLeaseStatusModal = ({ isOpen, onClose, lease, onUpdate }) => {
  const [error, setError] = useState(null);
  const [isUpdating, setIsUpdating] = useState(false);
  const [userType, setUserType] = useState(null);

  useEffect(() => {
    // Get the user type from localStorage
    const storedUserType = localStorage.getItem('user_type');
    console.log('Current user type from localStorage:', storedUserType);
    setUserType(storedUserType);
  }, []);

  if (!isOpen || !lease) return null;

  const getStatusBadgeClass = (status) => {
    switch (status.toLowerCase()) {
      case 'active':
        return 'badge-success';
      case 'pending':
        return 'badge-warning';
      case 'expired':
      case 'terminated':
        return 'badge-danger';
      case 'draft':
        return 'badge-info';
      default:
        return 'badge-info';
    }
  };

  const handleStatusChange = async (newStatus) => {
    setIsUpdating(true);
    setError(null);
    
    try {
      console.log(`Updating lease ${lease.id} status to ${newStatus} with user type ${userType}`);
      // The status must be uppercase to match the enum values in the backend
      const response = await updateLeaseStatus(lease.id, newStatus);
      console.log('Lease status updated successfully:', response);
      
      if (onUpdate) {
        onUpdate();
      }
      onClose();
    } catch (err) {
      console.error('Error updating lease status:', err);
      
      // Log more details about the error for debugging
      console.error('Error status:', err.status);
      console.error('Error message:', err.message);
      if (err.data) console.error('Error data:', err.data);
      
      // Check if it's a network error (CORS or other) or a database greenlet error
      const isNetworkError = !err.status && (
        (err.message && (
          err.message.includes('Failed to fetch') || 
          err.message.includes('NetworkError') ||
          err.message.includes('fetch')
        )) || 
        err instanceof TypeError
      );
      
      const isGreenletError = err.message && 
        (err.message.includes('MissingGreenlet') || 
         err.message.includes('greenlet_spawn') ||
         err.message.includes('await_only'));
      
      // Handle different types of errors
      if (err.status === 403) {
        setError('You do not have permission to update the lease status. Only landlords and admins can change lease status.');
      } else if (err.status === 422) {
        setError(`Invalid status value: ${newStatus}. Please try again.`);
      } else if (err.status === 500 || isNetworkError || isGreenletError) {
        // Show a clear message
        setError(`Error occurred. Your change may have been applied.`);
        
        // Add buttons for retry and check status
        setTimeout(() => {
          const container = document.querySelector('.retry-button-container');
          if (container) {
            // Clear any existing buttons
            container.innerHTML = '';
            
            // Add retry button
            const retryBtn = document.createElement('button');
            retryBtn.className = 'bg-blue-500 hover:bg-blue-700 text-white font-bold py-1 px-3 rounded mr-2';
            retryBtn.textContent = 'Retry';
            retryBtn.onclick = () => handleStatusChange(newStatus);
            container.appendChild(retryBtn);
            
            // Add check status button
            const checkBtn = document.createElement('button');
            checkBtn.className = 'bg-gray-500 hover:bg-gray-700 text-white font-bold py-1 px-3 rounded';
            checkBtn.textContent = 'Check Status';
            checkBtn.onclick = () => {
              if (onUpdate) {
                onUpdate();
                onClose();
              }
            };
            container.appendChild(checkBtn);
          }
        }, 10);
      } else {
        setError(`Failed to update lease status: ${err.message || 'Unknown error'}`);
      }
    } finally {
      setIsUpdating(false);
    }
  };

  // Render authorization error if user is not a landlord or admin
  if (userType && userType !== 'LANDLORD' && userType !== 'ADMIN') {
    return (
      <div className="fixed inset-0 overflow-y-auto z-50 flex items-center justify-center">
        <div className="fixed inset-0 bg-black bg-opacity-50"></div>
        <div className="relative bg-white rounded-lg max-w-md w-full mx-auto p-6">
          <div className="flex justify-between items-center mb-4">
            <h3 className="text-lg font-medium">Update Lease Status</h3>
            <button onClick={onClose} className="text-gray-400 hover:text-gray-500">
              <i className="fas fa-times"></i>
            </button>
          </div>
          
          <div className="mb-4 bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
            You do not have permission to update lease status. Only landlords and administrators can perform this action.
          </div>
          
          <div className="mt-6 flex justify-end">
            <button
              onClick={onClose}
              className="inline-flex justify-center px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md shadow-sm hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
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
      <div className="relative bg-white rounded-lg max-w-md w-full mx-auto p-6">
        <div className="flex justify-between items-center mb-4">
          <h3 className="text-lg font-medium">Update Lease Status</h3>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-500">
            <i className="fas fa-times"></i>
          </button>
        </div>
        
        {error && (
          <div className="mb-4 bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded relative error-message">
            <span className="block sm:inline">{error}</span>
            <button
              onClick={() => setError(null)}
              className="absolute top-0 right-0 px-4 py-3"
            >
              <span className="sr-only">Dismiss</span>
              <svg
                className="h-6 w-6 text-red-500"
                xmlns="http://www.w3.org/2000/svg"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                aria-hidden="true"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth="2"
                  d="M6 18L18 6M6 6l12 12"
                />
              </svg>
            </button>
            <div className="retry-button-container mt-2"></div>
          </div>
        )}
        
        <div className="mb-4">
          <p className="text-sm text-gray-500">
            Current Status: <span className={`badge ${getStatusBadgeClass(lease.status)}`}>
              {lease.status.charAt(0).toUpperCase() + lease.status.slice(1).toLowerCase()}
            </span>
          </p>
        </div>
        
        <div className="space-y-2">
          <p className="text-sm font-medium text-gray-700">Change status to:</p>
          
          <div className="grid grid-cols-2 gap-2">
            {['DRAFT', 'PENDING', 'ACTIVE', 'EXPIRED', 'TERMINATED', 'RENEWED'].map((status) => (
              <button
                key={status}
                onClick={() => handleStatusChange(status)}
                disabled={isUpdating || lease.status.toUpperCase() === status}
                className={`px-4 py-2 text-sm font-medium rounded-md ${
                  lease.status.toUpperCase() === status 
                    ? 'bg-gray-100 text-gray-400 cursor-not-allowed'
                    : 'bg-white border border-gray-300 text-gray-700 hover:bg-gray-50'
                }`}
              >
                {status.charAt(0) + status.slice(1).toLowerCase()}
              </button>
            ))}
          </div>
        </div>
        
        <div className="mt-6 flex justify-end">
          <button
            onClick={onClose}
            className="inline-flex justify-center px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md shadow-sm hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
          >
            Cancel
          </button>
        </div>
      </div>
    </div>
  );
};

export default UpdateLeaseStatusModal; 