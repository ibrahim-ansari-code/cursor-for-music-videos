/**
 * Subscription Management Hook
 * Provides subscription status and guards for premium features
 */

import { useState, useEffect, useCallback } from 'react';
import * as Sentry from '@sentry/react';
import { getSubscriptionStatus, isPaymentRequiredError } from '../utils/api/billing';
import type { SubscriptionStatus } from '../types/billing';

interface UseSubscriptionReturn {
  subscriptionStatus: SubscriptionStatus | null;
  loading: boolean;
  error: string | null;
  hasActiveSubscription: boolean;
  isTrialing: boolean;
  refetchStatus: () => Promise<void>;
}

/**
 * Hook to fetch and manage subscription status
 * @returns Subscription status and helper functions
 */
export function useSubscription(): UseSubscriptionReturn {
  const [subscriptionStatus, setSubscriptionStatus] = useState<SubscriptionStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchStatus = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      
      const status = await getSubscriptionStatus();
      setSubscriptionStatus(status);
      
      Sentry.logger.debug('Subscription status loaded', {
        hasActiveSubscription: status.has_active_subscription,
        status: status.subscription_status,
      });
    } catch (err) {
      console.error('Failed to fetch subscription status:', err);
      setError('Failed to load subscription status');
      
      Sentry.captureException(err, {
        tags: {
          hook: 'useSubscription',
          action: 'fetch_status',
        },
      });
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchStatus();
  }, [fetchStatus]);

  return {
    subscriptionStatus,
    loading,
    error,
    hasActiveSubscription: subscriptionStatus?.has_active_subscription ?? false,
    isTrialing: subscriptionStatus?.trial_active ?? false,
    refetchStatus: fetchStatus,
  };
}

/**
 * Global error handler for API errors
 * Redirects to billing page if subscription is required
 * @param error Error object from API
 */
export function handleSubscriptionError(error: unknown): void {
  if (isPaymentRequiredError(error)) {
    console.warn('Subscription required, redirecting to billing...');
    
    Sentry.logger.warn('User attempted to access premium feature without subscription', {
      error: error instanceof Error ? error.message : String(error),
    });
    
    // Redirect to billing page with query parameter
    window.location.href = '/settings?tab=billing&reason=subscription_required';
  }
}

