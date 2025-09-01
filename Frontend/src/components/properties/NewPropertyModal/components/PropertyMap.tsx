import React, { useCallback, useRef, useEffect, useState, useMemo } from 'react';
import { GoogleMap } from '@react-google-maps/api';
import { useFormContext } from 'react-hook-form';
import { PropertyFormData } from '@/types/property';
import { reverseGeocode } from '../hooks/useGoogleMaps';
import MapSkeleton from './MapSkeleton';

// Global cache for marker library to avoid repeated imports
let markerLibraryCache: {
  AdvancedMarkerElement: typeof google.maps.marker.AdvancedMarkerElement;
  PinElement: typeof google.maps.marker.PinElement;
} | null = null;

// Utility function to load or retrieve marker library components
const getMarkerLibrary = async (
  markerLibraryRef: React.RefObject<typeof markerLibraryCache | null>
): Promise<{
  AdvancedMarkerElement: typeof google.maps.marker.AdvancedMarkerElement;
  PinElement: typeof google.maps.marker.PinElement;
}> => {
  if (markerLibraryRef.current) {
    return markerLibraryRef.current;
  }
  
  if (markerLibraryCache) {
    markerLibraryRef.current = markerLibraryCache;
    return markerLibraryCache;
  }
  
  const markerLib = await google.maps.importLibrary('marker') as google.maps.MarkerLibrary;
  const library = {
    AdvancedMarkerElement: markerLib.AdvancedMarkerElement,
    PinElement: markerLib.PinElement
  };
  
  markerLibraryCache = library;
  markerLibraryRef.current = library;
  
  return library;
};

interface PropertyMapProps {
  className?: string;
  height?: string;
  showEmptyState?: boolean;
  isGoogleMapsLoaded: boolean;
  userLocation: { lat: number; lng: number } | null;
}

const PropertyMap: React.FC<PropertyMapProps> = React.memo(({ 
  className = '', 
  height = '400px',
  showEmptyState = false,
  isGoogleMapsLoaded,
  userLocation
}) => {
  const { watch, setValue } = useFormContext<PropertyFormData>();
  const mapRef = useRef<google.maps.Map | null>(null);
  const markerRef = useRef<google.maps.marker.AdvancedMarkerElement | null>(null);
  const handleLocationUpdateRef = useRef<((lat: number, lng: number) => void) | null>(null);
  const markerLibraryRef = useRef<typeof markerLibraryCache>(null);
  const [mapCenter, setMapCenter] = useState({ lat: 43.6532, lng: -79.3832 }); // Toronto default
  const [isReverseGeocoding, setIsReverseGeocoding] = useState(false);
  const appliedBoundsRef = useRef<string | null>(null);
  
  const latitudeRaw = watch('latitude');
  const longitudeRaw = watch('longitude');
  
  // Ensure coordinates are numbers
  const latitude = typeof latitudeRaw === 'number' ? latitudeRaw : null;
  const longitude = typeof longitudeRaw === 'number' ? longitudeRaw : null;
  const mapsData = watch('google_maps_data');

  // Set initial map center to user's location when available
  useEffect(() => {
    if (userLocation && !latitude && !longitude) {
      setMapCenter(userLocation);
    }
  }, [userLocation, latitude, longitude]);

  // Update map center when coordinates change
  useEffect(() => {
    if (latitude && longitude && mapRef.current) {
      const newCenter = { lat: latitude, lng: longitude };
      setMapCenter(newCenter);
      mapRef.current.panTo(newCenter);
      mapRef.current.setZoom(17);
      
      // Clear any applied bounds since we're now using specific coordinates
      appliedBoundsRef.current = null;
    }
  }, [latitude, longitude]);

  // Map ID must be constant - define outside of useMemo to ensure consistency
  const MAP_ID = import.meta.env.VITE_GOOGLE_MAP_ID || '235a15a8eb6db4dcd6108694';
  
  const mapOptions: google.maps.MapOptions = useMemo(() => ({
    mapId: MAP_ID, // Required for AdvancedMarkerElement
    disableDefaultUI: false,
    zoomControl: true,
    streetViewControl: false,
    mapTypeControl: false,
    fullscreenControl: false,
    clickableIcons: false,
    gestureHandling: 'cooperative',
  }), []); // Empty deps array is safe since MAP_ID is constant

  const onMapLoad = useCallback(async (map: google.maps.Map) => {
    mapRef.current = map;
    
    // Preload marker library immediately when map loads
    if (!markerLibraryCache && window.google) {
      try {
        const markerLib = await google.maps.importLibrary('marker') as google.maps.MarkerLibrary;
        markerLibraryCache = {
          AdvancedMarkerElement: markerLib.AdvancedMarkerElement,
          PinElement: markerLib.PinElement
        };
        markerLibraryRef.current = markerLibraryCache;
      } catch (error) {
        // Silently handle error - marker creation will retry later
      }
    } else if (markerLibraryCache) {
      markerLibraryRef.current = markerLibraryCache;
    }
    
    // Priority 1: Use coordinates if present (most precise)
    if (latitude !== null && longitude !== null) {
      const center = { lat: latitude, lng: longitude };
      map.panTo(center);
      map.setZoom(17);
      
      // Always create/recreate marker when map loads with coordinates
      // This ensures marker persists when returning to LocationStep
      if (markerLibraryRef.current) {
        // Clean up existing marker if any
        if (markerRef.current) {
          markerRef.current.map = null;
          markerRef.current = null;
        }
        
        const { AdvancedMarkerElement, PinElement } = markerLibraryRef.current;
        
        const pinElement = new PinElement({
          background: '#3B82F6',
          borderColor: '#1E40AF',
          glyphColor: '#FFFFFF',
          scale: 1.2
        });
        
        const marker = new AdvancedMarkerElement({
          map: map,
          position: new google.maps.LatLng(latitude, longitude),
          gmpDraggable: true,
          title: 'Property Location',
          content: pinElement.element,
          collisionBehavior: google.maps.CollisionBehavior.REQUIRED
        });
        
        marker.addListener('dragend', () => {
          const position = marker.position;
          if (position && handleLocationUpdateRef.current) {
            if (position instanceof google.maps.LatLng) {
              handleLocationUpdateRef.current(position.lat(), position.lng());
            } else {
              const positionLiteral = position as google.maps.LatLngLiteral;
              handleLocationUpdateRef.current(positionLiteral.lat, positionLiteral.lng);
            }
          }
        });
        
        markerRef.current = marker;
      }
      
      return;
    }
    
    // Priority 2: Use viewport bounds from Places API
    if (mapsData?.viewport) {
      const ne = new google.maps.LatLng(
        mapsData.viewport.northeast.lat,
        mapsData.viewport.northeast.lng
      );
      const sw = new google.maps.LatLng(
        mapsData.viewport.southwest.lat,
        mapsData.viewport.southwest.lng
      );
      const bounds = new google.maps.LatLngBounds(sw, ne);
      const key = `${sw.lat()},${sw.lng()}-${ne.lat()},${ne.lng()}`;
      if (appliedBoundsRef.current !== key) {
        map.fitBounds(bounds);
        appliedBoundsRef.current = key;
      }
      return;
    }
    
    // Priority 3: Use user location if available
    if (userLocation) {
      map.panTo(userLocation);
      map.setZoom(12);
    }
  }, [latitude, longitude, mapsData, userLocation]);

  // Helper function to parse geocoding results
  const parseGeocodingResult = useCallback((result: google.maps.GeocoderResult) => {
    const addressComponents = result.address_components || [];
    const parsed = {
      streetNumber: '',
      streetName: '',
      city: '',
      province: '',
      postalCode: ''
    };

    addressComponents.forEach((component) => {
      const types = component.types;
      
      if (types.includes('street_number')) {
        parsed.streetNumber = component.long_name;
      }
      if (types.includes('route')) {
        parsed.streetName = component.long_name;
      }
      if (types.includes('locality')) {
        parsed.city = component.long_name;
      }
      if (types.includes('administrative_area_level_1')) {
        parsed.province = component.short_name;
      }
      if (types.includes('postal_code')) {
        parsed.postalCode = component.long_name.replace(/\s/g, '');
      }
    });

    const streetAddress = parsed.streetNumber && parsed.streetName 
      ? `${parsed.streetNumber} ${parsed.streetName}` 
      : parsed.streetName || result.formatted_address?.split(',')[0] || '';

    return {
      address: streetAddress,
      city: parsed.city,
      province: parsed.province,
      postal_code: parsed.postalCode,
      formatted_address: result.formatted_address || ''
    };
  }, []);

  const handleLocationUpdate = useCallback(async (lat: number, lng: number) => {
    if (isReverseGeocoding) return;
    
    setValue('latitude', lat);
    setValue('longitude', lng);
    
    setIsReverseGeocoding(true);
    try {
      const result = await reverseGeocode({ lat, lng });
      if (result) {
        const parsed = parseGeocodingResult(result);
        setValue('address', parsed.address);
        setValue('city', parsed.city);
        setValue('province', parsed.province);
        setValue('postal_code', parsed.postal_code);
        setValue('formatted_address', parsed.formatted_address);
      }
    } catch (error) {
      // Silently handle reverse geocoding errors
    } finally {
      setIsReverseGeocoding(false);
    }
  }, [setValue, isReverseGeocoding, parseGeocodingResult]);

  // Keep ref updated with latest function
  useEffect(() => {
    handleLocationUpdateRef.current = handleLocationUpdate;
  }, [handleLocationUpdate]);

  // Create and manage AdvancedMarkerElement - optimized for immediate display
  useEffect(() => {
    let isMounted = true;
    
    const createAdvancedMarker = async () => {
      // Wait for map to be loaded and coordinates to be available
      if (!mapRef.current || !window.google || latitude === null || longitude === null) {
        // Remove marker if coordinates are cleared
        if (markerRef.current && (latitude === null || longitude === null)) {
          markerRef.current.map = null;
          markerRef.current = null;
        }
        return;
      }
      
      // Always ensure we have the marker library loaded
      if (!markerLibraryRef.current && !markerLibraryCache) {
        try {
          const markerLib = await google.maps.importLibrary('marker') as google.maps.MarkerLibrary;
          markerLibraryCache = {
            AdvancedMarkerElement: markerLib.AdvancedMarkerElement,
            PinElement: markerLib.PinElement
          };
          markerLibraryRef.current = markerLibraryCache;
        } catch {
          return; // Silently fail if library can't be loaded
        }
      }

      try {
        // Load marker library using utility function
        const { AdvancedMarkerElement, PinElement } = await getMarkerLibrary(markerLibraryRef);
        
        if (!isMounted) return; // Check if component is still mounted
        
        // Update existing marker position if it exists
        if (markerRef.current) {
          const newPosition = new google.maps.LatLng(latitude, longitude);
          markerRef.current.position = newPosition;
          
          // Also pan the map to the new position
          if (mapRef.current) {
            mapRef.current.panTo(newPosition);
          }
          return;
        }
        
        // Create custom pin for better visibility
        const pinElement = new PinElement({
          background: '#3B82F6',
          borderColor: '#1E40AF',
          glyphColor: '#FFFFFF',
          scale: 1.2
        });
        
        // Create new AdvancedMarkerElement with custom pin
        const marker = new AdvancedMarkerElement({
          map: mapRef.current,
          position: new google.maps.LatLng(latitude, longitude),
          gmpDraggable: true,
          title: 'Property Location',
          content: pinElement.element,
          collisionBehavior: google.maps.CollisionBehavior.REQUIRED
        });

        // Add drag end listener with proper position handling
        marker.addListener('dragend', () => {
          const position = marker.position;
          if (position && handleLocationUpdateRef.current) {
            if (position instanceof google.maps.LatLng) {
              handleLocationUpdateRef.current(position.lat(), position.lng());
            } else {
              // Fallback for LatLngLiteral object
              const positionLiteral = position as google.maps.LatLngLiteral;
              handleLocationUpdateRef.current(positionLiteral.lat, positionLiteral.lng);
            }
          }
        });

        markerRef.current = marker;
      } catch (error) {
        // Silently handle marker creation errors
      }
    };

    // Execute immediately without delay
    createAdvancedMarker();

    // Cleanup function
    return () => {
      isMounted = false;
      if (markerRef.current) {
        // AdvancedMarkerElement cleanup
        markerRef.current.map = null;
        markerRef.current = null;
      }
    };
  }, [latitude, longitude]); // Dependencies optimized using ref for handleLocationUpdate

  const handleMapClick = useCallback((e: google.maps.MapMouseEvent) => {
    if (e.latLng) {
      handleLocationUpdate(e.latLng.lat(), e.latLng.lng());
    }
  }, [handleLocationUpdate]);

  if (!isGoogleMapsLoaded) {
    return <MapSkeleton className={className} style={{ height }} />;
  }

  return (
    <div className="relative h-full" role="application" aria-label="Property location map">
      <GoogleMap
        mapContainerStyle={{ width: '100%', height }}
        center={mapCenter}
        zoom={showEmptyState ? (userLocation ? 12 : 10) : 17}
        options={mapOptions}
        onLoad={onMapLoad}
        onClick={handleMapClick}
      >
        {/* AdvancedMarkerElement is managed programmatically via useEffect above */}
      </GoogleMap>
      {showEmptyState && !(latitude && longitude) && (
        <div className="pointer-events-none absolute inset-0 flex items-center justify-center">
          <div className="bg-white/80 backdrop-blur rounded-md px-3 py-1.5 text-xs text-gray-700 border border-gray-200">
            Search an address to drop a pin
          </div>
        </div>
      )}
    </div>
  );
});

PropertyMap.displayName = 'PropertyMap';

export default PropertyMap;