/**
 * Subscription Guard Hook
 * Provides a function that checks subscription before executing premium actions
 */

import { useCallback } from 'react';
import { useSubscriptionModal } from '../contexts/SubscriptionContext';
import { getSubscriptionStatus } from '../utils/api/billing';
import * as Sentry from '@sentry/react';

interface UseSubscriptionGuardOptions {
  featureName?: string;
}

/**
 * Hook that returns a guard function to check subscription before premium actions
 * 
 * Usage:
 * ```tsx
 * const guardAction = useSubscriptionGuard({ featureName: 'creating properties' });
 * 
 * const handleAddProperty = guardAction(async () => {
 *   setShowPropertyModal(true);
 * });
 * ```
 */
export function useSubscriptionGuard(options: UseSubscriptionGuardOptions = {}) {
  const { showSubscriptionModal } = useSubscriptionModal();
  const { featureName = 'this feature' } = options;

  const guardAction = useCallback(
    <T extends (...args: any[]) => any>(action: T) => {
      return async (...args: Parameters<T>): Promise<ReturnType<T> | void> => {
        try {
          // Check subscription status
          const status = await getSubscriptionStatus();
          
          if (!status.has_active_subscription) {
            // User doesn't have subscription - show modal
            Sentry.logger.info('Subscription required for action', {
              feature: featureName,
              subscription_status: status.subscription_status,
              trial_active: status.trial_active,
            });
            
            showSubscriptionModal(featureName);
            return;
          }
          
          // User has subscription - proceed with action
          return await action(...args);
        } catch (error) {
          // If subscription check fails, log but allow action
          // (Backend will enforce anyway)
          console.error('Failed to check subscription status:', error);
          Sentry.captureException(error, {
            tags: {
              component: 'useSubscriptionGuard',
              feature: featureName,
            },
          });
          
          // Proceed with action - backend will handle 402
          return await action(...args);
        }
      };
    },
    [showSubscriptionModal, featureName]
  );

  return guardAction;
}

