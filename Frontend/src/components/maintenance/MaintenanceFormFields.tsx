import React, { useState, useEffect } from 'react';
import type { MaintenanceFormData, MaintenancePhotoState, Property, PropertyUnit, Tenant } from '../../types/tenant';
import MaintenancePhotoUpload from './MaintenancePhotoUpload';
import { getSecurePhotoUrl } from '../../utils/api/maintenance';

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
  onReorderPhotos?: (newOrder: string[]) => void;
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
  const [securePhotoUrls, setSecurePhotoUrls] = useState<Record<string, string>>({});
  const [loadingPhotos, setLoadingPhotos] = useState(false);

  // Fetch secure URLs for all photos when component mounts
  useEffect(() => {
    const fetchSecureUrls = async () => {
      if (!formData.photos || formData.photos.length === 0) {
        setLoadingPhotos(false);
        return;
      }

      setLoadingPhotos(true);
      const urlMap: Record<string, string> = {};

      try {
        console.log('[MaintenanceView] Fetching secure URLs for photos:', formData.photos);
        
        // Fetch secure URLs for all photos in parallel
        const secureUrlPromises = formData.photos.map(async (photoUrl) => {
          try {
            const { secure_url, expires_at } = await getSecurePhotoUrl(photoUrl);
            console.log(`[MaintenanceView] Got secure URL for ${photoUrl}, expires at ${expires_at}`);
            return { original: photoUrl, secure: secure_url };
          } catch (error) {
            console.error(`Failed to get secure URL for photo: ${photoUrl}`, error);
            // Return original URL as fallback (will likely fail but shows error state)
            return { original: photoUrl, secure: photoUrl };
          }
        });

        const results = await Promise.all(secureUrlPromises);
        results.forEach(({ original, secure }) => {
          urlMap[original] = secure;
        });

        console.log('[MaintenanceView] Secure photo URLs loaded:', urlMap);
        setSecurePhotoUrls(urlMap);
      } catch (error) {
        console.error('Failed to fetch secure photo URLs:', error);
      } finally {
        setLoadingPhotos(false);
      }
    };

    fetchSecureUrls();
  }, [formData.photos]);

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
      {/* Photos Section - At Top (View-Only) */}
      {formData.photos && formData.photos.length > 0 && (
        <div className="bg-white dark:bg-gray-800 rounded-lg p-5 shadow-sm border border-gray-100 dark:border-gray-600 transition-colors duration-300">
          <div className="flex items-center mb-3">
            <div className="w-9 h-9 bg-purple-50 dark:bg-purple-900/20 rounded-lg flex items-center justify-center mr-3 transition-colors duration-300">
              <svg className="w-4 h-4 text-purple-600 dark:text-purple-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
              </svg>
            </div>
            <h3 className="text-base font-medium text-gray-900 dark:text-gray-100 transition-colors duration-300">Photos ({formData.photos.length})</h3>
          </div>
          
          {/* Simple photo grid for view mode - no dropzone, no actions */}
          {loadingPhotos ? (
            <div className="flex items-center justify-center py-8">
              <div className="flex flex-col items-center gap-2">
                <div className="w-8 h-8 border-4 border-purple-200 dark:border-purple-800 border-t-purple-600 dark:border-t-purple-400 rounded-full animate-spin" />
                <p className="text-sm text-gray-500 dark:text-gray-400">Loading photos...</p>
              </div>
            </div>
          ) : (
            <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-3">
              {formData.photos.map((url, index) => {
                const isPdf = url.toLowerCase().includes('.pdf');
                // Use secure URL if available, otherwise show loading state
                const displayUrl = securePhotoUrls[url];
                const isPhotoReady = !!displayUrl;
                
                return (
                  <div key={index} className="relative aspect-square rounded-lg overflow-hidden bg-gray-100 dark:bg-gray-700 shadow-md hover:shadow-lg transition-shadow duration-300 border-2 border-gray-200 dark:border-gray-600">
                    {!isPhotoReady ? (
                      // Loading state while fetching secure URL
                      <div className="w-full h-full flex items-center justify-center">
                        <div className="w-6 h-6 border-2 border-purple-200 dark:border-purple-800 border-t-purple-600 dark:border-t-purple-400 rounded-full animate-spin" />
                      </div>
                    ) : isPdf ? (
                      <div className="w-full h-full flex items-center justify-center bg-gray-100 dark:bg-gray-700">
                        <svg className="w-8 h-8 text-gray-400 dark:text-gray-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                        </svg>
                      </div>
                    ) : (
                      <img
                        src={displayUrl}
                        alt={`Photo ${index + 1}`}
                        className="w-full h-full object-cover cursor-pointer"
                        onClick={() => window.open(displayUrl, '_blank')}
                        onError={(e) => {
                          // Handle broken images
                          const target = e.target as HTMLImageElement;
                          target.style.display = 'none';
                          const parent = target.parentElement;
                          if (parent) {
                            parent.innerHTML = `
                              <div class="w-full h-full flex flex-col items-center justify-center bg-red-50 dark:bg-red-900/20 p-2">
                                <svg class="w-8 h-8 text-red-400 mb-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                                </svg>
                                <span class="text-xs text-red-600 dark:text-red-400 text-center">Image not found</span>
                              </div>
                            `;
                          }
                        }}
                      />
                    )}
                    
                    {/* Hover overlay to view full size - only show when photo is ready */}
                    {!isPdf && isPhotoReady && (
                      <div className="absolute inset-0 bg-black bg-opacity-0 hover:bg-opacity-20 transition-all duration-200 flex items-center justify-center">
                        <a
                          href={displayUrl}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="opacity-0 hover:opacity-100 text-white bg-black bg-opacity-60 px-3 py-1.5 rounded-lg text-xs font-medium transition-opacity"
                          onClick={(e) => e.stopPropagation()}
                        >
                          View Full
                        </a>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}
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
  onReorderPhotos,
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

  // Handle file change from dropzone
  const handleDropzoneFileChange = (files: File[]) => {
    // Create a fake event to match existing signature
    const fileList = files as unknown as FileList;
    const fakeEvent = {
      target: {
        files: fileList,
      },
    } as unknown as React.ChangeEvent<HTMLInputElement>;
    onFileChange(fakeEvent);
  };

  // Handle photo reorder
  const handlePhotoReorder = (newOrder: string[]) => {
    onUpdateField('photos', newOrder);
    if (onReorderPhotos) {
      onReorderPhotos(newOrder);
    }
  };

  return (
    <div className="space-y-3">
      {/* Photos Section - At Top */}
      <div className="bg-white dark:bg-gray-800 rounded-lg p-4 border border-gray-200 dark:border-gray-700 transition-colors duration-300">
        <div className="flex items-center mb-3">
          <div className="w-8 h-8 bg-purple-50 dark:bg-purple-900/20 rounded-lg flex items-center justify-center mr-3">
            <svg className="w-4 h-4 text-purple-600 dark:text-purple-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
            </svg>
          </div>
          <div>
            <h3 className="text-base font-semibold text-gray-900 dark:text-gray-100">Photos</h3>
          </div>
        </div>

        <MaintenancePhotoUpload
          photos={formData.photos || []}
          photoState={photoState}
          onFileChange={handleDropzoneFileChange}
          onRemovePhoto={onRemovePhoto}
          onReorderPhotos={handlePhotoReorder}
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
          <div className="w-8 h-8 bg-orange-50 dark:bg-orange-900/20 rounded-lg flex items-center justify-center mr-3">
            <svg className="w-4 h-4 text-orange-600 dark:text-orange-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
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
          <div className="w-8 h-8 bg-green-50 dark:bg-green-900/20 rounded-lg flex items-center justify-center mr-3">
            <svg className="w-4 h-4 text-green-600 dark:text-green-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
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

    </div>
  );
};

export default MaintenanceFormFields;
