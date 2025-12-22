import { useEffect, useRef, useContext } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import * as Sentry from '@sentry/react';
import { supabase } from '../supabaseClient';
import { AuthContext } from '../contexts/AuthContext';
import type { RealtimeChannel } from '@supabase/supabase-js';

/**
 * Hook to subscribe to real-time changes on the maintenance_requests table.
 *
 * Automatically invalidates React Query cache when:
 * - New maintenance request is created (INSERT)
 * - Maintenance request is updated (UPDATE)
 * - Maintenance request is deleted (DELETE)
 *
 * This provides instant updates without polling, following the same pattern
 * used by Linear, Notion, and Figma for real-time collaborative data.
 *
 * @example
 * ```tsx
 * // In your Maintenance page component:
 * useMaintenanceRealtime();
 *
 * // That's it! The hook handles subscription lifecycle and cache invalidation.
 * // Your existing useMaintenanceRequests and useMaintenanceSummary hooks
 * // will automatically refetch when changes occur.
 * ```
 */
export const useMaintenanceRealtime = () => {
  const queryClient = useQueryClient();
  const authContext = useContext(AuthContext);
  const channelRef = useRef<RealtimeChannel | null>(null);

  useEffect(() => {
    // Only subscribe if user is authenticated
    if (!authContext?.isAuthenticated || !authContext?.user?.id) {
      return;
    }


    // Create a unique channel name for this user's maintenance subscriptions
    const channelName = `maintenance-realtime-${authContext.user.id}`;

    // Set up Supabase Realtime subscription
    const channel = supabase
      .channel(channelName)
      .on(
        'postgres_changes',
        {
          event: 'INSERT',
          schema: 'public',
          table: 'maintenance_requests',
        },
        (payload) => {
          // Only log IDs to avoid sensitive data exposure
          console.log('[MaintenanceRealtime] New request received, id:', payload.new?.id);

          // Invalidate all maintenance queries to refetch fresh data
          queryClient.invalidateQueries({ queryKey: ['maintenance'] });

          Sentry.addBreadcrumb({
            category: 'realtime',
            message: 'Maintenance request created',
            level: 'info',
            data: { requestId: payload.new?.id },
          });
        }
      )
      .on(
        'postgres_changes',
        {
          event: 'UPDATE',
          schema: 'public',
          table: 'maintenance_requests',
        },
        (payload) => {
          // Only log IDs to avoid sensitive data exposure
          console.log('[MaintenanceRealtime] Request updated, id:', payload.new?.id);

          // Invalidate all maintenance queries to refetch fresh data
          queryClient.invalidateQueries({ queryKey: ['maintenance'] });

          Sentry.addBreadcrumb({
            category: 'realtime',
            message: 'Maintenance request updated',
            level: 'info',
            data: { requestId: payload.new?.id },
          });
        }
      )
      .on(
        'postgres_changes',
        {
          event: 'DELETE',
          schema: 'public',
          table: 'maintenance_requests',
        },
        (payload) => {
          // Only log IDs to avoid sensitive data exposure
          console.log('[MaintenanceRealtime] Request deleted, id:', payload.old?.id);

          // Invalidate all maintenance queries to refetch fresh data
          queryClient.invalidateQueries({ queryKey: ['maintenance'] });

          Sentry.addBreadcrumb({
            category: 'realtime',
            message: 'Maintenance request deleted',
            level: 'info',
            data: { requestId: payload.old?.id },
          });
        }
      )
      .subscribe((status) => {
        console.log('[MaintenanceRealtime] Subscription status:', status);

        if (status === 'SUBSCRIBED') {
          Sentry.addBreadcrumb({
            category: 'realtime',
            message: 'Maintenance realtime subscription active',
            level: 'info',
          });
        } else if (status === 'CHANNEL_ERROR' || status === 'TIMED_OUT') {
          console.warn('[MaintenanceRealtime] Subscription failed:', status);

          Sentry.captureMessage(`Maintenance realtime subscription ${status}`, {
            level: 'warning',
            tags: {
              component: 'useMaintenanceRealtime',
              status,
            },
          });
        }
        // CLOSED status is ignored when isUnsubscribing is true (intentional cleanup)
      });

    channelRef.current = channel;

    // Cleanup subscription on unmount or auth change
    return () => {
      console.log('[MaintenanceRealtime] Unsubscribing from channel');
      if (channelRef.current) {
        supabase.removeChannel(channelRef.current);
        channelRef.current = null;
      }
    };
  }, [authContext?.isAuthenticated, authContext?.user?.id, queryClient]);

  // Return nothing - this is a side-effect only hook
  return null;
};

export default useMaintenanceRealtime;
