/**
 * Number parsing utilities for safe type conversions
 * These functions prevent NaN from propagating through the application
 */

/**
 * Safely parse a string to an integer, returning null if parsing fails
 * @param value - The string value to parse
 * @param radix - The radix (base) to use for parsing (default: 10)
 * @returns The parsed integer or null if parsing fails
 *
 * @example
 * parseIntSafe("123") // returns 123
 * parseIntSafe("abc") // returns null
 * parseIntSafe("") // returns null
 * parseIntSafe("12.5") // returns 12
 */
export const parseIntSafe = (value: string | number | null | undefined, radix: number = 10): number | null => {
  if (value === null || value === undefined || value === '') {
    return null;
  }

  const parsed = Number.parseInt(String(value), radix);
  return isNaN(parsed) ? null : parsed;
};

/**
 * Safely parse a string to a float, returning null if parsing fails
 * @param value - The string value to parse
 * @returns The parsed float or null if parsing fails
 *
 * @example
 * parseFloatSafe("123.45") // returns 123.45
 * parseFloatSafe("abc") // returns null
 * parseFloatSafe("") // returns null
 * parseFloatSafe("12") // returns 12
 */
export const parseFloatSafe = (value: string | number | null | undefined): number | null => {
  if (value === null || value === undefined || value === '') {
    return null;
  }

  const parsed = Number.parseFloat(String(value));
  return isNaN(parsed) ? null : parsed;
};

/**
 * Safely parse a string to a number using Number() constructor
 * More permissive than parseInt/parseFloat and handles edge cases better
 * @param value - The string value to parse
 * @returns The parsed number or null if parsing fails
 *
 * @example
 * parseNumberSafe("123") // returns 123
 * parseNumberSafe("123.45") // returns 123.45
 * parseNumberSafe("abc") // returns null
 * parseNumberSafe("") // returns null
 */
export const parseNumberSafe = (value: string | number | null | undefined): number | null => {
  if (value === null || value === undefined || value === '') {
    return null;
  }

  const parsed = Number(value);
  return isNaN(parsed) ? null : parsed;
};

/**
 * Format a number as currency
 * @param value - The number to format
 * @param currency - The currency code (default: 'USD')
 * @param locale - The locale to use for formatting (default: 'en-US')
 * @returns The formatted currency string
 *
 * @example
 * formatCurrency(1234.56) // returns "$1,234.56"
 * formatCurrency(1234.56, 'EUR', 'de-DE') // returns "1.234,56 €"
 */
export const formatCurrency = (
  value: number | string | null | undefined,
  currency: string = 'USD',
  locale: string = 'en-US'
): string => {
  const parsed = parseFloatSafe(value);

  if (parsed === null) {
    return '--';
  }

  return new Intl.NumberFormat(locale, {
    style: 'currency',
    currency,
  }).format(parsed);
};

/**
 * Format a number with thousand separators
 * @param value - The number to format
 * @param decimals - Number of decimal places (default: 2)
 * @param locale - The locale to use for formatting (default: 'en-US')
 * @returns The formatted number string
 *
 * @example
 * formatNumber(1234.567) // returns "1,234.57"
 * formatNumber(1234.567, 0) // returns "1,235"
 */
export const formatNumber = (
  value: number | string | null | undefined,
  decimals: number = 2,
  locale: string = 'en-US'
): string => {
  const parsed = parseFloatSafe(value);

  if (parsed === null) {
    return '--';
  }

  return new Intl.NumberFormat(locale, {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  }).format(parsed);
};
