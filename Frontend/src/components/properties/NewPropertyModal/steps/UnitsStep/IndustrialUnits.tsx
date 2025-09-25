import React, { useState, useEffect } from 'react';
import { useFormContext } from 'react-hook-form';
import { PropertyFormData, GeneratedUnit } from '@/types/property';
import { 
  Factory, Warehouse, Square, DollarSign,
  TrendingUp, Truck, Building, Gauge,
  Info, Shield, Package, Zap, Train, Plus, X, Check
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

interface IndustrialUnitsProps {
  onNext?: () => void;
}

interface EditingState {
  unitIndex: number;
  field: 'name' | 'rent' | 'size' | 'type';
}

const IndustrialUnits: React.FC<IndustrialUnitsProps> = () => {
  const { watch, setValue, getValues } = useFormContext<PropertyFormData>();
  const typeSpecificDetails = watch('type_specific_details');
  
  // Get data from IndustrialForm
  const industrialType = typeSpecificDetails?.industrial_type || 'warehouse';
  const totalSquareFeet = Number(typeSpecificDetails?.total_square_feet) || 0;
  const warehouseSquareFeet = Number(typeSpecificDetails?.warehouse_square_feet) || 0;
  const officeSquareFeet = Number(typeSpecificDetails?.office_square_feet) || 0;
  const manufacturingSquareFeet = Number(typeSpecificDetails?.manufacturing_square_feet) || 0;
  const clearHeight = Number(typeSpecificDetails?.clear_height) || 0;
  const loadingDocksCount = Number(typeSpecificDetails?.loading_docks_count) || 0;
  const driveInDoorsCount = Number(typeSpecificDetails?.drive_in_doors_count) || 0;
  const railAccess = typeSpecificDetails?.rail_access || false;
  
  const [units, setUnits] = useState<GeneratedUnit[]>([]);
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
    orange: {
      gradient: 'bg-gradient-to-br from-orange-50 to-orange-100/50',
      border: 'border-orange-200'
    },
    purple: {
      gradient: 'bg-gradient-to-br from-purple-50 to-purple-100/50',
      border: 'border-purple-200'
    },
    cyan: {
      gradient: 'bg-gradient-to-br from-cyan-50 to-cyan-100/50',
      border: 'border-cyan-200'
    }
  };

  // Industrial type configurations
  const industrialTypeConfig = {
    warehouse: { 
      emoji: '📦', 
      label: 'Warehouse', 
      color: 'blue' as keyof typeof colorClassMap,
      defaultRentPerSF: 8,
      typicalSizes: [5000, 10000, 25000, 50000, 100000],
      spaceTypes: ['warehouse', 'storage', 'distribution']
    },
    distribution: { 
      emoji: '🚚', 
      label: 'Distribution', 
      color: 'green' as keyof typeof colorClassMap,
      defaultRentPerSF: 9,
      typicalSizes: [10000, 25000, 50000, 75000, 150000],
      spaceTypes: ['distribution', 'cross-dock', 'fulfillment']
    },
    manufacturing: { 
      emoji: '🏭', 
      label: 'Manufacturing', 
      color: 'orange' as keyof typeof colorClassMap,
      defaultRentPerSF: 10,
      typicalSizes: [5000, 15000, 30000, 50000, 100000],
      spaceTypes: ['production', 'assembly', 'fabrication']
    },
    flex: { 
      emoji: '🔄', 
      label: 'Flex Space', 
      color: 'purple' as keyof typeof colorClassMap,
      defaultRentPerSF: 12,
      typicalSizes: [2500, 5000, 10000, 20000, 40000],
      spaceTypes: ['flex', 'mixed-use', 'showroom']
    },
    cold_storage: { 
      emoji: '❄️', 
      label: 'Cold Storage', 
      color: 'cyan' as keyof typeof colorClassMap,
      defaultRentPerSF: 15,
      typicalSizes: [5000, 10000, 20000, 40000, 80000],
      spaceTypes: ['freezer', 'cooler', 'refrigerated']
    },
    data_center: { 
      emoji: '🖥️', 
      label: 'Data Center', 
      color: 'indigo',
      defaultRentPerSF: 25,
      typicalSizes: [1000, 2500, 5000, 10000, 20000],
      spaceTypes: ['colocation', 'server-room', 'tech-space']
    },
    light_industrial: { 
      emoji: '💡', 
      label: 'Light Industrial', 
      color: 'amber',
      defaultRentPerSF: 11,
      typicalSizes: [3000, 7500, 15000, 30000, 60000],
      spaceTypes: ['light-manufacturing', 'assembly', 'workshop']
    },
    rd_tech: { 
      emoji: '🔬', 
      label: 'R&D/Tech', 
      color: 'pink',
      defaultRentPerSF: 18,
      typicalSizes: [2000, 5000, 10000, 20000, 40000],
      spaceTypes: ['laboratory', 'research', 'tech-development']
    }
  };
  
  const currentIndustrialType = industrialTypeConfig[industrialType as keyof typeof industrialTypeConfig] || industrialTypeConfig.warehouse;
  
  // Initialize units based on space breakdown
  useEffect(() => {
    const existingUnits = getValues('generated_units');
    
    if (existingUnits && existingUnits.length > 0) {
      setUnits(existingUnits);
    } else {
      generateUnitsFromSpaceBreakdown();
    }
  }, [industrialType, totalSquareFeet]);
  
  const generateUnitsFromSpaceBreakdown = () => {
    const newUnits: GeneratedUnit[] = [];
    
    // Main warehouse/industrial space
    if (warehouseSquareFeet > 0 || (totalSquareFeet > 0 && !officeSquareFeet && !manufacturingSquareFeet)) {
      const mainSize = warehouseSquareFeet || totalSquareFeet;
      newUnits.push({
        name: `${currentIndustrialType.label} Space`,
        size: mainSize,
        monthly_rent: Math.round(mainSize * currentIndustrialType.defaultRentPerSF / 12),
        unit_type: 'warehouse',
        description: `Main ${currentIndustrialType.label.toLowerCase()} facility`,
        floor: 1
      });
    }
    
    // Office space if specified
    if (officeSquareFeet > 0) {
      newUnits.push({
        name: 'Office Space',
        size: officeSquareFeet,
        monthly_rent: Math.round(officeSquareFeet * 15 / 12), // Higher rate for office
        unit_type: 'office',
        description: 'Administrative office area',
        floor: 1
      });
    }
    
    // Manufacturing space if specified
    if (manufacturingSquareFeet > 0) {
      newUnits.push({
        name: 'Manufacturing Area',
        size: manufacturingSquareFeet,
        monthly_rent: Math.round(manufacturingSquareFeet * currentIndustrialType.defaultRentPerSF / 12),
        unit_type: 'manufacturing',
        description: 'Production/manufacturing floor',
        floor: 1
      });
    }
    
    // If no breakdown provided, create single unit
    if (newUnits.length === 0 && totalSquareFeet > 0) {
      newUnits.push({
        name: `${currentIndustrialType.label} Facility`,
        size: totalSquareFeet,
        monthly_rent: Math.round(totalSquareFeet * currentIndustrialType.defaultRentPerSF / 12),
        unit_type: industrialType,
        description: `Complete ${currentIndustrialType.label.toLowerCase()} facility`,
        floor: 1
      });
    }
    
    setUnits(newUnits);
  };
  
  // Save units to form when they change
  useEffect(() => {
    setValue('generated_units', units);
  }, [units, setValue]);
  
  const addUnit = () => {
    const remainingSpace = totalSquareFeet - units.reduce((sum, u) => sum + (u.size || 0), 0);
    const newUnit: GeneratedUnit = {
      name: `Additional Space ${units.length + 1}`,
      size: Math.min(10000, remainingSpace),
      monthly_rent: Math.round(Math.min(10000, remainingSpace) * currentIndustrialType.defaultRentPerSF / 12),
      unit_type: industrialType,
      description: `Additional ${currentIndustrialType.label.toLowerCase()} space`,
      floor: 1
    };
    setUnits([...units, newUnit]);
  };
  
  const removeUnit = (index: number) => {
    if (units.length > 1) {
      setUnits(units.filter((_, i) => i !== index));
    }
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
      } else if (editing.field === 'type') {
        unit.unit_type = tempValue;
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
    const totalRent = getTotalMonthlyRent() * 12;
    const totalSize = getTotalSize();
    return totalSize > 0 ? totalRent / totalSize : 0;
  };
  
  const getSpaceUtilization = () => {
    return totalSquareFeet > 0 ? (getTotalSize() / totalSquareFeet) * 100 : 0;
  };
  
  // Get unit type icon
  const getUnitTypeIcon = (type: string) => {
    switch(type) {
      case 'warehouse': return <Warehouse className="h-3.5 w-3.5 text-blue-500" />;
      case 'office': return <Building className="h-3.5 w-3.5 text-indigo-500" />;
      case 'manufacturing': return <Factory className="h-3.5 w-3.5 text-orange-500" />;
      case 'distribution': return <Truck className="h-3.5 w-3.5 text-green-500" />;
      default: return <Package className="h-3.5 w-3.5 text-gray-500" />;
    }
  };
  
  return (
    <div className="h-full flex flex-col">
      {/* Header with industrial type */}
      <div className="mb-6">
        <div className="flex items-center gap-3 mb-2">
          <span className="text-2xl">{currentIndustrialType.emoji}</span>
          <div>
            <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-100">
              {currentIndustrialType.label} Configuration
            </h2>
            <p className="text-sm text-gray-600 dark:text-gray-300">
              {totalSquareFeet.toLocaleString()} SF total • 
              {clearHeight > 0 && ` ${clearHeight}' clear height • `}
              {loadingDocksCount > 0 && ` ${loadingDocksCount} loading docks`}
              {railAccess && ' • Rail access'}
            </p>
          </div>
        </div>
      </div>
      
      {/* Facility Features Summary */}
      <div className={`rounded-xl p-4 mb-4 ${
        currentIndustrialType.color === 'blue' ? 'bg-gradient-to-br from-blue-50 to-blue-100/50 dark:from-blue-900/20 dark:to-blue-800/20 border-blue-200 dark:border-blue-700' :
        currentIndustrialType.color === 'green' ? 'bg-gradient-to-br from-green-50 to-green-100/50 dark:from-green-900/20 dark:to-green-800/20 border-green-200 dark:border-green-700' :
        currentIndustrialType.color === 'orange' ? 'bg-gradient-to-br from-orange-50 to-orange-100/50 dark:from-orange-900/20 dark:to-orange-800/20 border-orange-200 dark:border-orange-700' :
        currentIndustrialType.color === 'purple' ? 'bg-gradient-to-br from-purple-50 to-purple-100/50 dark:from-purple-900/20 dark:to-purple-800/20 border-purple-200 dark:border-purple-700' :
        currentIndustrialType.color === 'cyan' ? 'bg-gradient-to-br from-cyan-50 to-cyan-100/50 dark:from-cyan-900/20 dark:to-cyan-800/20 border-cyan-200 dark:border-cyan-700' :
        'bg-gradient-to-br from-gray-50 to-gray-100/50 dark:from-gray-900/20 dark:to-gray-800/20 border-gray-200 dark:border-gray-700'
      }`}>
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-sm font-semibold text-gray-900 dark:text-gray-100 flex items-center">
            <Shield className="h-4 w-4 mr-1.5 text-indigo-600" />
            Facility Features
          </h3>
        </div>
        
        <div className="grid grid-cols-4 gap-3">
          {clearHeight > 0 && (
            <div className="bg-white dark:bg-gray-700 rounded-lg p-2 border border-gray-200 dark:border-gray-600">
              <div className="flex items-center gap-1 mb-0.5">
                <Gauge className="h-3 w-3 text-blue-500" />
                <span className="text-[10px] font-medium text-gray-600 dark:text-gray-300">Clear Height</span>
              </div>
              <span className="text-sm font-bold text-gray-900 dark:text-gray-100">{clearHeight}'</span>
            </div>
          )}
          
          {loadingDocksCount > 0 && (
            <div className="bg-white dark:bg-gray-700 rounded-lg p-2 border border-gray-200 dark:border-gray-600">
              <div className="flex items-center gap-1 mb-0.5">
                <Truck className="h-3 w-3 text-green-500" />
                <span className="text-[10px] font-medium text-gray-600 dark:text-gray-300">Loading Docks</span>
              </div>
              <span className="text-sm font-bold text-gray-900 dark:text-gray-100">{loadingDocksCount}</span>
            </div>
          )}
          
          {driveInDoorsCount > 0 && (
            <div className="bg-white dark:bg-gray-700 rounded-lg p-2 border border-gray-200 dark:border-gray-600">
              <div className="flex items-center gap-1 mb-0.5">
                <Package className="h-3 w-3 text-amber-500" />
                <span className="text-[10px] font-medium text-gray-600 dark:text-gray-300">Drive-In Doors</span>
              </div>
              <span className="text-sm font-bold text-gray-900 dark:text-gray-100">{driveInDoorsCount}</span>
            </div>
          )}
          
          {railAccess && (
            <div className="bg-white dark:bg-gray-700 rounded-lg p-2 border border-gray-200 dark:border-gray-600">
              <div className="flex items-center gap-1 mb-0.5">
                <Train className="h-3 w-3 text-purple-500" />
                <span className="text-[10px] font-medium text-gray-600 dark:text-gray-300">Rail Access</span>
              </div>
              <span className="text-sm font-bold text-gray-900 dark:text-gray-100">Available</span>
            </div>
          )}
        </div>
        
        {/* Quick size presets */}
        <div className="mt-3 pt-3 border-t border-gray-200 dark:border-gray-600 flex items-center gap-2">
          <span className="text-xs text-gray-600 dark:text-gray-300">Quick sizes:</span>
          {currentIndustrialType.typicalSizes.slice(0, 4).map(size => (
            <button
              key={size}
              type="button"
              onClick={() => {
                const newUnits = [...units];
                if (units.length === 1) {
                  // Single unit: update the only unit
                  newUnits[0].size = size;
                  newUnits[0].monthly_rent = Math.round(size * currentIndustrialType.defaultRentPerSF / 12);
                } else {
                  // Multiple units: update all units to the same size
                  newUnits.forEach(unit => {
                    unit.size = size;
                    unit.monthly_rent = Math.round(size * currentIndustrialType.defaultRentPerSF / 12);
                  });
                }
                setUnits(newUnits);
              }}
              className="px-2 py-1 text-xs bg-white dark:bg-gray-700 border border-gray-200 dark:border-gray-600 rounded hover:border-blue-300 dark:hover:border-blue-600 transition-colors dark:text-gray-200"
            >
              {(size / 1000).toFixed(0)}K SF
            </button>
          ))}
        </div>
      </div>
      
      {/* Units/Spaces List */}
      <div className="flex-1 overflow-y-auto">
        <div className="space-y-3">
          <AnimatePresence>
            {units.map((unit, index) => (
              <motion.div
                key={`${unit.name}-${index}`}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -20 }}
                transition={{ delay: index * 0.05 }}
                className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-4 hover:shadow-lg transition-shadow"
              >
                {/* Unit Header */}
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-2">
                    {getUnitTypeIcon(unit.unit_type || '')}
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
                          className="px-2 py-1 text-sm font-semibold border border-blue-300 dark:border-blue-600 rounded-md focus:ring-2 focus:ring-blue-500 dark:focus:ring-blue-400 dark:bg-gray-700 dark:text-gray-100"
                          autoFocus
                        />
                        <button type="button" onClick={saveEdit} className="p-1 text-green-600">
                          <Check className="h-4 w-4" />
                        </button>
                        <button type="button" onClick={cancelEdit} className="p-1 text-red-600">
                          <X className="h-4 w-4" />
                        </button>
                      </div>
                    ) : (
                      <h3 
                        className="font-semibold text-gray-900 dark:text-gray-100 cursor-pointer hover:text-blue-600 dark:hover:text-blue-400"
                        onClick={() => startEditing(index, 'name', unit.name)}
                      >
                        {unit.name}
                      </h3>
                    )}
                    
                    {/* Space type badge */}
                    <span className={`px-2 py-0.5 text-xs font-medium rounded-full ${
                      unit.unit_type === 'warehouse' ? 'bg-blue-100 text-blue-700' :
                      unit.unit_type === 'office' ? 'bg-indigo-100 text-indigo-700' :
                      unit.unit_type === 'manufacturing' ? 'bg-orange-100 text-orange-700' :
                      'bg-gray-100 text-gray-700'
                    }`}>
                      {unit.unit_type}
                    </span>
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
                          className="w-full px-2 py-1 text-sm font-medium border border-blue-300 dark:border-blue-600 rounded-md focus:ring-2 focus:ring-blue-500 dark:focus:ring-blue-400 dark:bg-gray-700 dark:text-gray-100"
                          autoFocus
                        />
                        <button type="button" onClick={saveEdit} className="p-1 text-green-600">
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
                          className="w-full px-2 py-1 text-sm font-medium border border-green-300 dark:border-green-600 rounded-md focus:ring-2 focus:ring-green-500 dark:focus:ring-green-400 dark:bg-gray-700 dark:text-gray-100"
                          autoFocus
                        />
                        <button type="button" onClick={saveEdit} className="p-1 text-green-600">
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
                
                {/* Unit description */}
                {unit.description && (
                  <div className="mt-3 pt-3 border-t border-gray-100 dark:border-gray-700">
                    <p className="text-xs text-gray-600 dark:text-gray-400">{unit.description}</p>
                  </div>
                )}
              </motion.div>
            ))}
          </AnimatePresence>
          
          {/* Add Unit Button */}
          {getTotalSize() < totalSquareFeet && units.length < 10 && (
            <button
              type="button"
              onClick={addUnit}
              className="w-full p-3 border-2 border-dashed border-gray-300 dark:border-gray-600 rounded-xl hover:border-orange-400 dark:hover:border-orange-500 hover:bg-orange-50 dark:hover:bg-orange-900/20 transition-all group"
            >
              <div className="flex items-center justify-center gap-2">
                <Plus className="h-4 w-4 text-gray-400 group-hover:text-orange-600 dark:group-hover:text-orange-400" />
                <span className="text-sm font-medium text-gray-600 dark:text-gray-300 group-hover:text-orange-600 dark:group-hover:text-orange-400">
                  Add Space ({(totalSquareFeet - getTotalSize()).toLocaleString()} SF remaining)
                </span>
              </div>
            </button>
          )}
        </div>
      </div>
      
      {/* Footer Summary */}
      <div className="mt-6 space-y-3">
        {/* Financial & Space Summary */}
        {getTotalMonthlyRent() > 0 && (
          <div className="bg-gradient-to-br from-green-50 to-emerald-50/50 dark:from-green-900/20 dark:to-emerald-900/20 rounded-xl p-4 border border-green-200 dark:border-green-700">
            <div className="grid grid-cols-4 gap-3">
              <div>
                <div className="flex items-center gap-1 mb-1">
                  <DollarSign className="h-3.5 w-3.5 text-green-600" />
                  <span className="text-xs font-medium text-green-900 dark:text-green-100">Monthly</span>
                </div>
                <div className="text-lg font-bold text-green-700 dark:text-green-300">
                  ${getTotalMonthlyRent().toLocaleString()}
                </div>
                <div className="text-xs text-green-600 dark:text-green-400">
                  ${(getTotalMonthlyRent() * 12).toLocaleString()}/yr
                </div>
              </div>
              
              <div>
                <div className="flex items-center gap-1 mb-1">
                  <Square className="h-3.5 w-3.5 text-blue-600" />
                  <span className="text-xs font-medium text-blue-900 dark:text-blue-100">Configured</span>
                </div>
                <div className="text-lg font-bold text-blue-700 dark:text-blue-300">
                  {(getTotalSize() / 1000).toFixed(0)}K SF
                </div>
                <div className="text-xs text-blue-600 dark:text-blue-400">
                  {getSpaceUtilization().toFixed(0)}% utilized
                </div>
              </div>
              
              <div>
                <div className="flex items-center gap-1 mb-1">
                  <TrendingUp className="h-3.5 w-3.5 text-purple-600" />
                  <span className="text-xs font-medium text-purple-900 dark:text-purple-100">Avg Rate</span>
                </div>
                <div className="text-lg font-bold text-purple-700 dark:text-purple-300">
                  ${getAverageRentPerSF().toFixed(2)}
                </div>
                <div className="text-xs text-purple-600 dark:text-purple-400">per SF/year</div>
              </div>
              
              <div>
                <div className="flex items-center gap-1 mb-1">
                  <Zap className="h-3.5 w-3.5 text-orange-600" />
                  <span className="text-xs font-medium text-orange-900 dark:text-orange-100">Efficiency</span>
                </div>
                <div className="text-lg font-bold text-orange-700 dark:text-orange-300">
                  {warehouseSquareFeet > 0 
                    ? Math.round((warehouseSquareFeet / totalSquareFeet) * 100)
                    : 100}%
                </div>
                <div className="text-xs text-orange-600 dark:text-orange-400">warehouse</div>
              </div>
            </div>
          </div>
        )}
        
        {/* Info Box */}
        <div className="bg-blue-50 dark:bg-blue-900/20 rounded-xl p-3.5 border border-blue-200 dark:border-blue-700">
          <div className="flex items-start gap-2">
            <Info className="h-4 w-4 text-blue-600 mt-0.5 flex-shrink-0" />
            <div>
              <p className="text-xs font-semibold text-blue-900 dark:text-blue-100 mb-1">Industrial Configuration</p>
              <p className="text-xs text-blue-700 dark:text-blue-300 leading-relaxed">
                Your {currentIndustrialType.label.toLowerCase()} facility has been configured based on the space breakdown provided. 
                {clearHeight > 0 && ` With ${clearHeight}' clear height, this facility is suitable for ${
                  clearHeight >= 30 ? 'high-bay storage and distribution' : 
                  clearHeight >= 20 ? 'standard warehousing' : 
                  'light industrial use'
                }.`}
                {railAccess && ' Rail access adds significant value for heavy manufacturing and distribution operations.'}
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default React.memo(IndustrialUnits);