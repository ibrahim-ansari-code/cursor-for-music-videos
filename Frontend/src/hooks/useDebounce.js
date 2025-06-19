import { useState, useEffect } from "react";

// Debounce hook to prevent excessive API calls while typing
const useDebounce = (value, delay = 300) => {
  const [debouncedValue, setDebouncedValue] = useState(value);
  useEffect(() => {
    if (delay < 0) {
      throw new Error("Debounce delay cannot be negative");
    }
    const handler = setTimeout(() => {
       setDebouncedValue(value);
     }, delay);
    return () => {
      clearTimeout(handler);
    };
  }, [value, delay]);
  return debouncedValue;
};

export default useDebounce; 