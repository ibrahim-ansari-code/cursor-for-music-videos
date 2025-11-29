/**
 * Tenant Invitations API Functions
 * 
 * API utilities for managing tenant portal invitations.
 * Used by landlords to invite tenants to the Tenant Portal.
 */
import { apiRequest, formatQueryString } from './core';
import {
  InvitationResponse,
  InvitationListResponse,
  InvitationRevokeResponse,
  InvitationResendResponse,
  InvitationStatus,
} from '../../types/invitation';

// ============================================================================
// LANDLORD ENDPOINTS (used by app.brikli.com)
// ============================================================================

/**
 * Create and send a tenant portal invitation
 * 
 * @param tenantId - ID of the tenant to invite
 * @returns Created invitation response
 * @throws Error if tenant doesn't exist, has no email, or already has portal access
 */
export const createTenantInvitation = async (
  tenantId: number
): Promise<InvitationResponse> => {
  return apiRequest('/tenant-invitations/invitations', {
    method: 'POST',
    body: JSON.stringify({ tenant_id: tenantId }),
  });
};

/**
 * List all tenant invitations for the current landlord
 * 
 * @param statusFilter - Optional filter by invitation status
 * @returns List of invitations with total count
 */
export const listTenantInvitations = async (
  statusFilter?: InvitationStatus
): Promise<InvitationListResponse> => {
  const queryParams = new URLSearchParams();
  if (statusFilter) {
    queryParams.append('status_filter', statusFilter);
  }
  const queryString = queryParams.toString();
  return apiRequest(`/tenant-invitations/invitations${formatQueryString(queryString)}`);
};

/**
 * Get invitation status for a specific tenant
 * 
 * Uses a dedicated backend endpoint for efficient single-tenant lookup
 * instead of fetching all invitations and filtering client-side.
 * 
 * @param tenantId - ID of the tenant to check
 * @returns The most recent invitation for this tenant, or null if none exists
 */
export const getTenantInvitation = async (
  tenantId: number
): Promise<InvitationResponse | null> => {
  try {
    // Use dedicated endpoint for efficient single-tenant lookup
    return await apiRequest(`/tenant-invitations/invitations/tenant/${tenantId}`);
  } catch (error) {
    // 404 means no invitation exists - this is expected, not an error
    if (error instanceof Error && error.message.includes('Not Found')) {
      return null;
    }
    console.error('Error fetching tenant invitation:', error);
    return null;
  }
};

/**
 * Revoke a pending invitation
 * 
 * @param invitationId - UUID of the invitation to revoke
 * @returns Revoke response with success status and message
 */
export const revokeTenantInvitation = async (
  invitationId: string
): Promise<InvitationRevokeResponse> => {
  return apiRequest(`/tenant-invitations/invitations/${invitationId}`, {
    method: 'DELETE',
  });
};

/**
 * Resend an invitation email and extend expiry
 * 
 * @param invitationId - UUID of the invitation to resend
 * @returns Resend response with new expiry date
 */
export const resendTenantInvitation = async (
  invitationId: string
): Promise<InvitationResendResponse> => {
  return apiRequest(`/tenant-invitations/invitations/${invitationId}/resend`, {
    method: 'POST',
  });
};

// ============================================================================
// HELPER FUNCTIONS
// ============================================================================

/**
 * Check if an invitation is still valid (pending and not expired)
 */
export const isInvitationValid = (invitation: InvitationResponse): boolean => {
  if (invitation.status !== InvitationStatus.PENDING) {
    return false;
  }
  const expiresAt = new Date(invitation.expires_at);
  return expiresAt > new Date();
};

/**
 * Get human-readable time until invitation expires
 */
export const getInvitationExpiryText = (invitation: InvitationResponse): string => {
  const expiresAt = new Date(invitation.expires_at);
  const now = new Date();
  
  if (expiresAt <= now) {
    return 'Expired';
  }
  
  const diffMs = expiresAt.getTime() - now.getTime();
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));
  const diffHours = Math.floor((diffMs % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
  
  if (diffDays > 0) {
    return `Expires in ${diffDays} day${diffDays !== 1 ? 's' : ''}`;
  }
  if (diffHours > 0) {
    return `Expires in ${diffHours} hour${diffHours !== 1 ? 's' : ''}`;
  }
  return 'Expires soon';
};

