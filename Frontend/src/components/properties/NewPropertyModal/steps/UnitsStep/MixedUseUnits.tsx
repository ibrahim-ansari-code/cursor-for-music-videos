import React, { useState, useEffect } from 'react';
import { useFormContext } from 'react-hook-form';
import { PropertyFormData, GeneratedUnit } from '@/types/property';
import { 
  Home, Store, TrendingUp, Car,
  Info, ChevronDown, ChevronRight, X, Check
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

interface MixedUseUnitsProps {
  onNext?: () => void;
}


interface EditingState {
  sectionType: 'residential' | 'commercial';
  unitIndex: number;
  field: 'name' | 'rent' | 'size' | 'bedrooms' | 'bathrooms';
}

const MixedUseUnits: React.FC<MixedUseUnitsProps> = () => {
  const { watch, setValue, getValues } = useFormContext<PropertyFormData>();
  const typeSpecificDetails = watch('type_specific_details');
  
  // Get data from MixedUseForm
  const mixedUseType = typeSpecificDetails?.mixed_use_type || 'retail_residential';
  const residentialSquareFeet = Number(typeSpecificDetails?.residential_square_feet) || 0;
  const commercialSquareFeet = Number(typeSpecificDetails?.commercial_square_feet) || 0;
  const residentialUnitsCount = Number(typeSpecificDetails?.residential_units_count) || 0;
  const commercialUnitsCount = Number(typeSpecificDetails?.commercial_units_count) || 0;
  const parkingSpacesTotal = Number(typeSpecificDetails?.parking_spaces_total) || 0;
  const residentialUnitTypes = typeSpecificDetails?.residential_unit_types || {};
  const commercialSpaceTypes = typeSpecificDetails?.commercial_space_types || [];
  
  const [residentialUnits, setResidentialUnits] = useState<GeneratedUnit[]>([]);
  const [commercialUnits, setCommercialUnits] = useState<GeneratedUnit[]>([]);
  const [expandedSections, setExpandedSections] = useState<Set<string>>(new Set(['residential', 'commercial']));
  const [editing, setEditing] = useState<EditingState | null>(null);
  const [tempValue, setTempValue] = useState<string>('');
  
  // Color mapping for Tailwind CSS production safety
  const colorClassMap = {
    blue: {
      gradient: 'bg-gradient-to-br from-blue-50 to-blue-100/50',
      border: 'border-blue-200'
    },
    green: {
      gradient: 'bg-gradient-to-br from-green-50 to-green-100/50',
      border: 'border-green-200'
    },
    indigo: {
      gradient: 'bg-gradient-to-br from-indigo-50 to-indigo-100/50',
      border: 'border-indigo-200'
    },
    purple: {
      gradient: 'bg-gradient-to-br from-purple-50 to-purple-100/50',
      border: 'border-purple-200'
    },
    orange: {
      gradient: 'bg-gradient-to-br from-orange-50 to-orange-100/50',
      border: 'border-orange-200'
    },
    amber: {
      gradient: 'bg-gradient-to-br from-amber-50 to-amber-100/50',
      border: 'border-amber-200'
    }
  };
  
  // Mixed-use type configurations
  const mixedUseTypeConfig = {
    live_work: { 
      emoji: '🏠', 
      label: 'Live/Work', 
      color: 'blue' as keyof typeof colorClassMap,
      defaultResRent: 1800,
      defaultComRent: 2000
    },
    retail_residential: { 
      emoji: '🛍️', 
      label: 'Retail + Residential', 
      color: 'green' as keyof typeof colorClassMap,
      defaultResRent: 1500,
      defaultComRent: 2500
    },
    office_residential: { 
      emoji: '🏢', 
      label: 'Office + Residential', 
      color: 'indigo' as keyof typeof colorClassMap,
      defaultResRent: 1600,
      defaultComRent: 2200
    },
    hotel_retail: { 
      emoji: '🏨', 
      label: 'Hotel + Retail', 
      color: 'purple' as keyof typeof colorClassMap,
      defaultResRent: 150, // per night
      defaultComRent: 3000
    },
    vertical_mixed: { 
      emoji: '🏗️', 
      label: 'Vertical Mixed', 
      color: 'orange' as keyof typeof colorClassMap,
      defaultResRent: 1700,
      defaultComRent: 2300
    },
    horizontal_mixed: { 
      emoji: '🏘️', 
      label: 'Horizontal Mixed', 
      color: 'amber' as keyof typeof colorClassMap,
      defaultResRent: 1400,
      defaultComRent: 2000
    }
  };
  
  const currentMixedType = mixedUseTypeConfig[mixedUseType as keyof typeof mixedUseTypeConfig] || mixedUseTypeConfig.retail_residential;
  
  // Unit type configurations
  const residentialUnitConfig = {
    studio: { label: 'Studio', bedrooms: 0, bathrooms: 1, defaultSize: 450 },
    '1br': { label: '1 Bedroom', bedrooms: 1, bathrooms: 1, defaultSize: 700 },
    '2br': { label: '2 Bedroom', bedrooms: 2, bathrooms: 2, defaultSize: 1000 },
    '3br': { label: '3 Bedroom', bedrooms: 3, bathrooms: 2, defaultSize: 1300 },
    '4br': { label: '4+ Bedroom', bedrooms: 4, bathrooms: 3, defaultSize: 1600 },
    penthouse: { label: 'Penthouse', bedrooms: 3, bathrooms: 3, defaultSize: 2000 }
  };
  
  const commercialTypeConfig = {
    retail: { label: 'Retail', emoji: '🛍️', defaultSize: 1500 },
    office: { label: 'Office', emoji: '💼', defaultSize: 1000 },
    restaurant: { label: 'Restaurant', emoji: '🍽️', defaultSize: 2500 },
    cafe: { label: 'Cafe', emoji: '☕', defaultSize: 800 },
    service: { label: 'Service', emoji: '🔧', defaultSize: 1200 },
    medical: { label: 'Medical', emoji: '🏥', defaultSize: 1500 }
  };
  
  // Initialize units based on unit types from MixedUseForm
  useEffect(() => {
    const existingUnits = getValues('generated_units');
    
    if (existingUnits && existingUnits.length > 0) {
      // Separate existing units
      const resUnits = existingUnits.filter((u: GeneratedUnit) => u.unit_type?.startsWith('res_'));
      const comUnits = existingUnits.filter((u: GeneratedUnit) => !u.unit_type?.startsWith('res_'));
      setResidentialUnits(resUnits);
      setCommercialUnits(comUnits);
    } else {
      generateUnitsFromMix();
    }
  }, [mixedUseType, residentialUnitsCount, commercialUnitsCount]);
  
  const generateUnitsFromMix = () => {
    // Generate residential units based on unit mix
    const newResUnits: GeneratedUnit[] = [];
    let resUnitCounter = 1;
    
    Object.entries(residentialUnitTypes).forEach(([type, count]) => {
      const config = residentialUnitConfig[type as keyof typeof residentialUnitConfig];
      if (config && count && Number(count) > 0) {
        for (let i = 0; i < Number(count); i++) {
          newResUnits.push({
            name: `Unit ${resUnitCounter}${String.fromCharCode(64 + (i % 26))}`,
            bedrooms: config.bedrooms,
            bathrooms: config.bathrooms,
            size: config.defaultSize,
            monthly_rent: currentMixedType.defaultResRent,
            unit_type: `res_${type}`,
            floor: Math.ceil(resUnitCounter / 10) + (mixedUseType === 'vertical_mixed' ? 1 : 0)
          });
          resUnitCounter++;
        }
      }
    });
    
    // If no unit mix specified but count given, generate default units
    if (newResUnits.length === 0 && residentialUnitsCount > 0) {
      const avgSize = residentialSquareFeet / residentialUnitsCount;
      for (let i = 0; i < residentialUnitsCount; i++) {
        newResUnits.push({
          name: `Residential Unit ${i + 1}`,
          bedrooms: 2,
          bathrooms: 1,
          size: avgSize,
          monthly_rent: currentMixedType.defaultResRent,
          unit_type: 'res_2br',
          floor: Math.ceil((i + 1) / 10) + (mixedUseType === 'vertical_mixed' ? 1 : 0)
        });
      }
    }
    
    // Generate commercial units based on space types
    const newComUnits: GeneratedUnit[] = [];
    
    if (commercialSpaceTypes.length > 0) {
      const sizePerUnit = commercialSquareFeet / Math.max(commercialSpaceTypes.length, commercialUnitsCount);
      commercialSpaceTypes.forEach((type: string, index: number) => {
        const config = commercialTypeConfig[type as keyof typeof commercialTypeConfig];
        if (config) {
          newComUnits.push({
            name: `${config.label} Space ${index + 1}`,
            size: config.defaultSize || sizePerUnit,
            monthly_rent: Math.round((config.defaultSize || sizePerUnit) * (currentMixedType.defaultComRent / 1000)),
            unit_type: type,
            description: `${config.label} space`,
            floor: mixedUseType === 'vertical_mixed' ? 1 : undefined
          });
        }
      });
    } else if (commercialUnitsCount > 0) {
      // Generate generic commercial units
      const sizePerUnit = commercialSquareFeet / commercialUnitsCount;
      for (let i = 0; i < commercialUnitsCount; i++) {
        newComUnits.push({
          name: `Commercial Suite ${String.fromCharCode(65 + i)}`,
          size: sizePerUnit,
          monthly_rent: Math.round(sizePerUnit * (currentMixedType.defaultComRent / 1000)),
          unit_type: 'retail',
          description: 'Commercial space',
          floor: mixedUseType === 'vertical_mixed' ? 1 : undefined
        });
      }
    }
    
    setResidentialUnits(newResUnits);
    setCommercialUnits(newComUnits);
  };
  
  // Save all units to form when they change
  useEffect(() => {
    const allUnits = [...residentialUnits, ...commercialUnits];
    setValue('generated_units', allUnits);
  }, [residentialUnits, commercialUnits, setValue]);
  
  const toggleSection = (section: string) => {
    setExpandedSections(prev => {
      const newSet = new Set(prev);
      if (newSet.has(section)) {
        newSet.delete(section);
      } else {
        newSet.add(section);
      }
      return newSet;
    });
  };
  
  const startEditing = (sectionType: 'residential' | 'commercial', unitIndex: number, field: EditingState['field'], currentValue: any) => {
    setEditing({ sectionType, unitIndex, field });
    setTempValue(currentValue?.toString() || '');
  };
  
  const saveEdit = () => {
    if (editing) {
      const units = editing.sectionType === 'residential' ? [...residentialUnits] : [...commercialUnits];
      const unit = units[editing.unitIndex];
      
      if (editing.field === 'name') {
        unit.name = tempValue;
      } else if (editing.field === 'rent') {
        unit.monthly_rent = parseFloat(tempValue) || 0;
      } else if (editing.field === 'size') {
        unit.size = parseFloat(tempValue) || 0;
      } else if (editing.field === 'bedrooms') {
        unit.bedrooms = parseInt(tempValue) || 0;
      } else if (editing.field === 'bathrooms') {
        unit.bathrooms = parseFloat(tempValue) || 0;
      }
      
      if (editing.sectionType === 'residential') {
        setResidentialUnits(units);
      } else {
        setCommercialUnits(units);
      }
      
      setEditing(null);
      setTempValue('');
    }
  };
  
  const cancelEdit = () => {
    setEditing(null);
    setTempValue('');
  };
  
  const removeUnit = (sectionType: 'residential' | 'commercial', index: number) => {
    if (sectionType === 'residential' && residentialUnits.length > 1) {
      setResidentialUnits(residentialUnits.filter((_, i) => i !== index));
    } else if (sectionType === 'commercial' && commercialUnits.length > 1) {
      setCommercialUnits(commercialUnits.filter((_, i) => i !== index));
    }
  };
  
  const getTotalMonthlyRent = () => {
    const resTotal = residentialUnits.reduce((sum, u) => sum + (u.monthly_rent || 0), 0);
    const comTotal = commercialUnits.reduce((sum, u) => sum + (u.monthly_rent || 0), 0);
    return resTotal + comTotal;
  };
  
  const getResidentialMonthlyRent = () => {
    return residentialUnits.reduce((sum, u) => sum + (u.monthly_rent || 0), 0);
  };
  
  const getCommercialMonthlyRent = () => {
    return commercialUnits.reduce((sum, u) => sum + (u.monthly_rent || 0), 0);
  };
  
  return (
    <div className="h-full flex flex-col">
      {/* Header with mixed-use type */}
      <div className="mb-6">
        <div className="flex items-center gap-3 mb-2">
          <span className="text-2xl">{currentMixedType.emoji}</span>
          <div>
            <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-100 transition-colors duration-300">
              {currentMixedType.label} Configuration
            </h2>
            <p className="text-sm text-gray-600 dark:text-gray-400 transition-colors duration-300">
              {residentialUnits.length} residential units • 
              {commercialUnits.length} commercial spaces
              {parkingSpacesTotal > 0 && ` • ${parkingSpacesTotal} parking spaces`}
            </p>
          </div>
        </div>
      </div>
      
      {/* Property Summary */}
      <div className={`rounded-xl p-4 mb-4 ${
        currentMixedType.color === 'blue' ? 'bg-gradient-to-br from-blue-50 to-blue-100/50 dark:from-blue-900/20 dark:to-blue-800/20 border-blue-200 dark:border-blue-700' :
        currentMixedType.color === 'green' ? 'bg-gradient-to-br from-green-50 to-green-100/50 dark:from-green-900/20 dark:to-green-800/20 border-green-200 dark:border-green-700' :
        currentMixedType.color === 'indigo' ? 'bg-gradient-to-br from-indigo-50 to-indigo-100/50 dark:from-indigo-900/20 dark:to-indigo-800/20 border-indigo-200 dark:border-indigo-700' :
        currentMixedType.color === 'purple' ? 'bg-gradient-to-br from-purple-50 to-purple-100/50 dark:from-purple-900/20 dark:to-purple-800/20 border-purple-200 dark:border-purple-700' :
        currentMixedType.color === 'orange' ? 'bg-gradient-to-br from-orange-50 to-orange-100/50 dark:from-orange-900/20 dark:to-orange-800/20 border-orange-200 dark:border-orange-700' :
        currentMixedType.color === 'amber' ? 'bg-gradient-to-br from-amber-50 to-amber-100/50 dark:from-amber-900/20 dark:to-amber-800/20 border-amber-200 dark:border-amber-700' :
        'bg-gradient-to-br from-gray-50 to-gray-100/50 dark:from-gray-900/20 dark:to-gray-800/20 border-gray-200 dark:border-gray-700'
      }`}>
        <div className="grid grid-cols-3 gap-3">
          <div className="bg-white dark:bg-gray-700 rounded-lg p-3 border border-gray-200 dark:border-gray-600 transition-colors duration-300">
            <div className="flex items-center gap-1 mb-1">
              <Home className="h-3.5 w-3.5 text-green-600" />
              <span className="text-xs font-medium text-gray-700 dark:text-gray-200 transition-colors duration-300">Residential</span>
            </div>
            <div className="text-lg font-bold text-gray-900 dark:text-gray-100 transition-colors duration-300">
              {residentialSquareFeet.toLocaleString()} SF
            </div>
            <div className="text-xs text-gray-600 dark:text-gray-400 transition-colors duration-300">
              {residentialUnits.length} units configured
            </div>
          </div>
          
          <div className="bg-white dark:bg-gray-700 rounded-lg p-3 border border-gray-200 dark:border-gray-600 transition-colors duration-300">
            <div className="flex items-center gap-1 mb-1">
              <Store className="h-3.5 w-3.5 text-purple-600" />
              <span className="text-xs font-medium text-gray-700 dark:text-gray-200">Commercial</span>
            </div>
            <div className="text-lg font-bold text-gray-900 dark:text-gray-100 transition-colors duration-300">
              {commercialSquareFeet.toLocaleString()} SF
            </div>
            <div className="text-xs text-gray-600 dark:text-gray-400 transition-colors duration-300">
              {commercialUnits.length} spaces configured
            </div>
          </div>
          
          <div className="bg-white dark:bg-gray-700 rounded-lg p-3 border border-gray-200 dark:border-gray-600 transition-colors duration-300">
            <div className="flex items-center gap-1 mb-1">
              <Car className="h-3.5 w-3.5 text-blue-600" />
              <span className="text-xs font-medium text-gray-700 dark:text-gray-200">Parking</span>
            </div>
            <div className="text-lg font-bold text-gray-900 dark:text-gray-100 transition-colors duration-300">
              {parkingSpacesTotal || 0}
            </div>
            <div className="text-xs text-gray-600 dark:text-gray-400 transition-colors duration-300">
              {parkingSpacesTotal > 0 
                ? `${(parkingSpacesTotal / (residentialUnits.length + commercialUnits.length)).toFixed(1)} per unit`
                : 'No parking'}
            </div>
          </div>
        </div>
      </div>
      
      {/* Units Sections */}
      <div className="flex-1 overflow-y-auto">
        <div className="space-y-3">
          {/* Residential Units Section */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-600 overflow-hidden transition-colors duration-300"

          >
            <button
              type="button"
              onClick={() => toggleSection('residential')}
              className="w-full px-4 py-3 bg-gradient-to-r from-green-50 to-emerald-50 dark:from-green-900/20 dark:to-emerald-900/20 hover:from-green-100 hover:to-emerald-100 dark:hover:from-green-800/30 dark:hover:to-emerald-800/30 transition-all flex items-center justify-between"

            >
              <div className="flex items-center gap-3">
                <Home className="h-5 w-5 text-green-600" />
                <div className="text-left">
                  <h4 className="font-semibold text-gray-900 dark:text-gray-100 transition-colors duration-300">Residential Units</h4>
                  <span className="text-xs text-gray-600 dark:text-gray-400 transition-colors duration-300">
                    {residentialUnits.length} units • ${getResidentialMonthlyRent().toLocaleString()}/mo
                  </span>
                </div>
              </div>
              {expandedSections.has('residential') ? (
                <ChevronDown className="h-4 w-4 text-gray-400" />
              ) : (
                <ChevronRight className="h-4 w-4 text-gray-400" />
              )}
            </button>
            
            <AnimatePresence>
              {expandedSections.has('residential') && (
                <motion.div
                  initial={{ height: 0 }}
                  animate={{ height: 'auto' }}
                  exit={{ height: 0 }}
                  className="overflow-hidden"
                >
                  <div className="p-4 bg-gray-50/50 dark:bg-gray-800/20 space-y-2 transition-colors duration-300">
                    {residentialUnits.map((unit, index) => (
                      <div key={`res-${index}`} className="bg-white dark:bg-gray-700 rounded-lg p-3 border border-gray-200 dark:border-gray-600 transition-colors duration-300">

                        <div className="flex items-center justify-between mb-2">
                          <div className="flex items-center gap-2">
                            {editing?.sectionType === 'residential' && editing?.unitIndex === index && editing?.field === 'name' ? (
                              <div className="flex items-center gap-1">
                                <input
                                  type="text"
                                  value={tempValue}
                                  onChange={(e) => setTempValue(e.target.value)}
                                  onKeyDown={(e) => {
                                    if (e.key === 'Enter') saveEdit();
                                    if (e.key === 'Escape') cancelEdit();
                                  }}
                                  className="px-2 py-1 text-sm font-semibold border border-blue-300 dark:border-blue-500 rounded-md focus:ring-2 focus:ring-blue-500 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 transition-colors duration-300"

                                  autoFocus
                                />
                                <Check onClick={saveEdit} className="h-4 w-4 text-green-600 cursor-pointer" />
                                <X onClick={cancelEdit} className="h-4 w-4 text-red-600 cursor-pointer" />
                              </div>
                            ) : (
                              <h4 
                                className="font-medium text-gray-900 dark:text-gray-100 cursor-pointer hover:text-blue-600 dark:hover:text-blue-400 transition-colors"

                                onClick={() => startEditing('residential', index, 'name', unit.name)}
                              >
                                {unit.name}
                              </h4>
                            )}
                            
                            {unit.floor && (
                              <span className="px-2 py-0.5 text-xs font-medium text-gray-600 dark:text-gray-400 bg-gray-100 dark:bg-gray-600 rounded-full transition-colors duration-300">
                                Floor {unit.floor}
                              </span>
                            )}
                          </div>
                          
                          {residentialUnits.length > 1 && (
                            <button
                              type="button"
                              onClick={() => removeUnit('residential', index)}
                              className="p-1 text-gray-400 hover:text-red-500"
                            >
                              <X className="h-4 w-4" />
                            </button>
                          )}
                        </div>
                        
                        <div className="grid grid-cols-5 gap-2">
                          <div className="text-center">
                            <span className="text-[10px] text-gray-500 dark:text-gray-400 transition-colors duration-300">Beds</span>
                            <div className="text-sm font-semibold text-gray-700 dark:text-gray-200 transition-colors duration-300">{unit.bedrooms || 0}</div>
                          </div>
                          <div className="text-center">
                            <span className="text-[10px] text-gray-500 dark:text-gray-400 transition-colors duration-300">Baths</span>
                            <div className="text-sm font-semibold text-gray-700 dark:text-gray-200 transition-colors duration-300">{unit.bathrooms || 0}</div>
                          </div>
                          <div className="text-center">
                            <span className="text-[10px] text-gray-500 dark:text-gray-400 transition-colors duration-300">Size</span>
                            <div 
                              className="text-sm font-semibold text-blue-600 dark:text-blue-400 cursor-pointer hover:text-blue-700 dark:hover:text-blue-300 transition-colors"
                              onClick={() => startEditing('residential', index, 'size', unit.size)}
                            >
                              {unit.size || 0} SF
                            </div>
                          </div>
                          <div className="text-center">
                            <span className="text-[10px] text-gray-500 dark:text-gray-400 transition-colors duration-300">Rent</span>
                            <div 
                              className="text-sm font-semibold text-green-600 dark:text-green-400 cursor-pointer hover:text-green-700 dark:hover:text-green-300 transition-colors"
                              onClick={() => startEditing('residential', index, 'rent', unit.monthly_rent)}
                            >
                              ${unit.monthly_rent || 0}
                            </div>
                          </div>
                          <div className="text-center">
                            <span className="text-[10px] text-gray-500 dark:text-gray-400 transition-colors duration-300">$/SF</span>
                            <div className="text-sm font-semibold text-purple-600 dark:text-purple-400 transition-colors duration-300">
                              ${unit.size && unit.monthly_rent 
                                ? ((unit.monthly_rent * 12) / unit.size).toFixed(2)
                                : '0.00'}
                            </div>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </motion.div>
          
          {/* Commercial Units Section */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
            className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-600 overflow-hidden transition-colors duration-300"

          >
            <button
              type="button"
              onClick={() => toggleSection('commercial')}
              className="w-full px-4 py-3 bg-gradient-to-r from-purple-50 to-indigo-50 dark:from-purple-900/20 dark:to-indigo-900/20 hover:from-purple-100 hover:to-indigo-100 dark:hover:from-purple-800/30 dark:hover:to-indigo-800/30 transition-all flex items-center justify-between"

            >
              <div className="flex items-center gap-3">
                <Store className="h-5 w-5 text-purple-600" />
                <div className="text-left">
                  <h4 className="font-semibold text-gray-900 dark:text-gray-100 transition-colors duration-300">Commercial Spaces</h4>
                  <span className="text-xs text-gray-600 dark:text-gray-400 transition-colors duration-300">
                    {commercialUnits.length} spaces • ${getCommercialMonthlyRent().toLocaleString()}/mo
                  </span>
                </div>
              </div>
              {expandedSections.has('commercial') ? (
                <ChevronDown className="h-4 w-4 text-gray-400" />
              ) : (
                <ChevronRight className="h-4 w-4 text-gray-400" />
              )}
            </button>
            
            <AnimatePresence>
              {expandedSections.has('commercial') && (
                <motion.div
                  initial={{ height: 0 }}
                  animate={{ height: 'auto' }}
                  exit={{ height: 0 }}
                  className="overflow-hidden"
                >
                  <div className="p-4 bg-gray-50/50 dark:bg-gray-800/20 space-y-2 transition-colors duration-300">
                    {commercialUnits.map((unit, index) => {
                      const typeConfig = commercialTypeConfig[unit.unit_type as keyof typeof commercialTypeConfig];
                      
                      return (
                        <div key={`com-${index}`} className="bg-white dark:bg-gray-700 rounded-lg p-3 border border-gray-200 dark:border-gray-600 transition-colors duration-300">

                          <div className="flex items-center justify-between mb-2">
                            <div className="flex items-center gap-2">
                              <span className="text-lg">{typeConfig?.emoji || '🏢'}</span>
                              {editing?.sectionType === 'commercial' && editing?.unitIndex === index && editing?.field === 'name' ? (
                                <div className="flex items-center gap-1">
                                  <input
                                    type="text"
                                    value={tempValue}
                                    onChange={(e) => setTempValue(e.target.value)}
                                    onKeyDown={(e) => {
                                      if (e.key === 'Enter') saveEdit();
                                      if (e.key === 'Escape') cancelEdit();
                                    }}
                                    className="px-2 py-1 text-sm font-semibold border border-blue-300 dark:border-blue-500 rounded-md focus:ring-2 focus:ring-blue-500 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 transition-colors duration-300"

                                    autoFocus
                                  />
                                  <Check onClick={saveEdit} className="h-4 w-4 text-green-600 cursor-pointer" />
                                  <X onClick={cancelEdit} className="h-4 w-4 text-red-600 cursor-pointer" />
                                </div>
                              ) : (
                                <h4 
                                  className="font-medium text-gray-900 dark:text-gray-100 cursor-pointer hover:text-blue-600 dark:hover:text-blue-400 transition-colors"

                                  onClick={() => startEditing('commercial', index, 'name', unit.name)}
                                >
                                  {unit.name}
                                </h4>
                              )}
                              
                              {unit.floor && (
                                <span className="px-2 py-0.5 text-xs font-medium text-gray-600 dark:text-gray-400 bg-gray-100 dark:bg-gray-600 rounded-full transition-colors duration-300">
                                  Floor {unit.floor}
                                </span>
                              )}
                            </div>
                            
                            {commercialUnits.length > 1 && (
                              <button
                                type="button"
                                onClick={() => removeUnit('commercial', index)}
                                className="p-1 text-gray-400 hover:text-red-500"
                              >
                                <X className="h-4 w-4" />
                              </button>
                            )}
                          </div>
                          
                          <div className="grid grid-cols-3 gap-2">
                            <div className="text-center">
                              <span className="text-[10px] text-gray-500 dark:text-gray-400 transition-colors duration-300">Size</span>
                              <div 
                                className="text-sm font-semibold text-blue-600 dark:text-blue-400 cursor-pointer hover:text-blue-700 dark:hover:text-blue-300 transition-colors"
                                onClick={() => startEditing('commercial', index, 'size', unit.size)}
                              >
                                {(unit.size || 0).toLocaleString()} SF
                              </div>
                            </div>
                            <div className="text-center">
                              <span className="text-[10px] text-gray-500 dark:text-gray-400 transition-colors duration-300">Monthly Rent</span>
                              <div 
                                className="text-sm font-semibold text-green-600 dark:text-green-400 cursor-pointer hover:text-green-700 dark:hover:text-green-300 transition-colors"
                                onClick={() => startEditing('commercial', index, 'rent', unit.monthly_rent)}
                              >
                                ${unit.monthly_rent?.toLocaleString() || 0}
                              </div>
                            </div>
                            <div className="text-center">
                              <span className="text-[10px] text-gray-500 dark:text-gray-400 transition-colors duration-300">$/SF/Year</span>
                              <div className="text-sm font-semibold text-purple-600 dark:text-purple-400 transition-colors duration-300">
                                ${unit.size && unit.monthly_rent 
                                  ? ((unit.monthly_rent * 12) / unit.size).toFixed(2)
                                  : '0.00'}
                              </div>
                            </div>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </motion.div>
        </div>
      </div>
      
      {/* Footer Summary */}
      <div className="mt-6 space-y-3">
        {/* Revenue Summary */}
        {getTotalMonthlyRent() > 0 && (
          <div className="bg-gradient-to-br from-green-50 to-emerald-50/50 dark:from-green-900/20 dark:to-emerald-900/20 rounded-xl p-4 border border-green-200 dark:border-green-700">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <TrendingUp className="h-4 w-4 text-green-600" />
                <span className="text-sm font-medium text-green-900 dark:text-green-100">
                  Revenue Projection
                </span>
              </div>
              <div className="text-right">
                <div className="text-lg font-bold text-green-700 dark:text-green-300">
                  ${getTotalMonthlyRent().toLocaleString()}/mo
                </div>
                <div className="text-xs text-green-600 dark:text-green-400">
                  ${(getTotalMonthlyRent() * 12).toLocaleString()}/year
                </div>
              </div>
            </div>
            
            <div className="grid grid-cols-2 gap-3 pt-3 border-t border-green-200 dark:border-green-700">
              <div>
                <div className="flex items-center gap-1 mb-1">
                  <Home className="h-3 w-3 text-green-600" />
                  <span className="text-xs text-green-700 dark:text-green-300">Residential Income</span>
                </div>
                <div className="text-sm font-semibold text-green-800 dark:text-green-200">
                  ${getResidentialMonthlyRent().toLocaleString()}/mo
                </div>
              </div>
              <div>
                <div className="flex items-center gap-1 mb-1">
                  <Store className="h-3 w-3 text-purple-600" />
                  <span className="text-xs text-purple-700 dark:text-purple-300">Commercial Income</span>
                </div>
                <div className="text-sm font-semibold text-purple-800 dark:text-purple-200">
                  ${getCommercialMonthlyRent().toLocaleString()}/mo
                </div>
              </div>
            </div>
          </div>
        )}
        
        {/* Info Box */}
        <div className="bg-blue-50 dark:bg-blue-900/20 rounded-xl p-3.5 border border-blue-200 dark:border-blue-700">
          <div className="flex items-start gap-2">
            <Info className="h-4 w-4 text-blue-600 mt-0.5 flex-shrink-0" />
            <div>
              <p className="text-xs font-semibold text-blue-900 dark:text-blue-100 mb-1">Mixed-Use Configuration</p>
              <p className="text-xs text-blue-700 dark:text-blue-300 leading-relaxed">
                Your {currentMixedType.label.toLowerCase()} property combines residential and commercial spaces. 
                {mixedUseType === 'vertical_mixed' && ' Commercial spaces are on the ground floor with residential units above.'}
                {mixedUseType === 'horizontal_mixed' && ' Residential and commercial areas are separated horizontally.'}
                {' '}This configuration typically provides stable income through diversified revenue streams.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default React.memo(MixedUseUnits);