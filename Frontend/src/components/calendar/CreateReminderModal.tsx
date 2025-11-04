/**
 * Create/Edit Reminder Modal
 * 
 * Modal for creating or editing custom calendar reminders with:
 * - Title and description
 * - Date/time selection (with all-day option)
 * - Smart property/unit/tenant dropdowns
 * - Notification settings
 * - Matches app design aesthetic
 */

import React, { useState, useEffect } from 'react';
import * as Dialog from '@radix-ui/react-dialog';
import * as Select from '@radix-ui/react-select';
import { motion } from 'framer-motion';
import { X, Calendar, Clock, Bell, MapPin, Users, Home, AlertCircle, ChevronDown, CheckCircle } from 'lucide-react';
import { createCustomReminder, updateCustomReminder, CustomReminderCreate, CustomReminderUpdate } from '../../utils/api/calendar';
import { fetchProperties } from '../../utils/api/properties';
import { fetchPropertyUnits } from '../../utils/api/units';
import { fetchTenants } from '../../utils/api/tenants';
import { toast } from 'react-toastify';

interface Property {
  id: number;
  name: string;
  address?: string;
}

interface Unit {
  id: number;
  name: string;
  property_id: number;
}

interface Tenant {
  id: number;
  first_name?: string;
  last_name?: string;
  company_name?: string;
}

interface CreateReminderModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
  editReminder?: {
    id: string;
    title: string;
    description?: string;
    reminder_date: string;
    all_day: boolean;
    property_id?: number;
    unit_id?: number;
    tenant_id?: number;
    notify_before_hours: number;
  };
}

export const CreateReminderModal: React.FC<CreateReminderModalProps> = ({
  isOpen,
  onClose,
  onSuccess,
  editReminder,
}) => {
  const [formData, setFormData] = useState({
    title: '',
    description: '',
    reminder_date: '',
    reminder_time: '09:00',
    all_day: false,
    property_id: null as number | null,
    unit_id: null as number | null,
    tenant_id: null as number | null,
    notify_before_hours: 24,
  });
  const [loading, setLoading] = useState(false);
  const [loadingData, setLoadingData] = useState(false);
  const [errors, setErrors] = useState<Record<string, string>>({});
  
  // Data state
  const [properties, setProperties] = useState<Property[]>([]);
  const [units, setUnits] = useState<Unit[]>([]);
  const [tenants, setTenants] = useState<Tenant[]>([]);
  
  // Filtered units based on selected property
  const filteredUnits = formData.property_id
    ? units.filter(unit => unit.property_id === formData.property_id)
    : units;

  // Load data when modal opens
  useEffect(() => {
    if (isOpen) {
      loadInitialData();
      
    if (editReminder) {
        const reminderDate = new Date(editReminder.reminder_date);
        const dateStr = reminderDate.toISOString().split('T')[0];
        const timeStr = reminderDate.toTimeString().slice(0, 5);

      setFormData({
        title: editReminder.title,
        description: editReminder.description || '',
        reminder_date: dateStr,
          reminder_time: editReminder.all_day ? '09:00' : timeStr,
        all_day: editReminder.all_day,
        property_id: editReminder.property_id ?? null,
        unit_id: editReminder.unit_id ?? null,
        tenant_id: editReminder.tenant_id ?? null,
          notify_before_hours: editReminder.notify_before_hours,
      });
    } else {
      // Reset form for new reminder
      setFormData({
        title: '',
        description: '',
        reminder_date: '',
          reminder_time: '09:00',
          all_day: false,
        property_id: null,
        unit_id: null,
        tenant_id: null,
          notify_before_hours: 24,
      });
      }
      setErrors({});
    }
  }, [editReminder, isOpen]);

  const loadInitialData = async () => {
    setLoadingData(true);
    try {
      const [propertiesData, tenantsData] = await Promise.all([
        fetchProperties(),
        fetchTenants(),
      ]);
      
      setProperties(propertiesData || []);
      setTenants(tenantsData || []);
      
      // Load all units from all properties
      if (propertiesData && propertiesData.length > 0) {
        const allUnits: Unit[] = [];
        for (const property of propertiesData) {
          try {
            const propertyUnits = await fetchPropertyUnits(property.id);
            if (propertyUnits && propertyUnits.length > 0) {
              allUnits.push(...propertyUnits.map((u: any) => ({
                id: u.id,
                name: u.name,
                property_id: property.id
              })));
            }
          } catch (err) {
            console.error(`Error loading units for property ${property.id}:`, err);
          }
        }
        setUnits(allUnits);
      }
    } catch (error) {
      console.error('Error loading data:', error);
      toast.error('Failed to load properties and tenants');
    } finally {
      setLoadingData(false);
    }
  };
  
  // Reset unit selection when property changes
  const handlePropertyChange = (value: string) => {
    const propertyId = value ? parseInt(value) : null;
    setFormData({
      ...formData,
      property_id: propertyId,
      unit_id: null // Reset unit when property changes
    });
  };
  
  const getTenantName = (tenant: Tenant): string => {
    if (tenant.company_name) {
      return tenant.company_name;
    }
    return `${tenant.first_name || ''} ${tenant.last_name || ''}`.trim() || 'Unnamed Tenant';
  };

  const validateForm = (): boolean => {
    const newErrors: Record<string, string> = {};

    if (!formData.title.trim()) {
      newErrors.title = 'Title is required';
    }

    if (!formData.reminder_date) {
      newErrors.reminder_date = 'Date is required';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!validateForm()) {
      return;
    }

    setLoading(true);

    try {
      // Combine date and time into ISO datetime
      // For all-day events, use noon local time to avoid timezone edge cases
      // (midnight UTC can display on wrong day for negative UTC timezones)
      // For timed events, convert local time to UTC
      const dateTime = formData.all_day
        ? new Date(`${formData.reminder_date}T12:00:00`).toISOString()
        : (() => {
            // Create Date object from local date/time (browser timezone)
            const localDateTime = new Date(`${formData.reminder_date}T${formData.reminder_time}`);
            // Convert to ISO string (automatically converts to UTC)
            return localDateTime.toISOString();
          })();

      if (editReminder) {
        // Update existing reminder
        const updateData: CustomReminderUpdate = {
        title: formData.title,
        description: formData.description || undefined,
          reminder_date: dateTime,
        all_day: formData.all_day,
        property_id: formData.property_id ?? undefined,
        unit_id: formData.unit_id ?? undefined,
        tenant_id: formData.tenant_id ?? undefined,
          notify_before_hours: formData.notify_before_hours,
      };

        await updateCustomReminder(editReminder.id, updateData);
        toast.success('Reminder updated successfully');
      } else {
        // Create new reminder
        const createData: CustomReminderCreate = {
          title: formData.title,
          description: formData.description || undefined,
          reminder_date: dateTime,
          all_day: formData.all_day,
          property_id: formData.property_id ?? undefined,
          unit_id: formData.unit_id ?? undefined,
          tenant_id: formData.tenant_id ?? undefined,
          notify_before_hours: formData.notify_before_hours,
        };

        await createCustomReminder(createData);
        toast.success('Reminder created successfully');
      }

      onSuccess();
      onClose();
    } catch (error: any) {
      console.error('Error saving reminder:', error);
      toast.error(error.message || 'Failed to save reminder');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Dialog.Root open={isOpen} onOpenChange={onClose}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 bg-black/60 dark:bg-black/80 backdrop-blur-sm z-50">
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
            className="w-[90vw] max-w-3xl bg-white dark:bg-gray-800 rounded-2xl shadow-2xl overflow-hidden relative flex flex-col"
            style={{ maxHeight: '90vh' }}
          >
          {/* Header */}
            <div className="relative bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 px-6 py-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-3">
                  <div className="p-2 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
                    <Bell className="h-5 w-5 text-blue-600 dark:text-blue-400" />
                  </div>
                  <div>
                    <Dialog.Title className="text-lg font-semibold text-gray-900 dark:text-gray-100">
              {editReminder ? 'Edit Reminder' : 'Create Reminder'}
                    </Dialog.Title>
                    <Dialog.Description className="text-sm text-gray-500 dark:text-gray-400 mt-0.5">
                      Set up a custom calendar reminder for your property
                    </Dialog.Description>
                  </div>
                </div>
                <Dialog.Close asChild>
            <button
                    className="p-1.5 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors disabled:opacity-50"
                    disabled={loading}
                    aria-label="Close"
            >
                    <X className="h-5 w-5 text-gray-500 dark:text-gray-400" />
            </button>
                </Dialog.Close>
              </div>
          </div>

            {/* Content */}
            <motion.div
              className="overflow-y-auto p-6 bg-gray-50/50 dark:bg-gray-800/50"
              style={{ maxHeight: '65vh' }}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.4, delay: 0.1 }}
            >
              {loadingData ? (
                <motion.div
                  className="flex flex-col items-center justify-center py-12"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                >
                  <div className="w-8 h-8 border-2 border-blue-200 dark:border-blue-700 rounded-full animate-spin border-t-blue-600 dark:border-t-blue-400"></div>
                  <p className="text-blue-700 dark:text-blue-300 font-medium mt-3 text-sm">Loading data...</p>
                </motion.div>
              ) : (
                <form onSubmit={handleSubmit} className="space-y-5">
            {/* Title */}
            <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Title <span className="text-red-500">*</span>
              </label>
              <input
                type="text"
                value={formData.title}
                onChange={(e) => setFormData({ ...formData, title: e.target.value })}
                      className={`w-full px-4 py-2.5 border rounded-lg transition-colors focus:ring-2 focus:ring-blue-500 focus:border-transparent dark:bg-gray-700 dark:text-white ${
                        errors.title 
                          ? 'border-red-300 dark:border-red-500' 
                          : 'border-gray-300 dark:border-gray-600'
                      }`}
                      placeholder="e.g., Property inspection, Rent review meeting"
                    />
                    {errors.title && (
                      <p className="mt-1.5 text-sm text-red-600 dark:text-red-400 flex items-center">
                        <AlertCircle className="w-4 h-4 mr-1" />
                        {errors.title}
                      </p>
                    )}
            </div>

            {/* Description */}
            <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Description
              </label>
              <textarea
                value={formData.description}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                rows={3}
                      className="w-full px-4 py-2.5 border border-gray-300 dark:border-gray-600 rounded-lg transition-colors focus:ring-2 focus:ring-blue-500 focus:border-transparent dark:bg-gray-700 dark:text-white resize-none"
                      placeholder="Add any additional details or notes..."
              />
            </div>

            {/* Date and Time */}
            <div className="grid grid-cols-2 gap-4">
              <div>
                      <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                        <Calendar className="w-4 h-4 inline mr-1.5" />
                  Date <span className="text-red-500">*</span>
                </label>
                  <input
                    type="date"
                    value={formData.reminder_date}
                    onChange={(e) => setFormData({ ...formData, reminder_date: e.target.value })}
                        className={`w-full px-4 py-2.5 border rounded-lg transition-colors focus:ring-2 focus:ring-blue-500 focus:border-transparent dark:bg-gray-700 dark:text-white ${
                          errors.reminder_date 
                            ? 'border-red-300 dark:border-red-500' 
                            : 'border-gray-300 dark:border-gray-600'
                        }`}
                      />
                      {errors.reminder_date && (
                        <p className="mt-1.5 text-sm text-red-600 dark:text-red-400 flex items-center">
                          <AlertCircle className="w-4 h-4 mr-1" />
                          {errors.reminder_date}
                        </p>
                      )}
              </div>

              <div>
                      <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                        <Clock className="w-4 h-4 inline mr-1.5" />
                  Time
                </label>
                  <input
                    type="time"
                    value={formData.reminder_time}
                    onChange={(e) => setFormData({ ...formData, reminder_time: e.target.value })}
                    disabled={formData.all_day}
                        className="w-full px-4 py-2.5 border border-gray-300 dark:border-gray-600 rounded-lg transition-colors focus:ring-2 focus:ring-blue-500 focus:border-transparent dark:bg-gray-700 dark:text-white disabled:bg-gray-100 dark:disabled:bg-gray-600 disabled:cursor-not-allowed"
                  />
              </div>
            </div>

                  {/* All Day */}
            <div className="flex items-center">
                    <label className="flex items-center space-x-2.5 cursor-pointer">
              <input
                type="checkbox"
                checked={formData.all_day}
                onChange={(e) => setFormData({ ...formData, all_day: e.target.checked })}
                        className="w-4 h-4 text-blue-600 border-gray-300 dark:border-gray-600 rounded focus:ring-blue-500 dark:bg-gray-700"
              />
                      <span className="text-sm text-gray-700 dark:text-gray-300 font-medium">All day event</span>
              </label>
            </div>

                  {/* Notification */}
            <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                      <Bell className="w-4 h-4 inline mr-1.5" />
                Notify me before
              </label>
                    <Select.Root
                      value={formData.notify_before_hours.toString()}
                      onValueChange={(value) => setFormData({ ...formData, notify_before_hours: parseInt(value) })}
                    >
                      <Select.Trigger className="w-full px-4 py-2.5 border border-gray-300 dark:border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 flex items-center justify-between hover:border-gray-400 dark:hover:border-gray-500">
                        <Select.Value />
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
                            <Select.Item
                              value="0"
                              className="relative flex items-center px-8 py-2 text-sm text-gray-900 dark:text-gray-100 rounded cursor-pointer hover:bg-blue-50 dark:hover:bg-blue-900/20 focus:bg-blue-50 dark:focus:bg-blue-900/20 outline-none select-none data-[state=checked]:bg-blue-50 dark:data-[state=checked]:bg-blue-900/30"
                            >
                              <Select.ItemText>At time of event</Select.ItemText>
                              <Select.ItemIndicator className="absolute left-2 inline-flex items-center">
                                <CheckCircle className="h-4 w-4 text-blue-600 dark:text-blue-400" />
                              </Select.ItemIndicator>
                            </Select.Item>
                            <Select.Item
                              value="1"
                              className="relative flex items-center px-8 py-2 text-sm text-gray-900 dark:text-gray-100 rounded cursor-pointer hover:bg-blue-50 dark:hover:bg-blue-900/20 focus:bg-blue-50 dark:focus:bg-blue-900/20 outline-none select-none data-[state=checked]:bg-blue-50 dark:data-[state=checked]:bg-blue-900/30"
                            >
                              <Select.ItemText>1 hour before</Select.ItemText>
                              <Select.ItemIndicator className="absolute left-2 inline-flex items-center">
                                <CheckCircle className="h-4 w-4 text-blue-600 dark:text-blue-400" />
                              </Select.ItemIndicator>
                            </Select.Item>
                            <Select.Item
                              value="24"
                              className="relative flex items-center px-8 py-2 text-sm text-gray-900 dark:text-gray-100 rounded cursor-pointer hover:bg-blue-50 dark:hover:bg-blue-900/20 focus:bg-blue-50 dark:focus:bg-blue-900/20 outline-none select-none data-[state=checked]:bg-blue-50 dark:data-[state=checked]:bg-blue-900/30"
                            >
                              <Select.ItemText>1 day before</Select.ItemText>
                              <Select.ItemIndicator className="absolute left-2 inline-flex items-center">
                                <CheckCircle className="h-4 w-4 text-blue-600 dark:text-blue-400" />
                              </Select.ItemIndicator>
                            </Select.Item>
                            <Select.Item
                              value="48"
                              className="relative flex items-center px-8 py-2 text-sm text-gray-900 dark:text-gray-100 rounded cursor-pointer hover:bg-blue-50 dark:hover:bg-blue-900/20 focus:bg-blue-50 dark:focus:bg-blue-900/20 outline-none select-none data-[state=checked]:bg-blue-50 dark:data-[state=checked]:bg-blue-900/30"
                            >
                              <Select.ItemText>2 days before</Select.ItemText>
                              <Select.ItemIndicator className="absolute left-2 inline-flex items-center">
                                <CheckCircle className="h-4 w-4 text-blue-600 dark:text-blue-400" />
                              </Select.ItemIndicator>
                            </Select.Item>
                            <Select.Item
                              value="168"
                              className="relative flex items-center px-8 py-2 text-sm text-gray-900 dark:text-gray-100 rounded cursor-pointer hover:bg-blue-50 dark:hover:bg-blue-900/20 focus:bg-blue-50 dark:focus:bg-blue-900/20 outline-none select-none data-[state=checked]:bg-blue-50 dark:data-[state=checked]:bg-blue-900/30"
                            >
                              <Select.ItemText>1 week before</Select.ItemText>
                              <Select.ItemIndicator className="absolute left-2 inline-flex items-center">
                                <CheckCircle className="h-4 w-4 text-blue-600 dark:text-blue-400" />
                              </Select.ItemIndicator>
                            </Select.Item>
                          </Select.Viewport>
                        </Select.Content>
                      </Select.Portal>
                    </Select.Root>
                  </div>

                  {/* Optional Associations */}
                  <div className="border-t border-gray-200 dark:border-gray-700 pt-5 mt-2">
                    <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-4 flex items-center">
                      <MapPin className="w-4 h-4 mr-2 text-blue-600 dark:text-blue-400" />
                      Associate with (optional)
                    </h3>
                    
                    <div className="space-y-4">
                      {/* Property */}
                      <div>
                        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                          <Home className="w-4 h-4 inline mr-1.5" />
                          Property
                        </label>
                        <Select.Root
                          value={formData.property_id?.toString() || ''}
                          onValueChange={handlePropertyChange}
                        >
                          <Select.Trigger className="w-full px-4 py-2.5 border border-gray-300 dark:border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 flex items-center justify-between hover:border-gray-400 dark:hover:border-gray-500">
                            <Select.Value placeholder="Select a property..." />
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
                              <Select.Viewport className="p-1 max-h-[300px]">
                                {properties.map((property) => (
                                  <Select.Item
                                    key={property.id}
                                    value={property.id.toString()}
                                    className="relative flex items-center px-8 py-2 text-sm text-gray-900 dark:text-gray-100 rounded cursor-pointer hover:bg-blue-50 dark:hover:bg-blue-900/20 focus:bg-blue-50 dark:focus:bg-blue-900/20 outline-none select-none data-[state=checked]:bg-blue-50 dark:data-[state=checked]:bg-blue-900/30"
                                  >
                                    <Select.ItemText>
                                      {property.name} {property.address && `- ${property.address}`}
                                    </Select.ItemText>
                                    <Select.ItemIndicator className="absolute left-2 inline-flex items-center">
                                      <CheckCircle className="h-4 w-4 text-blue-600 dark:text-blue-400" />
                                    </Select.ItemIndicator>
                                  </Select.Item>
                                ))}
                              </Select.Viewport>
                            </Select.Content>
                          </Select.Portal>
                        </Select.Root>
                      </div>

                      {/* Unit */}
                      <div>
                        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                          <MapPin className="w-4 h-4 inline mr-1.5" />
                          Unit
                        </label>
                        <Select.Root
                          value={formData.unit_id?.toString() || ''}
                          onValueChange={(value) => setFormData({ ...formData, unit_id: value ? parseInt(value) : null })}
                          disabled={!formData.property_id}
                        >
                          <Select.Trigger className="w-full px-4 py-2.5 border border-gray-300 dark:border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 flex items-center justify-between hover:border-gray-400 dark:hover:border-gray-500 disabled:bg-gray-100 dark:disabled:bg-gray-600 disabled:cursor-not-allowed disabled:opacity-60">
                            <Select.Value placeholder={formData.property_id ? 'Select a unit...' : 'Select a property first'} />
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
                              <Select.Viewport className="p-1 max-h-[300px]">
                                {filteredUnits.map((unit) => (
                                  <Select.Item
                                    key={unit.id}
                                    value={unit.id.toString()}
                                    className="relative flex items-center px-8 py-2 text-sm text-gray-900 dark:text-gray-100 rounded cursor-pointer hover:bg-blue-50 dark:hover:bg-blue-900/20 focus:bg-blue-50 dark:focus:bg-blue-900/20 outline-none select-none data-[state=checked]:bg-blue-50 dark:data-[state=checked]:bg-blue-900/30"
                                  >
                                    <Select.ItemText>{unit.name}</Select.ItemText>
                                    <Select.ItemIndicator className="absolute left-2 inline-flex items-center">
                                      <CheckCircle className="h-4 w-4 text-blue-600 dark:text-blue-400" />
                                    </Select.ItemIndicator>
                                  </Select.Item>
                                ))}
                              </Select.Viewport>
                            </Select.Content>
                          </Select.Portal>
                        </Select.Root>
                        {formData.property_id && filteredUnits.length === 0 && (
                          <p className="mt-1.5 text-xs text-gray-500 dark:text-gray-400">
                            No units available for this property
                          </p>
                        )}
            </div>

                      {/* Tenant */}
                      <div>
                        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                          <Users className="w-4 h-4 inline mr-1.5" />
                          Tenant
              </label>
                        <Select.Root
                          value={formData.tenant_id?.toString() || ''}
                          onValueChange={(value) => setFormData({ ...formData, tenant_id: value ? parseInt(value) : null })}
                        >
                          <Select.Trigger className="w-full px-4 py-2.5 border border-gray-300 dark:border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 flex items-center justify-between hover:border-gray-400 dark:hover:border-gray-500">
                            <Select.Value placeholder="Select a tenant..." />
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
                              <Select.Viewport className="p-1 max-h-[300px]">
                                {tenants.map((tenant) => (
                                  <Select.Item
                                    key={tenant.id}
                                    value={tenant.id.toString()}
                                    className="relative flex items-center px-8 py-2 text-sm text-gray-900 dark:text-gray-100 rounded cursor-pointer hover:bg-blue-50 dark:hover:bg-blue-900/20 focus:bg-blue-50 dark:focus:bg-blue-900/20 outline-none select-none data-[state=checked]:bg-blue-50 dark:data-[state=checked]:bg-blue-900/30"
                                  >
                                    <Select.ItemText>{getTenantName(tenant)}</Select.ItemText>
                                    <Select.ItemIndicator className="absolute left-2 inline-flex items-center">
                                      <CheckCircle className="h-4 w-4 text-blue-600 dark:text-blue-400" />
                                    </Select.ItemIndicator>
                                  </Select.Item>
                                ))}
                              </Select.Viewport>
                            </Select.Content>
                          </Select.Portal>
                        </Select.Root>
                      </div>
                    </div>
                  </div>

                </form>
              )}
            </motion.div>

            {/* Footer */}
            <div className="border-t border-gray-200 dark:border-gray-700 px-6 py-4 flex justify-end items-center bg-white dark:bg-gray-800 flex-shrink-0">
              <div className="flex items-center space-x-3">
              <button
                type="button"
                onClick={onClose}
                disabled={loading}
                  className="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-600 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 dark:focus:ring-offset-gray-800 disabled:opacity-50 transition-colors"
              >
                Cancel
              </button>
                
              <button
                type="submit"
                  onClick={handleSubmit}
                  disabled={loading || loadingData}
                  className={`px-5 py-2 text-sm font-medium text-white rounded-lg transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 dark:focus:ring-offset-gray-800 disabled:opacity-50 disabled:cursor-not-allowed flex items-center space-x-2 ${
                    loading || loadingData
                      ? 'bg-gray-400 dark:bg-gray-600'
                      : 'bg-blue-600 dark:bg-blue-700 hover:bg-blue-700 dark:hover:bg-blue-600'
                  }`}
                >
                  {loading ? (
                    <>
                      <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                      <span>{editReminder ? 'Updating...' : 'Creating...'}</span>
                    </>
                  ) : (
                    <span>{editReminder ? 'Update Reminder' : 'Create Reminder'}</span>
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
