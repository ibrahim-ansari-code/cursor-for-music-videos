import React from 'react';
import type { MaintenanceFormData, MaintenancePhotoState, Property, PropertyUnit, Tenant } from '../../../../types/tenant';
import MaintenancePhotoUpload from '../../MaintenancePhotoUpload';

interface RequestDetailsStepProps {
  formData: MaintenanceFormData;
  errors: Record<string, string>;
  properties: Property[];
  units: PropertyUnit[];
  tenants: Tenant[];
  photoState: MaintenancePhotoState;
  onUpdateField: <K extends keyof MaintenanceFormData>(field: K, value: MaintenanceFormData[K]) => void;
  onFileChange: (files: File[]) => void;
  onRemovePhoto: (id: string) => void;
  onReorderPhotos: (newOrder: string[]) => void;
  isLoadingUnits?: boolean;
  isLoadingTenants?: boolean;
}

const RequestDetailsStep: React.FC<RequestDetailsStepProps> = ({
  formData,
  errors,
  properties,
  units,
  tenants,
  photoState,
  onUpdateField,
  onFileChange,
  onRemovePhoto,
  onReorderPhotos,
  isLoadingUnits,
  isLoadingTenants,
}) => {
  const getInputClassName = (fieldName: string): string => {
    const baseClasses = "w-full px-4 py-2.5 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all bg-white dark:bg-gray-700 dark:text-gray-100 text-sm";
    return errors[fieldName]
      ? `${baseClasses} border-red-300 dark:border-red-500 bg-red-50 dark:bg-red-900/20 focus:ring-red-100`
      : `${baseClasses} border-gray-200 dark:border-gray-600 hover:border-gray-400 dark:hover:border-gray-500`;
  };

  // Helper to get tenant name
  const getTenantName = (tenant?: Tenant | null): string => {
    if (!tenant) return '';
    if (tenant.tenant_type === 'Company' && tenant.company_name) {
      return tenant.company_name;
    }
    if (tenant.first_name || tenant.last_name) {
      return `${tenant.first_name || ''} ${tenant.last_name || ''}`.trim();
    }
    return '';
  };

  return (
    <div className="space-y-4 p-6">
      {/* Photos Section */}
      <div className="bg-white dark:bg-gray-800 rounded-lg p-4 border border-gray-200 dark:border-gray-700 transition-colors duration-300">
        <div className="flex items-center mb-3">
          <div className="w-8 h-8 bg-purple-50 dark:bg-purple-900/20 rounded-lg flex items-center justify-center mr-3">
            <svg className="w-4 h-4 text-purple-600 dark:text-purple-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
            </svg>
          </div>
          <div>
            <h3 className="text-base font-semibold text-gray-900 dark:text-gray-100">Photos</h3>
            <p className="text-xs text-gray-500 dark:text-gray-400">Upload photos of the issue (optional)</p>
          </div>
        </div>

        <MaintenancePhotoUpload
          photos={formData.photos || []}
          photoState={photoState}
          onFileChange={onFileChange}
          onRemovePhoto={onRemovePhoto}
          onReorderPhotos={onReorderPhotos}
          disabled={false}
        />
      </div>

      {/* Location Section */}
      <div className="bg-white dark:bg-gray-800 rounded-lg p-4 border border-gray-200 dark:border-gray-700 transition-colors duration-300">
        <div className="flex items-center mb-3">
          <div className="w-8 h-8 bg-blue-50 dark:bg-blue-900/20 rounded-lg flex items-center justify-center mr-3">
            <svg className="w-4 h-4 text-blue-600 dark:text-blue-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" />
            </svg>
          </div>
          <div>
            <h3 className="text-base font-semibold text-gray-900 dark:text-gray-100">Location</h3>
            <p className="text-xs text-gray-500 dark:text-gray-400">Where is the maintenance needed?</p>
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
                {isLoadingUnits ? 'Loading...' : 'Select Unit (optional)'}
              </option>
              <option value="common_area">Common Area / Building-wide</option>
              {units.map((u) => (
                <option key={u.id} value={u.id}>
                  {u.name}
                </option>
              ))}
            </select>
            <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
              Select "Common Area" for building-wide maintenance
            </p>
          </div>

          {/* Tenant */}
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

        {/* Notify Tenant Checkbox - only show when tenant is selected */}
        {formData.tenant_id && (
          <div className="mt-3">
            <div className="flex items-center space-x-3">
              <input
                type="checkbox"
                id="notify_tenant"
                checked={formData.notify_tenant || false}
                onChange={(e) => onUpdateField('notify_tenant', e.target.checked)}
                className="w-4 h-4 text-green-600 border-gray-300 dark:border-gray-600 rounded focus:ring-green-500 dark:focus:ring-green-400 dark:bg-gray-700"
              />
              <label htmlFor="notify_tenant" className="text-sm font-medium text-gray-700 dark:text-gray-300 cursor-pointer">
                Notify Tenant via Email
              </label>
            </div>
            <p className="text-xs text-gray-500 dark:text-gray-400 ml-7 mt-1">
              Tenant will receive email notifications about request updates
            </p>
          </div>
        )}
      </div>

      {/* Issue Details */}
      <div className="bg-white dark:bg-gray-800 rounded-lg p-4 border border-gray-200 dark:border-gray-700 transition-colors duration-300">
        <div className="flex items-center mb-3">
          <div className="w-8 h-8 bg-orange-50 dark:bg-orange-900/20 rounded-lg flex items-center justify-center mr-3">
            <svg className="w-4 h-4 text-orange-600 dark:text-orange-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
          </div>
          <div>
            <h3 className="text-base font-semibold text-gray-900 dark:text-gray-100">Issue Details</h3>
            <p className="text-xs text-gray-500 dark:text-gray-400">Describe the maintenance issue</p>
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
        </div>
      </div>
    </div>
  );
};

export default RequestDetailsStep;

