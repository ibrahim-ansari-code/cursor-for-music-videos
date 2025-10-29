import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import * as Dialog from '@radix-ui/react-dialog';
import * as Select from '@radix-ui/react-select';
import { ChevronDown, CheckCircle } from 'lucide-react';
import { toast } from 'react-toastify';
import * as Sentry from '@sentry/react';
import {
  OwnershipEntity,
  EntityType,
  ENTITY_TYPES,
  updateOwnershipEntity
} from '../../utils/api/ownershipEntities';

interface EditOwnershipEntityModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: (entity: OwnershipEntity) => void;
  entity: OwnershipEntity | null;
}

interface FormData {
  entity_type: EntityType | '';
  name: string;
  legal_name: string;
  tax_id: string;
  contact_name: string;
  contact_email: string;
  contact_phone: string;
  address: string;
  city: string;
  province: string;
  postal_code: string;
  country: string;
  notes: string;
}

const EditOwnershipEntityModal: React.FC<EditOwnershipEntityModalProps> = ({
  isOpen,
  onClose,
  onSuccess,
  entity,
}) => {
  const [formData, setFormData] = useState<FormData>({
    entity_type: '',
    name: '',
    legal_name: '',
    tax_id: '',
    contact_name: '',
    contact_email: '',
    contact_phone: '',
    address: '',
    city: '',
    province: '',
    postal_code: '',
    country: 'Canada',
    notes: '',
  });

  const [errors, setErrors] = useState<Record<string, string>>({});
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [showContactInfo, setShowContactInfo] = useState(false);
  const [showAddress, setShowAddress] = useState(false);

  // Load entity data when modal opens or entity changes
  useEffect(() => {
    if (isOpen && entity) {
      setFormData({
        entity_type: entity.entity_type,
        name: entity.name,
        legal_name: entity.legal_name || '',
        tax_id: entity.tax_id || '',
        contact_name: entity.contact_name || '',
        contact_email: entity.contact_email || '',
        contact_phone: entity.contact_phone || '',
        address: entity.address || '',
        city: entity.city || '',
        province: entity.province || '',
        postal_code: entity.postal_code || '',
        country: entity.country || 'Canada',
        notes: entity.notes || '',
      });
      setErrors({});
      // Auto-expand sections if they have data
      setShowContactInfo(!!(entity.contact_email || entity.contact_phone || entity.contact_name));
      setShowAddress(!!(entity.address || entity.city || entity.province));
    }
  }, [isOpen, entity]);

  const validateForm = (): boolean => {
    const newErrors: Record<string, string> = {};

    // Required fields
    if (!formData.entity_type) {
      newErrors.entity_type = 'Entity type is required';
    }

    if (!formData.name.trim()) {
      newErrors.name = 'Name is required';
    } else if (formData.name.trim().length < 1) {
      newErrors.name = 'Name must be at least 1 character';
    } else if (formData.name.trim().length > 255) {
      newErrors.name = 'Name must not exceed 255 characters';
    }

    // Optional field validations
    if (formData.legal_name && formData.legal_name.trim().length > 255) {
      newErrors.legal_name = 'Legal name must not exceed 255 characters';
    }

    if (formData.tax_id && formData.tax_id.trim().length > 100) {
      newErrors.tax_id = 'Tax ID must not exceed 100 characters';
    }

    // Email validation (optional but must be valid if provided)
    if (formData.contact_email && formData.contact_email.trim()) {
      const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
      if (!emailRegex.test(formData.contact_email)) {
        newErrors.contact_email = 'Invalid email format';
      }
    }

    // Phone validation (optional but must be valid if provided)
    if (formData.contact_phone && formData.contact_phone.trim()) {
      const phoneDigits = formData.contact_phone.replace(/\D/g, '');
      if (phoneDigits.length < 10 || phoneDigits.length > 15) {
        newErrors.contact_phone = 'Phone number must contain 10-15 digits';
      }
    }

    // Notes length validation
    if (formData.notes && formData.notes.length > 2000) {
      newErrors.notes = 'Notes must not exceed 2000 characters';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!entity) return;

    if (!validateForm()) {
      Sentry.logger.debug('Ownership entity form validation failed', {
        errorCount: Object.keys(errors).length,
      });
      return;
    }

    setIsSubmitting(true);

    try {
      await Sentry.startSpan(
        {
          op: 'ownership.entity.update',
          name: 'Update Ownership Entity',
        },
        async (span) => {
          span.setAttribute('entityId', entity.id);
          span.setAttribute('entityType', formData.entity_type);
          span.setAttribute('entityName', formData.name);

          Sentry.logger.debug('Updating ownership entity', {
            entityId: entity.id,
            entityType: formData.entity_type,
          });

          // Prepare data for the update payload.
          // All fields are included to allow clearing existing values.
          const entityData = {
            entity_type: formData.entity_type as EntityType,
            name: formData.name.trim(),
            legal_name: formData.legal_name.trim() || undefined,
            tax_id: formData.tax_id.trim() || undefined,
            contact_name: formData.contact_name.trim() || undefined,
            contact_email: formData.contact_email.trim() || undefined,
            contact_phone: formData.contact_phone.trim() || undefined,
            address: formData.address.trim() || undefined,
            city: formData.city.trim() || undefined,
            province: formData.province.trim() || undefined,
            postal_code: formData.postal_code.trim() || undefined,
            country: formData.country.trim() || undefined,
            notes: formData.notes.trim() || undefined,
          };

          const updatedEntity = await updateOwnershipEntity(entity.id, entityData);

          Sentry.logger.info('Ownership entity updated successfully', {
            entityId: updatedEntity.id,
            entityType: updatedEntity.entity_type,
            entityName: updatedEntity.name,
          });

          toast.success(`Ownership entity "${updatedEntity.name}" updated successfully`);
          onSuccess(updatedEntity);
          onClose();
        }
      );
    } catch (error) {
      console.error('Failed to update ownership entity:', error);
      Sentry.captureException(error, {
        tags: {
          component: 'EditOwnershipEntityModal',
          action: 'update_entity',
          feature: 'ownership_management',
        },
        contexts: {
          business: {
            entityId: entity.id,
            entityType: formData.entity_type,
            userAction: 'edit_from_settings',
          },
        },
      });
      setErrors({ submit: 'Failed to update ownership entity. Please try again.' });
      toast.error('Failed to update ownership entity');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleInputChange = (field: keyof FormData, value: string) => {
    setFormData(prev => ({ ...prev, [field]: value }));
    // Clear error for this field when user starts typing
    if (errors[field]) {
      setErrors(prev => {
        const newErrors = { ...prev };
        delete newErrors[field];
        return newErrors;
      });
    }
  };

  if (!entity) return null;

  return (
    <Dialog.Root open={isOpen} onOpenChange={onClose}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50">
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="fixed inset-0"
          />
        </Dialog.Overlay>

        <Dialog.Content className="fixed left-[50%] top-[50%] translate-x-[-50%] translate-y-[-50%] z-50">
          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 20 }}
            transition={{ duration: 0.3, type: 'spring', stiffness: 300, damping: 30 }}
            className="w-[90vw] max-w-2xl bg-white dark:bg-gray-800 rounded-2xl shadow-2xl overflow-hidden relative flex flex-col"
            style={{ maxHeight: '90vh' }}
          >
            {/* Header */}
            <div className="relative bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 px-6 py-4 flex-shrink-0">
              <div className="flex justify-between items-center">
                <div>
                  <Dialog.Title className="text-xl font-semibold text-gray-900 dark:text-gray-100">
                    Edit Ownership Entity
                  </Dialog.Title>
                  <Dialog.Description className="text-gray-600 dark:text-gray-400 mt-0.5 text-sm">
                    Update information for {entity.name}
                  </Dialog.Description>
                </div>
                <button
                  onClick={onClose}
                  className="text-gray-400 dark:text-gray-500 hover:text-gray-600 dark:hover:text-gray-300 p-1.5 rounded-lg transition-colors"
                  disabled={isSubmitting}
                  aria-label="Close modal"
                >
                  <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
            </div>

            {/* Content */}
            <form onSubmit={handleSubmit} className="flex-1 overflow-y-auto bg-gray-50 dark:bg-gray-900">
              {errors.submit && (
                <div className="mx-6 mt-4 p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-700 text-red-700 dark:text-red-300 rounded-lg text-sm">
                  {errors.submit}
                </div>
              )}

              <div className="p-6 space-y-5">
                {/* Required Fields Section */}
                <div className="space-y-4">
                  <h3 className="text-sm font-semibold text-gray-900 dark:text-gray-100 uppercase tracking-wide">
                    Required Information
                  </h3>

                  {/* Entity Type Field */}
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                      Entity Type <span className="text-red-500">*</span>
                    </label>
                    <Select.Root 
                      value={formData.entity_type || undefined}
                      onValueChange={(value) => handleInputChange('entity_type', value)}
                    >
                      <Select.Trigger 
                        className={`w-full px-4 py-2.5 border ${
                          errors.entity_type
                            ? 'border-red-300 dark:border-red-600'
                            : 'border-gray-200 dark:border-gray-600'
                        } rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-transparent transition-all bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 flex items-center justify-between hover:border-gray-300 dark:hover:border-gray-500`}
                      >
                        <Select.Value placeholder="Select entity type" />
                        <Select.Icon>
                          <ChevronDown className="h-4 w-4 text-gray-500 dark:text-gray-400" />
                        </Select.Icon>
                      </Select.Trigger>
                      <Select.Portal>
                        <Select.Content 
                          className="overflow-hidden bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-600 shadow-lg z-50"
                          position="popper"
                          side="bottom"
                          align="start"
                          sideOffset={4}
                        >
                          <Select.Viewport className="p-1">
                            {ENTITY_TYPES.map((type) => (
                              <Select.Item
                                key={type.value}
                                value={type.value}
                                className="relative flex items-center px-8 py-2 text-sm text-gray-900 dark:text-gray-100 rounded cursor-pointer hover:bg-green-50 dark:hover:bg-green-900/20 focus:bg-green-50 dark:focus:bg-green-900/20 outline-none select-none data-[state=checked]:bg-green-50 dark:data-[state=checked]:bg-green-900/30"
                              >
                                <Select.ItemText>{type.label}</Select.ItemText>
                                <Select.ItemIndicator className="absolute left-2 inline-flex items-center">
                                  <CheckCircle className="h-4 w-4 text-green-600 dark:text-green-400" />
                                </Select.ItemIndicator>
                              </Select.Item>
                            ))}
                          </Select.Viewport>
                        </Select.Content>
                      </Select.Portal>
                    </Select.Root>
                    {errors.entity_type && (
                      <p className="mt-1 text-sm text-red-600 dark:text-red-400">{errors.entity_type}</p>
                    )}
                  </div>

                  {/* Name Field */}
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                      Name <span className="text-red-500">*</span>
                    </label>
                    <input
                      type="text"
                      value={formData.name}
                      onChange={(e) => handleInputChange('name', e.target.value)}
                      placeholder="e.g., Maple Properties LLC"
                      className={`w-full px-4 py-2.5 border ${
                        errors.name
                          ? 'border-red-300 dark:border-red-600'
                          : 'border-gray-200 dark:border-gray-600'
                      } rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-transparent transition-all bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100`}
                    />
                    {errors.name && (
                      <p className="mt-1 text-sm text-red-600 dark:text-red-400">{errors.name}</p>
                    )}
                    <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
                      Display name for this ownership entity
                    </p>
                  </div>
                </div>

                {/* Optional Fields Section */}
                <div className="space-y-4 pt-4 border-t border-gray-200 dark:border-gray-700">
                  <h3 className="text-sm font-semibold text-gray-900 dark:text-gray-100 uppercase tracking-wide">
                    Additional Information <span className="text-gray-400 text-xs font-normal">(Optional)</span>
                  </h3>

                  {/* Legal Name Field */}
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                      Legal Name
                    </label>
                    <input
                      type="text"
                      value={formData.legal_name}
                      onChange={(e) => handleInputChange('legal_name', e.target.value)}
                      placeholder="Legal or registered name"
                      className={`w-full px-4 py-2.5 border ${
                        errors.legal_name
                          ? 'border-red-300 dark:border-red-600'
                          : 'border-gray-200 dark:border-gray-600'
                      } rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-transparent transition-all bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100`}
                    />
                    {errors.legal_name && (
                      <p className="mt-1 text-sm text-red-600 dark:text-red-400">{errors.legal_name}</p>
                    )}
                  </div>

                  {/* Tax ID Field */}
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                      Tax ID / EIN
                    </label>
                    <input
                      type="text"
                      value={formData.tax_id}
                      onChange={(e) => handleInputChange('tax_id', e.target.value)}
                      placeholder="Tax identification number"
                      className={`w-full px-4 py-2.5 border ${
                        errors.tax_id
                          ? 'border-red-300 dark:border-red-600'
                          : 'border-gray-200 dark:border-gray-600'
                      } rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-transparent transition-all bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100`}
                    />
                    {errors.tax_id && (
                      <p className="mt-1 text-sm text-red-600 dark:text-red-400">{errors.tax_id}</p>
                    )}
                  </div>
                </div>

                {/* Contact Information Section */}
                <div className="space-y-4 pt-4 border-t border-gray-200 dark:border-gray-700">
                  <button
                    type="button"
                    onClick={() => setShowContactInfo(!showContactInfo)}
                    className="flex items-center justify-between w-full text-left"
                  >
                    <h3 className="text-sm font-semibold text-gray-900 dark:text-gray-100 uppercase tracking-wide">
                      Contact Information <span className="text-gray-400 text-xs font-normal">(Optional)</span>
                    </h3>
                    <svg
                      className={`h-5 w-5 text-gray-500 transition-transform ${showContactInfo ? 'rotate-180' : ''}`}
                      fill="none"
                      viewBox="0 0 24 24"
                      stroke="currentColor"
                    >
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                    </svg>
                  </button>

                  {showContactInfo && (
                    <div className="space-y-4 pl-4">
                      {/* Contact Name */}
                      <div>
                        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                          Contact Name
                        </label>
                        <input
                          type="text"
                          value={formData.contact_name}
                          onChange={(e) => handleInputChange('contact_name', e.target.value)}
                          placeholder="Primary contact person"
                          className="w-full px-4 py-2.5 border border-gray-200 dark:border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-transparent transition-all bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
                        />
                      </div>

                      {/* Contact Email */}
                      <div>
                        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                          Contact Email
                        </label>
                        <input
                          type="email"
                          value={formData.contact_email}
                          onChange={(e) => handleInputChange('contact_email', e.target.value)}
                          placeholder="contact@example.com"
                          className={`w-full px-4 py-2.5 border ${
                            errors.contact_email
                              ? 'border-red-300 dark:border-red-600'
                              : 'border-gray-200 dark:border-gray-600'
                          } rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-transparent transition-all bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100`}
                        />
                        {errors.contact_email && (
                          <p className="mt-1 text-sm text-red-600 dark:text-red-400">{errors.contact_email}</p>
                        )}
                      </div>

                      {/* Contact Phone */}
                      <div>
                        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                          Contact Phone
                        </label>
                        <input
                          type="tel"
                          value={formData.contact_phone}
                          onChange={(e) => handleInputChange('contact_phone', e.target.value)}
                          placeholder="+1 (555) 123-4567"
                          className={`w-full px-4 py-2.5 border ${
                            errors.contact_phone
                              ? 'border-red-300 dark:border-red-600'
                              : 'border-gray-200 dark:border-gray-600'
                          } rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-transparent transition-all bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100`}
                        />
                        {errors.contact_phone && (
                          <p className="mt-1 text-sm text-red-600 dark:text-red-400">{errors.contact_phone}</p>
                        )}
                      </div>
                    </div>
                  )}
                </div>

                {/* Address Section */}
                <div className="space-y-4 pt-4 border-t border-gray-200 dark:border-gray-700">
                  <button
                    type="button"
                    onClick={() => setShowAddress(!showAddress)}
                    className="flex items-center justify-between w-full text-left"
                  >
                    <h3 className="text-sm font-semibold text-gray-900 dark:text-gray-100 uppercase tracking-wide">
                      Address <span className="text-gray-400 text-xs font-normal">(Optional)</span>
                    </h3>
                    <svg
                      className={`h-5 w-5 text-gray-500 transition-transform ${showAddress ? 'rotate-180' : ''}`}
                      fill="none"
                      viewBox="0 0 24 24"
                      stroke="currentColor"
                    >
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                    </svg>
                  </button>

                  {showAddress && (
                    <div className="space-y-4 pl-4">
                      {/* Street Address */}
                      <div>
                        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                          Street Address
                        </label>
                        <input
                          type="text"
                          value={formData.address}
                          onChange={(e) => handleInputChange('address', e.target.value)}
                          placeholder="123 Main Street"
                          className="w-full px-4 py-2.5 border border-gray-200 dark:border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-transparent transition-all bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
                        />
                      </div>

                      {/* City & Province */}
                      <div className="grid grid-cols-2 gap-4">
                        <div>
                          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                            City
                          </label>
                          <input
                            type="text"
                            value={formData.city}
                            onChange={(e) => handleInputChange('city', e.target.value)}
                            placeholder="Montreal"
                            className="w-full px-4 py-2.5 border border-gray-200 dark:border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-transparent transition-all bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
                          />
                        </div>
                        <div>
                          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                            Province
                          </label>
                          <input
                            type="text"
                            value={formData.province}
                            onChange={(e) => handleInputChange('province', e.target.value)}
                            placeholder="QC"
                            className="w-full px-4 py-2.5 border border-gray-200 dark:border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-transparent transition-all bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
                          />
                        </div>
                      </div>

                      {/* Postal Code & Country */}
                      <div className="grid grid-cols-2 gap-4">
                        <div>
                          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                            Postal Code
                          </label>
                          <input
                            type="text"
                            value={formData.postal_code}
                            onChange={(e) => handleInputChange('postal_code', e.target.value)}
                            placeholder="H3A 1A1"
                            className="w-full px-4 py-2.5 border border-gray-200 dark:border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-transparent transition-all bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
                          />
                        </div>
                        <div>
                          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                            Country
                          </label>
                          <input
                            type="text"
                            value={formData.country}
                            onChange={(e) => handleInputChange('country', e.target.value)}
                            placeholder="Canada"
                            className="w-full px-4 py-2.5 border border-gray-200 dark:border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-transparent transition-all bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
                          />
                        </div>
                      </div>
                    </div>
                  )}
                </div>

                {/* Notes Section */}
                <div className="space-y-4 pt-4 border-t border-gray-200 dark:border-gray-700">
                  <h3 className="text-sm font-semibold text-gray-900 dark:text-gray-100 uppercase tracking-wide">
                    Notes <span className="text-gray-400 text-xs font-normal">(Optional)</span>
                  </h3>
                  <div>
                    <textarea
                      value={formData.notes}
                      onChange={(e) => handleInputChange('notes', e.target.value)}
                      placeholder="Additional information about this ownership entity..."
                      rows={3}
                      className={`w-full px-4 py-2.5 border ${
                        errors.notes
                          ? 'border-red-300 dark:border-red-600'
                          : 'border-gray-200 dark:border-gray-600'
                      } rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-transparent transition-all bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 resize-none`}
                    />
                    {errors.notes && (
                      <p className="mt-1 text-sm text-red-600 dark:text-red-400">{errors.notes}</p>
                    )}
                    <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
                      {formData.notes.length} / 2000 characters
                    </p>
                  </div>
                </div>
              </div>
            </form>

            {/* Footer */}
            <div className="px-6 py-4 bg-gray-50 dark:bg-gray-900 border-t border-gray-200 dark:border-gray-700 flex-shrink-0">
              <div className="flex justify-end gap-3">
                <button
                  type="button"
                  onClick={onClose}
                  className="px-4 py-2.5 border border-gray-300 dark:border-gray-600 rounded-lg text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-700 hover:bg-gray-50 dark:hover:bg-gray-600 transition-all text-sm font-medium"
                  disabled={isSubmitting}
                >
                  Cancel
                </button>
                <button
                  onClick={handleSubmit}
                  className="px-5 py-2.5 bg-green-600 text-white rounded-lg hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-green-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed transition-all text-sm font-medium flex items-center gap-2 min-w-[140px] justify-center"
                  disabled={isSubmitting}
                >
                  {isSubmitting ? (
                    <>
                      <svg className="animate-spin h-4 w-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                      </svg>
                      Saving...
                    </>
                  ) : (
                    'Save Changes'
                  )}
                </button>
              </div>
            </div>
          </motion.div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
};

export default EditOwnershipEntityModal;

