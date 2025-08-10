import { useEffect, useState } from "react";
import { fetchProperties as fetchPropertiesApi } from "../utils/api/properties";

export default function useProperties() {
  const [properties, setProperties] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let isMounted = true;
    const controller = new AbortController();

    const load = async () => {
      try {
        setLoading(true);
        const data = await fetchPropertiesApi({}, { signal: controller.signal });
        if (isMounted) setProperties(data);
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
  }, []);

  const options = [{ id: "all", name: "All Properties" }, ...properties];

  return { properties, loading, error, options };
}
