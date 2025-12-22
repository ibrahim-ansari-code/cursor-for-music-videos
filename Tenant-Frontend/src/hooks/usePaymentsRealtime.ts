/**
 * usePaymentsRealtime Hook
 *
 * Subscribes to real-time changes on the rent_payment_transactions table.
 * Automatically invalidates React Query cache when payments are created/updated/deleted.
 *
 * This provides instant balance updates without polling, following the same pattern
 * used by Linear, Notion, and Figma for real-time collaborative data.
 *
 * Industry standard best practices:
 * - Single connection per browser tab (Supabase handles multiplexing)
 * - Proper cleanup on unmount to prevent memory leaks
 * - Fallback to polling if realtime fails (handled by React Query staleTime)
 * - Row Level Security (RLS) ensures tenants only see their own transactions
 */
import { useEffect, useRef, useContext } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import * as Sentry from '@sentry/react';
import { supabase } from '@/utils/supabaseClient';
import { AuthContext } from '@/contexts/AuthContext';
import type { RealtimeChannel } from '@supabase/supabase-js';
import { paymentsKeys } from './usePayments';

export const usePaymentsRealtime = () => {
  const queryClient = useQueryClient();
  const authContext = useContext(AuthContext);
  const channelRef = useRef<RealtimeChannel | null>(null);
  // Track intentional unsubscription to avoid false "failed" warnings
  const isUnsubscribingRef = useRef(false);

  useEffect(() => {
    // Reset flag when effect runs
    isUnsubscribingRef.current = false;

    // Only subscribe if user is authenticated
    if (!authContext?.user?.id) {
      return;
    }

    // Create a unique channel name for this tenant's payment subscriptions
    const channelName = `tenant-payments-realtime-${authContext.user.id}`;

    // Set up Supabase Realtime subscription for rent_payment_transactions table
    const channel = supabase
      .channel(channelName)
      .on(
        'postgres_changes',
        {
          event: 'INSERT',
          schema: 'public',
          table: 'rent_payment_transactions',
        },
        (payload) => {
          console.log('[TenantPaymentsRealtime] New transaction, id:', payload.new?.id);

          // Invalidate balance and transactions to refetch fresh data
          queryClient.invalidateQueries({ queryKey: paymentsKeys.balance() });
          queryClient.invalidateQueries({ queryKey: paymentsKeys.transactions() });

          Sentry.addBreadcrumb({
            category: 'realtime',
            message: 'Rent payment transaction created',
            level: 'info',
            data: { transactionId: payload.new?.id },
          });
        }
      )
      .on(
        'postgres_changes',
        {
          event: 'UPDATE',
          schema: 'public',
          table: 'rent_payment_transactions',
        },
        (payload) => {
          console.log('[TenantPaymentsRealtime] Transaction updated, id:', payload.new?.id);

          // Invalidate balance and transactions - status changes affect balance
          queryClient.invalidateQueries({ queryKey: paymentsKeys.balance() });
          queryClient.invalidateQueries({ queryKey: paymentsKeys.transactions() });

          // Also invalidate specific transaction if it's being viewed
          if (payload.new?.id) {
            queryClient.invalidateQueries({
              queryKey: paymentsKeys.transaction(payload.new.id),
            });
          }

          Sentry.addBreadcrumb({
            category: 'realtime',
            message: 'Rent payment transaction updated',
            level: 'info',
            data: {
              transactionId: payload.new?.id,
              status: payload.new?.status,
            },
          });
        }
      )
      .on(
        'postgres_changes',
        {
          event: 'DELETE',
          schema: 'public',
          table: 'rent_payment_transactions',
        },
        (payload) => {
          console.log('[TenantPaymentsRealtime] Transaction deleted, id:', payload.old?.id);

          // Invalidate balance and transactions
          queryClient.invalidateQueries({ queryKey: paymentsKeys.balance() });
          queryClient.invalidateQueries({ queryKey: paymentsKeys.transactions() });

          Sentry.addBreadcrumb({
            category: 'realtime',
            message: 'Rent payment transaction deleted',
            level: 'info',
            data: { transactionId: payload.old?.id },
          });
        }
      )
      .subscribe((status) => {
        console.log('[TenantPaymentsRealtime] Subscription status:', status);

        if (status === 'SUBSCRIBED') {
          Sentry.addBreadcrumb({
            category: 'realtime',
            message: 'Tenant payments realtime subscription active',
            level: 'info',
          });
        } else if (status === 'CHANNEL_ERROR' || status === 'TIMED_OUT' || status === 'CLOSED') {
          // Only warn if this wasn't an intentional unsubscription
          if (!isUnsubscribingRef.current) {
            console.warn('[TenantPaymentsRealtime] Subscription failed:', status);

            Sentry.captureMessage(`Tenant payments realtime subscription ${status}`, {
              level: 'warning',
              tags: {
                component: 'usePaymentsRealtime',
                status,
              },
            });
          }
          // React Query's staleTime provides automatic fallback via polling
        }
      });

    channelRef.current = channel;

    // Cleanup subscription on unmount or auth change
    return () => {
      console.log('[TenantPaymentsRealtime] Unsubscribing from channel');
      // Mark as intentional unsubscription to prevent false warnings
      isUnsubscribingRef.current = true;
      if (channelRef.current) {
        supabase.removeChannel(channelRef.current);
        channelRef.current = null;
      }
    };
  }, [authContext?.user?.id, queryClient]);

  // Return nothing - this is a side-effect only hook
  return null;
};

export default usePaymentsRealtime;
