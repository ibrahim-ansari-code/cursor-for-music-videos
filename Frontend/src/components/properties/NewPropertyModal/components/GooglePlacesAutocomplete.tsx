import React, { useState, useCallback, useRef, useEffect } from 'react';
import { useFormContext } from 'react-hook-form';
import { Search, X } from 'lucide-react';
import { debounce } from 'lodash';
import { PropertyFormData } from '../../../../types/property';
import { fetchAutocompleteSuggestions, fetchPlaceDetails } from '../hooks/useGoogleMaps';

// Google logo SVG component
const GoogleIcon = ({ className }: { className?: string }) => (
  <svg className={className} viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
    <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
    <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
    <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
    <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
  </svg>
);

interface GooglePlacesAutocompleteProps {
  onPlaceSelect?: (place: google.maps.places.PlaceResult) => void;
  className?: string;
}

interface Suggestion {
  placeId: string;
  mainText: string;
  secondaryText: string;
  fullText: string;
  suggestion?: google.maps.places.AutocompleteSuggestion;
}

const GooglePlacesAutocomplete: React.FC<GooglePlacesAutocompleteProps> = React.memo(({
  onPlaceSelect,
  className = '',
}) => {
  const [inputValue, setInputValue] = useState('');
  const [suggestions, setSuggestions] = useState<Suggestion[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [selectedIndex, setSelectedIndex] = useState(-1);
  
  const sessionToken = useRef<google.maps.places.AutocompleteSessionToken | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const suggestionsRef = useRef<HTMLDivElement>(null);
  const listboxId = useRef<string>('gpa-listbox-' + Math.random().toString(36).slice(2));
  const lastExternalAddress = useRef<string>('');
  const isMountedRef = useRef(true);
  
  const { setValue, watch } = useFormContext<PropertyFormData>();
  const currentAddress = watch('address');

  // Initialize session token
  useEffect(() => {
    if (window.google && window.google.maps && window.google.maps.places) {
      sessionToken.current = new google.maps.places.AutocompleteSessionToken();
    }
    
    // Set mounted state
    isMountedRef.current = true;
    
    return () => {
      isMountedRef.current = false;
    };
  }, []);

  // Sync with external address changes (e.g., from map dragging)
  useEffect(() => {
    // Only update if address changed externally (not from this component)
    if (currentAddress && currentAddress !== lastExternalAddress.current && currentAddress !== inputValue) {
      lastExternalAddress.current = currentAddress;
      setInputValue(currentAddress);
    }
  }, [currentAddress]);

  // Fetch autocomplete suggestions using new API
  const fetchSuggestions = useCallback(
    debounce(async (input: string) => {
      if (!window.google || !window.google.maps) {
        return;
      }

      if (!sessionToken.current) {
        sessionToken.current = new google.maps.places.AutocompleteSessionToken();
      }

      if (input.length < 3) {
        setSuggestions([]);
        return;
      }

      setIsLoading(true);

      try {
        const suggestions = await fetchAutocompleteSuggestions(
          input,
          sessionToken.current
        );

        const formattedSuggestions = suggestions.slice(0, 5).map((suggestion) => ({
          placeId: suggestion.placePrediction?.placeId || '',
          mainText: suggestion.placePrediction?.mainText?.text || suggestion.placePrediction?.text?.text?.split(',')[0] || '',
          secondaryText: suggestion.placePrediction?.secondaryText?.text || suggestion.placePrediction?.text?.text?.split(',').slice(1).join(',').trim() || '',
          fullText: suggestion.placePrediction?.text?.text || '',
          suggestion
        }));

        setSuggestions(formattedSuggestions);
        setShowSuggestions(true);
        setIsLoading(false);
      } catch (error) {
        setIsLoading(false);
        setSuggestions([]);
      }
    }, 300),
    []
  );

  // Get place details when a suggestion is selected using new API
  const selectPlace = useCallback(
    async (suggestion: Suggestion) => {
      if (!sessionToken.current) {
        return;
      }

      setInputValue(suggestion.mainText);
      setShowSuggestions(false);
      setSuggestions([]);

      try {
        const place = await fetchPlaceDetails(suggestion.placeId, sessionToken.current);
        
        if (place) {
          // Parse address components using new API structure
          const addressComponents = place.addressComponents || [];
          let streetNumber = '';
          let streetName = '';
          let city = '';
          let province = '';
          let postalCode = '';

          addressComponents.forEach((component) => {
            const types = component.types;
            
            if (types.includes('street_number')) {
              streetNumber = component.longText || '';
            }
            if (types.includes('route')) {
              streetName = component.longText || '';
            }
            if (types.includes('locality')) {
              city = component.longText || '';
            }
            if (types.includes('administrative_area_level_1')) {
              province = component.shortText || '';
            }
            if (types.includes('postal_code')) {
              postalCode = (component.longText || '').replace(/\s/g, '');
            }
          });

          // Construct street address
          const streetAddress = streetNumber && streetName 
            ? `${streetNumber} ${streetName}` 
            : streetName || suggestion.mainText;

          // Update display value and track it as external change
          setInputValue(streetAddress);
          lastExternalAddress.current = streetAddress;

          // Update form values using new API structure
          setValue('address', streetAddress);
          setValue('city', city);
          setValue('province', province);
          setValue('postal_code', postalCode);
          setValue('formatted_address', place.formattedAddress || '');
          setValue('place_id', place.id || '');
          
          if (place.location) {
            const lat = place.location.lat();
            const lng = place.location.lng();
            setValue('latitude', lat);
            setValue('longitude', lng);
          }

          // Store viewport data using new API structure
          if (place.viewport) {
            setValue('google_maps_data', {
              viewport: {
                northeast: {
                  lat: place.viewport.getNorthEast().lat(),
                  lng: place.viewport.getNorthEast().lng()
                },
                southwest: {
                  lat: place.viewport.getSouthWest().lat(),
                  lng: place.viewport.getSouthWest().lng()
                }
              }
            });
          }

          // Call parent callback
          if (onPlaceSelect && place) {
            // Convert to Google Maps PlaceResult format for compatibility
            const placeResult: google.maps.places.PlaceResult = {
              place_id: place.id,
              name: place.displayName || '',
              formatted_address: place.formattedAddress || '',
              geometry: place.location ? {
                location: new google.maps.LatLng(
                  place.location.lat() || 0, 
                  place.location.lng() || 0
                )
              } : undefined,
              address_components: place.addressComponents?.map(component => ({
                long_name: component.longText || '',
                short_name: component.shortText || '',
                types: component.types
              })) || []
            };
            onPlaceSelect(placeResult);
          }

          // Reset session token
          sessionToken.current = new google.maps.places.AutocompleteSessionToken();
        }
      } catch (error) {
        // Silently handle errors
      }
    },
    [setValue, onPlaceSelect]
  );

  // Handle input change
  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value;
    setInputValue(value);
    lastExternalAddress.current = value; // Track user input as the latest value
    
    if (value.trim()) {
      // Update address in form as user types
      setValue('address', value);
      fetchSuggestions(value);
    } else {
      setSuggestions([]);
      setShowSuggestions(false);
      // Clear form values when input is cleared manually by user
      setValue('address', '');
      setValue('city', '');
      setValue('province', '');
      setValue('postal_code', '');
      setValue('latitude', null);
      setValue('longitude', null);
    }
  };

  // Handle keyboard navigation
  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (!showSuggestions || suggestions.length === 0) return;

    switch (e.key) {
      case 'ArrowDown':
        e.preventDefault();
        setSelectedIndex((prev) => 
          prev < suggestions.length - 1 ? prev + 1 : prev
        );
        break;
      case 'ArrowUp':
        e.preventDefault();
        setSelectedIndex((prev) => (prev > 0 ? prev - 1 : -1));
        break;
      case 'Enter':
        e.preventDefault();
        if (selectedIndex >= 0 && selectedIndex < suggestions.length) {
          selectPlace(suggestions[selectedIndex]);
        }
        break;
      case 'Escape':
        setShowSuggestions(false);
        setSelectedIndex(-1);
        break;
    }
  };

  // Clear input
  const clearInput = () => {
    setInputValue('');
    lastExternalAddress.current = ''; // Reset tracked value
    setSuggestions([]);
    setShowSuggestions(false);
    setValue('address', '');
    setValue('city', '');
    setValue('province', '');
    setValue('postal_code', '');
    setValue('formatted_address', null);
    setValue('place_id', null);
    setValue('latitude', null);
    setValue('longitude', null);
    setValue('google_maps_data', null);
    inputRef.current?.focus();
  };

  // Handle click outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (
        suggestionsRef.current &&
        !suggestionsRef.current.contains(event.target as Node) &&
        !inputRef.current?.contains(event.target as Node)
      ) {
        setShowSuggestions(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Ensure focused option is visible
  useEffect(() => {
    if (!suggestionsRef.current) return;
    const item = suggestionsRef.current.querySelector(
      `[data-index="${selectedIndex}"]`
    ) as HTMLElement | null;
    if (item) {
      item.scrollIntoView({ block: 'nearest' });
    }
  }, [selectedIndex]);

  return (
    <div className={`relative ${className}`}>
      <span id="address-search-instructions" className="sr-only">
        Start typing an address to see suggestions. Use arrow keys to navigate and Enter to select.
      </span>
      <div className="relative">
        <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
          <Search className="h-4 w-4 text-gray-400 dark:text-gray-500 transition-colors duration-300" />
        </div>
        <input
          ref={inputRef}
          type="text"
          value={inputValue}
          onChange={handleInputChange}
          onKeyDown={handleKeyDown}
          onFocus={() => suggestions.length > 0 && setShowSuggestions(true)}
          placeholder="123 Main Street, Toronto"
          className="block w-full pl-10 pr-16 py-3 text-sm border border-gray-300 dark:border-gray-600 rounded-md 
                     focus:ring-1 focus:ring-blue-500 focus:border-blue-500 transition-colors bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
          autoComplete="off"
          role="combobox"
          aria-expanded={showSuggestions}
          aria-controls={listboxId.current}
          aria-autocomplete="list"
          aria-activedescendant={
            selectedIndex >= 0 ? `${listboxId.current}-option-${selectedIndex}` : undefined
          }
          aria-label="Property address search"
          aria-describedby="address-search-instructions"
        />
        <div className="absolute inset-y-0 right-0 flex items-center pr-3 gap-2">
          {/* Google Icon */}
          <div className="flex items-center border-l border-gray-200 dark:border-gray-600 pl-2 transition-colors duration-300">
            <GoogleIcon className="h-4 w-4" />
          </div>
          {/* Clear/Loading button */}
          {(inputValue || isLoading) && (
            <button
              type="button"
              onClick={clearInput}
              className="ml-1 hover:bg-gray-50 dark:hover:bg-gray-600 rounded p-1 transition-colors"
              aria-label={isLoading ? "Loading suggestions" : "Clear address"}
            >
              {isLoading ? (
                <span className="h-3.5 w-3.5 inline-block animate-spin border-2 border-gray-300 border-t-transparent rounded-full" />
              ) : (
                <X className="h-3.5 w-3.5 text-gray-400 dark:text-gray-500 hover:text-gray-600 dark:hover:text-gray-300 transition-colors duration-300" />
              )}
            </button>
          )}
        </div>
      </div>

      {/* Suggestions dropdown */}
      {showSuggestions && (
        <div
          ref={suggestionsRef}
          className="absolute z-50 w-full mt-1 bg-white dark:bg-gray-800 rounded-md shadow-lg border border-gray-200 dark:border-gray-600 
                     max-h-60 overflow-auto transition-colors duration-300"
          id={listboxId.current}
          role="listbox"
        >
          {suggestions.length > 0 ? (
            suggestions.map((suggestion, index) => (
              <button
                key={suggestion.placeId}
                type="button"
                onClick={() => selectPlace(suggestion)}
                onMouseEnter={() => setSelectedIndex(index)}
                className={`w-full px-3 py-2 text-left text-sm hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors duration-300
                           ${index === selectedIndex ? 'bg-gray-50 dark:bg-gray-700' : ''}
                           ${index > 0 ? 'border-t border-gray-100 dark:border-gray-600' : ''}`}
                id={`${listboxId.current}-option-${index}`}
                role="option"
                aria-selected={index === selectedIndex}
                data-index={index}
              >
                <div className="font-medium text-gray-900 dark:text-gray-100 truncate transition-colors duration-300">
                  {suggestion.mainText}
                </div>
                <div className="text-xs text-gray-500 dark:text-gray-400 truncate transition-colors duration-300">
                  {suggestion.secondaryText}
                </div>
              </button>
            ))
          ) : (
            inputValue.trim().length >= 3 && (
              <div className="px-3 py-2 text-sm text-gray-500 dark:text-gray-400 transition-colors duration-300">No results</div>
            )
          )}
        </div>
      )}
    </div>
  );
});

GooglePlacesAutocomplete.displayName = 'GooglePlacesAutocomplete';

export default GooglePlacesAutocomplete;