import { useMemo } from 'react';

/**
 * Custom hook to filter tenants based on various criteria
 * @param {Array} tenants - Array of tenant objects with their leases
 * @param {string|null} filter - Active filter ('active_leases', 'expiring', 'overdue', or null)
 * @param {Array} expiringLeases - Array of expiring lease objects
 * @param {Array} outstandingPayments - Array of outstanding payment objects
 * @returns {Array} Filtered array of tenants
 */
const useFilteredTenants = (tenants, filter, expiringLeases = [], outstandingPayments = []) => {
  return useMemo(() => {
    if (!filter) return tenants;

    const today = new Date();

    switch (filter) {
      case 'active_leases':
        return tenants.filter(tenant => {
          if (!tenant.leases || tenant.leases.length === 0) {
            return false;
          }
          // Check if tenant has at least one active and current lease
          return tenant.leases.some(lease => {
            const startDate = new Date(lease.start_date);
            const endDate = new Date(lease.end_date);
            endDate.setHours(23, 59, 59, 999); // Set to end of day
            return (
              lease.status?.toUpperCase() === "ACTIVE" &&
              startDate <= today &&
              endDate >= today
            );
          });
        });
      case 'expiring':
        const expiringTenantIds = new Set(expiringLeases.map(l => l.tenantId));
        return tenants.filter(tenant => expiringTenantIds.has(tenant.id));
      case 'overdue':
        const overdueTenantIds = new Set(
          outstandingPayments?.map(p => p.tenant_id) || []
        );
        return tenants.filter(tenant => overdueTenantIds.has(tenant.id));
      default:
        return tenants;
    }
  }, [tenants, filter, expiringLeases, outstandingPayments]);
};

export default useFilteredTenants;
