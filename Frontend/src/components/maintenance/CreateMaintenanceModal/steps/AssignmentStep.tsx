import React from 'react';
import * as Select from '@radix-ui/react-select';
import { ChevronDown, Check } from 'lucide-react';
import type { MaintenanceFormData } from '../../../../types/tenant';
import type { VendorContact } from '../../../../types/vendor';

interface AssignmentStepProps {
  formData: MaintenanceFormData;
  errors: Record<string, string>;
  vendors: VendorContact[];
  onUpdateField: <K extends keyof MaintenanceFormData>(field: K, value: MaintenanceFormData[K]) => void;
  isLoadingVendors?: boolean;
}

const AssignmentStep: React.FC<AssignmentStepProps> = ({
  formData,
  errors,
  vendors,
  onUpdateField,
  isLoadingVendors,
}) => {
  // Ensure selected vendor remains valid when vendor list changes
  const selectedVendorExists =
    !!formData.vendor_id && vendors.some(v => v.id === Number(formData.vendor_id));
  React.useEffect(() => {
    if (formData.vendor_id && !selectedVendorExists) {
      onUpdateField('vendor_id', '');
    }
  }, [formData.vendor_id, selectedVendorExists, onUpdateField]);

  const getInputClassName = (fieldName: string): string => {
    const baseClasses = "w-full px-4 py-2.5 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all bg-white dark:bg-gray-700 dark:text-gray-100 text-sm";
    return errors[fieldName]
      ? `${baseClasses} border-red-300 dark:border-red-500 bg-red-50 dark:bg-red-900/20 focus:ring-red-100`
      : `${baseClasses} border-gray-200 dark:border-gray-600 hover:border-gray-400 dark:hover:border-gray-500`;
  };

  return (
    <div className="space-y-4 p-6">
      {/* Vendor Assignment Section */}
      <div className="bg-white dark:bg-gray-800 rounded-lg p-4 border border-gray-200 dark:border-gray-700 transition-colors duration-300">
        <div className="flex items-center mb-3">
          <div className="w-8 h-8 bg-green-50 dark:bg-green-900/20 rounded-lg flex items-center justify-center mr-3">
            <svg className="w-4 h-4 text-green-600 dark:text-green-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
            </svg>
          </div>
          <div>
            <h3 className="text-base font-semibold text-gray-900 dark:text-gray-100">Assign Vendor</h3>
            <p className="text-xs text-gray-500 dark:text-gray-400">Choose a vendor to handle this request</p>
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
            Vendor
          </label>
          <Select.Root
            value={formData.vendor_id || 'NONE'}
            onValueChange={(value) => onUpdateField('vendor_id', value === 'NONE' ? '' : value)}
            disabled={isLoadingVendors}
          >
            <Select.Trigger
              className={`w-full px-4 py-2.5 pr-9 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent flex items-center justify-between transition-colors text-sm ${
                isLoadingVendors
                  ? 'bg-gray-100 dark:bg-gray-900/50 cursor-not-allowed border-gray-300 dark:border-gray-600'
                  : 'bg-white dark:bg-gray-700 border-gray-200 dark:border-gray-600 hover:border-gray-400 dark:hover:border-gray-500'
              } text-gray-900 dark:text-gray-100`}
              disabled={isLoadingVendors}
            >
              <Select.Value placeholder="Select a vendor...">
                {formData.vendor_id && vendors.find(v => v.id === Number(formData.vendor_id)) ? (() => {
                  const vendor = vendors.find(v => v.id === Number(formData.vendor_id));
                  return vendor ? `${vendor.company_name} (${vendor.trade_category})` : 'Select a vendor...';
                })() : 'Select a vendor...'}
              </Select.Value>
              <ChevronDown className="h-4 w-4 text-gray-500 dark:text-gray-400 ml-2 flex-shrink-0" />
            </Select.Trigger>
            <Select.Portal>
              <Select.Content className="overflow-hidden bg-white dark:bg-gray-800 rounded-lg shadow-lg border border-gray-200 dark:border-gray-700 z-[10001] max-h-80">
                <Select.Viewport className="p-1">
                  <Select.Item
                    value="NONE"
                    className="relative flex items-center px-8 py-2 text-sm text-gray-900 dark:text-gray-100 rounded cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-700 focus:bg-gray-100 dark:focus:bg-gray-700 outline-none"
                  >
                    <Select.ItemText>No vendor assigned</Select.ItemText>
                    <Select.ItemIndicator className="absolute left-2 inline-flex items-center">
                      <Check className="h-4 w-4" />
                    </Select.ItemIndicator>
                  </Select.Item>
                  {vendors.length === 0 && !isLoadingVendors && (
                    <div className="px-8 py-2 text-sm text-gray-500 dark:text-gray-400">
                      No vendors available. Add vendors in the Vendors page first.
                    </div>
                  )}
                  {vendors.map((vendor) => (
                    <Select.Item
                      key={vendor.id}
                      value={String(vendor.id)}
                      className="relative flex items-center px-8 py-2 text-sm text-gray-900 dark:text-gray-100 rounded cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-700 focus:bg-gray-100 dark:focus:bg-gray-700 outline-none"
                    >
                      <Select.ItemText>
                        <div>
                          <div className="font-medium">{vendor.company_name}</div>
                          <div className="text-xs text-gray-500 dark:text-gray-400">
                            {vendor.trade_category} • {vendor.phone}
                          </div>
                        </div>
                      </Select.ItemText>
                      <Select.ItemIndicator className="absolute left-2 inline-flex items-center">
                        <Check className="h-4 w-4" />
                      </Select.ItemIndicator>
                    </Select.Item>
                  ))}
                </Select.Viewport>
              </Select.Content>
            </Select.Portal>
          </Select.Root>
          <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
            Vendor will be notified via email and SMS when assigned
          </p>
        </div>
      </div>

      {/* Priority & Status Section */}
      <div className="bg-white dark:bg-gray-800 rounded-lg p-4 border border-gray-200 dark:border-gray-700 transition-colors duration-300">
        <div className="flex items-center mb-3">
          <div className="w-8 h-8 bg-orange-50 dark:bg-orange-900/20 rounded-lg flex items-center justify-center mr-3">
            <svg className="w-4 h-4 text-orange-600 dark:text-orange-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
          </div>
          <div>
            <h3 className="text-base font-semibold text-gray-900 dark:text-gray-100">Priority & Status</h3>
            <p className="text-xs text-gray-500 dark:text-gray-400">Set the urgency and current status</p>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Priority */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Priority
            </label>
            <select
              value={formData.priority || ''}
              onChange={(e) => onUpdateField('priority', e.target.value as 'Low' | 'Medium' | 'High')}
              className={getInputClassName('priority')}
            >
              <option value="Low">Low</option>
              <option value="Medium">Medium</option>
              <option value="High">High</option>
            </select>
          </div>

          {/* Status */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Status
            </label>
            <select
              value={formData.status || ''}
              onChange={(e) => onUpdateField('status', e.target.value as any)}
              className={getInputClassName('status')}
            >
              <option value="Pending">Pending</option>
              <option value="In Progress">In Progress</option>
              <option value="Scheduled">Scheduled</option>
              <option value="Completed">Completed</option>
              <option value="Cancelled">Cancelled</option>
            </select>
          </div>
        </div>
      </div>

      {/* Requested Timeline Section */}
      <div className="bg-white dark:bg-gray-800 rounded-lg p-4 border border-gray-200 dark:border-gray-700 transition-colors duration-300">
        <div className="flex items-center mb-3">
          <div className="w-8 h-8 bg-blue-50 dark:bg-blue-900/20 rounded-lg flex items-center justify-center mr-3">
            <svg className="w-4 h-4 text-blue-600 dark:text-blue-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
            </svg>
          </div>
          <div>
            <h3 className="text-base font-semibold text-gray-900 dark:text-gray-100">Scheduling</h3>
            <p className="text-xs text-gray-500 dark:text-gray-400">When should this repair be scheduled?</p>
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
            Scheduled Date
          </label>
          <input
            type="date"
            value={formData.scheduled_date || ''}
            onChange={(e) => onUpdateField('scheduled_date', e.target.value)}
            className={getInputClassName('scheduled_date')}
          />
          {errors.scheduled_date && (
            <p className="mt-2 text-sm text-red-600 dark:text-red-400">{errors.scheduled_date}</p>
          )}
          <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
            Date when the repair work is scheduled
          </p>
        </div>
      </div>
    </div>
  );
};

export default AssignmentStep;

