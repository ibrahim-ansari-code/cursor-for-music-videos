/**
 * Unit type definitions with strict type safety
 * These types are used for property units and related components
 */

import type { Lease } from './lease';

/**
 * Property Unit Interface
 * Represents a rentable unit within a property
 */
export interface Unit {
  id: number;
  name: string;
  property_id: number;
  tenant_id?: number | null;
  description?: string | null;
  size?: number | null;
  monthly_rent?: number | null;
  is_rented: boolean;
  bedrooms?: number | null;
  bathrooms?: number | null;
  floor?: number | null;
  created_at?: string;
  updated_at?: string;
  unit_type_details?: Record<string, unknown>;
}

/**
 * Tenant info as returned with unit data
 * Simplified version for unit context
 */
export interface UnitTenant {
  id?: number;
  first_name?: string;
  last_name?: string;
  email?: string;
  phone?: string;
  tenant_type?: string;
  company_name?: string;
  status?: string;
}

/**
 * Unit with attached tenant data
 * Used when fetching units with tenant relationships
 */
export interface UnitWithTenant extends Unit {
  tenant?: UnitTenant | null;
}

/**
 * Unit with attached lease data
 * Used in PropertyDetail page where lease info is fetched separately
 */
export interface UnitWithLease extends UnitWithTenant {
  /** 
   * Lease data attached to unit
   * - undefined: fetch in progress
   * - null: fetch completed, no lease found
   * - Lease object: lease data available
   */
  lease?: Lease | null;
}

/**
 * Data required to create a new unit
 */
export interface UnitCreateData {
  name: string;
  description?: string;
  size?: number;
  monthly_rent?: number;
  bedrooms?: number;
  bathrooms?: number;
  floor?: number;
  is_rented?: boolean;
  unit_type_details?: Record<string, unknown>;
}

/**
 * Data for updating an existing unit
 * All fields are optional for partial updates
 */
export interface UnitUpdateData {
  name?: string;
  description?: string | null;
  size?: number | null;
  monthly_rent?: number | null;
  bedrooms?: number | null;
  bathrooms?: number | null;
  floor?: number | null;
  is_rented?: boolean;
  tenant_id?: number | null;
  unit_type_details?: Record<string, unknown>;
}

/**
 * Property stats returned from API
 */
export interface PropertyStats {
  total_units: number;
  occupied_units: number;
  vacant_units: number;
  monthly_revenue: number | string;
  occupancy_rate?: number;
}

/**
 * Property with units and stats
 * Used in PropertyDetail page
 */
export interface PropertyWithUnits {
  id: number;
  name: string;
  address?: string;
  city?: string;
  province?: string;
  postal_code?: string;
  property_type?: string;
  year_built?: number;
  description?: string;
  status?: string;
  user_id?: string;
  created_at?: string;
  updated_at?: string;
  units?: UnitWithLease[];
  stats?: PropertyStats | null;
}

/**
 * Props for UnitTable component
 */
export interface UnitTableProps {
  units: UnitWithLease[];
  loading?: boolean;
  error?: string | null;
  onEdit?: (unitId: number) => void;
  onDelete?: (unitId: number) => void;
  onAssign?: (unit: UnitWithLease) => void;
  onViewLease?: (unitId: number) => void;
  selectedUnits?: number[];
  onUnitSelect?: (unitId: number) => void;
  onSelectAll?: () => void;
  showSelection?: boolean;
  bulkMode?: boolean;
}

/**
 * Props for UnitStatusBadge component
 */
export interface UnitStatusBadgeProps {
  isRented: boolean;
  size?: 'small' | 'medium' | 'large';
}

