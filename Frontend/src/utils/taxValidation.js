/**
 * @file taxValidation.js
 * @description Shared utility functions for tax data validation.
 */

/**
 * Filters an array of taxes, returning only items with valid names and rates.
 * @param {Array<Object>} taxes - The array of tax objects to filter. Each object should have `tax_name` and `tax_rate`.
 * @returns {Array<Object>} A new array containing only valid tax objects.
 */
export const filterValidTaxes = (taxes) => {
  if (!Array.isArray(taxes)) {
    return [];
  }

  return taxes.filter((tax) => {
    if (!tax.tax_name || !tax.tax_name.trim() || !tax.tax_rate) {
      return false;
    }

    const taxRate = Number.parseFloat(tax.tax_rate);
    if (isNaN(taxRate) || taxRate < 0 || taxRate > 100) {
      console.warn(
        `Invalid tax rate "${tax.tax_rate}" for tax "${tax.tax_name}". Valid range is 0-100%.`
      );
      return false;
    }
    return true;
  });
}; 