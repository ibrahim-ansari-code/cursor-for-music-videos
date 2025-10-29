import React, { useState, useEffect, useCallback } from 'react';
import { useFormContext } from 'react-hook-form';
import { Building, Briefcase, ChevronDown, CheckCircle } from 'lucide-react';
import * as Select from '@radix-ui/react-select';
import * as Sentry from '@sentry/react';
import { PropertyStatus } from '../../../../types/property';
import { EditPropertyFormData } from '../validation/editPropertySchema';
import {
  fetchOwnershipEntities,
  type OwnershipEntity
} from '../../../../utils/api/ownershipEntities';
import NewOwnershipEntityModal from '../../../ownership/NewOwnershipEntityModal';

// Constant for "no ownership entity" value - can't use empty string with Radix Select
const NO_OWNERSHIP_ENTITY = '__none__';

export const BasicInfoSection: React.FC = () => {
  const {
    register,
    formState: { errors },
    setValue,
    watch,
  } = useFormContext<EditPropertyFormData>();

  const ownershipEntityId = watch('ownership_entity_id');

  const [ownershipEntities, setOwnershipEntities] = useState<OwnershipEntity[]>([]);
  const [loadingEntities, setLoadingEntities] = useState<boolean>(true);
  const [isCreateEntityModalOpen, setIsCreateEntityModalOpen] = useState(false);

  // Load ownership entities on mount
  useEffect(() => {
    const loadOwnershipEntities = async () => {
      try {
        setLoadingEntities(true);
        const response = await fetchOwnershipEntities({ pageSize: 100 });
        setOwnershipEntities(response.entities || []);
      } catch (error) {
        console.error('Failed to load ownership entities:', error);
      } finally {
        setLoadingEntities(false);
      }
    };

    loadOwnershipEntities();
  }, []);

  // Handle ownership entity creation
  const handleEntityCreated = useCallback((newEntity: OwnershipEntity) => {
    Sentry.logger.info('Ownership entity created from edit property modal', {
      entityId: newEntity.id,
      entityName: newEntity.name,
      entityType: newEntity.entity_type,
    });

    // Add to list using functional setState
    setOwnershipEntities(prev => [...prev, newEntity]);

    // Auto-select the newly created entity
    setValue('ownership_entity_id', newEntity.id, { shouldDirty: true });

    // Close modal
    setIsCreateEntityModalOpen(false);

    // Success toast is already shown by the modal component
  }, [setValue]);

  return (
    <div className="space-y-4">
      <div className="flex items-center space-x-2 mb-4">
        <Building className="h-5 w-5 text-blue-600 dark:text-blue-400" />
        <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">Basic Information</h3>
      </div>

      {/* Property Name */}
      <div>
        <label htmlFor="name" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
          Property Name <span className="text-red-500">*</span>
        </label>
        <input
          {...register('name')}
          type="text"
          id="name"
          className={`w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:border-gray-600 dark:text-gray-100 ${
            errors.name ? 'border-red-500' : 'border-gray-300 dark:border-gray-600'
          }`}
          placeholder="Enter property name"
        />
        {errors.name && (
          <p className="mt-1 text-sm text-red-600 dark:text-red-400">{errors.name.message}</p>
        )}
      </div>

      {/* Status */}
      <div>
        <label htmlFor="status" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
          Status <span className="text-red-500">*</span>
        </label>
        <select
          {...register('status')}
          id="status"
          className={`w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:border-gray-600 dark:text-gray-100 ${
            errors.status ? 'border-red-500' : 'border-gray-300 dark:border-gray-600'
          }`}
        >
          <option value={PropertyStatus.ACTIVE}>Active</option>
          <option value={PropertyStatus.INACTIVE}>Inactive</option>
          <option value={PropertyStatus.VACANT}>Vacant</option>
          <option value={PropertyStatus.RENTED}>Rented</option>
          <option value={PropertyStatus.PARTIALLY_RENTED}>Partially Rented</option>
          <option value={PropertyStatus.DRAFT}>Draft</option>
          <option value={PropertyStatus.ARCHIVED}>Archived</option>
        </select>
        {errors.status && (
          <p className="mt-1 text-sm text-red-600 dark:text-red-400">{errors.status.message}</p>
        )}
      </div>

      {/* Year Built */}
      <div>
        <label htmlFor="year_built" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
          Year Built
        </label>
        <input
          {...register('year_built', {
            setValueAs: (v) => v === '' || v === null ? null : parseInt(v, 10)
          })}
          type="number"
          id="year_built"
          className={`w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:border-gray-600 dark:text-gray-100 ${
            errors.year_built ? 'border-red-500' : 'border-gray-300 dark:border-gray-600'
          }`}
          placeholder="e.g., 2010"
          min="1800"
          max="2100"
        />
        {errors.year_built && (
          <p className="mt-1 text-sm text-red-600 dark:text-red-400">{errors.year_built.message}</p>
        )}
      </div>

      {/* Ownership Entity */}
      <div>
        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
          <Briefcase className="h-4 w-4 inline mr-1 mb-0.5" />
          Ownership Entity
        </label>
        {loadingEntities ? (
          <div className="w-full px-3 py-2 border rounded-lg bg-gray-50 dark:bg-gray-800 border-gray-300 dark:border-gray-600">
            <span className="text-sm text-gray-500 dark:text-gray-400">Loading entities...</span>
          </div>
        ) : (
          <>
            <Select.Root
              value={ownershipEntityId ?? NO_OWNERSHIP_ENTITY}
              onValueChange={(value) => {
                Sentry.logger.trace('Ownership entity changed', { value, isNone: value === NO_OWNERSHIP_ENTITY });
                setValue('ownership_entity_id', value === NO_OWNERSHIP_ENTITY ? null : value, { shouldDirty: true });
              }}
            >
              <Select.Trigger className="w-full px-3 py-2.5 text-sm font-medium border-2 border-gray-200 dark:border-gray-600 rounded-lg focus:border-blue-500 dark:focus:border-blue-400 focus:ring-2 focus:ring-blue-100 dark:focus:ring-blue-900 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 transition-all flex items-center justify-between hover:border-gray-300 dark:hover:border-gray-500">
                <Select.Value placeholder="None" />
                <Select.Icon>
                  <ChevronDown className="h-4 w-4 text-gray-500 dark:text-gray-400" />
                </Select.Icon>
              </Select.Trigger>
              <Select.Portal>
                <Select.Content
                  className="overflow-hidden bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-600 shadow-lg z-50 max-h-[300px]"
                  position="popper"
                  side="bottom"
                  align="start"
                  sideOffset={4}
                >
                  <Select.Viewport className="p-1">
                    <Select.Item
                      value={NO_OWNERSHIP_ENTITY}
                      className="relative flex items-center px-8 py-2 text-sm text-gray-900 dark:text-gray-100 rounded cursor-pointer hover:bg-blue-50 dark:hover:bg-blue-900/20 focus:bg-blue-50 dark:focus:bg-blue-900/20 outline-none select-none data-[state=checked]:bg-blue-50 dark:data-[state=checked]:bg-blue-900/30"
                    >
                      <Select.ItemText>None</Select.ItemText>
                      <Select.ItemIndicator className="absolute left-2 inline-flex items-center">
                        <CheckCircle className="h-4 w-4 text-blue-600 dark:text-blue-400" />
                      </Select.ItemIndicator>
                    </Select.Item>
                    {ownershipEntities.map((entity) => (
                      <Select.Item
                        key={entity.id}
                        value={entity.id}
                        className="relative flex items-center px-8 py-2 text-sm text-gray-900 dark:text-gray-100 rounded cursor-pointer hover:bg-blue-50 dark:hover:bg-blue-900/20 focus:bg-blue-50 dark:focus:bg-blue-900/20 outline-none select-none data-[state=checked]:bg-blue-50 dark:data-[state=checked]:bg-blue-900/30"
                      >
                        <Select.ItemText>{entity.name}</Select.ItemText>
                        <Select.ItemIndicator className="absolute left-2 inline-flex items-center">
                          <CheckCircle className="h-4 w-4 text-blue-600 dark:text-blue-400" />
                        </Select.ItemIndicator>
                      </Select.Item>
                    ))}
                  </Select.Viewport>
                </Select.Content>
              </Select.Portal>
            </Select.Root>
            {ownershipEntities.length === 0 && (
              <p className="mt-1 text-xs text-amber-600 dark:text-amber-400">
                No ownership entities found. You can create one from Settings.
              </p>
            )}
            {!loadingEntities && (
              <button
                type="button"
                onClick={() => setIsCreateEntityModalOpen(true)}
                className="mt-2 text-sm text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-300 font-medium transition-colors flex items-center gap-1"
              >
                <Briefcase className="h-3.5 w-3.5" />
                Create New Ownership Entity
              </button>
            )}
          </>
        )}
      </div>

      {/* Description */}
      <div>
        <label htmlFor="description" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
          Description
        </label>
        <textarea
          {...register('description')}
          id="description"
          rows={4}
          className={`w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:border-gray-600 dark:text-gray-100 resize-none ${
            errors.description ? 'border-red-500' : 'border-gray-300 dark:border-gray-600'
          }`}
          placeholder="Add a description of the property..."
          maxLength={2000}
        />
        {errors.description && (
          <p className="mt-1 text-sm text-red-600 dark:text-red-400">{errors.description.message}</p>
        )}
      </div>

      {/* Ownership Entity Creation Modal */}
      <NewOwnershipEntityModal
        isOpen={isCreateEntityModalOpen}
        onClose={() => setIsCreateEntityModalOpen(false)}
        onSuccess={handleEntityCreated}
      />
    </div>
  );
};
