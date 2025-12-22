/**
 * Settings API Utilities
 *
 * API calls for tenant profile and preferences management.
 */

import { apiRequest } from './core';
import type { User } from '@/types';

// =============================================================================
// Types
// =============================================================================

export interface ProfileUpdateRequest {
  first_name?: string | null;
  last_name?: string | null;
  phone?: string | null;
}

export interface PasswordChangeRequest {
  current_password: string;
  new_password: string;
}

export interface PasswordChangeResponse {
  message: string;
}

// =============================================================================
// Notification Preferences Types
// =============================================================================

export interface NotificationTypePreference {
  enabled: boolean;
  channels: ('in_app' | 'email' | 'sms')[];
  frequency: 'immediate' | 'hourly' | 'daily' | 'weekly' | 'never';
}

export interface NotificationPreferences {
  id: string;
  user_id: string;
  enabled: boolean;
  preferences: {
    rent_reminder?: NotificationTypePreference;
    payment_received?: NotificationTypePreference;
    lease_expiring?: NotificationTypePreference;
    maintenance_update?: NotificationTypePreference;
    new_application?: NotificationTypePreference;
    system_update?: NotificationTypePreference;
  };
  email_digest_frequency: 'immediate' | 'hourly' | 'daily' | 'weekly' | 'never';
  email_digest_time: string;
  timezone: string;
  quiet_hours_enabled: boolean;
  quiet_hours_start: string | null;
  quiet_hours_end: string | null;
  created_at: string;
  updated_at: string;
}

export interface NotificationPreferencesUpdateRequest {
  enabled?: boolean;
  preferences?: {
    [key: string]: {
      enabled?: boolean;
      channels?: ('in_app' | 'email' | 'sms')[];
      frequency?: 'immediate' | 'hourly' | 'daily' | 'weekly' | 'never';
    };
  };
  email_digest_frequency?: 'immediate' | 'hourly' | 'daily' | 'weekly' | 'never';
}

export interface NotificationPreferencesUpdateResponse {
  success: boolean;
  message: string;
  preferences: NotificationPreferences;
}

// =============================================================================
// Profile API
// =============================================================================

/**
 * Update the current user's profile.
 */
export async function updateProfile(userId: string, data: ProfileUpdateRequest): Promise<User> {
  const result = await apiRequest<User>(`/auth/users/${userId}/profile`, {
    method: 'PUT',
    body: JSON.stringify(data),
  });

  if (!result) {
    throw new Error('Failed to update profile');
  }

  return result;
}

/**
 * Change the current user's password.
 * This uses Supabase Auth, so we'll handle it client-side.
 */
export async function changePassword(data: PasswordChangeRequest): Promise<PasswordChangeResponse> {
  const result = await apiRequest<PasswordChangeResponse>('/auth/change-password', {
    method: 'POST',
    body: JSON.stringify(data),
  });

  if (!result) {
    throw new Error('Failed to change password');
  }

  return result;
}

// =============================================================================
// Notification Preferences API
// =============================================================================

/**
 * Get the current user's notification preferences.
 */
export async function getNotificationPreferences(): Promise<NotificationPreferences> {
  const result = await apiRequest<NotificationPreferences>('/notifications/preferences', {
    method: 'GET',
  });

  if (!result) {
    throw new Error('Failed to fetch notification preferences');
  }

  return result;
}

/**
 * Update the current user's notification preferences.
 */
export async function updateNotificationPreferences(
  data: NotificationPreferencesUpdateRequest
): Promise<NotificationPreferencesUpdateResponse> {
  const result = await apiRequest<NotificationPreferencesUpdateResponse>('/notifications/preferences', {
    method: 'PUT',
    body: JSON.stringify(data),
  });

  if (!result) {
    throw new Error('Failed to update notification preferences');
  }

  return result;
}
