/**
 * Calendar API Client
 * 
 * Handles all API calls for the calendar feature including:
 * - Fetching unified calendar events
 * - Creating/updating/deleting custom reminders
 */

import { apiRequest, formatQueryString } from './core';

// ============================================================================
// TYPES
// ============================================================================

export interface CalendarFilters {
  from_date: string;
  to_date: string;
  property_id?: number;
  unit_id?: number;
  tenant_id?: number;
  event_type?: CalendarEventType;
  status?: CalendarEventStatus;
}

export enum CalendarEventType {
  INVOICE_DUE = 'invoice_due',
  LEASE_START = 'lease_start',
  LEASE_EXPIRING = 'lease_expiring',
  MAINTENANCE_SCHEDULED = 'maintenance_scheduled',
  INSURANCE_EXPIRY = 'insurance_expiry',
  MORTGAGE_RENEWAL = 'mortgage_renewal',
  CUSTOM_REMINDER = 'custom_reminder',
}

export enum CalendarEventStatus {
  UPCOMING = 'upcoming',
  DUE = 'due',
  OVERDUE = 'overdue',
  COMPLETED = 'completed',
}

export enum CalendarEventPriority {
  LOW = 'low',
  MEDIUM = 'medium',
  HIGH = 'high',
}

export interface RelatedEntity {
  id: number;
  name: string;
}

export interface CalendarEvent {
  id: string;
  type: CalendarEventType;
  title: string;
  description?: string;
  start_at: string;
  end_at?: string;
  all_day: boolean;
  status: CalendarEventStatus;
  priority: CalendarEventPriority;
  link?: string;
  property?: RelatedEntity;
  property_id?: number;
  property_name?: string;
  unit?: RelatedEntity;
  unit_id?: number;
  tenant?: RelatedEntity;
  tenant_id?: number;
  tenant_name?: string;
  lease_id?: number;
  source_type?: string;
  source_id: string;
  color: string;
  quick_actions: string[];
  metadata: Record<string, any>;
}

export interface CalendarEventsResponse {
  events: CalendarEvent[];
  total: number;
  from_date: string;
  to_date: string;
}

export interface CustomReminderCreate {
  title: string;
  description?: string;
  reminder_date: string;
  all_day?: boolean;
  property_id?: number;
  unit_id?: number;
  tenant_id?: number;
  notify_before_hours?: number;
}

export interface CustomReminderUpdate {
  title?: string;
  description?: string;
  reminder_date?: string;
  all_day?: boolean;
  is_completed?: boolean;
  property_id?: number;
  unit_id?: number;
  tenant_id?: number;
  notify_before_hours?: number;
}

export interface CustomReminder {
  id: string;
  user_id: string;
  title: string;
  description?: string;
  reminder_date: string;
  all_day: boolean;
  property_id?: number;
  unit_id?: number;
  tenant_id?: number;
  is_completed: boolean;
  completed_at?: string;
  notify_before_hours: number;
  created_at: string;
  updated_at: string;
}

// ============================================================================
// API FUNCTIONS
// ============================================================================

/**
 * Fetch unified calendar events from all sources
 */
export const fetchCalendarEvents = async (
  filters: CalendarFilters
): Promise<CalendarEventsResponse> => {
  const params = new URLSearchParams();
  
  if (filters.from_date) params.append('from_date', filters.from_date);
  if (filters.to_date) params.append('to_date', filters.to_date);
  if (filters.property_id) params.append('property_id', filters.property_id.toString());
  if (filters.unit_id) params.append('unit_id', filters.unit_id.toString());
  if (filters.tenant_id) params.append('tenant_id', filters.tenant_id.toString());
  if (filters.event_type) params.append('event_type', filters.event_type);
  if (filters.status) params.append('status', filters.status);

  const queryString = params.toString();
  return apiRequest(`/calendar/events${formatQueryString(queryString)}`);
};

/**
 * Create a new custom reminder
 */
export const createCustomReminder = async (
  reminderData: CustomReminderCreate
): Promise<CustomReminder> => {
  return apiRequest('/calendar/reminders', {
    method: 'POST',
    body: JSON.stringify(reminderData),
  });
};

/**
 * Update an existing custom reminder
 */
export const updateCustomReminder = async (
  reminderId: string,
  updateData: CustomReminderUpdate
): Promise<CustomReminder> => {
  return apiRequest(`/calendar/reminders/${reminderId}`, {
    method: 'PATCH',
    body: JSON.stringify(updateData),
  });
};

/**
 * Delete a custom reminder
 */
export const deleteCustomReminder = async (reminderId: string): Promise<void> => {
  return apiRequest(`/calendar/reminders/${reminderId}`, {
    method: 'DELETE',
  });
};

/**
 * Mark a custom reminder as complete
 */
export const completeReminder = async (reminderId: string): Promise<CustomReminder> => {
  return updateCustomReminder(reminderId, { is_completed: true });
};

/**
 * Get a specific custom reminder
 */
export const getCustomReminder = async (reminderId: string): Promise<CustomReminder> => {
  return apiRequest(`/calendar/reminders/${reminderId}`);
};

