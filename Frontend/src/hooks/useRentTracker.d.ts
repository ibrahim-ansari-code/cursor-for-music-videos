interface RentTrackerParams {
  month: number;
  year: number;
  propertyId?: string;
}

interface RentData {
  lease_id: number | string;
  tenant_name: string;
  remaining_due: number;
  status: string;
}

interface UseRentTrackerReturn {
  data: RentData[];
  loading: boolean;
  error: Error | null;
}

declare function useRentTracker(params: RentTrackerParams): UseRentTrackerReturn;

export default useRentTracker;

