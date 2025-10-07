import React from 'react';
import { Wrench } from 'lucide-react';
import { useFormContext } from 'react-hook-form';
import { PropertyType } from '../../../../types/property';

// Import type-specific forms from NewPropertyModal
import ResidentialForm from '../../NewPropertyModal/steps/DetailsStep/typeSpecificForms/ResidentialForm';
import ApartmentComplexForm from '../../NewPropertyModal/steps/DetailsStep/typeSpecificForms/ApartmentComplexForm';
import CommercialForm from '../../NewPropertyModal/steps/DetailsStep/typeSpecificForms/CommercialForm';
import IndustrialForm from '../../NewPropertyModal/steps/DetailsStep/typeSpecificForms/IndustrialForm';
import MixedUseForm from '../../NewPropertyModal/steps/DetailsStep/typeSpecificForms/MixedUseForm';

interface TypeSpecificSectionProps {
  propertyType: PropertyType;
}

export const TypeSpecificSection: React.FC<TypeSpecificSectionProps> = ({ propertyType }) => {
  useFormContext();
  
  // Watch type_specific_details to trigger re-renders when they change

  const renderTypeSpecificForm = () => {
    switch (propertyType) {
      case PropertyType.RESIDENTIAL:
        return <ResidentialForm />;
      case PropertyType.APARTMENT_COMPLEX:
        return <ApartmentComplexForm />;
      case PropertyType.COMMERCIAL:
        return <CommercialForm />;
      case PropertyType.INDUSTRIAL:
        return <IndustrialForm />;
      case PropertyType.MIXED_USE:
        return <MixedUseForm />;
      case PropertyType.LAND:
      case PropertyType.SPECIAL_PURPOSE:
      case PropertyType.OTHER:
        return (
          <div className="p-4 bg-gray-50 dark:bg-gray-700 rounded-lg border border-gray-200 dark:border-gray-600">
            <p className="text-sm text-gray-600 dark:text-gray-400">
              No additional property-specific details available for this property type.
            </p>
          </div>
        );
      default:
        return null;
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center space-x-2 mb-4">
        <Wrench className="h-5 w-5 text-blue-600 dark:text-blue-400" />
        <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
          {propertyType} Details
        </h3>
      </div>

      <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-700 rounded-lg p-3 mb-4">
        <p className="text-sm text-blue-800 dark:text-blue-200">
          <strong>Note:</strong> Property type cannot be changed after creation. You can only edit the property-specific details below.
        </p>
      </div>

      {renderTypeSpecificForm()}
    </div>
  );
};
