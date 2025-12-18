/**
 * useConnectStatus Hook
 * 
 * TanStack Query hook for managing Stripe Connect account status.
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { 
  getConnectStatus, 
  startConnectOnboarding, 
  refreshConnectLink,
  getStripeDashboardLink,
  getFeeSchedule,
} from '../utils/api/connect';
import type { 
  ConnectStatusResponse, 
  ConnectOnboardingResponse,
  ConnectDashboardLinkResponse,
  FeeScheduleResponse,
} from '../types/rentPayments';

// =============================================================================
// Query Keys
// =============================================================================

export const connectQueryKeys = {
  all: ['connect'] as const,
  status: () => [...connectQueryKeys.all, 'status'] as const,
  fees: () => [...connectQueryKeys.all, 'fees'] as const,
};

// =============================================================================
// Connect Status Hook
// =============================================================================

interface UseConnectStatusOptions {
  enabled?: boolean;
}

export function useConnectStatus(options: UseConnectStatusOptions = {}) {
  const { enabled = true } = options;

  return useQuery<ConnectStatusResponse, Error>({
    queryKey: connectQueryKeys.status(),
    queryFn: getConnectStatus,
    enabled,
    staleTime: 30 * 1000, // 30 seconds - status can change frequently during onboarding
    refetchOnWindowFocus: true,
  });
}

// =============================================================================
// Onboarding Mutation
// =============================================================================

export function useStartOnboarding() {
  const queryClient = useQueryClient();

  return useMutation<ConnectOnboardingResponse, Error>({
    mutationFn: startConnectOnboarding,
    onSuccess: () => {
      // Invalidate status to refetch after onboarding starts
      queryClient.invalidateQueries({ queryKey: connectQueryKeys.status() });
    },
  });
}

// =============================================================================
// Refresh Link Mutation
// =============================================================================

export function useRefreshOnboardingLink() {
  return useMutation<ConnectOnboardingResponse, Error>({
    mutationFn: refreshConnectLink,
  });
}

// =============================================================================
// Dashboard Link Mutation
// =============================================================================

export function useStripeDashboardLink() {
  return useMutation<ConnectDashboardLinkResponse, Error>({
    mutationFn: getStripeDashboardLink,
  });
}

// =============================================================================
// Fee Schedule Hook
// =============================================================================

export function useFeeSchedule() {
  return useQuery<FeeScheduleResponse, Error>({
    queryKey: connectQueryKeys.fees(),
    queryFn: getFeeSchedule,
    staleTime: 5 * 60 * 1000, // 5 minutes - fees don't change often
  });
}

// =============================================================================
// Utility Hook - Combined Status
// =============================================================================

export interface ConnectAccountState {
  isLoading: boolean;
  error: Error | null;
  isConnected: boolean;
  isFullyOnboarded: boolean;
  onboardingStatus: ConnectStatusResponse['onboarding_status'] | null;
  needsAction: boolean;
  statusMessage: string;
}

/**
 * Combined hook that provides a simplified view of Connect account state.
 */
export function useConnectAccountState(): ConnectAccountState {
  const { data, isLoading, error } = useConnectStatus();

  if (isLoading) {
    return {
      isLoading: true,
      error: null,
      isConnected: false,
      isFullyOnboarded: false,
      onboardingStatus: null,
      needsAction: false,
      statusMessage: 'Loading...',
    };
  }

  if (error) {
    return {
      isLoading: false,
      error,
      isConnected: false,
      isFullyOnboarded: false,
      onboardingStatus: null,
      needsAction: false,
      statusMessage: 'Failed to load payment status',
    };
  }

  if (!data) {
    return {
      isLoading: false,
      error: null,
      isConnected: false,
      isFullyOnboarded: false,
      onboardingStatus: 'not_started',
      needsAction: true,
      statusMessage: 'Set up online payments to let tenants pay you directly',
    };
  }

  const isFullyOnboarded = data.charges_enabled && data.payouts_enabled && data.details_submitted;

  let statusMessage = '';
  let needsAction = false;

  // Check if Stripe needs additional information/documents
  if (data.needs_action) {
    const isPastDue = data.requirements_past_due && data.requirements_past_due.length > 0;
    statusMessage = isPastDue 
      ? 'Urgent: Additional information required to continue receiving payments'
      : 'Additional information required from Stripe';
    needsAction = true;
  } else {
    // Use standard onboarding status messages
    switch (data.onboarding_status) {
      case 'not_started':
        statusMessage = 'Set up online payments to let tenants pay you directly';
        needsAction = true;
        break;
      case 'incomplete':
        statusMessage = 'Complete your payout setup to start receiving payments';
        needsAction = true;
        break;
      case 'pending_verification':
        statusMessage = 'Your account is being verified by Stripe';
        needsAction = false;
        break;
      case 'active':
        statusMessage = 'Online payments are active';
        needsAction = false;
        break;
      default:
        statusMessage = 'Unknown status';
        needsAction = false;
    }
  }

  return {
    isLoading: false,
    error: null,
    isConnected: data.is_connected,
    isFullyOnboarded,
    onboardingStatus: data.onboarding_status,
    needsAction,
    statusMessage,
  };
}

