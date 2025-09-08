/**
 * @file taxUtils.ts
 * @description Shared tax utilities for validation, comparison, and formatting
 */

export interface TaxDetail {
  tax_name: string;
  tax_rate: string | number;
}

/**
 * Validates a tax rate input and returns a numeric value
 * @param taxRate - The tax rate as string or number
 * @returns The numeric tax rate or NaN if invalid
 */
export const validateTaxRate = (taxRate: string | number): number => {
  if (typeof taxRate === 'number') {
    return taxRate;
  }
  
  if (typeof taxRate === 'string') {
    return Number.parseFloat(taxRate.trim());
  }
  
  return NaN;
};

/**
 * Checks if a tax rate is valid (between 0 and 100, inclusive)
 * @param taxRate - The tax rate to validate
 * @returns True if valid, false otherwise
 */
export const isValidTaxRate = (taxRate: string | number): boolean => {
  const rate = validateTaxRate(taxRate);
  return !isNaN(rate) && rate >= 0 && rate <= 100;
};

/**
 * Normalizes a tax rate to a string for consistent comparison
 * @param taxRate - The tax rate as string or number  
 * @returns Normalized string representation
 */
export const normalizeTaxRate = (taxRate: string | number): string => {
  const rate = validateTaxRate(taxRate);
  return isNaN(rate) ? '' : rate.toString();
};

/**
 * Compares two tax details for equality (name and rate)
 * @param tax1 - First tax detail
 * @param tax2 - Second tax detail
 * @returns True if both name and rate match
 */
export const compareTaxDetails = (tax1: TaxDetail, tax2: TaxDetail): boolean => {
  return (
    tax1.tax_name === tax2.tax_name &&
    normalizeTaxRate(tax1.tax_rate) === normalizeTaxRate(tax2.tax_rate)
  );
};

/**
 * Validates tax rate with user-friendly error handling
 * @param tax - The tax detail to validate
 * @returns Object with validity status and error message
 */
export const validateTaxForSubmission = (tax: TaxDetail): { isValid: boolean; error?: string } => {
  if (!tax.tax_name || !tax.tax_rate) {
    return { isValid: false, error: "Please fill in both tax name and rate before setting as default." };
  }

  const rate = validateTaxRate(tax.tax_rate);
  if (isNaN(rate) || rate <= 0 || rate > 100) {
    return { isValid: false, error: "Please enter a valid tax rate between 0.01% and 100%." };
  }

  return { isValid: true };
};
