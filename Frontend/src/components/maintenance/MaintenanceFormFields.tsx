import React from 'react';
import type { MaintenanceFormData, MaintenancePhotoState, Property, PropertyUnit, Tenant } from '../../types/tenant';
import LoadingSpinner from '../LoadingSpinner';

interface MaintenanceFormFieldsProps {
  formData: MaintenanceFormData;
  errors: Record<string, string>;
  properties: Property[];
  units: PropertyUnit[];
  tenants: Tenant[];
  photoState: MaintenancePhotoState;
  onUpdateField: <K extends keyof MaintenanceFormData>(field: K, value: MaintenanceFormData[K]) => void;
  onFileChange: (e: React.ChangeEvent<HTMLInputElement>) => void;
  onRemovePhoto: (id: string) => void;
  isViewing?: boolean;
  isLoadingUnits?: boolean;
  isLoadingTenants?: boolean;
}

// Helper to get tenant name
const getTenantName = (tenant?: Tenant | null): string => {
  if (!tenant) return 'N/A';
  if (tenant.tenant_type === 'Company' && tenant.company_name) {
    return tenant.company_name;
  }
  if (tenant.first_name || tenant.last_name) {
    return `${tenant.first_name || ''} ${tenant.last_name || ''}`.trim();
  }
  return 'N/A';
};

// View-only mode component
const MaintenanceViewMode: React.FC<{
  formData: MaintenanceFormData;
  properties: Property[];
  units: PropertyUnit[];
  tenants: Tenant[];
}> = ({ formData, properties, units, tenants }) => {
  const renderField = (label: string, value: React.ReactNode) => (
    <div className="flex flex-col gap-1">
      <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 transition-colors duration-300">
        {label}
      </label>
      <div className="bg-gray-50 dark:bg-gray-700 border border-gray-200 dark:border-gray-600 rounded-md px-3 py-2 text-gray-700 dark:text-gray-200 min-h-[40px] flex items-center transition-colors duration-300">
        {value || <span className="text-gray-400 dark:text-gray-500">—</span>}
      </div>
    </div>
  );

  // Type-safe ID comparisons using numeric conversion with proper null handling
  // Avoids fragile string comparisons and leverages TypeScript type safety
  const propertyIdNum = formData.property_id ? Number(formData.property_id) : null;
  const unitIdNum = formData.unit_id && formData.unit_id !== 'common_area' ? Number(formData.unit_id) : null;
  const tenantIdNum = formData.tenant_id ? Number(formData.tenant_id) : null;

  const property = propertyIdNum !== null ? properties.find(p => p.id === propertyIdNum) : undefined;
  const unit = unitIdNum !== null ? units.find(u => u.id === unitIdNum) : undefined;
  const tenant = tenantIdNum !== null ? tenants.find(t => t.id === tenantIdNum) : undefined;

  return (
    <div className="p-6 space-y-4">
      {/* Property and Unit Information */}
      <div className="bg-white dark:bg-gray-800 rounded-lg p-5 shadow-sm border border-gray-100 dark:border-gray-600">
        <div className="flex items-center mb-3">
          <div className="w-9 h-9 bg-blue-50 dark:bg-blue-900/20 rounded-lg flex items-center justify-center mr-3 transition-colors duration-300">
            <svg className="w-4 h-4 text-blue-600 dark:text-blue-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" />
            </svg>
          </div>
          <h3 className="text-base font-medium text-gray-900 dark:text-gray-100 transition-colors duration-300">Location Information</h3>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {renderField('Property', property?.name)}
          {renderField(
            'Unit',
            formData.unit_id && formData.unit_id !== 'common_area'
              ? unit?.name
              : 'Common Area / Building-wide'
          )}
        </div>
      </div>

      {/* Request Details */}
      <div className="bg-white dark:bg-gray-800 rounded-lg p-5 shadow-sm border border-gray-100 dark:border-gray-600">
        <div className="flex items-center mb-3">
          <div className="w-9 h-9 bg-orange-50 dark:bg-orange-900/20 rounded-lg flex items-center justify-center mr-3 transition-colors duration-300">
            <svg className="w-4 h-4 text-orange-600 dark:text-orange-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
          </div>
          <h3 className="text-base font-medium text-gray-900 dark:text-gray-100 transition-colors duration-300">Request Details</h3>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {renderField('Issue Title', formData.issue_title)}
          {renderField('Priority', formData.priority)}
          {renderField('Status', formData.status)}
          {renderField('Assign To', formData.assigned_to)}
        </div>
        <div className="mt-4">
          {renderField('Description', formData.description)}
        </div>
      </div>

      {/* Additional Information */}
      <div className="bg-white dark:bg-gray-800 rounded-lg p-5 shadow-sm border border-gray-100 dark:border-gray-600">
        <div className="flex items-center mb-3">
          <div className="w-9 h-9 bg-green-50 dark:bg-green-900/20 rounded-lg flex items-center justify-center mr-3 transition-colors duration-300">
            <svg className="w-4 h-4 text-green-600 dark:text-green-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M9 7h6m0 10v-3m-3 3h.01M9 17h.01M9 14h.01M12 14h.01M15 11h.01M12 11h.01M9 11h.01M7 21h10a2 2 0 002-2V5a2 2 0 00-2-2H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
            </svg>
          </div>
          <h3 className="text-base font-medium text-gray-900 dark:text-gray-100 transition-colors duration-300">Additional Information</h3>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {renderField(
            'Scheduled Date',
            formData.scheduled_date ? new Date(formData.scheduled_date).toLocaleDateString() : ''
          )}
          {renderField('Estimated Cost', formData.estimated_cost ? `$${formData.estimated_cost}` : '')}
          {renderField('Tenant', getTenantName(tenant))}
        </div>
      </div>

      {/* Photos */}
      {formData.photos && formData.photos.length > 0 && (
        <div className="bg-white dark:bg-gray-800 rounded-lg p-5 shadow-sm border border-gray-100 dark:border-gray-600 transition-colors duration-300">
          <div className="flex items-center mb-3">
            <div className="w-9 h-9 bg-purple-50 dark:bg-purple-900/20 rounded-lg flex items-center justify-center mr-3 transition-colors duration-300">
              <svg className="w-4 h-4 text-purple-600 dark:text-purple-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
              </svg>
            </div>
            <h3 className="text-base font-medium text-gray-900 dark:text-gray-100 transition-colors duration-300">Photos</h3>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
            {formData.photos.map((url, idx) => (
              <div key={idx} className="relative group">
                <div className="aspect-square bg-gray-100 rounded-lg overflow-hidden">
                  {url.toLowerCase().includes('.pdf') ? (
                    <div className="w-full h-full flex items-center justify-center bg-gray-100">
                      <svg className="w-8 h-8 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                      </svg>
                    </div>
                  ) : (
                    <img src={url} alt={`Photo ${idx + 1}`} className="w-full h-full object-cover" />
                  )}
                </div>
                <div className="absolute inset-0 bg-black bg-opacity-0 group-hover:bg-opacity-30 transition-all duration-200 rounded-lg flex items-center justify-center">
                  <a
                    href={url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="opacity-0 group-hover:opacity-100 text-white bg-black bg-opacity-50 px-3 py-1 rounded text-sm transition-opacity"
                  >
                    View Full
                  </a>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

// Edit/Create mode component
const MaintenanceFormFields: React.FC<MaintenanceFormFieldsProps> = ({
  formData,
  errors,
  properties,
  units,
  tenants,
  photoState,
  onUpdateField,
  onFileChange,
  onRemovePhoto,
  isViewing,
  isLoadingUnits,
  isLoadingTenants,
}) => {
  // If viewing mode, render view component
  if (isViewing) {
    return <MaintenanceViewMode formData={formData} properties={properties} units={units} tenants={tenants} />;
  }

  const getInputClassName = (fieldName: string): string => {
    const baseClasses = "w-full px-4 py-2.5 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all bg-white dark:bg-gray-700 dark:text-gray-100 text-sm";
    return errors[fieldName]
      ? `${baseClasses} border-red-300 dark:border-red-500 bg-red-50 dark:bg-red-900/20 focus:ring-red-100`
      : `${baseClasses} border-gray-200 dark:border-gray-600 hover:border-gray-400 dark:hover:border-gray-500`;
  };

  return (
    <div className="space-y-3">
      {/* Location Section */}
      <div className="bg-white dark:bg-gray-800 rounded-lg p-4 border border-gray-200 dark:border-gray-700 transition-colors duration-300">
        <div className="flex items-center mb-3">
          <div className="w-8 h-8 bg-gradient-to-br from-blue-500 to-blue-600 rounded-lg flex items-center justify-center mr-3">
            <svg className="w-4 h-4 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" />
            </svg>
          </div>
          <div>
            <h3 className="text-base font-semibold text-gray-900 dark:text-gray-100">Location Information</h3>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          {/* Property */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Property <span className="text-red-500">*</span>
            </label>
            <select
              value={formData.property_id || ''}
              onChange={(e) => onUpdateField('property_id', e.target.value)}
              className={getInputClassName('property_id')}
            >
              <option value="">Select Property</option>
              {properties.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name}
                </option>
              ))}
            </select>
            {errors.property_id && (
              <p className="mt-2 text-sm text-red-600 dark:text-red-400">{errors.property_id}</p>
            )}
          </div>

          {/* Unit */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Unit
            </label>
            <select
              value={formData.unit_id || ''}
              onChange={(e) => onUpdateField('unit_id', e.target.value)}
              disabled={!formData.property_id || isLoadingUnits}
              className={getInputClassName('unit_id')}
            >
              <option value="">
                {isLoadingUnits ? 'Loading...' : 'Select Unit or leave blank for common area'}
              </option>
              <option value="common_area">Common Area / Building-wide</option>
              {units.map((u) => (
                <option key={u.id} value={u.id}>
                  {u.name}
                </option>
              ))}
            </select>
            <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
              Select "Common Area" for property-wide maintenance like parking lots, building exterior, etc.
            </p>
          </div>

          {/* Tenant - Moved from Additional Information section */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Tenant
            </label>
            <select
              value={formData.tenant_id || ''}
              onChange={(e) => onUpdateField('tenant_id', e.target.value)}
              disabled={!formData.property_id || isLoadingTenants}
              className={getInputClassName('tenant_id')}
            >
              <option value="">
                {isLoadingTenants ? 'Loading...' : 'Select Tenant (optional)'}
              </option>
              {tenants.map((t) => (
                <option key={t.id} value={t.id}>
                  {getTenantName(t)}
                </option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {/* Request Details Section */}
      <div className="bg-white dark:bg-gray-800 rounded-lg p-4 border border-gray-200 dark:border-gray-700 transition-colors duration-300">
        <div className="flex items-center mb-3">
          <div className="w-8 h-8 bg-gradient-to-br from-orange-500 to-orange-600 rounded-lg flex items-center justify-center mr-3">
            <svg className="w-4 h-4 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
          </div>
          <div>
            <h3 className="text-base font-semibold text-gray-900 dark:text-gray-100">Request Details</h3>
          </div>
        </div>

        <div className="space-y-4">
          {/* Issue Title */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Issue Title <span className="text-red-500">*</span>
            </label>
            <input
              type="text"
              value={formData.issue_title || ''}
              onChange={(e) => onUpdateField('issue_title', e.target.value)}
              placeholder="Brief description of the issue"
              className={getInputClassName('issue_title')}
            />
            {errors.issue_title && (
              <p className="mt-2 text-sm text-red-600 dark:text-red-400">{errors.issue_title}</p>
            )}
          </div>

          {/* Description */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Description
            </label>
            <textarea
              value={formData.description || ''}
              onChange={(e) => onUpdateField('description', e.target.value)}
              rows={3}
              placeholder="Detailed description of the maintenance issue..."
              className="w-full px-4 py-2.5 border border-gray-200 dark:border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all bg-white dark:bg-gray-700 dark:text-gray-100 resize-none text-sm"
            />
          </div>

          {/* Priority and Status */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
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
      </div>

      {/* Additional Information Section */}
      <div className="bg-white dark:bg-gray-800 rounded-lg p-4 border border-gray-200 dark:border-gray-700 transition-colors duration-300">
        <div className="flex items-center mb-3">
          <div className="w-8 h-8 bg-gradient-to-br from-green-500 to-green-600 rounded-lg flex items-center justify-center mr-3">
            <svg className="w-4 h-4 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M9 7h6m0 10v-3m-3 3h.01M9 17h.01M9 14h.01M12 14h.01M15 11h.01M12 11h.01M9 11h.01M7 21h10a2 2 0 002-2V5a2 2 0 00-2-2H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
            </svg>
          </div>
          <div>
            <h3 className="text-base font-semibold text-gray-900 dark:text-gray-100">Additional Information</h3>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {/* Assigned To */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Assign To
            </label>
            <input
              type="text"
              value={formData.assigned_to || ''}
              onChange={(e) => onUpdateField('assigned_to', e.target.value)}
              placeholder="Name of person or company"
              className={getInputClassName('assigned_to')}
            />
          </div>

          {/* Scheduled Date */}
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
          </div>

          {/* Estimated Cost */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Estimated Cost
            </label>
            <input
              type="number"
              value={formData.estimated_cost || ''}
              onChange={(e) => onUpdateField('estimated_cost', e.target.value)}
              placeholder="0.00"
              min="0"
              step="0.01"
              className={getInputClassName('estimated_cost')}
            />
            {errors.estimated_cost && (
              <p className="mt-2 text-sm text-red-600 dark:text-red-400">{errors.estimated_cost}</p>
            )}
          </div>
        </div>
      </div>

      {/* Photos Section */}
      <div className="bg-white dark:bg-gray-800 rounded-lg p-4 border border-gray-200 dark:border-gray-700 transition-colors duration-300">
        <div className="flex items-center mb-3">
          <div className="w-8 h-8 bg-gradient-to-br from-purple-500 to-purple-600 rounded-lg flex items-center justify-center mr-3">
            <svg className="w-4 h-4 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
            </svg>
          </div>
          <div>
            <h3 className="text-base font-semibold text-gray-900 dark:text-gray-100">Photos</h3>
          </div>
        </div>

        <div>
          <input
            type="file"
            name="photos"
            multiple
            accept="image/*,.pdf"
            className="block w-full text-sm file:mr-4 file:py-2.5 file:px-4 file:rounded-lg file:border-0 file:text-sm file:font-medium file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100 file:cursor-pointer cursor-pointer border border-gray-200 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 dark:text-gray-200"
            disabled={photoState.uploadingPhotos}
            onChange={onFileChange}
          />
          <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
            Upload images or PDFs (max 10MB each). Supported formats: JPG, PNG, GIF, PDF
          </p>

          {photoState.uploadingPhotos && (
            <div className="mt-2 text-blue-600 dark:text-blue-400 text-sm flex items-center">
              <div className="mr-2">
                <LoadingSpinner size="sm" />
              </div>
              Uploading photos...
            </div>
          )}

          {photoState.uploadError && (
            <div className="mt-2 text-red-600 text-sm">{photoState.uploadError}</div>
          )}

          {formData.photos && formData.photos.length > 0 && (
            <div className="mt-4">
              <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Uploaded Photos</h4>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                {formData.photos.map((url, idx) => (
                  <div key={idx} className="relative group">
                    <div className="aspect-square bg-gray-100 dark:bg-gray-700 rounded-lg overflow-hidden border border-gray-200 dark:border-gray-600">
                      {url.toLowerCase().includes('.pdf') ? (
                        <div className="w-full h-full flex items-center justify-center bg-gray-50 dark:bg-gray-700">
                          <svg className="w-6 h-6 text-gray-400 dark:text-gray-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                          </svg>
                        </div>
                      ) : (
                        <img src={url} alt={`Photo ${idx + 1}`} className="w-full h-full object-cover" />
                      )}
                    </div>
                    <button
                      type="button"
                      onClick={() => onRemovePhoto(url)}
                      className="absolute -top-2 -right-2 bg-red-500 text-white rounded-full w-6 h-6 flex items-center justify-center text-xs hover:bg-red-600 transition-colors"
                    >
                      ×
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default MaintenanceFormFields;
