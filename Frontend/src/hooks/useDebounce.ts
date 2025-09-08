import { useState, useEffect, useRef, useCallback } from 'react';

// Value-based debounce hook (new API)
function useDebouncedValue<T>(value: T, delay: number): T {
  const [debouncedValue, setDebouncedValue] = useState<T>(value);

  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedValue(value);
    }, delay);

    return () => {
      clearTimeout(handler);
    };
  }, [value, delay]);

  return debouncedValue;
}

// Callback-based debounce hook (original API for backward compatibility)
export function useDebounceCallback<T extends (...args: any[]) => void>(
  callback: T,
  delay: number = 300
): [T, () => void] {
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  
  const debouncedCallback = useCallback(
    (...args: Parameters<T>) => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }
      
      timeoutRef.current = setTimeout(() => {
        callback(...args);
      }, delay);
    },
    [callback, delay]
  ) as T;
  
  const cancel = useCallback(() => {
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
      timeoutRef.current = null;
    }
  }, []);
  
  // Cancel any pending timeout when callback or delay changes
  useEffect(() => {
    return () => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
        timeoutRef.current = null;
      }
    };
  }, [callback, delay]);
  
  // Cancel pending timeout on unmount
  useEffect(() => {
    return () => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }
    };
  }, []);
  
  return [debouncedCallback, cancel];
}

// Main useDebounce function - supports both APIs for compatibility
function useDebounce<T>(value: T, delay: number): T;
function useDebounce<T extends (...args: any[]) => void>(
  callback: T,
  delay?: number
): [T, () => void];
function useDebounce<T>(valueOrCallback: T, delay: number = 300): T | [T, () => void] {
  // If it's a function, use callback-based API
  if (typeof valueOrCallback === 'function') {
    return useDebounceCallback(valueOrCallback as any, delay);
  }
  // Otherwise, use value-based API
  return useDebouncedValue(valueOrCallback, delay);
}

// Original function signature
export function useFormFieldDebounce(
  fieldName: string,
  value: unknown,
  onChange: (field: string, value: unknown) => void,
  delay?: number
): unknown;

// Overload for direct callback usage with conflict resolution
export function useFormFieldDebounce<T>(
  value: T,
  callback: (value: T) => void,
  delay: number,
  conflictResolver?: (current: T, incoming: T) => T
): {
  updateValue: (newValue: T) => void;
  cancel: () => void;
};

// Implementation
export function useFormFieldDebounce<T = unknown>(
  fieldNameOrValue: string | T,
  valueOrCallback: unknown | ((value: T) => void),
  onChangeOrDelay: ((field: string, value: unknown) => void) | number,
  delayOrConflictResolver?: number | ((current: T, incoming: T) => T)
): unknown | { updateValue: (newValue: T) => void; cancel: () => void } {
  // Handle overload 1: (fieldName, value, onChange, delay?)
  if (typeof fieldNameOrValue === 'string') {
    const fieldName = fieldNameOrValue;
    const value = valueOrCallback;
    // Add runtime validation for type casting
    if (typeof onChangeOrDelay !== 'function') {
      throw new Error('useFormFieldDebounce: onChange must be a function when first parameter is string');
    }
    const onChange = onChangeOrDelay as (field: string, value: unknown) => void;
    const delay = (typeof delayOrConflictResolver === 'number' ? delayOrConflictResolver : 300);
    
    const debouncedValue = useDebounce(value, delay);
    
    useEffect(() => {
      if (debouncedValue !== undefined) {
        onChange(fieldName, debouncedValue);
      }
    }, [debouncedValue, fieldName, onChange]);

    return debouncedValue;
  } 
  
  // Handle overload 2: (value, callback, delay, conflictResolver?)
  else {
    const initialValue = fieldNameOrValue as T;
    // Add runtime validation for type casting
    if (typeof valueOrCallback !== 'function') {
      throw new Error('useFormFieldDebounce: callback must be a function when first parameter is not string');
    }
    if (typeof onChangeOrDelay !== 'number') {
      throw new Error('useFormFieldDebounce: delay must be a number when first parameter is not string');
    }
    const callback = valueOrCallback as (value: T) => void;
    const delay = onChangeOrDelay as number;
    const conflictResolver = (typeof delayOrConflictResolver === 'function' ? delayOrConflictResolver : undefined) as ((current: T, incoming: T) => T) | undefined;
    
    const [currentValue, setCurrentValue] = useState(initialValue);
    const [resolvedValue, setResolvedValue] = useState(initialValue);
    
    // Apply conflict resolution if provided - safe functional state updater
    useEffect(() => {
      setResolvedValue(prev => {
        const resolved = conflictResolver ? conflictResolver(prev, currentValue) : currentValue;
        return resolved === prev ? prev : resolved;
      });
    }, [currentValue, conflictResolver]);
    
    // Use callback-based debounce to get proper cancel functionality
    const [debouncedCallback, cancelDebounce] = useDebounceCallback(
      (value: T) => {
        if (value !== undefined) {
          callback(value);
        }
      },
      delay
    );
    
    // Call the debounced callback when resolved value changes
    useEffect(() => {
      debouncedCallback(resolvedValue);
    }, [resolvedValue, debouncedCallback]);

    return {
      updateValue: (newValue: T) => {
        setCurrentValue(newValue);
      },
      cancel: () => {
        cancelDebounce();
        // Reset to current resolved value to cancel pending changes
        setResolvedValue(currentValue);
      }
    };
  }
}

export default useDebounce;