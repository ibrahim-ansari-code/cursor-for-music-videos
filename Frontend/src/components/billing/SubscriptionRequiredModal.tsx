/**
 * Subscription Required Modal
 * Shown when users attempt to access premium features without an active subscription
 */

import React from 'react';
import ReactDOM from 'react-dom';
import { useNavigate } from 'react-router-dom';
import * as Sentry from '@sentry/react';

interface SubscriptionRequiredModalProps {
  isOpen: boolean;
  onClose: () => void;
  featureName?: string;
}

const SubscriptionRequiredModal: React.FC<SubscriptionRequiredModalProps> = ({
  isOpen,
  onClose,
  featureName = 'this feature',
}) => {
  const navigate = useNavigate();

  if (!isOpen) return null;

  const handleUpgrade = () => {
    Sentry.logger.info('User clicked upgrade from subscription modal', {
      feature: featureName,
    });
    
    // Use React Router for client-side navigation to avoid page refresh
    navigate('/settings?tab=billing');
    onClose(); // Close the modal after navigating
  };

  return ReactDOM.createPortal(
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-[9999] p-4 backdrop-blur-sm">
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-2xl max-w-md w-full p-6 transform transition-all scale-100 opacity-100 border border-gray-200 dark:border-gray-700">
        {/* Icon */}
        <div className="flex justify-center mb-4">
          <div className="rounded-full bg-blue-100 dark:bg-blue-900/30 p-3">
            <i className="fas fa-lock text-blue-600 dark:text-blue-400 text-3xl"></i>
          </div>
        </div>

        {/* Title */}
        <h2 className="text-2xl font-bold text-gray-900 dark:text-white text-center mb-2">
          Subscription Required
        </h2>

        {/* Description */}
        <p className="text-gray-600 dark:text-gray-400 text-center mb-6">
          Access to {featureName} requires an active Brikli Premium subscription.
        </p>

        {/* Features List */}
        <div className="bg-gray-50 dark:bg-gray-900/50 rounded-lg p-4 mb-6">
          <p className="text-sm font-semibold text-gray-900 dark:text-white mb-3">
            Brikli Premium includes:
          </p>
          <ul className="space-y-2 text-sm text-gray-600 dark:text-gray-400">
            <li className="flex items-center">
              <i className="fas fa-check text-green-500 mr-2"></i>
              <span>Unlimited properties and tenants</span>
            </li>
            <li className="flex items-center">
              <i className="fas fa-check text-green-500 mr-2"></i>
              <span>Advanced reporting and analytics</span>
            </li>
            <li className="flex items-center">
              <i className="fas fa-check text-green-500 mr-2"></i>
              <span>QuickBooks integration</span>
            </li>
            <li className="flex items-center">
              <i className="fas fa-check text-green-500 mr-2"></i>
              <span>Priority support</span>
            </li>
            <li className="flex items-center">
              <i className="fas fa-gift text-green-500 mr-2"></i>
              <span className="font-medium">14-day free trial</span>
            </li>
          </ul>
        </div>

        {/* Actions */}
        <div className="flex gap-3">
          <button
            onClick={onClose}
            className="flex-1 px-4 py-2 border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
          >
            Not Now
          </button>
          <button
            onClick={handleUpgrade}
            className="flex-1 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors font-medium"
          >
            <i className="fas fa-arrow-right mr-2"></i>
            Upgrade Now
          </button>
        </div>
      </div>
    </div>,
    document.body
  );
};

export default SubscriptionRequiredModal;

