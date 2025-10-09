// Leases API Functions
import { apiRequest, formatQueryString, uploadFile } from './core';
import type {
  Lease,
  LeaseCreate,
  LeaseUpdate,
  LeaseDocument,
  LeaseAnalysisResponse,
  LeaseUploadResponse,
  LeasesQueryParams,
  SecureDocumentUrlResponse,
} from '../../types/lease';

export const fetchLeases = async (params: LeasesQueryParams = {}): Promise<Lease[]> => {
  const queryParams = new URLSearchParams();

  if (params.status) queryParams.append("status", params.status.toString());
  if (params.property_id) queryParams.append("property_id", params.property_id.toString());
  if (params.tenant_id) queryParams.append("tenant_id", params.tenant_id.toString());

  const queryString = queryParams.toString();
  return apiRequest(`/leases/${formatQueryString(queryString)}`);
};

export const fetchLease = async (leaseId: number): Promise<Lease> => {
  return apiRequest(`/leases/${leaseId}`);
};

export const createLease = async (leaseData: LeaseCreate): Promise<Lease> => {
  return apiRequest("/leases/", {
    method: "POST",
    body: JSON.stringify(leaseData),
  });
};

export const updateLease = async (leaseId: number, leaseData: LeaseUpdate): Promise<Lease> => {
  return apiRequest(`/leases/${leaseId}`, {
    method: "PUT",
    body: JSON.stringify(leaseData),
  });
};

export const deleteLease = async (leaseId: number): Promise<void> => {
  return apiRequest(`/leases/${leaseId}`, {
    method: "DELETE",
  });
};

export const validateLease = async (leaseId: number): Promise<Lease> => {
  return apiRequest(`/leases/${leaseId}/validate`, {
    method: "POST",
  });
};

export const updateLeaseStatus = async (leaseId: number, status: string): Promise<Lease> => {
  return apiRequest(`/leases/${leaseId}/status`, {
    method: "POST",
    body: JSON.stringify({ status }),
  });
};

export const uploadLeaseDocument = async (
  leaseId: number,
  formData: FormData
): Promise<LeaseDocument> => {
  return uploadFile(`/leases/${leaseId}/upload`, formData);
};

export const fetchLeaseDocuments = async (leaseId: number): Promise<LeaseDocument[]> => {
  return apiRequest(`/leases/${leaseId}/documents`);
};

export const analyzeLease = async (formData: FormData): Promise<LeaseAnalysisResponse> => {
  return apiRequest("/leases/analyze", {
    method: "POST",
    body: formData,
  });
};

export const parseLease = async (formData: FormData): Promise<LeaseAnalysisResponse> => {
  return apiRequest("/leases/parse", {
    method: "POST",
    body: formData,
  });
};

export const uploadLeasePDF = async (file: File): Promise<string> => {
  const data = await uploadFile("/leases/upload-lease", file) as LeaseUploadResponse;
  return data.file_url;
};

export const getSecureDocumentUrl = async (
  leaseId: number,
  documentId: number
): Promise<SecureDocumentUrlResponse> => {
  return apiRequest(`/leases/${leaseId}/documents/${documentId}/secure-url`);
};

