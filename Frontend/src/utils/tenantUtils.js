// Count active leases from tenant data
export const countActiveLeases = (tenantList) => {
    if (!tenantList) return 0;

    // Count unique tenants with at least one active lease
    const tenantsWithActiveLeases = tenantList.filter((tenant) => {
      if (!tenant.leases || tenant.leases.length === 0) {
        return false;
      }

      const today = new Date();

      // Check if any lease is active and current
      return tenant.leases.some((lease) => {
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

// Get leases expiring this month with details
export const getExpiringLeases = (tenantList) => {
    if (!tenantList) return [];

    const today = new Date();
    // Change from end of month to next 30 days
    const thirtyDaysFromNow = new Date(today);
    thirtyDaysFromNow.setDate(today.getDate() + 30);

    const expiringLeases = [];

    // Find all leases expiring in next 30 days
    tenantList.forEach((tenant) => {
      if (!tenant.leases || tenant.leases.length === 0) {
        return;
      }

      // Get expiring leases for this tenant
      tenant.leases.forEach((lease) => {
        const endDate = new Date(lease.end_date);

        if (
          endDate >= today &&
          endDate <= thirtyDaysFromNow &&
          lease.status?.toUpperCase() === "ACTIVE"
        ) {
          // Calculate days until expiration
          const daysUntilExpiration = Math.ceil(
            (endDate - today) / (1000 * 60 * 60 * 24)
          );

          expiringLeases.push({
            tenantId: tenant.id,
            tenantName: `${tenant.first_name} ${tenant.last_name}`,
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

// Generate initials for avatar
export const getInitials = (tenant) => {
    if (!tenant) return "--";

    // Check if we have first_name and last_name fields
    if (tenant.first_name || tenant.last_name) {
      const first = tenant.first_name ? tenant.first_name[0] : "";
      const last = tenant.last_name ? tenant.last_name[0] : "";
      return (first + last).toUpperCase();
    }

    // Fall back to full_name if that's what we have
    if (tenant.full_name) {
      return tenant.full_name
        .split(" ")
        .map((part) => part[0])
        .join("")
        .toUpperCase()
        .substring(0, 2);
    }

    return "--";
};

// Format currency
export const formatCurrency = (amount) => {
    if (amount === null || amount === undefined) return "--";
    return `$${parseFloat(amount).toLocaleString("en-US", {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    })}`;
};

// Format date
export const formatDate = (dateString) => {
    if (!dateString) return "--";
    return new Date(dateString).toLocaleDateString();
};

// Get status badge class
export const getStatusBadgeClass = (status) => {
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