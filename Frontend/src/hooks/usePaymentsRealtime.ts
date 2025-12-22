import { useEffect, useRef, useContext } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import * as Sentry from '@sentry/react';
import { supabase } from '../supabaseClient';
import { AuthContext } from '../contexts/AuthContext';
import type { RealtimeChannel } from '@supabase/supabase-js';

/**
 * Hook to subscribe to real-time changes on the payments table.
 *
 * Automatically invalidates React Query cache when:
 * - New payment is created (INSERT)
 * - Payment is updated (UPDATE)
 * - Payment is deleted (DELETE)
 *
 * This provides instant updates without polling, following the same pattern
 * used by Linear, Notion, and Figma for real-time collaborative data.
 *
 */
export const usePaymentsRealtime = () => {
  const queryClient = useQueryClient();
  const authContext = useContext(AuthContext);
  const channelRef = useRef<RealtimeChannel | null>(null);

  useEffect(() => {
    // Only subscribe if user is authenticated
    if (!authContext?.isAuthenticated || !authContext?.user?.id) {
      return;
    }

    // Create a unique channel name for this user's payments subscriptions
    const channelName = `payments-realtime-${authContext.user.id}`;

    // Set up Supabase Realtime subscription
    const channel = supabase
      .channel(channelName)
      .on(
        'postgres_changes',
        {
          event: 'INSERT',
          schema: 'public',
          table: 'payments',
        },
        (payload) => {
          // Only log IDs to avoid sensitive data exposure
          console.log('[PaymentsRealtime] New payment received, id:', payload.new?.id);

          // Invalidate all accounting/payments queries to refetch fresh data
          queryClient.invalidateQueries({ queryKey: ['accounting', 'payments'] });
          queryClient.invalidateQueries({ queryKey: ['accounting', 'outstandingPayments'] });
          queryClient.invalidateQueries({ queryKey: ['accounting', 'overview'] });

          Sentry.addBreadcrumb({
            category: 'realtime',
            message: 'Payment created',
            level: 'info',
            data: { paymentId: payload.new?.id },
          });
        }
      )
      .on(
        'postgres_changes',
        {
          event: 'UPDATE',
          schema: 'public',
          table: 'payments',
        },
        (payload) => {
          // Only log IDs to avoid sensitive data exposure
          console.log('[PaymentsRealtime] Payment updated, id:', payload.new?.id);

          // Invalidate all accounting/payments queries to refetch fresh data
          queryClient.invalidateQueries({ queryKey: ['accounting', 'payments'] });
          queryClient.invalidateQueries({ queryKey: ['accounting', 'outstandingPayments'] });
          queryClient.invalidateQueries({ queryKey: ['accounting', 'overview'] });

          Sentry.addBreadcrumb({
            category: 'realtime',
            message: 'Payment updated',
            level: 'info',
            data: { paymentId: payload.new?.id },
          });
        }
      )
      .on(
        'postgres_changes',
        {
          event: 'DELETE',
          schema: 'public',
          table: 'payments',
        },
        (payload) => {
          // Only log IDs to avoid sensitive data exposure
          console.log('[PaymentsRealtime] Payment deleted, id:', payload.old?.id);

          // Invalidate all accounting/payments queries to refetch fresh data
          queryClient.invalidateQueries({ queryKey: ['accounting', 'payments'] });
          queryClient.invalidateQueries({ queryKey: ['accounting', 'outstandingPayments'] });
          queryClient.invalidateQueries({ queryKey: ['accounting', 'overview'] });

          Sentry.addBreadcrumb({
            category: 'realtime',
            message: 'Payment deleted',
            level: 'info',
            data: { paymentId: payload.old?.id },
          });
        }
      )
      .subscribe((status) => {
        console.log('[PaymentsRealtime] Subscription status:', status);

        if (status === 'SUBSCRIBED') {
          Sentry.addBreadcrumb({
            category: 'realtime',
            message: 'Payments realtime subscription active',
            level: 'info',
          });
        } else if (status === 'CHANNEL_ERROR' || status === 'TIMED_OUT' || status === 'CLOSED') {
          console.warn('[PaymentsRealtime] Subscription failed:', status);

          Sentry.captureMessage(`Payments realtime subscription ${status}`, {
            level: 'warning',
            tags: {
              component: 'usePaymentsRealtime',
              status,
            },
          });
        }
      });

    channelRef.current = channel;

    // Cleanup subscription on unmount or auth change
    return () => {
      console.log('[PaymentsRealtime] Unsubscribing from channel');
      if (channelRef.current) {
        supabase.removeChannel(channelRef.current);
        channelRef.current = null;
      }
    };
  }, [authContext?.isAuthenticated, authContext?.user?.id, queryClient]);

  // Return nothing - this is a side-effect only hook
  return null;
};

export default usePaymentsRealtime;
