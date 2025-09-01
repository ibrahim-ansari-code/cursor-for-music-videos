import React, { useMemo, useEffect } from 'react';
import { useFormContext } from 'react-hook-form';
import { PropertyFormData, PropertyStatus } from '@/types/property';
import { 
  MapPin, Home, Image as ImageIcon, AlertCircle,
  Bed, Bath, Square, Car, Key,
  TrendingUp, Layers, Trees
} from 'lucide-react';
import { motion } from 'framer-motion';

const ResidentialReview: React.FC = () => {
  const { watch, getValues } = useFormContext<PropertyFormData>();

  const formData = getValues();
  const images = watch('images_to_upload') || [];
  const generatedUnits = watch('generated_units') || [];
  const typeSpecificDetails = formData.type_specific_details || {};

  // Create object URLs with proper cleanup
  const imageUrls = useMemo(() => {
    return images.map((img: File) => URL.createObjectURL(img));
  }, [images]);

  // Cleanup object URLs when component unmounts or images change
  useEffect(() => {
    return () => {
      imageUrls.forEach(url => URL.revokeObjectURL(url));
    };
  }, [imageUrls]);
  
  // Status info for consistent badge display
  const statusInfo = {
    [PropertyStatus.ACTIVE]: { label: 'Active' },
    [PropertyStatus.INACTIVE]: { label: 'Inactive' },
    [PropertyStatus.MAINTENANCE]: { label: 'Maintenance' },
    [PropertyStatus.VACANT]: { label: 'Vacant' },
    [PropertyStatus.DRAFT]: { label: 'Draft' },
    [PropertyStatus.ARCHIVED]: { label: 'Archived' }
  }[formData.status || PropertyStatus.ACTIVE];
  
  // Calculate totals from units
  const totalMonthlyRent = generatedUnits.reduce((sum, unit) => sum + (unit.monthly_rent || 0), 0);
  const totalUnits = generatedUnits.length;
  const hasADU = generatedUnits.some(unit => unit.unit_type === 'adu');
  
  // Residential-specific data
  const bedrooms = typeSpecificDetails.bedrooms;
  const bathrooms = typeSpecificDetails.bathrooms;
  const squareFeet = typeSpecificDetails.square_feet;
  const garageSpaces = typeSpecificDetails.garage_spaces;
  const propertySubtype = typeSpecificDetails.property_subtype;
  const stories = typeSpecificDetails.stories;
  const lotSize = typeSpecificDetails.lot_size;
  
  // Check for warnings - residential-specific
  const warnings = [];
  if (!formData.year_built) {
    warnings.push('Year built not specified');
  }
  if (!formData.description) {
    warnings.push('No description provided');
  }
  if (images.length === 0) {
    warnings.push('No images uploaded');
  }
  if (!bedrooms || !bathrooms) {
    warnings.push('Bedrooms or bathrooms not specified');
  }

  // Property subtype emoji mapping
  const subtypeConfig = {
    single_family: { emoji: '🏡', label: 'Single Family Home' },
    townhouse: { emoji: '🏘️', label: 'Townhouse' },
    condo: { emoji: '🏢', label: 'Condominium' },
    duplex: { emoji: '👥', label: 'Duplex' },
    manufactured: { emoji: '🏗️', label: 'Manufactured Home' },
    mobile_home: { emoji: '🚐', label: 'Mobile Home' }
  };
  
  const currentSubtype = subtypeConfig[propertySubtype as keyof typeof subtypeConfig] || subtypeConfig.single_family;

  return (
    <div className="h-full overflow-y-auto">
      <div className="space-y-2 pb-4">
        {/* Compact Header */}
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="bg-gradient-to-r from-blue-50 to-indigo-50 rounded-xl p-3 border border-blue-200"
        >
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-white rounded-lg shadow-sm">
                <Home className="h-6 w-6 text-blue-600" />
              </div>
              <div>
                <h3 className="text-lg font-bold text-gray-900">{formData.name}</h3>
                <div className="flex items-center gap-2 text-sm text-gray-600">
                  <span>{currentSubtype.emoji} {currentSubtype.label}</span>
                  <span>•</span>
                  <span>{formData.city}, {formData.province}</span>
                  {formData.year_built && (
                    <>
                      <span>•</span>
                      <span>{formData.year_built}</span>
                    </>
                  )}
                </div>
              </div>
            </div>
            <span className={`inline-flex items-center px-3 py-1 rounded-full text-xs font-semibold
              ${formData.status === PropertyStatus.ACTIVE 
                ? 'bg-gradient-to-r from-green-50 to-emerald-50 text-green-700 border border-green-200' 
                : formData.status === PropertyStatus.MAINTENANCE 
                ? 'bg-gradient-to-r from-orange-50 to-amber-50 text-orange-700 border border-orange-200' 
                : formData.status === PropertyStatus.VACANT
                ? 'bg-gradient-to-r from-yellow-50 to-amber-50 text-yellow-700 border border-yellow-200'
                : 'bg-gradient-to-r from-gray-50 to-slate-50 text-gray-700 border border-gray-200'
              }`}>
              <span className={`w-1.5 h-1.5 rounded-full mr-2 ${
                formData.status === PropertyStatus.ACTIVE ? 'bg-green-500' :
                formData.status === PropertyStatus.MAINTENANCE ? 'bg-orange-500' : 
                formData.status === PropertyStatus.VACANT ? 'bg-yellow-500' : 'bg-gray-500'
              }`} />
                             {statusInfo.label}
            </span>
          </div>
        </motion.div>

        {/* Main Content - Balanced 2-Column Layout for Residential */}
        <div className="flex flex-col lg:flex-row gap-3 lg:items-stretch">
          {/* Left Column */}
          <div className="flex-1 flex flex-col space-y-2">
            {/* Location & Basic Info Combined */}
            <motion.div
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: 0.1 }}
              className="bg-white rounded-xl border border-gray-200 p-3"
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <MapPin className="h-4 w-4 text-gray-500" />
                  <h4 className="font-semibold text-gray-900">Location</h4>
                </div>
                <div className="text-right text-sm">
                  <p className="font-medium text-gray-900">{formData.address}</p>
                  <p className="text-gray-600">
                    {formData.city}, {formData.province} {formData.postal_code?.replace(/^(.{3})(.{3})$/, '$1 $2')}
                    {formData.year_built && (
                      <span className="ml-2">• Built {formData.year_built}</span>
                    )}
                  </p>
                </div>
              </div>
            </motion.div>

            {/* Property Specifications */}
            <motion.div
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: 0.2 }}
              className="bg-white rounded-xl border border-gray-200 p-3"
            >
              <div className="flex items-center gap-2 mb-3">
                <Home className="h-4 w-4 text-gray-500" />
                <h4 className="font-semibold text-gray-900">Property Specifications</h4>
              </div>
              
              <div className="grid grid-cols-3 gap-2">
                {bedrooms && (
                  <div className="bg-blue-50 rounded-lg p-2 flex items-center gap-2 min-h-[60px]">
                    <Bed className="h-5 w-5 text-blue-600 flex-shrink-0 ml-1.5 mr-1.5" />
                    <div className="flex-1">
                      <div className="text-base font-bold text-gray-900 text-center">{bedrooms}</div>
                      <div className="text-xs text-gray-600 text-center">Bedroom{bedrooms !== 1 ? 's' : ''}</div>
                    </div>
                  </div>
                )}
                {bathrooms && (
                  <div className="bg-blue-50 rounded-lg p-2 flex items-center gap-2 min-h-[60px]">
                    <Bath className="h-5 w-5 text-blue-600 flex-shrink-0 ml-1.5 mr-1.5" />
                    <div className="flex-1">
                      <div className="text-base font-bold text-gray-900 text-center">{bathrooms}</div>
                      <div className="text-xs text-gray-600 text-center">Bathroom{bathrooms !== 1 ? 's' : ''}</div>
                    </div>
                  </div>
                )}
                {squareFeet && (
                  <div className="bg-indigo-50 rounded-lg p-2 flex items-center gap-2 min-h-[60px]">
                    <Square className="h-5 w-5 text-indigo-600 flex-shrink-0 ml-1.5 mr-1.5" />
                    <div className="flex-1">
                      <div className="text-base font-bold text-gray-900 text-center">{squareFeet.toLocaleString()}</div>
                      <div className="text-xs text-gray-600 text-center">Sq Ft</div>
                    </div>
                  </div>
                )}
                {garageSpaces > 0 && (
                  <div className="bg-amber-50 rounded-lg p-2 flex items-center gap-2 min-h-[60px]">
                    <Car className="h-5 w-5 text-amber-600 flex-shrink-0 ml-1.5 mr-1.5" />
                    <div className="flex-1">
                      <div className="text-base font-bold text-gray-900 text-center">{garageSpaces}</div>
                      <div className="text-xs text-gray-600 text-center">Garage</div>
                    </div>
                  </div>
                )}
                {stories && (
                  <div className="bg-purple-50 rounded-lg p-2 flex items-center gap-2 min-h-[60px]">
                    <Layers className="h-5 w-5 text-purple-600 flex-shrink-0 ml-1.5 mr-1.5" />
                    <div className="flex-1">
                      <div className="text-base font-bold text-gray-900 text-center">{stories}</div>
                      <div className="text-xs text-gray-600 text-center">Stories</div>
                    </div>
                  </div>
                )}
                {lotSize && (
                  <div className="bg-green-50 rounded-lg p-2 flex items-center gap-2 min-h-[60px]">
                    <Trees className="h-5 w-5 text-green-600 flex-shrink-0 ml-1.5 mr-1.5" />
                    <div className="flex-1">
                      <div className="text-base font-bold text-gray-900 text-center">
                        {lotSize >= 1000 ? `${(lotSize/1000).toFixed(1)}K` : lotSize.toLocaleString()}
                      </div>
                      <div className="text-xs text-gray-600 text-center">Lot SF</div>
                    </div>
                  </div>
                )}
              </div>
              
              {formData.description && (
                <div className="mt-2 text-xs text-gray-600 leading-tight">
                  <span className="font-medium text-gray-700">Note:</span> {formData.description}
                </div>
              )}
            </motion.div>

            {/* Units & Revenue - Only show if configured */}
            {totalUnits > 0 && (
              <motion.div
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.3 }}
                className="bg-white rounded-xl border border-gray-200 p-3"
              >
                <div className="flex items-center gap-2 mb-3">
                  <Key className="h-4 w-4 text-gray-500" />
                  <h4 className="font-semibold text-gray-900">
                    {hasADU ? 'Units Configuration' : 'Rental Configuration'}
                  </h4>
                </div>
                
                <div className="space-y-2">
                  {generatedUnits.map((unit, idx) => (
                    <div key={idx} className="bg-gray-50 rounded-lg p-3">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <div className={`w-2 h-2 rounded-full ${
                            unit.unit_type === 'adu' ? 'bg-blue-500' : 'bg-green-500'
                          }`} />
                          <span className="text-sm font-medium text-gray-900">{unit.name}</span>
                          {unit.unit_type === 'adu' && (
                            <span className="px-2 py-0.5 text-xs font-medium text-blue-700 bg-blue-100 rounded-full">
                              ADU
                            </span>
                          )}
                        </div>
                        <div className="flex items-center gap-3 text-sm">
                          {unit.bedrooms !== undefined && (
                            <span className="text-gray-600">{unit.bedrooms}BR</span>
                          )}
                          {unit.bathrooms !== undefined && (
                            <span className="text-gray-600">{unit.bathrooms}BA</span>
                          )}
                          {unit.size && (
                            <span className="text-gray-600">{unit.size.toLocaleString()}SF</span>
                          )}
                          {unit.monthly_rent && (
                            <span className="font-semibold text-green-600">${unit.monthly_rent.toLocaleString()}</span>
                          )}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
                
                {/* Revenue Summary */}
                {totalMonthlyRent > 0 && (
                  <div className="mt-3 bg-gradient-to-r from-green-50 to-emerald-50 rounded-lg p-3 border border-green-200">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <TrendingUp className="h-4 w-4 text-green-600" />
                        <span className="text-sm font-medium text-green-900">Potential Income</span>
                      </div>
                      <div className="text-right">
                        <div className="text-lg font-bold text-green-700">${totalMonthlyRent.toLocaleString()}/mo</div>
                        <div className="text-xs text-green-600">${(totalMonthlyRent * 12).toLocaleString()}/year</div>
                      </div>
                    </div>
                  </div>
                )}
              </motion.div>
            )}
          </div>

          {/* Right Column */}
          <div className="flex-1 flex flex-col space-y-2">

            {/* Media Preview */}
            <motion.div
              initial={{ opacity: 0, x: 10 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: 0.2 }}
              className="bg-white rounded-xl border border-gray-200 p-3"
            >
              <div className="flex items-center gap-2 mb-3">
                <ImageIcon className="h-4 w-4 text-gray-500" />
                <h4 className="font-semibold text-gray-900">Photos</h4>
                <span className="text-sm text-gray-500">({images.length})</span>
              </div>
              
              {images.length > 0 ? (
                <div className="space-y-2">
                  <div className="grid grid-cols-2 gap-2">
                    {imageUrls.slice(0, 4).map((url, idx) => (
                      <div
                        key={idx}
                        className="aspect-[4/3] rounded-lg overflow-hidden border border-gray-200"
                      >
                        <img
                          src={url}
                          alt={`Preview ${idx + 1}`}
                          className="w-full h-full object-cover"
                        />
                      </div>
                    ))}
                  </div>
                  {images.length > 4 && (
                    <div className="text-center py-2 bg-gray-50 rounded-lg">
                      <span className="text-xs text-gray-600">+{images.length - 4} more photos</span>
                    </div>
                  )}
                </div>
              ) : (
                <div className="text-center py-6">
                  <ImageIcon className="h-8 w-8 text-gray-300 mx-auto mb-2" />
                  <p className="text-xs text-gray-500">No photos added</p>
                  <p className="text-xs text-gray-400 mt-1">Consider adding photos to showcase your property</p>
                </div>
              )}
            </motion.div>

            {/* Flexible spacer to push bottom content down */}
            <div className="flex-grow"></div>

            {/* Features & Systems */}
            {(typeSpecificDetails.heating_type || typeSpecificDetails.cooling_type || typeSpecificDetails.has_driveway) && (
              <motion.div
                initial={{ opacity: 0, x: 10 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.3 }}
                className="bg-white rounded-xl border border-gray-200 p-3"
              >
                <h4 className="font-semibold text-gray-900 mb-2">Features & Systems</h4>
                <div className="space-y-2 text-sm">
                  {typeSpecificDetails.heating_type && (
                    <div className="flex justify-between">
                      <span className="text-gray-600">Heating:</span>
                      <span className="font-medium text-gray-900 capitalize">{typeSpecificDetails.heating_type.replace(/_/g, ' ')}</span>
                    </div>
                  )}
                  {typeSpecificDetails.cooling_type && (
                    <div className="flex justify-between">
                      <span className="text-gray-600">Cooling:</span>
                      <span className="font-medium text-gray-900 capitalize">{typeSpecificDetails.cooling_type.replace(/_/g, ' ')}</span>
                    </div>
                  )}
                  {typeSpecificDetails.has_driveway && (
                    <div className="flex justify-between">
                      <span className="text-gray-600">Driveway:</span>
                      <span className="font-medium text-green-600">Yes</span>
                    </div>
                  )}
                  {typeSpecificDetails.street_parking && (
                    <div className="flex justify-between">
                      <span className="text-gray-600">Street Parking:</span>
                      <span className="font-medium text-green-600">Available</span>
                    </div>
                  )}
                </div>
              </motion.div>
            )}

            {/* Compact Warnings */}
            {warnings.length > 0 && (
              <motion.div
                initial={{ opacity: 0, x: 10 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.4 }}
                className="bg-yellow-50 border border-yellow-200 rounded-xl p-3"
              >
                <div className="flex items-start gap-2">
                  <AlertCircle className="h-4 w-4 text-yellow-600 mt-0.5 flex-shrink-0" />
                  <div>
                    <p className="text-xs font-medium text-yellow-900 mb-1">Optional items missing</p>
                    <ul className="text-xs text-yellow-700 space-y-0.5">
                      {warnings.map((warning, idx) => (
                        <li key={idx}>• {warning}</li>
                      ))}
                    </ul>
                  </div>
                </div>
              </motion.div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default ResidentialReview;
