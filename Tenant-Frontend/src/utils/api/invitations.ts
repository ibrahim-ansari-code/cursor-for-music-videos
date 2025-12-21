/**
 * Invitation API Utils for Tenant Portal
 * 
 * Handles invitation validation and acceptance for the tenant portal.
 * These are the tenant-facing endpoints.
 */
import { supabase } from '@/utils/supabaseClient';

// Types for invitation API responses
export interface InvitationValidateResponse {
  valid: boolean;
  email: string | null;
  tenant_name: string | null;
  landlord_name: string | null;
  property_name: string | null;
  unit_name: string | null;
  expires_at: string | null;
  message: string | null;
}

export interface InvitationAcceptResponse {
  success: boolean;
  message: string;
  tenant_id: number | null;
}

export interface RegisterAndAcceptResponse {
  success: boolean;
  message: string;
  tenant_id: number | null;
  user_id: string | null;
  access_token: string | null;
  refresh_token: string | null;
}

// Sanitize the base URL
const API_BASE_URL = (
  import.meta.env.VITE_API_URL || 
  (import.meta.env.MODE === 'test' ? 'http://localhost:8000' : '')
).replace(/\/+$/, '');

/**
 * Validates an invitation token.
 * This is a PUBLIC endpoint - no authentication required.
 * Called when tenant visits /accept-invite?token=xxx
 * 
 * @param token - The invitation token from the URL
 * @returns Invitation validation response with tenant/landlord/property info
 */
export const validateInvitationToken = async (
  token: string
): Promise<InvitationValidateResponse> => {
  const response = await fetch(
    `${API_BASE_URL}/api/tenant-invitations/validate-invite?token=${encodeURIComponent(token)}`,
    {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    }
  );

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || 'Failed to validate invitation');
  }

  return response.json();
};

/**
 * Accepts an invitation and links the tenant record to the current user.
 * Requires authentication - user must be logged in.
 * Uses Supabase session management for secure token handling.
 *
 * @param token - The invitation token
 * @returns Accept response with success status
 */
export const acceptInvitation = async (
  token: string
): Promise<InvitationAcceptResponse> => {
  // Get session from Supabase - more secure than reading localStorage directly
  const { data: { session }, error: sessionError } = await supabase.auth.getSession();

  if (sessionError || !session) {
    throw new Error('Authentication required. Please log in first.');
  }

  const response = await fetch(
    `${API_BASE_URL}/api/tenant-invitations/accept-invite`,
    {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${session.access_token}`,
      },
      body: JSON.stringify({ token }),
    }
  );

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || 'Failed to accept invitation');
  }

  return response.json();
};

/**
 * Registers a new user and accepts the invitation in one step.
 * This is a PUBLIC endpoint - no authentication required.
 *
 * This streamlined flow skips email verification because clicking
 * the invitation link already proves email ownership (industry standard
 * pattern used by Slack, Notion, Discourse, etc.).
 *
 * @param token - The invitation token from the email link
 * @param password - User's chosen password
 * @param firstName - User's first name
 * @param lastName - User's last name
 * @returns Response with session tokens for auto-sign-in
 */
export const registerAndAcceptInvitation = async (
  token: string,
  password: string,
  firstName: string,
  lastName: string
): Promise<RegisterAndAcceptResponse> => {
  const response = await fetch(
    `${API_BASE_URL}/api/tenant-invitations/register-and-accept`,
    {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ token, password, first_name: firstName, last_name: lastName }),
    }
  );

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || 'Failed to create account');
  }

  return response.json();
};

// =============================================================================
// DEPRECATED: The following functions are no longer used in the streamlined flow.
// Email verification is skipped because clicking the invitation link proves ownership.
// Kept for reference in case needed for edge cases or future features.
// =============================================================================

// export const sendTenantVerificationEmail = async (token: string, email: string) => { ... }
// export const verifyMagicLink = async (magicToken: string) => { ... }
// export const verifyTenantEmail = async (token: string, email: string) => { ... }
