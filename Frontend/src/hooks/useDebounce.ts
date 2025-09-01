import { useRef, useCallback, useEffect } from 'react';

/**
 * Custom hook for debouncing function calls with proper cleanup
 * Industry-standard implementation with AbortController support
 */
export function useDebounce<T extends (...args: any[]) => void>(
  callback: T,
  delay: number = 300
): [T, () => void] {
  const timeoutRef = useRef<NodeJS.Timeout | null>(null);
  const abortControllerRef = useRef<AbortController | null>(null);
  const callbackRef = useRef(callback);

  // Always update the callback ref to avoid stale closures
  useEffect(() => {
    callbackRef.current = callback;
  });

  const debouncedCallback = useCallback(
    ((...args: Parameters<T>) => {
      // Cancel previous timeout
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }

      // Cancel previous async operations
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }

      // Create new abort controller for this operation
      abortControllerRef.current = new AbortController();

      timeoutRef.current = setTimeout(() => {
        try {
          callbackRef.current(...args);
        } catch (error) {
          console.error('Debounced callback error:', error);
        }
      }, delay);
    }) as T,
    [delay]
  );

  const cancel = useCallback(() => {
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
      timeoutRef.current = null;
    }
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
  }, []);

  // Cleanup on unmount
  useEffect(() => {
    return cancel;
  }, [cancel]);

  return [debouncedCallback, cancel];
}

/**
 * Hook for debouncing form field updates with proper conflict resolution
 * Designed specifically for complex forms with multiple interdependent fields
 */
export function useFormFieldDebounce<T>(
  initialValue: T,
  onUpdate: (value: T) => void,
  delay: number = 300,
  conflictResolver?: (current: T, incoming: T) => T
) {
  const currentValueRef = useRef<T>(initialValue);
  const pendingValueRef = useRef<T | null>(null);
  const isUpdatingRef = useRef(false);

  const [debouncedUpdate, cancelUpdate] = useDebounce((value: T) => {
    // Check for conflicts if a conflict resolver is provided
    if (conflictResolver && pendingValueRef.current !== null) {
      const resolvedValue = conflictResolver(currentValueRef.current, value);
      onUpdate(resolvedValue);
      currentValueRef.current = resolvedValue;
    } else {
      onUpdate(value);
      currentValueRef.current = value;
    }
    
    pendingValueRef.current = null;
    isUpdatingRef.current = false;
  }, delay);

  const updateValue = useCallback((newValue: T) => {
    if (isUpdatingRef.current) {
      // Store as pending if update is in progress
      pendingValueRef.current = newValue;
      return;
    }

    isUpdatingRef.current = true;
    pendingValueRef.current = newValue;
    debouncedUpdate(newValue);
  }, [debouncedUpdate]);

  const setValue = useCallback((value: T) => {
    currentValueRef.current = value;
    cancelUpdate(); // Cancel any pending updates
    isUpdatingRef.current = false;
    pendingValueRef.current = null;
  }, [cancelUpdate]);

  return {
    updateValue,
    setValue,
    cancel: cancelUpdate,
    isPending: () => isUpdatingRef.current,
    getCurrentValue: () => currentValueRef.current
  };
}