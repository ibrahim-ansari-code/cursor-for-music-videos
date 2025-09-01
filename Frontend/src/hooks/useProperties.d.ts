import { Property } from '../types/property';

interface UsePropertiesReturn {
  properties: Property[];
  loading: boolean;
  error: string | null;
  refetch: () => void;
}

declare function useProperties(): UsePropertiesReturn;

export default useProperties;