/**
 * @file financialCalculations.ts
 * @description Precise financial calculations using Decimal.js for money arithmetic
 */

import Decimal from 'decimal.js';

// Configure Decimal.js for financial precision
Decimal.set({
  precision: 20,
  rounding: Decimal.ROUND_HALF_EVEN, // Banker's rounding
  toExpNeg: -9,
  toExpPos: 21,
});

export interface TaxCalculation {
  taxName: string;
  taxRate: Decimal;
  taxAmount: Decimal;
}

export interface FinancialBreakdown {
  subtotal: Decimal;
  taxes: TaxCalculation[];
  totalTax: Decimal;
  grandTotal: Decimal;
}

/**
 * Calculate tax amount for a given subtotal and tax rate
 */
export const calculateTaxAmount = (subtotal: Decimal | number | string, taxRate: Decimal | number | string): Decimal => {
  try {
    const subtotalDecimal = new Decimal(subtotal);
    const taxRateDecimal = new Decimal(taxRate);
    
    if (subtotalDecimal.isNaN() || subtotalDecimal.isNegative()) {
      return new Decimal(0);
    }
    
    if (taxRateDecimal.isNaN() || taxRateDecimal.isNegative() || taxRateDecimal.greaterThan(100)) {
      return new Decimal(0);
    }
    
    return subtotalDecimal.mul(taxRateDecimal).div(100);
  } catch {
    return new Decimal(0);
  }
};

/**
 * Calculate comprehensive financial breakdown with multiple taxes
 */
export const calculateFinancialBreakdown = (
  subtotal: Decimal | number | string,
  taxes: Array<{ tax_name: string; tax_rate: Decimal | number | string }>
): FinancialBreakdown => {
  const subtotalDecimal = new Decimal(subtotal || 0);
  const taxCalculations: TaxCalculation[] = [];
  let totalTax = new Decimal(0);

  for (const tax of taxes) {
    if (!tax.tax_name || !tax.tax_rate) continue;

    try {
      const taxRateDecimal = new Decimal(tax.tax_rate);
      const taxAmount = calculateTaxAmount(subtotalDecimal, taxRateDecimal);

      if (taxAmount.greaterThan(0)) {
        taxCalculations.push({
          taxName: tax.tax_name,
          taxRate: taxRateDecimal,
          taxAmount,
        });
        
        totalTax = totalTax.add(taxAmount);
      }
    } catch {
      // Skip invalid tax entries
      continue;
    }
  }

  const grandTotal = subtotalDecimal.add(totalTax);

  return {
    subtotal: subtotalDecimal,
    taxes: taxCalculations,
    totalTax,
    grandTotal,
  };
};

/**
 * Format monetary amount for display
 */
export const formatCurrency = (
  amount: Decimal | number | string,
  currency: string = 'CAD',
  locale: string = 'en-CA'
): string => {
  try {
    const decimal = new Decimal(amount);
    const number = decimal.toNumber();
    
    return new Intl.NumberFormat(locale, {
      style: 'currency',
      currency,
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(number);
  } catch {
    return new Intl.NumberFormat(locale, {
      style: 'currency',
      currency,
    }).format(0);
  }
};

/**
 * Format percentage for display
 */
export const formatPercentage = (
  rate: Decimal | number | string,
  decimalPlaces: number = 2
): string => {
  try {
    const decimal = new Decimal(rate);
    return `${decimal.toFixed(decimalPlaces)}%`;
  } catch {
    return '0.00%';
  }
};

/**
 * Round monetary amount to 2 decimal places using banker's rounding
 */
export const roundCurrency = (amount: Decimal | number | string): Decimal => {
  try {
    const decimal = new Decimal(amount);
    return decimal.toDecimalPlaces(2, Decimal.ROUND_HALF_EVEN);
  } catch {
    return new Decimal(0);
  }
};

/**
 * Validate monetary amount range
 */
export const validateAmountRange = (
  amount: Decimal | number | string,
  min: Decimal | number | string = 0,
  max: Decimal | number | string = '999999999.99'
): { valid: boolean; amount: Decimal; error?: string } => {
  try {
    const amountDecimal = new Decimal(amount);
    const minDecimal = new Decimal(min);
    const maxDecimal = new Decimal(max);

    if (amountDecimal.isNaN()) {
      return { valid: false, amount: new Decimal(0), error: 'Invalid amount' };
    }

    if (amountDecimal.lessThan(minDecimal)) {
      return { 
        valid: false, 
        amount: amountDecimal, 
        error: `Amount must be at least ${formatCurrency(minDecimal)}` 
      };
    }

    if (amountDecimal.greaterThan(maxDecimal)) {
      return { 
        valid: false, 
        amount: amountDecimal, 
        error: `Amount cannot exceed ${formatCurrency(maxDecimal)}` 
      };
    }

    return { valid: true, amount: amountDecimal };
  } catch {
    return { valid: false, amount: new Decimal(0), error: 'Invalid amount format' };
  }
};

/**
 * Calculate compound tax (tax on tax)
 */
export const calculateCompoundTax = (
  subtotal: Decimal | number | string,
  primaryTaxRate: Decimal | number | string,
  secondaryTaxRate: Decimal | number | string
): { primaryTax: Decimal; secondaryTax: Decimal; total: Decimal } => {
  try {
    const subtotalDecimal = new Decimal(subtotal);
    const primaryRate = new Decimal(primaryTaxRate);
    const secondaryRate = new Decimal(secondaryTaxRate);

    const primaryTax = calculateTaxAmount(subtotalDecimal, primaryRate);
    const subtotalPlusPrimaryTax = subtotalDecimal.add(primaryTax);
    const secondaryTax = calculateTaxAmount(subtotalPlusPrimaryTax, secondaryRate);
    const total = subtotalDecimal.add(primaryTax).add(secondaryTax);

    return {
      primaryTax,
      secondaryTax,
      total,
    };
  } catch {
    const zero = new Decimal(0);
    return {
      primaryTax: zero,
      secondaryTax: zero,
      total: new Decimal(subtotal || 0),
    };
  }
};

/**
 * Calculate reverse tax (find subtotal from total including tax)
 */
export const calculateReverseTax = (
  totalAmount: Decimal | number | string,
  taxRate: Decimal | number | string
): { subtotal: Decimal; taxAmount: Decimal } => {
  try {
    const totalDecimal = new Decimal(totalAmount);
    const taxRateDecimal = new Decimal(taxRate);

    if (taxRateDecimal.equals(0)) {
      return {
        subtotal: totalDecimal,
        taxAmount: new Decimal(0),
      };
    }

    // Formula: subtotal = total / (1 + (tax_rate / 100))
    const divisor = new Decimal(1).add(taxRateDecimal.div(100));
    const subtotal = totalDecimal.div(divisor);
    const taxAmount = totalDecimal.sub(subtotal);

    return {
      subtotal: roundCurrency(subtotal),
      taxAmount: roundCurrency(taxAmount),
    };
  } catch {
    const totalDecimal = new Decimal(totalAmount || 0);
    return {
      subtotal: totalDecimal,
      taxAmount: new Decimal(0),
    };
  }
};

/**
 * Calculate effective tax rate from multiple taxes
 */
export const calculateEffectiveTaxRate = (
  taxes: Array<{ tax_rate: Decimal | number | string }>
): Decimal => {
  try {
    const totalRate = taxes.reduce((sum, tax) => {
      const rate = new Decimal(tax.tax_rate || 0);
      return sum.add(rate);
    }, new Decimal(0));

    return totalRate;
  } catch {
    return new Decimal(0);
  }
};

/**
 * Split amount among multiple parties (useful for rent splitting)
 */
export const splitAmount = (
  totalAmount: Decimal | number | string,
  numParts: number,
  roundingMethod: 'up' | 'down' | 'even' = 'even'
): Decimal[] => {
  try {
    const totalDecimal = new Decimal(totalAmount);
    const parts: Decimal[] = [];

    if (numParts <= 0) {
      return [totalDecimal];
    }

    // Determine the rounding mode based on the method
    let roundingMode: Decimal.Rounding;
    switch (roundingMethod) {
      case 'up':
        roundingMode = Decimal.ROUND_UP;
        break;
      case 'down':
        roundingMode = Decimal.ROUND_DOWN;
        break;
      case 'even':
      default:
        roundingMode = Decimal.ROUND_HALF_EVEN; // Banker's rounding
        break;
    }

    const baseAmount = totalDecimal.div(numParts);
    
    // Apply rounding to each part
    for (let i = 0; i < numParts - 1; i++) {
      const roundedAmount = baseAmount.toDecimalPlaces(2, roundingMode);
      parts.push(roundedAmount);
    }
    
    // Calculate the last part to ensure total equals original amount
    const sumOfParts = parts.reduce((sum, part) => sum.add(part), new Decimal(0));
    const lastPart = totalDecimal.sub(sumOfParts);
    parts.push(lastPart);

    return parts;
  } catch {
    return [new Decimal(totalAmount || 0)];
  }
};

export default {
  calculateTaxAmount,
  calculateFinancialBreakdown,
  formatCurrency,
  formatPercentage,
  roundCurrency,
  validateAmountRange,
  calculateCompoundTax,
  calculateReverseTax,
  calculateEffectiveTaxRate,
  splitAmount,
};