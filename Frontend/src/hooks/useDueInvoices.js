import { useEffect, useState } from "react";
import { fetchInvoices } from "../utils/api/index.js";

// Fetch top due invoices (Pending/Overdue), filtered by property and date window
export default function useDueInvoices({ propertyId, startDate, endDate, limit = 5 }) {
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let isMounted = true;
    const controller = new AbortController();

    const load = async () => {
      try {
        setLoading(true);
        const params = {};
        if (propertyId) params.property_id = propertyId;
        if (startDate) params.start_date = startDate;
        if (endDate) params.end_date = endDate;

        const resp = await fetchInvoices(params, { signal: controller.signal });
        const all = Array.isArray(resp) ? resp : resp?.items || [];

        // Keep only Pending or Overdue
        const pending = all.filter((inv) => {
          const s = (inv.status || "").toLowerCase();
          return s === "pending" || s === "overdue";
        });

        // Sort by due_date ascending, nulls last
        pending.sort((a, b) => {
          const ad = a.due_date ? new Date(a.due_date).getTime() : Infinity;
          const bd = b.due_date ? new Date(b.due_date).getTime() : Infinity;
          return ad - bd;
        });

        const sliced = limit ? pending.slice(0, limit) : pending;
        if (isMounted) setData(sliced);
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
  }, [propertyId, startDate, endDate, limit]);

  return { data, loading, error };
}
