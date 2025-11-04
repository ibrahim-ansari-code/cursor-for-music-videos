import { useState, useCallback } from "react";
import * as Sentry from "@sentry/react";
import { useCreateLease } from "../../../../hooks/useLeasesQueries";
import { LeaseStatus } from "../../../../types/lease";
import type { Lease } from "../../../../types/lease";
import type { Tenant } from "../../../../types/tenant";
import type { FormData, FieldErrors } from "../types";

interface UseLeaseFormProps {
  initialPropertyId?: number | null;
  initialUnitId?: number | null;
  initialUnitName?: string;
  mode: 'file' | 'manual';
  onSuccess: (lease: Lease) => void;
}

interface UseLeaseFormReturn {
  formData: FormData;
  fieldErrors: FieldErrors;
  error: string | null;
  isLoading: boolean;
  selectedTenant: Tenant | null;
  setFormData: React.Dispatch<React.SetStateAction<FormData>>;
  setFieldErrors: React.Dispatch<React.SetStateAction<FieldErrors>>;
  setError: (error: string | null) => void;
  setSelectedTenant: (tenant: Tenant | null) => void;
  handleFormChange: (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => void;
  handlePropertyChange: (value: string, onPropertyChange: (propertyId: number) => void) => void;
  handleUnitChange: (value: string) => void;
  handleTenantChange: (value: string, availableTenants: Tenant[]) => void;
  updateFormData: (updates: Partial<FormData>) => void;
  validateForm: () => FieldErrors;
  submitLease: (parsedFileUrl: string | null) => Promise<void>;
  resetForm: () => void;
}

const getInitialFormData = (
  initialPropertyId?: number | null,
  initialUnitId?: number | null,
  initialUnitName?: string
): FormData => ({
  property_id: initialPropertyId?.toString() || "",
  unit_id: initialUnitId?.toString() || "",
  unit_name: initialUnitName || "",
  tenant_id: null,
  monthly_rent: "",
  security_deposit: "",
  start_date: "",
  end_date: "",
  rent_due_day: "1",
  late_fee_amount: "",
  late_fee_after_days: "",
  special_terms: "",
});

export const useLeaseForm = ({
  initialPropertyId,
  initialUnitId,
  initialUnitName,
  mode,
  onSuccess,
}: UseLeaseFormProps): UseLeaseFormReturn => {
  const [formData, setFormData] = useState<FormData>(
    getInitialFormData(initialPropertyId, initialUnitId, initialUnitName)
  );
  const [fieldErrors, setFieldErrors] = useState<FieldErrors>({});
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [selectedTenant, setSelectedTenant] = useState<Tenant | null>(null);

  const createLeaseMutation = useCreateLease();

  const handleFormChange = useCallback((e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    const { name, value } = e.target;
    
    // Clear field error when user starts typing
    setFieldErrors(prev => {
      if (prev[name as keyof FieldErrors]) {
        const updated = { ...prev };
        delete updated[name as keyof FieldErrors];
        return updated;
      }
      return prev;
    });

    setFormData(prev => ({ ...prev, [name]: value }));
  }, []);

  const handlePropertyChange = useCallback((value: string, onPropertyChange: (propertyId: number) => void) => {
    // Clear field error
    setFieldErrors(prev => {
      if (prev.property_id) {
        const updated = { ...prev };
        delete updated.property_id;
        return updated;
      }
      return prev;
    });

    const propertyId = parseInt(value);
    if (propertyId) {
      onPropertyChange(propertyId);
    }
    setFormData(prev => ({ 
      ...prev, 
      property_id: value, 
      unit_id: "", 
      unit_name: "",
      tenant_id: null
    }));
    setSelectedTenant(null);
  }, []);

  const handleUnitChange = useCallback((value: string) => {
    setFieldErrors(prev => {
      if (prev.unit_id) {
        const updated = { ...prev };
        delete updated.unit_id;
        return updated;
      }
      return prev;
    });

    setFormData(prev => ({ ...prev, unit_id: value }));
  }, []);

  const handleTenantChange = useCallback((value: string, availableTenants: Tenant[]) => {
    setFieldErrors(prev => {
      if (prev.tenant_id) {
        const updated = { ...prev };
        delete updated.tenant_id;
        return updated;
      }
      return prev;
    });

    const tenantId = parseInt(value, 10);
    
    // Guard against NaN
    if (isNaN(tenantId)) {
      setSelectedTenant(null);
      setFormData(prev => ({ ...prev, tenant_id: null }));
      return;
    }
    
    const tenant = availableTenants.find(t => t.id === tenantId);
    
    setSelectedTenant(tenant || null);
    setFormData(prev => ({ ...prev, tenant_id: tenantId }));
  }, []);

  const updateFormData = useCallback((updates: Partial<FormData>) => {
    setFormData(prev => ({ ...prev, ...updates }));
  }, []);

  const validateForm = useCallback((): FieldErrors => {
    const errors: FieldErrors = {};

    if (!formData.property_id) errors.property_id = "Property is required";
    if (!formData.unit_id && mode !== 'manual') errors.unit_id = "Unit is required";
    if (!formData.tenant_id) errors.tenant_id = "Tenant is required";
    if (!formData.start_date) errors.start_date = "Start date is required";
    if (!formData.end_date) errors.end_date = "End date is required";
    if (!formData.monthly_rent) errors.monthly_rent = "Monthly rent is required";
    if (!formData.security_deposit) errors.security_deposit = "Security deposit is required";

    // Date validation
    if (formData.start_date && formData.end_date) {
      const start = new Date(formData.start_date);
      const end = new Date(formData.end_date);
      if (start > end) {
        errors.end_date = "End date must be after start date";
      }
    }

    return errors;
  }, [formData, mode]);

  const submitLease = useCallback(async (parsedFileUrl: string | null) => {
    // Validate form
    const errors = validateForm();
    if (Object.keys(errors).length > 0) {
      setFieldErrors(errors);
      setError("Please correct the validation errors below.");
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      // Prepare lease data with NaN checks
      const parseIntSafe = (value: string): number | null => {
        const parsed = Number.parseInt(value);
        return isNaN(parsed) ? null : parsed;
      };
      
      const parseFloatSafe = (value: string): number | null => {
        const parsed = Number.parseFloat(value);
        return isNaN(parsed) ? null : parsed;
      };

      const leaseData = {
        property_id: parseIntSafe(formData.property_id)!,
        unit_id: formData.unit_id ? parseIntSafe(formData.unit_id) : null,
        tenant_id: formData.tenant_id!,
        start_date: formData.start_date,
        end_date: formData.end_date,
        monthly_rent: parseFloatSafe(formData.monthly_rent)!,
        security_deposit: parseFloatSafe(formData.security_deposit)!,
        rent_due_day: parseIntSafe(formData.rent_due_day || '1') || undefined,
        late_fee_amount: formData.late_fee_amount ? parseFloatSafe(formData.late_fee_amount) : null,
        late_fee_after_days: formData.late_fee_after_days ? parseIntSafe(formData.late_fee_after_days) : null,
        special_terms: formData.special_terms || null,
        status: LeaseStatus.ACTIVE,
        file_url: parsedFileUrl,
      };

      Sentry.logger.info("Creating lease", { 
        propertyId: leaseData.property_id,
        tenantId: leaseData.tenant_id,
        hasFileUrl: !!parsedFileUrl,
      });

      const createdLease = await createLeaseMutation.mutateAsync(leaseData);
      
      Sentry.logger.info("Lease created successfully", { 
        leaseId: createdLease.id,
        status: createdLease.status,
      });

      onSuccess(createdLease);
    } catch (err: any) {
      Sentry.logger.error("Failed to create lease", {
        error: err.message,
        propertyId: formData.property_id,
        tenantId: formData.tenant_id,
      });

      Sentry.captureException(err, {
        tags: {
          component: 'ImportLeaseModal',
          action: 'create_lease',
          feature: 'leases',
          mode,
        },
        contexts: {
          formData: {
            property_id: formData.property_id,
            tenant_id: formData.tenant_id,
          },
        },
      });

      setError(err.message || "Failed to create lease. Please try again.");
    } finally {
      setIsLoading(false);
    }
  }, [formData, mode, validateForm, createLeaseMutation, onSuccess]);

  const resetForm = useCallback(() => {
    setFormData(getInitialFormData(initialPropertyId, initialUnitId, initialUnitName));
    setFieldErrors({});
    setError(null);
    setSelectedTenant(null);
  }, [initialPropertyId, initialUnitId, initialUnitName]);

  return {
    formData,
    fieldErrors,
    error,
    isLoading,
    selectedTenant,
    setFormData,
    setFieldErrors,
    setError,
    setSelectedTenant,
    handleFormChange,
    handlePropertyChange,
    handleUnitChange,
    handleTenantChange,
    updateFormData,
    validateForm,
    submitLease,
    resetForm,
  };
};

