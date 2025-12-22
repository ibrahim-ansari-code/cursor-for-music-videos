// Centralized query key management for consistent caching
// Following TanStack Query best practices: hierarchical keys

import type { LeasesQueryParams } from '../types/lease';
import type { MaintenanceQueryParams } from './useMaintenanceQueries';

// Type-safe query key builders
interface QueryParams {
  [key: string]: any;
}

export const QUERY_KEYS = {
  // Properties domain
  properties: {
    all: () => ["properties"] as const,
    detail: (id: number) => ["properties", "detail", id] as const,
  },

  // Dashboard domain  
  dashboard: {
    data: (params?: QueryParams) => ["dashboard", "data", params] as const,
    previousPeriod: (params?: QueryParams) => ["dashboard", "previousPeriod", params] as const,
    rentTracker: (params?: QueryParams) => ["dashboard", "rentTracker", params] as const,
    dueInvoices: (params?: QueryParams) => ["dashboard", "dueInvoices", params] as const,
  },

  // Tenants domain
  tenants: {
    all: (params?: QueryParams) => ["tenants", "list", params] as const,
    detail: (id: number) => ["tenants", "detail", id] as const,
    count: (propertyId?: number) => ["tenants", "count", propertyId] as const,
    byProperty: (propertyId: number) => ["tenants", "byProperty", propertyId] as const,
  },

  // Leases domain
  leases: {
    all: (params?: LeasesQueryParams) => ["leases", "list", params] as const,
    detail: (id: number) => ["leases", "detail", id] as const,
    documents: (leaseId: number | null) => ["leases", "documents", leaseId] as const,
    withDocuments: (params?: LeasesQueryParams) => ["leases", "withDocuments", params] as const,
    unitStatus: (unitId: number) => ["leases", "unitStatus", unitId] as const,
  },

  // Accounting domain
  accounting: {
    overview: (params?: QueryParams) => ["accounting", "overview", params] as const,
    payments: (params?: QueryParams) => ["accounting", "payments", params] as const,
    outstandingPayments: (params?: QueryParams) => ["accounting", "outstandingPayments", params] as const,
    expenses: (params?: QueryParams) => ["accounting", "expenses", params] as const, 
    invoices: (params?: QueryParams) => ["accounting", "invoices", params] as const,
    invoice: (id: number) => ["accounting", "invoice", id] as const,
    insights: {
      occupancy: (params?: QueryParams) => ["accounting", "insights", "occupancy", params] as const,
      revenue: (params?: QueryParams) => ["accounting", "insights", "revenue", params] as const,
    },
    reports: (params?: QueryParams) => ["accounting", "reports", params] as const,
    rentTracker: (params?: QueryParams) => ["accounting", "rentTracker", params] as const,
  },

  // Units domain
  units: {
    all: (params?: QueryParams) => ["units", "list", params] as const,
    detail: (id: number) => ["units", "detail", id] as const,
  },

  // Maintenance domain
  maintenance: {
    requests: (params?: MaintenanceQueryParams) => ["maintenance", "requests", params] as const,
    summary: (params?: MaintenanceQueryParams) => ["maintenance", "summary", params] as const,
  },

  // Tenant Documents domain
  tenantDocuments: {
    all: () => ["tenantDocuments"] as const,
    lists: () => ["tenantDocuments", "list"] as const,
    list: (tenantId: number, filters?: QueryParams) => ["tenantDocuments", "list", tenantId, filters] as const,
    details: () => ["tenantDocuments", "detail"] as const,
    detail: (tenantId: number, documentId: string) => ["tenantDocuments", "detail", tenantId, documentId] as const,
    taxonomy: () => ["tenantDocuments", "taxonomy"] as const,
  },

  // Tenant Invitations domain
  tenantInvitations: {
    all: () => ["tenantInvitations"] as const,
    list: (params?: QueryParams) => ["tenantInvitations", "list", params] as const,
    forTenant: (tenantId: number) => ["tenantInvitations", "forTenant", tenantId] as const,
  },
} as const;

// Helper functions for query invalidation
export const getQueryKeyPattern = (domain: string, entity: string): readonly [string, string] => {
  return [domain, entity] as const;
};

export const getAllQueriesPattern = (domain: string): readonly [string] => {
  return [domain] as const;
};

