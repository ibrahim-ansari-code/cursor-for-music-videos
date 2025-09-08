/**
 * @file taxValidation.ts
 * @description Shared utility functions for tax data validation.
 */

interface TaxObject {
  tax_name: string;
  tax_rate: number | string;
}

/**
 * Filters an array of taxes, returning only items with valid names and rates.
 * @param taxes - The array of tax objects to filter. Each object should have `tax_name` and `tax_rate`.
 * @returns A new array containing only valid tax objects.
 */
export const filterValidTaxes = (taxes: TaxObject[]): TaxObject[] => {
  if (!Array.isArray(taxes)) {
    return [];
  }

  return taxes.filter((tax) => {
    // Must have a valid tax name
    if (!tax || !tax.tax_name || typeof tax.tax_name !== 'string' || tax.tax_name.trim().length === 0) {
      return false;
    }
    
    // Must have a tax rate that exists (not null, undefined, or empty string)
    // Note: 0 is a valid tax rate (0% tax)
    if (tax.tax_rate === null || tax.tax_rate === undefined || tax.tax_rate === '') {
      return false;
    }

    // Convert to number and validate
    // Number() already handles 0 and '0' correctly, returning 0 in both cases
    const numericRate = Number(tax.tax_rate);
    
    // Must be a valid number between 0 and 100 (inclusive)
    if (isNaN(numericRate) || numericRate < 0 || numericRate > 100) {
      console.warn(
        `Invalid tax rate "${tax.tax_rate}" for tax "${tax.tax_name}". Valid range is 0-100%.`
      );
      return false;
    }
    
    return true;
  });
};