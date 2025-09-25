import React, { useEffect } from 'react';
import { useFormContext } from 'react-hook-form';
import { Check, Info } from 'lucide-react';
import { PropertyFormData } from '@/types/property';
import GooglePlacesAutocomplete from '../components/GooglePlacesAutocomplete';
import PropertyMap from '../components/PropertyMap';
import { useGoogleMaps } from '../hooks/useGoogleMaps';
import { validateGoogleMapsEnvironment } from '@/utils/googleMapsLoader';

interface LocationStepProps {
  onNext: () => void;
}

const LocationStep: React.FC<LocationStepProps> = ({ onNext: _onNext }) => {
  const { watch, formState: { errors } } = useFormContext<PropertyFormData>();
  
  // Single Google Maps hook call for the entire LocationStep
  const { isLoaded: isGoogleMapsLoaded, isMapConstructorReady, userLocation, loadError } = useGoogleMaps();
  
  const latitude = watch('latitude');
  const longitude = watch('longitude');
  const address = watch('address');
  const city = watch('city');
  const province = watch('province');
  const postalCode = watch('postal_code');

  // Check if location is complete
  const isLocationComplete = !!(
    address && 
    city && 
    province && 
    postalCode && 
    latitude && 
    longitude
  );

  // Debug Google Maps environment on component mount
  useEffect(() => {
    const diagnostics = validateGoogleMapsEnvironment();
    if (!diagnostics.isValid) {
      console.error('LocationStep - Google Maps configuration issues:', diagnostics);
    }
  }, []);



  // Error state for Google Maps
  if (loadError) {
    return (
      <div className="flex flex-col h-full min-h-0">
        <div className="flex items-center justify-center h-64 bg-red-50 dark:bg-red-900/20 rounded-lg border border-red-200 dark:border-red-800">
          <div className="text-center px-4">
            <svg className="h-12 w-12 mx-auto text-red-400 dark:text-red-500 mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} 
                    d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
            <p className="text-sm font-medium text-red-800 dark:text-red-300 mb-1">Failed to load Google Maps</p>
            <p className="text-xs text-red-600 dark:text-red-400">Please check your internet connection and refresh the page.</p>
            <button 
              onClick={() => window.location.reload()} 
              className="mt-4 px-4 py-2 bg-red-600 dark:bg-red-700 text-white text-xs font-medium rounded hover:bg-red-700 dark:hover:bg-red-600 transition-colors"
            >
              Refresh Page
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full min-h-0">
      {/* Main content - responsive grid */}
      <div className="grid grid-cols-1 lg:grid-cols-[380px,1fr] gap-4">
        {/* Left side - responsive */}
        <div className="flex flex-col lg:min-w-[380px]">
          {/* Search input */}
          <div className="mb-4">
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Property Address
            </label>
            <GooglePlacesAutocomplete 
              className="w-full"
            />
            {errors.address && (
              <p className="mt-1 text-xs text-red-600 dark:text-red-400">{errors.address.message}</p>
            )}
          </div>

          {/* Content based on state */}
          {isLocationComplete ? (
            <div className="space-y-2">
              {/* Address confirmation */}
              <div className="bg-gradient-to-r from-green-50 to-emerald-50 dark:from-green-900/30 dark:to-emerald-900/20 border border-green-200 dark:border-green-700 rounded-lg p-3">
                <div className="flex items-center gap-4">
                  <div className="flex-shrink-0 w-5 h-5 bg-green-600 dark:bg-green-500 rounded-full flex items-center justify-center">
                    <Check className="w-3 h-3 text-white" />
                  </div>
                  <div className="flex-1">
                    <p className="text-sm font-semibold text-gray-900 dark:text-gray-100 mb-0.5">
                      Location Confirmed
                    </p>
                    <p className="text-sm font-medium text-gray-800 dark:text-gray-200">
                      {address}
                    </p>
                    <p className="text-xs text-gray-600 dark:text-gray-400 mt-0.5">
                      {city}, {province} {postalCode?.replace(/^(.{3})(.{3})$/, '$1 $2')}
                    </p>
                  </div>
                </div>
              </div>

              {/* Location details - enhanced */}
              <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-600 rounded-lg p-3.5">
                <div className="flex items-center gap-2 mb-2">
                  <div className="w-4 h-4 bg-gray-100 dark:bg-gray-700 rounded-full flex items-center justify-center">
                    <div className="w-2 h-2 bg-gray-500 dark:bg-gray-400 rounded-full"></div>
                  </div>
                  <h4 className="text-xs font-semibold text-gray-700 dark:text-gray-300 uppercase tracking-wide">
                    Details
                  </h4>
                </div>
                <dl className="space-y-1.5">
                  <div className="flex justify-between items-center py-0.5">
                    <dt className="text-xs text-gray-500 dark:text-gray-400">City</dt>
                    <dd className="text-xs font-medium text-gray-900 dark:text-gray-100">{city}</dd>
                  </div>
                  <div className="flex justify-between items-center py-0.5">
                    <dt className="text-xs text-gray-500 dark:text-gray-400">Province</dt>
                    <dd className="text-xs font-medium text-gray-900 dark:text-gray-100">{province}</dd>
                  </div>
                  <div className="flex justify-between items-center py-0.5">
                    <dt className="text-xs text-gray-500 dark:text-gray-400">Postal</dt>
                    <dd className="text-xs font-medium text-gray-900 dark:text-gray-100">{postalCode?.replace(/^(.{3})(.{3})$/, '$1 $2')}</dd>
                  </div>
                </dl>
              </div>

              {/* Interactive tip */}
              <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-700 rounded-lg p-3.5">
                <div className="flex items-center gap-2.5">
                  <Info className="w-4 h-4 text-blue-600 dark:text-blue-400 flex-shrink-0" />
                  <div>
                    <p className="text-xs font-medium text-blue-900 dark:text-blue-100 mb-0.5">
                      Fine-tune location
                    </p>
                    <p className="text-xs text-blue-700 dark:text-blue-300">
                      Drag the map pin to adjust the exact position if needed
                    </p>
                  </div>
                </div>
              </div>
            </div>
          ) : (
            <div className="space-y-4 h-full flex flex-col">
              {/* Enhanced step-by-step guide */}
              <div className="bg-gradient-to-br from-green-50 via-green-50/70 to-emerald-50/50 dark:from-green-900/30 dark:via-green-900/20 dark:to-emerald-900/10 border border-green-200 dark:border-green-700 rounded-lg p-4">
                <div className="space-y-3.5">
                  <div className="grid grid-cols-[32px,1fr] gap-3 items-center">
                    <div className="w-8 h-8 bg-gradient-to-br from-white to-green-50 dark:from-gray-700 dark:to-green-900/50 border-2 border-green-500 dark:border-green-600 rounded-full flex items-center justify-center text-sm font-bold text-green-700 dark:text-green-300 shadow-sm">
                      1
                    </div>
                    <div className="min-w-0">
                      <p className="text-sm font-semibold text-gray-900 dark:text-gray-100 mb-0.5">
                        Enter your address
                      </p>
                      <p className="text-xs text-gray-600 dark:text-gray-400 leading-relaxed">
                        Start typing the street address in the search box
                      </p>
                    </div>
                  </div>
                  <div className="grid grid-cols-[32px,1fr] gap-3 items-center">
                    <div className="w-8 h-8 bg-gradient-to-br from-white to-green-50 dark:from-gray-700 dark:to-green-900/50 border-2 border-green-500 dark:border-green-600 rounded-full flex items-center justify-center text-sm font-bold text-green-700 dark:text-green-300 shadow-sm">
                      2
                    </div>
                    <div className="min-w-0">
                      <p className="text-sm font-semibold text-gray-900 dark:text-gray-100 mb-0.5">
                        Choose from suggestions
                      </p>
                      <p className="text-xs text-gray-600 dark:text-gray-400 leading-relaxed">
                        Select the correct address from the dropdown list
                      </p>
                    </div>
                  </div>
                  <div className="grid grid-cols-[32px,1fr] gap-3 items-center">
                    <div className="w-8 h-8 bg-gradient-to-br from-white to-green-50 dark:from-gray-700 dark:to-green-900/50 border-2 border-green-500 dark:border-green-600 rounded-full flex items-center justify-center text-sm font-bold text-green-700 dark:text-green-300 shadow-sm">
                      3
                    </div>
                    <div className="min-w-0">
                      <p className="text-sm font-semibold text-gray-900 dark:text-gray-100 mb-0.5">
                        Confirm location
                      </p>
                      <p className="text-xs text-gray-600 dark:text-gray-400 leading-relaxed">
                        Verify the pin placement on the map
                      </p>
                    </div>
                  </div>
                </div>
              </div>

              {/* Coverage info */}
              <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-600 rounded-lg p-3.5">
                <div className="flex items-center gap-2 mb-2">
                  <div className="w-4 h-4 bg-green-100 dark:bg-green-900/50 rounded-full flex items-center justify-center">
                    <div className="w-2 h-2 bg-green-500 dark:bg-green-400 rounded-full animate-pulse"></div>
                  </div>
                  <span className="text-xs font-semibold text-gray-700 dark:text-gray-300 uppercase tracking-wide">
                    Coverage
                  </span>
                </div>
                <p className="text-xs text-gray-600 dark:text-gray-400 leading-relaxed">
                  All addresses across Canada are supported with automatic location detection.
                </p>
              </div>
            </div>
          )}
        </div>

        {/* Right side - Map */}
        <div className="relative rounded-lg overflow-hidden border border-gray-200 dark:border-gray-600 h-[384px]">
          <PropertyMap 
            height="384px" 
            showEmptyState={!isLocationComplete}
            isGoogleMapsLoaded={isGoogleMapsLoaded}
            isMapConstructorReady={isMapConstructorReady}
            userLocation={userLocation}
          />
        </div>
      </div>
    </div>
  );
};

export default LocationStep;