import React, { useMemo, useEffect } from 'react';
import { useFormContext } from 'react-hook-form';
import { PropertyFormData, PropertyStatus } from '@/types/property';
import { 
  MapPin, Trees, Image as ImageIcon, AlertCircle,
  Ruler, FileText, Shield, Mountain, Zap, Building
} from 'lucide-react';
import { motion } from 'framer-motion';

const LandReview: React.FC = () => {
  const { watch } = useFormContext<PropertyFormData>();

  // Watch all relevant fields for real-time updates
  const name = watch('name');
  const address = watch('address');
  const city = watch('city');
  const province = watch('province');
  const postal_code = watch('postal_code');
  const status = watch('status');
  const year_built = watch('year_built');
  const description = watch('description');
  const images = watch('images_to_upload') || [];
  const typeSpecificDetails = watch('type_specific_details') || {};

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
  }[status || PropertyStatus.ACTIVE];
  
  // Land-specific data - safe number parsing with fallbacks
  const totalAreaSqft = (() => {
    const val = Number(typeSpecificDetails.total_area_sqft);
    return !isNaN(val) && val > 0 ? val : 0;
  })();
  
  const totalAcres = (() => {
    if (totalAreaSqft <= 0) return null;
    const acres = totalAreaSqft / 43560;
    return !isNaN(acres) ? acres.toFixed(4) : null;
  })();
  
  const leasedPortionSqft = (() => {
    const val = Number(typeSpecificDetails.leased_portion_sqft);
    return !isNaN(val) && val > 0 ? val : 0;
  })();
  
  const frontageMeter = (() => {
    const val = Number(typeSpecificDetails.frontage_meters);
    return !isNaN(val) && val > 0 ? val : null;
  })();
  
  const depthMeters = (() => {
    const val = Number(typeSpecificDetails.depth_meters);
    return !isNaN(val) && val > 0 ? val : null;
  })();
  
  const leaseStructure = typeSpecificDetails.lease_structure || null;
  const municipality = typeSpecificDetails.municipality || null;
  const zoningCode = typeSpecificDetails.zoning_code || null;
  const permittedUses = Array.isArray(typeSpecificDetails.permitted_uses) ? typeSpecificDetails.permitted_uses : [];
  const allowsStructures = Boolean(typeSpecificDetails.allows_structures);
  const signageRights = Boolean(typeSpecificDetails.signage_rights);
  const utilitiesStatus = typeSpecificDetails.utilities_status && typeof typeSpecificDetails.utilities_status === 'object' 
    ? typeSpecificDetails.utilities_status 
    : {};
  
  // Check for warnings
  const warnings = [];
  if (!totalAreaSqft) {
    warnings.push('Land area not specified');
  }
  if (!leaseStructure) {
    warnings.push('Lease structure not specified');
  }
  if (!description) {
    warnings.push('No description provided');
  }
  if (images.length === 0) {
    warnings.push('No images uploaded');
  }

  return (
    <div className="max-w-5xl mx-auto p-6 space-y-6">
      {/* Header Card */}
      <motion.div
        initial={{ opacity: 0, y: -10 }}
        animate={{ opacity: 1, y: 0 }}
        className="bg-gradient-to-r from-green-500 to-emerald-600 dark:from-green-600 dark:to-emerald-700 rounded-xl p-6 text-white shadow-lg transition-colors duration-300"
      >
        <div className="flex items-start justify-between">
          <div className="flex-1">
            <div className="flex items-center gap-2 mb-2">
              <Trees className="h-6 w-6" />
              <h2 className="text-2xl font-bold">{name || 'Unnamed Land Property'}</h2>
            </div>
            <div className="flex items-center gap-2 text-sm opacity-90 mb-3">
              <MapPin className="h-4 w-4" />
              <span>{address}, {city}, {province} {postal_code}</span>
            </div>
            {totalAreaSqft > 0 && (
              <div className="flex items-center gap-4 text-sm opacity-95">
                <div className="flex items-center gap-1.5">
                  <Ruler className="h-4 w-4" />
                  <span className="font-semibold">{totalAreaSqft.toLocaleString()} sq ft</span>
                </div>
                {totalAcres && (
                  <div className="flex items-center gap-1.5">
                    <Trees className="h-4 w-4" />
                    <span className="font-semibold">{totalAcres} acres</span>
                  </div>
                )}
              </div>
            )}
          </div>
          <div>
            <span className="inline-flex items-center px-3 py-1.5 rounded-full text-xs font-semibold bg-white/20 backdrop-blur-sm">
              {statusInfo.label}
            </span>
          </div>
        </div>
      </motion.div>

      {/* Main Content Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column - Land Details */}
        <div className="lg:col-span-2 space-y-4">
          {/* Basic Information */}
          <motion.div
            initial={{ opacity: 0, x: -10 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.1 }}
            className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-4 transition-colors duration-300"
          >
            <h3 className="font-semibold text-gray-900 dark:text-gray-100 mb-3 flex items-center gap-2 transition-colors duration-300">
              <MapPin className="h-5 w-5 text-blue-600 dark:text-blue-400" />
              Basic Information
            </h3>
            <div className="space-y-2 text-sm">
              {year_built && (
                <div className="flex justify-between py-1.5 border-b border-gray-100 dark:border-gray-700">
                  <span className="text-gray-600 dark:text-gray-400 transition-colors duration-300">Year:</span>
                  <span className="font-medium text-gray-900 dark:text-gray-100 transition-colors duration-300">{year_built}</span>
                </div>
              )}
              {description && (
                <div className="py-1.5">
                  <span className="text-gray-600 dark:text-gray-400 block mb-1 transition-colors duration-300">Description:</span>
                  <p className="text-gray-900 dark:text-gray-100 text-xs leading-relaxed transition-colors duration-300">{description}</p>
                </div>
              )}
              {municipality && (
                <div className="flex justify-between py-1.5 border-b border-gray-100 dark:border-gray-700">
                  <span className="text-gray-600 dark:text-gray-400 transition-colors duration-300">Municipality:</span>
                  <span className="font-medium text-gray-900 dark:text-gray-100 transition-colors duration-300">{municipality}</span>
                </div>
              )}
              {typeSpecificDetails.lot_numbers && (
                <div className="flex justify-between py-1.5 border-b border-gray-100 dark:border-gray-700">
                  <span className="text-gray-600 dark:text-gray-400 transition-colors duration-300">Lot Numbers:</span>
                  <span className="font-medium text-gray-900 dark:text-gray-100 transition-colors duration-300">{typeSpecificDetails.lot_numbers}</span>
                </div>
              )}
            </div>
          </motion.div>

          {/* Land Measurements */}
          {totalAreaSqft > 0 && (
            <motion.div
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: 0.15 }}
              className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-4 transition-colors duration-300"
            >
              <h3 className="font-semibold text-gray-900 dark:text-gray-100 mb-3 flex items-center gap-2 transition-colors duration-300">
                <Ruler className="h-5 w-5 text-green-600 dark:text-green-400" />
                Land Measurements
              </h3>
              <div className="grid grid-cols-2 gap-3">
                <div className="bg-green-50 dark:bg-green-900/20 rounded-lg p-3">
                  <p className="text-xs text-gray-600 dark:text-gray-400 mb-1">Total Area</p>
                  <p className="text-lg font-bold text-green-700 dark:text-green-300">{totalAreaSqft.toLocaleString()} ft²</p>
                  {totalAcres && <p className="text-xs text-gray-600 dark:text-gray-400 mt-1">{totalAcres} acres</p>}
                </div>
                {leasedPortionSqft > 0 && totalAreaSqft > 0 && (
                  <div className="bg-blue-50 dark:bg-blue-900/20 rounded-lg p-3">
                    <p className="text-xs text-gray-600 dark:text-gray-400 mb-1">Leased Portion</p>
                    <p className="text-lg font-bold text-blue-700 dark:text-blue-300">{leasedPortionSqft.toLocaleString()} ft²</p>
                    <p className="text-xs text-gray-600 dark:text-gray-400 mt-1">
                      {((() => {
                        const percentage = (leasedPortionSqft / totalAreaSqft) * 100;
                        return !isNaN(percentage) ? percentage.toFixed(1) : '0.0';
                      })())}% of total
                    </p>
                  </div>
                )}
                {frontageMeter !== null && (
                  <div className="bg-gray-50 dark:bg-gray-700/30 rounded-lg p-3">
                    <p className="text-xs text-gray-600 dark:text-gray-400 mb-1">Frontage</p>
                    <p className="text-base font-semibold text-gray-900 dark:text-gray-100">{frontageMeter.toFixed(2)}m</p>
                  </div>
                )}
                {depthMeters !== null && (
                  <div className="bg-gray-50 dark:bg-gray-700/30 rounded-lg p-3">
                    <p className="text-xs text-gray-600 dark:text-gray-400 mb-1">Depth</p>
                    <p className="text-base font-semibold text-gray-900 dark:text-gray-100">{depthMeters.toFixed(2)}m</p>
                  </div>
                )}
              </div>
            </motion.div>
          )}

          {/* Zoning & Land Use */}
          {(zoningCode || typeSpecificDetails.official_plan_designation || permittedUses.length > 0) && (
            <motion.div
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: 0.2 }}
              className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-4 transition-colors duration-300"
            >
              <h3 className="font-semibold text-gray-900 dark:text-gray-100 mb-3 flex items-center gap-2 transition-colors duration-300">
                <MapPin className="h-5 w-5 text-blue-600 dark:text-blue-400" />
                Zoning & Land Use
              </h3>
              <div className="space-y-2 text-sm">
                {zoningCode && (
                  <div className="flex justify-between">
                    <span className="text-gray-600 dark:text-gray-400">Zoning Code:</span>
                    <span className="font-medium text-gray-900 dark:text-gray-100">{zoningCode}</span>
                  </div>
                )}
                {typeSpecificDetails.official_plan_designation && (
                  <div className="flex justify-between">
                    <span className="text-gray-600 dark:text-gray-400">Official Plan:</span>
                    <span className="font-medium text-gray-900 dark:text-gray-100 capitalize">
                      {typeSpecificDetails.official_plan_designation}
                    </span>
                  </div>
                )}
                {typeSpecificDetails.site_plan_status && (
                  <div className="flex justify-between">
                    <span className="text-gray-600 dark:text-gray-400">Site Plan:</span>
                    <span className={`font-medium capitalize ${
                      typeSpecificDetails.site_plan_status === 'approved' 
                        ? 'text-green-600 dark:text-green-400' 
                        : 'text-amber-600 dark:text-amber-400'
                    }`}>
                      {typeSpecificDetails.site_plan_status.replace(/_/g, ' ')}
                    </span>
                  </div>
                )}
                {permittedUses.length > 0 && (
                  <div>
                    <span className="text-gray-600 dark:text-gray-400 block mb-1.5">Permitted Uses:</span>
                    <div className="flex flex-wrap gap-1.5">
                      {permittedUses.map((use: string) => (
                        <span 
                          key={use} 
                          className="px-2 py-1 bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 rounded-md text-xs font-medium capitalize"
                        >
                          {use.replace(/_/g, ' ')}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </motion.div>
          )}

          {/* Lease Structure */}
          {leaseStructure && (
            <motion.div
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: 0.25 }}
              className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-4 transition-colors duration-300"
            >
              <h3 className="font-semibold text-gray-900 dark:text-gray-100 mb-3 flex items-center gap-2 transition-colors duration-300">
                <FileText className="h-5 w-5 text-purple-600 dark:text-purple-400" />
                Ground Lease Structure
              </h3>
              <div className="space-y-2 text-sm">
                <div className="flex justify-between py-1.5 border-b border-gray-100 dark:border-gray-700">
                  <span className="text-gray-600 dark:text-gray-400">Lease Type:</span>
                  <span className="font-medium text-gray-900 dark:text-gray-100 capitalize">{leaseStructure.replace(/_/g, ' ')}</span>
                </div>
                <div className="flex justify-between py-1.5">
                  <span className="text-gray-600 dark:text-gray-400">Structures Allowed:</span>
                  <span className={`font-medium ${allowsStructures ? 'text-green-600 dark:text-green-400' : 'text-gray-500 dark:text-gray-400'}`}>
                    {allowsStructures ? 'Yes' : 'No'}
                  </span>
                </div>
                <div className="flex justify-between py-1.5">
                  <span className="text-gray-600 dark:text-gray-400">Signage Rights:</span>
                  <span className={`font-medium ${signageRights ? 'text-green-600 dark:text-green-400' : 'text-gray-500 dark:text-gray-400'}`}>
                    {signageRights ? 'Yes' : 'No'}
                  </span>
                </div>
                {typeSpecificDetails.subletting_allowed && (
                  <div className="flex justify-between py-1.5">
                    <span className="text-gray-600 dark:text-gray-400">Subletting:</span>
                    <span className="font-medium text-green-600 dark:text-green-400">Allowed</span>
                  </div>
                )}
                {(() => {
                  const revenueShare = Number(typeSpecificDetails.revenue_share_percentage);
                  return !isNaN(revenueShare) && revenueShare > 0 ? (
                    <div className="flex justify-between py-1.5">
                      <span className="text-gray-600 dark:text-gray-400">Revenue Share:</span>
                      <span className="font-medium text-gray-900 dark:text-gray-100">{revenueShare.toFixed(2)}%</span>
                    </div>
                  ) : null;
                })()}
              </div>
            </motion.div>
          )}

          {/* Physical Features */}
          {(typeSpecificDetails.topography || typeSpecificDetails.floodplain_indicator || typeSpecificDetails.conservation_area) && (
            <motion.div
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: 0.3 }}
              className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-4 transition-colors duration-300"
            >
              <h3 className="font-semibold text-gray-900 dark:text-gray-100 mb-3 flex items-center gap-2 transition-colors duration-300">
                <Mountain className="h-5 w-5 text-amber-600 dark:text-amber-400" />
                Physical Features
              </h3>
              <div className="space-y-2 text-sm">
                {typeSpecificDetails.topography && (
                  <div className="flex justify-between">
                    <span className="text-gray-600 dark:text-gray-400">Topography:</span>
                    <span className="font-medium text-gray-900 dark:text-gray-100 capitalize">{typeSpecificDetails.topography}</span>
                  </div>
                )}
                {typeSpecificDetails.soil_type && (
                  <div className="flex justify-between">
                    <span className="text-gray-600 dark:text-gray-400">Soil Type:</span>
                    <span className="font-medium text-gray-900 dark:text-gray-100">{typeSpecificDetails.soil_type}</span>
                  </div>
                )}
                {typeSpecificDetails.drainage && (
                  <div className="flex justify-between">
                    <span className="text-gray-600 dark:text-gray-400">Drainage:</span>
                    <span className="font-medium text-gray-900 dark:text-gray-100 capitalize">{typeSpecificDetails.drainage}</span>
                  </div>
                )}
                {typeSpecificDetails.floodplain_indicator && (
                  <div className="flex items-center gap-2 py-1.5 px-2 bg-blue-50 dark:bg-blue-900/20 rounded">
                    <AlertCircle className="h-4 w-4 text-blue-600 dark:text-blue-400" />
                    <span className="text-blue-700 dark:text-blue-300 font-medium">In Floodplain Zone</span>
                  </div>
                )}
                {typeSpecificDetails.brownfield_indicator && (
                  <div className="flex items-center gap-2 py-1.5 px-2 bg-orange-50 dark:bg-orange-900/20 rounded">
                    <AlertCircle className="h-4 w-4 text-orange-600 dark:text-orange-400" />
                    <span className="text-orange-700 dark:text-orange-300 font-medium">Brownfield Site</span>
                  </div>
                )}
                {typeSpecificDetails.conservation_area && (
                  <div className="flex items-center gap-2 py-1.5 px-2 bg-green-50 dark:bg-green-900/20 rounded">
                    <Trees className="h-4 w-4 text-green-600 dark:text-green-400" />
                    <span className="text-green-700 dark:text-green-300 font-medium">Conservation Area</span>
                  </div>
                )}
              </div>
            </motion.div>
          )}

          {/* Utilities */}
          {Object.keys(utilitiesStatus).length > 0 && (
            <motion.div
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: 0.35 }}
              className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-4 transition-colors duration-300"
            >
              <h3 className="font-semibold text-gray-900 dark:text-gray-100 mb-3 flex items-center gap-2 transition-colors duration-300">
                <Zap className="h-5 w-5 text-yellow-600 dark:text-yellow-400" />
                Utilities Status
              </h3>
              <div className="grid grid-cols-2 gap-2">
                {Object.entries(utilitiesStatus).map(([utility, status]) => {
                  const statusStr = String(status || '');
                  return (
                    <div key={utility} className="flex justify-between items-center py-1.5">
                      <span className="text-gray-600 dark:text-gray-400 capitalize text-sm">{utility.replace(/_/g, ' ')}:</span>
                      <span className={`text-xs font-semibold px-2 py-0.5 rounded ${
                        statusStr === 'connected' 
                          ? 'bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300' 
                          : statusStr === 'available'
                          ? 'bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300'
                          : 'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400'
                      }`}>
                        {statusStr === 'not_available' ? 'N/A' : statusStr}
                      </span>
                    </div>
                  );
                })}
              </div>
            </motion.div>
          )}

          {/* Environmental & Legal */}
          {(typeSpecificDetails.environmental_assessment_phase1 || 
            typeSpecificDetails.environmental_assessment_phase2 || 
            typeSpecificDetails.title_registration_number) && (
            <motion.div
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: 0.4 }}
              className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-4 transition-colors duration-300"
            >
              <h3 className="font-semibold text-gray-900 dark:text-gray-100 mb-3 flex items-center gap-2 transition-colors duration-300">
                <Shield className="h-5 w-5 text-emerald-600 dark:text-emerald-400" />
                Environmental & Legal
              </h3>
              <div className="space-y-2 text-sm">
                {(typeSpecificDetails.environmental_assessment_phase1 || typeSpecificDetails.environmental_assessment_phase2) && (
                  <div className="flex justify-between">
                    <span className="text-gray-600 dark:text-gray-400">ESA Completed:</span>
                    <span className="font-medium text-gray-900 dark:text-gray-100">
                      {typeSpecificDetails.environmental_assessment_phase1 && 'Phase I'}
                      {typeSpecificDetails.environmental_assessment_phase1 && typeSpecificDetails.environmental_assessment_phase2 && ' & '}
                      {typeSpecificDetails.environmental_assessment_phase2 && 'Phase II'}
                    </span>
                  </div>
                )}
                {typeSpecificDetails.title_registration_province && (
                  <div className="flex justify-between">
                    <span className="text-gray-600 dark:text-gray-400">Title Registration:</span>
                    <span className="font-medium text-gray-900 dark:text-gray-100">{typeSpecificDetails.title_registration_province}</span>
                  </div>
                )}
                {typeSpecificDetails.title_registration_number && (
                  <div className="flex justify-between">
                    <span className="text-gray-600 dark:text-gray-400">Registration No.:</span>
                    <span className="font-medium text-gray-900 dark:text-gray-100">{typeSpecificDetails.title_registration_number}</span>
                  </div>
                )}
              </div>
            </motion.div>
          )}
        </div>

        {/* Right Column - Summary & Media */}
        <div className="space-y-4">
          {/* Quick Summary */}
          <motion.div
            initial={{ opacity: 0, x: 10 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.2 }}
            className="bg-gradient-to-br from-green-50 to-emerald-50 dark:from-green-900/30 dark:to-emerald-900/20 rounded-xl border border-green-200 dark:border-green-700 p-4 transition-colors duration-300"
          >
            <h4 className="font-semibold text-gray-900 dark:text-gray-100 mb-3 transition-colors duration-300">Quick Summary</h4>
            <div className="space-y-2 text-sm">
              {totalAcres && (
                <div className="bg-white dark:bg-gray-800 rounded-lg p-2">
                  <div className="flex items-center justify-between">
                    <span className="text-gray-600 dark:text-gray-400">Total Size:</span>
                    <span className="font-bold text-green-700 dark:text-green-300">{totalAcres} ac</span>
                  </div>
                </div>
              )}
              {leaseStructure && (
                <div className="bg-white dark:bg-gray-800 rounded-lg p-2">
                  <div className="flex items-center justify-between">
                    <span className="text-gray-600 dark:text-gray-400">Type:</span>
                    <span className="font-bold text-purple-700 dark:text-purple-300 capitalize text-xs">
                      {leaseStructure.replace(/_/g, ' ')}
                    </span>
                  </div>
                </div>
              )}
              {allowsStructures && (
                <div className="bg-white dark:bg-gray-800 rounded-lg p-2">
                  <div className="flex items-center gap-2">
                    <Building className="h-4 w-4 text-purple-600 dark:text-purple-400" />
                    <span className="text-xs font-medium text-gray-900 dark:text-gray-100">Development Allowed</span>
                  </div>
                </div>
              )}
            </div>
          </motion.div>

          {/* Images Preview */}
          {images.length > 0 && (
            <motion.div
              initial={{ opacity: 0, x: 10 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: 0.25 }}
              className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-4 transition-colors duration-300"
            >
              <h4 className="font-semibold text-gray-900 dark:text-gray-100 mb-3 flex items-center gap-2 transition-colors duration-300">
                <ImageIcon className="h-5 w-5 text-blue-600 dark:text-blue-400" />
                Images ({images.length})
              </h4>
              <div className="grid grid-cols-2 gap-2">
                {imageUrls.slice(0, 4).map((url, index) => (
                  <div key={index} className="relative aspect-video rounded-lg overflow-hidden bg-gray-100 dark:bg-gray-700">
                    <img
                      src={url}
                      alt={`Preview ${index + 1}`}
                      className="w-full h-full object-cover"
                    />
                  </div>
                ))}
              </div>
              {images.length > 4 && (
                <p className="text-xs text-gray-500 dark:text-gray-400 text-center mt-2 transition-colors duration-300">
                  +{images.length - 4} more image{images.length - 4 !== 1 ? 's' : ''}
                </p>
              )}
            </motion.div>
          )}

          {/* Warnings */}
          {warnings.length > 0 && (
            <motion.div
              initial={{ opacity: 0, x: 10 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: 0.3 }}
              className="bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-700 rounded-xl p-4 transition-colors duration-300"
            >
              <h4 className="font-semibold text-amber-900 dark:text-amber-200 mb-2 flex items-center gap-2 transition-colors duration-300">
                <AlertCircle className="h-5 w-5" />
                Recommendations
              </h4>
              <ul className="space-y-1 text-sm text-amber-800 dark:text-amber-300 transition-colors duration-300">
                {warnings.map((warning, index) => (
                  <li key={index} className="flex items-start gap-2">
                    <span className="text-amber-500 dark:text-amber-400 mt-0.5">•</span>
                    <span>{warning}</span>
                  </li>
                ))}
              </ul>
            </motion.div>
          )}
        </div>
      </div>
    </div>
  );
};

export default LandReview;

