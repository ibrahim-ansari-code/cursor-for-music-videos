/**
 * useCalendar Hook
 * 
 * Custom hook for fetching and managing calendar events data
 */

import { useState, useEffect, useCallback } from 'react';
import { fetchCalendarEvents, CalendarFilters, CalendarEventsResponse } from '../utils/api/calendar';
import { startOfMonth, endOfMonth, format } from 'date-fns';

export const useCalendar = (initialFilters?: Partial<CalendarFilters>) => {
  const [data, setData] = useState<CalendarEventsResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<Error | null>(null);
  
  const [filters, setFilters] = useState<CalendarFilters>({
    from_date: format(startOfMonth(new Date()), 'yyyy-MM-dd'),
    to_date: format(endOfMonth(new Date()), 'yyyy-MM-dd'),
    ...initialFilters,
  });

  const fetchEvents = useCallback(async () => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await fetchCalendarEvents(filters);
      setData(response);
    } catch (err) {
      setError(err as Error);
      console.error('Failed to fetch calendar events:', err);
    } finally {
      setLoading(false);
    }
  }, [filters]);

  useEffect(() => {
    fetchEvents();
  }, [fetchEvents]);

  const updateFilters = useCallback((newFilters: Partial<CalendarFilters>) => {
    setFilters(prev => ({ ...prev, ...newFilters }));
  }, []);

  const refetch = useCallback(() => {
    fetchEvents();
  }, [fetchEvents]);

  return {
    events: data?.events || [],
    total: data?.total || 0,
    loading,
    error,
    filters,
    updateFilters,
    refetch,
  };
};

