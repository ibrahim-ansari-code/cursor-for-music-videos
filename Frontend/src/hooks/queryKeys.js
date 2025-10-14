// Centralized query key management for consistent caching
// Following TanStack Query best practices: hierarchical keys

export const QUERY_KEYS = {
  // Properties domain
  properties: {
    all: () => ["properties"],
    detail: (id) => ["properties", "detail", id],
  },

  // Dashboard domain  
  dashboard: {
    data: (params) => ["dashboard", "data", params],
    previousPeriod: (params) => ["dashboard", "previousPeriod", params],
    rentTracker: (params) => ["dashboard", "rentTracker", params],
    dueInvoices: (params) => ["dashboard", "dueInvoices", params],
  },

  // Tenants domain
  tenants: {
    all: (params) => ["tenants", "list", params],
    detail: (id) => ["tenants", "detail", id],
    count: (propertyId) => ["tenants", "count", propertyId],
    byProperty: (propertyId) => ["tenants", "byProperty", propertyId],
  },

  // Leases domain
  leases: {
    all: (params) => ["leases", "list", params],
    detail: (id) => ["leases", "detail", id],
    documents: (leaseId) => ["leases", "documents", leaseId],
    withDocuments: (params) => ["leases", "withDocuments", params],
    unitStatus: (unitId) => ["leases", "unitStatus", unitId],
  },

  // Accounting domain
  accounting: {
    overview: (params) => ["accounting", "overview", params],
    payments: (params) => ["accounting", "payments", params],
    outstandingPayments: (params) => ["accounting", "outstandingPayments", params],
    expenses: (params) => ["accounting", "expenses", params], 
    invoices: (params) => ["accounting", "invoices", params],
    invoice: (id) => ["accounting", "invoice", id],
    insights: {
      occupancy: (params) => ["accounting", "insights", "occupancy", params],
      revenue: (params) => ["accounting", "insights", "revenue", params],
    },
    reports: (params) => ["accounting", "reports", params],
    rentTracker: (params) => ["accounting", "rentTracker", params],
  },

  // Units domain
  units: {
    all: (params) => ["units", "list", params],
    detail: (id) => ["units", "detail", id],
  },

  // Maintenance domain
  maintenance: {
    requests: (params) => ["maintenance", "requests", params],
    summary: (params) => ["maintenance", "summary", params],
  },
};

// Helper functions for query invalidation
export const getQueryKeyPattern = (domain, entity) => {
  return [domain, entity];
};

export const getAllQueriesPattern = (domain) => {
  return [domain];
};
