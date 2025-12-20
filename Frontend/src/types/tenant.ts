/**
 * Tenant type definitions with strict type safety and security considerations
 *
 * Security Note: All string fields in these interfaces should be validated
 * and sanitized before use. The backend applies XSS protection via HTML escaping.
 */

export enum TenantType {
  INDIVIDUAL = 'Individual',
  COMPANY = 'Company'
}

/**
 * Branded type for validated email addresses
 * Use this to ensure emails have passed validation before assignment
 */
export type ValidatedEmail = string & { readonly __brand: 'ValidatedEmail' };

/**
 * Branded type for validated phone numbers
 * Use this to ensure phone numbers have passed validation before assignment
 */
export type ValidatedPhone = string & { readonly __brand: 'ValidatedPhone' };

/**
 * Emergency Contact Interface
 *
 * Security Considerations:
 * - All text fields are sanitized on the backend using HTML escaping
 * - Phone numbers are stripped of non-numeric characters (except +, -, (), spaces)
 * - Email addresses must match a valid email pattern
 * - Maximum 5 emergency contacts allowed per tenant (enforced at DB level)
 * - Only one contact can be marked as primary (enforced at DB level)
 *
 * Validation Rules:
 * - name: Required, non-empty after trimming
 * - relationship: Required, non-empty after trimming (e.g., "Spouse", "Parent", "Sibling")
 * - phone: Required, non-empty after trimming
 * - email: Optional, must be valid email format if provided
 * - is_primary: Required boolean, only one can be true across all contacts
 * - notes: Optional, user-generated content (XSS risk mitigated by backend sanitization)
 *
 * @example
 * ```typescript
 * const contact: EmergencyContact = {
 *   name: 'John Doe',
 *   relationship: 'Spouse',
 *   phone: '+1-555-123-4567',
 *   email: 'john.doe@example.com',
 *   is_primary: true,
 *   notes: 'Available 24/7'
 * };
 * ```
 */
export interface EmergencyContact {
  /**
   * Client-side UUID for tracking (optional, generated on create)
   * Server does not use this field; it's for React key props and optimistic updates
   */
  readonly id?: string;

  /**
   * Full name of the emergency contact
   * Required, validated and HTML-escaped on backend to prevent XSS
   * @minLength 1 (after trimming)
   * @maxLength 200 (reasonable limit for names)
   */
  name: string;

  /**
   * Relationship to tenant (e.g., "Spouse", "Parent", "Sibling", "Friend")
   * Required, validated and HTML-escaped on backend to prevent XSS
   * @minLength 1 (after trimming)
   * @maxLength 100 (reasonable limit for relationship description)
   */
  relationship: string;

  /**
   * Contact phone number
   * Required, sanitized on backend (only digits, +, -, (), spaces allowed)
   * @pattern Must contain at least some digits
   * @example '+1-555-123-4567' or '(555) 123-4567'
   */
  phone: string;

  /**
   * Contact email address (optional)
   * Validated for proper email format if provided
   * HTML-escaped on backend (though emails shouldn't contain HTML)
   * @format email
   * @pattern ^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$
   */
  email?: string;

  /**
   * Whether this is the primary emergency contact
   * Only one contact per tenant can have this set to true (enforced at DB level)
   * @default false
   */
  is_primary: boolean;

  /**
   * Additional notes about the contact (optional)
   * User-generated content - high XSS risk, sanitized with HTML escaping on backend
   * @maxLength 500 (reasonable limit for notes)
   */
  notes?: string;
}

/**
 * Type guard to check if an emergency contact is valid
 * Use this before sending to API to catch client-side validation issues early
 *
 * @param contact - The contact object to validate
 * @returns True if contact has all required fields populated
 */
export function isValidEmergencyContact(contact: Partial<EmergencyContact>): contact is EmergencyContact {
  return (
    typeof contact.name === 'string' &&
    contact.name.trim().length > 0 &&
    typeof contact.relationship === 'string' &&
    contact.relationship.trim().length > 0 &&
    typeof contact.phone === 'string' &&
    contact.phone.trim().length > 0 &&
    typeof contact.is_primary === 'boolean'
  );
}

export enum TenantStatus {
  ACTIVE = 'Active',
  INACTIVE = 'Inactive',
  PENDING = 'Pending',
  EVICTED = 'Evicted',
  MOVED_OUT = 'Moved Out'
}

export enum MaintenancePriority {
  LOW = 'Low',
  MEDIUM = 'Medium',
  HIGH = 'High',
  URGENT = 'Urgent'
}

export enum MaintenanceStatus {
  NEW = 'New',
  PENDING = 'Pending',
  IN_PROGRESS = 'In Progress',
  SCHEDULED = 'Scheduled',
  COMPLETED = 'Completed',
  CANCELLED = 'Cancelled'
}

export enum LeaseStatus {
  DRAFT = 'DRAFT',
  PENDING = 'PENDING',
  ACTIVE = 'ACTIVE',
  EXPIRED = 'EXPIRED',
  TERMINATED = 'TERMINATED',
  RENEWED = 'RENEWED'
}

// Core Tenant Interface
export interface Tenant {
  id: number;
  user_id?: string;
  tenant_type: TenantType;
  first_name?: string;
  last_name?: string;
  company_name?: string;
  contact_person?: string;
  phone?: string;
  email?: string;
  status: TenantStatus;
  created_at: string;
  updated_at: string;
  current_property_id?: number;
  landlord_id: string;
  profile_image_url?: string;
  quickbooks_customer_id?: string;
  last_synced_at?: string;
  emergency_contacts?: EmergencyContact[];
}

// Property Unit Interface
export interface PropertyUnit {
  id: number;
  name: string;
  property_id: number;
  floor?: number;
  description?: string;
  size?: number;
  monthly_rent?: number;
  is_rented?: boolean;
  bedrooms?: number;
  bathrooms?: number;
  tenant_id?: number;
  created_at?: string;
  updated_at?: string;
  property?: {
    id: number;
    name: string;
    address?: string;
    city?: string;
    province?: string;
  };
}

// Property Interface (simplified for tenant context)
export interface Property {
  id: number;
  name: string;
  address?: string;
  city?: string;
  province?: string;
  postal_code?: string;
  property_type?: string;
  status?: string;
}

// Lease Interface
export interface Lease {
  id: number;
  start_date: string;
  end_date: string;
  monthly_rent: number;
  security_deposit: number;
  status: LeaseStatus;
  is_renewable: boolean;
  auto_renew: boolean;
  rent_due_day: number;
  late_fee_amount?: number;
  late_fee_after_days?: number;
  special_terms?: string;
  property_id: number;
  unit_id?: number;
  tenant_id: number;
  created_at: string;
  updated_at: string;
  property?: Property;
  unit?: PropertyUnit;
  documents?: LeaseDocument[];
}

// Lease Document Interface
export interface LeaseDocument {
  id: number;
  name: string;
  file_path: string;
  document_type: string;
  upload_date: string;
  lease_id: number;
  file_size?: number;
  mime_type?: string;
}

// Vendor Contact Info (basic info embedded in maintenance requests)
export interface VendorContactInfo {
  id: number;
  company_name: string;
  contact_person: string | null;
  trade_category: string;
  phone: string;
  email: string | null;
}

// Maintenance Request Interface
export interface MaintenanceRequest {
  id: number;
  issue_title: string;
  description?: string;
  property_id: number;
  unit_id?: number;
  tenant_id?: number;
  user_id?: string;
  request_date: string;
  priority: MaintenancePriority;
  status: MaintenanceStatus;
  scheduled_date?: string;
  completed_date?: string;
  estimated_cost?: number;
  actual_cost?: number;
  photos?: string[];
  created_at: string;
  updated_at: string;
  assigned_to?: string;
  vendor_id?: number | null;
  vendor?: VendorContactInfo | null;
  notify_tenant: boolean;
  property?: Property;
  unit?: PropertyUnit;
  tenant?: Tenant;  // Populated by backend when loading maintenance requests
  preferred_time?: string;
}

// Payment Interface
export interface Payment {
  id: number;
  amount: number;
  payment_date: string;
  payment_method?: string;
  transaction_reference?: string;
  description?: string;
  status: 'Pending' | 'Paid' | 'Partial' | 'Overdue' | 'Cancelled' | 'Refunded' | 'Draft' | 'Void' | 'Uncollectible';
  tenant_id: number;
  lease_id?: number;
  reduction_amount?: number;
  reduction_reason?: string;
  receipt_url?: string;
  created_at: string;
  updated_at: string;
}

// Invoice Interface
export interface Invoice {
  id: number;
  invoice_number: string;
  amount: number;
  due_date: string;
  issue_date: string;
  description: string;
  status: 'Pending' | 'Paid' | 'Partial' | 'Overdue' | 'Cancelled' | 'Refunded' | 'Draft' | 'Void' | 'Uncollectible';
  tenant_id: number;
  property_id?: number;
  created_at: string;
  updated_at: string;
}

// Enriched Tenant with all relationships
export interface EnrichedTenant extends Tenant {
  leases?: Lease[];
  maintenance_requests?: MaintenanceRequest[];
  documents?: LeaseDocument[];
  payments?: Payment[];
  invoices?: Invoice[];
  unit?: PropertyUnit;
  property?: Property;
  assigned_units?: PropertyUnit[];
  units?: PropertyUnit[];
}

// API Response Types
export interface TenantResponse extends EnrichedTenant {
  // Additional computed fields that might come from backend
  full_name?: string;
  display_name?: string;
}

// Component Prop Types
export interface TenantTableProps {
  tenants: EnrichedTenant[];
  onAddTenant: () => void;
  isLoading: boolean;
  selectedTenants: number[];
  onToggleSelectAll: () => void;
  onToggleSelect: (tenantId: number) => void;
}

// Maintenance Form Types
export interface MaintenanceFormData {
  issue_title: string;
  description?: string;
  priority: MaintenancePriority | 'Low' | 'Medium' | 'High';
  status: MaintenanceStatus | 'Pending' | 'In Progress' | 'Scheduled' | 'Completed' | 'Cancelled';
  property_id: string;
  unit_id?: string;
  tenant_id?: string;
  assigned_to?: string;
  vendor_id?: string;
  notify_tenant?: boolean;
  scheduled_date?: string;
  estimated_cost?: string;
  start_date?: string;
  end_date?: string;
  photos?: string[];
  preferred_time?: string;
}

// Photo Upload Types
export interface PhotoFileWithId {
  id: string;
  file: File;
  name: string;
  size: number;
  preview?: string; // Object URL for local preview before upload
}

export interface PhotoUploadProgress {
  id: string;
  status: 'pending' | 'uploading' | 'done' | 'error';
  error?: string;
}

export interface MaintenancePhotoState {
  selectedFiles: PhotoFileWithId[];
  uploadingPhotos: boolean;
  uploadProgress: PhotoUploadProgress[];
  uploadError: string | null;
}

// Maintenance Summary Type
export interface MaintenanceSummary {
  total_requests: number;
  new: number;
  pending: number;
  in_progress: number;
  completed: number;
  cancelled: number;
}

// Table Props
export interface MaintenanceTableProps {
  requests: MaintenanceRequest[];
  onEdit: (request: MaintenanceRequest) => void;
  onDelete: (requestId: number) => void;
  onView: (request: MaintenanceRequest) => void;
  currentPage?: number;
  pageSize?: number;
}