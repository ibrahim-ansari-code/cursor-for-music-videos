/**
 * Google Maps Loader Singleton
 * YC-grade performance optimization for Google Maps loading
 * Implements best practices from 2025 research
 */

import { Loader } from '@googlemaps/js-api-loader';

// Singleton instance
let loaderInstance: Loader | null = null;
let loadPromise: Promise<void> | null = null;

// Performance metrics
const performanceMetrics = {
  startTime: 0,
  endTime: 0,
  loadDuration: 0,
};

// Static libraries configuration - use type assertion to match Loader expectations
const GOOGLE_MAPS_LIBRARIES = ['places', 'marker'] as any;

/**
 * Creates or returns the singleton Google Maps loader instance
 * Uses dynamic library loading for optimal performance
 */
export const getGoogleMapsLoader = (): Loader => {
  if (!loaderInstance) {
    const apiKey = import.meta.env.VITE_GOOGLE_MAPS_API_KEY;
    
    if (!apiKey) {
      console.warn('Google Maps API key not found. Maps functionality will be limited.');
    }
    
    loaderInstance = new Loader({
      apiKey: apiKey || '',
      version: 'weekly',
      libraries: GOOGLE_MAPS_LIBRARIES,
      language: 'en',
      region: 'CA',
      // Performance optimizations
      mapIds: [], // Add your map IDs here for preloading
    });
  }
  return loaderInstance;
};

/**
 * Loads Google Maps API with performance tracking
 * Returns a promise that resolves when the API is loaded
 */
export const loadGoogleMapsAPI = async (): Promise<void> => {
  // Return existing promise if already loading
  if (loadPromise) {
    return loadPromise;
  }

  // Start performance tracking
  performanceMetrics.startTime = performance.now();

  const loader = getGoogleMapsLoader();
  
  loadPromise = loader.load().then(() => {
    // Track performance metrics
    performanceMetrics.endTime = performance.now();
    performanceMetrics.loadDuration = performanceMetrics.endTime - performanceMetrics.startTime;
    
    // Log performance metrics in development
    if (import.meta.env.DEV) {
      console.log(`Google Maps API loaded in ${performanceMetrics.loadDuration.toFixed(2)}ms`);
    }

    // Report to analytics if available
    if (typeof window !== 'undefined' && window.gtag) {
      window.gtag('event', 'timing_complete', {
        name: 'google_maps_load',
        value: Math.round(performanceMetrics.loadDuration),
        event_category: 'JS Dependencies',
      });
    }
  });

  return loadPromise;
};

/**
 * Preloads Google Maps API on user intent
 * Call this on hover or focus of the trigger element
 */
export const preloadGoogleMaps = (): void => {
  // Only preload if not already loaded or loading
  if (!loadPromise && !window.google?.maps) {
    loadGoogleMapsAPI().catch((error) => {
      console.error('Failed to preload Google Maps:', error);
    });
  }
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
  ...performanceMetrics,
  isLoaded: isGoogleMapsLoaded(),
});

/**
 * Cleans up the loader instance (useful for testing)
 */
export const resetGoogleMapsLoader = (): void => {
  loaderInstance = null;
  loadPromise = null;
  performanceMetrics.startTime = 0;
  performanceMetrics.endTime = 0;
  performanceMetrics.loadDuration = 0;
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