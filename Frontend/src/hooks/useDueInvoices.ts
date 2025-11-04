import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { fetchInvoices } from "../utils/api";
import { QUERY_KEYS } from "./queryKeys";

interface Invoice {
  id: number;
  status: string;
  due_date?: string;
  amount: number | string;
  tenant?: {
    full_name?: string;
  };
  property?: {
    name?: string;
  };
  invoice_number?: string;
  [key: string]: any;
}

interface InvoicesResponse {
  items?: Invoice[];
}

interface UseDueInvoicesParams {
  propertyId?: string;
  startDate?: string;
  endDate?: string;
  limit?: number;
}

interface QueryParams {
  property_id?: number;
  start_date?: string;
  end_date?: string;
}

interface UseDueInvoicesReturn {
  data: Invoice[];
  loading: boolean;
  error: Error | null;
}

// Fetch top due invoices (Pending/Overdue), filtered by property and date window
export default function useDueInvoices({ 
  propertyId, 
  startDate, 
  endDate, 
  limit = 5 
}: UseDueInvoicesParams): UseDueInvoicesReturn {
  // Build query parameters
  const queryParams = useMemo<QueryParams>(() => {
    const params: QueryParams = {};
    if (propertyId) {
      const numericId = typeof propertyId === 'string' ? parseInt(propertyId, 10) : propertyId;
      if (!isNaN(numericId)) {
        params.property_id = numericId;
      }
    }
    if (startDate) params.start_date = startDate;
    if (endDate) params.end_date = endDate;
    return params;
  }, [propertyId, startDate, endDate]);

  // Use TanStack Query internally
  const { data: invoicesResponse, isLoading: loading, error } = useQuery<Invoice[] | InvoicesResponse>({
    queryKey: QUERY_KEYS.dashboard.dueInvoices({ ...queryParams, limit }),
    queryFn: () => fetchInvoices(queryParams),
    staleTime: 1 * 60 * 1000, // 1 minute for due invoices (need fresh data)
  });

  // Process data to extract due invoices
  const data = useMemo<Invoice[]>(() => {
    if (!invoicesResponse) return [];
    
    const all = Array.isArray(invoicesResponse) 
      ? invoicesResponse 
      : (invoicesResponse as InvoicesResponse)?.items || [];

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

    return limit ? pending.slice(0, limit) : pending;
  }, [invoicesResponse, limit]);

  return { data, loading, error: error as Error | null };
}

