import type { Lease, Property } from "../../../types/lease";
import type { Tenant } from "../../../types/tenant";

export interface Unit {
  id: number;
  name: string;
  property_id: number;
}

export interface FormData {
  property_id: string;
  unit_id: string;
  unit_name: string;
  tenant_id: number | null;
  monthly_rent: string;
  security_deposit: string;
  start_date: string;
  end_date: string;
  rent_due_day: string;
  late_fee_amount: string;
  late_fee_after_days: string;
  special_terms: string;
}

export interface FieldErrors {
  property_id?: string;
  unit_id?: string;
  tenant_id?: string;
  start_date?: string;
  end_date?: string;
  monthly_rent?: string;
  security_deposit?: string;
}

export interface ImportLeaseModalProps {
  isOpen: boolean;
  onClose: () => void;
  onImport: (lease: Lease) => void;
  initialMode?: 'file' | 'manual';
  propertyId?: number | null;
  unitId?: number | null;
  unitName?: string;
}

export interface PropertyDataState {
  properties: Property[];
  availableUnits: Unit[];
  availableTenants: Tenant[];
  isLoadingUnits: boolean;
  isLoadingTenants: boolean;
}

export interface LeaseFormState {
  formData: FormData;
  fieldErrors: FieldErrors;
  error: string | null;
  isLoading: boolean;
  selectedTenant: Tenant | null;
}

