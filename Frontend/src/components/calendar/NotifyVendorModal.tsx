/**
 * NotifyVendorModal Component
 * 
 * Modal for manually notifying vendors about maintenance requests.
 * Features:
 * - Preview of the email that will be sent
 * - Ability to add a custom message
 * - Shows vendor contact information
 * - Confirmation before sending
 */

import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, Mail, AlertCircle, Send, User, Building2, Wrench } from 'lucide-react';
import type { MaintenanceRequest } from '../../types/tenant';

interface NotifyVendorModalProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: (customMessage: string) => Promise<void>;
  maintenanceRequest: MaintenanceRequest;
  isSubmitting?: boolean;
}

export const NotifyVendorModal: React.FC<NotifyVendorModalProps> = ({
  isOpen,
  onClose,
  onConfirm,
  maintenanceRequest,
  isSubmitting = false,
}) => {
  const [customMessage, setCustomMessage] = useState('');
  const [showPreview, setShowPreview] = useState(true);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    await onConfirm(customMessage);
  };

  const handleClose = () => {
    if (!isSubmitting) {
      setCustomMessage('');
      setShowPreview(true);
      onClose();
    }
  };

  if (!isOpen) return null;

  const vendor = maintenanceRequest.vendor;
  const property = maintenanceRequest.property;
  const unit = maintenanceRequest.unit;

  return (
    <AnimatePresence>
      <div className="fixed inset-0 z-[9999] flex items-center justify-center">
        {/* Backdrop */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="absolute inset-0 bg-black/60 backdrop-blur-sm"
          onClick={handleClose}
        />

        {/* Modal */}
        <motion.div
          initial={{ scale: 0.95, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          exit={{ scale: 0.95, opacity: 0 }}
          className="relative w-full max-w-3xl max-h-[90vh] bg-white dark:bg-gray-800 rounded-xl shadow-2xl overflow-hidden z-10"
          onClick={(e) => e.stopPropagation()}
        >
          {/* Header */}
          <div className="sticky top-0 z-20 bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 px-6 py-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-3">
                <div className="p-2 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
                  <Mail className="h-6 w-6 text-blue-600 dark:text-blue-400" />
                </div>
                <div>
                  <h2 className="text-xl font-bold text-gray-900 dark:text-gray-100">
                    Notify Vendor
                  </h2>
                  <p className="text-sm text-gray-500 dark:text-gray-400">
                    Send email notification to {vendor?.company_name || 'vendor'}
                  </p>
                </div>
              </div>
              <button
                onClick={handleClose}
                disabled={isSubmitting}
                className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors disabled:opacity-50"
              >
                <X className="h-5 w-5 text-gray-500 dark:text-gray-400" />
              </button>
            </div>
          </div>

          {/* Content */}
          <div className="overflow-y-auto px-6 pt-6 pb-6" style={{ maxHeight: 'calc(90vh - 160px)' }}>
            <form onSubmit={handleSubmit} className="space-y-6">
              {/* Vendor Information */}
              {vendor && (
                <div className="bg-gradient-to-r from-blue-50 to-indigo-50 dark:from-blue-900/20 dark:to-indigo-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4">
                  <div className="flex items-start gap-3">
                    <div className="flex-shrink-0 mt-1">
                      <User className="w-5 h-5 text-blue-600 dark:text-blue-400" />
                    </div>
                    <div className="flex-1">
                      <h3 className="font-semibold text-blue-900 dark:text-blue-100 mb-2">
                        Vendor Contact
                      </h3>
                      <div className="space-y-1 text-sm text-blue-700 dark:text-blue-300">
                        <p><strong>Company:</strong> {vendor.company_name}</p>
                        {vendor.contact_person && (
                          <p><strong>Contact:</strong> {vendor.contact_person}</p>
                        )}
                        <p><strong>Trade:</strong> {vendor.trade_category}</p>
                        {vendor.email && (
                          <p><strong>Email:</strong> {vendor.email}</p>
                        )}
                        {vendor.phone && (
                          <p><strong>Phone:</strong> {vendor.phone}</p>
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {/* Request Summary */}
              <div className="bg-gray-50 dark:bg-gray-900 rounded-lg p-4 border border-gray-200 dark:border-gray-700">
                <h3 className="text-base font-semibold text-gray-900 dark:text-gray-100 mb-3 flex items-center gap-2">
                  <Wrench className="w-5 h-5 text-gray-600 dark:text-gray-400" />
                  Request Details
                </h3>
                <div className="space-y-2 text-sm">
                  <div className="flex items-start gap-2">
                    <Building2 className="w-4 h-4 text-gray-500 mt-0.5 flex-shrink-0" />
                    <div>
                      <p className="font-medium text-gray-900 dark:text-gray-100">
                        {property?.name || 'Unknown Property'}
                      </p>
                      {unit && (
                        <p className="text-gray-600 dark:text-gray-400">Unit: {unit.name}</p>
                      )}
                    </div>
                  </div>
                  <div className="pt-2 border-t border-gray-200 dark:border-gray-700">
                    <p className="font-medium text-gray-900 dark:text-gray-100">
                      {maintenanceRequest.issue_title}
                    </p>
                    {maintenanceRequest.description && (
                      <p className="text-gray-600 dark:text-gray-400 mt-1">
                        {maintenanceRequest.description}
                      </p>
                    )}
                  </div>
                </div>
              </div>

              {/* Custom Message */}
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  Add Custom Message (Optional)
                </label>
                <textarea
                  value={customMessage}
                  onChange={(e) => setCustomMessage(e.target.value)}
                  placeholder="Add any additional notes or instructions for the vendor..."
                  rows={4}
                  disabled={isSubmitting}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 dark:focus:ring-blue-400 focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 placeholder-gray-500 dark:placeholder-gray-400 disabled:opacity-50 disabled:cursor-not-allowed"
                />
                <p className="mt-2 text-xs text-gray-500 dark:text-gray-400">
                  This message will be included in the email notification to the vendor.
                </p>
              </div>

              {/* Email Preview Toggle */}
              <div>
                <button
                  type="button"
                  onClick={() => setShowPreview(!showPreview)}
                  className="text-sm font-medium text-blue-600 dark:text-blue-400 hover:text-blue-700 dark:hover:text-blue-300 transition-colors"
                >
                  {showPreview ? '▼' : '▶'} {showPreview ? 'Hide' : 'Show'} Email Preview
                </button>
              </div>

              {/* Email Preview */}
              {showPreview && (
                <div className="bg-white dark:bg-gray-900 border-2 border-gray-200 dark:border-gray-700 rounded-lg p-6">
                  <div className="flex items-center gap-2 mb-4 pb-3 border-b border-gray-200 dark:border-gray-700">
                    <Mail className="w-5 h-5 text-gray-600 dark:text-gray-400" />
                    <h3 className="font-semibold text-gray-900 dark:text-gray-100">
                      Email Preview
                    </h3>
                  </div>
                  
                  <div className="space-y-4 text-sm">
                    <div>
                      <p className="text-gray-600 dark:text-gray-400 mb-1">Subject:</p>
                      <p className="font-medium text-gray-900 dark:text-gray-100">
                        Service Request - {property?.name || 'Property'}
                      </p>
                    </div>

                    <div className="pt-3 border-t border-gray-200 dark:border-gray-700">
                      <p className="text-gray-900 dark:text-gray-100 mb-3">
                        Hi {vendor?.contact_person || vendor?.company_name},
                      </p>
                      
                      <p className="text-gray-700 dark:text-gray-300 mb-3">
                        We are requesting your services for a maintenance issue at one of our properties.
                      </p>

                      {customMessage && (
                        <div className="my-4 p-3 bg-blue-50 dark:bg-blue-900/20 border-l-4 border-blue-500 rounded">
                          <p className="font-semibold text-blue-900 dark:text-blue-100">
                            "{customMessage}"
                          </p>
                        </div>
                      )}

                      <div className="my-4 p-4 bg-gray-50 dark:bg-gray-800 rounded-lg space-y-2">
                        <p className="font-medium text-gray-900 dark:text-gray-100">
                          📍 Property: {property?.name || 'Unknown'}
                        </p>
                        {unit && (
                          <p className="text-gray-700 dark:text-gray-300">
                            🏠 Unit: {unit.name}
                          </p>
                        )}
                        <p className="text-gray-700 dark:text-gray-300">
                          🔧 Issue: {maintenanceRequest.issue_title}
                        </p>
                        <p className="text-gray-700 dark:text-gray-300">
                          ⚡ Priority: {maintenanceRequest.priority}
                        </p>
                      </div>

                      <p className="text-gray-700 dark:text-gray-300">
                        Please contact us to discuss the work, pricing, and scheduling.
                      </p>
                    </div>
                  </div>
                </div>
              )}

              {/* Info Notice */}
              <div className="bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg p-4">
                <div className="flex items-start gap-3">
                  <AlertCircle className="w-5 h-5 text-yellow-600 dark:text-yellow-400 flex-shrink-0 mt-0.5" />
                  <div className="text-sm text-yellow-800 dark:text-yellow-200">
                    <p className="font-medium mb-1">Before sending:</p>
                    <ul className="list-disc list-inside space-y-1 text-yellow-700 dark:text-yellow-300">
                      <li>Verify the vendor email address is correct</li>
                      <li>Ensure all request details are accurate</li>
                      <li>The vendor will receive the full request details including photos</li>
                    </ul>
                  </div>
                </div>
              </div>
            </form>
          </div>

          {/* Footer */}
          <div className="sticky bottom-0 bg-gray-50 dark:bg-gray-900 border-t border-gray-200 dark:border-gray-700 px-6 py-4">
            <div className="flex items-center justify-end space-x-3">
              <button
                type="button"
                onClick={handleClose}
                disabled={isSubmitting}
                className="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-600 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-gray-500 disabled:opacity-50 transition-colors"
              >
                Cancel
              </button>
              <button
                type="submit"
                onClick={handleSubmit}
                disabled={isSubmitting || !vendor?.email}
                className="px-5 py-2 text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 dark:bg-blue-500 dark:hover:bg-blue-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center space-x-2"
              >
                {isSubmitting ? (
                  <>
                    <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                    <span>Sending...</span>
                  </>
                ) : (
                  <>
                    <Send className="w-4 h-4" />
                    <span>Send Notification</span>
                  </>
                )}
              </button>
            </div>
          </div>
        </motion.div>
      </div>
    </AnimatePresence>
  );
};

