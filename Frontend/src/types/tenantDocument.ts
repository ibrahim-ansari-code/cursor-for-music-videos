/**
 * Tenant Document Type Definitions
 * 
 * Strongly-typed TypeScript interfaces and enums for tenant document management.
 * These types must stay in sync with backend enums and database schema.
 * 
 * Type Safety Strategy:
 * - Database: PostgreSQL ENUM types (document_category_enum, document_status_enum)
 * - Backend: Python str, Enum classes
 * - Frontend: TypeScript enum (this file)
 * 
 * Benefits:
 * - Compile-time validation of category/status values
 * - IDE autocomplete for valid options
 * - Refactoring safety (rename propagates)
 * - Self-documenting code
 */

// ============================================================================
// ENUMS (Must match backend exactly)
// ============================================================================

export enum DocumentCategory {
  LEASE_AGREEMENTS = 'lease_agreements',
  LEASE_ADDENDUMS = 'lease_addendums',
  CONDITION_INSPECTIONS = 'condition_inspections',
  PROVINCE_FORMS = 'province_forms',
  COMMERCIAL_FILES = 'commercial_files',
  APPLICATIONS_KYC = 'applications_kyc',
  INSURANCE_RISK = 'insurance_risk',
  FINANCIAL_PAYMENTS = 'financial_payments',
  MAINTENANCE_WORK = 'maintenance_work',
  LEGAL_NOTICES = 'legal_notices',
  COMMUNICATIONS = 'communications',
  MOVE_IN_OUT = 'move_in_out',
  PRIVACY_SECURITY = 'privacy_security',
  HEALTH_SAFETY = 'health_safety'
}

export enum DocumentStatus {
  PENDING = 'pending',
  VERIFIED = 'verified',
  REJECTED = 'rejected',
  EXPIRED = 'expired'
}

// ============================================================================
// LABEL MAPPINGS (For UI Display)
// ============================================================================

export const CATEGORY_LABELS: Record<DocumentCategory, string> = {
  [DocumentCategory.LEASE_AGREEMENTS]: 'Lease & Core Agreements',
  [DocumentCategory.LEASE_ADDENDUMS]: 'Lease Addendums',
  [DocumentCategory.CONDITION_INSPECTIONS]: 'Condition & Inspections',
  [DocumentCategory.PROVINCE_FORMS]: 'Province/Territory Forms',
  [DocumentCategory.COMMERCIAL_FILES]: 'Commercial Tenant Files',
  [DocumentCategory.APPLICATIONS_KYC]: 'Applications & Screening/KYC',
  [DocumentCategory.INSURANCE_RISK]: 'Insurance & Risk',
  [DocumentCategory.FINANCIAL_PAYMENTS]: 'Financial & Payments',
  [DocumentCategory.MAINTENANCE_WORK]: 'Maintenance/Unit-Level Work',
  [DocumentCategory.LEGAL_NOTICES]: 'Legal Notices & Tribunal',
  [DocumentCategory.COMMUNICATIONS]: 'Communications & Records',
  [DocumentCategory.MOVE_IN_OUT]: 'Move-In/Move-Out & Assets',
  [DocumentCategory.PRIVACY_SECURITY]: 'Privacy & Data Security',
  [DocumentCategory.HEALTH_SAFETY]: 'Health/Safety/Accessibility'
};

export const STATUS_LABELS: Record<DocumentStatus, string> = {
  [DocumentStatus.PENDING]: 'Pending',
  [DocumentStatus.VERIFIED]: 'Verified',
  [DocumentStatus.REJECTED]: 'Rejected',
  [DocumentStatus.EXPIRED]: 'Expired'
};

// ============================================================================
// CORE INTERFACES
// ============================================================================

/**
 * Main tenant document interface
 * 
 * Represents a document uploaded for a tenant with full metadata,
 * classification, and computed fields for expiry tracking.
 */
export interface TenantDocument {
  // Core fields
  id: string;
  tenant_id: string;
  document_name: string | null;  // User-friendly name (falls back to file_name)
  file_name: string;
  file_path: string;
  file_size: number;
  file_type: string;

  // Classification (strongly typed)
  document_category: DocumentCategory;
  document_type: string;

  // Organization
  tags: string[];
  notes: string | null;

  // Compliance
  expiry_date: string | null;  // ISO date string (YYYY-MM-DD)
  status: DocumentStatus;

  // Audit trail
  uploaded_by: string;
  uploaded_at: string;  // ISO datetime string
  created_at: string;   // ISO datetime string
  updated_at: string;   // ISO datetime string

  // Computed fields (from backend)
  is_expired: boolean;
  days_until_expiry: number | null;
}

/**
 * Category information from taxonomy
 * 
 * Describes a document category with its metadata and available types.
 */
export interface CategoryInfo {
  key: string;  // Category enum value
  label: string;  // Human-readable label
  types: string[];  // List of specific document types
  requires_expiry: boolean;  // Whether expiry tracking is recommended
  icon: string;  // Icon name for UI
}

/**
 * Complete document taxonomy structure
 * 
 * Contains all 14 categories with 200+ document types.
 * Fetched from /api/document-types/taxonomy endpoint.
 */
export interface DocumentTaxonomy {
  categories: CategoryInfo[];
}

// ============================================================================
// FILTER & QUERY INTERFACES
// ============================================================================

/**
 * Filter parameters for document list queries
 * 
 * All fields are optional. Used in GET /api/tenants/{tenant_id}/documents
 */
export interface DocumentFilters {
  search?: string;
  category?: DocumentCategory;
  type?: string;
  status?: DocumentStatus;
  date_from?: string;  // ISO date string
  date_to?: string;    // ISO date string
}

// ============================================================================
// FORM DATA INTERFACES
// ============================================================================

/**
 * Upload form data structure
 *
 * Used when creating FormData for document upload.
 */
export interface DocumentUploadData {
  file: File;
  document_name?: string;  // Optional user-friendly name
  document_category: DocumentCategory;
  document_type: string;
  tags: string[];
  notes: string;
  expiry_date: string | null;  // ISO date string (YYYY-MM-DD)
}

/**
 * Update request data structure
 *
 * All fields optional - only provided fields will be updated.
 * Used in PATCH /api/tenants/{tenant_id}/documents/{document_id}
 */
export interface DocumentUpdateData {
  document_name?: string;
  tags?: string[];
  notes?: string;
  status?: DocumentStatus;
  expiry_date?: string | null;  // ISO date string or null to remove
}

// ============================================================================
// API RESPONSE INTERFACES
// ============================================================================

/**
 * Paginated document list response
 * 
 * Returned from GET /api/tenants/{tenant_id}/documents
 */
export interface DocumentListResponse {
  documents: TenantDocument[];
  total: number;
  limit: number;
  offset: number;
}

/**
 * Secure URL response
 * 
 * Returned from GET /api/tenants/{tenant_id}/documents/{document_id}/secure-url
 * Contains time-limited SAS token URL for secure document access.
 */
export interface SecureUrlResponse {
  secure_url: string;
  expires_at: string;  // ISO datetime string
  expires_in_seconds: number;
}

// ============================================================================
// UTILITY FUNCTIONS
// ============================================================================

/**
 * Get human-readable label for a category
 */
export function getCategoryLabel(category: DocumentCategory): string {
  return CATEGORY_LABELS[category] || category;
}

/**
 * Get human-readable label for a status
 */
export function getStatusLabel(status: DocumentStatus): string {
  return STATUS_LABELS[status] || status;
}

/**
 * Check if a document is expiring soon (within 30 days)
 */
export function isExpiringSoon(document: TenantDocument): boolean {
  if (!document.days_until_expiry) return false;
  return document.days_until_expiry > 0 && document.days_until_expiry <= 30;
}

/**
 * Get urgency level based on days until expiry
 */
export function getExpiryUrgency(document: TenantDocument): 'expired' | 'critical' | 'warning' | 'normal' | 'none' {
  if (!document.expiry_date) return 'none';
  if (document.is_expired) return 'expired';
  if (document.days_until_expiry !== null) {
    if (document.days_until_expiry <= 7) return 'critical';
    if (document.days_until_expiry <= 30) return 'warning';
  }
  return 'normal';
}

/**
 * Format file size for display
 */
export function formatFileSize(bytes: number): string {
  if (bytes === 0) return '0 Bytes';
  
  const k = 1024;
  const sizes = ['Bytes', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(2))} ${sizes[i]}`;
}

/**
 * Format expiry date for display
 */
export function formatExpiryDisplay(document: TenantDocument): string {
  if (!document.expiry_date) return 'No expiry';

  if (document.is_expired) {
    const daysAgo = Math.abs(document.days_until_expiry || 0);
    return `Expired ${daysAgo} day${daysAgo !== 1 ? 's' : ''} ago`;
  }

  if (document.days_until_expiry !== null) {
    if (document.days_until_expiry === 0) return 'Expires today';
    if (document.days_until_expiry === 1) return 'Expires tomorrow';
    if (document.days_until_expiry <= 30) {
      return `Expires in ${document.days_until_expiry} days`;
    }
  }

  // Format as readable date
  const expiryDate = new Date(document.expiry_date);
  return `Expires ${expiryDate.toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric'
  })}`;
}

/**
 * Get display name for a document
 * Falls back to file_name if document_name is not set
 */
export function getDocumentDisplayName(document: TenantDocument): string {
  return document.document_name || document.file_name;
}


