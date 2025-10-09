// Lease-related TypeScript interfaces matching backend schemas

export enum LeaseStatus {
  DRAFT = 'DRAFT',
  PENDING = 'PENDING',
  ACTIVE = 'ACTIVE',
  EXPIRED = 'EXPIRED',
  TERMINATED = 'TERMINATED',
  RENEWED = 'RENEWED',
}

export interface Tenant {
  id: number;
  first_name?: string;
  last_name?: string;
  full_name?: string;
  email?: string;
  phone?: string;
  status?: string;
  user_id?: string;
  landlord_id?: string;
  current_property_id?: number;
  created_at?: string;
  updated_at?: string;
}

export interface Property {
  id: number;
  name?: string;
  address?: string;
  city?: string;
  province?: string;
  postal_code?: string;
  property_type?: string;
  status?: string;
  user_id?: string;
  created_at?: string;
  updated_at?: string;
}

export interface PropertyUnit {
  id: number;
  name: string;
  property_id: number;
  tenant_id?: number;
  monthly_rent?: number;
  is_rented: boolean;
  bedrooms?: number;
  bathrooms?: number;
  size?: number;
  description?: string;
  floor?: number;
}

export interface LeaseBase {
  start_date: string;
  end_date: string;
  monthly_rent: number | string;
  security_deposit: number | string;
  is_renewable?: boolean;
  auto_renew?: boolean;
  rent_due_day?: number;
  late_fee_amount?: number | string | null;
  late_fee_after_days?: number | null;
  special_terms?: string | null;
  property_id: number;
  unit_id?: number | null;
  tenant_id: number;
}

export interface LeaseCreate extends LeaseBase {
  status?: LeaseStatus;
  file_url?: string | null;
}

export interface LeaseUpdate {
  start_date?: string;
  end_date?: string;
  monthly_rent?: number | string;
  security_deposit?: number | string;
  rent_due_day?: number;
  late_fee_amount?: number | string | null;
  late_fee_after_days?: number | null;
  special_terms?: string | null;
}

export interface Lease extends LeaseBase {
  id: number;
  status: LeaseStatus | string;
  created_at: string;
  updated_at: string;
  tenant?: Tenant;
  property?: Property;
  unit?: PropertyUnit | null;
  documents?: LeaseDocument[];
  file_url?: string | null;
}

export interface LeaseDocument {
  id: number;
  name: string;
  file_path: string;
  document_type: string;
  upload_date: string;
  lease_id?: number;
  uploaded_by_id?: string | null;
}

export interface LeaseAnalysisResponse {
  monthly_rent: number | string;
  start_date?: string | null;
  end_date?: string | null;
  security_deposit: number | string;
  late_fee_amount?: number | string | null;
  tenant_name?: string | null;
  unit?: string | null;
}

export interface LeaseUploadResponse {
  file_url: string;
}

export interface SecureDocumentUrlResponse {
  secure_url: string;
  expires_at: string;  // ISO 8601 datetime string
  expires_in_seconds: number;
}

export interface LeasesQueryParams {
  status?: LeaseStatus | string;
  property_id?: number;
  tenant_id?: number;
}

