import React, { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { X, AlertCircle, MapPin, Image as ImageIcon } from "lucide-react";
import * as Select from "@radix-ui/react-select";
import { ChevronDown, Check } from "lucide-react";
import { useVendors } from "../../hooks/useVendorQueries";
import PhotoPreviewModal from "./PhotoPreviewModal";
import { getSecurePhotoUrl } from "../../utils/api/maintenance";
import type { MaintenanceRequest } from "../../types/tenant";
import { MaintenancePriority, MaintenanceStatus } from "../../types/tenant";

interface MaintenanceTriageModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (data: TriageData) => Promise<void>;
  request: MaintenanceRequest;
  isSubmitting?: boolean;
}

interface TriageData {
  priority: MaintenancePriority;
  status: MaintenanceStatus;
  vendor_id?: number;
  scheduled_date?: string;
}

const MaintenanceTriageModal: React.FC<MaintenanceTriageModalProps> = ({
  isOpen,
  onClose,
  onSubmit,
  request,
  isSubmitting = false,
}) => {
  const [triageData, setTriageData] = useState<TriageData>({
    priority: request.priority || MaintenancePriority.MEDIUM,
    status: request.status,
  });
  const [error, setError] = useState<string | null>(null);
  const [previewIndex, setPreviewIndex] = useState<number | null>(null);
  const [securePhotoUrls, setSecurePhotoUrls] = useState<string[]>([]);
  const [loadingPhotos, setLoadingPhotos] = useState(false);

  const { data: vendorsData, isLoading: isLoadingVendors } = useVendors();

  // Load secure photo URLs
  useEffect(() => {
    const loadPhotos = async () => {
      if (!request.photos || request.photos.length === 0) return;

      setLoadingPhotos(true);
      try {
        const urls = await Promise.all(
          request.photos.map(async (photo) => {
            try {
              const { secure_url } = await getSecurePhotoUrl(photo);
              return secure_url;
            } catch {
              return photo;
            }
          })
        );
        setSecurePhotoUrls(urls);
      } catch (error) {
        console.error("Failed to load photos:", error);
      } finally {
        setLoadingPhotos(false);
      }
    };

    if (isOpen) {
      loadPhotos();
    }
  }, [isOpen, request.photos]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    try {
      await onSubmit(triageData);
      onClose();
    } catch (err: any) {
      setError(err?.message || "Failed to update request");
    }
  };

  const updateField = <K extends keyof TriageData>(field: K, value: TriageData[K]) => {
    setTriageData((prev) => ({ ...prev, [field]: value }));
  };

  if (!isOpen) return null;

  return (
    <AnimatePresence>
      <div className="fixed inset-0 z-[9999] flex items-center justify-center">
        {/* Backdrop */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="absolute inset-0 bg-black/60 backdrop-blur-sm"
          onClick={onClose}
        />

        {/* Modal */}
        <motion.div
          initial={{ scale: 0.95, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          exit={{ scale: 0.95, opacity: 0 }}
          className="relative w-full max-w-4xl max-h-[90vh] bg-white dark:bg-gray-800 rounded-xl shadow-2xl overflow-hidden z-10"
          onClick={(e) => e.stopPropagation()}
        >
          {/* Header */}
          <div className="sticky top-0 z-20 bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 px-6 py-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-3">
                <div className="p-2 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
                  <AlertCircle className="h-6 w-6 text-blue-600 dark:text-blue-400" />
                </div>
                <div>
                  <h2 className="text-xl font-bold text-gray-900 dark:text-gray-100">
                    Review & Assign Maintenance Request
                  </h2>
                  <p className="text-sm text-gray-500 dark:text-gray-400">
                    Review tenant's request and assign priority, vendor, and schedule
                  </p>
                </div>
              </div>
              <button
                onClick={onClose}
                disabled={isSubmitting}
                className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors disabled:opacity-50"
              >
                <X className="h-5 w-5 text-gray-500 dark:text-gray-400" />
              </button>
            </div>
          </div>

          {/* Content */}
          <div className="overflow-y-auto px-6 pt-6 pb-6" style={{ maxHeight: "calc(90vh - 160px)" }}>
            {/* Compact Triage Banner - scrolls with content */}
            <div className="mb-4 p-3 bg-blue-50 dark:bg-blue-900/20 border-l-4 border-blue-500 dark:border-blue-400 rounded">
              <p className="text-xs text-blue-700 dark:text-blue-300">
                <span className="font-semibold">Triage Required:</span> Set priority, assign vendor, schedule date, and update status
              </p>
            </div>

            {error && (
              <div className="mb-4 p-3 bg-red-50 dark:bg-red-900/20 border-l-4 border-red-500 rounded">
                <div className="flex items-center">
                  <AlertCircle className="h-4 w-4 text-red-500 mr-2 flex-shrink-0" />
                  <span className="text-xs text-red-700 dark:text-red-300">{error}</span>
                </div>
              </div>
            )}
            <form onSubmit={handleSubmit} className="space-y-6">
              {/* Request Details - Read Only */}
              <div className="bg-gray-50 dark:bg-gray-900 rounded-lg p-4 border border-gray-200 dark:border-gray-700">
                <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">
                  Request Details
                </h3>
                
                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                      Issue Title
                    </label>
                    <p className="text-base text-gray-900 dark:text-gray-100 font-medium">
                      {request.issue_title}
                    </p>
                  </div>

                  {request.description && (
                    <div>
                      <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                        Description
                      </label>
                      <p className="text-sm text-gray-700 dark:text-gray-300">
                        {request.description}
                      </p>
                    </div>
                  )}

                  {request.preferred_time && (
                    <div>
                      <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                        Preferred Time
                      </label>
                      <p className="text-sm text-gray-700 dark:text-gray-300">
                        {request.preferred_time}
                      </p>
                    </div>
                  )}
                </div>
              </div>

              {/* Photos */}
              {request.photos && request.photos.length > 0 && (
                <div className="bg-white dark:bg-gray-800 rounded-lg p-4 border border-gray-200 dark:border-gray-700">
                  <div className="flex items-center mb-3">
                    <ImageIcon className="h-5 w-5 text-purple-600 dark:text-purple-400 mr-2" />
                    <h3 className="text-base font-semibold text-gray-900 dark:text-gray-100">
                      Photos ({request.photos.length})
                    </h3>
                    <span className="ml-2 text-xs text-gray-500 dark:text-gray-400">
                      Submitted by tenant
                    </span>
                  </div>

                  {loadingPhotos ? (
                    <div className="flex items-center justify-center py-8">
                      <div className="w-8 h-8 border-4 border-purple-200 dark:border-purple-800 border-t-purple-600 dark:border-t-purple-400 rounded-full animate-spin" />
                    </div>
                  ) : (
                    <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-3">
                      {securePhotoUrls.map((url, index) => (
                        <button
                          key={index}
                          type="button"
                          onClick={() => setPreviewIndex(index)}
                          className="relative aspect-square bg-gray-100 dark:bg-gray-700 rounded-lg overflow-hidden border border-gray-200 dark:border-gray-600 group cursor-pointer"
                        >
                          <img
                            src={url}
                            alt={`Photo ${index + 1}`}
                            className="w-full h-full object-cover"
                          />
                          <div className="absolute inset-0 bg-black/50 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
                            <ImageIcon className="w-8 h-8 text-white" />
                          </div>
                        </button>
                      ))}
                    </div>
                  )}

                  {previewIndex !== null && (
                    <PhotoPreviewModal
                      photos={securePhotoUrls}
                      initialIndex={previewIndex}
                      isOpen={previewIndex !== null}
                      onClose={() => setPreviewIndex(null)}
                    />
                  )}
                </div>
              )}

              {/* Location Info - Read Only */}
              <div className="bg-gray-50 dark:bg-gray-900 rounded-lg p-4 border border-gray-200 dark:border-gray-700">
                <div className="flex items-center mb-3">
                  <MapPin className="h-5 w-5 text-blue-600 dark:text-blue-400 mr-2" />
                  <h3 className="text-base font-semibold text-gray-900 dark:text-gray-100">
                    Location Information
                  </h3>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <div>
                    <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">
                      Property
                    </label>
                    <p className="text-sm text-gray-900 dark:text-gray-100">
                      {request.property?.name || 'N/A'}
                    </p>
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">
                      Unit
                    </label>
                    <p className="text-sm text-gray-900 dark:text-gray-100">
                      {request.unit?.name || 'Common Area'}
                    </p>
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">
                      Tenant
                    </label>
                    <p className="text-sm text-gray-900 dark:text-gray-100">
                      {request.tenant
                        ? `${request.tenant.first_name || ''} ${request.tenant.last_name || ''}`.trim() || request.tenant.company_name || 'N/A'
                        : 'N/A'}
                    </p>
                  </div>
                </div>
              </div>

              {/* Vendor Notification Context Banner */}
              <div className="bg-gradient-to-r from-blue-50 to-indigo-50 dark:from-blue-900/20 dark:to-indigo-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4">
                <div className="flex items-start gap-3">
                  <div className="flex-shrink-0 mt-0.5">
                    <svg className="w-5 h-5 text-blue-600 dark:text-blue-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                  </div>
                  <div className="flex-1 text-sm">
                    <p className="font-medium text-blue-900 dark:text-blue-100 mb-1">
                      Vendor Notification System
                    </p>
                    <p className="text-blue-700 dark:text-blue-300 leading-relaxed">
                      When you assign a vendor below, they will automatically receive an email with the request details, photos, tenant contact info, and scheduling information. You and your team will also receive a confirmation notification.
                    </p>
                  </div>
                </div>
              </div>

              {/* Triage Fields - Editable */}
              <div className="bg-white dark:bg-gray-800 rounded-lg p-4 border border-gray-200 dark:border-gray-700">
                <h3 className="text-base font-semibold text-gray-900 dark:text-gray-100 mb-4">
                  Assignment & Scheduling
                </h3>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {/* Priority */}
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                      Priority <span className="text-red-500">*</span>
                    </label>
                    <Select.Root
                      value={triageData.priority}
                      onValueChange={(value) => updateField("priority", value as MaintenancePriority)}
                    >
                      <Select.Trigger className="flex items-center justify-between w-full px-3 py-2 text-left bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg hover:border-gray-400 dark:hover:border-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500 dark:focus:ring-blue-400 focus:border-transparent transition-colors cursor-pointer">
                        <Select.Value />
                        <Select.Icon>
                          <ChevronDown className="h-4 w-4 text-gray-500" />
                        </Select.Icon>
                      </Select.Trigger>
                      <Select.Portal>
                        <Select.Content className="overflow-hidden bg-white dark:bg-gray-800 rounded-lg shadow-lg border border-gray-200 dark:border-gray-700 z-[9999]">
                          <Select.Viewport className="p-1">
                            {Object.values(MaintenancePriority).map((priority) => (
                              <Select.Item
                                key={priority}
                                value={priority}
                                className="relative flex items-center px-8 py-2 text-sm text-gray-900 dark:text-gray-100 rounded-md hover:bg-gray-100 dark:hover:bg-gray-700 cursor-pointer outline-none data-[highlighted]:bg-gray-100 dark:data-[highlighted]:bg-gray-700"
                              >
                                <Select.ItemText>{priority}</Select.ItemText>
                                <Select.ItemIndicator className="absolute left-2">
                                  <Check className="h-4 w-4" />
                                </Select.ItemIndicator>
                              </Select.Item>
                            ))}
                          </Select.Viewport>
                        </Select.Content>
                      </Select.Portal>
                    </Select.Root>
                  </div>

                  {/* Status */}
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                      Status <span className="text-red-500">*</span>
                    </label>
                    <Select.Root
                      value={triageData.status}
                      onValueChange={(value) => updateField("status", value as MaintenanceStatus)}
                    >
                      <Select.Trigger className="flex items-center justify-between w-full px-3 py-2 text-left bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg hover:border-gray-400 dark:hover:border-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500 dark:focus:ring-blue-400 focus:border-transparent transition-colors cursor-pointer">
                        <Select.Value />
                        <Select.Icon>
                          <ChevronDown className="h-4 w-4 text-gray-500" />
                        </Select.Icon>
                      </Select.Trigger>
                      <Select.Portal>
                        <Select.Content className="overflow-hidden bg-white dark:bg-gray-800 rounded-lg shadow-lg border border-gray-200 dark:border-gray-700 z-[9999]">
                          <Select.Viewport className="p-1">
                            {Object.values(MaintenanceStatus)
                              .filter((status) => status !== MaintenanceStatus.NEW)
                              .map((status) => (
                                <Select.Item
                                  key={status}
                                  value={status}
                                  className="relative flex items-center px-8 py-2 text-sm text-gray-900 dark:text-gray-100 rounded-md hover:bg-gray-100 dark:hover:bg-gray-700 cursor-pointer outline-none data-[highlighted]:bg-gray-100 dark:data-[highlighted]:bg-gray-700"
                                >
                                  <Select.ItemText>{status}</Select.ItemText>
                                  <Select.ItemIndicator className="absolute left-2">
                                    <Check className="h-4 w-4" />
                                  </Select.ItemIndicator>
                                </Select.Item>
                              ))}
                          </Select.Viewport>
                        </Select.Content>
                      </Select.Portal>
                    </Select.Root>
                  </div>

                  {/* Vendor - Full Width */}
                  <div className="md:col-span-2">
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                      Assign to Vendor
                    </label>
                    <Select.Root
                      value={triageData.vendor_id?.toString() || "none"}
                      onValueChange={(value) => updateField("vendor_id", value === "none" ? undefined : Number(value))}
                      disabled={isLoadingVendors}
                    >
                      <Select.Trigger className="flex items-center justify-between w-full px-3 py-2 text-left bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg hover:border-gray-400 dark:hover:border-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500 dark:focus:ring-blue-400 focus:border-transparent transition-colors cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed">
                        <Select.Value placeholder={isLoadingVendors ? "Loading vendors..." : "Select Vendor (optional)"}>
                          {triageData.vendor_id && vendorsData?.vendors.find((v) => v.id === Number(triageData.vendor_id))
                            ? (() => {
                                const vendor = vendorsData.vendors.find((v) => v.id === Number(triageData.vendor_id));
                                if (vendor) {
                                  const contact = vendor.email || vendor.phone;
                                  return (
                                    <span className="flex flex-col">
                                      <span className="font-medium">{vendor.company_name}</span>
                                      <span className="text-xs text-gray-500 dark:text-gray-400">
                                        {vendor.trade_category}{contact ? ` • ${contact}` : ""}
                                      </span>
                                    </span>
                                  );
                                }
                                return "Select Vendor (optional)";
                              })()
                            : "Select Vendor (optional)"}
                        </Select.Value>
                        <Select.Icon>
                          <ChevronDown className="h-4 w-4 text-gray-500" />
                        </Select.Icon>
                      </Select.Trigger>
                      <Select.Portal>
                        <Select.Content className="overflow-hidden bg-white dark:bg-gray-800 rounded-lg shadow-lg border border-gray-200 dark:border-gray-700 z-[9999] max-h-[300px]">
                          <Select.Viewport className="p-1">
                            <Select.Item
                              value="none"
                              className="relative flex items-center px-8 py-2 text-sm text-gray-900 dark:text-gray-100 rounded-md hover:bg-gray-100 dark:hover:bg-gray-700 cursor-pointer outline-none data-[highlighted]:bg-gray-100 dark:data-[highlighted]:bg-gray-700"
                            >
                              <Select.ItemText>None</Select.ItemText>
                              <Select.ItemIndicator className="absolute left-2">
                                <Check className="h-4 w-4" />
                              </Select.ItemIndicator>
                            </Select.Item>
                            {vendorsData?.vendors.map((vendor) => {
                              const contact = vendor.email || vendor.phone;
                              return (
                                <Select.Item
                                  key={vendor.id}
                                  value={vendor.id.toString()}
                                  className="relative flex items-start px-8 py-2.5 text-sm text-gray-900 dark:text-gray-100 rounded-md hover:bg-gray-100 dark:hover:bg-gray-700 cursor-pointer outline-none data-[highlighted]:bg-gray-100 dark:data-[highlighted]:bg-gray-700"
                                >
                                  <Select.ItemText>
                                    <div className="flex flex-col">
                                      <span className="font-medium">{vendor.company_name}</span>
                                      <span className="text-xs text-gray-500 dark:text-gray-400">
                                        {vendor.trade_category}{contact ? ` • ${contact}` : ""}
                                      </span>
                                    </div>
                                  </Select.ItemText>
                                  <Select.ItemIndicator className="absolute left-2 top-3">
                                    <Check className="h-4 w-4" />
                                  </Select.ItemIndicator>
                                </Select.Item>
                              );
                            })}
                          </Select.Viewport>
                        </Select.Content>
                      </Select.Portal>
                    </Select.Root>
                    <p className="mt-2 text-xs text-gray-500 dark:text-gray-400">
                      The vendor will coordinate with the tenant to schedule the work
                    </p>
                  </div>
                </div>
              </div>
            </form>
          </div>

          {/* Footer */}
          <div className="sticky bottom-0 bg-gray-50 dark:bg-gray-900 border-t border-gray-200 dark:border-gray-700 px-6 py-4">
            <div className="flex items-center justify-between">
              <p className="text-sm text-gray-500 dark:text-gray-400">
                <span className="text-red-500">*</span> Required fields
              </p>
              <div className="flex space-x-3">
                <button
                  type="button"
                  onClick={onClose}
                  disabled={isSubmitting}
                  className="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-600 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-gray-500 disabled:opacity-50 transition-colors cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  onClick={handleSubmit}
                  disabled={isSubmitting}
                  className="px-5 py-2 text-sm font-medium text-white bg-green-600 hover:bg-green-700 dark:bg-green-500 dark:hover:bg-green-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors cursor-pointer flex items-center space-x-2"
                >
                  {isSubmitting ? (
                    <>
                      <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                      <span>Updating...</span>
                    </>
                  ) : (
                    <span>Update Request</span>
                  )}
                </button>
              </div>
            </div>
          </div>
        </motion.div>
      </div>
    </AnimatePresence>
  );
};

export default MaintenanceTriageModal;

