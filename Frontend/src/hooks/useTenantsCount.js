import { useEffect, useState } from "react";
import { fetchTenants, fetchTenantsByProperty } from "../utils/api/index.js";

export default function useTenantsCount(selectedProperty, fallbackOccupiedUnits = 0) {
  const [count, setCount] = useState(0);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let isMounted = true;
    const load = async () => {
      try {
        setLoading(true);
        let total = 0;
        if (selectedProperty === "all") {
          const allTenants = await fetchTenants();
          total = Array.isArray(allTenants) ? allTenants.length : 0;
        } else {
          const propertyTenants = await fetchTenantsByProperty(selectedProperty);
          total = Array.isArray(propertyTenants) ? propertyTenants.length : 0;
        }
        if (isMounted) setCount(total);
      } catch (err) {
        if (isMounted) setCount(fallbackOccupiedUnits || 0);
      } finally {
        if (isMounted) setLoading(false);
      }
    };
    load();
    return () => {
      isMounted = false;
    };
  }, [selectedProperty, fallbackOccupiedUnits]);

  return { count, loading };
}
