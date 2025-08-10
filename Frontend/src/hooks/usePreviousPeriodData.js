import { useEffect, useMemo, useState } from "react";
import { fetchDashboardData } from "../utils/api/index.js";
import { getPresetRange, toIsoDate, startOfMonth, startOfQuarter, startOfYear } from "../utils/dateRanges";


export default function usePreviousPeriodData({ propertyId, timePeriod, currentRange }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const rangeParams = useMemo(() => {
    // If currentRange (start/end) supplied, derive previous range of same length ending at the day before current start
    if (currentRange?.start && currentRange?.end) {
      const start = new Date(currentRange.start);
      const end = new Date(currentRange.end);
      const diffDays = Math.ceil((end - start) / (1000 * 60 * 60 * 24)) + 1;
      const prevEnd = new Date(start);
      prevEnd.setDate(prevEnd.getDate() - 1);
      const prevStart = new Date(prevEnd);
      prevStart.setDate(prevStart.getDate() - (diffDays - 1));
      return {
        start_date: toIsoDate(prevStart),
        end_date: toIsoDate(prevEnd),
      };
    }
    // Otherwise use preset mapping
    let preset = "this_month";
    if (timePeriod === "quarter") preset = "this_quarter";
    if (timePeriod === "year") preset = "ytd";
    const { start, end } = getPresetRange(preset);
    // Previous of preset
    let prev;
    if (preset === "this_month") prev = getPresetRange("last_month");
    else if (preset === "this_quarter") prev = getPresetRange("last_quarter");
    else if (preset === "ytd") {
      const lastYearStart = new Date(start.getFullYear() - 1, 0, 1);
      const lastYearEnd = new Date(start.getFullYear() - 1, 11, 31);
      prev = { start: lastYearStart, end: lastYearEnd };
    }
    else prev = getPresetRange("last_month");
    return { start_date: toIsoDate(prev.start), end_date: toIsoDate(prev.end) };
  }, [currentRange, timePeriod]);

  useEffect(() => {
    let isMounted = true;
    const controller = new AbortController();

    const load = async () => {
      try {
        setLoading(true);
        const resp = await fetchDashboardData(
          {
            property_id: propertyId || undefined,
            time_period: timePeriod,
            ...rangeParams,
          },
          { signal: controller.signal }
        );
        if (isMounted) {
          setData(resp);
          setError(null);
        }
      } catch (err) {
        if (isMounted) setError(err);
      } finally {
        if (isMounted) setLoading(false);
      }
    };
    load();

    return () => {
      isMounted = false;
      controller.abort();
    };
  }, [propertyId, timePeriod, rangeParams]);

  return { data, loading, error };
}
