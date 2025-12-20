/**
 * Notification API Functions
 * 
 * API client for notification management - mirrors landlord portal implementation
 */

import { apiRequest } from './core';

// ========================================================================
// TYPE DEFINITIONS
// ========================================================================

export interface Notification {
  id: string;
  user_id: string;
  type: string;
  title: string;
  message: string;
  link: string | null;
  actor_id: string | null;
  actor_name: string | null;
  actor_avatar_url: string | null;
  metadata_: Record<string, unknown>;
  is_read: boolean;
  is_archived: boolean;
  read_at: string | null;
  priority: string;
  delivery_channels: string[];
  group_key: string | null;
  created_at: string;
  expires_at: string | null;
}

export interface NotificationListParams {
  limit?: number;
  offset?: number;
  is_read?: boolean;
  is_archived?: boolean;
  type?: string;
  priority?: string;
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

// ========================================================================
// API FUNCTIONS
// ========================================================================

/**
 * Get paginated list of notifications for the current user
 */
export const getNotifications = async (
  params: NotificationListParams = {}
): Promise<NotificationListResponse> => {
  const queryParams = new URLSearchParams();
  
  if (params.limit !== undefined) queryParams.append('limit', params.limit.toString());
  if (params.offset !== undefined) queryParams.append('offset', params.offset.toString());
  if (params.is_read !== undefined) queryParams.append('is_read', params.is_read.toString());
  if (params.is_archived !== undefined) queryParams.append('is_archived', params.is_archived.toString());
  if (params.type) queryParams.append('type', params.type);
  if (params.priority) queryParams.append('priority', params.priority);
  
  const queryString = queryParams.toString();
  const endpoint = `/notifications${queryString ? `?${queryString}` : ''}`;
  
  const response = await apiRequest<NotificationListResponse>(endpoint, {
    method: 'GET'
  });
  
  if (!response) {
    throw new Error('Failed to fetch notifications');
  }
  
  return response;
};

/**
 * Get count of unread notifications
 */
export const getUnreadCount = async (): Promise<UnreadCountResponse> => {
  const response = await apiRequest<UnreadCountResponse>('/notifications/unread-count', {
    method: 'GET'
  });
  
  if (!response) {
    throw new Error('Failed to fetch unread count');
  }
  
  return response;
};

/**
 * Mark one or more notifications as read
 */
export const markAsRead = async (notificationIds: string | string[]): Promise<MarkAsReadResponse> => {
  const ids = Array.isArray(notificationIds) ? notificationIds : [notificationIds];
  
  // Single notification: use PATCH /{id}/read endpoint
  if (ids.length === 1) {
    const response = await apiRequest<MarkAsReadResponse>(`/notifications/${ids[0]}/read`, {
      method: 'PATCH'
    });
    
    if (!response) {
      throw new Error('Failed to mark notification as read');
    }
    
    return response;
  }
  
  // Multiple notifications: call individual endpoints
  let totalMarked = 0;
  for (const id of ids) {
    try {
      const response = await apiRequest<MarkAsReadResponse>(`/notifications/${id}/read`, {
        method: 'PATCH'
      });
      
      if (response) {
        totalMarked += response.marked_count;
      }
    } catch (error) {
      console.error(`Failed to mark notification ${id} as read:`, error);
    }
  }
  
  return {
    success: true,
    marked_count: totalMarked,
    message: `Marked ${totalMarked} notification(s) as read`
  };
};

/**
 * Mark all notifications as read
 */
export const markAllAsRead = async (): Promise<MarkAsReadResponse> => {
  const response = await apiRequest<MarkAsReadResponse>('/notifications/mark-all-read', {
    method: 'PATCH'
  });
  
  if (!response) {
    throw new Error('Failed to mark all notifications as read');
  }
  
  return response;
};

/**
 * Delete (archive) a notification
 */
export const dismissNotification = async (notificationId: string): Promise<void> => {
  await apiRequest<void>(`/notifications/${notificationId}`, {
    method: 'DELETE'
  });
};

