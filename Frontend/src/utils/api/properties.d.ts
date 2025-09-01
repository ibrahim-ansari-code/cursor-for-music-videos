declare module "@utils/api/properties" {
  import type {
    PropertyCreatePayload,
    PropertyUpdatePayload,
  } from "@types/property";

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

  export function fetchProperties(
    params?: FetchPropertiesParams,
    options?: FetchOptions
  ): Promise<any[]>;

  export function fetchPropertyById(
    propertyId: number | string
  ): Promise<any>;

  export function createProperty(
    propertyData: PropertyCreatePayload
  ): Promise<any>;

  export function updateProperty(
    propertyId: number,
    propertyData: PropertyUpdatePayload
  ): Promise<any>;

  export function deleteProperty(propertyId: number): Promise<any>;
}


