import { useEffect, useState } from "react";
import { fetchRentTracker } from "../utils/api/index.js";

export default function useRentTracker({ month, year, propertyId }) {
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let isMounted = true;
    const load = async () => {
      try {
        setLoading(true);
        const resp = await fetchRentTracker({ month, year, property_id: propertyId });
        const unpaid = Array.isArray(resp)
          ? resp.filter((r) => r.status === "DUE" || r.status === "PARTIAL")
          : [];
        if (isMounted) setData(unpaid);
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
  }, [month, year, propertyId]);

  return { data, loading, error };
}
