import React, { useState, useEffect } from 'react';
import { useFormContext } from 'react-hook-form';
import { PropertyFormData, GeneratedUnit } from '@/types/property';
import { 
  Key, X, Check, Lock,
  Bed, Bath, DollarSign, Square,
  Info, Sparkles, AlertCircle
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

interface ResidentialUnitsProps {
  onNext?: () => void;
}

// Residential subtype configurations - matching ResidentialForm.tsx
const RESIDENTIAL_CONFIGS = {
  single_family: {
    title: 'Single Family Home',
    emoji: '🏡',
    unitCount: 1,
    canAddADU: true,
    defaultUnits: [
      { name: 'Main Residence', bedrooms: 3, bathrooms: 2, unit_type: 'main' }
    ]
  },
  townhouse: {
    title: 'Townhouse',
    emoji: '🏘️',
    unitCount: 1,
    canAddADU: false,
    defaultUnits: [
      { name: 'Townhouse Unit', bedrooms: 3, bathrooms: 2.5, unit_type: 'townhouse' }
    ]
  },
  condo: {
    title: 'Condominium',
    emoji: '🏢',
    unitCount: 1,
    canAddADU: false,
    defaultUnits: [
      { name: 'Condo Unit', bedrooms: 2, bathrooms: 2, unit_type: 'condo' }
    ]
  },
  duplex: {
    title: 'Duplex',
    emoji: '👥',
    unitCount: 2,
    canAddADU: false,
    defaultUnits: [
      { name: 'Unit A', bedrooms: 2, bathrooms: 1.5, unit_type: 'duplex' },
      { name: 'Unit B', bedrooms: 2, bathrooms: 1.5, unit_type: 'duplex' }
    ]
  },
  manufactured: {
    title: 'Manufactured Home',
    emoji: '🏗️',
    unitCount: 1,
    canAddADU: true,
    defaultUnits: [
      { name: 'Main Unit', bedrooms: 3, bathrooms: 2, unit_type: 'manufactured' }
    ]
  },
  mobile_home: {
    title: 'Mobile Home',
    emoji: '🚐',
    unitCount: 1,
    canAddADU: false,
    defaultUnits: [
      { name: 'Mobile Home Unit', bedrooms: 2, bathrooms: 1, unit_type: 'mobile' }
    ]
  }
};

interface EditingState {
  unitIndex: number;
  field: 'bedrooms' | 'bathrooms' | 'rent' | 'size';
}

const ResidentialUnits: React.FC<ResidentialUnitsProps> = () => {
  const { watch, setValue, getValues } = useFormContext<PropertyFormData>();
  const typeSpecificDetails = watch('type_specific_details');
  const subtype = typeSpecificDetails?.property_subtype || 'single_family';
  
  // Get bedrooms and bathrooms from previous step
  const bedroomsFromDetails = typeSpecificDetails?.bedrooms;
  const bathroomsFromDetails = typeSpecificDetails?.bathrooms;
  
  const [units, setUnits] = useState<GeneratedUnit[]>([]);
  const [hasADU, setHasADU] = useState(false);
  const [editing, setEditing] = useState<EditingState | null>(null);
  const [tempValue, setTempValue] = useState<string>('');
  
  const config = RESIDENTIAL_CONFIGS[subtype as keyof typeof RESIDENTIAL_CONFIGS] || RESIDENTIAL_CONFIGS.single_family;
  const isDuplex = subtype === 'duplex';

  // Initialize units based on subtype
  useEffect(() => {
    const existingUnits = getValues('generated_units');
    
    // Check if we already have the right units for this subtype
    if (existingUnits && existingUnits.length > 0) {
      // For duplex, maintain the distribution but ensure totals match
      if (isDuplex && bedroomsFromDetails && bathroomsFromDetails) {
        // Don't override existing units for duplex
        setUnits(existingUnits);
      } else {
        // Update the main unit with values from ResidentialForm if available
        const updatedUnits = existingUnits.map((unit, index) => {
          if (index === 0 && unit.unit_type !== 'adu') {
            // This is the main unit - use values from ResidentialForm
            return {
              ...unit,
              bedrooms: bedroomsFromDetails || unit.bedrooms,
              bathrooms: bathroomsFromDetails || unit.bathrooms
            };
          }
          return unit;
        });
        setUnits(updatedUnits);
      }
      setHasADU(existingUnits.some(u => u.unit_type === 'adu'));
    } else {
      // Initialize with default units for this subtype
      if (isDuplex && bedroomsFromDetails && bathroomsFromDetails) {
        // For duplex, distribute bedrooms and bathrooms intelligently
        const totalBedrooms = bedroomsFromDetails;
        const totalBathrooms = bathroomsFromDetails;
        
        // Try to distribute evenly, with Unit A getting any remainder
        const bedroomsPerUnit = Math.floor(totalBedrooms / 2);
        const bedroomsRemainder = totalBedrooms % 2;
        const bathroomsPerUnit = Math.floor(totalBathrooms / 2);
        const bathroomsRemainder = totalBathrooms - (bathroomsPerUnit * 2);
        
        const duplexUnits = [
          {
            name: 'Unit A',
            bedrooms: bedroomsPerUnit + bedroomsRemainder,
            bathrooms: bathroomsPerUnit + (bathroomsRemainder > 0 ? 0.5 : 0),
            unit_type: 'duplex',
            monthly_rent: undefined,
            size: undefined
          },
          {
            name: 'Unit B', 
            bedrooms: bedroomsPerUnit,
            bathrooms: bathroomsPerUnit + (bathroomsRemainder > 0.5 ? 0.5 : 0),
            unit_type: 'duplex',
            monthly_rent: undefined,
            size: undefined
          }
        ];
        setUnits(duplexUnits);
      } else {
        const defaultUnits = config.defaultUnits.map((u, index) => {
          if (index === 0) {
            // For the main unit, use values from ResidentialForm if available
            return {
              ...u,
              bedrooms: bedroomsFromDetails || u.bedrooms,
              bathrooms: bathroomsFromDetails || u.bathrooms,
              monthly_rent: undefined,
              size: undefined
            };
          }
          return { 
            ...u, 
            monthly_rent: undefined,
            size: undefined 
          };
        });
        setUnits(defaultUnits);
      }
      setHasADU(false);
    }
  }, [subtype, bedroomsFromDetails, bathroomsFromDetails, isDuplex]);

  // Save units to form when they change
  useEffect(() => {
    setValue('generated_units', units);
  }, [units, setValue]);

  const addADU = () => {
    const aduUnit: GeneratedUnit = {
      name: 'Accessory Dwelling Unit (ADU)',
      bedrooms: 1,
      bathrooms: 1,
      unit_type: 'adu',
      size: 600,
      monthly_rent: undefined
    };
    setUnits([...units, aduUnit]);
    setHasADU(true);
  };

  const removeADU = () => {
    setUnits(units.filter(u => u.unit_type !== 'adu'));
    setHasADU(false);
  };

  const startEditing = (unitIndex: number, field: EditingState['field'], currentValue: any) => {
    const unit = units[unitIndex];
    
    // For single-family homes and other single-unit types
    if (!isDuplex) {
      const isMainUnit = unitIndex === 0 && unit.unit_type !== 'adu';
      
      if (isMainUnit && (field === 'bedrooms' || field === 'bathrooms')) {
        // Main unit bedrooms/bathrooms are locked from ResidentialForm
        return;
      }
    }
    
    // For duplex, bedrooms and bathrooms can be edited with validation
    setEditing({ unitIndex, field });
    setTempValue(currentValue?.toString() || '');
  };

  const saveEdit = () => {
    if (editing) {
      const newUnits = [...units];
      const value = tempValue === '' ? undefined : 
                    (editing.field === 'bedrooms' ? parseInt(tempValue) :
                     editing.field === 'bathrooms' || editing.field === 'size' || editing.field === 'rent' ? 
                     parseFloat(tempValue) : tempValue);
      
      // For duplex, validate bedroom/bathroom changes
      if (isDuplex && (editing.field === 'bedrooms' || editing.field === 'bathrooms')) {
        const otherUnitIndex = editing.unitIndex === 0 ? 1 : 0;
        const otherUnit = newUnits[otherUnitIndex];
        
        if (editing.field === 'bedrooms') {
          const newBedrooms = value as number || 0;
          const totalRequired = bedroomsFromDetails || 0;
          const remainingBedrooms = totalRequired - newBedrooms;
          
          if (remainingBedrooms < 0) {
            // Can't exceed total
            return;
          }
          
          // Update both units
          newUnits[editing.unitIndex] = { ...newUnits[editing.unitIndex], bedrooms: newBedrooms };
          newUnits[otherUnitIndex] = { ...otherUnit, bedrooms: remainingBedrooms };
        } else if (editing.field === 'bathrooms') {
          const newBathrooms = value as number || 0;
          const totalRequired = bathroomsFromDetails || 0;
          const remainingBathrooms = totalRequired - newBathrooms;
          
          if (remainingBathrooms < 0) {
            // Can't exceed total
            return;
          }
          
          // Update both units
          newUnits[editing.unitIndex] = { ...newUnits[editing.unitIndex], bathrooms: newBathrooms };
          newUnits[otherUnitIndex] = { ...otherUnit, bathrooms: remainingBathrooms };
        }
      } else if (editing.field === 'rent') {
        newUnits[editing.unitIndex] = { ...newUnits[editing.unitIndex], monthly_rent: value as number };
      } else {
        newUnits[editing.unitIndex] = { ...newUnits[editing.unitIndex], [editing.field]: value };
      }
      
      setUnits(newUnits);
      setEditing(null);
      setTempValue('');
    }
  };

  const cancelEdit = () => {
    setEditing(null);
    setTempValue('');
  };

  const getTotalMonthlyRent = () => {
    return units.reduce((sum, unit) => sum + (unit.monthly_rent || 0), 0);
  };

  const getTotalBedrooms = () => {
    return units.filter(u => u.unit_type !== 'adu').reduce((sum, unit) => sum + (unit.bedrooms || 0), 0);
  };

  const getTotalBathrooms = () => {
    return units.filter(u => u.unit_type !== 'adu').reduce((sum, unit) => sum + (unit.bathrooms || 0), 0);
  };

  const isValidDistribution = () => {
    if (!isDuplex) return true;
    
    const totalBeds = getTotalBedrooms();
    const totalBaths = getTotalBathrooms();
    
    return totalBeds === (bedroomsFromDetails || 0) && 
           totalBaths === (bathroomsFromDetails || 0);
  };

  return (
    <div className="h-full flex flex-col">
      {/* Header with emoji and title */}
      <div className="mb-6">
        <div className="flex items-center gap-3 mb-2">
          <span className="text-2xl">{config.emoji}</span>
          <div>
            <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-100 transition-colors duration-300">{config.title}</h2>
            <p className="text-sm text-gray-600 dark:text-gray-400 transition-colors duration-300">
              Quick setup for {config.unitCount} {config.unitCount === 1 ? 'unit' : 'units'}
              {config.canAddADU && ' with optional ADU'}
            </p>
          </div>
        </div>
      </div>

      {/* Duplex Distribution Info */}
      {isDuplex && bedroomsFromDetails && bathroomsFromDetails && (
        <div className={`mb-4 p-3 rounded-lg border transition-colors duration-300 ${
          isValidDistribution() 
            ? 'bg-green-50 dark:bg-green-900/20 border-green-200 dark:border-green-700' 
            : 'bg-amber-50 dark:bg-amber-900/20 border-amber-200 dark:border-amber-700'
        }`}>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              {isValidDistribution() ? (
                <Check className="h-4 w-4 text-green-600" />
              ) : (
                <AlertCircle className="h-4 w-4 text-amber-600" />
              )}
              <span className={`text-xs font-medium transition-colors duration-300 ${
                isValidDistribution() ? 'text-green-900 dark:text-green-100' : 'text-amber-900 dark:text-amber-100'
              }`}>
                Total Property: {bedroomsFromDetails} bed, {bathroomsFromDetails} bath
              </span>
            </div>
            <span className={`text-xs transition-colors duration-300 ${
              isValidDistribution() ? 'text-green-700 dark:text-green-300' : 'text-amber-700 dark:text-amber-300'
            }`}>
              Units Total: {getTotalBedrooms()} bed, {getTotalBathrooms()} bath
            </span>
          </div>
          {!isValidDistribution() && (
            <p className="text-xs text-amber-700 dark:text-amber-300 mt-2 transition-colors duration-300">
              Adjust unit bedrooms/bathrooms to match the property total
            </p>
          )}
        </div>
      )}

      {/* Units Container */}
      <div className="flex-1 overflow-y-auto">
        <div className="space-y-4">
          <AnimatePresence>
            {units.map((unit, index) => (
              <motion.div
                key={`${unit.name}-${index}`}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, x: -100 }}
                transition={{ delay: index * 0.05 }}
              >
                {/* Unit Card - Modern Design */}
                <div className={`bg-gradient-to-br ${
                  unit.unit_type === 'adu' 
                    ? 'from-blue-50 to-indigo-50/50 dark:from-blue-900/20 dark:to-indigo-900/20' 
                    : 'from-gray-50 to-gray-100/50 dark:from-gray-900/20 dark:to-gray-800/20'
                } rounded-xl p-4 border ${
                  unit.unit_type === 'adu' ? 'border-blue-200 dark:border-blue-700' : 'border-gray-200 dark:border-gray-700'
                }`}>
                  {/* Unit Header */}
                  <div className="flex items-center justify-between mb-4">
                    <div className="flex items-center gap-2">
                      <h3 className="font-semibold text-gray-900 dark:text-gray-100">{unit.name}</h3>
                      {unit.unit_type === 'adu' && (
                        <span className="px-2.5 py-0.5 text-xs font-medium text-blue-700 bg-blue-100 rounded-full">
                          ADU
                        </span>
                      )}
                    </div>
                    {unit.unit_type === 'adu' && (
                      <button
                        type="button"
                        onClick={removeADU}
                        className="p-1.5 text-gray-400 hover:text-red-500 hover:bg-red-50 rounded-lg transition-all"
                        title="Remove ADU"
                      >
                        <X className="h-4 w-4" />
                      </button>
                    )}
                  </div>

                  {/* Unit Details Grid - Matching ResidentialForm Style */}
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                    {/* Bedrooms */}
                    {(() => {
                      const isMainUnit = index === 0 && unit.unit_type !== 'adu' && !isDuplex;
                      const isLocked = isMainUnit && bedroomsFromDetails;
                      
                      return (
                        <div className={`bg-white dark:bg-gray-800 rounded-lg p-3 border transition-colors group ${
                          isLocked ? 'border-gray-200 dark:border-gray-600 bg-gray-50 dark:bg-gray-700' : 
                          isDuplex ? 'border-blue-200 dark:border-blue-600 hover:border-blue-300 dark:hover:border-blue-400' :
                          'border-gray-200 dark:border-gray-600 hover:border-blue-300 dark:hover:border-blue-400'
                        }`}>
                          <div className="flex items-center justify-between mb-1.5">
                            <span className="text-xs font-medium text-gray-600 dark:text-gray-300 group-hover:text-gray-900 transition-colors">
                              <Bed className="h-3.5 w-3.5 inline mr-1 text-blue-500 dark:text-blue-400" />
                              Bedrooms
                              {isLocked && <Lock className="h-3 w-3 inline ml-1 text-gray-400 dark:text-gray-500" />}
                            </span>
                            {!editing || editing.unitIndex !== index || editing.field !== 'bedrooms' ? (
                              <span className="text-xs text-blue-600 dark:text-blue-400 font-semibold">
                                {unit.bedrooms || 0} {unit.bedrooms === 1 ? 'bed' : 'beds'}
                              </span>
                            ) : null}
                          </div>
                          {editing?.unitIndex === index && editing?.field === 'bedrooms' ? (
                            <div className="flex items-center gap-1">
                              <input
                                type="number"
                                min="0"
                                max={isDuplex ? bedroomsFromDetails : 10}
                                value={tempValue}
                                onChange={(e) => setTempValue(e.target.value)}
                                onKeyDown={(e) => {
                                  if (e.key === 'Enter') saveEdit();
                                  if (e.key === 'Escape') cancelEdit();
                                }}
                                className="w-full px-2 py-1 text-sm font-medium border border-blue-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                                autoFocus
                              />
                              <button
                                type="button"
                                onClick={saveEdit}
                                className="p-1 text-green-600 hover:text-green-700 hover:bg-green-50 rounded"
                              >
                                <Check className="h-3.5 w-3.5" />
                              </button>
                            </div>
                          ) : (
                            <button
                              type="button"
                              onClick={() => startEditing(index, 'bedrooms', unit.bedrooms)}
                              className={`w-full text-left px-2.5 py-1.5 text-sm font-medium border rounded-md transition-all ${
                                isLocked 
                                  ? 'border-gray-200 dark:border-gray-600 bg-gray-50 dark:bg-gray-700 text-gray-500 dark:text-gray-400 cursor-not-allowed' 
                                  : isDuplex
                                  ? 'border-blue-200 dark:border-blue-600 hover:bg-blue-50 dark:hover:bg-blue-900/20 text-blue-700 dark:text-blue-300'
                                  : 'border-gray-200 dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-700 dark:hover:bg-gray-700 dark:text-gray-200'
                              }`}
                              disabled={isLocked}
                              title={isLocked ? 'Set from property details' : 
                                     isDuplex ? 'Adjust to match property total' : undefined}
                            >
                              {unit.bedrooms || 0}
                            </button>
                          )}
                        </div>
                      );
                    })()}

                    {/* Bathrooms */}
                    {(() => {
                      const isMainUnit = index === 0 && unit.unit_type !== 'adu' && !isDuplex;
                      const isLocked = isMainUnit && bathroomsFromDetails;
                      
                      return (
                        <div className={`bg-white dark:bg-gray-800 rounded-lg p-3 border ${
                          isLocked ? 'border-gray-200 dark:border-gray-600 bg-gray-50 dark:bg-gray-700' :
                          isDuplex ? 'border-blue-200 dark:border-blue-600 hover:border-blue-300 dark:hover:border-blue-400' :
                          'border-gray-200 dark:border-gray-600 hover:border-blue-300 dark:hover:border-blue-400'
                        } transition-colors group`}>
                          <div className="flex items-center justify-between mb-1.5">
                            <span className="text-xs font-medium text-gray-600 dark:text-gray-300 group-hover:text-gray-900 transition-colors">
                              <Bath className="h-3.5 w-3.5 inline mr-1 text-blue-500 dark:text-blue-400" />
                              Bathrooms
                              {isLocked && <Lock className="h-3 w-3 inline ml-1 text-gray-400 dark:text-gray-500" />}
                            </span>
                            {!editing || editing.unitIndex !== index || editing.field !== 'bathrooms' ? (
                              <span className="text-xs text-blue-600 dark:text-blue-400 font-semibold">
                                {unit.bathrooms || 0} {unit.bathrooms === 1 ? 'bath' : 'baths'}
                              </span>
                            ) : null}
                          </div>
                          {editing?.unitIndex === index && editing?.field === 'bathrooms' ? (
                            <div className="flex items-center gap-1">
                              <input
                                type="number"
                                min="0"
                                max={isDuplex ? bathroomsFromDetails : 10}
                                step="0.5"
                                value={tempValue}
                                onChange={(e) => setTempValue(e.target.value)}
                                onKeyDown={(e) => {
                                  if (e.key === 'Enter') saveEdit();
                                  if (e.key === 'Escape') cancelEdit();
                                }}
                                className="w-full px-2 py-1 text-sm font-medium border border-blue-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                                autoFocus
                              />
                              <button
                                type="button"
                                onClick={saveEdit}
                                className="p-1 text-green-600 hover:text-green-700 hover:bg-green-50 rounded"
                              >
                                <Check className="h-3.5 w-3.5" />
                              </button>
                            </div>
                          ) : (
                            <button
                              type="button"
                              onClick={() => startEditing(index, 'bathrooms', unit.bathrooms)}
                              className={`w-full text-left px-2.5 py-1.5 text-sm font-medium border rounded-md transition-all ${
                                isLocked 
                                  ? 'border-gray-200 dark:border-gray-600 bg-gray-50 dark:bg-gray-700 text-gray-500 dark:text-gray-400 cursor-not-allowed'
                                  : isDuplex
                                  ? 'border-blue-200 dark:border-blue-600 hover:bg-blue-50 dark:hover:bg-blue-900/20 text-blue-700 dark:text-blue-300'
                                  : 'border-gray-200 dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-700 dark:hover:bg-gray-700 dark:text-gray-200'
                              }`}
                              disabled={isLocked}
                              title={isLocked ? 'Set from property details' :
                                     isDuplex ? 'Adjust to match property total' : undefined}
                            >
                              {unit.bathrooms || 0}
                            </button>
                          )}
                        </div>
                      );
                    })()}

                    {/* Size */}
                    <div className="bg-white dark:bg-gray-800 rounded-lg p-3 border border-gray-200 dark:border-gray-600 hover:border-blue-300 dark:hover:border-blue-400 transition-colors group">
                      <div className="flex items-center justify-between mb-1.5">
                        <span className="text-xs font-medium text-gray-600 dark:text-gray-400 group-hover:text-gray-900 dark:group-hover:text-gray-100 transition-colors">
                          <Square className="h-3.5 w-3.5 inline mr-1 text-blue-500 dark:text-blue-400" />
                          Size
                        </span>
                        {unit.size && !editing || editing?.unitIndex !== index || editing?.field !== 'size' ? (
                          <span className="text-xs text-blue-600 dark:text-blue-400 font-semibold transition-colors duration-300">
                            {unit.size} sq ft
                          </span>
                        ) : null}
                      </div>
                      {editing?.unitIndex === index && editing?.field === 'size' ? (
                        <div className="flex items-center gap-1">
                          <input
                            type="number"
                            min="0"
                            value={tempValue}
                            onChange={(e) => setTempValue(e.target.value)}
                            onKeyDown={(e) => {
                              if (e.key === 'Enter') saveEdit();
                              if (e.key === 'Escape') cancelEdit();
                            }}
                            className="w-full px-2 py-1 text-sm font-medium border border-blue-300 dark:border-blue-500 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 transition-colors duration-300"
                            placeholder="sq ft"
                            autoFocus
                          />
                          <button
                            type="button"
                            onClick={saveEdit}
                            className="p-1 text-green-600 dark:text-green-400 hover:text-green-700 dark:hover:text-green-500 hover:bg-green-50 dark:hover:bg-green-900/20 rounded transition-colors"
                          >
                            <Check className="h-3.5 w-3.5" />
                          </button>
                        </div>
                      ) : (
                        <button
                          type="button"
                          onClick={() => startEditing(index, 'size', unit.size)}
                          className="w-full text-left px-2.5 py-1.5 text-sm font-medium border border-gray-200 dark:border-gray-600 rounded-md hover:bg-gray-50 dark:hover:bg-gray-700 transition-all bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100"
                        >
                          {unit.size || '+ Add'}
                        </button>
                      )}
                    </div>

                    {/* Rent */}
                    <div className="bg-white dark:bg-gray-800 rounded-lg p-3 border border-gray-200 dark:border-gray-600 hover:border-green-300 dark:hover:border-green-400 transition-colors group">
                      <div className="flex items-center justify-between mb-1.5">
                        <span className="text-xs font-medium text-gray-600 dark:text-gray-400 group-hover:text-gray-900 dark:group-hover:text-gray-100 transition-colors">
                          <DollarSign className="h-3.5 w-3.5 inline mr-1 text-green-500 dark:text-green-400" />
                          Rent
                        </span>
                        {unit.monthly_rent && !editing || editing?.unitIndex !== index || editing?.field !== 'rent' ? (
                          <span className="text-xs text-green-600 dark:text-green-400 font-semibold transition-colors duration-300">
                            ${unit.monthly_rent}/mo
                          </span>
                        ) : null}
                      </div>
                      {editing?.unitIndex === index && editing?.field === 'rent' ? (
                        <div className="flex items-center gap-1">
                          <input
                            type="number"
                            min="0"
                            value={tempValue}
                            onChange={(e) => setTempValue(e.target.value)}
                            onKeyDown={(e) => {
                              if (e.key === 'Enter') saveEdit();
                              if (e.key === 'Escape') cancelEdit();
                            }}
                            className="w-full px-2 py-1 text-sm font-medium border border-green-300 dark:border-green-500 rounded-md focus:ring-2 focus:ring-green-500 focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 transition-colors duration-300"
                            placeholder="0"
                            autoFocus
                          />
                          <button
                            type="button"
                            onClick={saveEdit}
                            className="p-1 text-green-600 dark:text-green-400 hover:text-green-700 dark:hover:text-green-500 hover:bg-green-50 dark:hover:bg-green-900/20 rounded transition-colors"
                          >
                            <Check className="h-3.5 w-3.5" />
                          </button>
                        </div>
                      ) : (
                        <button
                          type="button"
                          onClick={() => startEditing(index, 'rent', unit.monthly_rent)}
                          className="w-full text-left px-2.5 py-1.5 text-sm font-medium border border-gray-200 dark:border-gray-600 rounded-md hover:bg-gray-50 dark:hover:bg-gray-700 transition-all bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100"
                        >
                          {unit.monthly_rent ? `$${unit.monthly_rent}` : '+ Add'}
                        </button>
                      )}
                    </div>
                  </div>
                </div>
              </motion.div>
            ))}
          </AnimatePresence>

          {/* Add ADU Button - Only for single family homes without ADU */}
          {config.canAddADU && !hasADU && (
            <motion.button
              type="button"
              onClick={addADU}
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="w-full group relative overflow-hidden rounded-xl border-2 border-dashed border-gray-300 dark:border-gray-600 bg-gradient-to-br from-gray-50 to-gray-100/50 dark:from-gray-900/20 dark:to-gray-800/20 p-4 hover:border-blue-400 dark:hover:border-blue-500 hover:from-blue-50 hover:to-indigo-50/50 dark:hover:from-blue-900/20 dark:hover:to-indigo-900/20 transition-all duration-300"
            >
              <div className="flex items-center justify-center gap-2">
                <Key className="h-5 w-5 text-gray-400 dark:text-gray-500 group-hover:text-blue-600 dark:group-hover:text-blue-400 transition-colors" />
                <span className="text-sm font-medium text-gray-600 dark:text-gray-300 group-hover:text-blue-600 dark:group-hover:text-blue-400 transition-colors">
                  Add Accessory Dwelling Unit (ADU)
                </span>
              </div>
              <div className="absolute inset-0 bg-gradient-to-r from-blue-600/0 via-blue-600/5 to-blue-600/0 transform translate-x-[-100%] group-hover:translate-x-[100%] transition-transform duration-1000"></div>
            </motion.button>
          )}
        </div>
      </div>

      {/* Footer Info */}
      <div className="mt-6 space-y-3">
        {/* Rent Summary - Only show if rent is entered */}
        {getTotalMonthlyRent() > 0 && (
          <div className="bg-gradient-to-br from-green-50 to-emerald-50/50 dark:from-green-900/20 dark:to-emerald-900/20 rounded-xl p-4 border border-green-200 dark:border-green-700">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Sparkles className="h-4 w-4 text-green-600" />
                <span className="text-sm font-medium text-green-900 dark:text-green-100">
                  Potential Monthly Income
                </span>
              </div>
              <span className="text-lg font-bold text-green-700 dark:text-green-300">
                ${getTotalMonthlyRent().toLocaleString()}/mo
              </span>
            </div>
          </div>
        )}

        {/* Info Box - Matching ResidentialForm Style */}
        <div className="bg-blue-50 dark:bg-blue-900/20 rounded-xl p-3.5 border border-blue-200 dark:border-blue-700 transition-colors duration-300">
          <div className="flex items-start gap-2">
            <Info className="h-4 w-4 text-blue-600 dark:text-blue-400 mt-0.5 flex-shrink-0" />
            <div>
              <p className="text-xs font-semibold text-blue-900 dark:text-blue-100 mb-1 transition-colors duration-300">Quick Setup Only</p>
              <p className="text-xs text-blue-700 dark:text-blue-300 leading-relaxed transition-colors duration-300">
                {isDuplex 
                  ? "Bedroom and bathroom counts must match the property total. Adjusting one unit automatically updates the other."
                  : "This is just the initial configuration. You'll be able to fully customize units, add detailed information, and manage tenants after creating the property."
                }
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default React.memo(ResidentialUnits);