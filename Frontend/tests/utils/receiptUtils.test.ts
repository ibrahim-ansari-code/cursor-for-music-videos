import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest';
import {
  extractReceiptAmount,
  extractReceiptDate,
  extractReceiptDescription,
  determineTaxName,
  processTaxDetails,
  calculateTaxRate,
  createTaxFromRate,
  extractReceiptTaxes,
  generateTaxSuccessMessage,
  extractReceiptVendor,
  extractReceiptCategory,
  extractReceiptPaymentMethod,
  extractExpenseReceiptData,
  generateEnhancedTaxSuccessMessage,
} from '../../src/utils/receiptUtils';

// Mock constants for testing
vi.mock('../../src/utils/constants', () => ({
  EXPENSE_CATEGORIES: ['maintenance', 'utilities', 'taxes', 'insurance', 'administrative', 'other'],
  PAYMENT_METHODS: ['Credit Card', 'Debit Card', 'Bank Transfer', 'Wire Transfer', 'Cash', 'Check', 'Other']
}));

describe('receiptUtils', () => {
  let consoleWarnSpy: ReturnType<typeof vi.spyOn>;

  beforeEach(() => {
    consoleWarnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {});
  });

  afterEach(() => {
    consoleWarnSpy.mockRestore();
  });

  describe('extractReceiptAmount', () => {
    it('should prioritize subtotal_amount over total_amount', () => {
      const parsedDetails = {
        subtotal_amount: 100,
        total_amount: 115
      };
      expect(extractReceiptAmount(parsedDetails, 50)).toBe(100);
    });

    it('should use total_amount when subtotal_amount is not available', () => {
      const parsedDetails = {
        total_amount: 115
      };
      expect(extractReceiptAmount(parsedDetails, 50)).toBe(115);
    });

    it('should return current amount when no parsed amounts are available', () => {
      const parsedDetails = {};
      expect(extractReceiptAmount(parsedDetails, 50)).toBe(50);
      expect(extractReceiptAmount(parsedDetails, '75.50')).toBe('75.50');
    });

    it('should handle null and undefined values', () => {
      const parsedDetails = {
        subtotal_amount: null,
        total_amount: undefined
      };
      expect(extractReceiptAmount(parsedDetails, 25)).toBe(25);
    });

    it('should reject zero or negative amounts', () => {
      const parsedDetails = {
        subtotal_amount: 0,
        total_amount: -10
      };
      expect(extractReceiptAmount(parsedDetails, 25)).toBe(25);
    });

    it('should handle edge case amounts', () => {
      const parsedDetails = {
        subtotal_amount: 0.01 // Very small positive amount
      };
      expect(extractReceiptAmount(parsedDetails, 25)).toBe(0.01);
    });
  });

  describe('extractReceiptDate', () => {
    it('should prioritize expense_date over payment_date', () => {
      const parsedDetails = {
        expense_date: '2023-12-01',
        payment_date: '2023-12-02'
      };
      expect(extractReceiptDate(parsedDetails, '2023-11-30')).toBe('2023-12-01');
    });

    it('should use payment_date when expense_date is not available', () => {
      const parsedDetails = {
        payment_date: '2023-12-02'
      };
      expect(extractReceiptDate(parsedDetails, '2023-11-30')).toBe('2023-12-02');
    });

    it('should return current date when no parsed dates are available', () => {
      const parsedDetails = {};
      expect(extractReceiptDate(parsedDetails, '2023-11-30')).toBe('2023-11-30');
    });

    it('should handle invalid dates', () => {
      const parsedDetails = {
        expense_date: 'invalid-date',
        payment_date: '2023-13-45' // Invalid date
      };
      expect(extractReceiptDate(parsedDetails, '2023-11-30')).toBe('2023-11-30');
    });

    it('should handle various date formats', () => {
      const validDates = [
        '2023-12-01',
        '2023-12-01T10:30:00Z',
        '12/01/2023',
        'December 1, 2023'
      ];

      validDates.forEach(date => {
        const parsedDetails = { expense_date: date };
        const result = extractReceiptDate(parsedDetails, '2023-11-30');
        // Should return the date string if it's parseable
        expect(new Date(result).getTime()).not.toBeNaN();
      });
    });
  });

  describe('extractReceiptDescription', () => {
    it('should extract description_notes when available', () => {
      const parsedDetails = {
        description_notes: 'Office supplies from Staples'
      };
      expect(extractReceiptDescription(parsedDetails, 'Default description')).toBe('Office supplies from Staples');
    });

    it('should return current description when not available', () => {
      const parsedDetails = {};
      expect(extractReceiptDescription(parsedDetails, 'Default description')).toBe('Default description');
    });

    it('should handle empty or null description_notes', () => {
      const parsedDetails1 = { description_notes: '' };
      const parsedDetails2 = { description_notes: null };
      
      expect(extractReceiptDescription(parsedDetails1, 'Default')).toBe('Default');
      expect(extractReceiptDescription(parsedDetails2, 'Default')).toBe('Default');
    });
  });

  describe('determineTaxName', () => {
    it('should identify Canadian tax types', () => {
      expect(determineTaxName('HST charged on purchase')).toBe('HST');
      expect(determineTaxName('GST applicable')).toBe('GST');
      expect(determineTaxName('PST included')).toBe('PST');
      expect(determineTaxName('QST Quebec tax')).toBe('QST');
    });

    it('should identify other tax types', () => {
      expect(determineTaxName('Sales tax applied')).toBe('Sales Tax');
      expect(determineTaxName('VAT included')).toBe('VAT');
    });

    it('should return generic tax name for unrecognized patterns', () => {
      expect(determineTaxName('Unknown tax type')).toBe('Tax');
      expect(determineTaxName('')).toBe('Tax');
      expect(determineTaxName()).toBe('Tax');
    });

    it('should be case insensitive', () => {
      expect(determineTaxName('HST CHARGED')).toBe('HST');
      expect(determineTaxName('gst applied')).toBe('GST');
      expect(determineTaxName('Sales TAX')).toBe('Sales Tax');
    });
  });

  describe('processTaxDetails', () => {
    it('should process valid tax details', () => {
      const taxDetails = [
        { tax_name: 'HST', tax_rate: 13 },
        { tax_name: 'GST', tax_rate: 5.5 }
      ];

      const result = processTaxDetails(taxDetails);
      expect(result).toHaveLength(2);
      expect(result[0]).toEqual({ tax_name: 'HST', tax_rate: '13.00' });
      expect(result[1]).toEqual({ tax_name: 'GST', tax_rate: '5.50' });
    });

    it('should filter out invalid tax rates', () => {
      const taxDetails = [
        { tax_name: 'Valid', tax_rate: 10 },
        { tax_name: 'Negative', tax_rate: -5 },
        { tax_name: 'Over 100', tax_rate: 150 },
        { tax_name: 'NaN', tax_rate: NaN },
        { tax_name: 'Another Valid', tax_rate: 7.25 }
      ];

      const result = processTaxDetails(taxDetails);
      expect(result).toHaveLength(2);
      expect(result[0]).toEqual({ tax_name: 'Valid', tax_rate: '10.00' });
      expect(result[1]).toEqual({ tax_name: 'Another Valid', tax_rate: '7.25' });
      expect(consoleWarnSpy).toHaveBeenCalledTimes(3);
    });

    it('should handle empty or invalid input', () => {
      expect(processTaxDetails([])).toEqual([{ tax_name: '', tax_rate: '' }]);
      expect(processTaxDetails(null as unknown as never[])).toEqual([{ tax_name: '', tax_rate: '' }]);
      expect(processTaxDetails(undefined as unknown as never[])).toEqual([{ tax_name: '', tax_rate: '' }]);
    });

    it('should provide default tax name for missing names', () => {
      const taxDetails = [
        { tax_rate: 13 },
        { tax_name: '', tax_rate: 5 },
        { tax_name: null, tax_rate: 7 }
      ];

      const result = processTaxDetails(taxDetails);
      expect(result).toHaveLength(3);
      expect(result.every(tax => tax.tax_name === 'Tax')).toBe(true);
    });

    it('should handle 0% tax rates correctly', () => {
      const taxDetails = [
        { tax_name: 'No Tax', tax_rate: 0 },
        { tax_name: 'Regular Tax', tax_rate: 13 }
      ];

      const result = processTaxDetails(taxDetails);
      expect(result).toHaveLength(2);
      expect(result[0]).toEqual({ tax_name: 'No Tax', tax_rate: '0.00' });
      expect(result[1]).toEqual({ tax_name: 'Regular Tax', tax_rate: '13.00' });
    });
  });

  describe('calculateTaxRate', () => {
    it('should calculate tax rate correctly', () => {
      expect(calculateTaxRate(13, 100)).toBe(13);
      expect(calculateTaxRate(7.25, 100)).toBe(7.25);
      expect(calculateTaxRate(15.75, 125)).toBe(12.6); // 15.75/125 * 100 = 12.6
    });

    it('should handle edge cases', () => {
      expect(calculateTaxRate(0, 100)).toBe(0); // 0% tax is valid
      expect(calculateTaxRate(13, 0)).toBe(0); // Division by zero
      expect(calculateTaxRate(-5, 100)).toBe(0); // Negative tax amount
      expect(calculateTaxRate(13, -100)).toBe(0); // Negative subtotal
    });

    it('should handle invalid inputs', () => {
      expect(calculateTaxRate(NaN, 100)).toBe(0);
      expect(calculateTaxRate(13, NaN)).toBe(0);
      expect(calculateTaxRate(Infinity, 100)).toBe(0);
      expect(calculateTaxRate(13, Infinity)).toBe(0);
    });

    it('should clamp results to 0-100% range', () => {
      expect(calculateTaxRate(200, 100)).toBe(100); // 200% clamped to 100%
      expect(calculateTaxRate(13, 0.1)).toBe(100); // Very high rate clamped to 100%
    });

    it('should round to 2 decimal places', () => {
      expect(calculateTaxRate(1, 3)).toBe(33.33); // 1/3 * 100 = 33.333... -> 33.33
      expect(calculateTaxRate(2, 3)).toBe(66.67); // 2/3 * 100 = 66.666... -> 66.67
    });
  });

  describe('createTaxFromRate', () => {
    it('should create tax from rate with proper tax name', () => {
      const result = createTaxFromRate(13, 'HST charged on purchase');
      expect(result).toEqual([{ tax_name: 'HST', tax_rate: '13.00' }]);
    });

    it('should return empty tax for zero or negative rates', () => {
      expect(createTaxFromRate(0)).toEqual([{ tax_name: '', tax_rate: '' }]);
      expect(createTaxFromRate(-5)).toEqual([{ tax_name: '', tax_rate: '' }]);
    });

    it('should use generic tax name when description is not provided', () => {
      const result = createTaxFromRate(10);
      expect(result).toEqual([{ tax_name: 'Tax', tax_rate: '10.00' }]);
    });
  });

  describe('extractReceiptTaxes', () => {
    it('should use structured tax details when available', () => {
      const parsedDetails = {
        tax_details: [
          { tax_name: 'HST', tax_rate: 13 },
          { tax_name: 'GST', tax_rate: 5 }
        ]
      };

      const result = extractReceiptTaxes(parsedDetails);
      expect(result).toHaveLength(2);
      expect(result[0]).toEqual({ tax_name: 'HST', tax_rate: '13.00' });
      expect(result[1]).toEqual({ tax_name: 'GST', tax_rate: '5.00' });
    });

    it('should calculate from total tax amount and subtotal when structured details unavailable', () => {
      const parsedDetails = {
        total_tax_amount: 13,
        subtotal_amount: 100,
        description_notes: 'HST charged'
      };

      const result = extractReceiptTaxes(parsedDetails);
      expect(result).toHaveLength(1);
      expect(result[0]).toEqual({ tax_name: 'HST', tax_rate: '13.00' });
    });

    it('should return empty tax entry when no tax data available', () => {
      const parsedDetails = {};
      const result = extractReceiptTaxes(parsedDetails);
      expect(result).toEqual([{ tax_name: '', tax_rate: '' }]);
    });

    it('should prioritize structured tax details over calculated values', () => {
      const parsedDetails = {
        tax_details: [{ tax_name: 'HST', tax_rate: 13 }],
        total_tax_amount: 5, // This should be ignored
        subtotal_amount: 100
      };

      const result = extractReceiptTaxes(parsedDetails);
      expect(result).toHaveLength(1);
      expect(result[0]).toEqual({ tax_name: 'HST', tax_rate: '13.00' });
    });
  });

  describe('generateTaxSuccessMessage', () => {
    it('should generate message for taxes found', () => {
      const taxes = [
        { tax_name: 'HST', tax_rate: '13.00' },
        { tax_name: 'GST', tax_rate: '5.00' }
      ];

      const result = generateTaxSuccessMessage(taxes, {});
      expect(result).toContain('Found 2 tax item(s): HST, GST');
      expect(result).toContain('Receipt parsed successfully!');
    });

    it('should generate message when no valid taxes found', () => {
      const taxes = [
        { tax_name: '', tax_rate: '' },
        { tax_name: 'Zero Tax', tax_rate: '0.00' }
      ];

      const result = generateTaxSuccessMessage(taxes, {});
      expect(result).toBe('Receipt parsed successfully! Review the extracted data below.');
    });

    it('should handle empty tax array', () => {
      const result = generateTaxSuccessMessage([], {});
      expect(result).toBe('Receipt parsed successfully! Review the extracted data below.');
    });
  });

  describe('extractReceiptVendor', () => {
    it('should extract vendor name when available', () => {
      const parsedDetails = { vendor_name: 'Staples Inc.' };
      expect(extractReceiptVendor(parsedDetails, 'Default Vendor')).toBe('Staples Inc.');
    });

    it('should return current vendor when not available', () => {
      const parsedDetails = {};
      expect(extractReceiptVendor(parsedDetails, 'Default Vendor')).toBe('Default Vendor');
    });
  });

  describe('extractReceiptCategory', () => {
    it('should extract valid category when available', () => {
      const parsedDetails = { expense_category: 'maintenance' };
      expect(extractReceiptCategory(parsedDetails, 'other')).toBe('maintenance');
    });

    it('should extract valid category with different casing', () => {
      const parsedDetails = { expense_category: 'MAINTENANCE' };
      expect(extractReceiptCategory(parsedDetails, 'other')).toBe('maintenance');
    });

    it('should return current category for invalid categories', () => {
      const parsedDetails = { expense_category: 'invalid-category' };
      expect(extractReceiptCategory(parsedDetails, 'other')).toBe('other');
    });

    it('should return current category when not available', () => {
      const parsedDetails = {};
      expect(extractReceiptCategory(parsedDetails, 'other')).toBe('other');
    });
  });

  describe('extractReceiptPaymentMethod', () => {
    it('should extract payment method when available', () => {
      const parsedDetails = { payment_method: 'Credit Card' };
      expect(extractReceiptPaymentMethod(parsedDetails, 'Other')).toBe('Credit Card');
    });

    it('should return current method when not available', () => {
      const parsedDetails = {};
      expect(extractReceiptPaymentMethod(parsedDetails, 'Cash')).toBe('Cash');
    });
  });

  describe('extractExpenseReceiptData', () => {
    it('should extract complete expense data', () => {
      const parsedDetails = {
        subtotal_amount: 100,
        expense_date: '2023-12-01',
        description_notes: 'Office supplies',
        vendor_name: 'Staples',
        expense_category: 'administrative',
        payment_method: 'Credit Card',
        tax_details: [{ tax_name: 'HST', tax_rate: 13 }]
      };

      const currentFormData = {
        amount: 50,
        expense_date: '2023-11-30',
        description: 'Default',
        category: 'other',
        payment_method: 'Other'
      };

      const result = extractExpenseReceiptData(parsedDetails, currentFormData);

      expect(result.amount).toBe(100);
      expect(result.expense_date).toBe('2023-12-01');
      expect(result.description).toBe('Staples - Office supplies');
      expect(result.category).toBe('administrative');
      expect(result.payment_method).toBe('Credit Card');
      expect(result.taxes).toEqual([{ tax_name: 'HST', tax_rate: '13.00' }]);
      expect(result.successMessage).toContain('Taxes: HST');
    });
  });

  describe('generateEnhancedTaxSuccessMessage', () => {
    it('should generate enhanced message with all details', () => {
      const taxes = [{ tax_name: 'HST', tax_rate: '13.00' }];
      const parsedDetails = {};
      const category = 'maintenance';
      const vendor = 'Home Depot';

      const result = generateEnhancedTaxSuccessMessage(taxes, parsedDetails, category, vendor);
      
      expect(result).toContain('Receipt parsed successfully!');
      expect(result).toContain('Vendor: Home Depot');
      expect(result).toContain('Category: maintenance');
      expect(result).toContain('Taxes: HST');
    });

    it('should handle missing vendor and category', () => {
      const taxes = [{ tax_name: 'GST', tax_rate: '5.00' }];
      const result = generateEnhancedTaxSuccessMessage(taxes, {}, '', '');
      
      expect(result).toContain('Receipt parsed successfully!');
      expect(result).not.toContain('Vendor:');
      expect(result).not.toContain('Category:');
      expect(result).toContain('Taxes: GST');
    });
  });
});