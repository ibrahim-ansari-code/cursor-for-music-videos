/**
 * Vendor Contact API Utilities
 *
 * HTTP request functions for vendor contact management
 */

import { apiRequest, formatQueryString } from './core';
import type {
  VendorContact,
  VendorContactCreate,
  VendorContactUpdate,
  VendorContactListResponse,
} from "../../types/vendor";

/**
 * List vendor contacts with optional filtering and pagination
 */
export async function listVendors(params?: {
  trade_category?: string;
  is_active?: boolean;
  search?: string;
  limit?: number;
  offset?: number;
}): Promise<VendorContactListResponse> {
  const queryParams = new URLSearchParams();

  if (params?.trade_category) queryParams.append("trade_category", params.trade_category);
  if (params?.is_active !== undefined) queryParams.append("is_active", String(params.is_active));
  if (params?.search) queryParams.append("search", params.search);
  if (params?.limit) queryParams.append("limit", String(params.limit));
  if (params?.offset) queryParams.append("offset", String(params.offset));

  const queryString = queryParams.toString();
  return apiRequest(`/vendors${formatQueryString(queryString)}`);
}

/**
 * Get a single vendor contact by ID
 */
export async function getVendor(vendorId: number): Promise<VendorContact> {
  return apiRequest(`/vendors/${vendorId}`);
}

/**
 * Create a new vendor contact
 */
export async function createVendor(data: VendorContactCreate): Promise<VendorContact> {
  return apiRequest("/vendors", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

/**
 * Update an existing vendor contact
 */
export async function updateVendor(
  vendorId: number,
  data: VendorContactUpdate
): Promise<VendorContact> {
  return apiRequest(`/vendors/${vendorId}`, {
    method: "PUT",
    body: JSON.stringify(data),
  });
}

/**
 * Delete a vendor contact
 */
export async function deleteVendor(vendorId: number): Promise<void> {
  return apiRequest(`/vendors/${vendorId}`, {
    method: "DELETE",
  });
}

/**
 * Bulk delete multiple vendor contacts
 */
export async function bulkDeleteVendors(vendorIds: number[]): Promise<void> {
  return apiRequest("/vendors/bulk", {
    method: "DELETE",
    body: JSON.stringify({ vendor_ids: vendorIds }),
  });
}

/**
 * Get list of trade categories used by the current user
 */
export async function getTradeCategories(): Promise<string[]> {
  return apiRequest("/vendors/trade-categories");
}
