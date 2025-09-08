import { useState, useCallback, useMemo, useEffect } from 'react';
import { toast } from 'react-toastify';
import Decimal from 'decimal.js';
import { createExpense, updateExpense, getUserTaxDefault, clearUserTaxDefault } from '../../utils/api/accounting';
import type { 
  ExpenseFormData, 
  CreateExpenseRequest, 
  UpdateExpenseRequest,
  TaxDetail} from '../../types/accounting';

interface UseExpenseFormProps {
  initialData?: Partial<ExpenseFormData>;
  mode?: 'create' | 'edit';
  onSuccess?: () => void;
}

interface ExpenseFormState {
  formData: ExpenseFormData;
  errors: Record<string, string>;
  isSubmitting: boolean;
  calculatedTotals: {
    subtotal: Decimal;
    totalTax: Decimal;
    grandTotal: Decimal;
  };
  isUserDefaultTax: boolean;
}

interface ExpenseFormActions {
  updateField: <K extends keyof ExpenseFormData>(field: K, value: ExpenseFormData[K]) => void;
  updateTaxes: (taxes: TaxDetail[]) => void;
  addTaxLine: () => void;
  removeTaxLine: (index: number) => void;
  updateTaxLine: (index: number, field: keyof TaxDetail, value: string) => void;
  validateForm: () => boolean;
  submitForm: () => Promise<boolean>;
  resetForm: () => void;
  setFormData: (data: Partial<ExpenseFormData>) => void;
  clearUserTaxDefaultFromForm: () => Promise<void>;
  setIsUserDefaultTax: (isDefault: boolean) => void;
}

const createInitialFormData = (): ExpenseFormData => ({
  property_id: "",
  property_name: "",
  category: "",
  amount: "",
  expense_date: new Date().toISOString().split("T")[0],
  description: "",
  payment_method: "",
  receipt_url: null,
  taxes: [{ tax_name: "", tax_rate: "" }],
});

export const useExpenseForm = ({ 
  initialData, 
  mode = 'create', 
  onSuccess 
}: UseExpenseFormProps): ExpenseFormState & ExpenseFormActions => {
  const [formData, setFormDataState] = useState<ExpenseFormData>(() => ({
    ...createInitialFormData(),
    ...initialData,
  }));
  
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isUserDefaultTax, setIsUserDefaultTax] = useState(false);
  
  // Load user's default tax rate on mount for new expenses
  useEffect(() => {
    if (mode === 'create' && !initialData?.taxes) {
      loadUserTaxDefault();
    }
  }, [mode, initialData]);

  const loadUserTaxDefault = async () => {
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
  };

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

  const updateField = useCallback(<K extends keyof ExpenseFormData>(
    field: K, 
    value: ExpenseFormData[K]
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

  const setFormData = useCallback((data: Partial<ExpenseFormData>) => {
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
    if (!formData.property_id) {
      newErrors.property_id = 'Property is required';
    }

    if (!formData.category?.trim()) {
      newErrors.category = 'Category is required';
    }

    if (!formData.amount || parseFloat(formData.amount.toString()) <= 0) {
      newErrors.amount = 'Amount must be greater than 0';
    }

    if (!formData.expense_date) {
      newErrors.expense_date = 'Expense date is required';
    }

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
        property_id: formData.property_id && formData.property_id.toString().trim() ? parseInt(formData.property_id.toString(), 10) : 0,
        category: formData.category,
        subtotal_amount: formData.amount, // Convert form field name to API field name
        expense_date: formData.expense_date,
        description: formData.description || undefined,
        payment_method: formData.payment_method || undefined,
        receipt_url: formData.receipt_url || undefined,
        taxes: validTaxes.length > 0 ? validTaxes : undefined,
      };

      let response;
      if (mode === 'create') {
        response = await createExpense(submitData as CreateExpenseRequest);
      } else {
        if (!formData.id) {
          throw new Error('Expense ID required for update');
        }
        response = await updateExpense(
          formData.id && formData.id.toString().trim() ? parseInt(formData.id.toString(), 10) : 0,
          submitData as UpdateExpenseRequest
        );
      }

      if (response) {
        toast.success(`Expense ${mode === 'create' ? 'created' : 'updated'} successfully`);
        onSuccess?.();
        return true;
      } else {
        throw new Error(`Failed to ${mode} expense`);
      }
    } catch (error) {
      console.error(`Error ${mode === 'create' ? 'creating' : 'updating'} expense:`, error);
      toast.error(error instanceof Error ? error.message : `Failed to ${mode} expense`);
      return false;
    } finally {
      setIsSubmitting(false);
    }
  }, [formData, validateForm, mode, onSuccess]);

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