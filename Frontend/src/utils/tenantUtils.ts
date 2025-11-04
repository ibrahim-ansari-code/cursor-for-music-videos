import type { EnrichedTenant } from '../types/tenant';

interface TenantLike {
  id?: number;
  tenant_type?: string;
  company_name?: string;
  first_name?: string;
  last_name?: string;
  full_name?: string;
  name?: string;
  contact_person?: string;
}

/**
 * Get display name for a tenant
 * Handles both Company and Individual tenant types
 */
export const getTenantDisplayName = (tenant: TenantLike | null | undefined, fallback: string = 'N/A'): string => {
  if (!tenant) return fallback;
  
  // Check for company tenant (case-insensitive)
  if (tenant.tenant_type?.toLowerCase() === 'company' && tenant.company_name) {
    return tenant.company_name;
  }
  
  // Check for full_name
  if (tenant.full_name) return tenant.full_name;
  if (tenant.name) return tenant.name;
  
  // Build from first_name and last_name
  if (tenant.first_name || tenant.last_name) {
    return `${tenant.first_name || ''} ${tenant.last_name || ''}`.trim();
  }
  
  return fallback;
};

/**
 * Get initials for a tenant avatar
 * Handles both Company and Individual tenant types
 */
export const getTenantInitials = (tenant: TenantLike | null | undefined): string => {
  if (!tenant) return 'T';

  // For company tenants, use company name initials (case-insensitive)
  if (tenant.tenant_type?.toLowerCase() === 'company' && tenant.company_name) {
    return tenant.company_name
      .split(' ')
      .filter((n) => n.length > 0)
      .map((n) => n[0])
      .join('')
      .toUpperCase()
      .slice(0, 2) || 'C';
  }

  // Handle individual tenants with full_name
  if (tenant.full_name) {
    return tenant.full_name
      .split(' ')
      .filter((n) => n.length > 0)
      .map((n) => n[0])
      .join('')
      .toUpperCase()
      .slice(0, 2) || 'T';
  }

  // Build from first_name and last_name
  if (tenant.first_name && tenant.first_name.length > 0 && tenant.last_name && tenant.last_name.length > 0) {
    return (tenant.first_name[0] + tenant.last_name[0]).toUpperCase();
  }

  if (tenant.first_name && tenant.first_name.length > 0) return tenant.first_name[0].toUpperCase();
  if (tenant.last_name && tenant.last_name.length > 0) return tenant.last_name[0].toUpperCase();

  return 'T';
};

// Count active leases from tenant data
export const countActiveLeases = (tenantList: EnrichedTenant[] | null | undefined): number => {
  if (!tenantList) return 0;

  // Count unique tenants with at least one active lease
  const tenantsWithActiveLeases = tenantList.filter((tenant) => {
    if (!tenant.leases || tenant.leases.length === 0) {
      return false;
    }

    const today = new Date();

    // Check if any lease is active and current
    return tenant.leases.some((lease: any) => {
      const startDate = new Date(lease.start_date);
      const endDate = new Date(lease.end_date);
      return (
        lease.status?.toUpperCase() === "ACTIVE" &&
        startDate <= today &&
        endDate >= today
      );
    });
  });

  return tenantsWithActiveLeases.length;
};

interface ExpiringLease {
  tenantId: number;
  tenantName: string;
  leaseId: number;
  unitInfo: string;
  expiryDate: string;
  daysRemaining: number;
}

// Get leases expiring this month with details
export const getExpiringLeases = (tenantList: EnrichedTenant[] | null | undefined): ExpiringLease[] => {
  if (!tenantList) return [];

  const today = new Date();
  // Change from end of month to next 30 days
  const thirtyDaysFromNow = new Date(today);
  thirtyDaysFromNow.setDate(today.getDate() + 30);

  const expiringLeases: ExpiringLease[] = [];

  // Find all leases expiring in next 30 days
  tenantList.forEach((tenant) => {
    if (!tenant.leases || tenant.leases.length === 0) {
      return;
    }

    // Get expiring leases for this tenant
    tenant.leases.forEach((lease: any) => {
      const endDate = new Date(lease.end_date);

      if (
        endDate >= today &&
        endDate <= thirtyDaysFromNow &&
        lease.status?.toUpperCase() === "ACTIVE"
      ) {
        // Calculate days until expiration
        const daysUntilExpiration = Math.ceil(
          (endDate.getTime() - today.getTime()) / (1000 * 60 * 60 * 24)
        );

        expiringLeases.push({
          tenantId: tenant.id,
          tenantName: getTenantDisplayName(tenant, 'Unknown Tenant'),
          leaseId: lease.id,
          unitInfo: lease.unit
            ? `${lease.property?.name || ""}, Unit ${
                lease.unit?.unit_number || ""
              }`
            : lease.property?.name || "",
          expiryDate: lease.end_date,
          daysRemaining: daysUntilExpiration,
        });
      }
    });
  });

  // Sort by days remaining (ascending)
  return expiringLeases.sort((a, b) => a.daysRemaining - b.daysRemaining);
};

// Legacy alias for backward compatibility
export const getInitials = getTenantInitials;

// Format currency
export const formatCurrency = (amount: number | string | null | undefined): string => {
  if (amount === null || amount === undefined) return "--";
  return `$${parseFloat(amount.toString()).toLocaleString("en-US", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`;
};

// Format date
export const formatDate = (dateString: string | null | undefined): string => {
  if (!dateString) return "--";
  return new Date(dateString).toLocaleDateString();
};

// Get status badge class
export const getStatusBadgeClass = (status: string | null | undefined): string => {
  if (!status) return "bg-gray-200 text-gray-800";

  switch (status.toLowerCase()) {
    case "active":
      return "bg-green-100 text-green-800";
    case "inactive":
      return "bg-red-100 text-red-800";
    case "pending":
      return "bg-yellow-100 text-yellow-800";
    case "evicted":
      return "bg-red-100 text-red-800";
    case "moved out":
      return "bg-gray-100 text-gray-800";
    default:
      return "bg-gray-100 text-gray-800";
  }
};

