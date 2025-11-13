/**
 * Vendor Contact type definitions
 *
 * Defines types for vendor/contractor management in the maintenance system.
 * Uses a normalized schema with a central vendor table and user-specific associations.
 * 
 * Architecture:
 * - `Vendor`: Central vendor data shared across platform
 * - `UserVendor`: User-specific vendor association and preferences
 * - `VendorContact`: Combined view for frontend (merges both)
 */

export interface VendorContact {
  // Central Vendor fields
  id: number;
  company_name: string;
  contact_person: string | null;
  trade_category: string;
  phone: string;
  email: string | null;
  is_verified: boolean;
  average_rating: number | null;
  total_reviews: number;
  created_at: string;
  updated_at: string;
  
  // User-specific fields (from UserVendor join table)
  user_id: string;
  notes: string | null;
  is_active: boolean;
  is_favorite: boolean;
  personal_rating: number | null; // 1-5 rating
}

export interface VendorContactCreate {
  company_name: string;
  contact_person?: string | null;
  trade_category: string;
  phone: string;
  email?: string | null;
  notes?: string | null;
  is_active?: boolean;
}

export interface VendorContactUpdate {
  // Only user-specific fields can be updated
  // Central vendor fields are managed at platform level
  notes?: string | null;
  is_active?: boolean;
  is_favorite?: boolean;
  personal_rating?: number | null; // 1-5 rating
}

export interface VendorContactListResponse {
  vendors: VendorContact[];
  total: number;
  limit: number;
  offset: number;
}

export interface VendorContactInfo {
  id: number;
  company_name: string;
  contact_person: string | null;
  trade_category: string;
  phone: string;
  email: string | null;
}

/**
 * Common trade categories for dropdowns
 */
export const COMMON_TRADE_CATEGORIES = [
  "Plumber",
  "Electrician",
  "HVAC",
  "Carpenter",
  "General Contractor",
  "Painter",
  "Roofer",
  "Locksmith",
  "Appliance Repair",
  "Landscaper",
  "Pest Control",
  "Cleaner",
  "Other",
] as const;

export type TradeCategory = typeof COMMON_TRADE_CATEGORIES[number];

/**
 * Props for vendor-related components
 */
export interface VendorTableProps {
  vendors: VendorContact[];
  onEdit: (vendor: VendorContact) => void;
  onDelete: (vendorId: number) => void;
  onView: (vendor: VendorContact) => void;
  isLoading: boolean;
  selectedVendors: number[];
  onToggleSelect: (vendorId: number) => void;
  onToggleSelectAll: () => void;
}

export interface VendorModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (data: VendorContactCreate | VendorContactUpdate) => Promise<void>;
  vendor?: VendorContact | null;
  isViewing?: boolean;
  isSubmitting?: boolean;
}

export interface VendorFormData {
  // For creating new vendors
  company_name: string;
  contact_person: string;
  trade_category: string;
  phone: string;
  email: string;
  notes: string;
  is_active: boolean;
}

export interface VendorUpdateFormData {
  // For updating existing vendor associations
  notes: string;
  is_active: boolean;
  is_favorite: boolean;
  personal_rating: number | null;
}

