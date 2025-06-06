import React, { useEffect, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";

// UI Components from TenantModal

export const Label = ({ htmlFor, required, children }) => (
  <label
    htmlFor={htmlFor}
    className={`block text-sm font-medium text-gray-700 mb-1.5 ${
      required ? 'after:content-["*"] after:ml-0.5 after:text-red-500' : ""
    }`}
  >
    {children}
  </label>
);

export const Input = ({
  id,
  name,
  value,
  onChange,
  onBlur,
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
    onBlur={onBlur}
    placeholder={placeholder}
    required={required}
    className={`w-full px-4 py-2.5 text-gray-900 bg-white border border-gray-300 rounded-lg shadow-sm focus:ring-2 focus:ring-blue-500/30 focus:border-blue-500 focus:outline-none transition-all duration-200 ${className}`}
    {...props}
  />
);

export const Select = ({
  id,
  name,
  value,
  onChange,
  onBlur,
  required,
  children,
  className = "",
  ...props
}) => (
  <div className="relative">
    <select
      id={id || name}
      name={name}
      value={value}
      onChange={onChange}
      onBlur={onBlur}
      required={required}
      className={`w-full px-4 py-2.5 text-gray-900 bg-white border border-gray-300 rounded-lg shadow-sm appearance-none focus:ring-2 focus:ring-blue-500/30 focus:border-blue-500 focus:outline-none transition-all duration-200 ${className}`}
      {...props}
    >
      {children}
    </select>
    <div className="absolute inset-y-0 right-0 flex items-center px-2 pointer-events-none">
      <svg
        className="w-5 h-5 text-gray-500"
        fill="currentColor"
        viewBox="0 0 20 20"
        aria-hidden="true"
      >
        <title>Dropdown arrow</title>
        <path
          fillRule="evenodd"
          d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z"
          clipRule="evenodd"
        />
      </svg>
    </div>
  </div>
);

export const TextArea = ({
  id,
  name,
  value,
  onChange,
  onBlur,
  placeholder,
  required,
  rows = 3,
  className = "",
  ...props
}) => (
  <textarea
    id={id || name}
    name={name}
    value={value}
    onChange={onChange}
    onBlur={onBlur}
    rows={rows}
    placeholder={placeholder}
    required={required}
    className={`w-full px-4 py-2.5 text-gray-900 bg-white border border-gray-300 rounded-lg shadow-sm focus:ring-2 focus:ring-blue-500/30 focus:border-blue-500 focus:outline-none transition-all duration-200 ${className}`}
    {...props}
  />
);

export const Checkbox = ({
  id,
  name,
  checked,
  onChange,
  children,
  className = "",
}) => (
  <div className={`flex items-center ${className}`}>
    <input
      id={id || name}
      name={name}
      type="checkbox"
      checked={checked}
      onChange={onChange}
      className="h-4 w-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500 focus:ring-offset-1 transition duration-150 ease-in-out disabled:opacity-70 disabled:cursor-not-allowed"
    />
    {children && (
      <label
        htmlFor={id || name}
        className="ml-2.5 block text-sm text-gray-800 cursor-pointer"
      >
        {children}
      </label>
    )}
  </div>
);

export const ErrorMessage = ({ message }) => (
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

export const Button = ({
  type = "button",
  onClick,
  variant = "primary",
  disabled,
  children,
  className = "",
  isLoading = false,
  loadingText = "Saving...",
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
      disabled={disabled || isLoading}
      className={`${baseClasses} ${variants[variant]} ${className}`}
      {...props}
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
            />
            <path
              className="opacity-75"
              fill="currentColor"
              d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
            />
          </svg>
          {loadingText}
        </>
      ) : (
        children
      )}
    </button>
  );
};

// FormSection Component (from EditLeaseModal)
export const FormSection = ({
  title,
  children,
  containerClass = "pt-6", // Default container style
  titleClass = "text-lg font-semibold text-gray-800 mb-4 pb-2 border-b border-gray-200", // Default title style
}) => (
  <div className={containerClass}>
    {title && <h3 className={titleClass}>{title}</h3>}
    {/* Render children directly for flexibility */}
    {children}
  </div>
);

// Modal Shell Component
export const ModalShell = ({
  isOpen,
  onClose,
  title,
  children, // For the main form/content
  footerContent, // For buttons or other footer elements
  maxWidth = "max-w-md", // Default max-width, can be overridden (e.g., max-w-xl, max-w-3xl)
  error, // Optional general error message for the top of the modal
}) => {
  const modalRef = useRef(null);

  // Handle Escape key to close modal
  useEffect(() => {
    const handleEscapeKey = (e) => {
      if (e.key === "Escape") {
        onClose();
      }
    };
    if (isOpen) {
      document.addEventListener("keydown", handleEscapeKey);
    }
    return () => {
      document.removeEventListener("keydown", handleEscapeKey);
    };
  }, [isOpen, onClose]);

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
  }, [isOpen, onClose, modalRef]);

  if (!isOpen) return null;

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 bg-black bg-opacity-30 backdrop-blur-sm overflow-y-auto h-full w-full z-50 flex items-center justify-center p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="modal-title"
    >
      <motion.div
        initial={{ scale: 0.95, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        exit={{ scale: 0.95, opacity: 0 }}
        transition={{ type: "spring", stiffness: 300, damping: 30 }}
        ref={modalRef}
        className={`relative w-full ${maxWidth} bg-white rounded-xl shadow-2xl flex flex-col overflow-hidden max-h-[calc(100vh-4rem)]`}
      >
        {/* Header */}
        <div className="sticky top-0 z-10 px-6 py-4 bg-white border-b border-gray-200 flex justify-between items-center flex-shrink-0">
          <h2 id="modal-title" className="text-xl font-semibold text-gray-900">
            {title}
          </h2>
          <button
            type="button"
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
        <div className="p-6 flex-grow overflow-y-auto">
          <AnimatePresence>
            {
              error && (
                <ErrorMessage message={error} />
              ) /* Display general error */
            }
          </AnimatePresence>
          {children}
        </div>

        {/* Footer */}
        {footerContent && (
          <div className="sticky bottom-0 z-10 px-6 py-4 bg-white border-t border-gray-200 flex justify-end space-x-3 flex-shrink-0">
            {footerContent}
          </div>
        )}
      </motion.div>
    </motion.div>
  );
};
