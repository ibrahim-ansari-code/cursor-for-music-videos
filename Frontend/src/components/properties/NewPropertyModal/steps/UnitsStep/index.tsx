import React from 'react';
import { useFormContext } from 'react-hook-form';
import { PropertyFormData, PropertyType } from '@/types/property';
import ResidentialUnits from './ResidentialUnits';
import ApartmentComplexUnits from './ApartmentComplexUnits';
import CommercialUnits from './CommercialUnits';
import IndustrialUnits from './IndustrialUnits';
import MixedUseUnits from './MixedUseUnits';
import { AlertCircle } from 'lucide-react';

interface UnitsStepProps {
  onNext?: () => void;
}

const UnitsStep: React.FC<UnitsStepProps> = ({ onNext }) => {
  const { watch } = useFormContext<PropertyFormData>();
  const propertyType = watch('property_type');

  // Route to appropriate component based on property type
  switch (propertyType) {
    case PropertyType.RESIDENTIAL:
      return <ResidentialUnits onNext={onNext} />;
    
    case PropertyType.APARTMENT_COMPLEX:
      return <ApartmentComplexUnits onNext={onNext} />;
    
    case PropertyType.COMMERCIAL:
      return <CommercialUnits onNext={onNext} />;
    
    case PropertyType.INDUSTRIAL:
      return <IndustrialUnits onNext={onNext} />;
    
    case PropertyType.MIXED_USE:
      return <MixedUseUnits onNext={onNext} />;
    
    case PropertyType.LAND:
    case PropertyType.SPECIAL_PURPOSE:
    case PropertyType.OTHER:
      // These types might not need units or have minimal configuration
      return (
        <div className="text-center py-8">
          <AlertCircle className="h-12 w-12 text-gray-400 mx-auto mb-3" />
          <p className="text-gray-600">
            Unit configuration is not available for {propertyType.toLowerCase()} properties.
          </p>
          <p className="text-sm text-gray-500 mt-2">
            You can add units manually after property creation if needed.
          </p>
        </div>
      );
    
    default:
      return (
        <div className="text-center py-8">
          <AlertCircle className="h-12 w-12 text-gray-400 mx-auto mb-3" />
          <p className="text-gray-600">Please select a property type first</p>
        </div>
      );
  }
};

export default React.memo(UnitsStep);