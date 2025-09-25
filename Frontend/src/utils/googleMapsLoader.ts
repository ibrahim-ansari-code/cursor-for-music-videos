/**
 * Google Maps Loader Singleton
 */

import { Loader } from '@googlemaps/js-api-loader';

// Singleton instance
let loaderInstance: Loader | null = null;
let loadPromise: Promise<void> | null = null;

// Static libraries configuration - use type assertion to match Loader expectations
const GOOGLE_MAPS_LIBRARIES = ['places', 'marker', 'core'] as any;

/**
 * Validates Google Maps environment variables
 */
const validateGoogleMapsConfig = (): { isValid: boolean; errors: string[] } => {
  const errors: string[] = [];
  const apiKey = import.meta.env.VITE_GOOGLE_MAPS_API_KEY;
  const mapId = import.meta.env.VITE_GOOGLE_MAP_ID;
  
  if (!apiKey) {
    errors.push('VITE_GOOGLE_MAPS_API_KEY environment variable is not set');
  } else if (apiKey.length < 20) {
    errors.push('VITE_GOOGLE_MAPS_API_KEY appears to be invalid (too short)');
  }
  
  if (!mapId) {
    console.warn('VITE_GOOGLE_MAP_ID not set, using fallback map ID');
  }
  
  return {
    isValid: errors.length === 0,
    errors
  };
};

/**
 * Creates or returns the singleton Google Maps loader instance
 * Uses dynamic library loading for optimal performance
 */
export const getGoogleMapsLoader = (): Loader => {
  if (!loaderInstance) {
    // Validate configuration first
    const validation = validateGoogleMapsConfig();
    
    if (!validation.isValid) {
      console.error('Google Maps configuration errors:', validation.errors);
      // Don't throw error - let the loader fail gracefully
    }
    
    const apiKey = import.meta.env.VITE_GOOGLE_MAPS_API_KEY;
    
    loaderInstance = new Loader({
      apiKey: apiKey || '',
      version: 'weekly',
      libraries: GOOGLE_MAPS_LIBRARIES,
      language: 'en',
      region: 'CA',
      // Performance optimizations
      mapIds: [
        import.meta.env.VITE_GOOGLE_MAP_ID || '235a15a8eb6db4dcd6108694'
      ],
    });
  }
  return loaderInstance;
};

/**
 * Loads Google Maps API
 */
export const loadGoogleMapsAPI = async (): Promise<void> => {
  if (loadPromise) {
    return loadPromise;
  }

  const validation = validateGoogleMapsConfig();
  if (!validation.isValid) {
    const error = new Error(`Google Maps configuration invalid: ${validation.errors.join(', ')}`);
    throw error;
  }

  const loader = getGoogleMapsLoader();
  
  loadPromise = loader.load().then(() => {
    console.info('Google Maps API successfully loaded');
  }).catch((error) => {
    loadPromise = null;
    throw error;
  });

  return loadPromise;
};

/**
 * Checks if Google Maps is already loaded
 */
export const isGoogleMapsLoaded = (): boolean => {
  return !!(window.google?.maps);
};

/**
 * Gets performance metrics for monitoring
 */
export const getPerformanceMetrics = () => ({
  isLoaded: isGoogleMapsLoaded(),
});

/**
 * Preloads Google Maps API on user intent
 */
export const preloadGoogleMaps = (): void => {
  if (!loadPromise && !window.google?.maps) {
    loadGoogleMapsAPI().catch((error) => {
      console.error('Failed to preload Google Maps:', error);
    });
  }
};

// Type definitions for window.gtag
declare global {
  interface Window {
    gtag?: (
      command: string,
      eventName: string,
      parameters: Record<string, any>
    ) => void;
  }
}