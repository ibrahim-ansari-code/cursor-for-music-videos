import { useEffect, useCallback, useRef } from 'react';
import { UseFormReturn } from 'react-hook-form';
import { PropertyFormData } from '@/types/property';

interface FormRecoveryOptions {
  formId: string;
  autoSaveInterval?: number; // in milliseconds
  enableAutoSave?: boolean;
  onRecover?: (data: Partial<PropertyFormData>) => void;
  onSave?: (data: Partial<PropertyFormData>) => void;
}

interface FormRecoveryReturn {
  saveFormData: () => void;
  restoreFormData: () => boolean;
  clearSavedData: () => void;
  hasSavedData: () => boolean;
  getSavedData: () => Partial<PropertyFormData> | null;
  lastSavedAt: Date | null;
}

// Security constants
const MAX_STORAGE_SIZE = 100000; // 100KB limit per form
const SENSITIVE_FIELDS = [
  'password', 'token', 'secret', 'key', 'ssn', 'credit_card',
  'email', 'phone', 'address', 'date_of_birth', 'birthday', 'birth',
  'license', 'bank_account', 'routing', 'account_number', 'cvv', 'cvc',
  'tax_id', 'ein', 'social', 'passport', 'driver', 'medicare', 
  'personal', 'private', 'confidential', 'sensitive'
];

// Additional PII patterns that require more sophisticated detection
const PII_PATTERNS = [
  /\b\d{3}-?\d{2}-?\d{4}\b/, // SSN pattern
  /\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b/, // Credit card pattern  
  /\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b/, // Email pattern
  /\b\(?(\d{3})\)?[-.\s]?(\d{3})[-.\s]?(\d{4})\b/, // Phone pattern
  /\b\d{1,5}\s+([a-zA-Z]+\s*){1,4}(street|st|avenue|ave|road|rd|lane|ln|drive|dr|court|ct|place|pl|way)\b/i, // Address pattern
];

/**
 * Check if a string value contains PII patterns
 */
function containsPII(value: string): boolean {
  if (typeof value !== 'string') return false;
  return PII_PATTERNS.some(pattern => pattern.test(value));
}

/**
 * Sanitize form data to remove sensitive information
 * Enhanced with pattern matching and value analysis
 */
function sanitizeFormData(data: any, maxDepth: number = 5): any {
  // Prevent infinite recursion and stack overflow attacks
  if (maxDepth <= 0) {
    console.warn('Maximum sanitization depth reached, truncating data');
    return '[TRUNCATED]';
  }

  if (typeof data !== 'object' || data === null) {
    // For primitive values, check for PII patterns
    if (typeof data === 'string' && containsPII(data)) {
      return '[PII_REDACTED]';
    }
    return data;
  }
  
  // Handle arrays
  if (Array.isArray(data)) {
    return data.map(item => sanitizeFormData(item, maxDepth - 1));
  }
  
  const sanitized: any = {};
  for (const [key, value] of Object.entries(data)) {
    const lowerKey = key.toLowerCase();
    
    // Check if field name indicates sensitive data
    const isFieldSensitive = SENSITIVE_FIELDS.some(field => lowerKey.includes(field));
    
    // Check if value contains PII patterns (for string values)
    const isValueSensitive = typeof value === 'string' && containsPII(value);
    
    if (isFieldSensitive || isValueSensitive) {
      sanitized[key] = '[REDACTED]';
    } else if (typeof value === 'object' && value !== null) {
      sanitized[key] = sanitizeFormData(value, maxDepth - 1);
    } else {
      sanitized[key] = value;
    }
  }
  return sanitized;
}

/**
 * Fast hash function for change detection
 * Uses a simple string hash to detect form data changes
 */
function fastHash(str: string): string {
  let hash = 0;
  for (let i = 0; i < str.length; i++) {
    const char = str.charCodeAt(i);
    hash = ((hash << 5) - hash) + char;
    hash = hash & hash; // Convert to 32-bit integer
  }
  return hash.toString(36);
}

/**
 * Enhanced localStorage availability and quota validation
 * Handles edge cases like private browsing, quota exceeded, etc.
 */
function validateStorageAvailable(): boolean {
  if (typeof window === 'undefined' || !window.localStorage) {
    return false;
  }
  
  try {
    // Test basic availability
    const testKey = '__storage_test__';
    const testValue = 'test_value';
    
    localStorage.setItem(testKey, testValue);
    const retrieved = localStorage.getItem(testKey);
    localStorage.removeItem(testKey);
    
    // Verify the value was actually stored and retrieved correctly
    return retrieved === testValue;
  } catch (error) {
    // Handle specific error cases
    if (error instanceof DOMException) {
      // QuotaExceededError or SecurityError in private browsing
      if (error.code === 22 || error.name === 'QuotaExceededError') {
        console.warn('localStorage quota exceeded');
      } else if (error.code === 18 || error.name === 'SecurityError') {
        console.warn('localStorage access denied (possibly private browsing)');
      }
    }
    return false;
  }
}

/**
 * Advanced storage quota management
 * Includes cleanup of old data and space estimation
 */
function manageStorageQuota(): void {
  try {
    if (!validateStorageAvailable()) return;
    
    // Estimate current usage
    let totalSize = 0;
    const formRecoveryKeys: string[] = [];
    
    for (let i = 0; i < localStorage.length; i++) {
      const key = localStorage.key(i);
      if (key?.startsWith('brikli_form_recovery_') || key?.startsWith('brikli_form_metadata_')) {
        const value = localStorage.getItem(key);
        if (value) {
          totalSize += key.length + value.length;
          if (key.startsWith('brikli_form_metadata_')) {
            formRecoveryKeys.push(key);
          }
        }
      }
    }
    
    // If using more than 2MB for form recovery, clean up old data
    if (totalSize > 2 * 1024 * 1024) {
      // Get metadata and sort by age
      const metadataEntries = formRecoveryKeys
        .map(key => {
          const metadata = localStorage.getItem(key);
          if (metadata) {
            try {
              const parsed = JSON.parse(metadata);
              return { key, metadata: parsed, savedAt: new Date(parsed.savedAt) };
            } catch {
              // Remove corrupted metadata
              localStorage.removeItem(key);
              return null;
            }
          }
          return null;
        })
        .filter((entry): entry is NonNullable<typeof entry> => entry !== null)
        .sort((a, b) => a.savedAt.getTime() - b.savedAt.getTime()); // Oldest first
      
      // Remove oldest entries until we're under the threshold
      for (const entry of metadataEntries) {
        const dataKey = entry.key.replace('brikli_form_metadata_', 'brikli_form_recovery_');
        localStorage.removeItem(entry.key);
        localStorage.removeItem(dataKey);
        
        // Recalculate size
        totalSize = 0;
        for (let i = 0; i < localStorage.length; i++) {
          const key = localStorage.key(i);
          if (key?.startsWith('brikli_form_recovery_') || key?.startsWith('brikli_form_metadata_')) {
            const value = localStorage.getItem(key);
            if (value) {
              totalSize += key.length + value.length;
            }
          }
        }
        
        if (totalSize < 1024 * 1024) break; // Stop when under 1MB
      }
    }
  } catch (error) {
    console.warn('Failed to manage storage quota:', error);
  }
}

/**
 * Check if storage operation would exceed quota
 */
function checkStorageQuota(data: string): boolean {
  if (data.length > MAX_STORAGE_SIZE) {
    console.warn('Form data too large for storage:', data.length, 'bytes');
    return false;
  }
  return true;
}

/**
 * Custom hook for form recovery with auto-save and restore functionality
 * Provides bulletproof form data persistence to prevent data loss on errors
 */
export function useFormRecovery(
  form: UseFormReturn<PropertyFormData>,
  options: FormRecoveryOptions
): FormRecoveryReturn {
  const {
    formId,
    autoSaveInterval = 30000, // Default: 30 seconds
    enableAutoSave = true,
    onRecover,
    onSave,
  } = options;

  const lastSavedAtRef = useRef<Date | null>(null);
  const autoSaveIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const isRestoringRef = useRef(false);
  const lastSavedDataHashRef = useRef<string>('');
  const saveInProgressRef = useRef(false);

  const getStorageKey = useCallback(() => `brikli_form_recovery_${formId}`, [formId]);
  const getMetadataKey = useCallback(() => `brikli_form_metadata_${formId}`, [formId]);

  // Save form data to localStorage with performance optimizations
  const saveFormData = useCallback(() => {
    try {
      // Skip if save already in progress to prevent race conditions
      if (saveInProgressRef.current) {
        return;
      }
      
      // Check if localStorage is available
      if (!validateStorageAvailable()) {
        console.warn('localStorage not available, skipping form save');
        return;
      }

      const currentValues = form.getValues();
      
      // Fast change detection using hash
      const currentDataString = JSON.stringify(currentValues);
      const currentHash = fastHash(currentDataString);
      
      if (currentHash === lastSavedDataHashRef.current) {
        // No changes detected, skip save
        return;
      }
      
      saveInProgressRef.current = true;
      
      const storageKey = getStorageKey();
      const metadataKey = getMetadataKey();
      
      // Only save if there's meaningful data (not just empty form)
      const hasData = Object.values(currentValues).some(value => {
        if (value === null || value === undefined || value === '') return false;
        if (Array.isArray(value)) {
          return value.length > 0 && value.some(item => item !== null && item !== undefined && item !== '');
        }
        if (typeof value === 'object' && value !== null && Object.keys(value).length === 0) return false;
        return true;
      });

      if (!hasData) {
        saveInProgressRef.current = false;
        return;
      }

      // Use requestIdleCallback for non-blocking operation when available
      const performSave = () => {
        try {
          // Sanitize sensitive data
          const sanitizedData = sanitizeFormData(currentValues);
          const dataString = JSON.stringify(sanitizedData);

          // Check storage quota
          if (!checkStorageQuota(dataString)) {
            console.warn('Form data too large for localStorage, attempting cleanup...');
            manageStorageQuota();
            
            // Try again after cleanup
            if (!checkStorageQuota(dataString)) {
              console.warn('Form data still too large after cleanup, skipping save');
              saveInProgressRef.current = false;
              return;
            }
          }

          // Save form data with retry logic for quota errors
          try {
            localStorage.setItem(storageKey, dataString);
          } catch (error) {
            if (error instanceof DOMException && (error.code === 22 || error.name === 'QuotaExceededError')) {
              console.warn('Storage quota exceeded, attempting cleanup and retry...');
              manageStorageQuota();
              
              try {
                localStorage.setItem(storageKey, dataString);
              } catch (retryError) {
                console.warn('Failed to save after cleanup, storage may be full');
                saveInProgressRef.current = false;
                return;
              }
            } else {
              throw error; // Re-throw non-quota errors
            }
          }
          
          // Save metadata
          const metadata = {
            savedAt: new Date().toISOString(),
            version: '1.0',
            formId,
            checksum: btoa(dataString).slice(-10), // Simple integrity check
          };
          localStorage.setItem(metadataKey, JSON.stringify(metadata));
          
          // Update state
          lastSavedAtRef.current = new Date();
          lastSavedDataHashRef.current = currentHash;
          
          if (onSave) {
            onSave(sanitizedData);
          }

          if (import.meta.env.DEV) {
            console.log('Form data auto-saved:', formId);
          }
        } catch (error) {
          console.warn('Failed to save form data:', error);
        } finally {
          saveInProgressRef.current = false;
        }
      };

      // Use requestIdleCallback for better performance, fallback to setTimeout
      if (typeof window !== 'undefined' && 'requestIdleCallback' in window) {
        (window as any).requestIdleCallback(performSave, { timeout: 5000 });
      } else {
        setTimeout(performSave, 0); // Defer to next tick
      }
      
    } catch (error) {
      console.warn('Failed to save form data:', error);
      saveInProgressRef.current = false;
    }
  }, [form, getStorageKey, getMetadataKey, formId, onSave]);

  // Validate restored data structure and content
  const validateRestoredData = (data: any): data is Partial<PropertyFormData> => {
    if (!data || typeof data !== 'object') return false;
    
    // Check for malicious or unexpected properties
    const allowedTopLevelKeys = [
      'name', 'address', 'property_type', 'description', 'units', 
      'acquisition_cost', 'mortgage_amount', 'down_payment', 
      'type_specific_details', 'shared_amenities'
    ];
    
    for (const key in data) {
      if (!allowedTopLevelKeys.includes(key)) {
        console.warn('Unknown property found in restored data:', key);
        return false;
      }
      
      const value = data[key];
      
      // Validate data types and reasonable limits
      if (key === 'name' && (typeof value !== 'string' || value.length > 200)) {
        console.warn('Invalid name field in restored data');
        return false;
      }
      
      if (key === 'description' && value && (typeof value !== 'string' || value.length > 2000)) {
        console.warn('Invalid description field in restored data');
        return false;
      }
      
      if (['acquisition_cost', 'mortgage_amount', 'down_payment'].includes(key)) {
        if (value && (typeof value !== 'number' || value < 0 || value > 1e12)) {
          console.warn(`Invalid monetary field ${key} in restored data`);
          return false;
        }
      }
      
      if (key === 'units' && value && (typeof value !== 'number' || value < 1 || value > 10000)) {
        console.warn('Invalid units field in restored data');
        return false;
      }
      
      // Prevent script injection in string fields
      if (typeof value === 'string' && /<script|javascript:|data:/i.test(value)) {
        console.warn('Potential script injection detected in restored data');
        return false;
      }
      
      // Check for suspicious nested object sizes
      if (typeof value === 'object' && value !== null) {
        const jsonSize = JSON.stringify(value).length;
        if (jsonSize > 50000) { // 50KB limit per field
          console.warn(`Field ${key} too large in restored data: ${jsonSize} bytes`);
          return false;
        }
      }
    }
    
    return true;
  };

  // Restore form data from localStorage
  const restoreFormData = useCallback((): boolean => {
    try {
      if (!validateStorageAvailable()) {
        console.warn('localStorage not available, cannot restore data');
        return false;
      }

      const storageKey = getStorageKey();
      const metadataKey = getMetadataKey();
      
      const savedData = localStorage.getItem(storageKey);
      const savedMetadata = localStorage.getItem(metadataKey);
      
      if (!savedData || !savedMetadata) return false;

      let parsedData: Partial<PropertyFormData>;
      let parsedMetadata: any;

      try {
        parsedData = JSON.parse(savedData) as Partial<PropertyFormData>;
        parsedMetadata = JSON.parse(savedMetadata);
      } catch (parseError) {
        console.warn('Failed to parse saved data, clearing corrupted data');
        localStorage.removeItem(storageKey);
        localStorage.removeItem(metadataKey);
        return false;
      }

      // Validate metadata
      if (parsedMetadata.formId !== formId) {
        console.warn('Form ID mismatch in saved data');
        return false;
      }

      // Validate data structure
      if (!validateRestoredData(parsedData)) {
        console.warn('Invalid data structure in saved form data');
        localStorage.removeItem(storageKey);
        localStorage.removeItem(metadataKey);
        return false;
      }

      // Check if data is recent (within 24 hours) and validate date
      const savedAt = new Date(parsedMetadata.savedAt);
      if (isNaN(savedAt.getTime())) {
        console.warn('Invalid date in saved metadata, clearing corrupted data');
        localStorage.removeItem(storageKey);
        localStorage.removeItem(metadataKey);
        return false;
      }
      
      const hoursSinceSave = (Date.now() - savedAt.getTime()) / (1000 * 60 * 60);
      if (hoursSinceSave > 24) {
        // Clear old data
        localStorage.removeItem(storageKey);
        localStorage.removeItem(metadataKey);
        return false;
      }

      isRestoringRef.current = true;

      // Restore form data
      Object.entries(parsedData).forEach(([key, value]) => {
        if (value !== null && value !== undefined) {
          try {
            form.setValue(key as keyof PropertyFormData, value);
          } catch (error) {
            console.warn(`Failed to restore field ${key}:`, error);
          }
        }
      });

      lastSavedAtRef.current = savedAt;
      
      if (onRecover) {
        onRecover(parsedData);
      }

      setTimeout(() => {
        isRestoringRef.current = false;
      }, 100);

      if (import.meta.env.DEV) {
        console.log('Form data restored:', formId, parsedData);
      }

      return true;
    } catch (error) {
      console.warn('Failed to restore form data:', error);
      return false;
    }
  }, [form, getStorageKey, getMetadataKey, formId, onRecover]);

  // Clear saved form data
  const clearSavedData = useCallback(() => {
    try {
      const storageKey = getStorageKey();
      const metadataKey = getMetadataKey();
      
      localStorage.removeItem(storageKey);
      localStorage.removeItem(metadataKey);
      lastSavedAtRef.current = null;

      if (import.meta.env.DEV) {
        console.log('Form data cleared:', formId);
      }
    } catch (error) {
      console.warn('Failed to clear form data:', error);
    }
  }, [getStorageKey, getMetadataKey, formId]);

  // Check if saved data exists
  const hasSavedData = useCallback((): boolean => {
    try {
      const storageKey = getStorageKey();
      const metadataKey = getMetadataKey();
      
      const savedData = localStorage.getItem(storageKey);
      const savedMetadata = localStorage.getItem(metadataKey);
      
      if (!savedData || !savedMetadata) return false;

      const parsedMetadata = JSON.parse(savedMetadata);
      return parsedMetadata.formId === formId;
    } catch (error) {
      return false;
    }
  }, [getStorageKey, getMetadataKey, formId]);

  // Get saved data without restoring
  const getSavedData = useCallback((): Partial<PropertyFormData> | null => {
    try {
      const storageKey = getStorageKey();
      const savedData = localStorage.getItem(storageKey);
      
      if (!savedData) return null;
      
      return JSON.parse(savedData) as Partial<PropertyFormData>;
    } catch (error) {
      console.warn('Failed to get saved data:', error);
      return null;
    }
  }, [getStorageKey]);

  // Set up auto-save with proper cleanup
  useEffect(() => {
    if (!enableAutoSave) return;

    let isSubscriptionActive = true;
    let currentTimeout: NodeJS.Timeout | null = null;

    const subscription = form.watch(() => {
      // Don't auto-save while restoring data or if subscription is no longer active
      if (isRestoringRef.current || !isSubscriptionActive) return;

      // Clear existing timeout
      if (currentTimeout) {
        clearTimeout(currentTimeout);
        currentTimeout = null;
      }
      
      // Clear the ref timeout as well to prevent conflicts
      if (autoSaveIntervalRef.current) {
        clearTimeout(autoSaveIntervalRef.current);
        autoSaveIntervalRef.current = null;
      }

      // Set new timeout with proper cleanup check
      currentTimeout = setTimeout(() => {
        if (isSubscriptionActive && !isRestoringRef.current) {
          saveFormData();
        }
        currentTimeout = null;
      }, autoSaveInterval);
      
      // Update ref for external cleanup
      autoSaveIntervalRef.current = currentTimeout;
    });

    return () => {
      isSubscriptionActive = false;
      subscription.unsubscribe();
      
      // Clean up all timeouts
      if (currentTimeout) {
        clearTimeout(currentTimeout);
      }
      if (autoSaveIntervalRef.current) {
        clearTimeout(autoSaveIntervalRef.current);
        autoSaveIntervalRef.current = null;
      }
    };
  }, [form, enableAutoSave, autoSaveInterval, saveFormData]);

  // Save on page unload with race condition protection
  useEffect(() => {
    let isUnloadHandlerActive = true;
    
    const handleBeforeUnload = () => {
      if (!isRestoringRef.current && isUnloadHandlerActive) {
        // Use synchronous approach for beforeunload to ensure data is saved
        try {
          if (!validateStorageAvailable()) return;
          
          const currentValues = form.getValues();
          const sanitizedData = sanitizeFormData(currentValues);
          const dataString = JSON.stringify(sanitizedData);
          
          if (checkStorageQuota(dataString)) {
            const storageKey = `brikli_form_recovery_${formId}`;
            const metadataKey = `brikli_form_metadata_${formId}`;
            
            localStorage.setItem(storageKey, dataString);
            localStorage.setItem(metadataKey, JSON.stringify({
              savedAt: new Date().toISOString(),
              version: '1.0',
              formId,
              checksum: btoa(dataString).slice(-10),
            }));
          }
        } catch (error) {
          console.warn('Failed to save form data on unload:', error);
        }
      }
    };

    window.addEventListener('beforeunload', handleBeforeUnload);
    
    return () => {
      isUnloadHandlerActive = false;
      window.removeEventListener('beforeunload', handleBeforeUnload);
    };
  }, [formId]); // Remove saveFormData dependency to prevent unnecessary re-renders

  // Comprehensive cleanup on unmount
  useEffect(() => {
    return () => {
      // Clear all timeouts
      if (autoSaveIntervalRef.current) {
        clearTimeout(autoSaveIntervalRef.current);
        autoSaveIntervalRef.current = null;
      }
      
      // Mark component as unmounted to prevent race conditions
      isRestoringRef.current = false;
      saveInProgressRef.current = false;
      
      // Reset state
      lastSavedAtRef.current = null;
      lastSavedDataHashRef.current = '';
    };
  }, []);

  return {
    saveFormData,
    restoreFormData,
    clearSavedData,
    hasSavedData,
    getSavedData,
    lastSavedAt: lastSavedAtRef.current,
  };
}