import React, { useState, useEffect } from 'react';
import { useFormContext } from 'react-hook-form';
import { PropertyFormData, GeneratedUnit } from '@/types/property';
import { 
  Square, DollarSign, TrendingUp, Plus, 
  Minus, Check, X, Info, Layers
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

interface CommercialUnitsProps {
  onNext?: () => void;
}

interface EditingState {
  unitIndex: number;
  field: 'name' | 'rent' | 'size';
}

const CommercialUnits: React.FC<CommercialUnitsProps> = () => {
  const { watch, setValue, getValues } = useFormContext<PropertyFormData>();
  const typeSpecificDetails = watch('type_specific_details');
  
  // Get data from CommercialForm
  const spaceType = typeSpecificDetails?.space_type || 'retail';
  const usableSquareFeet = Number(typeSpecificDetails?.usable_square_feet) || 0;
  const rentableSquareFeet = Number(typeSpecificDetails?.rentable_square_feet) || 0;
  const leaseType = typeSpecificDetails?.lease_type || 'gross';
  const floorCount = Number(typeSpecificDetails?.floor_count) || 1;
  const permittedUses = typeSpecificDetails?.permitted_uses || [];
  
  const [units, setUnits] = useState<GeneratedUnit[]>([]);
  const [editing, setEditing] = useState<EditingState | null>(null);
  const [tempValue, setTempValue] = useState<string>('');
  const [autoSplit, setAutoSplit] = useState(false);
  const [numberOfSpaces, setNumberOfSpaces] = useState(1);
  
  // Space type configurations
  const spaceTypeConfig = {
    retail: { 
      emoji: '🛍️', 
      label: 'Retail', 
      color: 'green',
      defaultRentPerSF: 25,
      typicalSizes: [1000, 1500, 2000, 3000, 5000]
    },
    office: { 
      emoji: '🏢', 
      label: 'Office', 
      color: 'blue',
      defaultRentPerSF: 22,
      typicalSizes: [500, 1000, 1500, 2500, 5000]
    },
    medical: { 
      emoji: '🏥', 
      label: 'Medical', 
      color: 'red',
      defaultRentPerSF: 30,
      typicalSizes: [800, 1200, 2000, 3000, 4000]
    },
    restaurant: { 
      emoji: '🍽️', 
      label: 'Restaurant', 
      color: 'amber',
      defaultRentPerSF: 35,
      typicalSizes: [1500, 2500, 3500, 5000, 7500]
    },
    hotel_motel: { 
      emoji: '🏨', 
      label: 'Hotel/Motel', 
      color: 'purple',
      defaultRentPerSF: 0, // Hotels typically don't rent by SF
      typicalSizes: [400, 500, 600, 800, 1000] // Per room
    },
    mixed: { 
      emoji: '🏬', 
      label: 'Mixed/Multi-Tenant', 
      color: 'indigo',
      defaultRentPerSF: 20,
      typicalSizes: [800, 1200, 1800, 2500, 4000]
    }
  };
  
  const currentSpaceType = spaceTypeConfig[spaceType as keyof typeof spaceTypeConfig] || spaceTypeConfig.retail;
  
  // Lease type descriptions
  const leaseTypeLabels = {
    gross: 'Gross Lease',
    triple_net: 'Triple Net (NNN)',
    modified_gross: 'Modified Gross',
    percentage: 'Percentage Lease',
    other: 'Custom Structure'
  };
  
  // Initialize units
  useEffect(() => {
    const existingUnits = getValues('generated_units');
    
    if (existingUnits && existingUnits.length > 0) {
      setUnits(existingUnits);
      setNumberOfSpaces(existingUnits.length);
    } else {
      // Generate initial unit based on space type
      generateUnits(1);
    }
  }, [spaceType, usableSquareFeet]);
  
  const generateUnits = (count: number) => {
    const newUnits: GeneratedUnit[] = [];
    const baseSize = Math.floor(usableSquareFeet / count);
    
    for (let i = 0; i < count; i++) {
      const floorNumber = Math.min(i + 1, floorCount);
      const unitName = count === 1 
        ? `${currentSpaceType.label} Space`
        : `Suite ${String.fromCharCode(65 + i)}`;
      
      newUnits.push({
        name: unitName,
        size: baseSize,
        monthly_rent: Math.round(baseSize * currentSpaceType.defaultRentPerSF / 12),
        floor: floorNumber,
        unit_type: spaceType,
        description: `${currentSpaceType.label} space on floor ${floorNumber}`
      });
    }
    
    setUnits(newUnits);
    setNumberOfSpaces(count);
  };
  
  // Save units to form when they change
  useEffect(() => {
    setValue('generated_units', units);
  }, [units, setValue]);
  
  
  const addUnit = () => {
    const newUnit: GeneratedUnit = {
      name: `Suite ${String.fromCharCode(65 + units.length)}`,
      size: Math.floor(usableSquareFeet / (units.length + 1)),
      monthly_rent: Math.round((usableSquareFeet / (units.length + 1)) * currentSpaceType.defaultRentPerSF / 12),
      floor: 1,
      unit_type: spaceType,
      description: `${currentSpaceType.label} space`
    };
    setUnits([...units, newUnit]);
  };
  
  const removeUnit = (index: number) => {
    setUnits(units.filter((_, i) => i !== index));
  };
  
  const startEditing = (unitIndex: number, field: EditingState['field'], currentValue: any) => {
    setEditing({ unitIndex, field });
    setTempValue(currentValue?.toString() || '');
  };
  
  const saveEdit = () => {
    if (editing) {
      const newUnits = [...units];
      const unit = newUnits[editing.unitIndex];
      
      if (editing.field === 'name') {
        unit.name = tempValue;
      } else if (editing.field === 'rent') {
        unit.monthly_rent = parseFloat(tempValue) || 0;
      } else if (editing.field === 'size') {
        unit.size = parseFloat(tempValue) || 0;
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
  
  const getTotalSize = () => {
    return units.reduce((sum, unit) => sum + (unit.size || 0), 0);
  };
  
  const getAverageRentPerSF = () => {
    const totalRent = getTotalMonthlyRent() * 12; // Annual rent
    const totalSize = getTotalSize();
    return totalSize > 0 ? totalRent / totalSize : 0;
  };
  
  const getLoadFactor = () => {
    return usableSquareFeet > 0 && rentableSquareFeet > 0 
      ? ((rentableSquareFeet - usableSquareFeet) / usableSquareFeet) * 100
      : 0;
  };
  
  return (
    <div className="h-full flex flex-col">
      {/* Header with space type */}
      <div className="mb-6">
        <div className="flex items-center gap-3 mb-2">
          <span className="text-2xl">{currentSpaceType.emoji}</span>
          <div>
            <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-100">
              {currentSpaceType.label} Space Configuration
            </h2>
            <p className="text-sm text-gray-600 dark:text-gray-300">
              {usableSquareFeet.toLocaleString()} SF usable • 
              {rentableSquareFeet > 0 && ` ${rentableSquareFeet.toLocaleString()} SF rentable • `}
              {leaseTypeLabels[leaseType as keyof typeof leaseTypeLabels]}
            </p>
          </div>
        </div>
      </div>
      
      {/* Quick Split Options */}
      <div className={(() => {
        const color = currentSpaceType.color;
        if (color === 'green') return 'bg-gradient-to-br from-green-50 to-green-100/50 dark:from-green-900/20 dark:to-green-800/20 rounded-xl p-4 border border-green-200 dark:border-green-700 mb-4';
        if (color === 'blue') return 'bg-gradient-to-br from-blue-50 to-blue-100/50 dark:from-blue-900/20 dark:to-blue-800/20 rounded-xl p-4 border border-blue-200 dark:border-blue-700 mb-4';
        if (color === 'red') return 'bg-gradient-to-br from-red-50 to-red-100/50 dark:from-red-900/20 dark:to-red-800/20 rounded-xl p-4 border border-red-200 dark:border-red-700 mb-4';
        if (color === 'amber') return 'bg-gradient-to-br from-amber-50 to-amber-100/50 dark:from-amber-900/20 dark:to-amber-800/20 rounded-xl p-4 border border-amber-200 dark:border-amber-700 mb-4';
        if (color === 'purple') return 'bg-gradient-to-br from-purple-50 to-purple-100/50 dark:from-purple-900/20 dark:to-purple-800/20 rounded-xl p-4 border border-purple-200 dark:border-purple-700 mb-4';
        if (color === 'indigo') return 'bg-gradient-to-br from-indigo-50 to-indigo-100/50 dark:from-indigo-900/20 dark:to-indigo-800/20 rounded-xl p-4 border border-indigo-200 dark:border-indigo-700 mb-4';
        return 'bg-gradient-to-br from-gray-50 to-gray-100/50 dark:from-gray-900/20 dark:to-gray-800/20 rounded-xl p-4 border border-gray-200 dark:border-gray-700 mb-4';
      })()}>
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-sm font-semibold text-gray-900 dark:text-gray-100 flex items-center">
            <Layers className="h-4 w-4 mr-1.5 text-indigo-600" />
            Space Division Options
          </h3>
        </div>
        
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={() => generateUnits(1)}
            className={`px-3 py-2 rounded-lg text-sm font-medium transition-all ${
              units.length === 1 && !autoSplit
                ? 'bg-gradient-to-r from-green-500 to-emerald-500 text-white shadow-md'
                : 'bg-white dark:bg-gray-700 text-gray-700 dark:text-gray-200 border border-gray-200 dark:border-gray-600 hover:border-gray-300 dark:hover:border-gray-500'
            }`}
          >
            Single Tenant
          </button>
          
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => setAutoSplit(true)}
              className={`px-3 py-2 rounded-lg text-sm font-medium transition-all ${
                autoSplit
                  ? 'bg-gradient-to-r from-blue-500 to-indigo-500 text-white shadow-md'
                  : 'bg-white dark:bg-gray-700 text-gray-700 dark:text-gray-200 border border-gray-200 dark:border-gray-600 hover:border-gray-300 dark:hover:border-gray-500'
              }`}
            >
              Multi-Tenant
            </button>
            
            {autoSplit && (
              <div className="flex items-center gap-1 bg-white dark:bg-gray-700 rounded-lg px-2 py-1 border border-gray-200 dark:border-gray-600">
                <button
                  type="button"
                  onClick={() => {
                    const newCount = Math.max(2, numberOfSpaces - 1);
                    setNumberOfSpaces(newCount);
                    generateUnits(newCount);
                  }}
                  className="p-1 text-gray-500 hover:text-blue-600 transition-colors"
                >
                  <Minus className="h-3 w-3" />
                </button>
                <span className="px-2 text-sm font-medium text-gray-700 dark:text-gray-200 min-w-[30px] text-center">
                  {numberOfSpaces}
                </span>
                <button
                  type="button"
                  onClick={() => {
                    const newCount = Math.min(10, numberOfSpaces + 1);
                    setNumberOfSpaces(newCount);
                    generateUnits(newCount);
                  }}
                  className="p-1 text-gray-500 hover:text-blue-600 transition-colors"
                >
                  <Plus className="h-3 w-3" />
                </button>
              </div>
            )}
          </div>
          
          {/* Quick size presets */}
          <div className="ml-auto flex items-center gap-2">
            <span className="text-xs text-gray-600 dark:text-gray-400">Quick sizes:</span>
            {currentSpaceType.typicalSizes.slice(0, 3).map(size => (
              <button
                key={size}
                type="button"
                onClick={() => {
                  if (units.length === 1) {
                    const newUnits = [...units];
                    newUnits[0].size = size;
                    newUnits[0].monthly_rent = Math.round(size * currentSpaceType.defaultRentPerSF / 12);
                    setUnits(newUnits);
                  }
                }}
                className="px-2 py-1 text-xs bg-white dark:bg-gray-700 border border-gray-200 dark:border-gray-600 rounded hover:border-blue-300 dark:hover:border-blue-600 transition-colors dark:text-gray-200"
              >
                {size.toLocaleString()} SF
              </button>
            ))}
          </div>
        </div>
      </div>
      
      {/* Units/Spaces List */}
      <div className="flex-1 overflow-y-auto">
        <div className="space-y-3">
          <AnimatePresence>
            {units.map((unit, index) => (
              <motion.div
                key={`${unit.name}-${index}`}
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: 20 }}
                transition={{ delay: index * 0.05 }}
                className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-4 hover:shadow-md transition-shadow"
              >
                {/* Unit Header */}
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-2">
                    {editing?.unitIndex === index && editing?.field === 'name' ? (
                      <div className="flex items-center gap-1">
                        <input
                          type="text"
                          value={tempValue}
                          onChange={(e) => setTempValue(e.target.value)}
                          onKeyDown={(e) => {
                            if (e.key === 'Enter') saveEdit();
                            if (e.key === 'Escape') cancelEdit();
                          }}
                          className="px-2 py-1 text-sm font-semibold border border-blue-300 dark:border-blue-600 rounded-md focus:ring-2 focus:ring-blue-500 dark:focus:ring-blue-400 focus:border-transparent dark:bg-gray-700 dark:text-gray-100"
                          autoFocus
                        />
                        <button
                          type="button"
                          onClick={saveEdit}
                          className="p-1 text-green-600 hover:text-green-700"
                        >
                          <Check className="h-4 w-4" />
                        </button>
                        <button
                          type="button"
                          onClick={cancelEdit}
                          className="p-1 text-red-600 hover:text-red-700"
                        >
                          <X className="h-4 w-4" />
                        </button>
                      </div>
                    ) : (
                      <h3 
                        className="font-semibold text-gray-900 dark:text-gray-100 cursor-pointer hover:text-blue-600 dark:hover:text-blue-400 transition-colors"
                        onClick={() => startEditing(index, 'name', unit.name)}
                      >
                        {unit.name}
                      </h3>
                    )}
                    
                    {unit.floor && floorCount > 1 && (
                      <span className="px-2 py-0.5 text-xs font-medium text-gray-600 bg-gray-100 rounded-full">
                        Floor {unit.floor}
                      </span>
                    )}
                  </div>
                  
                  {units.length > 1 && (
                    <button
                      type="button"
                      onClick={() => removeUnit(index)}
                      className="p-1.5 text-gray-400 hover:text-red-500 hover:bg-red-50 rounded-lg transition-all"
                    >
                      <X className="h-4 w-4" />
                    </button>
                  )}
                </div>
                
                {/* Unit Details Grid */}
                <div className="grid grid-cols-3 gap-3">
                  {/* Size */}
                  <div className="bg-gradient-to-br from-blue-50 to-indigo-50/50 dark:from-blue-900/20 dark:to-indigo-900/20 rounded-lg p-3 border border-blue-200 dark:border-blue-700">
                    <div className="flex items-center justify-between mb-1.5">
                      <span className="text-xs font-medium text-gray-600 dark:text-gray-300">
                        <Square className="h-3.5 w-3.5 inline mr-1 text-blue-500" />
                        Size
                      </span>
                    </div>
                    {editing?.unitIndex === index && editing?.field === 'size' ? (
                      <div className="flex items-center gap-1">
                        <input
                          type="number"
                          value={tempValue}
                          onChange={(e) => setTempValue(e.target.value)}
                          onKeyDown={(e) => {
                            if (e.key === 'Enter') saveEdit();
                            if (e.key === 'Escape') cancelEdit();
                          }}
                          className="w-full px-2 py-1 text-sm font-medium border border-blue-300 dark:border-blue-600 rounded-md focus:ring-2 focus:ring-blue-500 dark:focus:ring-blue-400 focus:border-transparent dark:bg-gray-700 dark:text-gray-100"
                          autoFocus
                        />
                        <button
                          type="button"
                          onClick={saveEdit}
                          className="p-1 text-green-600 hover:text-green-700"
                        >
                          <Check className="h-3.5 w-3.5" />
                        </button>
                      </div>
                    ) : (
                      <button
                        type="button"
                        onClick={() => startEditing(index, 'size', unit.size)}
                        className="w-full text-left"
                      >
                        <span className="text-lg font-bold text-blue-700 dark:text-blue-300">
                          {unit.size?.toLocaleString() || 0} SF
                        </span>
                      </button>
                    )}
                  </div>
                  
                  {/* Monthly Rent */}
                  <div className="bg-gradient-to-br from-green-50 to-emerald-50/50 dark:from-green-900/20 dark:to-emerald-900/20 rounded-lg p-3 border border-green-200 dark:border-green-700">
                    <div className="flex items-center justify-between mb-1.5">
                      <span className="text-xs font-medium text-gray-600 dark:text-gray-300">
                        <DollarSign className="h-3.5 w-3.5 inline mr-1 text-green-500" />
                        Monthly Rent
                      </span>
                    </div>
                    {editing?.unitIndex === index && editing?.field === 'rent' ? (
                      <div className="flex items-center gap-1">
                        <input
                          type="number"
                          value={tempValue}
                          onChange={(e) => setTempValue(e.target.value)}
                          onKeyDown={(e) => {
                            if (e.key === 'Enter') saveEdit();
                            if (e.key === 'Escape') cancelEdit();
                          }}
                          className="w-full px-2 py-1 text-sm font-medium border border-green-300 dark:border-green-600 rounded-md focus:ring-2 focus:ring-green-500 dark:focus:ring-green-400 focus:border-transparent dark:bg-gray-700 dark:text-gray-100"
                          autoFocus
                        />
                        <button
                          type="button"
                          onClick={saveEdit}
                          className="p-1 text-green-600 hover:text-green-700"
                        >
                          <Check className="h-3.5 w-3.5" />
                        </button>
                      </div>
                    ) : (
                      <button
                        type="button"
                        onClick={() => startEditing(index, 'rent', unit.monthly_rent)}
                        className="w-full text-left"
                      >
                        <span className="text-lg font-bold text-green-700 dark:text-green-300">
                          ${unit.monthly_rent?.toLocaleString() || 0}
                        </span>
                      </button>
                    )}
                  </div>
                  
                  {/* Rent per SF */}
                  <div className="bg-gradient-to-br from-purple-50 to-indigo-50/50 dark:from-purple-900/20 dark:to-indigo-900/20 rounded-lg p-3 border border-purple-200 dark:border-purple-700">
                    <div className="flex items-center justify-between mb-1.5">
                      <span className="text-xs font-medium text-gray-600 dark:text-gray-300">
                        <TrendingUp className="h-3.5 w-3.5 inline mr-1 text-purple-500" />
                        $/SF/Year
                      </span>
                    </div>
                    <span className="text-lg font-bold text-purple-700 dark:text-purple-300">
                      ${unit.size && unit.monthly_rent 
                        ? ((unit.monthly_rent * 12) / unit.size).toFixed(2)
                        : '0.00'}
                    </span>
                  </div>
                </div>
                
                {/* Permitted Uses (if applicable) */}
                {permittedUses.length > 0 && index === 0 && (
                  <div className="mt-3 pt-3 border-t border-gray-100 dark:border-gray-700">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="text-xs font-medium text-gray-600 dark:text-gray-300">Permitted:</span>
                      {permittedUses.slice(0, 4).map((use: string) => (
                        <span key={use} className="px-2 py-0.5 text-xs font-medium text-indigo-700 bg-indigo-100 rounded-full">
                          {use.replace(/_/g, ' ')}
                        </span>
                      ))}
                      {permittedUses.length > 4 && (
                        <span className="text-xs text-gray-500">+{permittedUses.length - 4} more</span>
                      )}
                    </div>
                  </div>
                )}
              </motion.div>
            ))}
          </AnimatePresence>
          
          {/* Add Unit Button */}
          {units.length < 10 && (
            <button
              type="button"
              onClick={addUnit}
              className="w-full p-3 border-2 border-dashed border-gray-300 dark:border-gray-600 rounded-xl hover:border-blue-400 dark:hover:border-blue-500 hover:bg-blue-50 dark:hover:bg-blue-900/20 transition-all group"
            >
              <div className="flex items-center justify-center gap-2">
                <Plus className="h-4 w-4 text-gray-400 group-hover:text-blue-600 dark:group-hover:text-blue-400" />
                <span className="text-sm font-medium text-gray-600 dark:text-gray-300 group-hover:text-blue-600 dark:group-hover:text-blue-400">
                  Add Another Space
                </span>
              </div>
            </button>
          )}
        </div>
      </div>
      
      {/* Footer Summary */}
      <div className="mt-6 space-y-3">
        {/* Financial Summary */}
        {getTotalMonthlyRent() > 0 && (
          <div className="bg-gradient-to-br from-green-50 to-emerald-50/50 dark:from-green-900/20 dark:to-emerald-900/20 rounded-xl p-4 border border-green-200 dark:border-green-700">
            <div className="grid grid-cols-3 gap-4">
              <div>
                <div className="flex items-center gap-1 mb-1">
                  <DollarSign className="h-3.5 w-3.5 text-green-600" />
                  <span className="text-xs font-medium text-green-900 dark:text-green-100">Monthly Revenue</span>
                </div>
                <div className="text-lg font-bold text-green-700 dark:text-green-300">
                  ${getTotalMonthlyRent().toLocaleString()}
                </div>
                <div className="text-xs text-green-600 dark:text-green-400">
                  ${(getTotalMonthlyRent() * 12).toLocaleString()}/year
                </div>
              </div>
              
              <div>
                <div className="flex items-center gap-1 mb-1">
                  <Square className="h-3.5 w-3.5 text-blue-600" />
                  <span className="text-xs font-medium text-blue-900 dark:text-blue-100">Total Leased</span>
                </div>
                <div className="text-lg font-bold text-blue-700 dark:text-blue-300">
                  {getTotalSize().toLocaleString()} SF
                </div>
                <div className="text-xs text-blue-600 dark:text-blue-400">
                  {usableSquareFeet > 0 ? Math.round((getTotalSize() / usableSquareFeet) * 100) : 0}% utilized
                </div>
              </div>
              
              <div>
                <div className="flex items-center gap-1 mb-1">
                  <TrendingUp className="h-3.5 w-3.5 text-purple-600" />
                  <span className="text-xs font-medium text-purple-900 dark:text-purple-100">Avg Rate</span>
                </div>
                <div className="text-lg font-bold text-purple-700 dark:text-purple-300">
                  ${getAverageRentPerSF().toFixed(2)}/SF
                </div>
                <div className="text-xs text-purple-600 dark:text-purple-400">
                  {getLoadFactor() > 0 && `${getLoadFactor().toFixed(1)}% load factor`}
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
              <p className="text-xs font-semibold text-blue-900 dark:text-blue-100 mb-1">Commercial Configuration</p>
              <p className="text-xs text-blue-700 dark:text-blue-300 leading-relaxed">
                Configure your {currentSpaceType.label.toLowerCase()} space as single or multi-tenant. 
                Set individual rents and sizes for each unit. 
                {leaseType === 'triple_net' && ' Tenants will be responsible for property expenses under NNN lease.'}
                {leaseType === 'percentage' && ' Consider setting base rent lower as you\'ll collect percentage of sales.'}
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default React.memo(CommercialUnits);