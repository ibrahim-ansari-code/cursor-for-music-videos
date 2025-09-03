import React, { useMemo, useEffect } from 'react';
import { useFormContext } from 'react-hook-form';
import { PropertyFormData, PropertyStatus } from '@/types/property';
import { 
  MapPin, Building, Image as ImageIcon,
  Home, Store, Users
} from 'lucide-react';
import { motion } from 'framer-motion';

const MixedUseReview: React.FC = () => {
  const { watch, getValues } = useFormContext<PropertyFormData>();

  const formData = getValues();
  const images = watch('images_to_upload') || [];
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
  
  // Mixed use specific data
  const mixedUseType = typeSpecificDetails.mixed_use_type;
  const residentialSquareFeet = typeSpecificDetails.residential_square_feet;
  const commercialSquareFeet = typeSpecificDetails.commercial_square_feet;
  const resUnitsCount = typeSpecificDetails.residential_units_count;
  const comUnitsCount = typeSpecificDetails.commercial_units_count;
  
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
                <Building className="h-6 w-6 text-blue-600" />
              </div>
              <div>
                <h3 className="text-lg font-bold text-gray-900">{formData.name}</h3>
                <div className="flex items-center gap-2 text-sm text-gray-600">
                  <span>{mixedUseType && `${mixedUseType.replace(/_/g, ' ')} `}Mixed Use</span>
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
          <div className="lg:col-span-2 space-y-4">
            <motion.div className="bg-white rounded-xl border border-gray-200 p-4">
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
            
            <motion.div className="bg-white rounded-xl border border-gray-200 p-4">
              <h4 className="font-semibold text-gray-900 mb-3">Mixed Use Details</h4>
              <div className="grid grid-cols-4 gap-2">
                {residentialSquareFeet && (
                  <div className="text-center p-2 bg-green-50 rounded-lg">
                    <Home className="h-4 w-4 mx-auto text-green-600 mb-1" />
                    <div className="text-sm font-semibold text-gray-900">{Number(residentialSquareFeet).toLocaleString()}</div>
                    <div className="text-xs text-gray-600">Res SF</div>
                  </div>
                )}
                {commercialSquareFeet && (
                  <div className="text-center p-2 bg-purple-50 rounded-lg">
                    <Store className="h-4 w-4 mx-auto text-purple-600 mb-1" />
                    <div className="text-sm font-semibold text-gray-900">{Number(commercialSquareFeet).toLocaleString()}</div>
                    <div className="text-xs text-gray-600">Com SF</div>
                  </div>
                )}
                {(resUnitsCount || 0) > 0 && (
                  <div className="text-center p-2 bg-blue-50 rounded-lg">
                    <Users className="h-4 w-4 mx-auto text-blue-600 mb-1" />
                    <div className="text-sm font-semibold text-gray-900">{resUnitsCount}</div>
                    <div className="text-xs text-gray-600">Res Units</div>
                  </div>
                )}
                {(comUnitsCount || 0) > 0 && (
                  <div className="text-center p-2 bg-indigo-50 rounded-lg">
                    <Building className="h-4 w-4 mx-auto text-indigo-600 mb-1" />
                    <div className="text-sm font-semibold text-gray-900">{comUnitsCount}</div>
                    <div className="text-xs text-gray-600">Com Spaces</div>
                  </div>
                )}
              </div>
            </motion.div>
          </div>
          
          <div className="space-y-4">
            <motion.div className="bg-white rounded-xl border border-gray-200 p-4">
              <div className="flex items-center gap-2 mb-3">
                <ImageIcon className="h-4 w-4 text-gray-500" />
                <h4 className="font-semibold text-gray-900">Media</h4>
                <span className="text-sm text-gray-500">({images.length})</span>
              </div>
              
              {images.length > 0 ? (
                <div className="grid grid-cols-3 gap-1">
                  {imageUrls.slice(0, 6).map((url, idx) => (
                    <div key={idx} className="aspect-square rounded-lg overflow-hidden border border-gray-200">
                      <img src={url} alt={`Preview ${idx + 1}`} className="w-full h-full object-cover" />
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-center py-4">
                  <ImageIcon className="h-8 w-8 text-gray-300 mx-auto mb-2" />
                  <p className="text-xs text-gray-500">No images added</p>
                </div>
              )}
            </motion.div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default MixedUseReview;
