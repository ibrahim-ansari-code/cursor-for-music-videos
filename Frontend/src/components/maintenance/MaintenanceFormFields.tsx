import React, { useState, useEffect } from "react";
import * as Select from "@radix-ui/react-select";
import { ChevronDown, Check, Building2, User, Calendar, CheckCircle2 } from "lucide-react";
import type {
  MaintenanceFormData,
  MaintenancePhotoState,
  MaintenanceRequest,
  Property,
  PropertyUnit,
  Tenant,
} from "../../types/tenant";
import type { VendorContact } from "../../types/vendor";
import MaintenancePhotoUpload from "./MaintenancePhotoUpload";
import { getSecurePhotoUrl } from "../../utils/api/maintenance";

interface MaintenanceFormFieldsProps {
  formData: MaintenanceFormData;
  errors: Record<string, string>;
  properties: Property[];
  units: PropertyUnit[];
  tenants: Tenant[];
  vendors: VendorContact[];
  photoState: MaintenancePhotoState;
  onUpdateField: <K extends keyof MaintenanceFormData>(
    field: K,
    value: MaintenanceFormData[K]
  ) => void;
  onFileChange: (e: React.ChangeEvent<HTMLInputElement>) => void;
  onRemovePhoto: (id: string) => void;
  onReorderPhotos?: (newOrder: string[]) => void;
  isViewing?: boolean;
  /** If true, property/unit/tenant are read-only (edit mode vs create mode) */
  isEditMode?: boolean;
  isLoadingUnits?: boolean;
  isLoadingTenants?: boolean;
  isLoadingVendors?: boolean;
  /** Original request object for view mode - contains nested property/unit/tenant/vendor */
  request?: MaintenanceRequest | null;
}

// Helper to get tenant name
const getTenantName = (tenant?: Tenant | null): string => {
  if (!tenant) return "N/A";
  if (tenant.tenant_type === "Company" && tenant.company_name) {
    return tenant.company_name;
  }
  if (tenant.first_name || tenant.last_name) {
    return `${tenant.first_name || ""} ${tenant.last_name || ""}`.trim();
  }
  return "N/A";
};

// View-only mode component
const MaintenanceViewMode: React.FC<{
  formData: MaintenanceFormData;
  properties: Property[];
  units: PropertyUnit[];
  tenants: Tenant[];
  vendors: VendorContact[];
  /** Original request object - contains nested property/unit/tenant/vendor objects */
  request?: MaintenanceRequest | null;
}> = ({ formData, properties, units, tenants, vendors, request }) => {
  const [securePhotoUrls, setSecurePhotoUrls] = useState<
    Record<string, string>
  >({});
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
        console.log(
          "[MaintenanceView] Fetching secure URLs for photos:",
          formData.photos
        );

        // Fetch secure URLs for all photos in parallel
        const secureUrlPromises = formData.photos.map(async (photoUrl) => {
          try {
            const { secure_url, expires_at } = await getSecurePhotoUrl(
              photoUrl
            );
            console.log(
              `[MaintenanceView] Got secure URL for ${photoUrl}, expires at ${expires_at}`
            );
            return { original: photoUrl, secure: secure_url };
          } catch (error) {
            console.error(
              `Failed to get secure URL for photo: ${photoUrl}`,
              error
            );
            // Return original URL as fallback (will likely fail but shows error state)
            return { original: photoUrl, secure: photoUrl };
          }
        });

        const results = await Promise.all(secureUrlPromises);
        results.forEach(({ original, secure }) => {
          urlMap[original] = secure;
        });

        console.log("[MaintenanceView] Secure photo URLs loaded:", urlMap);
        setSecurePhotoUrls(urlMap);
      } catch (error) {
        console.error("Failed to fetch secure photo URLs:", error);
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

  // Prefer nested objects from request (populated by backend), fallback to array lookups
  // This ensures view mode works correctly even before arrays are loaded
  const propertyIdNum = formData.property_id
    ? Number(formData.property_id)
    : null;
  const unitIdNum =
    formData.unit_id && formData.unit_id !== "common_area"
      ? Number(formData.unit_id)
      : null;
  const tenantIdNum = formData.tenant_id ? Number(formData.tenant_id) : null;
  const vendorIdNum = formData.vendor_id ? Number(formData.vendor_id) : null;

  // Use nested objects from request first, then fallback to array lookup
  const property = request?.property ?? (
    propertyIdNum !== null
      ? properties.find((p) => p.id === propertyIdNum)
      : undefined
  );
  const unit = request?.unit ?? (
    unitIdNum !== null ? units.find((u) => u.id === unitIdNum) : undefined
  );
  const tenant = request?.tenant ?? (
    tenantIdNum !== null
      ? tenants.find((t) => t.id === tenantIdNum)
      : undefined
  );
  const vendor = request?.vendor ?? (
    vendorIdNum !== null
      ? vendors.find((v) => v.id === vendorIdNum)
      : undefined
  );

  return (
    <div className="p-6 space-y-4">
      {/* Photos Section - At Top (View-Only) */}
      {formData.photos && formData.photos.length > 0 && (
        <div className="bg-white dark:bg-gray-800 rounded-lg p-5 shadow-sm border border-gray-100 dark:border-gray-600 transition-colors duration-300">
          <div className="flex items-center mb-3">
            <div className="w-9 h-9 bg-purple-50 dark:bg-purple-900/20 rounded-lg flex items-center justify-center mr-3 transition-colors duration-300">
              <svg
                className="w-4 h-4 text-purple-600 dark:text-purple-400"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                strokeWidth={2}
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"
                />
              </svg>
            </div>
            <h3 className="text-base font-medium text-gray-900 dark:text-gray-100 transition-colors duration-300">
              Photos ({formData.photos.length})
            </h3>
          </div>

          {/* Simple photo grid for view mode - no dropzone, no actions */}
          {loadingPhotos ? (
            <div className="flex items-center justify-center py-8">
              <div className="flex flex-col items-center gap-2">
                <div className="w-8 h-8 border-4 border-purple-200 dark:border-purple-800 border-t-purple-600 dark:border-t-purple-400 rounded-full animate-spin" />
                <p className="text-sm text-gray-500 dark:text-gray-400">
                  Loading photos...
                </p>
              </div>
            </div>
          ) : (
            <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-3">
              {formData.photos.map((url, index) => {
                const isPdf = url.toLowerCase().includes(".pdf");
                // Use secure URL if available, otherwise show loading state
                const displayUrl = securePhotoUrls[url];
                const isPhotoReady = !!displayUrl;

                return (
                  <div
                    key={index}
                    className="relative aspect-square rounded-lg overflow-hidden bg-gray-100 dark:bg-gray-700 shadow-md hover:shadow-lg transition-shadow duration-300 border-2 border-gray-200 dark:border-gray-600"
                  >
                    {!isPhotoReady ? (
                      // Loading state while fetching secure URL
                      <div className="w-full h-full flex items-center justify-center">
                        <div className="w-6 h-6 border-2 border-purple-200 dark:border-purple-800 border-t-purple-600 dark:border-t-purple-400 rounded-full animate-spin" />
                      </div>
                    ) : isPdf ? (
                      <div className="w-full h-full flex items-center justify-center bg-gray-100 dark:bg-gray-700">
                        <svg
                          className="w-8 h-8 text-gray-400 dark:text-gray-500"
                          fill="none"
                          viewBox="0 0 24 24"
                          stroke="currentColor"
                        >
                          <path
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            strokeWidth={2}
                            d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                          />
                        </svg>
                      </div>
                    ) : (
                      <img
                        src={displayUrl}
                        alt={`Photo ${index + 1}`}
                        className="w-full h-full object-cover cursor-pointer"
                        onClick={() => window.open(displayUrl, "_blank")}
                        onError={(e) => {
                          // Handle broken images
                          const target = e.target as HTMLImageElement;
                          target.style.display = "none";
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
            <svg
              className="w-4 h-4 text-blue-600 dark:text-blue-400"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={2}
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4"
              />
            </svg>
          </div>
          <h3 className="text-base font-medium text-gray-900 dark:text-gray-100 transition-colors duration-300">
            Location Information
          </h3>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {renderField("Property", property?.name)}
          {renderField(
            "Unit",
            formData.unit_id && formData.unit_id !== "common_area"
              ? unit?.name
              : "Common Area / Building-wide"
          )}
        </div>
      </div>

      {/* Request Details */}
      <div className="bg-white dark:bg-gray-800 rounded-lg p-5 shadow-sm border border-gray-100 dark:border-gray-600">
        <div className="flex items-center mb-3">
          <div className="w-9 h-9 bg-orange-50 dark:bg-orange-900/20 rounded-lg flex items-center justify-center mr-3 transition-colors duration-300">
            <svg
              className="w-4 h-4 text-orange-600 dark:text-orange-400"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={2}
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
              />
            </svg>
          </div>
          <h3 className="text-base font-medium text-gray-900 dark:text-gray-100 transition-colors duration-300">
            Request Details
          </h3>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {renderField("Issue Title", formData.issue_title)}
          {renderField("Priority", formData.priority)}
          {renderField("Status", formData.status)}
          {renderField(
            "Vendor",
            vendor ? `${vendor.company_name} (${vendor.trade_category})` : ""
          )}
        </div>
        <div className="mt-4">
          {renderField("Description", formData.description)}
        </div>
        <div className="mt-4">
          {renderField(
            "Preferred Time",
            formData.preferred_time && formData.preferred_time !== ""
              ? formData.preferred_time
              : ""
          )}
        </div>
      </div>

      {/* Additional Information */}
      <div className="bg-white dark:bg-gray-800 rounded-lg p-5 shadow-sm border border-gray-100 dark:border-gray-600">
        <div className="flex items-center mb-3">
          <div className="w-9 h-9 bg-green-50 dark:bg-green-900/20 rounded-lg flex items-center justify-center mr-3 transition-colors duration-300">
            <svg
              className="w-4 h-4 text-green-600 dark:text-green-400"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={2}
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M9 7h6m0 10v-3m-3 3h.01M9 17h.01M9 14h.01M12 14h.01M15 11h.01M12 11h.01M9 11h.01M7 21h10a2 2 0 002-2V5a2 2 0 00-2-2H7a2 2 0 00-2 2v14a2 2 0 002 2z"
              />
            </svg>
          </div>
          <h3 className="text-base font-medium text-gray-900 dark:text-gray-100 transition-colors duration-300">
            Additional Information
          </h3>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {renderField("Tenant", getTenantName(tenant))}
          {renderField(
            "Notify Tenant via Email",
            formData.notify_tenant ? "Yes" : "No"
          )}
          {renderField(
            "Scheduled Date",
            formData.scheduled_date
              ? new Date(formData.scheduled_date).toLocaleDateString()
              : ""
          )}
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
  vendors,
  photoState,
  onUpdateField,
  onFileChange,
  onRemovePhoto,
  onReorderPhotos,
  isViewing,
  isEditMode,
  isLoadingUnits,
  isLoadingTenants,
  isLoadingVendors,
  request,
}) => {
  // If viewing mode, render view component
  if (isViewing) {
    return (
      <MaintenanceViewMode
        formData={formData}
        properties={properties}
        units={units}
        tenants={tenants}
        vendors={vendors}
        request={request}
      />
    );
  }

  const getInputClassName = (fieldName: string): string => {
    const baseClasses =
      "w-full px-4 py-2.5 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all bg-white dark:bg-gray-700 dark:text-gray-100 text-sm";
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
    onUpdateField("photos", newOrder);
    if (onReorderPhotos) {
      onReorderPhotos(newOrder);
    }
  };

  // Helper to render toggle switch
  const ToggleSwitch = ({ checked, onChange, label, description }: {
    checked: boolean;
    onChange: () => void;
    label: string;
    description?: string;
  }) => (
    <label className="flex items-center justify-between cursor-pointer">
      <div>
        <span className="text-sm text-gray-700 dark:text-gray-300">{label}</span>
        {description && <p className="text-xs text-gray-500 dark:text-gray-400">{description}</p>}
      </div>
      <button
        type="button"
        role="switch"
        aria-checked={checked}
        onClick={onChange}
        className={`relative inline-flex h-5 w-9 flex-shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none focus:ring-2 focus:ring-green-500 focus:ring-offset-2 dark:focus:ring-offset-gray-800 ${
          checked ? 'bg-green-500' : 'bg-gray-300 dark:bg-gray-600'
        }`}
      >
        <span
          className={`pointer-events-none inline-block h-4 w-4 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out ${
            checked ? 'translate-x-4' : 'translate-x-0'
          }`}
        />
      </button>
    </label>
  );

  // Get location display info
  const propertyName = request?.property?.name || properties.find(p => p.id === Number(formData.property_id))?.name || "—";
  const unitName = request?.unit?.name || units.find(u => u.id === Number(formData.unit_id))?.name || "Common Area";
  const tenantName = getTenantName(request?.tenant || tenants.find(t => t.id === Number(formData.tenant_id)));

  // EDIT MODE - Task-focused layout
  if (isEditMode) {
    return (
      <div className="p-6 space-y-6">
        {/* Location Context Bar */}
        <div className="flex items-center gap-4 text-sm text-gray-600 dark:text-gray-400 pb-4 border-b border-gray-200 dark:border-gray-700">
          <div className="flex items-center gap-1.5">
            <Building2 className="h-4 w-4" />
            <span>{propertyName}</span>
            <span className="text-gray-400 dark:text-gray-500">•</span>
            <span>{unitName}</span>
          </div>
          {formData.tenant_id && (
            <>
              <span className="text-gray-400 dark:text-gray-500">•</span>
              <div className="flex items-center gap-1.5">
                <User className="h-4 w-4" />
                <span>{tenantName}</span>
              </div>
            </>
          )}
        </div>

        {/* PRIMARY ACTION ZONE - Status & Assignment */}
        <div className="bg-gradient-to-r from-green-50 to-emerald-50 dark:from-green-900/20 dark:to-emerald-900/20 rounded-xl p-5 border border-green-200 dark:border-green-800">
          <h3 className="text-sm font-semibold text-green-800 dark:text-green-300 mb-4 uppercase tracking-wide">
            Status & Assignment
          </h3>

          {/* Status and Priority Row */}
          <div className="grid grid-cols-2 gap-4 mb-4">
            {/* Status Dropdown - Radix UI */}
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">
                Status
              </label>
              <Select.Root
                value={formData.status || "Pending"}
                onValueChange={(value) => onUpdateField("status", value as any)}
              >
                <Select.Trigger className="w-full px-3 py-2.5 border rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-transparent flex items-center justify-between transition-colors text-sm bg-white dark:bg-gray-700 border-gray-200 dark:border-gray-600 hover:border-gray-400 dark:hover:border-gray-500 text-gray-900 dark:text-gray-100">
                  <Select.Value />
                  <Select.Icon><ChevronDown className="h-4 w-4 text-gray-500 dark:text-gray-400" /></Select.Icon>
                </Select.Trigger>
                <Select.Portal>
                  <Select.Content className="overflow-hidden bg-white dark:bg-gray-800 rounded-lg shadow-lg border border-gray-200 dark:border-gray-700 z-[10001]">
                    <Select.Viewport className="p-1">
                      {[
                        { value: "Pending", label: "Pending" },
                        { value: "In Progress", label: "In Progress" },
                        { value: "Scheduled", label: "Scheduled" },
                        { value: "Completed", label: "Completed" },
                        { value: "Cancelled", label: "Cancelled" },
                      ].map((option) => (
                        <Select.Item key={option.value} value={option.value} className="relative flex items-center px-8 py-2 text-sm text-gray-900 dark:text-gray-100 rounded cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-700 outline-none">
                          <Select.ItemText>{option.label}</Select.ItemText>
                          <Select.ItemIndicator className="absolute left-2"><Check className="h-4 w-4" /></Select.ItemIndicator>
                        </Select.Item>
                      ))}
                    </Select.Viewport>
                  </Select.Content>
                </Select.Portal>
              </Select.Root>
            </div>

            {/* Priority Dropdown - Radix UI */}
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">
                Priority
              </label>
              <Select.Root
                value={formData.priority || "Medium"}
                onValueChange={(value) => onUpdateField("priority", value as "Low" | "Medium" | "High")}
              >
                <Select.Trigger className="w-full px-3 py-2.5 border rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-transparent flex items-center justify-between transition-colors text-sm bg-white dark:bg-gray-700 border-gray-200 dark:border-gray-600 hover:border-gray-400 dark:hover:border-gray-500 text-gray-900 dark:text-gray-100">
                  <Select.Value />
                  <Select.Icon><ChevronDown className="h-4 w-4 text-gray-500 dark:text-gray-400" /></Select.Icon>
                </Select.Trigger>
                <Select.Portal>
                  <Select.Content className="overflow-hidden bg-white dark:bg-gray-800 rounded-lg shadow-lg border border-gray-200 dark:border-gray-700 z-[10001]">
                    <Select.Viewport className="p-1">
                      {[
                        { value: "Low", label: "Low" },
                        { value: "Medium", label: "Medium" },
                        { value: "High", label: "High" },
                      ].map((option) => (
                        <Select.Item key={option.value} value={option.value} className="relative flex items-center px-8 py-2 text-sm text-gray-900 dark:text-gray-100 rounded cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-700 outline-none">
                          <Select.ItemText>{option.label}</Select.ItemText>
                          <Select.ItemIndicator className="absolute left-2"><Check className="h-4 w-4" /></Select.ItemIndicator>
                        </Select.Item>
                      ))}
                    </Select.Viewport>
                  </Select.Content>
                </Select.Portal>
              </Select.Root>
            </div>
          </div>

          {/* Vendor Assignment - Radix UI */}
          <div className="mb-4">
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">
              Assign Vendor
            </label>
            <Select.Root
              value={formData.vendor_id || "NONE"}
              onValueChange={(value) =>
                onUpdateField("vendor_id", value === "NONE" ? "" : value)
              }
              disabled={isLoadingVendors}
            >
              <Select.Trigger
                className={`w-full px-3 py-2.5 border rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-transparent flex items-center justify-between transition-colors text-sm ${
                  isLoadingVendors
                    ? "bg-gray-100 dark:bg-gray-900/50 cursor-not-allowed border-gray-300 dark:border-gray-600"
                    : "bg-white dark:bg-gray-700 border-gray-200 dark:border-gray-600 hover:border-gray-400 dark:hover:border-gray-500"
                } text-gray-900 dark:text-gray-100`}
                disabled={isLoadingVendors}
              >
                <Select.Value placeholder="No vendor assigned">
                  {formData.vendor_id && vendors.find((v) => v.id === Number(formData.vendor_id))
                    ? `${vendors.find((v) => v.id === Number(formData.vendor_id))?.company_name} (${vendors.find((v) => v.id === Number(formData.vendor_id))?.trade_category})`
                    : "No vendor assigned"}
                </Select.Value>
                <Select.Icon><ChevronDown className="h-4 w-4 text-gray-500 dark:text-gray-400" /></Select.Icon>
              </Select.Trigger>
              <Select.Portal>
                <Select.Content className="overflow-hidden bg-white dark:bg-gray-800 rounded-lg shadow-lg border border-gray-200 dark:border-gray-700 z-[10001] max-h-80">
                  <Select.Viewport className="p-1">
                    <Select.Item value="NONE" className="relative flex items-center px-8 py-2 text-sm text-gray-900 dark:text-gray-100 rounded cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-700 outline-none">
                      <Select.ItemText>No vendor assigned</Select.ItemText>
                      <Select.ItemIndicator className="absolute left-2"><Check className="h-4 w-4" /></Select.ItemIndicator>
                    </Select.Item>
                    {vendors.map((vendor) => (
                      <Select.Item key={vendor.id} value={String(vendor.id)} className="relative flex items-center px-8 py-2 text-sm text-gray-900 dark:text-gray-100 rounded cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-700 outline-none">
                        <Select.ItemText>
                          <div>
                            <div className="font-medium">{vendor.company_name}</div>
                            <div className="text-xs text-gray-500">{vendor.trade_category} • {vendor.email}</div>
                          </div>
                        </Select.ItemText>
                        <Select.ItemIndicator className="absolute left-2"><Check className="h-4 w-4" /></Select.ItemIndicator>
                      </Select.Item>
                    ))}
                  </Select.Viewport>
                </Select.Content>
              </Select.Portal>
            </Select.Root>
            <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
              Vendor will be notified via email after saving
            </p>
          </div>

          {/* Notify Tenant Toggle */}
          {formData.tenant_id && (
            <ToggleSwitch
              checked={formData.notify_tenant || false}
              onChange={() => onUpdateField("notify_tenant", !formData.notify_tenant)}
              label="Notify tenant of status changes"
              description="Send email updates when status changes"
            />
          )}
        </div>

        {/* Scheduling Section - Only show relevant fields based on status */}
        {(formData.status === "Scheduled" || formData.status === "Completed") && (
          <div className="space-y-4">
            <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300 flex items-center gap-2">
              <Calendar className="h-4 w-4" />
              Scheduling
            </h4>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {/* Scheduled Date */}
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">
                  Scheduled Date
                </label>
                <input
                  type="date"
                  value={formData.scheduled_date || ""}
                  onChange={(e) => onUpdateField("scheduled_date", e.target.value)}
                  className={getInputClassName("scheduled_date")}
                />
              </div>

              {/* Completion Date - only when Completed */}
              {formData.status === "Completed" && (
                <div>
                  <label className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5 flex items-center gap-1.5">
                    <CheckCircle2 className="h-4 w-4 text-green-500" />
                    Completion Date
                  </label>
                  <input
                    type="date"
                    value={formData.completion_date || new Date().toISOString().split('T')[0]}
                    onChange={(e) => onUpdateField("completion_date", e.target.value)}
                    className={getInputClassName("completion_date")}
                  />
                </div>
              )}
            </div>
          </div>
        )}

        {/* Issue Details - Collapsible/Secondary */}
        <div className="space-y-4 pt-4 border-t border-gray-200 dark:border-gray-700">
          <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300">Issue Details</h4>

          {/* Issue Title */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">
              Title <span className="text-red-500">*</span>
            </label>
            <input
              type="text"
              value={formData.issue_title || ""}
              onChange={(e) => onUpdateField("issue_title", e.target.value)}
              placeholder="Brief description of the issue"
              className={getInputClassName("issue_title")}
            />
            {errors.issue_title && (
              <p className="mt-1 text-sm text-red-600 dark:text-red-400">{errors.issue_title}</p>
            )}
          </div>

          {/* Description */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">
              Description
            </label>
            <textarea
              value={formData.description || ""}
              onChange={(e) => onUpdateField("description", e.target.value)}
              rows={3}
              placeholder="Detailed description..."
              className="w-full px-4 py-2.5 border border-gray-200 dark:border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all bg-white dark:bg-gray-700 dark:text-gray-100 resize-none text-sm"
            />
          </div>
        </div>

        {/* Photos Section - At Bottom */}
        <div className="space-y-3 pt-4 border-t border-gray-200 dark:border-gray-700">
          <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300">
            Photos {formData.photos && formData.photos.length > 0 && `(${formData.photos.length})`}
          </h4>
          <MaintenancePhotoUpload
            photos={formData.photos || []}
            photoState={photoState}
            onFileChange={handleDropzoneFileChange}
            onRemovePhoto={onRemovePhoto}
            onReorderPhotos={handlePhotoReorder}
            disabled={false}
          />
        </div>
      </div>
    );
  }

  // CREATE MODE - Original layout with some improvements
  return (
    <div className="space-y-4 p-6">
      {/* Location Section */}
      <div className="space-y-3">
        <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300">Location</h4>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          {/* Property */}
          <div>
            <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
              Property <span className="text-red-500">*</span>
            </label>
            <select
              value={formData.property_id || ""}
              onChange={(e) => onUpdateField("property_id", e.target.value)}
              className={getInputClassName("property_id")}
            >
              <option value="">Select Property</option>
              {properties.map((p) => (
                <option key={p.id} value={p.id}>{p.name}</option>
              ))}
            </select>
            {errors.property_id && (
              <p className="mt-1 text-xs text-red-600 dark:text-red-400">{errors.property_id}</p>
            )}
          </div>

          {/* Unit */}
          <div>
            <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">Unit</label>
            <select
              value={formData.unit_id || ""}
              onChange={(e) => onUpdateField("unit_id", e.target.value)}
              disabled={!formData.property_id || isLoadingUnits}
              className={getInputClassName("unit_id")}
            >
              <option value="">{isLoadingUnits ? "Loading..." : "Select Unit"}</option>
              <option value="common_area">Common Area</option>
              {units.map((u) => (
                <option key={u.id} value={u.id}>{u.name}</option>
              ))}
            </select>
          </div>

          {/* Tenant */}
          <div>
            <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">Tenant</label>
            <select
              value={formData.tenant_id || ""}
              onChange={(e) => onUpdateField("tenant_id", e.target.value)}
              disabled={!formData.property_id || isLoadingTenants}
              className={getInputClassName("tenant_id")}
            >
              <option value="">{isLoadingTenants ? "Loading..." : "Select Tenant (optional)"}</option>
              {tenants.map((t) => (
                <option key={t.id} value={t.id}>{getTenantName(t)}</option>
              ))}
            </select>
          </div>
        </div>

        {/* Notify Tenant Toggle */}
        {formData.tenant_id && (
          <ToggleSwitch
            checked={formData.notify_tenant || false}
            onChange={() => onUpdateField("notify_tenant", !formData.notify_tenant)}
            label="Notify Tenant via Email"
            description="Receive status updates"
          />
        )}
      </div>

      {/* Issue Details */}
      <div className="space-y-3 pt-4 border-t border-gray-200 dark:border-gray-700">
        <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300">Issue Details</h4>

        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">
            Issue Title <span className="text-red-500">*</span>
          </label>
          <input
            type="text"
            value={formData.issue_title || ""}
            onChange={(e) => onUpdateField("issue_title", e.target.value)}
            placeholder="Brief description of the issue"
            className={getInputClassName("issue_title")}
          />
          {errors.issue_title && (
            <p className="mt-1 text-sm text-red-600 dark:text-red-400">{errors.issue_title}</p>
          )}
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">Description</label>
          <textarea
            value={formData.description || ""}
            onChange={(e) => onUpdateField("description", e.target.value)}
            rows={3}
            placeholder="Detailed description..."
            className="w-full px-4 py-2.5 border border-gray-200 dark:border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all bg-white dark:bg-gray-700 dark:text-gray-100 resize-none text-sm"
          />
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">Priority</label>
            <select
              value={formData.priority || ""}
              onChange={(e) => onUpdateField("priority", e.target.value as "Low" | "Medium" | "High")}
              className={getInputClassName("priority")}
            >
              <option value="Low">Low</option>
              <option value="Medium">Medium</option>
              <option value="High">High</option>
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">Status</label>
            <select
              value={formData.status || ""}
              onChange={(e) => onUpdateField("status", e.target.value as any)}
              className={getInputClassName("status")}
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

      {/* Assignment & Scheduling */}
      <div className="space-y-3 pt-4 border-t border-gray-200 dark:border-gray-700">
        <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300">Assignment & Scheduling</h4>

        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">Assign Vendor</label>
          <Select.Root
            value={formData.vendor_id || "NONE"}
            onValueChange={(value) => onUpdateField("vendor_id", value === "NONE" ? "" : value)}
            disabled={isLoadingVendors}
          >
            <Select.Trigger
              className={`w-full px-4 py-2.5 pr-9 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 flex items-center justify-between text-sm ${
                isLoadingVendors ? "bg-gray-100 cursor-not-allowed" : "bg-white dark:bg-gray-700"
              } border-gray-200 dark:border-gray-600 text-gray-900 dark:text-gray-100`}
            >
              <Select.Value placeholder="Select a vendor...">
                {formData.vendor_id && vendors.find((v) => v.id === Number(formData.vendor_id))
                  ? `${vendors.find((v) => v.id === Number(formData.vendor_id))?.company_name}`
                  : "No vendor assigned"}
              </Select.Value>
              <ChevronDown className="h-4 w-4 text-gray-500" />
            </Select.Trigger>
            <Select.Portal>
              <Select.Content className="bg-white dark:bg-gray-800 rounded-lg shadow-lg border border-gray-200 dark:border-gray-700 z-[10001] max-h-80">
                <Select.Viewport className="p-1">
                  <Select.Item value="NONE" className="relative flex items-center px-8 py-2 text-sm rounded cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-700 outline-none">
                    <Select.ItemText>No vendor assigned</Select.ItemText>
                    <Select.ItemIndicator className="absolute left-2"><Check className="h-4 w-4" /></Select.ItemIndicator>
                  </Select.Item>
                  {vendors.map((vendor) => (
                    <Select.Item key={vendor.id} value={String(vendor.id)} className="relative flex items-center px-8 py-2 text-sm rounded cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-700 outline-none">
                      <Select.ItemText>
                        <div>
                          <div className="font-medium">{vendor.company_name}</div>
                          <div className="text-xs text-gray-500">{vendor.trade_category} • {vendor.email}</div>
                        </div>
                      </Select.ItemText>
                      <Select.ItemIndicator className="absolute left-2"><Check className="h-4 w-4" /></Select.ItemIndicator>
                    </Select.Item>
                  ))}
                </Select.Viewport>
              </Select.Content>
            </Select.Portal>
          </Select.Root>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">Scheduled Date</label>
          <input
            type="date"
            value={formData.scheduled_date || ""}
            onChange={(e) => onUpdateField("scheduled_date", e.target.value)}
            className={getInputClassName("scheduled_date")}
          />
        </div>
      </div>

      {/* Photos Section */}
      <div className="space-y-3 pt-4 border-t border-gray-200 dark:border-gray-700">
        <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300">
          Photos {formData.photos && formData.photos.length > 0 && `(${formData.photos.length})`}
        </h4>
        <MaintenancePhotoUpload
          photos={formData.photos || []}
          photoState={photoState}
          onFileChange={handleDropzoneFileChange}
          onRemovePhoto={onRemovePhoto}
          onReorderPhotos={handlePhotoReorder}
          disabled={false}
        />
      </div>
    </div>
  );
};

export default MaintenanceFormFields;
