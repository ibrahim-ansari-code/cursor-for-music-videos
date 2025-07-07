// Receipt parsing utility functions for cleaner, more maintainable code

import { PAYMENT_METHODS, EXPENSE_CATEGORIES } from './constants.js';

/**
 * Extracts and validates amount from parsed receipt details
 * @param {Object} parsedDetails - Parsed receipt data
 * @param {string|number} currentAmount - Current form amount as fallback
 * @returns {string|number} Extracted or fallback amount
 */
export const extractReceiptAmount = (parsedDetails, currentAmount = "") => {
  // Priority: subtotal_amount > total_amount > current amount
  if (
    parsedDetails.subtotal_amount !== null &&
    parsedDetails.subtotal_amount > 0
  ) {
    return parsedDetails.subtotal_amount;
  }

  if (parsedDetails.total_amount !== null && parsedDetails.total_amount > 0) {
    return parsedDetails.total_amount;
  }

  return currentAmount;
};

/**
 * Extracts and validates date from parsed receipt details
 * @param {Object} parsedDetails - Parsed receipt data
 * @param {string} currentDate - Current form date as fallback
 * @returns {string} Extracted or fallback date
 */
export const extractReceiptDate = (parsedDetails, currentDate = "") => {
  const dateStr = parsedDetails.expense_date || parsedDetails.payment_date;

  if (!dateStr) return currentDate;

  const parsedDate = new Date(dateStr);
  if (isNaN(parsedDate.getTime())) return currentDate;

  return dateStr;
};

/**
 * Extracts description from parsed receipt details
 * @param {Object} parsedDetails - Parsed receipt data
 * @param {string} currentDescription - Current form description as fallback
 * @returns {string} Extracted or fallback description
 */
export const extractReceiptDescription = (
  parsedDetails,
  currentDescription = ""
) => {
  return parsedDetails.description_notes || currentDescription;
};

/**
 * Determines tax name from description context
 * @param {string} description - Receipt description or notes
 * @returns {string} Most likely tax name
 */
export const determineTaxName = (description = "") => {
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
 * @param {Array} taxDetails - Array of tax detail objects
 * @returns {Array} Formatted tax array for form
 */
export const processTaxDetails = (taxDetails) => {
  if (!Array.isArray(taxDetails) || taxDetails.length === 0) {
    return [{ tax_name: "", tax_rate: "" }];
  }

  const validTaxDetails = taxDetails
    .map((taxDetail) => {
      const taxRate = parseFloat(taxDetail.tax_rate || 0);
      
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
    .filter(Boolean); // Remove null entries
    
  // Ensure at least one entry if no valid tax details were found
  return validTaxDetails.length > 0 ? validTaxDetails : [{ tax_name: "", tax_rate: "" }];
};

/**
 * Calculates tax rate from total tax amount and subtotal
 * @param {number} totalTaxAmount - Total tax amount
 * @param {number} subtotalAmount - Subtotal before tax
 * @returns {number} Tax rate as percentage
 */
export const calculateTaxRate = (totalTaxAmount, subtotalAmount) => {
  // Validate input parameters
  const taxAmount = parseFloat(totalTaxAmount);
  const subtotal = parseFloat(subtotalAmount);
  
  if (isNaN(taxAmount) || isNaN(subtotal) || subtotal <= 0 || taxAmount < 0) {
    return 0;
  }

  const calculatedRate = (taxAmount / subtotal) * 100;
  
  // Ensure the calculated rate is within reasonable bounds (0-100%) and round to 2 decimal places
  const clampedRate = Math.min(Math.max(calculatedRate, 0), 100);
  return parseFloat(clampedRate.toFixed(2));
};

/**
 * Creates tax details from calculated tax rate
 * @param {number} taxRate - Tax rate as percentage
 * @param {string} description - Receipt description for tax name inference
 * @returns {Array} Tax array with calculated rate
 */
export const createTaxFromRate = (taxRate, description = "") => {
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
 * @param {Object} parsedDetails - Parsed receipt data
 * @returns {Array} Processed tax array for form
 */
export const extractReceiptTaxes = (parsedDetails) => {
  // Strategy 1: Use structured tax details if available
  if (
    parsedDetails.tax_details &&
    Array.isArray(parsedDetails.tax_details) &&
    parsedDetails.tax_details.length > 0
  ) {
    return processTaxDetails(parsedDetails.tax_details);
  }

  // Strategy 2: Calculate from total tax amount and subtotal
  if (parsedDetails.total_tax_amount > 0 && parsedDetails.subtotal_amount > 0) {
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
 * @param {Array} extractedTaxes - Processed tax array
 * @param {Object} parsedDetails - Original parsed details for context
 * @returns {string} User-friendly success message
 */
export const generateTaxSuccessMessage = (extractedTaxes, parsedDetails) => {
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
 * @param {Object} parsedDetails - Parsed receipt data
 * @param {string} currentVendor - Current form vendor as fallback
 * @returns {string} Extracted or fallback vendor name
 */
export const extractReceiptVendor = (parsedDetails, currentVendor = "") => {
  return parsedDetails.vendor_name || currentVendor;
};

/**
 * Extracts and validates expense category from parsed receipt details
 * @param {Object} parsedDetails - Parsed receipt data
 * @param {string} currentCategory - Current form category as fallback
 * @returns {string} Extracted or fallback category
 */
export const extractReceiptCategory = (parsedDetails, currentCategory = "") => {
  const suggestedCategory = parsedDetails.expense_category;
  
  // Validate that the suggested category is in our allowed list
  if (suggestedCategory && EXPENSE_CATEGORIES.includes(suggestedCategory.toLowerCase())) {
    return suggestedCategory.toLowerCase();
  }
  
  return currentCategory;
};

/**
 * Extracts payment method from parsed receipt details
 * @param {Object} parsedDetails - Parsed receipt data
 * @param {string} currentPaymentMethod - Current form payment method as fallback
 * @returns {string} Extracted or fallback payment method
 */
export const extractReceiptPaymentMethod = (parsedDetails, currentPaymentMethod = "Other") => {
  const extractedMethod = parsedDetails.payment_method;
  
  if (!extractedMethod) {
    return currentPaymentMethod;
  }
  
  // First try exact match (case-sensitive)
  if (PAYMENT_METHODS.includes(extractedMethod)) {
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
 * @param {Object} parsedDetails - Parsed receipt data
 * @param {Object} currentFormData - Current form state
 * @returns {Object} Extracted data for form update
 */
export const extractExpenseReceiptData = (parsedDetails, currentFormData) => {
  const extractedAmount = extractReceiptAmount(
    parsedDetails,
    currentFormData.amount
  );
  const extractedTaxes = extractReceiptTaxes(parsedDetails);
  const extractedDate = extractReceiptDate(
    parsedDetails,
    currentFormData.expense_date
  );
  const extractedDescription = extractReceiptDescription(
    parsedDetails,
    currentFormData.description
  );
  const extractedCategory = extractReceiptCategory(
    parsedDetails,
    currentFormData.category
  );
  const extractedPaymentMethod = extractReceiptPaymentMethod(
    parsedDetails,
    currentFormData.payment_method
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
    amount: extractedAmount || currentFormData.amount,
    taxes: extractedTaxes,
    expense_date: extractedDate || currentFormData.expense_date,
    description: enhancedDescription || currentFormData.description,
    category: extractedCategory || currentFormData.category,
    payment_method: extractedPaymentMethod || currentFormData.payment_method,
    successMessage: generateEnhancedTaxSuccessMessage(extractedTaxes, parsedDetails, extractedCategory, extractedVendor),
  };
};

/**
 * Generates enhanced success message based on extracted information
 * @param {Array} extractedTaxes - Processed tax array
 * @param {Object} parsedDetails - Original parsed details for context
 * @param {string} extractedCategory - Extracted expense category
 * @param {string} extractedVendor - Extracted vendor name
 * @returns {string} User-friendly success message
 */
export const generateEnhancedTaxSuccessMessage = (extractedTaxes, parsedDetails, extractedCategory, extractedVendor) => {
  const baseMessage = "Receipt parsed successfully!";
  const details = [];

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
 * @param {Object} parsedDetails - Parsed receipt data
 * @param {Object} currentFormData - Current form state
 * @returns {Object} Extracted data for payment form update
 */
export const extractPaymentReceiptData = (parsedDetails, currentFormData) => {
  return {
    amount: parsedDetails.total_amount || currentFormData.amount,
    payment_date: parsedDetails.payment_date || currentFormData.payment_date,
    payment_method:
      parsedDetails.payment_method || currentFormData.payment_method,
    notes: parsedDetails.description_notes || currentFormData.notes,
    transaction_reference:
      parsedDetails.transaction_reference ||
      currentFormData.transaction_reference,
  };
};

/**
 * Extracts payment data for edit mode (conservative approach)
 * @param {Object} parsedDetails - Parsed receipt data
 * @param {Object} currentFormData - Current form state
 * @returns {Object} Extracted data for payment edit form
 */
export const extractPaymentReceiptDataForEdit = (
  parsedDetails,
  currentFormData
) => {
  // In edit mode, only update receipt URL to avoid overwriting user's edits
  return {
    // Optionally update other fields if desired:
    // amount: parsedDetails.total_amount?.toString() || currentFormData.amount,
    // payment_date: parsedDetails.payment_date || currentFormData.payment_date,
  };
};

/**
 * Extracts expense data for edit mode (conservative approach)
 * @param {Object} parsedDetails - Parsed receipt data
 * @param {Object} currentFormData - Current form state
 * @returns {Object} Extracted data for expense edit form
 */
export const extractExpenseReceiptDataForEdit = (
  parsedDetails,
  currentFormData
) => {
  // In edit mode, only update receipt URL to avoid overwriting user's edits
  // This maintains existing user data while allowing receipt replacement
  return {
    // Conservative approach - only update receipt, preserve user edits
    receipt_url: parsedDetails.receipt_url || currentFormData.receipt_url,
  };
};
