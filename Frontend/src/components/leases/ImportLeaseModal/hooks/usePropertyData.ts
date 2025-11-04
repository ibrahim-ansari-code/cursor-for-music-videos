import { useState, useCallback } from "react";
import * as Sentry from "@sentry/react";
import {
  fetchProperties,
  fetchTenants,
  fetchPropertyUnits,
  fetchLeases,
} from "../../../../utils/api";
import type { Lease, Property } from "../../../../types/lease";
import type { Tenant } from "../../../../types/tenant";
import type { Unit } from "../types";

interface UsePropertyDataReturn {
  properties: Property[];
  availableUnits: Unit[];
  availableTenants: Tenant[];
  isLoadingUnits: boolean;
  isLoadingTenants: boolean;
  loadProperties: () => Promise<void>;
  loadUnitsForProperty: (propertyId: number) => Promise<void>;
  loadTenantsForProperty: (propertyId: number) => Promise<Tenant[]>;
  setError: (error: string | null) => void;
}

export const usePropertyData = (): UsePropertyDataReturn => {
  const [properties, setProperties] = useState<Property[]>([]);
  const [availableUnits, setAvailableUnits] = useState<Unit[]>([]);
  const [availableTenants, setAvailableTenants] = useState<Tenant[]>([]);
  const [isLoadingUnits, setIsLoadingUnits] = useState(false);
  const [isLoadingTenants, setIsLoadingTenants] = useState(false);
  const [, setError] = useState<string | null>(null);
 
  const loadProperties = useCallback(async () => {
    try {
      const data = await fetchProperties();
      setProperties(data || []);
    } catch (err: any) {
      Sentry.logger.error("Failed to fetch properties", {
        error: err.message,
        component: 'ImportLeaseModal',
      });
      setError("Could not load properties.");
    }
  }, []);

  const loadTenantsForProperty = useCallback(async (propertyId: number): Promise<Tenant[]> => {
    if (!propertyId) {
      setAvailableTenants([]);
      return [];
    }
    setIsLoadingTenants(true);
    try {
      const tenants = await fetchTenants({ unassigned_only: true });
      setAvailableTenants(tenants || []);
      return tenants || [];
    } catch (err: any) {
      Sentry.logger.error("Failed to load available tenants", {
        error: err.message,
        propertyId,
        component: 'ImportLeaseModal',
      });
      setError("Could not load available tenants.");
      setAvailableTenants([]);
      return [];
    } finally {
      setIsLoadingTenants(false);
    }
  }, []);

  const loadUnitsForProperty = useCallback(async (propertyId: number) => {
    if (!propertyId) {
      setAvailableUnits([]);
      return;
    }
    setIsLoadingUnits(true);
    try {
      // Fetch all units for the property
      const unitsData = (await fetchPropertyUnits(propertyId)) as Unit[];

      // Fetch active leases to filter available units
      const activeLeases = (await fetchLeases({
        property_id: propertyId,
        status: "ACTIVE",
      })) as Lease[];
      const activeLeaseUnitIds = new Set(
        activeLeases.map((lease) => lease.unit_id).filter((id): id is number => id != null && id !== undefined)
      );

      const available = (unitsData || []).filter(
        (unit) => !activeLeaseUnitIds.has(unit.id)
      );
      setAvailableUnits(available);
    } catch (err: any) {
      Sentry.logger.error("Failed to load units", {
        error: err.message,
        propertyId,
        component: 'ImportLeaseModal',
      });
      setError("Failed to load unit information.");
      setAvailableUnits([]);
    } finally {
      setIsLoadingUnits(false);
    }
  }, []);

  return {
    properties,
    availableUnits,
    availableTenants,
    isLoadingUnits,
    isLoadingTenants,
    loadProperties,
    loadUnitsForProperty,
    loadTenantsForProperty,
    setError,
  };
};

