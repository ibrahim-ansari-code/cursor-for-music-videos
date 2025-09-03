import React, { MouseEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import { Property, PropertyStatus } from '../../../../../types/property';
import { StatusBadge } from './StatusBadge';

interface PropertyRowProps {
  property: Property;
  onEdit: (propertyId: number) => void;
  onDelete: (propertyId: number) => void;
}

export const PropertyRow: React.FC<PropertyRowProps> = ({
  property,
  onEdit,
  onDelete,
}) => {
  const navigate = useNavigate();

  const getImageInitial = (name: string): string => {
    if (!name) return '';
    return name.charAt(0).toUpperCase();
  };

  const handleImageError = (e: React.SyntheticEvent<HTMLImageElement, Event>) => {
    e.currentTarget.style.display = 'none';
    const fallback = e.currentTarget.nextElementSibling as HTMLElement;
    if (fallback) {
      fallback.style.display = 'flex';
    }
  };

  const getPrimaryImage = (): string | null => {
    if (!property.images || property.images.length === 0) return null;
    
    // First try to get the primary image
    const primaryImage = property.images.find(img => img.is_primary);
    if (primaryImage) return primaryImage.image_url;
    
    // If no primary image, get the first image
    return property.images[0]?.image_url || null;
  };

  const getFormattedAddress = (): { display: string; title: string } => {
    const addressParts = [property.address, property.city, property.province].filter(Boolean);
    const formattedAddress = addressParts.join(', ');
    return {
      display: formattedAddress || 'No address',
      title: formattedAddress
    };
  };

  const handleDelete = (e: MouseEvent<HTMLButtonElement>) => {
    e.stopPropagation();
    if (!property.id) {
      console.error('Property ID is missing');
      return;
    }
    if (window.confirm('Are you sure you want to delete this property?')) {
      onDelete(property.id);
    }
  };

  return (
    <tr
      className="hover:bg-gray-50 cursor-pointer transition-colors"
      onClick={() => property.id && navigate(`/properties/${property.id}`)}
    >
      <td className="px-6 py-4 whitespace-nowrap">
        <div className="flex items-center justify-start">
          <div className="relative flex-shrink-0 h-10 w-10 rounded-lg overflow-hidden">
            {getPrimaryImage() && (
              <img
                src={getPrimaryImage()!}
                alt={property.name}
                className="h-full w-full object-cover"
                onError={handleImageError}
              />
            )}
            <div 
              className={`absolute inset-0 bg-blue-100 rounded-lg flex items-center justify-center text-blue-600 font-bold ${
                getPrimaryImage() ? 'hidden' : 'flex'
              }`}
            >
              {getImageInitial(property.name)}
            </div>
          </div>
          <div className="ml-4">
            <div className="text-sm font-medium text-gray-900 text-left">
              {property.name}
            </div>
          </div>
        </div>
      </td>
      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 text-center">
        {property.property_type}
      </td>
      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 text-center">
        <div
          className="max-w-xs truncate mx-auto"
          title={getFormattedAddress().title}
        >
          {getFormattedAddress().display}
        </div>
      </td>
      <td className="px-6 py-4 whitespace-nowrap text-center">
        <div className="flex justify-center">
          <StatusBadge status={property.status || PropertyStatus.ACTIVE} />
        </div>
      </td>
      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 text-center">
        {property.created_at && new Date(property.created_at).toLocaleDateString()}
      </td>
      <td className="px-6 py-4 whitespace-nowrap text-center text-sm font-medium">
        <div className="flex justify-center space-x-3">
          <button
            onClick={(e) => {
              e.stopPropagation();
              property.id && navigate(`/properties/${property.id}`);
            }}
            className="text-indigo-600 hover:text-indigo-900"
          >
            View
          </button>
          <button
            onClick={(e) => {
              e.stopPropagation();
              property.id && onEdit(property.id);
            }}
            className="text-blue-600 hover:text-blue-900"
          >
            Edit
          </button>
          <button
            onClick={handleDelete}
            className="text-red-600 hover:text-red-900"
          >
            Delete
          </button>
        </div>
      </td>
    </tr>
  );
};