import { useState, useCallback, useMemo, useEffect } from 'react';
import { toast } from 'react-toastify';
import Decimal from 'decimal.js';
import { createInvoice, updateInvoice, getUserTaxDefault, clearUserTaxDefault } from '../../utils/api/accounting';
import type { 
  InvoiceFormData, 
  CreateInvoiceRequest, 
  UpdateInvoiceRequest,
  TaxDetail,
  InvoiceStatus 
} from '../../types/accounting';
import { reportError, reportWarning } from '../../utils/error-reporting';

interface UseInvoiceFormProps {
  initialData?: Partial<InvoiceFormData>;
  mode?: 'create' | 'edit';
  onSuccess?: () => void;
}

interface InvoiceFormState {
  formData: InvoiceFormData;
  errors: Record<string, string>;
  isSubmitting: boolean;
  calculatedTotals: {
    subtotal: Decimal;
    totalTax: Decimal;
    grandTotal: Decimal;
  };
  isUserDefaultTax: boolean;
}

interface InvoiceFormActions {
  updateField: <K extends keyof InvoiceFormData>(field: K, value: InvoiceFormData[K]) => void;
  updateTaxes: (taxes: TaxDetail[]) => void;
  addTaxLine: () => void;
  removeTaxLine: (index: number) => void;
  updateTaxLine: (index: number, field: keyof TaxDetail, value: string) => void;
  validateForm: () => boolean;
  submitForm: () => Promise<boolean>;
  resetForm: () => void;
  setFormData: (data: Partial<InvoiceFormData>) => void;
  clearUserTaxDefaultFromForm: () => Promise<void>;
  setIsUserDefaultTax: (isDefault: boolean) => void;
}

const createInitialFormData = (): InvoiceFormData => ({
  invoice_number: "",
  amount: "",
  description: "",
  issue_date: new Date().toISOString().split("T")[0],
  due_date: "",
  status: "Pending" as InvoiceStatus,
  property_id: "",
  property_name: "",
  tenant_id: "",
  tenant_name: "",
  taxes: [{ tax_name: "", tax_rate: "" }],
});

export const useInvoiceForm = ({ 
  initialData, 
  mode = 'create', 
  onSuccess 
}: UseInvoiceFormProps): InvoiceFormState & InvoiceFormActions => {
  const [formData, setFormDataState] = useState<InvoiceFormData>(() => ({
    ...createInitialFormData(),
    ...initialData,
  }));
  
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isUserDefaultTax, setIsUserDefaultTax] = useState(false);
  
  const loadUserTaxDefault = useCallback(async () => {
    try {
      const userTaxDefault = await getUserTaxDefault();
      if (userTaxDefault && userTaxDefault.tax_name && userTaxDefault.tax_rate) {
        setFormDataState(prev => ({
          ...prev,
          taxes: [{
            tax_name: userTaxDefault.tax_name,
            tax_rate: userTaxDefault.tax_rate,
          }],
        }));
        setIsUserDefaultTax(true);
      }
    } catch (error) {
      // Silently fail - user just won't get pre-populated tax defaults
      console.log('No user tax default found or error loading:', error);
    }
  }, []);

  // Load user's default tax rate on mount for new invoices
  useEffect(() => {
    if (mode === 'create' && !initialData?.taxes) {
      loadUserTaxDefault();
    }
  }, [mode, initialData, loadUserTaxDefault]);

  // Calculate totals based on current form data
  const calculatedTotals = useMemo(() => {
    const subtotal = new Decimal(formData.amount || 0);
    
    const totalTax = formData.taxes.reduce((acc, tax) => {
      if (tax.tax_name && tax.tax_rate) {
        const rate = new Decimal(tax.tax_rate);
        const taxAmount = subtotal.mul(rate).div(100);
        return acc.add(taxAmount);
      }
      return acc;
    }, new Decimal(0));

    const grandTotal = subtotal.add(totalTax);

    return {
      subtotal,
      totalTax,
      grandTotal,
    };
  }, [formData.amount, formData.taxes]);

  const updateField = useCallback(<K extends keyof InvoiceFormData>(
    field: K, 
    value: InvoiceFormData[K]
  ) => {
    setFormDataState(prev => ({
      ...prev,
      [field]: value,
    }));

    // Clear field error when user starts typing
    if (errors[field as string]) {
      setErrors(prev => {
        const newErrors = { ...prev };
        delete newErrors[field as string];
        return newErrors;
      });
    }
  }, [errors]);

  const setFormData = useCallback((data: Partial<InvoiceFormData>) => {
    setFormDataState(prev => ({
      ...prev,
      ...data,
    }));
  }, []);

  const updateTaxes = useCallback((taxes: TaxDetail[]) => {
    setFormDataState(prev => ({
      ...prev,
      taxes: taxes.length > 0 ? taxes : [{ tax_name: "", tax_rate: "" }],
    }));
  }, []);

  const addTaxLine = useCallback(() => {
    setFormDataState(prev => ({
      ...prev,
      taxes: [...prev.taxes, { tax_name: "", tax_rate: "" }],
    }));
  }, []);

  const removeTaxLine = useCallback((index: number) => {
    setFormDataState(prev => ({
      ...prev,
      taxes: prev.taxes.length > 1 
        ? prev.taxes.filter((_, i) => i !== index)
        : prev.taxes, // Keep at least one tax line
    }));
  }, []);

  const updateTaxLine = useCallback((
    index: number, 
    field: keyof TaxDetail, 
    value: string
  ) => {
    setFormDataState(prev => ({
      ...prev,
      taxes: prev.taxes.map((tax, i) => 
        i === index ? { ...tax, [field]: value } : tax
      ),
    }));
  }, []);

  const validateForm = useCallback((): boolean => {
    const newErrors: Record<string, string> = {};

    // Required field validations
    if (!formData.invoice_number?.trim()) {
      newErrors.invoice_number = 'Invoice number is required';
    }

    const amountValue = typeof formData.amount === 'number' ? formData.amount : parseFloat(formData.amount || '0');
    if (!formData.amount || isNaN(amountValue) || amountValue <= 0) {
      newErrors.amount = 'Amount must be greater than 0';
    }

    if (!formData.description?.trim()) {
      newErrors.description = 'Description is required';
    }

    if (!formData.issue_date) {
      newErrors.issue_date = 'Issue date is required';
    }

    if (!formData.due_date) {
      newErrors.due_date = 'Due date is required';
    }

    // Date validation
    if (formData.issue_date && formData.due_date) {
      const issueDate = new Date(formData.issue_date);
      const dueDate = new Date(formData.due_date);
      
      if (dueDate < issueDate) {
        newErrors.due_date = 'Due date cannot be before issue date';
      }
    }

    // Property/Tenant validation - property is optional
    // No validation required for property_id as it's optional

    // Tax validation  
    formData.taxes.forEach((tax, index) => {
      if (tax.tax_name && !tax.tax_rate) {
        newErrors[`tax_rate_${index}`] = 'Tax rate is required';
      }
      
      if (tax.tax_rate && (!tax.tax_name || !tax.tax_name.trim())) {
        newErrors[`tax_name_${index}`] = 'Tax name is required';
      }

      if (tax.tax_rate) {
        const rate = parseFloat(tax.tax_rate);
        if (isNaN(rate) || rate < 0 || rate > 100) {
          newErrors[`tax_rate_${index}`] = 'Tax rate must be between 0% and 100%';
        }
      }
    });

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  }, [formData]);

  const submitForm = useCallback(async (): Promise<boolean> => {
    if (!validateForm()) {
      toast.error('Please fix the form errors before submitting');
      return false;
    }

    setIsSubmitting(true);

    try {
      // Filter out empty tax entries
      const validTaxes = formData.taxes.filter(tax => {
        if (!tax.tax_name || !tax.tax_rate) return false;
        const rate = parseFloat(tax.tax_rate);
        return !isNaN(rate) && rate > 0;
      });

      const submitData = {
        invoice_number: formData.invoice_number,
        amount: calculatedTotals.grandTotal.toFixed(2),
        description: formData.description,
        issue_date: formData.issue_date,
        due_date: formData.due_date,
        status: formData.status,
        property_id: formData.property_id && formData.property_id.toString().trim() ? parseInt(formData.property_id.toString(), 10) : undefined,
        tenant_id: formData.tenant_id && formData.tenant_id.toString().trim() ? parseInt(formData.tenant_id.toString(), 10) : undefined,
        taxes: validTaxes.length > 0 ? validTaxes : undefined,
      };

      let response;
      if (mode === 'create') {
        response = await createInvoice(submitData as CreateInvoiceRequest);
      } else {
        if (!formData.id) {
          throw new Error('Invoice ID required for update');
        }
        response = await updateInvoice(
          formData.id && formData.id.toString().trim() ? parseInt(formData.id.toString(), 10) : 0,
          submitData as UpdateInvoiceRequest
        );
      }

      if (response) {
        toast.success(`Invoice ${mode === 'create' ? 'created' : 'updated'} successfully`);
        onSuccess?.();
        return true;
      } else {
        throw new Error(`Failed to ${mode} invoice`);
      }
    } catch (error) {
      console.error(`Error ${mode === 'create' ? 'creating' : 'updating'} invoice:`, error);
      
      // Report invoice form submission errors with financial tagging
      const errorToReport = error instanceof Error ? error : new Error(String(error));
      reportError(errorToReport, {
        component: 'useInvoiceForm',
        action: mode === 'create' ? 'create_invoice' : 'update_invoice',
        tags: {
          financial: true,
        },
        extra: {
          invoice: {
            mode,
            propertyId: formData.property_id,
            tenantId: formData.tenant_id,
            amount: formData.amount,
            taxesCount: formData.taxes?.length || 0,
          }
        },
      }, 'error');
      
      toast.error(error instanceof Error ? error.message : `Failed to ${mode} invoice`);
      return false;
    } finally {
      setIsSubmitting(false);
    }
  }, [formData, calculatedTotals, validateForm, mode, onSuccess]);

  const clearUserTaxDefaultFromForm = useCallback(async () => {
    try {
      await clearUserTaxDefault();
      // Clear the tax from the form and reset the user default flag
      setFormDataState(prev => ({
        ...prev,
        taxes: [{ tax_name: "", tax_rate: "" }],
      }));
      setIsUserDefaultTax(false);
      toast.success('Tax default removed');
    } catch (error) {
      console.error('Error clearing user tax default:', error);
      
      // Report tax default clearing errors with financial context
      reportWarning(error instanceof Error ? error : new Error(String(error)), {
        component: 'useInvoiceForm',
        action: 'clear_tax_default',
        tags: {
          financial: true,
        },
      });
      
      toast.error('Failed to clear tax default');
    }
  }, []);

  const resetForm = useCallback(() => {
    setFormDataState(createInitialFormData());
    setErrors({});
    setIsUserDefaultTax(false);
  }, []);

  return {
    // State
    formData,
    errors,
    isSubmitting,
    calculatedTotals,
    isUserDefaultTax,
    
    // Actions
    updateField,
    updateTaxes,
    addTaxLine,
    removeTaxLine,
    updateTaxLine,
    validateForm,
    submitForm,
    resetForm,
    setFormData,
    clearUserTaxDefaultFromForm,
    setIsUserDefaultTax,
  };
};