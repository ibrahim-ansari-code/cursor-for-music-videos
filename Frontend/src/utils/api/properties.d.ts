import { PropertyUnit } from '../../types/property';

export interface FetchOptions extends RequestInit {
  headers?: Record<string, string>;
  signal?: AbortSignal;
  cache?: boolean;
  cacheMaxAge?: number;
}

export interface FetchPropertiesParams {
  owner_id?: string;
  property_type?: string;
  [key: string]: unknown;
}

export interface Property {
  id: number;
  name: string;
  address?: string;
  property_type?: string;
  units?: PropertyUnit[];
  description?: string;
  purchase_price?: string;
  purchase_date?: string;
  market_value?: string;
  rental_income?: string;
  expenses?: string;
  net_income?: string;
  owner_id?: number;
  created_at?: string;
  updated_at?: string;
  // Allow additional fields but with better typing
  [key: string]: string | number | boolean | null | undefined;
}

export function fetchProperties(
  params?: FetchPropertiesParams,
  options?: FetchOptions
): Promise<Property[]>;

export function fetchPropertyById(
  propertyId: number | string
): Promise<Property>;

export interface PropertyCreatePayload {
  name: string;
  address: string;
  property_type?: string;
  units?: string[]; // Array of unit names/numbers for apartment complexes
  description?: string;
  purchase_price?: string;
  purchase_date?: string;
  market_value?: string;
  rental_income?: string;
  owner_id?: number;
}

export interface PropertyUpdatePayload extends Partial<PropertyCreatePayload> {
  // All fields are optional for updates
}

export function createProperty(
  propertyData: PropertyCreatePayload
): Promise<Property>;

export function updateProperty(
  propertyId: number,
  propertyData: PropertyUpdatePayload
): Promise<Property>;

export function deleteProperty(propertyId: number): Promise<any>;
