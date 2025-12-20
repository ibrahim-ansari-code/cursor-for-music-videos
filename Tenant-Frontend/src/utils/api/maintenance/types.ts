// TypeScript types for maintenance API

export enum MaintenancePriority {
  LOW = "Low",
  MEDIUM = "Medium", 
  HIGH = "High"
}

export enum MaintenanceStatus {
  NEW = "New",
  PENDING = "Pending",
  IN_PROGRESS = "In Progress",
  SCHEDULED = "Scheduled",
  COMPLETED = "Completed",
  CANCELLED = "Cancelled"
}

export interface PropertyInfo {
  id: number;
  name: string;
}

export interface UnitInfo {
  id: number;
  name: string;
}

export interface TenantInfo {
  id: number;
  first_name: string;
  last_name: string;
}

export interface MaintenanceRequest {
  id: number;
  issue_title: string;
  description: string | null;
  property: PropertyInfo | null;
  unit: UnitInfo | null;
  tenant: TenantInfo | null;
  request_date: string; // ISO datetime string
  priority: MaintenancePriority;
  status: MaintenanceStatus;
  scheduled_date: string | null; // ISO date string
  completed_date: string | null; // ISO datetime string
  estimated_cost: number | null;
  actual_cost: number | null;
  photos: string[] | null;
  created_at: string; // ISO datetime string
  updated_at: string; // ISO datetime string
  assigned_to: string | null;
  preferred_time: string | null;
}

export interface MaintenanceRequestCreate {
  issue_title: string;
  description?: string;
  property_id?: number; // Optional - auto-inferred for tenant users
  unit_id?: number;
  tenant_id?: number; // Optional - auto-inferred for tenant users
  priority: MaintenancePriority;
  scheduled_date?: string; // ISO date string
  estimated_cost?: number;
  actual_cost?: number;
  photos?: string[];
  assigned_to?: string;
  preferred_time?: string;
}

export interface MaintenanceRequestUpdate {
  issue_title?: string;
  description?: string;
  property_id?: number;
  unit_id?: number;
  tenant_id?: number;
  priority?: MaintenancePriority;
  status?: MaintenanceStatus;
  scheduled_date?: string; // ISO date string
  completed_date?: string; // ISO datetime string
  estimated_cost?: number;
  actual_cost?: number;
  photos?: string[];
  assigned_to?: string;
  preferred_time?: string;
}

export interface MaintenanceSummary {
  total_requests: number;
  pending: number;
  in_progress: number;
  completed: number;
  scheduled: number;
  cancelled: number;
}

export interface MaintenancePhotoUploadResponse {
  photo_url: string;
}

export interface MaintenanceFilters {
  status?: MaintenanceStatus;
  priority?: MaintenancePriority;
  property_id?: number;
  unit_id?: number;
  tenant_id?: number;
  assigned_to?: string;
  limit?: number;
  offset?: number;
}
