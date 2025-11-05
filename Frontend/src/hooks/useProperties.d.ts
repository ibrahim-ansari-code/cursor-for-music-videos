import { Property } from '../types/property';

interface PropertyOption {
  id: string;
  name: string;
}

interface UsePropertiesReturn {
  properties: Property[];
  loading: boolean;
  error: Error | string | null;
  options: PropertyOption[];
}

declare function useProperties(): UsePropertiesReturn;

export default useProperties;