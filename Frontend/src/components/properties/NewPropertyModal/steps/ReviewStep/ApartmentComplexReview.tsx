import React, { useMemo, useEffect } from 'react';
import { useFormContext } from 'react-hook-form';
import { PropertyFormData, PropertyStatus } from '@/types/property';
import { 
  MapPin, Building2, Image as ImageIcon, AlertCircle,
  Users, Car, Layers, DollarSign, Key, TrendingUp
} from 'lucide-react';
import { motion } from 'framer-motion';

const ApartmentComplexReview: React.FC = () => {
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
    [PropertyStatus.RENTED]: { label: 'Rented' },
    [PropertyStatus.VACANT]: { label: 'Vacant' },
    [PropertyStatus.DRAFT]: { label: 'Draft' },
    [PropertyStatus.ARCHIVED]: { label: 'Archived' },
    [PropertyStatus.PARTIALLY_RENTED]: { label: 'Partially Rented' }
  }[formData.status || PropertyStatus.ACTIVE];
  
  // Calculate totals from units
  const totalMonthlyRent = generatedUnits.reduce((sum, unit) => sum + (unit.monthly_rent || 0), 0);
  const totalUnits = generatedUnits.length;
  
  // Apartment complex specific data
  const numberOfBuildings = typeSpecificDetails.number_of_buildings;
  const totalAptUnits = typeSpecificDetails.total_units;
  const complexStyle = typeSpecificDetails.complex_style;
  const parkingTotal = typeSpecificDetails.parking_spaces_total;
  const elevatorCount = typeSpecificDetails.elevator_count;
  const unitMix = typeSpecificDetails.unit_mix || {};
  
  // Get top unit types for display
  const topUnitTypes = Object.entries(unitMix)
    .filter(([_, count]) => Number(count) > 0)
    .sort((a, b) => Number(b[1]) - Number(a[1]))
    .slice(0, 3);
  
  // Check for warnings
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

  return (
    <div className="h-full overflow-y-auto">
      <div className="space-y-4">
        {/* Compact Header */}
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="bg-gradient-to-r from-blue-50 to-indigo-50 rounded-xl p-4 border border-blue-200"
        >
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-white rounded-lg shadow-sm">
                <Building2 className="h-6 w-6 text-blue-600" />
              </div>
              <div>
                <h3 className="text-lg font-bold text-gray-900">{formData.name}</h3>
                <div className="flex items-center gap-2 text-sm text-gray-600">
                  <span>{complexStyle && `${complexStyle.charAt(0).toUpperCase() + complexStyle.slice(1)} `}Apartment Complex</span>
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
                : formData.status === PropertyStatus.RENTED 
                ? 'bg-gradient-to-r from-emerald-50 to-green-50 text-emerald-700 border border-emerald-200' 
                : formData.status === PropertyStatus.VACANT
                ? 'bg-gradient-to-r from-yellow-50 to-amber-50 text-yellow-700 border border-yellow-200'
                : 'bg-gradient-to-r from-gray-50 to-slate-50 text-gray-700 border border-gray-200'
              }`}>
              <span className={`w-1.5 h-1.5 rounded-full mr-2 ${
                formData.status === PropertyStatus.ACTIVE ? 'bg-green-500' :
                formData.status === PropertyStatus.RENTED ? 'bg-emerald-500' : 
                formData.status === PropertyStatus.VACANT ? 'bg-yellow-500' : 'bg-gray-500'
              }`} />
              {statusInfo.label}
            </span>
          </div>
        </motion.div>

        {/* Main Content Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          {/* Left Column - Location & Complex Details */}
          <div className="lg:col-span-2 space-y-4">
            {/* Location */}
            <motion.div
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: 0.1 }}
              className="bg-white rounded-xl border border-gray-200 p-4"
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <MapPin className="h-4 w-4 text-gray-500" />
                  <h4 className="font-semibold text-gray-900">Location</h4>
                </div>
                <div className="text-right text-sm">
                  <p className="font-medium text-gray-900">{formData.address}</p>
                  <p className="text-gray-600">{formData.city}, {formData.province} {formData.postal_code?.replace(/^(.{3})(.{3})$/, '$1 $2')}</p>
                </div>
              </div>
            </motion.div>

            {/* Complex Details */}
            <motion.div
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: 0.2 }}
              className="bg-white rounded-xl border border-gray-200 p-4"
            >
              <div className="flex items-center gap-2 mb-3">
                <Building2 className="h-4 w-4 text-gray-500" />
                <h4 className="font-semibold text-gray-900">Complex Details</h4>
              </div>
              
              <div className="grid grid-cols-4 gap-2 mb-3">
                {numberOfBuildings && (
                  <div className="text-center p-2 bg-blue-50 rounded-lg">
                    <Building2 className="h-4 w-4 mx-auto text-blue-600 mb-1" />
                    <div className="text-sm font-semibold text-gray-900">{numberOfBuildings}</div>
                    <div className="text-xs text-gray-600">Building{numberOfBuildings !== 1 ? 's' : ''}</div>
                  </div>
                )}
                {totalAptUnits && (
                  <div className="text-center p-2 bg-purple-50 rounded-lg">
                    <Users className="h-4 w-4 mx-auto text-purple-600 mb-1" />
                    <div className="text-sm font-semibold text-gray-900">{totalAptUnits}</div>
                    <div className="text-xs text-gray-600">Total Units</div>
                  </div>
                )}
                {parkingTotal > 0 && (
                  <div className="text-center p-2 bg-amber-50 rounded-lg">
                    <Car className="h-4 w-4 mx-auto text-amber-600 mb-1" />
                    <div className="text-sm font-semibold text-gray-900">{parkingTotal}</div>
                    <div className="text-xs text-gray-600">Parking</div>
                  </div>
                )}
                {elevatorCount > 0 && (
                  <div className="text-center p-2 bg-indigo-50 rounded-lg">
                    <Layers className="h-4 w-4 mx-auto text-indigo-600 mb-1" />
                    <div className="text-sm font-semibold text-gray-900">{elevatorCount}</div>
                    <div className="text-xs text-gray-600">Elevator{elevatorCount !== 1 ? 's' : ''}</div>
                  </div>
                )}
              </div>
              
              {topUnitTypes.length > 0 && (
                <div className="bg-gray-50 rounded-lg p-3">
                  <div className="text-xs font-medium text-gray-700 mb-2">Unit Mix:</div>
                  <div className="flex flex-wrap gap-2">
                    {topUnitTypes.map(([type, count]) => (
                      <span key={type} className="px-2 py-1 text-xs bg-white rounded border text-gray-700 font-medium">
                        {type.toUpperCase()}: {Number(count)}
                      </span>
                    ))}
                  </div>
                </div>
              )}
              
              {formData.description && (
                <div className="mt-3 pt-3 border-t border-gray-100">
                  <p className="text-xs text-gray-600 leading-relaxed">{formData.description}</p>
                </div>
              )}
            </motion.div>

            {/* Units & Revenue */}
            {totalUnits > 0 && (
              <motion.div
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.3 }}
                className="bg-white rounded-xl border border-gray-200 p-4"
              >
                <div className="flex items-center gap-2 mb-3">
                  <Key className="h-4 w-4 text-gray-500" />
                  <h4 className="font-semibold text-gray-900">Units & Revenue</h4>
                </div>
                
                <div className="grid grid-cols-3 gap-3 mb-3">
                  <div className="text-center p-2 bg-blue-50 rounded-lg">
                    <Key className="h-4 w-4 mx-auto text-blue-600 mb-1" />
                    <div className="text-sm font-semibold text-gray-900">{totalUnits}</div>
                    <div className="text-xs text-gray-600">Configured</div>
                  </div>
                  {totalMonthlyRent > 0 && (
                    <>
                      <div className="text-center p-2 bg-green-50 rounded-lg">
                        <DollarSign className="h-4 w-4 mx-auto text-green-600 mb-1" />
                        <div className="text-sm font-semibold text-gray-900">${totalMonthlyRent.toLocaleString()}</div>
                        <div className="text-xs text-gray-600">Monthly</div>
                      </div>
                      <div className="text-center p-2 bg-emerald-50 rounded-lg">
                        <TrendingUp className="h-4 w-4 mx-auto text-emerald-600 mb-1" />
                        <div className="text-sm font-semibold text-gray-900">${(totalMonthlyRent * 12).toLocaleString()}</div>
                        <div className="text-xs text-gray-600">Annual</div>
                      </div>
                    </>
                  )}
                </div>

                {/* Sample Units Preview */}
                {generatedUnits.length > 0 && (
                  <div className="bg-gray-50 rounded-lg p-3">
                    <div className="text-xs font-medium text-gray-700 mb-2">Sample Units:</div>
                    <div className="space-y-1">
                      {generatedUnits.slice(0, 3).map((unit, idx) => (
                        <div key={idx} className="flex justify-between items-center text-xs">
                          <span className="text-gray-600">{unit.name}</span>
                          <div className="flex gap-2 text-gray-500">
                            {unit.bedrooms !== undefined && (
                              <span>{unit.bedrooms}BR</span>
                            )}
                            {unit.size && (
                              <span>{unit.size.toLocaleString()}SF</span>
                            )}
                            {unit.monthly_rent && (
                              <span className="text-green-600 font-medium">${unit.monthly_rent}</span>
                            )}
                          </div>
                        </div>
                      ))}
                      {generatedUnits.length > 3 && (
                        <div className="text-xs text-gray-500 text-center pt-1">
                          +{generatedUnits.length - 3} more units
                        </div>
                      )}
                    </div>
                  </div>
                )}
              </motion.div>
            )}
          </div>

          {/* Right Column - Media & Summary */}
          <div className="space-y-4">
            {/* Media Preview */}
            <motion.div
              initial={{ opacity: 0, x: 10 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: 0.1 }}
              className="bg-white rounded-xl border border-gray-200 p-4"
            >
              <div className="flex items-center gap-2 mb-3">
                <ImageIcon className="h-4 w-4 text-gray-500" />
                <h4 className="font-semibold text-gray-900">Media</h4>
                <span className="text-sm text-gray-500">({images.length})</span>
              </div>
              
              {images.length > 0 ? (
                <div className="space-y-2">
                  <div className="grid grid-cols-3 gap-1">
                    {imageUrls.slice(0, 6).map((url, idx) => (
                      <div
                        key={idx}
                        className="aspect-square rounded-lg overflow-hidden border border-gray-200"
                      >
                        <img
                          src={url}
                          alt={`Preview ${idx + 1}`}
                          className="w-full h-full object-cover"
                        />
                      </div>
                    ))}
                  </div>
                  {images.length > 6 && (
                    <div className="text-center">
                      <span className="text-xs text-gray-500">+{images.length - 6} more images</span>
                    </div>
                  )}
                </div>
              ) : (
                <div className="text-center py-4">
                  <ImageIcon className="h-8 w-8 text-gray-300 mx-auto mb-2" />
                  <p className="text-xs text-gray-500">No images added</p>
                </div>
              )}
            </motion.div>

            {/* Compact Warnings */}
            {warnings.length > 0 && (
              <motion.div
                initial={{ opacity: 0, x: 10 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.3 }}
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

export default ApartmentComplexReview;
