import React, { MouseEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import { Property, PropertyStatus } from '../../../../../types/property';
import { StatusBadge } from './StatusBadge';
import { useSecureImageUrl } from '../../../../../hooks/useSecureImageUrl';

interface PropertyRowProps {
  property: Property;
  onEdit: (propertyId: number) => void;
  onDelete: (property: Property) => void;
  index: number;
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

  // Fetch secure URL for the primary image (for private Azure containers)
  const primaryImageUrl = getPrimaryImage();
  const secureImageUrl = useSecureImageUrl(primaryImageUrl);

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
      console.error('Cannot delete property: missing property ID');
      return;
    }
    onDelete(property);
  };

  // The data-table CSS class now handles zebra striping automatically
  return (
    <tr 
      className="cursor-pointer"
      onClick={() => property.id && navigate(`/properties/${property.id}`)}
    >
      <td className="px-6 py-4 whitespace-nowrap">
        <div className="flex items-center">
          <div className="relative flex-shrink-0 h-10 w-10 rounded-lg overflow-hidden">
            {secureImageUrl && (
              <img
                src={secureImageUrl}
                alt={property.name}
                className="h-full w-full object-cover"
                onError={handleImageError}
              />
            )}
            <div 
              className={`absolute inset-0 bg-blue-100 dark:bg-blue-900/20 rounded-lg flex items-center justify-center text-blue-600 dark:text-blue-400 font-bold ${
                secureImageUrl ? 'hidden' : 'flex'
              }`}
            >
              {getImageInitial(property.name)}
            </div>
          </div>
          <div className="ml-4">
            <div className="text-sm font-medium text-gray-900 dark:text-gray-100">
              {property.name}
            </div>
          </div>
        </div>
      </td>
      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400 text-left">
        {property.property_type}
      </td>
      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400 text-left">
        <div
          className="max-w-xs truncate"
          title={getFormattedAddress().title}
        >
          {getFormattedAddress().display}
        </div>
      </td>
      <td className="px-6 py-4 whitespace-nowrap text-center">
        <StatusBadge status={property.status || PropertyStatus.ACTIVE} />
      </td>
      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400 text-right">
        {property.created_at && new Date(property.created_at).toLocaleDateString()}
      </td>
      <td className="px-6 py-4 whitespace-nowrap text-center text-sm font-medium">
        <div className="inline-flex space-x-3">
          <button
            onClick={(e) => {
              e.stopPropagation();
              property.id && navigate(`/properties/${property.id}`);
            }}
            className="text-indigo-600 dark:text-indigo-400 hover:text-indigo-900 dark:hover:text-indigo-300"
          >
            View
          </button>
          <button
            onClick={(e) => {
              e.stopPropagation();
              property.id && onEdit(property.id);
            }}
            className="text-blue-600 dark:text-blue-400 hover:text-blue-900 dark:hover:text-blue-300"
          >
            Edit
          </button>
          <button
            onClick={handleDelete}
            className="text-red-600 dark:text-red-400 hover:text-red-900 dark:hover:text-red-300"
          >
            Delete
          </button>
        </div>
      </td>
    </tr>
  );
};