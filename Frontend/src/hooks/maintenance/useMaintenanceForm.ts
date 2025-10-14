import { useState, useCallback, useEffect } from 'react';
import type { MaintenanceFormData, MaintenanceRequest } from '../../types/tenant';

interface UseMaintenanceFormProps {
  mode: 'create' | 'edit' | 'view';
  initialData?: MaintenanceRequest | null;
  onSuccess?: (data: any) => Promise<void>;
}

const initialFormState: MaintenanceFormData = {
  issue_title: '',
  description: '',
  priority: 'Medium',
  status: 'Pending',
  property_id: '',
  unit_id: '',
  tenant_id: '',
  assigned_to: '',
  scheduled_date: '',
  estimated_cost: '',
  photos: [],
};

export const useMaintenanceForm = ({
  mode: _mode,
  initialData,
  onSuccess,
}: UseMaintenanceFormProps) => {
  // Initialize form data
  const [formData, setFormData] = useState<MaintenanceFormData>(initialFormState);

  // Update form data when initialData changes (important for pre-population)
  useEffect(() => {
    if (!initialData) {
      setFormData(initialFormState);
      return;
    }

    // Handle scheduled_date formatting
    const scheduledDate = initialData.scheduled_date
      ? new Date(initialData.scheduled_date).toISOString().split('T')[0]
      : '';

    setFormData({
      issue_title: initialData.issue_title || '',
      description: initialData.description || '',
      priority: initialData.priority || 'Medium',
      status: initialData.status || 'Pending',
      // Support both nested objects (editing) and direct IDs (pre-population)
      property_id: initialData.property?.id?.toString() || initialData.property_id?.toString() || '',
      unit_id: initialData.unit?.id?.toString() || initialData.unit_id?.toString() || '',
      tenant_id: initialData.tenant?.id?.toString() || initialData.tenant_id?.toString() || '',
      assigned_to: initialData.assigned_to || '',
      scheduled_date: scheduledDate,
      estimated_cost: initialData.estimated_cost?.toString() || '',
      photos: initialData.photos || [],
    });
  }, [initialData]);

  const [errors, setErrors] = useState<Record<string, string>>({});
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Validation function for individual fields
  const validateField = useCallback((name: string, value: any): string | null => {
    switch (name) {
      case 'issue_title':
        if (!value || value.trim() === '') {
          return 'Issue title is required';
        }
        break;
      case 'property_id':
        if (!value) {
          return 'Property is required';
        }
        break;
      case 'estimated_cost':
        if (value) {
          const numValue = Number(value);
          if (isNaN(numValue) || numValue <= 0) {
            return 'Estimated cost must be a positive number';
          }
        }
        break;
      case 'scheduled_date':
        if (value) {
          const today = new Date();
          today.setHours(0, 0, 0, 0);
          const scheduledDate = new Date(`${value}T00:00:00`);

          if (isNaN(scheduledDate.getTime())) {
            return 'Invalid date format';
          }
          if (scheduledDate < today) {
            return 'Scheduled date cannot be in the past';
          }
        }
        break;
      default:
        break;
    }
    return null;
  }, []);

  // Update a single field
  const updateField = useCallback(<K extends keyof MaintenanceFormData>(
    field: K,
    value: MaintenanceFormData[K]
  ) => {
    setFormData(prev => ({ ...prev, [field]: value }));

    // Clear or set error for this field
    const error = validateField(field, value);
    setErrors(prev => {
      const updated = { ...prev };
      if (error) {
        updated[field] = error;
      } else {
        delete updated[field];
      }
      return updated;
    });
  }, [validateField]);

  // Validate entire form
  const validateForm = useCallback((): boolean => {
    const newErrors: Record<string, string> = {};

    // Required fields
    const requiredFields: (keyof MaintenanceFormData)[] = ['issue_title', 'property_id'];

    requiredFields.forEach((fieldName) => {
      const error = validateField(fieldName, formData[fieldName]);
      if (error) {
        newErrors[fieldName] = error;
      }
    });

    // Validate optional fields that have values
    const optionalFields: (keyof MaintenanceFormData)[] = ['estimated_cost', 'scheduled_date'];
    optionalFields.forEach((fieldName) => {
      if (formData[fieldName]) {
        const error = validateField(fieldName, formData[fieldName]);
        if (error) {
          newErrors[fieldName] = error;
        }
      }
    });

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  }, [formData, validateField]);

  // Submit form
  const submitForm = useCallback(async () => {
    if (!validateForm()) {
      setErrors(prev => ({ ...prev, submit: 'Please correct the highlighted fields.' }));
      return;
    }

    setIsSubmitting(true);
    try {
      // Prepare payload with proper type conversions
      const payload = {
        issue_title: formData.issue_title.trim(),
        description: formData.description && formData.description.trim() !== ''
          ? formData.description.trim()
          : null,
        priority: formData.priority,
        status: formData.status,
        property_id: formData.property_id ? Number(formData.property_id) : null,
        unit_id: formData.unit_id && formData.unit_id !== '' && formData.unit_id !== 'common_area'
          ? Number(formData.unit_id)
          : null,
        tenant_id: formData.tenant_id && formData.tenant_id !== ''
          ? Number(formData.tenant_id)
          : null,
        assigned_to: formData.assigned_to && formData.assigned_to.trim() !== ''
          ? formData.assigned_to.trim()
          : null,
        scheduled_date: formData.scheduled_date && formData.scheduled_date.trim() !== ''
          ? formData.scheduled_date
          : null,
        estimated_cost: formData.estimated_cost && formData.estimated_cost !== ''
          ? Number(formData.estimated_cost)
          : null,
        photos: formData.photos && formData.photos.length > 0
          ? formData.photos
          : null,
      };

      if (onSuccess) {
        await onSuccess(payload);
      }
    } catch (err: any) {
      setErrors(prev => ({ ...prev, submit: err?.message || 'Failed to save the request.' }));
      throw err;
    } finally {
      setIsSubmitting(false);
    }
  }, [formData, validateForm, onSuccess]);

  // Reset form to initial state - useCallback ensures stable reference
  const resetForm = useCallback(() => {
    setFormData(initialFormState);
    setErrors({});
    setIsSubmitting(false);
  }, []); // Empty deps - uses initial state, no external dependencies

  return {
    formData,
    errors,
    isSubmitting,
    updateField,
    submitForm,
    resetForm,
    validateForm,
  };
};
