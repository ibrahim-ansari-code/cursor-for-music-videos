/**
 * Date utility functions for handling date ranges and date operations
 * Handles timezone-safe date formatting and parsing
 */

/**
 * Date range parameters returned by getDateRangeParams
 */
interface DateRangeParams {
  start_date?: string;
  end_date?: string;
}

/**
 * Supported date range identifiers
 */
export type DateRange = 'week' | 'month' | 'quarter' | 'year';

/**
 * Converts a date range string to start_date and end_date parameters.
 * @param dateRange - The date range identifier (e.g., "week", "month", "quarter", "year")
 * @returns An object containing start_date and end_date in ISO format (YYYY-MM-DD)
 */
export const getDateRangeParams = (dateRange: DateRange): DateRangeParams => {
  const today = new Date();
  const result: DateRangeParams = {};

  switch (dateRange) {
    case 'week':
      const weekAgo = new Date();
      weekAgo.setDate(today.getDate() - 7);
      result.start_date = weekAgo.toISOString().split('T')[0];
      result.end_date = today.toISOString().split('T')[0];
      break;

    case 'month':
      // Use a more robust method that handles month boundaries properly
      const monthAgo = new Date(today.getFullYear(), today.getMonth() - 1, today.getDate());
      // Handle case where the target month has fewer days (e.g., Jan 31 -> Feb 28)
      if (monthAgo.getMonth() !== (today.getMonth() - 1 + 12) % 12) {
        // If the date rolled over to the next month, set to last day of target month
        monthAgo.setDate(0);
      }
      result.start_date = monthAgo.toISOString().split('T')[0];
      result.end_date = today.toISOString().split('T')[0];
      break;

    case 'quarter':
      // Use a more robust method for quarter calculation
      const quarterAgo = new Date(today.getFullYear(), today.getMonth() - 3, today.getDate());
      // Handle month boundary issues
      if (quarterAgo.getMonth() !== (today.getMonth() - 3 + 12) % 12) {
        quarterAgo.setDate(0);
      }
      result.start_date = quarterAgo.toISOString().split('T')[0];
      result.end_date = today.toISOString().split('T')[0];
      break;

    case 'year':
      const yearAgo = new Date();
      yearAgo.setFullYear(today.getFullYear() - 1);
      result.start_date = yearAgo.toISOString().split('T')[0];
      result.end_date = today.toISOString().split('T')[0];
      break;

    default:
      // Return empty object for unknown date ranges
      break;
  }

  return result;
};

/**
 * Formats a date to ISO string format (YYYY-MM-DD).
 * @param date - The date to format
 * @returns The formatted date string
 */
export const formatDateToISO = (date: Date): string => {
  return date.toISOString().split('T')[0];
};

/**
 * Gets the current date in ISO string format (YYYY-MM-DD).
 * @returns Today's date in ISO format
 */
export const getTodayISO = (): string => {
  return new Date().toISOString().split('T')[0];
};

/**
 * Formats a Date object to YYYY-MM-DD string using local date components
 * Prevents timezone issues by using getFullYear/getMonth/getDate instead of toISOString
 *
 * @param date - The date to format
 * @returns Date string in YYYY-MM-DD format
 *
 * @example
 * formatDateToYYYYMMDD(new Date('2025-11-09')) // "2025-11-09"
 */
export const formatDateToYYYYMMDD = (date: Date): string => {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
};

/**
 * Parses a YYYY-MM-DD date string as local midnight to prevent timezone issues
 *
 * @param dateString - Date string in YYYY-MM-DD format
 * @returns Date object representing local midnight
 *
 * @example
 * parseLocalDate('2025-11-09') // Nov 9, 2025 00:00:00 (local time)
 */
export const parseLocalDate = (dateString: string): Date => {
  return new Date(`${dateString}T00:00:00`);
};

/**
 * Formats a date string (YYYY-MM-DD) for display using locale-specific formatting
 *
 * @param dateString - Date string in YYYY-MM-DD format
 * @param options - Intl.DateTimeFormat options
 * @returns Formatted date string
 *
 * @example
 * formatDateForDisplay('2025-11-09') // "Saturday, November 9, 2025"
 */
export const formatDateForDisplay = (
  dateString: string,
  options: Intl.DateTimeFormatOptions = {
    weekday: 'long',
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  }
): string => {
  return parseLocalDate(dateString).toLocaleDateString('en-US', options);
};

/**
 * Gets today's date in YYYY-MM-DD format using local timezone
 *
 * @returns Today's date string
 *
 * @example
 * getTodayDateString() // "2025-11-09"
 */
export const getTodayDateString = (): string => {
  return formatDateToYYYYMMDD(new Date());
};
