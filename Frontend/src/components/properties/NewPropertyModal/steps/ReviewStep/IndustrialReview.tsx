import React, { useMemo, useEffect } from 'react';
import { useFormContext } from 'react-hook-form';
import { PropertyFormData, PropertyStatus } from '@/types/property';
import { 
  MapPin, Factory, Image as ImageIcon,
  Square, Package, Gauge, Train
} from 'lucide-react';
import { motion } from 'framer-motion';

const IndustrialReview: React.FC = () => {
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
  
  // Industrial-specific data - using backend schema field names
  const industrialType = typeSpecificDetails.industrial_type;
  const totalSquareFeet = typeSpecificDetails.total_square_feet;
  const clearHeight = typeSpecificDetails.clear_height;
  const loadingDocks = typeSpecificDetails.loading_docks_count;
  const railAccess = typeSpecificDetails.rail_access;
  
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
          className="bg-gradient-to-r from-blue-50 to-indigo-50 dark:from-blue-900/30 dark:to-indigo-900/30 rounded-xl p-4 border border-blue-200 dark:border-blue-700 transition-colors duration-300"
        >
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-white dark:bg-gray-800 rounded-lg shadow-sm transition-colors duration-300">
                <Factory className="h-6 w-6 text-blue-600 dark:text-blue-400" />
              </div>
              <div>
                <h3 className="text-lg font-bold text-gray-900 dark:text-gray-100 transition-colors duration-300">{formData.name}</h3>
                <div className="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-400 transition-colors duration-300">
                  <span>{industrialType && `${industrialType.charAt(0).toUpperCase() + industrialType.slice(1).replace(/_/g, ' ')} `}Industrial</span>
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
                ? 'bg-gradient-to-r from-green-50 to-emerald-50 dark:from-green-900/30 dark:to-emerald-900/30 text-green-700 dark:text-green-300 border border-green-200 dark:border-green-700' 
                : formData.status === PropertyStatus.RENTED 
                ? 'bg-gradient-to-r from-emerald-50 to-green-50 dark:from-emerald-900/30 dark:to-green-900/30 text-emerald-700 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-700' 
                : formData.status === PropertyStatus.VACANT
                ? 'bg-gradient-to-r from-yellow-50 to-amber-50 dark:from-yellow-900/30 dark:to-amber-900/30 text-yellow-700 dark:text-yellow-300 border border-yellow-200 dark:border-yellow-700'
                : 'bg-gradient-to-r from-gray-50 to-slate-50 dark:from-gray-800/30 dark:to-slate-800/30 text-gray-700 dark:text-gray-300 border border-gray-200 dark:border-gray-700'
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

        {/* Rest of original layout - will be optimized later */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          <div className="lg:col-span-2 space-y-4">
            <motion.div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-4 transition-colors duration-300">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <MapPin className="h-4 w-4 text-gray-500 dark:text-gray-400" />
                  <h4 className="font-semibold text-gray-900 dark:text-gray-100 transition-colors duration-300">Location</h4>
                </div>
                <div className="text-right text-sm">
                  <p className="font-medium text-gray-900 dark:text-gray-100 transition-colors duration-300">{formData.address}</p>
                  <p className="text-gray-600 dark:text-gray-400 transition-colors duration-300">{formData.city}, {formData.province} {formData.postal_code?.replace(/^(.{3})(.{3})$/, '$1 $2')}</p>
                </div>
              </div>
            </motion.div>
            
            <motion.div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-4 transition-colors duration-300">
              <h4 className="font-semibold text-gray-900 dark:text-gray-100 mb-3 transition-colors duration-300">Industrial Details</h4>
              <div className="grid grid-cols-4 gap-2">
                {totalSquareFeet && (
                  <div className="text-center p-2 bg-orange-50 dark:bg-orange-900/20 rounded-lg transition-colors duration-300">
                    <Square className="h-4 w-4 mx-auto text-orange-600 dark:text-orange-400 mb-1" />
                    <div className="text-sm font-semibold text-gray-900 dark:text-gray-100 transition-colors duration-300">{Number(totalSquareFeet).toLocaleString()}</div>
                    <div className="text-xs text-gray-600 dark:text-gray-400 transition-colors duration-300">Total SF</div>
                  </div>
                )}
                {clearHeight && (
                  <div className="text-center p-2 bg-blue-50 dark:bg-blue-900/20 rounded-lg transition-colors duration-300">
                    <Gauge className="h-4 w-4 mx-auto text-blue-600 dark:text-blue-400 mb-1" />
                    <div className="text-sm font-semibold text-gray-900 dark:text-gray-100 transition-colors duration-300">{clearHeight}'</div>
                    <div className="text-xs text-gray-600 dark:text-gray-400 transition-colors duration-300">Clear Height</div>
                  </div>
                )}
                {loadingDocks != null && (
                  <div className="text-center p-2 bg-green-50 dark:bg-green-900/20 rounded-lg transition-colors duration-300">
                    <Package className="h-4 w-4 mx-auto text-green-600 dark:text-green-400 mb-1" />
                    <div className="text-sm font-semibold text-gray-900 dark:text-gray-100 transition-colors duration-300">{loadingDocks}</div>
                    <div className="text-xs text-gray-600 dark:text-gray-400 transition-colors duration-300">Loading Docks</div>
                  </div>
                )}
                {railAccess && (
                  <div className="text-center p-2 bg-purple-50 dark:bg-purple-900/20 rounded-lg transition-colors duration-300">
                    <Train className="h-4 w-4 mx-auto text-purple-600 dark:text-purple-400 mb-1" />
                    <div className="text-xs font-semibold text-gray-900 dark:text-gray-100 transition-colors duration-300">Yes</div>
                    <div className="text-xs text-gray-600 dark:text-gray-400 transition-colors duration-300">Rail Access</div>
                  </div>
                )}
              </div>
            </motion.div>
          </div>
          
          <div className="space-y-4">
            <motion.div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-4 transition-colors duration-300">
              <div className="flex items-center gap-2 mb-3">
                <ImageIcon className="h-4 w-4 text-gray-500 dark:text-gray-400" />
                <h4 className="font-semibold text-gray-900 dark:text-gray-100 transition-colors duration-300">Media</h4>
                <span className="text-sm text-gray-500 dark:text-gray-400 transition-colors duration-300">({images.length})</span>
              </div>
              
              {images.length > 0 ? (
                <div className="grid grid-cols-3 gap-1">
                  {imageUrls.slice(0, 6).map((url, idx) => (
                    <div key={idx} className="aspect-square rounded-lg overflow-hidden border border-gray-200 dark:border-gray-600 transition-colors duration-300">
                      <img src={url} alt={`Preview ${idx + 1}`} className="w-full h-full object-cover" />
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-center py-4">
                  <ImageIcon className="h-8 w-8 text-gray-300 dark:text-gray-600 mx-auto mb-2" />
                  <p className="text-xs text-gray-500 dark:text-gray-400 transition-colors duration-300">No images added</p>
                </div>
              )}
            </motion.div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default IndustrialReview;
