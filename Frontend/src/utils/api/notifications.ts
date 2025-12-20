/**
 * Notification API Utility Functions
 * 
 * Provides API calls for notification management and user preferences.
 */
import { apiRequest } from './core';

// Helper to create axios-like API wrapper
const createApiWrapper = () => ({
  get: async <T>(url: string, config?: { params?: Record<string, any> }): Promise<{ data: T }> => {
    const queryString = config?.params 
      ? '?' + new URLSearchParams(Object.entries(config.params).map(([k, v]) => [k, String(v)])).toString()
      : '';
    const data = await apiRequest(url + queryString, { method: 'GET' });
    return { data: data as T };
  },
  post: async <T>(url: string, data?: any): Promise<{ data: T }> => {
    const response = await apiRequest(url, {
      method: 'POST',
      body: data ? JSON.stringify(data) : undefined,
    });
    return { data: response as T };
  },
  put: async <T>(url: string, data?: any): Promise<{ data: T }> => {
    const response = await apiRequest(url, {
      method: 'PUT',
      body: data ? JSON.stringify(data) : undefined,
    });
    return { data: response as T };
  },
  patch: async <T>(url: string, data?: any): Promise<{ data: T }> => {
    const response = await apiRequest(url, {
      method: 'PATCH',
      body: data ? JSON.stringify(data) : undefined,
    });
    return { data: response as T };
  },
  delete: async <T = void>(url: string): Promise<{ data: T }> => {
    const response = await apiRequest(url, { method: 'DELETE' });
    return { data: response as T };
  },
});

const api = createApiWrapper();

// ========================================================================
// TYPE DEFINITIONS
// ========================================================================

export interface NotificationMetadata {
  property_id?: number;
  tenant_id?: number;
  unit_id?: number;
  amount?: number;
  lease_id?: number;
  maintenance_id?: number;
  payment_id?: number;
  invoice_id?: number;
  [key: string]: any;
}

export interface Notification {
  id: string;
  user_id: string;
  type: NotificationType;
  title: string;
  message: string;
  link?: string | null;
  actor_id?: string | null;
  actor_name?: string | null;
  actor_avatar_url?: string | null;
  is_read: boolean;
  is_archived: boolean;
  read_at?: string | null;
  priority: NotificationPriority;
  delivery_channels: string[];
  metadata_: NotificationMetadata;
  group_key?: string | null;
  created_at: string;
  expires_at?: string | null;
}

export type NotificationType =
  | 'rent_reminder'
  | 'payment_received'
  | 'lease_expiring'
  | 'maintenance_update'

  | 'maintenance_request_new'
  | 'new_application'
  | 'system_update';

export type NotificationPriority = 'urgent' | 'high' | 'normal' | 'low';

export type NotificationChannel = 'in_app' | 'email' | 'sms';

export type DigestFrequency = 'immediate' | 'hourly' | 'daily' | 'weekly' | 'never';

export interface NotificationTypePreference {
  enabled: boolean;
  channels: NotificationChannel[];
  frequency: string;
}

export interface NotificationPreferences {
  [type: string]: NotificationTypePreference;
}

export interface NotificationPreferenceData {
  id: string;
  user_id: string;
  enabled: boolean;
  preferences: NotificationPreferences;
  email_digest_frequency: DigestFrequency;
  email_digest_time: string;
  timezone: string;
  quiet_hours_enabled: boolean;
  quiet_hours_start?: string | null;
  quiet_hours_end?: string | null;
  created_at: string;
  updated_at: string;
}

export interface NotificationListParams {
  limit?: number;
  offset?: number;
  is_read?: boolean;
  type?: NotificationType;
  priority?: NotificationPriority;
}

export interface NotificationListResponse {
  notifications: Notification[];
  total: number;
  unread_count: number;
  limit: number;
  offset: number;
}

export interface UnreadCountResponse {
  unread_count: number;
}

export interface MarkAsReadResponse {
  success: boolean;
  marked_count: number;
  message: string;
}

export interface NotificationPreferenceUpdateRequest {
  enabled?: boolean;
  preferences?: NotificationPreferences;
  email_digest_frequency?: DigestFrequency;
  email_digest_time?: string;
  timezone?: string;
  quiet_hours_enabled?: boolean;
  quiet_hours_start?: string;
  quiet_hours_end?: string;
}

export interface NotificationPreferenceUpdateResponse {
  success: boolean;
  message: string;
  preferences: NotificationPreferenceData;
}

export interface TestNotificationResponse {
  success: boolean;
  message: string;
  notification_id: string;
}

export interface TestEmailResponse {
  success: boolean;
  message: string;
  email_sent_to: string;
}

// ========================================================================
// API FUNCTIONS
// ========================================================================

const notificationApi = {
  /**
   * Get paginated list of notifications for the current user
   */
  getNotifications: async (
    params: NotificationListParams = {}
  ): Promise<NotificationListResponse> => {
    const response = await api.get<NotificationListResponse>('/notifications', { params });
    return response.data;
  },

  /**
   * Get count of unread notifications
   */
  getUnreadCount: async (): Promise<UnreadCountResponse> => {
    const response = await api.get<UnreadCountResponse>('/notifications/unread-count');
    return response.data;
  },

  /**
   * Mark one or more notifications as read
   */
  markAsRead: async (notificationIds: string | string[]): Promise<MarkAsReadResponse> => {
    const ids = Array.isArray(notificationIds) ? notificationIds : [notificationIds];
    
    // Single notification: use PATCH /{id}/read endpoint
    if (ids.length === 1) {
      const response = await api.patch<MarkAsReadResponse>(`/notifications/${ids[0]}/read`);
      return response.data;
    }
    
    // Multiple notifications: call individual endpoints (batch endpoint not implemented)
    let totalMarked = 0;
    for (const id of ids) {
      try {
        const response = await api.patch<MarkAsReadResponse>(`/notifications/${id}/read`);
        totalMarked += response.data.marked_count;
      } catch (error) {
        console.error(`Failed to mark notification ${id} as read:`, error);
      }
    }
    
    return {
      success: true,
      marked_count: totalMarked,
      message: `Marked ${totalMarked} notification(s) as read`
    };
  },

  /**
   * Mark all notifications as read
   */
  markAllAsRead: async (): Promise<MarkAsReadResponse> => {
    const response = await api.patch<MarkAsReadResponse>('/notifications/mark-all-read');
    return response.data;
  },

  /**
   * Delete (archive) a notification
   */
  deleteNotification: async (notificationId: string): Promise<void> => {
    await api.delete(`/notifications/${notificationId}`);
  },

  /**
   * Get notification preferences for the current user
   */
  getPreferences: async (): Promise<NotificationPreferenceData> => {
    const response = await api.get<NotificationPreferenceData>('/notifications/preferences');
    return response.data;
  },

  /**
   * Update notification preferences
   */
  updatePreferences: async (
    preferences: NotificationPreferenceUpdateRequest
  ): Promise<NotificationPreferenceUpdateResponse> => {
    const response = await api.put<NotificationPreferenceUpdateResponse>(
      '/notifications/preferences',
      preferences
    );
    return response.data;
  },

  /**
   * Send a test in-app notification
   */
  sendTestNotification: async (notificationType: NotificationType = 'system_update'): Promise<TestNotificationResponse> => {
    const response = await api.post<TestNotificationResponse>('/notifications/test-notification', {
      notification_type: notificationType,
    });
    return response.data;
  },

  /**
   * Send a test email notification
   */
  sendTestEmail: async (notificationType: NotificationType = 'system_update'): Promise<TestEmailResponse> => {
    const response = await api.post<TestEmailResponse>('/notifications/test-email', {
      notification_type: notificationType,
    });
    return response.data;
  },
};

export default notificationApi;

// Named exports for convenience
export const getNotifications = notificationApi.getNotifications;
export const getUnreadCount = notificationApi.getUnreadCount;
export const markAsRead = notificationApi.markAsRead;
export const markAllAsRead = notificationApi.markAllAsRead;
export const dismissNotification = notificationApi.deleteNotification;
export const getPreferences = notificationApi.getPreferences;
export const updatePreferences = notificationApi.updatePreferences;
export const sendTestNotification = notificationApi.sendTestNotification;
export const sendTestEmail = notificationApi.sendTestEmail;

// Type aliases for backwards compatibility
export type NotificationPreferenceResponse = NotificationPreferenceData;
export type NotificationCategoryPreference = NotificationTypePreference;

