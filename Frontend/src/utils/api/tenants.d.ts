export interface Tenant {
  id: number;
  full_name: string;
  email?: string;
  property_units?: Array<{
    property_id: number;
  }>;
  [key: string]: any;
}

export interface FetchTenantsParams {
  property_id?: number | string; // URLSearchParams accepts both, converts to string
  status?: string;
  search?: string;
  unassigned_only?: boolean;
  [key: string]: unknown;
}

export function fetchTenants(params?: FetchTenantsParams): Promise<Tenant[]>;

export function fetchTenant(tenantId: number | string): Promise<Tenant>;

export function createTenant(tenantData: any): Promise<Tenant>;

export function updateTenant(tenantId: number, tenantData: any): Promise<Tenant>;

export function deleteTenant(tenantId: number): Promise<any>;

export function fetchTenantsByProperty(propertyId: number): Promise<Tenant[]>;
