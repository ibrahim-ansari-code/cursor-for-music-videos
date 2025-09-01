import React from 'react';
import { useFormContext } from 'react-hook-form';
import { PropertyFormData, PropertyType } from '@/types/property';
import { AlertCircle } from 'lucide-react';

// Import property-specific review components
import ResidentialReview from './ResidentialReview';
import ApartmentComplexReview from './ApartmentComplexReview';
import CommercialReview from './CommercialReview';
import IndustrialReview from './IndustrialReview';
import MixedUseReview from './MixedUseReview';

interface ReviewStepProps {
  isEditing: boolean;
}

const ReviewStep: React.FC<ReviewStepProps> = ({ isEditing: _ }) => {
  const { watch } = useFormContext<PropertyFormData>();
  const propertyType = watch('property_type');

  // Route to appropriate review component based on property type
  switch (propertyType) {
    case PropertyType.RESIDENTIAL:
      return <ResidentialReview />;
    
    case PropertyType.APARTMENT_COMPLEX:
      return <ApartmentComplexReview />;
    
    case PropertyType.COMMERCIAL:
      return <CommercialReview />;
    
    case PropertyType.INDUSTRIAL:
      return <IndustrialReview />;
    
    case PropertyType.MIXED_USE:
      return <MixedUseReview />;
    
    case PropertyType.LAND:
    case PropertyType.SPECIAL_PURPOSE:
    case PropertyType.OTHER:
      // These types might have minimal review requirements
      return (
        <div className="h-full flex items-center justify-center">
          <div className="text-center py-8">
            <AlertCircle className="h-12 w-12 text-gray-400 mx-auto mb-3" />
            <p className="text-gray-600 mb-2">
              Review configuration for {propertyType.toLowerCase().replace(/_/g, ' ')} properties
            </p>
            <p className="text-sm text-gray-500">
              Property will be created with basic information provided.
            </p>
          </div>
        </div>
      );
    
    default:
      return (
        <div className="h-full flex items-center justify-center">
          <div className="text-center py-8">
            <AlertCircle className="h-12 w-12 text-gray-400 mx-auto mb-3" />
            <p className="text-gray-600">Please select a property type first</p>
          </div>
        </div>
      );
  }
};

export default ReviewStep;
