// Receipt parsing utility functions for cleaner, more maintainable code

import { PAYMENT_METHODS, EXPENSE_CATEGORIES, type PaymentMethod } from './constants';

export interface ParsedReceiptDetails {
  subtotal_amount?: number | null;
  total_amount?: number | null;
  total_tax_amount?: number | null;
  expense_date?: string | null;
  payment_date?: string | null;
  description_notes?: string | null;
  vendor_name?: string | null;
  expense_category?: string | null;
  payment_method?: string | null;
  tax_details?: Array<{
    tax_name: string | null;
    tax_rate: number;
  }> | null;
  receipt_url?: string | null;
}

export interface FormData {
  amount?: string | number;
  expense_date?: string;
  description?: string;
  category?: string;
  payment_method?: string;
  vendor_name?: string;
  receipt_url?: string | null;
  payment_date?: string;
  notes?: string;
  transaction_reference?: string;
}

export interface TaxItem {
  tax_name: string;
  tax_rate: string;
}

export interface ExtractedExpenseData {
  amount: string | number;
  taxes: TaxItem[];
  expense_date: string;
  description: string;
  category: string;
  payment_method: string;
  successMessage: string;
}

/**
 * Extracts and validates amount from parsed receipt details
 */
export const extractReceiptAmount = (parsedDetails: ParsedReceiptDetails, currentAmount: string | number = ""): string | number => {
  // Priority: subtotal_amount > total_amount > current amount
  if (
    parsedDetails.subtotal_amount !== null &&
    parsedDetails.subtotal_amount !== undefined &&
    parsedDetails.subtotal_amount > 0
  ) {
    return parsedDetails.subtotal_amount;
  }

  if (parsedDetails.total_amount !== null && parsedDetails.total_amount !== undefined && parsedDetails.total_amount > 0) {
    return parsedDetails.total_amount;
  }

  return currentAmount;
};

/**
 * Extracts and validates date from parsed receipt details
 */
export const extractReceiptDate = (parsedDetails: ParsedReceiptDetails, currentDate: string = ""): string => {
  const dateStr = parsedDetails.expense_date || parsedDetails.payment_date;

  if (!dateStr) return currentDate;

  const parsedDate = new Date(dateStr);
  if (isNaN(parsedDate.getTime())) return currentDate;

  return dateStr;
};

/**
 * Extracts description from parsed receipt details
 */
export const extractReceiptDescription = (
  parsedDetails: ParsedReceiptDetails,
  currentDescription: string = ""
): string => {
  return parsedDetails.description_notes || currentDescription;
};

/**
 * Determines tax name from description context
 */
export const determineTaxName = (description: string = ""): string => {
  const desc = description.toLowerCase();

  // Canadian tax types (most common)
  if (desc.includes("hst")) return "HST";
  if (desc.includes("gst")) return "GST";
  if (desc.includes("pst")) return "PST";
  if (desc.includes("qst")) return "QST";

  // Other common tax types
  if (desc.includes("sales tax")) return "Sales Tax";
  if (desc.includes("vat")) return "VAT";

  return "Tax";
};

/**
 * Creates tax details from structured tax data
 */
export const processTaxDetails = (taxDetails: Array<{ tax_name?: string | null; tax_rate?: number }>): TaxItem[] => {
  if (!Array.isArray(taxDetails) || taxDetails.length === 0) {
    return [{ tax_name: "", tax_rate: "" }];
  }

  const validTaxDetails = taxDetails
    .map((taxDetail) => {
      const rawRate = taxDetail.tax_rate;
      
      
      // Check for NaN before any conversion - use Number.isNaN for precise detection
      if (rawRate !== undefined && rawRate !== null && Number.isNaN(rawRate)) {
        console.warn(`Invalid tax rate "${taxDetail.tax_rate}" skipped. Valid range is 0-100%.`);
        return null;
      }
      
      // Use rawRate directly if it exists and is not null/undefined, otherwise default to 0
      const valueToConvert = (rawRate !== undefined && rawRate !== null) ? rawRate : 0;
      const taxRate = parseFloat(valueToConvert.toString());
      
      // Validate tax rate is numeric and within bounds
      if (isNaN(taxRate) || taxRate < 0 || taxRate > 100) {
        console.warn(`Invalid tax rate "${taxDetail.tax_rate}" skipped. Valid range is 0-100%.`);
        return null;
      }
      
      return {
        tax_name: taxDetail.tax_name || "Tax",
        tax_rate: taxRate.toFixed(2),
      };
    })
    .filter((item): item is TaxItem => item !== null);
    
  // Ensure at least one entry if no valid tax details were found
  return validTaxDetails.length > 0 ? validTaxDetails : [{ tax_name: "", tax_rate: "" }];
};

/**
 * Calculates tax rate from total tax amount and subtotal
 */
export const calculateTaxRate = (totalTaxAmount: number, subtotalAmount: number): number => {
  // Check for invalid input types first
  if (totalTaxAmount === Infinity || totalTaxAmount === -Infinity || 
      subtotalAmount === Infinity || subtotalAmount === -Infinity ||
      isNaN(totalTaxAmount) || isNaN(subtotalAmount) ||
      subtotalAmount <= 0 || totalTaxAmount < 0) {
    return 0;
  }
  
  // Convert to numbers
  const taxAmount = parseFloat(totalTaxAmount.toString());
  const subtotal = parseFloat(subtotalAmount.toString());
  
  // Double-check after conversion
  if (isNaN(taxAmount) || isNaN(subtotal) || !isFinite(taxAmount) || !isFinite(subtotal)) {
    return 0;
  }

  const calculatedRate = (taxAmount / subtotal) * 100;
  
  // Check if calculated rate is finite before clamping
  if (!isFinite(calculatedRate)) {
    return 0;
  }
  
  // Ensure the calculated rate is within reasonable bounds (0-100%) and round to 2 decimal places
  const clampedRate = Math.min(Math.max(calculatedRate, 0), 100);
  return parseFloat(clampedRate.toFixed(2));
};

/**
 * Creates tax details from calculated tax rate
 */
export const createTaxFromRate = (taxRate: number, description: string = ""): TaxItem[] => {
  if (taxRate <= 0) {
    return [{ tax_name: "", tax_rate: "" }];
  }

  return [
    {
      tax_name: determineTaxName(description),
      tax_rate: taxRate.toFixed(2),
    },
  ];
};

/**
 * Main function to extract and process tax information from receipt
 */
export const extractReceiptTaxes = (parsedDetails: ParsedReceiptDetails): TaxItem[] => {
  // Strategy 1: Use structured tax details if available
  if (
    parsedDetails.tax_details &&
    Array.isArray(parsedDetails.tax_details) &&
    parsedDetails.tax_details.length > 0
  ) {
    return processTaxDetails(parsedDetails.tax_details);
  }

  // Strategy 2: Calculate from total tax amount and subtotal
  if (parsedDetails.total_tax_amount && parsedDetails.total_tax_amount > 0 && parsedDetails.subtotal_amount && parsedDetails.subtotal_amount > 0) {
    const taxRate = calculateTaxRate(
      parsedDetails.total_tax_amount,
      parsedDetails.subtotal_amount
    );
    const description = parsedDetails.description_notes || "";
    return createTaxFromRate(taxRate, description);
  }

  // Strategy 3: Fallback to empty tax entry
  return [{ tax_name: "", tax_rate: "" }];
};

/**
 * Generates success message based on extracted tax information
 */
export const generateTaxSuccessMessage = (extractedTaxes: TaxItem[], _parsedDetails: ParsedReceiptDetails): string => {
  const baseMessage = "Receipt parsed successfully!";

  // Check if we have meaningful tax data
  const validTaxes = extractedTaxes.filter(
    (tax) => tax.tax_name && parseFloat(tax.tax_rate) > 0
  );

  if (validTaxes.length === 0) {
    return `${baseMessage} Review the extracted data below.`;
  }

  const taxNames = validTaxes.map((tax) => tax.tax_name).join(", ");
  return `${baseMessage} Found ${validTaxes.length} tax item(s): ${taxNames}. Review the extracted data below.`;
};

/**
 * Extracts vendor name from parsed receipt details
 */
export const extractReceiptVendor = (parsedDetails: ParsedReceiptDetails, currentVendor: string = ""): string => {
  return parsedDetails.vendor_name || currentVendor;
};

/**
 * Extracts and validates expense category from parsed receipt details
 */
export const extractReceiptCategory = (parsedDetails: ParsedReceiptDetails, currentCategory: string = ""): string => {
  const suggestedCategory = parsedDetails.expense_category;
  
  // Validate that the suggested category is in our allowed list
  const lowercased = suggestedCategory?.toLowerCase();
  if (lowercased && (EXPENSE_CATEGORIES as readonly string[]).includes(lowercased)) {
    return lowercased;
  }
  
  return currentCategory;
};

/**
 * Extracts payment method from parsed receipt details
 */
export const extractReceiptPaymentMethod = (parsedDetails: ParsedReceiptDetails, currentPaymentMethod: string = "Other"): string => {
  const extractedMethod = parsedDetails.payment_method;
  
  if (!extractedMethod) {
    return currentPaymentMethod;
  }
  
  // First try exact match (case-sensitive)
  if (PAYMENT_METHODS.includes(extractedMethod as PaymentMethod)) {
    return extractedMethod;
  }
  
  // Then try case-insensitive match
  const normalizedExtracted = extractedMethod.toLowerCase().trim();
  const matchedMethod = PAYMENT_METHODS.find(
    method => method.toLowerCase() === normalizedExtracted
  );
  
  if (matchedMethod) {
    return matchedMethod;
  }
  
  return currentPaymentMethod;
};

/**
 * Complete receipt data extraction for expenses
 */
export const extractExpenseReceiptData = (parsedDetails: ParsedReceiptDetails, currentFormData: FormData): ExtractedExpenseData => {
  const extractedAmount = extractReceiptAmount(
    parsedDetails,
    currentFormData.amount
  );
  const extractedTaxes = extractReceiptTaxes(parsedDetails);
  const extractedDate = extractReceiptDate(
    parsedDetails,
    currentFormData.expense_date || ""
  );
  const extractedDescription = extractReceiptDescription(
    parsedDetails,
    currentFormData.description || ""
  );
  const extractedCategory = extractReceiptCategory(
    parsedDetails,
    currentFormData.category || ""
  );
  const extractedPaymentMethod = extractReceiptPaymentMethod(
    parsedDetails,
    currentFormData.payment_method || "Other"
  );
  const extractedVendor = extractReceiptVendor(
    parsedDetails,
    currentFormData.vendor_name || ""
  );

  // Enhanced description that includes vendor if extracted
  let enhancedDescription = extractedDescription;
  if (extractedVendor && extractedVendor.trim() && !enhancedDescription.toLowerCase().includes(extractedVendor.toLowerCase())) {
    enhancedDescription = extractedVendor + (enhancedDescription ? ` - ${enhancedDescription}` : "");
  }

  return {
    amount: extractedAmount || currentFormData.amount || "",
    taxes: extractedTaxes,
    expense_date: extractedDate || currentFormData.expense_date || "",
    description: enhancedDescription || currentFormData.description || "",
    category: extractedCategory || currentFormData.category || "",
    payment_method: extractedPaymentMethod || currentFormData.payment_method || "Other",
    successMessage: generateEnhancedTaxSuccessMessage(extractedTaxes, parsedDetails, extractedCategory, extractedVendor),
  };
};

/**
 * Generates enhanced success message based on extracted information
 */
export const generateEnhancedTaxSuccessMessage = (extractedTaxes: TaxItem[], _parsedDetails: ParsedReceiptDetails, extractedCategory: string, extractedVendor: string): string => {
  const baseMessage = "Receipt parsed successfully!";
  const details: string[] = [];

  // Add vendor information
  if (extractedVendor && extractedVendor.trim()) {
    details.push(`Vendor: ${extractedVendor}`);
  }

  // Add category information
  if (extractedCategory) {
    details.push(`Category: ${extractedCategory}`);
  }

  // Add tax information
  const validTaxes = extractedTaxes.filter(
    (tax) => tax.tax_name && parseFloat(tax.tax_rate) > 0
  );

  if (validTaxes.length > 0) {
    const taxNames = validTaxes.map((tax) => tax.tax_name).join(", ");
    details.push(`Taxes: ${taxNames}`);
  }

  if (details.length > 0) {
    return `${baseMessage} Found: ${details.join(", ")}. Review the extracted data below.`;
  }

  return `${baseMessage} Review the extracted data below.`;
};

// Payment receipt extraction utilities

/**
 * Extracts payment-specific data from parsed receipt details
 */
export const extractPaymentReceiptData = (parsedDetails: ParsedReceiptDetails, currentFormData: FormData): Partial<FormData> => {
  return {
    amount: parsedDetails.total_amount || currentFormData.amount,
    payment_date: parsedDetails.payment_date || currentFormData.payment_date,
    payment_method: parsedDetails.payment_method || currentFormData.payment_method,
    notes: parsedDetails.description_notes || currentFormData.notes,
    transaction_reference: currentFormData.transaction_reference,
  };
};

/**
 * Extracts payment data for edit mode (conservative approach)
 */
export const extractPaymentReceiptDataForEdit = (
  _parsedDetails: ParsedReceiptDetails,
  _currentFormData: FormData
): Partial<FormData> => {
  // In edit mode, only update receipt URL to avoid overwriting user's edits
  return {
    // Optionally update other fields if desired:
    // amount: parsedDetails.total_amount?.toString() || currentFormData.amount,
    // payment_date: parsedDetails.payment_date || currentFormData.payment_date,
  };
};

/**
 * Extracts expense data for edit mode (conservative approach)
 */
export const extractExpenseReceiptDataForEdit = (
  parsedDetails: ParsedReceiptDetails,
  currentFormData: FormData
): Partial<FormData> => {
  // In edit mode, only update receipt URL to avoid overwriting user's edits
  // This maintains existing user data while allowing receipt replacement
  return {
    // Conservative approach - only update receipt, preserve user edits
    receipt_url: parsedDetails.receipt_url || currentFormData.receipt_url,
  };
};