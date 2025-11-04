import React from 'react';
import * as Select from '@radix-ui/react-select';
import { ChevronDown, CheckCircle } from 'lucide-react';
import {
  Label,
  Input,
  TextArea,
} from '../../../ui/SharedModalComponents';
import type { Property } from '../../../../types/lease';
import type { Tenant } from '../../../../types/tenant';
import type { FormData, FieldErrors, Unit } from '../types';
import { getTenantDisplayName } from '../../../../utils/tenantUtils';

interface LeaseFormFieldsProps {
  formData: FormData;
  fieldErrors: FieldErrors;
  properties: Property[];
  availableUnits: Unit[];
  availableTenants: Tenant[];
  selectedTenant: Tenant | null;
  isLoadingUnits: boolean;
  isLoadingTenants: boolean;
  mode: 'file' | 'manual';
  initialPropertyId?: number | null;
  initialUnitId?: number | null;
  initialUnitName?: string;
  onFormChange: (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => void;
  onPropertyChange: (value: string) => void;
  onUnitChange: (value: string) => void;
  onTenantChange: (value: string) => void;
  onCreateNewTenant: () => void;
}

const getUnitDisplayName = (unit: Unit): string => {
  return unit.name || `Unit ${unit.id}`;
};

export const LeaseFormFields: React.FC<LeaseFormFieldsProps> = ({
  formData,
  fieldErrors,
  properties,
  availableUnits,
  availableTenants,
  selectedTenant,
  isLoadingUnits,
  isLoadingTenants,
  mode,
  initialPropertyId,
  initialUnitId,
  initialUnitName,
  onFormChange,
  onPropertyChange,
  onUnitChange,
  onTenantChange,
  onCreateNewTenant,
}) => {
  return (
    <div className="space-y-4">
      {/* Property Selection */}
      <div>
        <Label htmlFor="property_id" required>Property</Label>
        <Select.Root 
          value={formData.property_id} 
          onValueChange={onPropertyChange}
          disabled={!!initialPropertyId && mode === 'manual'}
        >
          <Select.Trigger 
            className={`w-full px-4 py-2.5 border ${
              fieldErrors.property_id
                ? 'border-red-300 dark:border-red-600'
                : 'border-gray-200 dark:border-gray-600'
            } rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-transparent transition-all bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 flex items-center justify-between hover:border-gray-300 dark:hover:border-gray-500 disabled:opacity-50 disabled:cursor-not-allowed`}
          >
            <Select.Value placeholder="Choose a property" />
            <Select.Icon>
              <ChevronDown className="h-4 w-4 text-gray-500 dark:text-gray-400" />
            </Select.Icon>
          </Select.Trigger>
          <Select.Portal>
            <Select.Content 
              className="overflow-hidden bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-600 shadow-lg z-[10001]"
              position="popper"
              side="bottom"
              align="start"
              sideOffset={4}
            >
              <Select.Viewport className="p-1">
                {properties.map((property) => (
                  <Select.Item
                    key={property.id}
                    value={property.id.toString()}
                    className="relative flex items-center pl-7 pr-3 py-2 text-sm text-gray-900 dark:text-gray-100 rounded cursor-pointer hover:bg-green-50 dark:hover:bg-green-900/20 focus:bg-green-50 dark:focus:bg-green-900/20 outline-none select-none data-[state=checked]:bg-green-50 dark:data-[state=checked]:bg-green-900/30"
                  >
                    <Select.ItemText>{property.name}</Select.ItemText>
                    <Select.ItemIndicator className="absolute left-1 inline-flex items-center">
                      <CheckCircle className="h-4 w-4 text-green-600 dark:text-green-400" />
                    </Select.ItemIndicator>
                  </Select.Item>
                ))}
              </Select.Viewport>
            </Select.Content>
          </Select.Portal>
        </Select.Root>
        {fieldErrors.property_id && (
          <p className="mt-1 text-sm text-red-600 dark:text-red-400">{fieldErrors.property_id}</p>
        )}
      </div>

      {/* Unit Selection */}
      <div>
        <Label htmlFor="unit_id" required={mode !== 'manual'}>Unit</Label>
        {mode === 'manual' && initialUnitId ? (
          <Input 
            value={initialUnitName} 
            disabled 
            className="bg-gray-50 dark:bg-gray-800"
          />
        ) : (
          <>
            <Select.Root 
              value={formData.unit_id} 
              onValueChange={onUnitChange}
              disabled={isLoadingUnits || !formData.property_id}
            >
              <Select.Trigger 
                className={`w-full px-4 py-2.5 border ${
                  fieldErrors.unit_id
                    ? 'border-red-300 dark:border-red-600'
                    : 'border-gray-200 dark:border-gray-600'
                } rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-transparent transition-all bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 flex items-center justify-between hover:border-gray-300 dark:hover:border-gray-500 disabled:opacity-50 disabled:cursor-not-allowed`}
              >
                <Select.Value placeholder={
                  isLoadingUnits 
                    ? "Loading units..." 
                    : !formData.property_id 
                      ? "Select property first" 
                      : availableUnits.length === 0
                        ? "No available units"
                        : "Select a unit"
                } />
                <Select.Icon>
                  {isLoadingUnits ? (
                    <svg className="animate-spin h-4 w-4 text-gray-500" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                  ) : (
                    <ChevronDown className="h-4 w-4 text-gray-500 dark:text-gray-400" />
                  )}
                </Select.Icon>
              </Select.Trigger>
              <Select.Portal>
                <Select.Content 
                  className="overflow-hidden bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-600 shadow-lg z-[10001] max-h-[300px]"
                  position="popper"
                  side="bottom"
                  align="start"
                  sideOffset={4}
                >
                  <Select.Viewport className="p-1">
                    {availableUnits.map((unit) => (
                      <Select.Item
                        key={unit.id}
                        value={unit.id.toString()}
                        className="relative flex items-center pl-7 pr-3 py-2 text-sm text-gray-900 dark:text-gray-100 rounded cursor-pointer hover:bg-green-50 dark:hover:bg-green-900/20 focus:bg-green-50 dark:focus:bg-green-900/20 outline-none select-none data-[state=checked]:bg-green-50 dark:data-[state=checked]:bg-green-900/30"
                      >
                        <Select.ItemText>{getUnitDisplayName(unit)}</Select.ItemText>
                        <Select.ItemIndicator className="absolute left-1 inline-flex items-center">
                          <CheckCircle className="h-4 w-4 text-green-600 dark:text-green-400" />
                        </Select.ItemIndicator>
                      </Select.Item>
                    ))}
                  </Select.Viewport>
                </Select.Content>
              </Select.Portal>
            </Select.Root>
            {fieldErrors.unit_id && (
              <p className="mt-1 text-sm text-red-600 dark:text-red-400">{fieldErrors.unit_id}</p>
            )}
          </>
        )}
      </div>

      {/* Tenant Selection */}
      <div>
        <Label htmlFor="tenant-select" required>Tenant</Label>
        <Select.Root 
          value={selectedTenant ? selectedTenant.id.toString() : undefined} 
          onValueChange={onTenantChange}
          disabled={isLoadingTenants || !formData.property_id}
        >
          <Select.Trigger 
            className={`w-full px-4 py-2.5 border ${
              fieldErrors.tenant_id
                ? 'border-red-300 dark:border-red-600'
                : 'border-gray-200 dark:border-gray-600'
            } rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-transparent transition-all bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 flex items-center justify-between hover:border-gray-300 dark:hover:border-gray-500 disabled:opacity-50 disabled:cursor-not-allowed`}
          >
            <Select.Value placeholder={
              isLoadingTenants 
                ? "Loading tenants..." 
                : !formData.property_id 
                  ? "Select property first"
                  : availableTenants.length === 0
                    ? "No available tenants"
                    : "Select a tenant"
            } />
            <Select.Icon>
              {isLoadingTenants ? (
                <svg className="animate-spin h-4 w-4 text-gray-500" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
              ) : (
                <ChevronDown className="h-4 w-4 text-gray-500 dark:text-gray-400" />
              )}
            </Select.Icon>
          </Select.Trigger>
          <Select.Portal>
            <Select.Content 
              className="overflow-hidden bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-600 shadow-lg z-[10001] max-h-[300px]"
              position="popper"
              side="bottom"
              align="start"
              sideOffset={4}
            >
              <Select.Viewport className="p-1">
                {availableTenants.map((tenant) => (
                  <Select.Item
                    key={tenant.id}
                    value={tenant.id.toString()}
                    className="relative flex flex-col items-start pl-7 pr-3 py-2 text-sm text-gray-900 dark:text-gray-100 rounded cursor-pointer hover:bg-green-50 dark:hover:bg-green-900/20 focus:bg-green-50 dark:focus:bg-green-900/20 outline-none select-none data-[state=checked]:bg-green-50 dark:data-[state=checked]:bg-green-900/30"
                  >
                    <Select.ItemText>
                      <div className="flex flex-col">
                        <span className="font-medium">{getTenantDisplayName(tenant)}</span>
                        {tenant.email && (
                          <span className="text-xs text-gray-500 dark:text-gray-400">
                            {tenant.email}
                          </span>
                        )}
                      </div>
                    </Select.ItemText>
                    <Select.ItemIndicator className="absolute left-1 top-2.5 inline-flex items-center">
                      <CheckCircle className="h-4 w-4 text-green-600 dark:text-green-400" />
                    </Select.ItemIndicator>
                  </Select.Item>
                ))}
                
                {/* Create New Tenant Option */}
                <Select.Separator className="h-px bg-gray-200 dark:bg-gray-600 my-1" />
                <button
                  type="button"
                  onClick={(e) => {
                    e.preventDefault();
                    onCreateNewTenant();
                  }}
                  className="w-full text-left pl-7 pr-3 py-2 text-sm font-semibold text-green-600 dark:text-green-400 rounded cursor-pointer hover:bg-green-50 dark:hover:bg-green-900/20 focus:bg-green-50 dark:focus:bg-green-900/20 outline-none"
                >
                  + Create New Tenant
                </button>
              </Select.Viewport>
            </Select.Content>
          </Select.Portal>
        </Select.Root>
        {fieldErrors.tenant_id && (
          <p className="mt-1 text-sm text-red-600 dark:text-red-400">{fieldErrors.tenant_id}</p>
        )}
      </div>

      {/* Lease Terms */}
      <div className="grid grid-cols-2 gap-4">
        <div>
          <Label htmlFor="start_date" required>Start Date</Label>
          <Input 
            name="start_date" 
            id="start_date" 
            type="date" 
            value={formData.start_date} 
            onChange={onFormChange}
          />
          {fieldErrors.start_date && (
            <p className="mt-1 text-sm text-red-600 dark:text-red-400">{fieldErrors.start_date}</p>
          )}
        </div>
        <div>
          <Label htmlFor="end_date" required>End Date</Label>
          <Input 
            name="end_date" 
            id="end_date" 
            type="date" 
            value={formData.end_date} 
            onChange={onFormChange}
          />
          {fieldErrors.end_date && (
            <p className="mt-1 text-sm text-red-600 dark:text-red-400">{fieldErrors.end_date}</p>
          )}
        </div>
      </div>

      {/* Financial Terms */}
      <div className="grid grid-cols-2 gap-4">
        <div>
          <Label htmlFor="monthly_rent" required>Monthly Rent ($)</Label>
          <Input 
            name="monthly_rent" 
            id="monthly_rent" 
            type="number" 
            step="0.01"
            placeholder="1500" 
            value={formData.monthly_rent} 
            onChange={onFormChange}
          />
          {fieldErrors.monthly_rent && (
            <p className="mt-1 text-sm text-red-600 dark:text-red-400">{fieldErrors.monthly_rent}</p>
          )}
        </div>
        <div>
          <Label htmlFor="security_deposit" required>Security Deposit ($)</Label>
          <Input 
            name="security_deposit" 
            id="security_deposit" 
            type="number" 
            step="0.01"
            placeholder="1500" 
            value={formData.security_deposit} 
            onChange={onFormChange}
          />
          {fieldErrors.security_deposit && (
            <p className="mt-1 text-sm text-red-600 dark:text-red-400">{fieldErrors.security_deposit}</p>
          )}
        </div>
      </div>

      {/* Additional Terms */}
      <div className="grid grid-cols-3 gap-4">
        <div>
          <Label htmlFor="rent_due_day">Rent Due Day</Label>
          <Input 
            name="rent_due_day" 
            id="rent_due_day" 
            type="number" 
            min="1" 
            max="31"
            value={formData.rent_due_day} 
            onChange={onFormChange}
          />
        </div>
        <div>
          <Label htmlFor="late_fee_amount">Late Fee ($)</Label>
          <Input 
            name="late_fee_amount" 
            id="late_fee_amount" 
            type="number" 
            step="0.01"
            placeholder="50" 
            value={formData.late_fee_amount} 
            onChange={onFormChange}
          />
        </div>
        <div>
          <Label htmlFor="late_fee_after_days">Late After (Days)</Label>
          <Input 
            name="late_fee_after_days" 
            id="late_fee_after_days" 
            type="number" 
            min="1"
            placeholder="5" 
            value={formData.late_fee_after_days} 
            onChange={onFormChange}
          />
        </div>
      </div>

      {/* Special Terms */}
      <div>
        <Label htmlFor="special_terms">Special Terms</Label>
        <TextArea 
          name="special_terms" 
          id="special_terms" 
          rows={3}
          placeholder="Any special conditions or notes..."
          value={formData.special_terms} 
          onChange={onFormChange}
        />
      </div>
    </div>
  );
};

