/**
 * Date utility functions for handling timezone-safe date formatting
 *
 * The issue: When a date like "2025-12-01" is parsed with `new Date("2025-12-01")`,
 * JavaScript interprets it as midnight UTC. When displayed in a western timezone
 * (like PST at UTC-8), it becomes "Nov 30, 2025 4:00 PM" - the wrong day!
 *
 * Solution: Parse dates as local midnight to prevent timezone shifts.
 */

/**
 * Parses a date string (YYYY-MM-DD or ISO format) as local midnight
 * to prevent timezone issues when displaying dates.
 *
 * @param dateString - Date string in YYYY-MM-DD or ISO format
 * @returns Date object representing local midnight, or null if invalid
 *
 * @example
 * parseLocalDate('2025-12-01') // Dec 1, 2025 00:00:00 (local time)
 * parseLocalDate('2025-12-01T00:00:00Z') // Dec 1, 2025 00:00:00 (local time)
 */
export const parseLocalDate = (dateString: string): Date | null => {
  if (!dateString) return null;

  // Extract just the date part (YYYY-MM-DD) regardless of format
  const datePart = dateString.split('T')[0];
  const [year, month, day] = datePart.split('-').map(Number);

  if (isNaN(year) || isNaN(month) || isNaN(day)) return null;

  // Create date using local timezone (month is 0-indexed)
  return new Date(year, month - 1, day);
};

/**
 * Formats a date string for display without timezone issues.
 *
 * @param dateString - Date string in YYYY-MM-DD or ISO format
 * @param options - Intl.DateTimeFormat options (default: short month format)
 * @param locale - Locale string (default: 'en-US')
 * @returns Formatted date string, or empty string if invalid
 *
 * @example
 * formatDateForDisplay('2025-12-01') // "Dec 1, 2025"
 * formatDateForDisplay('2025-12-01', { month: 'long' }) // "December 1, 2025"
 */
export const formatDateForDisplay = (
  dateString: string,
  options: Intl.DateTimeFormatOptions = {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  },
  locale = 'en-US'
): string => {
  const date = parseLocalDate(dateString);
  if (!date) return '';
  return date.toLocaleDateString(locale, options);
};

/**
 * Formats a date string to YYYY-MM-DD format (for input[type="date"])
 *
 * @param dateString - Date string in any parseable format
 * @returns Date string in YYYY-MM-DD format
 */
export const formatDateToYYYYMMDD = (dateString: string): string => {
  const date = parseLocalDate(dateString);
  if (!date) return '';

  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
};
