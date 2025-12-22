/**
 * OnlinePaymentsBanner Component
 * 
 * Contextual banner for Stripe Connect onboarding and status display.
 * Shows different states: not started, incomplete, pending, active.
 */

import React, { useState, useCallback } from 'react';
import { toast } from 'react-toastify';
import { 
  useConnectAccountState,
  useConnectStatus,
  useStartOnboarding, 
  useRefreshOnboardingLink,
  useStripeDashboardLink,
} from '../../hooks/useConnectStatus';
import { useSubscriptionGuard } from '../../hooks/useSubscriptionGuard';

// =============================================================================
// Banner States
// =============================================================================

interface BannerProps {
  onDismiss?: () => void;
}

/**
 * Not Started State - Encourage landlord to set up online payments
 */
const NotStartedBanner: React.FC<BannerProps> = ({ onDismiss }) => {
  const startOnboarding = useStartOnboarding();
  const guardAction = useSubscriptionGuard({ featureName: 'online rent payments' });
  const [isRedirecting, setIsRedirecting] = useState(false);

  const handleSetup = guardAction(useCallback(async () => {
    try {
      setIsRedirecting(true);
      const result = await startOnboarding.mutateAsync();
      // Redirect to Stripe hosted onboarding
      window.location.href = result.onboarding_url;
    } catch (error) {
      setIsRedirecting(false);
      toast.error('Failed to start setup. Please try again.');
      console.error('Onboarding error:', error);
    }
  }, [startOnboarding]));

  return (
    <div className="bg-gradient-to-r from-emerald-50 to-teal-50 dark:from-emerald-900/20 dark:to-teal-900/20 border border-emerald-200 dark:border-emerald-700/50 rounded-lg p-4 mb-4">
      <div className="flex items-start justify-between">
        <div className="flex items-start space-x-3">
          <div className="flex-shrink-0">
            <div className="w-10 h-10 rounded-full bg-emerald-100 dark:bg-emerald-800/50 flex items-center justify-center">
              <i className="fas fa-credit-card text-emerald-600 dark:text-emerald-400 text-lg" />
            </div>
          </div>
          <div className="flex-1">
            <h3 className="text-sm font-semibold text-emerald-900 dark:text-emerald-100">
              Accept Online Rent Payments
            </h3>
            <p className="mt-1 text-sm text-emerald-700 dark:text-emerald-300">
              Let tenants pay rent directly to your bank account.
            </p>
            <div className="mt-2 flex items-center space-x-4 text-xs text-emerald-600 dark:text-emerald-400">
              <span className="flex items-center">
                <i className="fas fa-check mr-1" />
                $3-8 flat fee per payment
              </span>
              <span className="flex items-center">
                <i className="fas fa-check mr-1" />
                No monthly cost
              </span>
              <span className="flex items-center">
                <i className="fas fa-check mr-1" />
                Cancel anytime
              </span>
            </div>
          </div>
        </div>
        <div className="flex items-center space-x-2">
          <button
            onClick={handleSetup}
            disabled={startOnboarding.isPending || isRedirecting}
            className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-emerald-600 hover:bg-emerald-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-emerald-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {startOnboarding.isPending || isRedirecting ? (
              <>
                <i className="fas fa-spinner fa-spin mr-2" />
                Setting up...
              </>
            ) : (
              <>
                Get Started
                <i className="fas fa-arrow-right ml-2" />
              </>
            )}
          </button>
          {onDismiss && (
            <button
              onClick={onDismiss}
              className="text-emerald-500 hover:text-emerald-700 dark:text-emerald-400 dark:hover:text-emerald-300 p-2"
              title="Dismiss for now"
            >
              <i className="fas fa-times" />
            </button>
          )}
        </div>
      </div>
    </div>
  );
};

/**
 * Incomplete State - Landlord started but didn't finish onboarding
 */
const IncompleteBanner: React.FC = () => {
  const refreshLink = useRefreshOnboardingLink();
  const guardAction = useSubscriptionGuard({ featureName: 'online rent payments' });
  const [isRedirecting, setIsRedirecting] = useState(false);

  const handleContinue = guardAction(useCallback(async () => {
    try {
      setIsRedirecting(true);
      const result = await refreshLink.mutateAsync();
      window.location.href = result.onboarding_url;
    } catch (error) {
      setIsRedirecting(false);
      toast.error('Failed to get setup link. Please try again.');
      console.error('Refresh link error:', error);
    }
  }, [refreshLink]));

  return (
    <div className="bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-700/50 rounded-lg p-4 mb-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <div className="flex-shrink-0">
            <div className="w-10 h-10 rounded-full bg-amber-100 dark:bg-amber-800/50 flex items-center justify-center">
              <i className="fas fa-exclamation-circle text-amber-600 dark:text-amber-400 text-lg" />
            </div>
          </div>
          <div>
            <h3 className="text-sm font-semibold text-amber-900 dark:text-amber-100">
              Complete Your Payout Setup
            </h3>
            <p className="mt-1 text-sm text-amber-700 dark:text-amber-300">
              Finish verifying your identity to start accepting online rent payments.
            </p>
          </div>
        </div>
        <button
          onClick={handleContinue}
          disabled={refreshLink.isPending || isRedirecting}
          className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-amber-600 hover:bg-amber-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-amber-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {refreshLink.isPending || isRedirecting ? (
            <>
              <i className="fas fa-spinner fa-spin mr-2" />
              Loading...
            </>
          ) : (
            <>
              Continue Setup
              <i className="fas fa-arrow-right ml-2" />
            </>
          )}
        </button>
      </div>
    </div>
  );
};

/**
 * Pending Verification State - Waiting on Stripe
 */
const PendingBanner: React.FC = () => {
  return (
    <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-700/50 rounded-lg p-4 mb-4">
      <div className="flex items-center space-x-3">
        <div className="flex-shrink-0">
          <div className="w-10 h-10 rounded-full bg-blue-100 dark:bg-blue-800/50 flex items-center justify-center">
            <i className="fas fa-clock text-blue-600 dark:text-blue-400 text-lg" />
          </div>
        </div>
        <div>
          <h3 className="text-sm font-semibold text-blue-900 dark:text-blue-100">
            Verification in Progress
          </h3>
          <p className="mt-1 text-sm text-blue-700 dark:text-blue-300">
            Your account is being verified by Stripe. This usually takes 1-2 business days.
          </p>
        </div>
      </div>
    </div>
  );
};

/**
 * Action Required State - Stripe needs additional information/documents
 */
interface ActionRequiredBannerProps {
  isPastDue: boolean;
  requirementsCount: number;
}

const ActionRequiredBanner: React.FC<ActionRequiredBannerProps> = ({ 
  isPastDue, 
  requirementsCount,
}) => {
  const refreshLink = useRefreshOnboardingLink();
  const guardAction = useSubscriptionGuard({ featureName: 'online rent payments' });
  const [isRedirecting, setIsRedirecting] = useState(false);

  const handleTakeAction = guardAction(useCallback(async () => {
    try {
      setIsRedirecting(true);
      const result = await refreshLink.mutateAsync();
      window.location.href = result.onboarding_url;
    } catch (error) {
      setIsRedirecting(false);
      toast.error('Failed to get verification link. Please try again.');
      console.error('Refresh link error:', error);
    }
  }, [refreshLink]));

  const bgColor = isPastDue 
    ? 'bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-700/50'
    : 'bg-amber-50 dark:bg-amber-900/20 border-amber-200 dark:border-amber-700/50';
  
  const iconColor = isPastDue
    ? 'bg-red-100 dark:bg-red-800/50 text-red-600 dark:text-red-400'
    : 'bg-amber-100 dark:bg-amber-800/50 text-amber-600 dark:text-amber-400';
  
  const textColor = isPastDue
    ? 'text-red-900 dark:text-red-100'
    : 'text-amber-900 dark:text-amber-100';
  
  const subTextColor = isPastDue
    ? 'text-red-700 dark:text-red-300'
    : 'text-amber-700 dark:text-amber-300';
  
  const buttonColor = isPastDue
    ? 'bg-red-600 hover:bg-red-700 focus:ring-red-500'
    : 'bg-amber-600 hover:bg-amber-700 focus:ring-amber-500';

  return (
    <div className={`${bgColor} border rounded-lg p-4 mb-4`}>
      <div className="flex items-start justify-between">
        <div className="flex items-start space-x-3">
          <div className="flex-shrink-0">
            <div className={`w-10 h-10 rounded-full ${iconColor} flex items-center justify-center`}>
              <i className={`fas ${isPastDue ? 'fa-exclamation-triangle' : 'fa-info-circle'} text-lg`} />
            </div>
          </div>
          <div>
            <h3 className={`text-sm font-semibold ${textColor}`}>
              {isPastDue ? 'Urgent: Action Required' : 'Additional Information Needed'}
            </h3>
            <p className={`mt-1 text-sm ${subTextColor}`}>
              {isPastDue 
                ? 'Stripe needs additional documents or information immediately to keep your account active.'
                : `Stripe needs ${requirementsCount} additional ${requirementsCount === 1 ? 'item' : 'items'} to complete your verification.`
              }
            </p>
            {isPastDue && (
              <p className={`mt-1 text-xs font-medium ${subTextColor}`}>
                <i className="fas fa-exclamation-circle mr-1" />
                Payment acceptance may be suspended until this is resolved.
              </p>
            )}
          </div>
        </div>
        <button
          onClick={handleTakeAction}
          disabled={refreshLink.isPending || isRedirecting}
          className={`inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white ${buttonColor} focus:outline-none focus:ring-2 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed transition-colors ${isPastDue ? 'animate-pulse' : ''}`}
        >
          {refreshLink.isPending || isRedirecting ? (
            <>
              <i className="fas fa-spinner fa-spin mr-2" />
              Loading...
            </>
          ) : (
            <>
              {isPastDue ? 'Take Action Now' : 'Submit Information'}
              <i className="fas fa-arrow-right ml-2" />
            </>
          )}
        </button>
      </div>
    </div>
  );
};

/**
 * Active State - Minimal, non-intrusive status indicator
 */
const ActiveBanner: React.FC = () => {
  const dashboardLink = useStripeDashboardLink();

  const handleOpenDashboard = useCallback(async () => {
    try {
      const result = await dashboardLink.mutateAsync();
      window.open(result.dashboard_url, '_blank', 'noopener,noreferrer');
    } catch (error) {
      toast.error('Failed to open dashboard. Please try again.');
      console.error('Dashboard link error:', error);
    }
  }, [dashboardLink]);

  return (
    <div className="bg-gray-50 dark:bg-gray-800/50 border border-gray-200 dark:border-gray-700 rounded-lg p-3 mb-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <div className="flex items-center space-x-2">
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-2 w-2 rounded-full bg-emerald-400 opacity-75" />
              <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500" />
            </span>
            <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
              Online Payments Active
            </span>
          </div>
        </div>
        <button
          onClick={handleOpenDashboard}
          disabled={dashboardLink.isPending}
          className="inline-flex items-center text-sm text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200 transition-colors"
        >
          {dashboardLink.isPending ? (
            <i className="fas fa-spinner fa-spin" />
          ) : (
            <>
              Manage Payouts
              <i className="fas fa-external-link-alt ml-1 text-xs" />
            </>
          )}
        </button>
      </div>
    </div>
  );
};

// =============================================================================
// Main Component
// =============================================================================

interface OnlinePaymentsBannerProps {
  /** Whether the banner can be dismissed (only for not_started state) */
  dismissible?: boolean;
}

const OnlinePaymentsBanner: React.FC<OnlinePaymentsBannerProps> = ({ 
  dismissible = true,
}) => {
  const { isLoading, error, onboardingStatus, isFullyOnboarded } = useConnectAccountState();
  const { data: connectData } = useConnectStatus();
  const [isDismissed, setIsDismissed] = useState(false);

  // Check session storage for dismissal (resets on new session)
  const sessionKey = 'brikli_connect_banner_dismissed';
  const wasDismissedThisSession = typeof window !== 'undefined' 
    ? sessionStorage.getItem(sessionKey) === 'true' 
    : false;

  const handleDismiss = useCallback(() => {
    setIsDismissed(true);
    if (typeof window !== 'undefined') {
      sessionStorage.setItem(sessionKey, 'true');
    }
  }, []);

  // Don't show while loading
  if (isLoading) {
    return null;
  }

  // Don't show on error (fail silently)
  if (error) {
    return null;
  }

  // Handle dismissed state (only for not_started)
  if ((isDismissed || wasDismissedThisSession) && onboardingStatus === 'not_started') {
    return null;
  }

  // PRIORITY 1: Check if action is required (overrides all other states)
  if (connectData?.needs_action) {
    const isPastDue = (connectData.requirements_past_due?.length ?? 0) > 0;
    const totalRequirements = 
      (connectData.requirements_currently_due?.length ?? 0) + 
      (connectData.requirements_past_due?.length ?? 0);
    
    return (
      <ActionRequiredBanner 
        isPastDue={isPastDue}
        requirementsCount={totalRequirements}
      />
    );
  }

  // PRIORITY 2: Render based on standard onboarding status
  switch (onboardingStatus) {
    case 'not_started':
      return <NotStartedBanner onDismiss={dismissible ? handleDismiss : undefined} />;
    case 'incomplete':
      return <IncompleteBanner />;
    case 'pending_verification':
      return <PendingBanner />;
    case 'active':
      return isFullyOnboarded ? <ActiveBanner /> : <IncompleteBanner />;
    default:
      return null;
  }
};

export default OnlinePaymentsBanner;


