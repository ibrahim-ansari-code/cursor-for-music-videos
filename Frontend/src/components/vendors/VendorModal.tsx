import React, { useState, useEffect } from "react";
import * as Select from "@radix-ui/react-select";
import { ChevronDown, Check } from "lucide-react";
import type { VendorContact, VendorContactCreate, VendorContactUpdate } from "../../types/vendor";
import { COMMON_TRADE_CATEGORIES } from "../../types/vendor";
import { formatPhoneNumber, validatePhone, validateEmail } from "../../utils/validation";

interface VendorModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (data: VendorContactCreate | VendorContactUpdate) => Promise<void>;
  vendor?: VendorContact | null;
  isViewing?: boolean;
}

const VendorModal: React.FC<VendorModalProps> = ({
  isOpen,
  onClose,
  onSubmit,
  vendor,
  isViewing = false,
}) => {
  const [formData, setFormData] = useState({
    company_name: "",
    contact_person: "",
    trade_category: "",
    phone: "",
    email: "",
    notes: "",
    is_active: true,
    is_favorite: false,
    personal_rating: null as number | null,
  });
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errors, setErrors] = useState<Record<string, string>>({});

  // Initialize form when vendor changes or modal opens
  useEffect(() => {
    if (vendor) {
      setFormData({
        company_name: vendor.company_name,
        contact_person: vendor.contact_person || "",
        trade_category: vendor.trade_category,
        phone: vendor.phone,
        email: vendor.email || "",
        notes: vendor.notes || "",
        is_active: vendor.is_active,
        is_favorite: vendor.is_favorite,
        personal_rating: vendor.personal_rating,
      });
    } else {
      setFormData({
        company_name: "",
        contact_person: "",
        trade_category: "",
        phone: "",
        email: "",
        notes: "",
        is_active: true,
        is_favorite: false,
        personal_rating: null,
      });
    }
    setErrors({});
  }, [vendor, isOpen]);

  const validate = (): boolean => {
    const newErrors: Record<string, string> = {};

    // For new vendors, require core fields
    if (!vendor) {
      if (!formData.company_name.trim()) {
        newErrors.company_name = "Company name is required";
      }
      if (!formData.trade_category) {
        newErrors.trade_category = "Trade category is required";
      }
    }

    // Phone validation (optional but must be valid if provided)
    if (formData.phone && !validatePhone(formData.phone)) {
      newErrors.phone = "Invalid phone number. Must be 10 digits: (xxx) xxx-xxxx";
    }

    // Email validation (optional but must be valid if provided)
    if (formData.email && !validateEmail(formData.email)) {
      newErrors.email = "Invalid email address";
    }

    // Rating validation
    if (formData.personal_rating !== null) {
      if (formData.personal_rating < 1 || formData.personal_rating > 5) {
        newErrors.personal_rating = "Rating must be between 1 and 5";
      }
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!validate()) {
      return;
    }

    setIsSubmitting(true);

    try {
      const submitData = vendor
        ? // For updates, only send user-specific fields
          ({
            notes: formData.notes || null,
            is_active: formData.is_active,
            personal_rating: formData.personal_rating,
          } as VendorContactUpdate)
        : // For creates, send all fields
          ({
            company_name: formData.company_name,
            contact_person: formData.contact_person || null,
            trade_category: formData.trade_category,
            phone: formData.phone,
            email: formData.email || null,
            notes: formData.notes || null,
            is_active: formData.is_active,
          } as VendorContactCreate);

      await onSubmit(submitData);
      onClose();
    } catch (error) {
      // Error already handled by parent component
      console.error("Form submission error:", error);
    } finally {
      setIsSubmitting(false);
    }
  };

  if (!isOpen) return null;

  const isEditing = !!vendor;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm">
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto border border-gray-200 dark:border-gray-700">
        {/* Header */}
        <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-600">
          <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-100">
            {isViewing ? "Vendor Details" : isEditing ? "Edit Vendor" : "Add New Vendor"}
          </h2>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="px-6 py-4 space-y-4">
          {/* Company Name */}
          <div>
            <label htmlFor="company_name" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Company Name {!isEditing && <span className="text-red-500">*</span>}
            </label>
            <input
              type="text"
              id="company_name"
              value={formData.company_name}
              onChange={(e) => setFormData({ ...formData, company_name: e.target.value })}
              disabled={isViewing || isEditing}
              className={`w-full px-3 py-2 border rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 placeholder-gray-500 dark:placeholder-gray-400 focus:outline-none focus:ring-1 focus:ring-blue-600 dark:focus:ring-blue-500 focus:border-blue-600 dark:focus:border-blue-500 transition-colors ${
                errors.company_name ? "border-red-500" : "border-gray-300 dark:border-gray-600"
              } ${isViewing || isEditing ? "bg-gray-100 dark:bg-gray-900/50 cursor-not-allowed" : ""}`}
              placeholder="ABC Plumbing Inc."
            />
            {errors.company_name && (
              <p className="mt-1 text-sm text-red-600 dark:text-red-400">{errors.company_name}</p>
            )}
            {isEditing && (
              <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
                Central vendor info cannot be edited by individual users
              </p>
            )}
          </div>

          {/* Contact Person */}
          <div>
            <label htmlFor="contact_person" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Contact Person
            </label>
            <input
              type="text"
              id="contact_person"
              value={formData.contact_person}
              onChange={(e) => setFormData({ ...formData, contact_person: e.target.value })}
              disabled={isViewing || isEditing}
              className={`w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 placeholder-gray-500 dark:placeholder-gray-400 focus:outline-none focus:ring-1 focus:ring-blue-600 dark:focus:ring-blue-500 focus:border-blue-600 dark:focus:border-blue-500 transition-colors ${
                isViewing || isEditing ? "bg-gray-100 dark:bg-gray-900/50 cursor-not-allowed" : ""
              }`}
              placeholder="John Smith"
            />
          </div>

          {/* Trade Category */}
          <div>
            <label htmlFor="trade_category" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Trade Category {!isEditing && <span className="text-red-500">*</span>}
            </label>
            <Select.Root
              value={formData.trade_category}
              onValueChange={(value) => setFormData({ ...formData, trade_category: value })}
              disabled={isViewing || isEditing}
            >
              <Select.Trigger
                className={`w-full px-3 py-2 pr-9 border rounded-lg focus:outline-none focus:ring-1 focus:ring-blue-600 dark:focus:ring-blue-500 focus:border-blue-600 dark:focus:border-blue-500 flex items-center transition-colors relative ${
                  errors.trade_category ? "border-red-500" : "border-gray-300 dark:border-gray-600"
                } ${
                  isViewing || isEditing
                    ? "bg-gray-100 dark:bg-gray-900/50 cursor-not-allowed text-gray-900 dark:text-gray-100"
                    : "bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 hover:border-gray-400 dark:hover:border-gray-500"
                }`}
                disabled={isViewing || isEditing}
              >
                <Select.Value placeholder="Select a trade...">
                  <span className="truncate block flex-1 text-left">
                    {formData.trade_category || "Select a trade..."}
                  </span>
                </Select.Value>
                <Select.Icon className="absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none">
                  <ChevronDown className="h-4 w-4 text-gray-500 dark:text-gray-400" />
                </Select.Icon>
              </Select.Trigger>
              <Select.Portal>
                <Select.Content className="overflow-hidden bg-white dark:bg-gray-800 rounded-lg shadow-lg border border-gray-200 dark:border-gray-700 z-50 max-h-80">
                  <Select.Viewport className="p-1">
                    {COMMON_TRADE_CATEGORIES.map((category) => (
                      <Select.Item
                        key={category}
                        value={category}
                        className="relative flex items-center px-8 py-2 text-sm text-gray-900 dark:text-gray-100 rounded cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-700 focus:bg-gray-100 dark:focus:bg-gray-700 outline-none"
                      >
                        <Select.ItemText>{category}</Select.ItemText>
                        <Select.ItemIndicator className="absolute left-2 inline-flex items-center">
                          <Check className="h-4 w-4" />
                        </Select.ItemIndicator>
                      </Select.Item>
                    ))}
                  </Select.Viewport>
                </Select.Content>
              </Select.Portal>
            </Select.Root>
            {errors.trade_category && (
              <p className="mt-1 text-sm text-red-600 dark:text-red-400">{errors.trade_category}</p>
            )}
          </div>

          {/* Phone */}
          <div>
            <label htmlFor="phone" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Phone Number
            </label>
            <div className="relative">
              <input
                type="tel"
                id="phone"
                value={formData.phone}
                onChange={(e) => {
                  const formatted = formatPhoneNumber(e.target.value);
                  setFormData({ ...formData, phone: formatted });
                  
                  // Live validation
                  if (formatted && !validatePhone(formatted)) {
                    setErrors({ ...errors, phone: "Invalid phone number. Must be 10 digits: (xxx) xxx-xxxx" });
                  } else {
                    const { phone, ...restErrors } = errors;
                    setErrors(restErrors);
                  }
                }}
                disabled={isViewing || isEditing}
                className={`w-full px-3 py-2 border rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 placeholder-gray-500 dark:placeholder-gray-400 focus:outline-none focus:ring-1 transition-colors ${
                  errors.phone 
                    ? "border-red-500 focus:ring-red-500 focus:border-red-500" 
                    : formData.phone && validatePhone(formData.phone)
                    ? "border-green-500 dark:border-green-600 focus:ring-green-500 focus:border-green-500"
                    : "border-gray-300 dark:border-gray-600 focus:ring-blue-600 dark:focus:ring-blue-500 focus:border-blue-600 dark:focus:border-blue-500"
                } ${isViewing || isEditing ? "bg-gray-100 dark:bg-gray-900/50 cursor-not-allowed" : ""}`}
                placeholder="(555) 123-4567"
                maxLength={14}
              />
              {formData.phone && validatePhone(formData.phone) && !errors.phone && (
                <div className="absolute inset-y-0 right-0 pr-3 flex items-center pointer-events-none">
                  <svg className="h-5 w-5 text-green-500" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                  </svg>
                </div>
              )}
            </div>
            {errors.phone && (
              <p className="mt-1 text-sm text-red-600 dark:text-red-400">{errors.phone}</p>
            )}
            {!errors.phone && !isViewing && !isEditing && (
              <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">Format: (555) 123-4567</p>
            )}
          </div>

          {/* Email */}
          <div>
            <label htmlFor="email" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Email
            </label>
            <div className="relative">
              <input
                type="email"
                id="email"
                value={formData.email}
                onChange={(e) => {
                  const value = e.target.value;
                  setFormData({ ...formData, email: value });
                  
                  // Live validation
                  if (value && !validateEmail(value)) {
                    setErrors({ ...errors, email: "Invalid email address" });
                  } else {
                    const { email, ...restErrors } = errors;
                    setErrors(restErrors);
                  }
                }}
                disabled={isViewing || isEditing}
                className={`w-full px-3 py-2 border rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 placeholder-gray-500 dark:placeholder-gray-400 focus:outline-none focus:ring-1 transition-colors ${
                  errors.email 
                    ? "border-red-500 focus:ring-red-500 focus:border-red-500" 
                    : formData.email && validateEmail(formData.email)
                    ? "border-green-500 dark:border-green-600 focus:ring-green-500 focus:border-green-500"
                    : "border-gray-300 dark:border-gray-600 focus:ring-blue-600 dark:focus:ring-blue-500 focus:border-blue-600 dark:focus:border-blue-500"
                } ${isViewing || isEditing ? "bg-gray-100 dark:bg-gray-900/50 cursor-not-allowed" : ""}`}
                placeholder="vendor@example.com"
              />
              {formData.email && validateEmail(formData.email) && !errors.email && (
                <div className="absolute inset-y-0 right-0 pr-3 flex items-center pointer-events-none">
                  <svg className="h-5 w-5 text-green-500" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                  </svg>
                </div>
              )}
            </div>
            {errors.email && (
              <p className="mt-1 text-sm text-red-600 dark:text-red-400">{errors.email}</p>
            )}
            {!errors.email && !isViewing && !isEditing && (
              <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">Optional - for email notifications</p>
            )}
          </div>

          {/* Personal Notes */}
          <div>
            <label htmlFor="notes" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Personal Notes
            </label>
            <textarea
              id="notes"
              value={formData.notes}
              onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
              disabled={isViewing}
              rows={3}
              className={`w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 placeholder-gray-500 dark:placeholder-gray-400 focus:outline-none focus:ring-1 focus:ring-blue-600 dark:focus:ring-blue-500 focus:border-blue-600 dark:focus:border-blue-500 transition-colors ${
                isViewing ? "bg-gray-100 dark:bg-gray-900/50 cursor-not-allowed" : ""
              }`}
              placeholder="Add your personal notes about this vendor..."
            />
          </div>

          {/* Personal Rating */}
          {isEditing && (
            <div>
              <label htmlFor="personal_rating" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Your Rating
              </label>
              <div className="flex items-center space-x-2">
                {[1, 2, 3, 4, 5].map((rating) => (
                  <button
                    key={rating}
                    type="button"
                    onClick={() =>
                      setFormData({
                        ...formData,
                        personal_rating: formData.personal_rating === rating ? null : rating,
                      })
                    }
                    disabled={isViewing}
                    className={`text-2xl ${
                      formData.personal_rating && rating <= formData.personal_rating
                        ? "text-yellow-500"
                        : "text-gray-300 dark:text-gray-600"
                    } hover:text-yellow-400 transition-colors ${
                      isViewing ? "cursor-not-allowed" : "cursor-pointer"
                    }`}
                  >
                    ★
                  </button>
                ))}
                {formData.personal_rating !== null && !isViewing && (
                  <button
                    type="button"
                    onClick={() => setFormData({ ...formData, personal_rating: null })}
                    className="text-sm text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300 ml-2"
                  >
                    Clear
                  </button>
                )}
              </div>
            </div>
          )}

          {/* Buttons */}
          <div className="flex justify-end space-x-3 pt-4 border-t border-gray-200 dark:border-gray-600">
            <button
              type="button"
              onClick={onClose}
              disabled={isSubmitting}
              className="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {isViewing ? "Close" : "Cancel"}
            </button>
            {!isViewing && (
              <button
                type="submit"
                disabled={isSubmitting}
                className="inline-flex items-center px-4 py-2 border border-transparent rounded-lg shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 dark:bg-blue-700 dark:hover:bg-blue-800 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                {isSubmitting ? (
                  <>
                    <svg
                      className="animate-spin -ml-1 mr-2 h-4 w-4 text-white"
                      xmlns="http://www.w3.org/2000/svg"
                      fill="none"
                      viewBox="0 0 24 24"
                    >
                      <circle
                        className="opacity-25"
                        cx="12"
                        cy="12"
                        r="10"
                        stroke="currentColor"
                        strokeWidth="4"
                      />
                      <path
                        className="opacity-75"
                        fill="currentColor"
                        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                      />
                    </svg>
                    Saving...
                  </>
                ) : isEditing ? (
                  "Update Vendor"
                ) : (
                  "Create Vendor"
                )}
              </button>
            )}
          </div>
        </form>
      </div>
    </div>
  );
};

export default VendorModal;

