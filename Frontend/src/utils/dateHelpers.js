/**
 * Date utility functions for handling date ranges and date operations.
 */

/**
 * Converts a date range string to start_date and end_date parameters.
 * @param {string} dateRange - The date range identifier (e.g., "week", "month", "quarter", "year")
 * @returns {Object} An object containing start_date and end_date in ISO format (YYYY-MM-DD)
 */
export const getDateRangeParams = (dateRange) => {
  const today = new Date();
  const result = {};

  switch (dateRange) {
    case "week":
      const weekAgo = new Date();
      weekAgo.setDate(today.getDate() - 7);
      result.start_date = weekAgo.toISOString().split("T")[0];
      result.end_date = today.toISOString().split("T")[0];
      break;

    case "month":
      // Use a more robust method that handles month boundaries properly
      const monthAgo = new Date(today.getFullYear(), today.getMonth() - 1, today.getDate());
      // Handle case where the target month has fewer days (e.g., Jan 31 -> Feb 28)
      if (monthAgo.getMonth() !== (today.getMonth() - 1 + 12) % 12) {
        // If the date rolled over to the next month, set to last day of target month
        monthAgo.setDate(0);
      }
      result.start_date = monthAgo.toISOString().split("T")[0];
      result.end_date = today.toISOString().split("T")[0];
      break;

    case "quarter":
      // Use a more robust method for quarter calculation
      const quarterAgo = new Date(today.getFullYear(), today.getMonth() - 3, today.getDate());
      // Handle month boundary issues
      if (quarterAgo.getMonth() !== (today.getMonth() - 3 + 12) % 12) {
        quarterAgo.setDate(0);
      }
      result.start_date = quarterAgo.toISOString().split("T")[0];
      result.end_date = today.toISOString().split("T")[0];
      break;

    case "year":
      const yearAgo = new Date();
      yearAgo.setFullYear(today.getFullYear() - 1);
      result.start_date = yearAgo.toISOString().split("T")[0];
      result.end_date = today.toISOString().split("T")[0];
      break;

    default:
      // Return empty object for unknown date ranges
      break;
  }

  return result;
};

/**
 * Formats a date to ISO string format (YYYY-MM-DD).
 * @param {Date} date - The date to format
 * @returns {string} The formatted date string
 */
export const formatDateToISO = (date) => {
  return date.toISOString().split("T")[0];
};

/**
 * Gets the current date in ISO string format (YYYY-MM-DD).
 * @returns {string} Today's date in ISO format
 */
export const getTodayISO = () => {
  return new Date().toISOString().split("T")[0];
};