import { useEffect, useState } from "react";
import { fetchDashboardData } from "../utils/api/index.js";

export default function useDashboardData({ propertyId, timePeriod, startDate, endDate }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let isMounted = true;
    const load = async () => {
      try {
        setLoading(true);
        const params = {
          property_id: propertyId || undefined,
          time_period: timePeriod,
        };
        if (startDate && endDate) {
          params.start_date = startDate;
          params.end_date = endDate;
        }
        const resp = await fetchDashboardData(params);
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
    };
  }, [propertyId, timePeriod, startDate, endDate]);

  return { data, loading, error };
}
