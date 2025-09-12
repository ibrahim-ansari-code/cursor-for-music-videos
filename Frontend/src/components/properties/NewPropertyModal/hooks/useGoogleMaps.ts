import { useEffect, useState, useRef } from 'react';
import { loadGoogleMapsAPI, isGoogleMapsLoaded, getPerformanceMetrics } from '@/utils/googleMapsLoader';

// Modern Places API utilities
export const loadPlacesLibrary = async () => {
  if (window.google && window.google.maps) {
    const { Place, AutocompleteSuggestion } = await google.maps.importLibrary('places') as google.maps.PlacesLibrary;
    return { Place, AutocompleteSuggestion };
  }
  throw new Error('Google Maps not loaded');
};

// Rate limiting helper
const createRateLimiter = (maxRequests: number, timeWindow: number) => {
  let requests: number[] = [];
  let cleanupTimer: NodeJS.Timeout | null = null;
  
  const scheduleCleanup = () => {
    if (cleanupTimer) clearTimeout(cleanupTimer);
    cleanupTimer = setTimeout(() => {
      const now = Date.now();
      const cutoff = now - timeWindow;
      requests = requests.filter(timestamp => timestamp >= cutoff);
      
      // Schedule next cleanup if there are still requests
      if (requests.length > 0) {
        scheduleCleanup();
      }
    }, timeWindow);
  };
  
  return () => {
    const now = Date.now();
    const cutoff = now - timeWindow;
    
    // Remove old requests
    requests = requests.filter(timestamp => timestamp >= cutoff);
    
    if (requests.length >= maxRequests) {
      return false; // Rate limit exceeded
    }
    
    requests.push(now);
    scheduleCleanup();
    return true;
  };
};

// Create rate limiters for different API calls
const autocompleteLimiter = createRateLimiter(10, 1000); // 10 requests per second
const geocodeLimiter = createRateLimiter(5, 1000); // 5 requests per second

export const useGoogleMaps = () => {
  const [isMapReady, setIsMapReady] = useState(false);
  const [isMapConstructorReady, setIsMapConstructorReady] = useState(false);
  const [userLocation, _setUserLocation] = useState<{ lat: number; lng: number } | null>(null);
  const [loadError, setLoadError] = useState<Error | null>(null);
  const [loadMetrics, setLoadMetrics] = useState<ReturnType<typeof getPerformanceMetrics> | null>(null);
  const pollingIntervalRef = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    let isMounted = true;
    
    const checkMapConstructor = () => {
      const hasMapConstructor = !!(window.google?.maps?.Map);
      if (isMounted) {
        setIsMapConstructorReady(hasMapConstructor);
      }
      return hasMapConstructor;
    };

    const startPollingForConstructor = () => {
      // Clear any existing polling interval
      if (pollingIntervalRef.current) {
        clearInterval(pollingIntervalRef.current);
        pollingIntervalRef.current = null;
      }

      // Short polling to check for constructor availability
      // This prevents the map from being stuck in loading skeleton
      pollingIntervalRef.current = setInterval(() => {
        const constructorReady = checkMapConstructor();
        
        if (constructorReady) {
          // Constructor is ready, stop polling
          if (pollingIntervalRef.current) {
            clearInterval(pollingIntervalRef.current);
            pollingIntervalRef.current = null;
          }
        }
      }, 100); // Check every 100ms

      // Safety timeout to prevent infinite polling
      setTimeout(() => {
        if (isMounted && pollingIntervalRef.current) {
          clearInterval(pollingIntervalRef.current);
          pollingIntervalRef.current = null;
          // Final check after timeout
          checkMapConstructor();
        }
      }, 5000); // Stop polling after 5 seconds
    };

    // Check if already loaded
    if (isGoogleMapsLoaded()) {
      setIsMapReady(true);
      setLoadMetrics(getPerformanceMetrics());
      
      const constructorReady = checkMapConstructor();
      if (!constructorReady) {
        // API is loaded but constructor not ready yet, start polling
        startPollingForConstructor();
      }
      return;
    }

    // Load Google Maps API using the singleton loader
    loadGoogleMapsAPI()
      .then(() => {
        if (!isMounted) return;
        
        setIsMapReady(true);
        const metrics = getPerformanceMetrics();
        setLoadMetrics(metrics);
        
        // Check if Map constructor is available after loading
        const constructorReady = checkMapConstructor();
        
        if (!constructorReady) {
          // API loaded but constructor not immediately ready, start polling
          startPollingForConstructor();
        }
        
        // Log performance metrics in development
        if (import.meta.env.DEV) {
          console.log('Google Maps loaded via optimized loader:', metrics);
        }
      })
      .catch((error) => {
        if (isMounted) {
          console.error('Failed to load Google Maps:', error);
          setLoadError(error);
        }
      });

    // Cleanup function to prevent memory leaks
    return () => {
      isMounted = false;
      if (pollingIntervalRef.current) {
        clearInterval(pollingIntervalRef.current);
        pollingIntervalRef.current = null;
      }
    };
  }, []);

  return {
    isLoaded: isMapReady,
    isMapConstructorReady,
    loadError,
    userLocation,
    loadMetrics, // Expose metrics for monitoring
  };
};

export const searchNearbyPlaces = async (
  location: google.maps.LatLngLiteral,
  type: string,
  radius: number = 1000
): Promise<google.maps.places.PlaceResult[]> => {
  return new Promise((resolve, reject) => {
    if (!window.google || !window.google.maps) {
      reject(new Error('Google Maps not loaded'));
      return;
    }

    const service = new google.maps.places.PlacesService(
      document.createElement('div')
    );

    const request = {
      location: new google.maps.LatLng(location.lat, location.lng),
      radius,
      type,
    };

    service.nearbySearch(request, (results, status) => {
      if (status === google.maps.places.PlacesServiceStatus.OK && results) {
        resolve(results);
      } else {
        resolve([]);
      }
    });
  });
};

export const getPlaceDetails = async (
  placeId: string
): Promise<google.maps.places.PlaceResult | null> => {
  return new Promise((resolve, reject) => {
    if (!window.google || !window.google.maps) {
      reject(new Error('Google Maps not loaded'));
      return;
    }

    const service = new google.maps.places.PlacesService(
      document.createElement('div')
    );

    const request = {
      placeId,
      fields: [
        'name',
        'formatted_address',
        'geometry',
        'address_components',
        'types',
        'plus_code',
        'viewport',
        'utc_offset_minutes',
      ],
    };

    service.getDetails(request, (place, status) => {
      if (status === google.maps.places.PlacesServiceStatus.OK && place) {
        resolve(place);
      } else {
        resolve(null);
      }
    });
  });
};

export const geocodeAddress = async (
  address: string
): Promise<google.maps.GeocoderResult | null> => {
  // Check rate limit
  if (!geocodeLimiter()) {
    return null;
  }
  
  return new Promise((resolve, reject) => {
    if (!window.google || !window.google.maps) {
      reject(new Error('Google Maps not loaded'));
      return;
    }

    const geocoder = new google.maps.Geocoder();

    geocoder.geocode({ address }, (results, status) => {
      if (status === 'OK' && results && results[0]) {
        resolve(results[0]);
      } else {
        resolve(null);
      }
    });
  });
};

export const reverseGeocode = async (
  location: google.maps.LatLngLiteral
): Promise<google.maps.GeocoderResult | null> => {
  // Check rate limit
  if (!geocodeLimiter()) {
    return null;
  }
  
  return new Promise((resolve, reject) => {
    if (!window.google || !window.google.maps) {
      reject(new Error('Google Maps not loaded'));
      return;
    }

    const geocoder = new google.maps.Geocoder();

    geocoder.geocode({ location }, (results, status) => {
      if (status === 'OK' && results && results[0]) {
        resolve(results[0]);
      } else {
        resolve(null);
      }
    });
  });
};

// Modern AutocompleteSuggestion API
export const fetchAutocompleteSuggestions = async (
  input: string,
  sessionToken: google.maps.places.AutocompleteSessionToken,
  _options?: {
    locationBias?: google.maps.places.LocationBias;
    componentRestrictions?: google.maps.places.ComponentRestrictions;
  }
): Promise<google.maps.places.AutocompleteSuggestion[]> => {
  // Check rate limit
  if (!autocompleteLimiter()) {
    // Silently handle rate limiting
    return [];
  }
  
  try {
    const { AutocompleteSuggestion } = await loadPlacesLibrary();
    
    // Build request with proper structure for new API
    const request = {
      input,
      sessionToken,
      includedRegionCodes: ['CA'], // Canada
      // Remove includedPrimaryTypes as it may be too restrictive
    };

    const { suggestions } = await AutocompleteSuggestion.fetchAutocompleteSuggestions(request);
    return suggestions || [];
  } catch (error) {
    // Silently handle API errors
    return [];
  }
};

// Modern Place API for getting details
export const fetchPlaceDetails = async (
  placeId: string,
  _sessionToken?: google.maps.places.AutocompleteSessionToken
): Promise<google.maps.places.Place | null> => {
  try {
    const { Place } = await loadPlacesLibrary();
    
    const place = new Place({
      id: placeId,
      requestedLanguage: 'en',
    });

    await place.fetchFields({
      fields: [
        'id',
        'displayName',
        'formattedAddress', 
        'location',
        'viewport',
        'addressComponents',
        'types'
      ]
    });

    return place;
  } catch (error) {
    return null;
  }
};

export const getUserLocation = (): Promise<GeolocationPosition> => {
  return new Promise((resolve, reject) => {
    if (!navigator.geolocation) {
      reject(new Error('Geolocation is not supported'));
      return;
    }

    navigator.geolocation.getCurrentPosition(
      (position) => resolve(position),
      (error) => reject(error),
      {
        enableHighAccuracy: true,
        timeout: 10000,
        maximumAge: 300000, // 5 minutes
      }
    );
  });
};
