/**
 * Subscription Banner
 * Displays trial countdown and subscription prompts
 */

import React from 'react';
import type { SubscriptionStatus } from '../../types/billing';

interface SubscriptionBannerProps {
  subscriptionStatus: SubscriptionStatus;
  onUpgradeClick?: () => void;
}

const SubscriptionBanner: React.FC<SubscriptionBannerProps> = ({
  subscriptionStatus,
  onUpgradeClick,
}) => {
  // Don't show banner if user has an active, non-trial, non-canceling subscription
  if (
    subscriptionStatus.has_active_subscription &&
    !subscriptionStatus.trial_active &&
    !subscriptionStatus.cancel_at_period_end
  ) {
    return null;
  }

  // Subscription set to cancel at end of period
  if (
    subscriptionStatus.has_active_subscription &&
    subscriptionStatus.cancel_at_period_end &&
    subscriptionStatus.current_period_end
  ) {
    const endDate = new Date(subscriptionStatus.current_period_end).toLocaleDateString();
    
    return (
      <div className="bg-orange-50 dark:bg-orange-900/20 border-l-4 border-orange-400 p-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center">
            <div className="flex-shrink-0">
              <i className="fas fa-info-circle text-orange-400 text-xl"></i>
            </div>
            <div className="ml-3">
              <p className="text-sm font-medium text-orange-800 dark:text-orange-300">
                Your subscription will end on {endDate}
              </p>
              <p className="text-sm text-orange-700 dark:text-orange-400 mt-1">
                You'll still have access until then. Resume anytime to keep your subscription active.
              </p>
            </div>
          </div>
          <button
            onClick={onUpgradeClick || (() => window.location.href = '/settings?tab=billing')}
            className="ml-4 px-4 py-2 bg-orange-600 text-white rounded-lg hover:bg-orange-700 transition-colors text-sm font-medium whitespace-nowrap"
          >
            Resume Subscription
          </button>
        </div>
      </div>
    );
  }

  // Trial ending soon (less than 3 days)
  if (
    subscriptionStatus.trial_active &&
    subscriptionStatus.trial_days_remaining !== undefined &&
    subscriptionStatus.trial_days_remaining <= 3
  ) {
    return (
      <div className="bg-yellow-50 dark:bg-yellow-900/20 border-l-4 border-yellow-400 p-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center">
            <div className="flex-shrink-0">
              <i className="fas fa-clock text-yellow-400 text-xl"></i>
            </div>
            <div className="ml-3">
              <p className="text-sm font-medium text-yellow-800 dark:text-yellow-300">
                Your trial ends in {subscriptionStatus.trial_days_remaining} day
                {subscriptionStatus.trial_days_remaining !== 1 ? 's' : ''}
              </p>
              <p className="text-sm text-yellow-700 dark:text-yellow-400 mt-1">
                Subscribe now to continue using Brikli without interruption
              </p>
            </div>
          </div>
          <button
            onClick={onUpgradeClick || (() => window.location.href = '/settings?tab=billing')}
            className="ml-4 px-4 py-2 bg-yellow-600 text-white rounded-lg hover:bg-yellow-700 transition-colors text-sm font-medium whitespace-nowrap"
          >
            Subscribe Now
          </button>
        </div>
      </div>
    );
  }

  // Trial active (more than 3 days remaining)
  if (subscriptionStatus.trial_active) {
    return (
      <div className="bg-blue-50 dark:bg-blue-900/20 border-l-4 border-blue-400 p-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center">
            <div className="flex-shrink-0">
              <i className="fas fa-gift text-blue-400 text-xl"></i>
            </div>
            <div className="ml-3">
              <p className="text-sm font-medium text-blue-800 dark:text-blue-300">
                You're on a free trial
              </p>
              <p className="text-sm text-blue-700 dark:text-blue-400 mt-1">
                {subscriptionStatus.trial_days_remaining} days remaining
              </p>
            </div>
          </div>
          <button
            onClick={onUpgradeClick || (() => window.location.href = '/settings?tab=billing')}
            className="ml-4 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors text-sm font-medium whitespace-nowrap"
          >
            View Plans
          </button>
        </div>
      </div>
    );
  }

  // No subscription, no trial
  if (!subscriptionStatus.has_active_subscription) {
    return (
      <div className="bg-red-50 dark:bg-red-900/20 border-l-4 border-red-400 p-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center">
            <div className="flex-shrink-0">
              <i className="fas fa-exclamation-triangle text-red-400 text-xl"></i>
            </div>
            <div className="ml-3">
              <p className="text-sm font-medium text-red-800 dark:text-red-300">
                Subscription required
              </p>
              <p className="text-sm text-red-700 dark:text-red-400 mt-1">
                Subscribe to continue using Brikli
              </p>
            </div>
          </div>
          <button
            onClick={onUpgradeClick || (() => window.location.href = '/settings?tab=billing')}
            className="ml-4 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors text-sm font-medium whitespace-nowrap"
          >
            Subscribe Now
          </button>
        </div>
      </div>
    );
  }

  return null;
};

export default SubscriptionBanner;

