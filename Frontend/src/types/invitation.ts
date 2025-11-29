/**
 * Tenant Portal Invitation Types
 * 
 * TypeScript types matching the backend schemas for tenant portal invitations.
 * These types are used for the landlord-to-tenant invitation flow.
 */

/**
 * Status of a tenant portal invitation
 * Matches backend InvitationStatus enum
 */
export enum InvitationStatus {
  PENDING = 'pending',
  ACCEPTED = 'accepted',
  EXPIRED = 'expired',
  REVOKED = 'revoked',
}

/**
 * Request to create a new tenant portal invitation
 * Matches backend InvitationCreateRequest schema
 */
export interface InvitationCreateRequest {
  tenant_id: number;
}

/**
 * Response for a tenant portal invitation
 * Matches backend InvitationResponse schema
 */
export interface InvitationResponse {
  id: string; // UUID
  tenant_id: number;
  invited_by: string; // UUID
  email: string;
  status: InvitationStatus;
  created_at: string; // ISO datetime
  expires_at: string; // ISO datetime
  accepted_at: string | null;
  revoked_at: string | null;
  
  // Nested tenant info
  tenant_name: string | null;
  tenant_email: string | null;
}

/**
 * Response for listing invitations
 * Matches backend InvitationListResponse schema
 */
export interface InvitationListResponse {
  invitations: InvitationResponse[];
  total: number;
}

/**
 * Response after revoking an invitation
 * Matches backend InvitationRevokeResponse schema
 */
export interface InvitationRevokeResponse {
  success: boolean;
  message: string;
}

/**
 * Response after resending an invitation
 * Matches backend InvitationResendResponse schema
 */
export interface InvitationResendResponse {
  success: boolean;
  message: string;
  new_expires_at: string | null; // ISO datetime
}

/**
 * Request to validate an invitation token
 * Matches backend InvitationValidateRequest schema
 */
export interface InvitationValidateRequest {
  token: string;
}

/**
 * Response for invitation token validation
 * Matches backend InvitationValidateResponse schema
 */
export interface InvitationValidateResponse {
  valid: boolean;
  email: string | null;
  tenant_name: string | null;
  landlord_name: string | null;
  property_name: string | null;
  unit_name: string | null;
  expires_at: string | null; // ISO datetime
  message: string | null;
}

/**
 * Request to accept an invitation
 * Matches backend InvitationAcceptRequest schema
 */
export interface InvitationAcceptRequest {
  token: string;
}

/**
 * Response after accepting an invitation
 * Matches backend InvitationAcceptResponse schema
 */
export interface InvitationAcceptResponse {
  success: boolean;
  message: string;
  tenant_id: number | null;
}

/**
 * Portal access status response
 * From GET /api/tenant-invitations/status
 */
export interface PortalStatusResponse {
  // For tenant users
  has_portal_access?: boolean;
  tenant_id?: number | null;
  landlord_id?: string | null;
  property_name?: string | null;
  
  // For landlord users
  user_type?: 'landlord';
  tenants_with_portal_access?: number;
}

/**
 * Portal status for display in UI
 * Computed from tenant data and invitation state
 */
export type TenantPortalStatus = 
  | 'active'      // tenant.user_id is set - has portal access
  | 'invited'     // pending invitation exists
  | 'not_invited' // no user_id and no pending invitation
  | 'expired'     // invitation expired
  | 'revoked';    // invitation was revoked

/**
 * Helper to determine tenant portal status display info
 */
export interface PortalStatusDisplay {
  status: TenantPortalStatus;
  label: string;
  color: 'green' | 'yellow' | 'gray' | 'red' | 'blue';
  bgClass: string;
  textClass: string;
}

/**
 * Get portal status display configuration
 */
export function getPortalStatusDisplay(
  hasUserLink: boolean,
  pendingInvitation: InvitationResponse | null
): PortalStatusDisplay {
  if (hasUserLink) {
    return {
      status: 'active',
      label: 'Active',
      color: 'green',
      bgClass: 'bg-green-100 dark:bg-green-900/30',
      textClass: 'text-green-700 dark:text-green-300',
    };
  }
  
  if (pendingInvitation) {
    if (pendingInvitation.status === InvitationStatus.PENDING) {
      // Check if expired
      const expiresAt = new Date(pendingInvitation.expires_at);
      if (expiresAt <= new Date()) {
        return {
          status: 'expired',
          label: 'Expired',
          color: 'red',
          bgClass: 'bg-red-100 dark:bg-red-900/30',
          textClass: 'text-red-700 dark:text-red-300',
        };
      }
      return {
        status: 'invited',
        label: 'Invited',
        color: 'yellow',
        bgClass: 'bg-yellow-100 dark:bg-yellow-900/30',
        textClass: 'text-yellow-700 dark:text-yellow-300',
      };
    }
    if (pendingInvitation.status === InvitationStatus.REVOKED) {
      return {
        status: 'revoked',
        label: 'Revoked',
        color: 'red',
        bgClass: 'bg-red-100 dark:bg-red-900/30',
        textClass: 'text-red-700 dark:text-red-300',
      };
    }
    if (pendingInvitation.status === InvitationStatus.EXPIRED) {
      return {
        status: 'expired',
        label: 'Expired',
        color: 'red',
        bgClass: 'bg-red-100 dark:bg-red-900/30',
        textClass: 'text-red-700 dark:text-red-300',
      };
    }
  }
  
  return {
    status: 'not_invited',
    label: 'Not Invited',
    color: 'gray',
    bgClass: 'bg-gray-100 dark:bg-gray-700',
    textClass: 'text-gray-600 dark:text-gray-400',
  };
}

