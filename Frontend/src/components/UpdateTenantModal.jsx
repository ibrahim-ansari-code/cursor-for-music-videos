import React, { useState, useEffect, useRef } from "react";
import { updateTenant } from "../utils/api";
import { motion, AnimatePresence } from "framer-motion";

// UI Components
const Label = ({ htmlFor, required, children }) => (
  <label
    htmlFor={htmlFor}
    className={`block text-sm font-medium text-gray-700 mb-1.5 ${
      required ? 'after:content-["*"] after:ml-0.5 after:text-red-500' : ""
    }`}
  >
    {children}
  </label>
);

const Input = ({
  id,
  name,
  value,
  onChange,
  placeholder,
  required,
  type = "text",
  className = "",
  ...props
}) => (
  <input
    id={id || name}
    name={name}
    type={type}
    value={value}
    onChange={onChange}
    placeholder={placeholder}
    required={required}
    className={`w-full px-4 py-2.5 text-gray-900 bg-white border border-gray-300 rounded-lg shadow-sm focus:ring-2 focus:ring-blue-500/30 focus:border-blue-500 focus:outline-none transition-all duration-200 ${className}`}
    {...props}
  />
);

const ErrorMessage = ({ message }) => (
  <motion.div
    initial={{ opacity: 0, y: -10 }}
    animate={{ opacity: 1, y: 0 }}
    exit={{ opacity: 0 }}
    className="mb-6 p-3 bg-red-50 border border-red-200 text-red-600 rounded-lg flex items-start gap-2"
  >
    <svg
      xmlns="http://www.w3.org/2000/svg"
      className="h-5 w-5 mt-0.5 flex-shrink-0"
      viewBox="0 0 20 20"
      fill="currentColor"
    >
      <path
        fillRule="evenodd"
        d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zm-1 9a1 1 0 100-2 1 1 0 000 2z"
        clipRule="evenodd"
      />
    </svg>
    <span>{message}</span>
  </motion.div>
);

const Button = ({
  type,
  onClick,
  variant = "primary",
  disabled,
  children,
  className = "",
  ...props
}) => {
  const baseClasses =
    "px-4 py-2.5 rounded-lg font-medium text-sm focus:outline-none focus:ring-2 focus:ring-offset-2 transition-all duration-200 inline-flex items-center justify-center gap-2 disabled:opacity-60 disabled:cursor-not-allowed";

  const variants = {
    primary:
      "bg-blue-600 hover:bg-blue-700 text-white border border-transparent focus:ring-blue-500",
    secondary:
      "bg-white hover:bg-gray-50 text-gray-700 border border-gray-300 focus:ring-blue-500",
    danger:
      "bg-red-600 hover:bg-red-700 text-white border border-transparent focus:ring-red-500",
  };

  return (
    <button
      type={type}
      onClick={onClick}
      disabled={disabled}
      className={`${baseClasses} ${variants[variant]} ${className}`}
      {...props}
    >
      {children}
    </button>
  );
};

const UpdateTenantModal = ({ isOpen, onClose, tenant, onSave }) => {
  const [formData, setFormData] = useState({
    first_name: "",
    last_name: "",
    phone: "",
    email: "",
    status: "active",
  });

  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [fieldErrors, setFieldErrors] = useState({});
  const [touched, setTouched] = useState({});
  const [submitAttempted, setSubmitAttempted] = useState(false);
  const modalRef = useRef(null);

  // Sync tenant prop to formData state
  useEffect(() => {
    if (tenant && isOpen) {
      setFormData({
        first_name: tenant.first_name || "",
        last_name: tenant.last_name || "",
        phone: tenant.phone || "",
        email: tenant.email || "",
        status: tenant.status || "active",
        current_property_id: tenant.current_property_id || null,
      });

      // Clear any previous errors
      setFieldErrors({});
      setError(null);
      setTouched({});
      setSubmitAttempted(false);
    }
  }, [tenant, isOpen]);

  // Handle form field changes
  const handleChange = (e) => {
    const { name, value } = e.target;

    setFormData((prev) => ({
      ...prev,
      [name]: value,
    }));

    // Mark field as touched
    setTouched((prev) => ({
      ...prev,
      [name]: true,
    }));

    // Clear field-specific error when user changes the field
    if (fieldErrors[name]) {
      setFieldErrors((prev) => {
        const updated = { ...prev };
        delete updated[name];
        return updated;
      });
    }
  };

  const validateForm = () => {
    const newErrors = {};
    let isValid = true;

    if (!formData.first_name || formData.first_name.trim() === "") {
      newErrors.first_name = "First name is required";
      isValid = false;
    }

    if (!formData.last_name || formData.last_name.trim() === "") {
      newErrors.last_name = "Last name is required";
      isValid = false;
    }

    if (!formData.email || formData.email.trim() === "") {
      newErrors.email = "Email is required";
      isValid = false;
    } else {
      // More robust email validation
      const emailRegex = /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/;
      if (!emailRegex.test(formData.email.trim())) {
        newErrors.email = "Please enter a valid email address";
        isValid = false;
      }
    }

    if (!formData.phone || formData.phone.trim() === "") {
      newErrors.phone = "Phone number is required";
      isValid = false;
    } else if (!/^[0-9]{10,15}$/.test(formData.phone.replace(/[^0-9]/g, ""))) {
      newErrors.phone =
        "Invalid phone number format (must contain 10-15 digits)";
      isValid = false;
    }

    setFieldErrors(newErrors);
    setTouched({
      first_name: true,
      last_name: true,
      email: true,
      phone: true,
    });
    setSubmitAttempted(true);

    return isValid;
  };

  // Click outside modal to close it
  useEffect(() => {
    function handleClickOutsideModal(event) {
      if (modalRef.current && !modalRef.current.contains(event.target)) {
        onClose();
      }
    }

    if (isOpen) {
      document.addEventListener("mousedown", handleClickOutsideModal);
    }

    return () => {
      document.removeEventListener("mousedown", handleClickOutsideModal);
    };
  }, [isOpen, onClose]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    setFieldErrors({});

    if (!validateForm()) {
      return;
    }

    setIsLoading(true);

    try {
      const response = await updateTenant(tenant.id, formData);

      if (onSave) {
        onSave(response);
      }

      onClose();
    } catch (err) {
      console.error("Failed to update tenant:", err);

      if (err.data?.detail && Array.isArray(err.data.detail)) {
        const validationErrors = {};
        err.data.detail.forEach((error) => {
          if (error.loc && error.loc.length > 1) {
            validationErrors[error.loc[1]] = error.msg;
          }
        });

        setFieldErrors(validationErrors);
        setError("Please correct the validation errors below.");
      } else {
        setError(err.message || "Failed to update tenant. Please try again.");
      }
    } finally {
      setIsLoading(false);
    }
  };

  if (!isOpen) return null;

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 bg-black bg-opacity-30 backdrop-blur-sm overflow-y-auto h-full w-full z-50 flex items-center justify-center p-4"
    >
      <motion.div
        initial={{ scale: 0.95, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        exit={{ scale: 0.95, opacity: 0 }}
        transition={{ type: "spring", stiffness: 300, damping: 30 }}
        ref={modalRef}
        className="relative w-full max-w-md bg-white rounded-xl shadow-2xl overflow-hidden"
      >
        {/* Header */}
        <div className="sticky top-0 z-10 px-6 py-4 bg-white border-b border-gray-200 flex justify-between items-center">
          <h2 className="text-xl font-semibold text-gray-900">Edit Tenant</h2>
          <button
            onClick={onClose}
            className="text-gray-500 hover:text-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 rounded-full p-1 transition-colors duration-200"
            aria-label="Close modal"
          >
            <svg
              className="h-6 w-6"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M6 18L18 6M6 6l12 12"
              />
            </svg>
          </button>
        </div>

        {/* Body */}
        <div className="p-6 max-h-[calc(100vh-12rem)] overflow-y-auto">
          <AnimatePresence>
            {error && <ErrorMessage message={error} />}
          </AnimatePresence>

          <form onSubmit={handleSubmit} className="space-y-5">
            <div className="space-y-4">
              <div>
                <Label htmlFor="first_name" required>
                  First Name
                </Label>
                <Input
                  id="first_name"
                  name="first_name"
                  value={formData.first_name}
                  onChange={handleChange}
                  placeholder="Enter first name"
                  required
                  className={
                    fieldErrors.first_name && touched.first_name
                      ? "border-red-500"
                      : ""
                  }
                />
                {fieldErrors.first_name && touched.first_name && (
                  <p className="mt-1 text-sm text-red-600">
                    {fieldErrors.first_name}
                  </p>
                )}
              </div>

              <div>
                <Label htmlFor="last_name" required>
                  Last Name
                </Label>
                <Input
                  id="last_name"
                  name="last_name"
                  value={formData.last_name}
                  onChange={handleChange}
                  placeholder="Enter last name"
                  required
                  className={
                    fieldErrors.last_name && touched.last_name
                      ? "border-red-500"
                      : ""
                  }
                />
                {fieldErrors.last_name && touched.last_name && (
                  <p className="mt-1 text-sm text-red-600">
                    {fieldErrors.last_name}
                  </p>
                )}
              </div>

              <div>
                <Label htmlFor="phone" required>
                  Phone Number
                </Label>
                <Input
                  id="phone"
                  name="phone"
                  type="tel"
                  value={formData.phone}
                  onChange={handleChange}
                  placeholder="Enter phone number"
                  required
                  className={
                    fieldErrors.phone && touched.phone ? "border-red-500" : ""
                  }
                />
                {fieldErrors.phone && touched.phone && (
                  <p className="mt-1 text-sm text-red-600">
                    {fieldErrors.phone}
                  </p>
                )}
              </div>

              <div>
                <Label htmlFor="email" required>
                  Email
                </Label>
                <Input
                  id="email"
                  name="email"
                  type="email"
                  value={formData.email}
                  onChange={handleChange}
                  placeholder="Enter email"
                  required
                  className={
                    fieldErrors.email && touched.email ? "border-red-500" : ""
                  }
                />
                {fieldErrors.email && touched.email && (
                  <p className="mt-1 text-sm text-red-600">
                    {fieldErrors.email}
                  </p>
                )}
              </div>
            </div>

            <div className="mt-2 mb-4 text-sm text-gray-500">
              <span className="text-red-600 font-bold">*</span> Required fields
            </div>
          </form>
        </div>

        {/* Footer */}
        <div className="sticky bottom-0 z-10 px-6 py-4 bg-white border-t border-gray-200 flex justify-end space-x-3">
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button
            type="submit"
            variant="primary"
            onClick={handleSubmit}
            disabled={isLoading}
          >
            {isLoading ? (
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
                  ></circle>
                  <path
                    className="opacity-75"
                    fill="currentColor"
                    d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                  ></path>
                </svg>
                Updating...
              </>
            ) : (
              "Save Changes"
            )}
          </Button>
        </div>
      </motion.div>
    </motion.div>
  );
};

export default UpdateTenantModal;
