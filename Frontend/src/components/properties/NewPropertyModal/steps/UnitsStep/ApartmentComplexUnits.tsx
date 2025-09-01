import React, { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import { useFormContext } from 'react-hook-form';
import { PropertyFormData, GeneratedUnit } from '@/types/property';
import { 
  Building2, Home, ChevronDown, ChevronRight,
  Info, Calculator, TrendingUp, AlertTriangle,
  CheckCircle, Hash, Percent,
  Layout, Settings, RefreshCw, Edit2
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

interface ApartmentComplexUnitsProps {
  onNext?: () => void;
}

interface BuildingUnits {
  buildingId: string;
  buildingName: string;
  units: GeneratedUnit[];
}

interface BuildingDistribution {
  buildingId: string;
  buildingName: string;
  unitCounts: { [unitType: string]: number };
  totalUnits: number;
  percentage: number;
}

const ApartmentComplexUnits: React.FC<ApartmentComplexUnitsProps> = () => {
  const { watch, setValue } = useFormContext<PropertyFormData>();
  const typeSpecificDetails = watch('type_specific_details');
  
  // Get data from ApartmentComplexForm - optimize watch calls
  const numberOfBuildings = Number(typeSpecificDetails?.number_of_buildings) || 1;
  const totalUnits = Number(typeSpecificDetails?.total_units) || 0;
  const unitMix = useMemo(() => typeSpecificDetails?.unit_mix || {}, [typeSpecificDetails?.unit_mix]);
  const complexStyle = typeSpecificDetails?.complex_style || 'garden';
  const buildingCodesNames = useMemo(() => typeSpecificDetails?.building_codes_names || {}, [typeSpecificDetails?.building_codes_names]);
  
  const [buildings, setBuildings] = useState<BuildingUnits[]>([]);
  const [buildingDistributions, setBuildingDistributions] = useState<BuildingDistribution[]>([]);
  const [expandedBuildings, setExpandedBuildings] = useState<Set<string>>(new Set(['Building-1']));
  const [distributionMode, setDistributionMode] = useState<'even' | 'custom'>('even');
  const [showDistributionWarning, setShowDistributionWarning] = useState(false);
  const [unitNumberingPattern, setUnitNumberingPattern] = useState<'sequential' | 'floor-based'>('floor-based');
  const [showQuickSetup, setShowQuickSetup] = useState(true);
  const [editingUnitName, setEditingUnitName] = useState<{buildingIndex: number, unitIndex: number} | null>(null);
  const [tempUnitName, setTempUnitName] = useState('');
  const [isUpdatingQuickSetup, setIsUpdatingQuickSetup] = useState(false);
  
  // Simplified state for quick setup - separate from building units
  const [quickSetupValues, setQuickSetupValues] = useState<{
    [unitType: string]: { rent?: number; size?: number }
  }>({});
  
  // Refs to track previous values to prevent unnecessary setValue calls
  const prevGeneratedUnitsRef = useRef<any>(null);
  const prevBuildingDistributionsRef = useRef<any>(null);
  
  // Simplified: just get the value from quick setup state
  const getQuickSetupValue = useCallback((unitType: string, field: 'rent' | 'size') => {
    return quickSetupValues[unitType]?.[field] || undefined;
  }, [quickSetupValues]);
  
  // Complex style configurations
  const complexStyleConfig = {
    garden: { emoji: '🌳', label: 'Garden Style', color: 'green' },
    highrise: { emoji: '🏢', label: 'High-Rise', color: 'blue' },
    midrise: { emoji: '🏘️', label: 'Mid-Rise', color: 'indigo' },
    townhome: { emoji: '🏡', label: 'Townhome', color: 'amber' },
    luxury: { emoji: '💎', label: 'Luxury', color: 'purple' },
    student: { emoji: '🎓', label: 'Student Housing', color: 'orange' }
  };
  
  const currentStyle = complexStyleConfig[complexStyle as keyof typeof complexStyleConfig] || complexStyleConfig.garden;
  
     // Unit type configurations - no default rent/size, start blank
   const unitTypeConfig = {
     studio: { label: 'Studio', bedrooms: 0, bathrooms: 1 },
     '1br': { label: '1 Bedroom', bedrooms: 1, bathrooms: 1 },
     '2br': { label: '2 Bedroom', bedrooms: 2, bathrooms: 2 },
     '3br': { label: '3 Bedroom', bedrooms: 3, bathrooms: 2 },
     '4br': { label: '4+ Bedroom', bedrooms: 4, bathrooms: 3 },
     penthouse: { label: 'Penthouse', bedrooms: 3, bathrooms: 3 }
   };
  
  // Memoize building distributions to prevent recreation on every render
  const memoizedBuildingDistributions = useMemo(() => {
    const distributions: BuildingDistribution[] = [];
    let remainingUnits = totalUnits;
    
    for (let i = 1; i <= numberOfBuildings; i++) {
      const buildingId = `Building-${i}`;
      const buildingName = buildingCodesNames[String(i)] || 
                         buildingCodesNames[String.fromCharCode(64 + i)] || 
                         `Building ${String.fromCharCode(64 + i)}`;
      
      const isLastBuilding = i === numberOfBuildings;
      let buildingUnitsCount = 0;
      let buildingUnitCounts: { [unitType: string]: number } = {};
      
      if (distributionMode === 'even') {
        // Even distribution
        buildingUnitsCount = isLastBuilding ? remainingUnits : Math.floor(totalUnits / numberOfBuildings);
        
        // Distribute unit types proportionally
        Object.entries(unitMix).forEach(([unitType, totalCount]) => {
          if (totalCount && Number(totalCount) > 0) {
            const unitsOfType = isLastBuilding 
              ? (totalCount as number) - distributions.reduce((sum, d) => sum + (d.unitCounts[unitType] || 0), 0)
              : Math.floor((totalCount as number) / numberOfBuildings);
            buildingUnitCounts[unitType] = Math.max(0, unitsOfType);
          }
        });
      } else {
        // Custom distribution - start with saved data or fall back to even distribution
        const customDist = typeSpecificDetails?.building_distributions?.[buildingId];
        if (customDist && Object.keys(customDist.unitCounts || {}).length > 0) {
          // Use saved custom distribution
          buildingUnitCounts = customDist.unitCounts || {};
          buildingUnitsCount = Object.values(buildingUnitCounts).reduce((sum: number, count: any) => sum + (count || 0), 0);
        } else {
          // Fall back to even distribution as starting point for custom mode
          buildingUnitsCount = isLastBuilding ? remainingUnits : Math.floor(totalUnits / numberOfBuildings);
          
          // Distribute unit types proportionally (same as even mode logic)
          Object.entries(unitMix).forEach(([unitType, totalCount]) => {
            if (totalCount && Number(totalCount) > 0) {
              const unitsOfType = isLastBuilding 
                ? (totalCount as number) - distributions.reduce((sum, d) => sum + (d.unitCounts[unitType] || 0), 0)
                : Math.floor((totalCount as number) / numberOfBuildings);
              buildingUnitCounts[unitType] = Math.max(0, unitsOfType);
            }
          });
        }
      }
      
      remainingUnits -= buildingUnitsCount;
      
      distributions.push({
        buildingId,
        buildingName,
        unitCounts: buildingUnitCounts,
        totalUnits: buildingUnitsCount,
        percentage: totalUnits > 0 ? (buildingUnitsCount / totalUnits) * 100 : 0
      });
    }
    
    return distributions;
  }, [numberOfBuildings, totalUnits, unitMix, distributionMode, buildingCodesNames]);
  
  // Update state only when distributions actually change
  useEffect(() => {
    setBuildingDistributions(memoizedBuildingDistributions);
  }, [memoizedBuildingDistributions]);
  
  // Generate units based on distribution - stable function reference
  const generateUnitsFromDistributionMemo = useCallback(() => {
    const newBuildings: BuildingUnits[] = [];
    
    buildingDistributions.forEach((dist, buildingIndex) => {
      const buildingNum = buildingIndex + 1;
      const buildingUnits: GeneratedUnit[] = [];
      let unitCounter = 0;
      
      // Generate units for each type in this building
      Object.entries(dist.unitCounts).forEach(([unitType, count]) => {
        const config = unitTypeConfig[unitType as keyof typeof unitTypeConfig];
        
        if (config && count > 0) {
          for (let i = 0; i < count; i++) {
            let unitNumber: string;
            
            if (unitNumberingPattern === 'floor-based') {
              // Floor-based numbering (e.g., 101, 102, 201, 202)
              const floorsCount = Math.max(1, Number(typeSpecificDetails?.floor_count) || 3);
              const unitsPerFloor = Math.ceil(count / floorsCount);
              const floor = Math.floor(i / unitsPerFloor) + 1;
              const unitOnFloor = (i % unitsPerFloor) + 1;
              unitNumber = `${buildingNum}${floor}${String(unitOnFloor).padStart(2, '0')}`;
            } else {
              // Sequential numbering (e.g., 101, 102, 103...)
              unitNumber = `${buildingNum}${String(101 + unitCounter).padStart(2, '0')}`;
            }
            
                    buildingUnits.push({
               name: `Unit ${unitNumber}`,
               bedrooms: config.bedrooms,
               bathrooms: config.bathrooms,
               size: getQuickSetupValue(unitType, 'size'),
               monthly_rent: getQuickSetupValue(unitType, 'rent'),
               unit_type: unitType,
               building_id: dist.buildingId,
               floor: unitNumberingPattern === 'floor-based' ? Math.floor(i / Math.ceil(count / (typeSpecificDetails?.floor_count || 3))) + 1 : undefined
             });
            
            unitCounter++;
          }
        }
      });
      
      newBuildings.push({
        buildingId: dist.buildingId,
        buildingName: dist.buildingName,
        units: buildingUnits
      });
    });
    
    setBuildings(newBuildings);
  }, [buildingDistributions, unitNumberingPattern, typeSpecificDetails?.floor_count, getQuickSetupValue]);
  
  // Generate units effect with better control - only regenerate when structure changes
  useEffect(() => {
    // Don't regenerate if we're just updating quick setup values
    if (isUpdatingQuickSetup) return;
    
    // Always generate on first load or when building structure changes
    if (buildingDistributions.length > 0 && (
      buildings.length === 0 || 
      buildings.length !== numberOfBuildings || 
      showDistributionWarning
    )) {
      generateUnitsFromDistributionMemo();
    }
  }, [buildingDistributions, numberOfBuildings, showDistributionWarning, generateUnitsFromDistributionMemo, isUpdatingQuickSetup, buildings.length]);
  
  
  // Save units to form when they change - with equality check to prevent cascading
  useEffect(() => {
    const allUnits = buildings.flatMap(b => b.units);
    const allUnitsStr = JSON.stringify(allUnits);
    
    if (prevGeneratedUnitsRef.current !== allUnitsStr) {
      prevGeneratedUnitsRef.current = allUnitsStr;
      setValue('generated_units', allUnits);
    }
    
    // Save building distributions to form with equality check
    const distMap: any = {};
    buildingDistributions.forEach(dist => {
      distMap[dist.buildingId] = {
        unitCounts: dist.unitCounts,
        totalUnits: dist.totalUnits
      };
    });
    
    const distMapStr = JSON.stringify(distMap);
    if (prevBuildingDistributionsRef.current !== distMapStr) {
      prevBuildingDistributionsRef.current = distMapStr;
      setValue('type_specific_details.building_distributions', distMap);
    }
  }, [buildings, buildingDistributions, setValue]);
  
  const toggleBuilding = (buildingId: string) => {
    setExpandedBuildings(prev => {
      const newSet = new Set(prev);
      if (newSet.has(buildingId)) {
        newSet.delete(buildingId);
      } else {
        newSet.add(buildingId);
      }
      return newSet;
    });
  };
  
  const updateBuildingDistribution = useCallback((buildingIndex: number, unitType: string, value: number) => {
    setBuildingDistributions(prev => {
      const newDistributions = [...prev];
      newDistributions[buildingIndex].unitCounts[unitType] = value;
      newDistributions[buildingIndex].totalUnits = Object.values(newDistributions[buildingIndex].unitCounts)
        .reduce((sum: number, count: any) => sum + (count || 0), 0);
      newDistributions[buildingIndex].percentage = totalUnits > 0 
        ? (newDistributions[buildingIndex].totalUnits / totalUnits) * 100 
        : 0;
      return newDistributions;
    });
    setShowDistributionWarning(true);
  }, [totalUnits]);
  
  const updateUnitField = useCallback((buildingIndex: number, unitIndex: number, field: string, value: any) => {
    setBuildings(prev => {
      const newBuildings = [...prev];
      const unit = newBuildings[buildingIndex].units[unitIndex];
      
             if (field === 'rent') {
         unit.monthly_rent = value;
       } else if (field === 'size') {
         unit.size = value;
       } else if (field === 'name') {
         unit.name = value;
       }
      
      return newBuildings;
    });
  }, []);
  
  // Simplified update function for quick setup - update values and existing units
  const updateQuickSetupValue = useCallback((unitType: string, field: 'rent' | 'size', value: number | undefined) => {
    // Set flag to prevent regeneration during quick setup updates
    setIsUpdatingQuickSetup(true);
    
    // Update the quick setup state
    setQuickSetupValues(prev => ({
      ...prev,
      [unitType]: {
        ...prev[unitType],
        [field]: value
      }
    }));
    
    // Update all existing units of this type in all buildings
    setBuildings(prev => {
      return prev.map(building => ({
        ...building,
        units: building.units.map(unit => {
          if (unit.unit_type === unitType) {
            return {
              ...unit,
              [field === 'rent' ? 'monthly_rent' : 'size']: value
            };
          }
          return unit;
        })
      }));
    });
    
    // Clear the flag after a brief delay
    setTimeout(() => setIsUpdatingQuickSetup(false), 100);
  }, []);
  
  const getTotalMonthlyRent = useCallback(() => {
    return buildings.reduce((total, building) => 
      total + building.units.reduce((buildingTotal, unit) => 
        buildingTotal + (unit.monthly_rent || 0), 0), 0);
  }, [buildings]);
  
  const getUnitCountByType = useCallback((unitType: string) => {
    return buildings.flatMap(b => b.units).filter(u => u.unit_type === unitType).length;
  }, [buildings]);
  
  const getTotalDistributedUnits = useCallback(() => {
    return buildingDistributions.reduce((sum, dist) => sum + dist.totalUnits, 0);
  }, [buildingDistributions]);
  
  const isDistributionValid = useCallback(() => {
    // Must have valid building distributions
    if (!buildingDistributions || buildingDistributions.length === 0) return false;
    
    const distributedTotal = getTotalDistributedUnits();
    
    // Primary validation: total distributed must match total units
    if (distributedTotal !== totalUnits) return false;
    
    // Additional validation: ensure no building has negative units
    const hasNegativeUnits = buildingDistributions.some(dist => 
      Object.values(dist.unitCounts).some(count => count < 0)
    );
    if (hasNegativeUnits) return false;
    
    // For even distribution mode, also check unit type consistency with original mix
    if (distributionMode === 'even') {
      for (const [unitType, totalCount] of Object.entries(unitMix)) {
        if (totalCount && Number(totalCount) > 0) {
          const distributedCount = buildingDistributions.reduce((sum, dist) => 
            sum + (dist.unitCounts[unitType] || 0), 0);
          if (distributedCount !== Number(totalCount)) return false;
        }
      }
    }
    
    // For custom distribution mode, just ensure totals match and no negatives
    return true;
  }, [getTotalDistributedUnits, totalUnits, unitMix, buildingDistributions, distributionMode]);
  
  return (
    <div className="h-full flex flex-col">
      {/* Header with complex style - Fixed spacing */}
      <div className="mb-6">
        <div className="flex items-center gap-3 mb-2">
          <span className="text-2xl">{currentStyle.emoji}</span>
          <div>
            <h2 className="text-xl font-semibold text-gray-900 flex items-center gap-2">
              {currentStyle.label} Complex Setup
            </h2>
            <p className="text-sm text-gray-600">
              {numberOfBuildings} {numberOfBuildings === 1 ? 'building' : 'buildings'} • {totalUnits} total units
            </p>
          </div>
        </div>
      </div>
      
      {/* Building Distribution Section */}
      <div className="bg-gradient-to-br from-indigo-50 to-blue-50 rounded-xl p-4 border border-indigo-200 mb-4">
        <div className="flex items-center justify-between mb-3">
          <div>
            <h3 className="text-sm font-semibold text-gray-900 flex items-center gap-2">
              <Layout className="h-4 w-4 text-indigo-600" />
              Building Distribution
            </h3>
            <p className="text-xs text-gray-600 mt-0.5">How to split your {totalUnits} units across {numberOfBuildings} buildings</p>
          </div>
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => setDistributionMode('even')}
              className={`px-3 py-1 text-xs font-medium rounded-lg transition-all ${
                distributionMode === 'even' 
                  ? 'bg-indigo-600 text-white shadow-sm' 
                  : 'bg-white text-gray-600 border border-gray-200 hover:bg-gray-50'
              }`}
            >
              <Percent className="h-3 w-3 inline mr-1" />
              Even
            </button>
            <button
              type="button"
              onClick={() => setDistributionMode('custom')}
              className={`px-3 py-1 text-xs font-medium rounded-lg transition-all ${
                distributionMode === 'custom' 
                  ? 'bg-indigo-600 text-white shadow-sm' 
                  : 'bg-white text-gray-600 border border-gray-200 hover:bg-gray-50'
              }`}
            >
              <Settings className="h-3 w-3 inline mr-1" />
              Custom
            </button>
          </div>
        </div>
        
        {/* Unit Numbering Pattern */}
        <div className="mb-3 flex items-center justify-between">
          <label className="text-xs font-medium text-gray-700">Unit Numbering</label>
          <div className="flex gap-1">
            <button
              type="button"
              onClick={() => {
                setUnitNumberingPattern('floor-based');
                setShowDistributionWarning(true);
              }}
              className={`px-2 py-1 text-xs rounded-md transition-all ${
                unitNumberingPattern === 'floor-based'
                  ? 'bg-indigo-100 text-indigo-700 font-medium'
                  : 'bg-white text-gray-600 hover:bg-gray-50'
              }`}
            >
              Floor-Based (101, 201)
            </button>
            <button
              type="button"
              onClick={() => {
                setUnitNumberingPattern('sequential');
                setShowDistributionWarning(true);
              }}
              className={`px-2 py-1 text-xs rounded-md transition-all ${
                unitNumberingPattern === 'sequential'
                  ? 'bg-indigo-100 text-indigo-700 font-medium'
                  : 'bg-white text-gray-600 hover:bg-gray-50'
              }`}
            >
              Sequential (101, 102)
            </button>
          </div>
        </div>
        
        {/* Distribution Grid */}
        <div className="space-y-2">
          {buildingDistributions.map((dist, index) => (
            <div key={dist.buildingId} className="bg-white rounded-lg p-3 border border-gray-200">
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-semibold text-gray-700 flex items-center gap-1">
                  <Building2 className="h-3 w-3 text-indigo-500" />
                  {dist.buildingName}
                </span>
                <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${
                  dist.totalUnits === Math.floor(totalUnits / numberOfBuildings) || 
                  (index === buildingDistributions.length - 1 && isDistributionValid())
                    ? 'bg-green-100 text-green-700'
                    : 'bg-amber-100 text-amber-700'
                }`}>
                  {dist.totalUnits} units ({dist.percentage.toFixed(1)}%)
                </span>
              </div>
              
              {distributionMode === 'custom' && (
                <div className="grid grid-cols-3 gap-2">
                  {Object.entries(unitMix).map(([unitType, totalCount]) => {
                    if (!totalCount || totalCount === 0) return null;
                    const config = unitTypeConfig[unitType as keyof typeof unitTypeConfig];
                    const currentCount = dist.unitCounts[unitType] || 0;
                    
                    return (
                      <div key={unitType} className="flex items-center gap-1">
                        <label className="text-[10px] text-gray-600 min-w-[40px]">
                          {config?.label || unitType}
                        </label>
                        <input
                          type="number"
                          min="0"
                          max={totalCount as number}
                          value={currentCount}
                          onChange={(e) => updateBuildingDistribution(index, unitType, parseInt(e.target.value) || 0)}
                          className="w-12 px-1 py-0.5 text-xs font-medium border border-gray-200 rounded text-center focus:ring-1 focus:ring-indigo-500 focus:border-transparent"
                        />
                      </div>
                    );
                  })}
                </div>
              )}
              
              {distributionMode === 'even' && (
                <div className="text-[10px] text-gray-500">
                  {Object.entries(dist.unitCounts)
                    .filter(([_, count]) => count > 0)
                    .map(([unitType, count]) => {
                      const config = unitTypeConfig[unitType as keyof typeof unitTypeConfig];
                      return `${config?.label}: ${count}`;
                    })
                    .join(' • ')}
                </div>
              )}
            </div>
          ))}
        </div>
        
        {/* Distribution Validation */}
        {!isDistributionValid() && (
          <div className="mt-2 p-2 bg-amber-50 rounded-lg border border-amber-200">
            <div className="flex items-start gap-2">
              <AlertTriangle className="h-4 w-4 text-amber-600 mt-0.5 flex-shrink-0" />
              <div>
                <p className="text-xs font-medium text-amber-900">
                  {distributionMode === 'custom' ? 'Distribution Incomplete' : 'Distribution Mismatch'}
                </p>
                <p className="text-[10px] text-amber-700 mt-0.5">
                  Total distributed: {getTotalDistributedUnits()} / {totalUnits} units
                  {distributionMode === 'even' && ' (Unit types must match original mix)'}
                </p>
              </div>
            </div>
          </div>
        )}
        
        {showDistributionWarning && (
          <div className="mt-2 flex items-center justify-between p-2 bg-blue-50 rounded-lg border border-blue-200">
            <div className="flex items-center gap-2">
              <Info className="h-4 w-4 text-blue-600" />
              <p className="text-xs text-blue-700">Distribution changed. Regenerate units?</p>
            </div>
            <button
              type="button"
              onClick={() => {
                generateUnitsFromDistributionMemo();
                setShowDistributionWarning(false);
              }}
              className="px-2 py-1 text-xs font-medium bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors flex items-center gap-1"
            >
              <RefreshCw className="h-3 w-3" />
              Regenerate
            </button>
          </div>
        )}
      </div>
      
      {/* Quick Setup by Unit Type - Collapsible */}
      <div className="bg-gradient-to-br from-gray-50 to-gray-100/50 rounded-xl border border-gray-200 mb-4 overflow-hidden">
        <button
          type="button"
          onClick={() => setShowQuickSetup(!showQuickSetup)}
          className="w-full px-4 py-3 hover:bg-gray-100 transition-all flex items-center justify-between"
        >
          <h3 className="text-sm font-semibold text-gray-900 flex items-center gap-2">
            <Calculator className="h-4 w-4 text-indigo-600" />
            Quick Setup by Unit Type
            <span className="text-xs font-normal text-gray-600 ml-2">(Optional)</span>
          </h3>
          <div className="flex items-center gap-2">
            <span className="text-xs text-gray-500">Set rent and size for all units of each type</span>
            {showQuickSetup ? (
              <ChevronDown className="h-4 w-4 text-gray-400" />
            ) : (
              <ChevronRight className="h-4 w-4 text-gray-400" />
            )}
          </div>
        </button>
        
        <AnimatePresence>
          {showQuickSetup && (
            <motion.div
              initial={{ height: 0 }}
              animate={{ height: 'auto' }}
              exit={{ height: 0 }}
              transition={{ duration: 0.2 }}
              className="overflow-hidden"
            >
              <div className="p-4 pt-0">
                <div className="grid grid-cols-2 gap-3">
          {Object.entries(unitMix).map(([unitType, count]) => {
            if (!count || count === 0) return null;
            const config = unitTypeConfig[unitType as keyof typeof unitTypeConfig];
            if (!config) return null;
            
            const unitCount = getUnitCountByType(unitType);
            const currentRent = getQuickSetupValue(unitType, 'rent');
            const currentSize = getQuickSetupValue(unitType, 'size');
            
            return (
              <div key={unitType} className="bg-white rounded-lg p-3 border border-gray-200">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs font-semibold text-gray-700">
                    {config.label} ({unitCount} units)
                  </span>
                  <span className="text-xs text-gray-500">
                    {config.bedrooms}BR/{config.bathrooms}BA
                  </span>
                </div>
                
                <div className="grid grid-cols-2 gap-2">
                  <div>
                    <label className="text-[10px] text-gray-600 mb-0.5 block">Rent/Unit</label>
                    <div className="flex items-center">
                      <span className="text-xs text-gray-500 mr-1">$</span>
                      <input
                        type="number"
                        value={currentRent || ''}
                        onChange={(e) => {
                          const value = e.target.value === '' ? undefined : parseFloat(e.target.value);
                          updateQuickSetupValue(unitType, 'rent', value);
                        }}
                        className="w-full px-2 py-1 text-xs font-medium border border-gray-200 rounded focus:ring-2 focus:ring-green-500 focus:border-transparent"
                        placeholder="Enter rent"
                      />
                    </div>
                  </div>
                  
                  <div>
                    <label className="text-[10px] text-gray-600 mb-0.5 block">Size (sq ft)</label>
                    <input
                      type="number"
                      value={currentSize || ''}
                      onChange={(e) => {
                        const value = e.target.value === '' ? undefined : parseFloat(e.target.value);
                        updateQuickSetupValue(unitType, 'size', value);
                      }}
                      className="w-full px-2 py-1 text-xs font-medium border border-gray-200 rounded focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                      placeholder="Enter size"
                    />
                  </div>
                </div>
              </div>
            );
          })}
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
      
      {/* Buildings with Units */}
      <div className="flex-1 overflow-y-auto">
        <div className="space-y-3">
          <AnimatePresence>
            {buildings.map((building, buildingIndex) => {
              const dist = buildingDistributions[buildingIndex];
              
              return (
                <motion.div
                  key={building.buildingId}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, x: -100 }}
                  transition={{ delay: buildingIndex * 0.05 }}
                  className="bg-white rounded-xl border border-gray-200 overflow-hidden"
                >
                  {/* Building Header */}
                  <button
                    type="button"
                    onClick={() => toggleBuilding(building.buildingId)}
                    className="w-full px-4 py-3 bg-gradient-to-r from-gray-50 to-gray-100 hover:from-gray-100 hover:to-gray-150 transition-all flex items-center justify-between"
                  >
                    <div className="flex items-center gap-3">
                      <Building2 className="h-5 w-5 text-indigo-600" />
                      <div className="text-left">
                        <h4 className="font-semibold text-gray-900">{building.buildingName}</h4>
                        <span className="text-xs text-gray-600">
                          {building.units.length} units • {dist?.percentage.toFixed(1)}% of complex
                        </span>
                      </div>
                    </div>
                    
                    <div className="flex items-center gap-3">
                      {isDistributionValid() && (
                        <CheckCircle className="h-4 w-4 text-green-500" />
                      )}
                      <span className="text-sm font-medium text-green-600">
                        ${building.units.reduce((sum, u) => sum + (u.monthly_rent || 0), 0).toLocaleString()}/mo
                      </span>
                      {expandedBuildings.has(building.buildingId) ? (
                        <ChevronDown className="h-4 w-4 text-gray-400" />
                      ) : (
                        <ChevronRight className="h-4 w-4 text-gray-400" />
                      )}
                    </div>
                  </button>
                  
                  {/* Building Units */}
                  <AnimatePresence>
                    {expandedBuildings.has(building.buildingId) && (
                      <motion.div
                        initial={{ height: 0 }}
                        animate={{ height: 'auto' }}
                        exit={{ height: 0 }}
                        transition={{ duration: 0.2 }}
                        className="overflow-hidden"
                      >
                        <div className="p-4 bg-gray-50/50">
                          {/* Group units by type */}
                          {Object.entries(
                            building.units.reduce((acc, unit) => {
                              const type = unit.unit_type || 'standard';
                              if (!acc[type]) acc[type] = [];
                              acc[type].push(unit);
                              return acc;
                            }, {} as { [key: string]: GeneratedUnit[] })
                          ).map(([unitType, unitsOfType]) => (
                            <div key={unitType} className="mb-3">
                              <h5 className="text-xs font-semibold text-gray-700 mb-2 uppercase tracking-wider flex items-center justify-between">
                                <div className="flex items-center gap-2">
                                  {unitTypeConfig[unitType as keyof typeof unitTypeConfig]?.label || unitType} 
                                  <span className="text-gray-500 normal-case">
                                    ({unitsOfType.length} {unitsOfType.length === 1 ? 'unit' : 'units'})
                                  </span>
                                  {unitNumberingPattern === 'floor-based' && (
                                    <Hash className="h-3 w-3 text-gray-400" />
                                  )}
                                </div>
                                <span className="text-[10px] text-gray-400 normal-case flex items-center gap-1">
                                  <Edit2 className="h-3 w-3" />
                                  Click names to edit
                                </span>
                              </h5>
                              
                              <div className="grid grid-cols-2 gap-2">
                                {unitsOfType.map((unit, unitIndex) => {
                                  const actualUnitIndex = building.units.findIndex(u => u === unit);
                                  
                                  return (
                                    <div key={`${unit.name}-${unitIndex}`} 
                                         className="bg-white rounded-lg p-2.5 border border-gray-200 hover:border-indigo-300 transition-colors">
                                      <div className="flex items-center justify-between mb-1.5">
                                        <div className="flex items-center gap-1 flex-1 min-w-0">
                                          <Home className="h-3 w-3 text-gray-400 flex-shrink-0" />
                                          {editingUnitName?.buildingIndex === buildingIndex && editingUnitName?.unitIndex === actualUnitIndex ? (
                                            <input
                                              type="text"
                                              value={tempUnitName}
                                              onChange={(e) => setTempUnitName(e.target.value)}
                                              onBlur={() => {
                                                updateUnitField(buildingIndex, actualUnitIndex, 'name', tempUnitName);
                                                setEditingUnitName(null);
                                              }}
                                              onKeyDown={(e) => {
                                                if (e.key === 'Enter') {
                                                  updateUnitField(buildingIndex, actualUnitIndex, 'name', tempUnitName);
                                                  setEditingUnitName(null);
                                                }
                                                if (e.key === 'Escape') {
                                                  setEditingUnitName(null);
                                                  setTempUnitName(unit.name);
                                                }
                                              }}
                                              className="text-xs font-medium text-gray-900 bg-indigo-50 border border-indigo-300 rounded px-1 py-0.5 w-full focus:outline-none focus:ring-1 focus:ring-indigo-500"
                                              autoFocus
                                            />
                                          ) : (
                                            <button
                                              type="button"
                                              onClick={() => {
                                                setEditingUnitName({ buildingIndex, unitIndex: actualUnitIndex });
                                                setTempUnitName(unit.name);
                                              }}
                                              className="text-xs font-medium text-gray-900 hover:bg-indigo-50 rounded px-1 py-0.5 transition-colors text-left truncate"
                                              title="Click to edit unit name/number"
                                            >
                                              {unit.name}
                                            </button>
                                          )}
                                        </div>
                                        <span className="text-[10px] text-gray-500 flex-shrink-0 ml-2">
                                          {unit.bedrooms}BR/{unit.bathrooms}BA
                                        </span>
                                      </div>
                                      
                                      <div className="grid grid-cols-2 gap-1.5">
                                        <div>
                                          <label className="text-[10px] text-gray-500">Rent</label>
                                          <div className="flex items-center">
                                            <span className="text-[10px] text-gray-400 mr-0.5">$</span>
                                            <input
                                              type="number"
                                              value={unit.monthly_rent || ''}
                                              onChange={(e) => updateUnitField(buildingIndex, actualUnitIndex, 'rent', parseFloat(e.target.value) || 0)}
                                              className="w-full px-1.5 py-0.5 text-xs font-medium border border-gray-200 rounded focus:ring-1 focus:ring-green-500 focus:border-transparent"
                                              placeholder=""
                                            />
                                          </div>
                                        </div>
                                        
                                        <div>
                                          <label className="text-[10px] text-gray-500">Size</label>
                                          <div className="flex items-center">
                                            <input
                                              type="number"
                                              value={unit.size || ''}
                                              onChange={(e) => updateUnitField(buildingIndex, actualUnitIndex, 'size', parseFloat(e.target.value) || 0)}
                                              className="w-full px-1.5 py-0.5 text-xs font-medium border border-gray-200 rounded focus:ring-1 focus:ring-blue-500 focus:border-transparent"
                                              placeholder=""
                                            />
                                            <span className="text-[10px] text-gray-400 ml-0.5">ft²</span>
                                          </div>
                                        </div>
                                      </div>
                                      
                                      {unit.floor && (
                                        <div className="mt-1 text-[10px] text-gray-500">
                                          Floor {unit.floor}
                                        </div>
                                      )}
                                    </div>
                                  );
                                })}
                              </div>
                            </div>
                          ))}
                        </div>
                      </motion.div>
                    )}
                  </AnimatePresence>
                </motion.div>
              );
            })}
          </AnimatePresence>
        </div>
      </div>
      
      {/* Footer Summary */}
      <div className="mt-6 space-y-3">
        {/* Revenue Projection */}
        {getTotalMonthlyRent() > 0 && (
          <div className="bg-gradient-to-br from-green-50 to-emerald-50/50 rounded-xl p-4 border border-green-200">
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2">
                <TrendingUp className="h-4 w-4 text-green-600" />
                <span className="text-sm font-medium text-green-900">
                  Revenue Projection
                </span>
              </div>
              <div className="text-right">
                <div className="text-lg font-bold text-green-700">
                  ${getTotalMonthlyRent().toLocaleString()}/mo
                </div>
                <div className="text-xs text-green-600">
                  ${(getTotalMonthlyRent() * 12).toLocaleString()}/year
                </div>
              </div>
            </div>
            
            {/* Occupancy scenarios */}
            <div className="grid grid-cols-3 gap-2 mt-3 pt-3 border-t border-green-200">
              {[100, 95, 90].map(occupancy => (
                <div key={occupancy} className="text-center">
                  <div className="text-xs text-green-600 mb-0.5">{occupancy}% Occupied</div>
                  <div className="text-sm font-semibold text-green-800">
                    ${Math.round(getTotalMonthlyRent() * (occupancy / 100)).toLocaleString()}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
        
        {/* Distribution Summary */}
        {isDistributionValid() ? (
          <div className="bg-green-50 rounded-xl p-3.5 border border-green-200">
            <div className="flex items-center gap-2">
              <CheckCircle className="h-4 w-4 text-green-600 flex-shrink-0" />
              <div>
                <p className="text-xs font-semibold text-green-900">Configuration Complete</p>
                <p className="text-xs text-green-700">
                  All {totalUnits} units have been distributed across {numberOfBuildings} buildings.
                </p>
              </div>
            </div>
          </div>
        ) : (
          <div className="bg-amber-50 rounded-xl p-3.5 border border-amber-200">
            <div className="flex items-start gap-2">
              <AlertTriangle className="h-4 w-4 text-amber-600 mt-0.5 flex-shrink-0" />
              <div>
                <p className="text-xs font-semibold text-amber-900 mb-1">Configuration Incomplete</p>
                <p className="text-xs text-amber-700 leading-relaxed">
                  Please ensure all units are properly distributed across buildings. 
                  Current: {getTotalDistributedUnits()} / {totalUnits} units distributed.
                  {distributionMode === 'even' && ' (Unit type distribution must match the original unit mix)'}
                </p>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default React.memo(ApartmentComplexUnits);