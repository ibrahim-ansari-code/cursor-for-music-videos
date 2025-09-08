import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { filterValidTaxes } from '../../src/utils/taxValidation';

describe('taxValidation', () => {
  describe('filterValidTaxes', () => {
    let consoleWarnSpy: ReturnType<typeof vi.spyOn>;

    beforeEach(() => {
      consoleWarnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {});
    });

    afterEach(() => {
      consoleWarnSpy.mockRestore();
    });

    it('should handle empty arrays', () => {
      expect(filterValidTaxes([])).toEqual([]);
    });

    it('should handle non-array inputs', () => {
      expect(filterValidTaxes(null as any)).toEqual([]);
      expect(filterValidTaxes(undefined as any)).toEqual([]);
      expect(filterValidTaxes('not an array' as any)).toEqual([]);
    });

    it('should filter out taxes with empty names', () => {
      const taxes = [
        { tax_name: '', tax_rate: 5 },
        { tax_name: '   ', tax_rate: 10 }, // whitespace only
        { tax_name: 'HST', tax_rate: 13 }
      ];

      const result = filterValidTaxes(taxes);
      expect(result).toHaveLength(1);
      expect(result[0]).toEqual({ tax_name: 'HST', tax_rate: 13 });
    });

    it('should filter out taxes with null or undefined names', () => {
      const taxes = [
        { tax_name: null as any, tax_rate: 5 },
        { tax_name: undefined as any, tax_rate: 10 },
        { tax_name: 'GST', tax_rate: 5 }
      ];

      const result = filterValidTaxes(taxes);
      expect(result).toHaveLength(1);
      expect(result[0]).toEqual({ tax_name: 'GST', tax_rate: 5 });
    });

    describe('0% tax rate handling', () => {
      it('should allow 0% tax rates (number)', () => {
        const taxes = [
          { tax_name: 'No Tax', tax_rate: 0 },
          { tax_name: 'HST', tax_rate: 13 }
        ];

        const result = filterValidTaxes(taxes);
        expect(result).toHaveLength(2);
        expect(result[0]).toEqual({ tax_name: 'No Tax', tax_rate: 0 });
        expect(result[1]).toEqual({ tax_name: 'HST', tax_rate: 13 });
      });

      it('should allow 0% tax rates (string)', () => {
        const taxes = [
          { tax_name: 'No Tax', tax_rate: '0' },
          { tax_name: 'Zero Tax', tax_rate: '0.0' },
          { tax_name: 'HST', tax_rate: '13.5' }
        ];

        const result = filterValidTaxes(taxes);
        expect(result).toHaveLength(3);
        expect(result[0]).toEqual({ tax_name: 'No Tax', tax_rate: '0' });
        expect(result[1]).toEqual({ tax_name: 'Zero Tax', tax_rate: '0.0' });
        expect(result[2]).toEqual({ tax_name: 'HST', tax_rate: '13.5' });
      });
    });

    describe('invalid tax rate filtering', () => {
      it('should filter out null, undefined, and empty string tax rates', () => {
      const taxes = [
        { tax_name: 'Valid Tax', tax_rate: 5 },
        { tax_name: 'Null Rate', tax_rate: null as any },
        { tax_name: 'Undefined Rate', tax_rate: undefined as any },
        { tax_name: 'Empty Rate', tax_rate: '' }
      ];

      const result = filterValidTaxes(taxes as any);
      expect(result).toHaveLength(1);
      expect(result[0]).toEqual({ tax_name: 'Valid Tax', tax_rate: 5 });
    });

      it('should filter out negative tax rates', () => {
        const taxes = [
          { tax_name: 'Valid Tax', tax_rate: 5 },
          { tax_name: 'Negative Tax', tax_rate: -5 },
          { tax_name: 'Negative String', tax_rate: '-10.5' }
        ];

        const result = filterValidTaxes(taxes);
        expect(result).toHaveLength(1);
        expect(result[0]).toEqual({ tax_name: 'Valid Tax', tax_rate: 5 });
        expect(consoleWarnSpy).toHaveBeenCalledWith(
          'Invalid tax rate "-5" for tax "Negative Tax". Valid range is 0-100%.'
        );
      });

      it('should filter out tax rates over 100%', () => {
        const taxes = [
          { tax_name: 'Valid Tax', tax_rate: 13.5 },
          { tax_name: 'Over 100', tax_rate: 150 },
          { tax_name: 'Over 100 String', tax_rate: '200.5' }
        ];

        const result = filterValidTaxes(taxes);
        expect(result).toHaveLength(1);
        expect(result[0]).toEqual({ tax_name: 'Valid Tax', tax_rate: 13.5 });
        expect(consoleWarnSpy).toHaveBeenCalledTimes(2);
        expect(consoleWarnSpy).toHaveBeenCalledWith('Invalid tax rate "150" for tax "Over 100". Valid range is 0-100%.');
        expect(consoleWarnSpy).toHaveBeenCalledWith('Invalid tax rate "200.5" for tax "Over 100 String". Valid range is 0-100%.');
      });

      it('should filter out non-numeric tax rates', () => {
        const taxes = [
          { tax_name: 'Valid Tax', tax_rate: 5 },
          { tax_name: 'Text Rate', tax_rate: 'not a number' },
          { tax_name: 'Mixed Text', tax_rate: '5abc' }
        ];

        const result = filterValidTaxes(taxes);
        expect(result).toHaveLength(1);
        expect(result[0]).toEqual({ tax_name: 'Valid Tax', tax_rate: 5 });
        expect(consoleWarnSpy).toHaveBeenCalledTimes(2);
        expect(consoleWarnSpy).toHaveBeenCalledWith('Invalid tax rate "not a number" for tax "Text Rate". Valid range is 0-100%.');
        expect(consoleWarnSpy).toHaveBeenCalledWith('Invalid tax rate "5abc" for tax "Mixed Text". Valid range is 0-100%.');
      });
    });

    describe('boundary value testing', () => {
      it('should allow exactly 100% tax rate', () => {
        const taxes = [
          { tax_name: 'Max Tax', tax_rate: 100 },
          { tax_name: 'Max Tax String', tax_rate: '100.0' }
        ];

        const result = filterValidTaxes(taxes);
        expect(result).toHaveLength(2);
        expect(result[0]).toEqual({ tax_name: 'Max Tax', tax_rate: 100 });
        expect(result[1]).toEqual({ tax_name: 'Max Tax String', tax_rate: '100.0' });
      });

      it('should reject 100.01% tax rate', () => {
        const taxes = [
          { tax_name: 'Valid Tax', tax_rate: 99.99 },
          { tax_name: 'Over Limit', tax_rate: 100.01 }
        ];

        const result = filterValidTaxes(taxes);
        expect(result).toHaveLength(1);
        expect(result[0]).toEqual({ tax_name: 'Valid Tax', tax_rate: 99.99 });
      });
    });

    describe('decimal precision handling', () => {
      it('should handle various decimal formats', () => {
        const taxes = [
          { tax_name: 'HST', tax_rate: 13.5 },
          { tax_name: 'GST', tax_rate: '5.0' },
          { tax_name: 'PST', tax_rate: 7.25 },
          { tax_name: 'QST', tax_rate: '9.975' }
        ];

        const result = filterValidTaxes(taxes);
        expect(result).toHaveLength(4);
        expect(result.map(tax => tax.tax_name)).toEqual(['HST', 'GST', 'PST', 'QST']);
      });
    });

    describe('edge cases', () => {
      it('should handle very small positive numbers', () => {
        const taxes = [
          { tax_name: 'Tiny Tax', tax_rate: 0.001 },
          { tax_name: 'Another Tiny', tax_rate: '0.0001' }
        ];

        const result = filterValidTaxes(taxes);
        expect(result).toHaveLength(2);
      });

      it('should handle scientific notation', () => {
        const taxes = [
          { tax_name: 'Scientific', tax_rate: '1e-5' }, // 0.00001
          { tax_name: 'Large Scientific', tax_rate: '1e2' } // 100
        ];

        const result = filterValidTaxes(taxes);
        expect(result).toHaveLength(2);
      });

      it('should handle Infinity and NaN', () => {
        const taxes = [
          { tax_name: 'Valid', tax_rate: 5 },
          { tax_name: 'Infinity', tax_rate: Infinity },
          { tax_name: 'NaN', tax_rate: NaN }
        ];

        const result = filterValidTaxes(taxes);
        expect(result).toHaveLength(1);
        expect(result[0]).toEqual({ tax_name: 'Valid', tax_rate: 5 });
        expect(consoleWarnSpy).toHaveBeenCalledTimes(2);
      });
    });

    describe('realistic Canadian tax scenarios', () => {
      it('should handle common Canadian tax rates', () => {
        const taxes = [
          { tax_name: 'HST', tax_rate: 13 }, // Ontario
          { tax_name: 'GST', tax_rate: 5 },  // Federal
          { tax_name: 'PST', tax_rate: 7 },  // BC
          { tax_name: 'QST', tax_rate: 9.975 }, // Quebec
          { tax_name: 'No Tax', tax_rate: 0 } // Tax-exempt
        ];

        const result = filterValidTaxes(taxes);
        expect(result).toHaveLength(5);
        expect(result.map(tax => tax.tax_name)).toEqual(['HST', 'GST', 'PST', 'QST', 'No Tax']);
      });

      it('should handle combined tax scenarios', () => {
        const taxes = [
          { tax_name: 'HST Ontario', tax_rate: 13 },
          { tax_name: 'HST Nova Scotia', tax_rate: 15 },
          { tax_name: 'GST + PST Alberta', tax_rate: 5 }, // Alberta has no PST
          { tax_name: 'GST + PST BC', tax_rate: 12 } // 5% GST + 7% PST
        ];

        const result = filterValidTaxes(taxes);
        expect(result).toHaveLength(4);
      });
    });
  });
});