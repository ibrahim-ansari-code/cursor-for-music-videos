/**
 * QuickActions Component
 * 
 * Provides quick action buttons for tenant profile management including:
 * - New Ticket (maintenance request)
 * - Upload Document
 * - Record Payment
 * - Send Message (coming soon)
 * - Invite to Portal (tenant portal invitation - coming soon)
 */
import React, { useState, useEffect } from 'react';
import { toast } from 'react-toastify';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import * as Sentry from '@sentry/react';
import { EnrichedTenant } from '../../../types/tenant';
import {
  InvitationResponse,
  InvitationStatus,
} from '../../../types/invitation';
import {
  createTenantInvitation,
  getTenantInvitation,
  resendTenantInvitation,
  revokeTenantInvitation,
  isInvitationValid,
  getInvitationExpiryText,
} from '../../../utils/api/tenantInvitations';
import { QUERY_KEYS } from '../../../hooks/queryKeys';

// Feature flag - set to true when ready to enable portal invitations
const PORTAL_INVITATIONS_ENABLED = false;

interface QuickActionsProps {
  tenant: EnrichedTenant;
  onNewTicket?: (initialData?: Record<string, unknown>) => void;
  onUploadDocument?: () => void;
  onRecordPayment?: () => void;
  onSendMessage?: () => void;
}

const QuickActions: React.FC<QuickActionsProps> = ({
  tenant,
  onNewTicket,
  onUploadDocument,
  onRecordPayment,
  onSendMessage,
}) => {
  const queryClient = useQueryClient();
  const [isInviting, setIsInviting] = useState(false);
  const [showInviteDropdown, setShowInviteDropdown] = useState(false);

  // Fetch invitation status for this tenant
  const {
    data: invitation,
    isLoading: isLoadingInvitation,
    refetch: refetchInvitation,
  } = useQuery<InvitationResponse | null>({
    queryKey: [...QUERY_KEYS.tenants.detail(tenant.id), 'invitation'],
    queryFn: () => getTenantInvitation(tenant.id),
    enabled: PORTAL_INVITATIONS_ENABLED && !!tenant.id && !tenant.user_id,
    staleTime: 60 * 1000, // 1 minute
  });

  // Determine portal status
  const hasPortalAccess = !!tenant.user_id;

  // Get active lease to extract property and unit info for new tickets
  const activeLease = tenant.leases?.find(lease => lease.status === 'ACTIVE');

  // Handle new ticket with pre-populated data
  const handleNewTicket = () => {
    if (!onNewTicket) return;

    // Build initial data for create mode with pre-selected values
    const propertyId = activeLease?.property_id || tenant.current_property_id;
    const unitId = activeLease?.unit_id || tenant.assigned_units?.[0]?.id || tenant.unit?.id;

    const initialData = {
      tenant_id: String(tenant.id),
      property_id: propertyId ? String(propertyId) : '',
      unit_id: unitId ? String(unitId) : '',
      priority: 'Medium',
      status: 'Pending',
    };

    onNewTicket(initialData);
  };

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      const target = event.target as HTMLElement;
      if (!target.closest('.invite-dropdown-container')) {
        setShowInviteDropdown(false);
      }
    };

    if (showInviteDropdown) {
      document.addEventListener('mousedown', handleClickOutside);
    }

    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [showInviteDropdown]);

  // Handle sending invitation
  const handleInvite = async () => {
    if (!tenant.email) {
      toast.error('Cannot invite tenant: No email address on file');
      return;
    }

    setIsInviting(true);
    setShowInviteDropdown(false);

    try {
      Sentry.startSpan(
        {
          op: 'api.call',
          name: 'Create Tenant Invitation',
        },
        async () => {
          const result = await createTenantInvitation(tenant.id);
          
          if (result) {
            toast.success(`Invitation sent to ${tenant.email}`);
            await refetchInvitation();
            queryClient.invalidateQueries({
              queryKey: QUERY_KEYS.tenants.detail(tenant.id),
            });
          }
        }
      );
    } catch (error: unknown) {
      console.error('Failed to send invitation:', error);
      
      Sentry.captureException(error, {
        tags: {
          component: 'QuickActions',
          action: 'invite_tenant',
        },
        contexts: {
          tenant: { id: tenant.id, email: tenant.email },
        },
      });

      const errorMessage = error instanceof Error ? error.message : 'Failed to send invitation';
      toast.error(errorMessage);
    } finally {
      setIsInviting(false);
    }
  };

  // Handle resending invitation
  const handleResend = async () => {
    if (!invitation) return;

    setIsInviting(true);
    setShowInviteDropdown(false);

    try {
      const result = await resendTenantInvitation(invitation.id);
      
      if (result.success) {
        toast.success('Invitation resent successfully');
        await refetchInvitation();
      } else {
        toast.error(result.message || 'Failed to resend invitation');
      }
    } catch (error: unknown) {
      console.error('Failed to resend invitation:', error);
      
      Sentry.captureException(error, {
        tags: {
          component: 'QuickActions',
          action: 'resend_invitation',
        },
      });

      toast.error('Failed to resend invitation');
    } finally {
      setIsInviting(false);
    }
  };

  // Handle revoking invitation
  const handleRevoke = async () => {
    if (!invitation) return;

    setIsInviting(true);
    setShowInviteDropdown(false);

    try {
      const result = await revokeTenantInvitation(invitation.id);
      
      if (result.success) {
        toast.success('Invitation revoked');
        await refetchInvitation();
      } else {
        toast.error(result.message || 'Failed to revoke invitation');
      }
    } catch (error: unknown) {
      console.error('Failed to revoke invitation:', error);
      
      Sentry.captureException(error, {
        tags: {
          component: 'QuickActions',
          action: 'revoke_invitation',
        },
      });

      toast.error('Failed to revoke invitation');
    } finally {
      setIsInviting(false);
    }
  };

  // Render portal invite button based on status
  const renderPortalButton = () => {
    // Feature flagged - show Coming Soon state
    if (!PORTAL_INVITATIONS_ENABLED) {
      return (
        <button
          disabled
          className="flex items-center gap-3 px-3 py-2.5 rounded-lg transition-colors text-left w-full opacity-50 cursor-not-allowed"
        >
          <svg className="w-4 h-4 text-gray-400 dark:text-gray-500 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
          </svg>
          <span className="text-sm font-medium text-gray-400 dark:text-gray-500">Invite to Portal</span>
          {/* Coming Soon flag */}
          <span className="ml-auto inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-medium bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-400">
            <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            Soon
          </span>
        </button>
      );
    }

    // Loading state
    if (isLoadingInvitation && !hasPortalAccess) {
      return (
        <button
          disabled
          className="flex items-center gap-3 px-3 py-2.5 rounded-lg text-left w-full opacity-50"
        >
          <svg className="w-4 h-4 text-gray-400 flex-shrink-0 animate-spin" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
          </svg>
          <span className="text-sm font-medium text-gray-400">Loading...</span>
        </button>
      );
    }

    // Tenant has portal access
    if (hasPortalAccess) {
      return (
        <div className="flex items-center gap-3 px-3 py-2.5 rounded-lg w-full">
          <svg className="w-4 h-4 text-green-500 dark:text-green-400 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <span className="text-sm font-medium text-green-600 dark:text-green-400">Portal Active</span>
        </div>
      );
    }

    // No email on file
    if (!tenant.email) {
      return (
        <button
          disabled
          className="flex items-center gap-3 px-3 py-2.5 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors text-left w-full opacity-50 cursor-not-allowed relative group"
        >
          <svg className="w-4 h-4 text-gray-400 dark:text-gray-500 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
          </svg>
          <span className="text-sm font-medium text-gray-400 dark:text-gray-500">Invite to Portal</span>
          <span className="absolute left-full ml-2 top-1/2 -translate-y-1/2 px-2 py-1 bg-gray-900 text-white text-xs rounded opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap pointer-events-none z-50">
            Add email first
          </span>
        </button>
      );
    }

    // Has pending invitation
    if (invitation && invitation.status === InvitationStatus.PENDING && isInvitationValid(invitation)) {
      return (
        <div className="relative invite-dropdown-container">
          <button
            onClick={() => setShowInviteDropdown(!showInviteDropdown)}
            disabled={isInviting}
            className="flex items-center justify-between gap-3 px-3 py-2.5 rounded-lg hover:bg-yellow-50 dark:hover:bg-yellow-900/20 transition-colors text-left w-full"
          >
            <div className="flex items-center gap-3">
              <svg className="w-4 h-4 text-yellow-500 dark:text-yellow-400 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <div className="flex flex-col">
                <span className="text-sm font-medium text-yellow-600 dark:text-yellow-400">Invited</span>
                <span className="text-xs text-gray-500 dark:text-gray-400">{getInvitationExpiryText(invitation)}</span>
              </div>
            </div>
            <svg className={`w-4 h-4 text-gray-400 transition-transform ${showInviteDropdown ? 'rotate-180' : ''}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
            </svg>
          </button>

          {/* Dropdown menu */}
          {showInviteDropdown && (
            <div className="absolute right-0 mt-1 w-48 bg-white dark:bg-gray-800 rounded-lg shadow-lg border border-gray-200 dark:border-gray-700 z-20 py-1">
              <button
                onClick={handleResend}
                disabled={isInviting}
                className="w-full text-left px-4 py-2 text-sm text-gray-700 dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-700 flex items-center gap-2"
              >
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                </svg>
                Resend Invite
              </button>
              <button
                onClick={handleRevoke}
                disabled={isInviting}
                className="w-full text-left px-4 py-2 text-sm text-red-600 dark:text-red-400 hover:bg-gray-100 dark:hover:bg-gray-700 flex items-center gap-2"
              >
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
                Revoke Invite
              </button>
            </div>
          )}
        </div>
      );
    }

    // Expired or revoked invitation, or no invitation
    return (
      <button
        onClick={handleInvite}
        disabled={isInviting}
        className="flex items-center gap-3 px-3 py-2.5 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors text-left w-full disabled:opacity-50"
      >
        {isInviting ? (
          <svg className="w-4 h-4 text-gray-500 dark:text-gray-400 flex-shrink-0 animate-spin" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
          </svg>
        ) : (
          <svg className="w-4 h-4 text-gray-500 dark:text-gray-400 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
          </svg>
        )}
        <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
          {isInviting ? 'Sending...' : 'Invite to Portal'}
        </span>
      </button>
    );
  };

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-5">
      <h3 className="text-sm font-semibold text-gray-900 dark:text-gray-100 mb-4">Quick Actions</h3>
      <div className="space-y-1">
        {/* New Ticket */}
        <button
          onClick={handleNewTicket}
          className="flex items-center gap-3 px-3 py-2.5 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors text-left w-full"
        >
          <svg className="w-4 h-4 text-gray-500 dark:text-gray-400 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
          </svg>
          <span className="text-sm font-medium text-gray-700 dark:text-gray-300">New Ticket</span>
        </button>

        {/* Upload Document */}
        <button
          onClick={onUploadDocument}
          className="flex items-center gap-3 px-3 py-2.5 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors text-left w-full"
        >
          <svg className="w-4 h-4 text-gray-500 dark:text-gray-400 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
          </svg>
          <span className="text-sm font-medium text-gray-700 dark:text-gray-300">Upload Doc</span>
        </button>

        {/* Record Payment */}
        <button
          onClick={onRecordPayment}
          className="flex items-center gap-3 px-3 py-2.5 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors text-left w-full"
        >
          <svg className="w-4 h-4 text-gray-500 dark:text-gray-400 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <span className="text-sm font-medium text-gray-700 dark:text-gray-300">Record Payment</span>
        </button>

        {/* Send Message - Coming Soon */}
        <button
          onClick={onSendMessage}
          disabled
          className="flex items-center gap-3 px-3 py-2.5 rounded-lg transition-colors text-left w-full opacity-50 cursor-not-allowed"
        >
          <svg className="w-4 h-4 text-gray-400 dark:text-gray-500 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
          </svg>
          <span className="text-sm font-medium text-gray-400 dark:text-gray-500">Send Message</span>
          {/* Coming Soon flag */}
          <span className="ml-auto inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-medium bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-400">
            <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            Soon
          </span>
        </button>

        {/* Invite to Portal - Dynamic based on status */}
        {renderPortalButton()}
      </div>
    </div>
  );
};

export default QuickActions;
