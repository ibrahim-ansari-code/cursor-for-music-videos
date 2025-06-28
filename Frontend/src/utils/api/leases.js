// Leases API Functions
import { apiRequest, formatQueryString, uploadFile } from './core';

const API_BASE_URL = (import.meta.env.VITE_API_URL || "").replace(/\/+$/, "");

export const fetchLeases = async (params = {}) => {
  const queryParams = new URLSearchParams();

  if (params.status) queryParams.append("status", params.status);
  if (params.property_id) queryParams.append("property_id", params.property_id);
  if (params.tenant_id) queryParams.append("tenant_id", params.tenant_id);

  const queryString = queryParams.toString();
  return apiRequest(`/leases/${formatQueryString(queryString)}`);
};

export const fetchLease = async (leaseId) => {
  return apiRequest(`/leases/${leaseId}`);
};

export const createLease = async (leaseData) => {
  return apiRequest("/leases/", {
    method: "POST",
    body: JSON.stringify(leaseData),
  });
};

export const updateLease = async (leaseId, leaseData) => {
  return apiRequest(`/leases/${leaseId}`, {
    method: "PUT",
    body: JSON.stringify(leaseData),
  });
};

export const deleteLease = async (leaseId) => {
  return apiRequest(`/leases/${leaseId}`, {
    method: "DELETE",
  });
};

export const validateLease = async (leaseId) => {
  return apiRequest(`/leases/${leaseId}/validate`, {
    method: "POST",
  });
};

export const updateLeaseStatus = async (leaseId, status) => {
  return apiRequest(`/leases/${leaseId}/status`, {
    method: "POST",
    body: JSON.stringify({ status }),
  });
};

export const uploadLeaseDocument = async (leaseId, formData) => {
  return uploadFile(`/leases/${leaseId}/upload`, formData, {
    errorMsg: "Failed to upload lease document.",
  });
};

export const fetchLeaseDocuments = async (leaseId) => {
  return apiRequest(`/leases/${leaseId}/documents`);
};

export const analyzeLease = async (formData) => {
  return apiRequest("/leases/analyze", {
    method: "POST",
    body: formData,
  });
};

export const parseLease = async (formData) => {
  return apiRequest("/leases/parse", {
    method: "POST",
    body: formData,
  });
};

export const uploadLeasePDF = async (file) => {
  const data = await uploadFile("/leases/upload-lease", file, {
    errorMsg: "Failed to upload lease PDF.",
  });
  return data.file_url;
}; 