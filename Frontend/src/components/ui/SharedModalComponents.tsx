import React, { useEffect, useRef, useState, ReactNode, RefObject } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { reportError } from '../../utils/error-reporting';

// Type definitions
export interface LabelProps {
  htmlFor?: string;
  required?: boolean;
  children: ReactNode;
  className?: string;
}

export interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  id?: string;
  name?: string;
  value?: string;
  onChange?: React.ChangeEventHandler<HTMLInputElement>;
  onBlur?: React.FocusEventHandler<HTMLInputElement>;
  placeholder?: string;
  required?: boolean;
  type?: string;
  className?: string;
}

export interface SelectProps extends React.SelectHTMLAttributes<HTMLSelectElement> {
  id?: string;
  name?: string;
  value?: string;
  onChange?: React.ChangeEventHandler<HTMLSelectElement>;
  onBlur?: React.FocusEventHandler<HTMLSelectElement>;
  required?: boolean;
  children: ReactNode;
  className?: string;
  disabled?: boolean;
}

export interface TextAreaProps extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {
  id?: string;
  name?: string;
  value?: string;
  onChange?: React.ChangeEventHandler<HTMLTextAreaElement>;
  onBlur?: React.FocusEventHandler<HTMLTextAreaElement>;
  placeholder?: string;
  required?: boolean;
  rows?: number;
  className?: string;
}

export interface CheckboxProps {
  id?: string;
  name?: string;
  checked?: boolean;
  onChange?: React.ChangeEventHandler<HTMLInputElement>;
  children?: ReactNode;
  className?: string;
}

export interface ErrorMessageProps {
  message: string;
}

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  type?: "button" | "submit" | "reset";
  onClick?: React.MouseEventHandler<HTMLButtonElement>;
  variant?: "primary" | "secondary" | "danger";
  disabled?: boolean;
  children: ReactNode;
  className?: string;
  isLoading?: boolean;
  loadingText?: string;
}

export interface FormSectionProps {
  title?: string;
  children: ReactNode;
  containerClass?: string;
  titleClass?: string;
}

export interface ModalShellProps {
  isOpen: boolean;
  onClose: () => void;
  title: string;
  children: ReactNode;
  footerContent?: ReactNode;
  maxWidth?: string;
  error?: string;
}

export interface ReceiptUploadAndPreviewProps {
  isParsingReceipt: boolean;
  receiptParseError: string | null;
  currentReceiptUrl: string | null;
  showReceiptPreview: boolean;
  setShowReceiptPreview: (show: boolean) => void;
  onReceiptFileChange: React.ChangeEventHandler<HTMLInputElement>;
  disabled?: boolean;
  title?: string;
  subtitle?: string;
  acceptedFileTypes?: string;
  className?: string;
}

export interface ReceiptPreviewProps {
  show: boolean;
  receiptUrl: string | null;
  height?: string;
  className?: string;
}

export interface ReceiptUploadState {
  receiptFile: File | null;
  isParsingReceipt: boolean;
  receiptParseError: string | null;
  currentReceiptUrl: string | null;
  showReceiptPreview: boolean;
  receiptParseAbortControllerRef: RefObject<AbortController | null>;
  setReceiptFile: (file: File | null) => void;
  setIsParsingReceipt: (parsing: boolean) => void;
  setReceiptParseError: (error: string | null) => void;
  setCurrentReceiptUrl: (url: string | null) => void;
  setShowReceiptPreview: (show: boolean) => void;
  resetReceiptState: () => void;
}

export type ParseReceiptFunction = (formData: FormData, options?: { signal?: AbortSignal }) => Promise<{
  success: boolean;
  parsed_details?: {
    subtotal_amount?: number;
    total_amount?: number;
    total_tax_amount?: number;
    expense_date?: string;
    payment_date?: string;
    description_notes?: string;
    vendor_name?: string;
    expense_category?: string;
    payment_method?: string;
    tax_details?: Array<{
      tax_name: string;
      tax_rate: number;
    }>;
  };
  receipt_url?: string;
  error?: string;
}>;

export type OnDataExtractedCallback = (
  parsedDetails: {
    subtotal_amount?: number;
    total_amount?: number;
    total_tax_amount?: number;
    expense_date?: string;
    payment_date?: string;
    description_notes?: string;
    vendor_name?: string;
    expense_category?: string;
    payment_method?: string;
    tax_details?: Array<{
      tax_name: string;
      tax_rate: number;
    }>;
  }, 
  receiptUrl: string
) => void;

// UI Components from TenantModal

export const Label: React.FC<LabelProps> = ({ htmlFor, required, children, className = "" }) => (
  <label
    htmlFor={htmlFor}
    className={`block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5 transition-colors duration-300 ${
      required ? 'after:content-["*"] after:ml-0.5 after:text-red-500 dark:after:text-red-400' : ""
    } ${className}`}
  >
    {children}
  </label>
);

export const Input: React.FC<InputProps> = ({
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
    className={`w-full px-4 py-2.5 text-gray-900 dark:text-gray-100 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg shadow-sm focus:ring-2 focus:ring-blue-500/30 focus:border-blue-500 dark:focus:border-blue-400 focus:outline-none transition-all duration-200 ${className}`}
    {...props}
  />
);

export const Select: React.FC<SelectProps> = ({
  id,
  name,
  value,
  onChange,
  onBlur,
  required,
  children,
  className = "",
  disabled = false,
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
      disabled={disabled}
      className={`w-full px-4 py-2.5 pr-10 text-gray-900 dark:text-gray-100 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg shadow-sm appearance-none 
        hover:border-gray-400 dark:hover:border-gray-500 
        focus:ring-2 focus:ring-blue-500/30 focus:border-blue-500 dark:focus:border-blue-400 focus:outline-none 
        disabled:bg-gray-50 dark:disabled:bg-gray-700 disabled:text-gray-500 dark:disabled:text-gray-400 disabled:border-gray-200 dark:disabled:border-gray-600 disabled:cursor-not-allowed
        transition-all duration-200 ${className}`}
      {...props}
    >
      {children}
    </select>
    <div className="absolute inset-y-0 right-0 flex items-center px-2 pointer-events-none">
      <svg
        className={`w-5 h-5 ${disabled ? "text-gray-400 dark:text-gray-500" : "text-gray-500 dark:text-gray-400"} transition-colors duration-200`}
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

export const TextArea: React.FC<TextAreaProps> = ({
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
    className={`w-full px-4 py-2.5 text-gray-900 dark:text-gray-100 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg shadow-sm focus:ring-2 focus:ring-blue-500/30 focus:border-blue-500 dark:focus:border-blue-400 focus:outline-none transition-all duration-200 ${className}`}
    {...props}
  />
);

export const Checkbox: React.FC<CheckboxProps> = ({
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
      className="h-4 w-4 text-blue-600 dark:text-blue-500 border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 rounded focus:ring-blue-500 focus:ring-offset-1 transition duration-150 ease-in-out disabled:opacity-70 disabled:cursor-not-allowed"
    />
    {children && (
      <label
        htmlFor={id || name}
        className="ml-2.5 block text-sm text-gray-800 dark:text-gray-200 cursor-pointer transition-colors duration-200"
      >
        {children}
      </label>
    )}
  </div>
);

export const ErrorMessage: React.FC<ErrorMessageProps> = ({ message }) => (
  <motion.div
    initial={{ opacity: 0, y: -10 }}
    animate={{ opacity: 1, y: 0 }}
    exit={{ opacity: 0 }}
    className="mb-6 p-3 bg-red-50 dark:bg-red-900/50 border border-red-200 dark:border-red-800 text-red-600 dark:text-red-400 rounded-lg flex items-start gap-2 transition-colors duration-200"
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

export const Button: React.FC<ButtonProps> = ({
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
      "bg-blue-600 dark:bg-blue-700 hover:bg-blue-700 dark:hover:bg-blue-600 text-white border border-transparent focus:ring-blue-500 dark:focus:ring-offset-gray-800",
    secondary:
      "bg-white dark:bg-gray-700 hover:bg-gray-50 dark:hover:bg-gray-600 text-gray-700 dark:text-gray-200 border border-gray-300 dark:border-gray-600 focus:ring-blue-500 dark:focus:ring-offset-gray-800",
    danger:
      "bg-red-600 dark:bg-red-700 hover:bg-red-700 dark:hover:bg-red-600 text-white border border-transparent focus:ring-red-500 dark:focus:ring-offset-gray-800",
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
            className={`animate-spin -ml-1 mr-2 h-4 w-4 ${
              variant === "secondary" ? "text-gray-600 dark:text-gray-300" : "text-white"
            }`}
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
export const FormSection: React.FC<FormSectionProps> = ({
  title,
  children,
  containerClass = "pt-6", // Default container style
  titleClass = "text-lg font-semibold text-gray-800 dark:text-gray-200 mb-4 pb-2 border-b border-gray-200 dark:border-gray-700", // Default title style
}) => (
  <div className={containerClass}>
    {title && <h3 className={titleClass}>{title}</h3>}
    {/* Render children directly for flexibility */}
    {children}
  </div>
);

// Modal Shell Component
export const ModalShell: React.FC<ModalShellProps> = ({
  isOpen,
  onClose,
  title,
  children, // For the main form/content
  footerContent, // For buttons or other footer elements
  maxWidth = "max-w-md", // Default max-width, can be overridden (e.g., max-w-xl, max-w-3xl)
  error, // Optional general error message for the top of the modal
}) => {
  const modalRef = useRef<HTMLDivElement>(null);

  // Handle Escape key to close modal
  useEffect(() => {
    const handleEscapeKey = (e: KeyboardEvent) => {
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
    function handleClickOutsideModal(event: MouseEvent) {
      if (modalRef.current && !modalRef.current.contains(event.target as Node)) {
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
      className="fixed inset-0 bg-black bg-opacity-30 backdrop-blur-sm overflow-y-auto h-full w-full z-[9999] flex items-center justify-center p-4"
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
        className={`relative w-full ${maxWidth} bg-white dark:bg-gray-800 rounded-xl shadow-2xl flex flex-col overflow-hidden max-h-[calc(100vh-4rem)] z-[10000]`}
      >
        {/* Header */}
        <div className="sticky top-0 z-10 px-6 py-4 bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 flex justify-between items-center flex-shrink-0">
          <h2 id="modal-title" className="text-xl font-semibold text-gray-900 dark:text-gray-100">
            {title}
          </h2>
          <button
            type="button"
            onClick={onClose}
            className="text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 dark:focus:ring-offset-gray-800 rounded-full p-1 transition-colors duration-200"
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
          <div className="sticky bottom-0 z-10 px-6 py-4 bg-white dark:bg-gray-800 border-t border-gray-200 dark:border-gray-700 flex justify-end space-x-3 flex-shrink-0">
            {footerContent}
          </div>
        )}
      </motion.div>
    </motion.div>
  );
};

// Receipt Upload and Preview Component
export const ReceiptUploadAndPreview: React.FC<ReceiptUploadAndPreviewProps> = ({
  // State props
  isParsingReceipt,
  receiptParseError,
  currentReceiptUrl,
  showReceiptPreview,
  setShowReceiptPreview,

  // Handler props
  onReceiptFileChange,

  // Configuration props
  disabled = false,
  title = "Upload and Parse Receipt (Optional)",
  subtitle = "Auto-extracts tax, amount, date & description",
  acceptedFileTypes = ".pdf,.png,.jpg,.jpeg",
  className = "",
}) => {
  return (
    <div
      className={`bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4 ${className}`}
    >
      <div className="flex items-center justify-between mb-3">
        <Label className="text-lg font-semibold text-blue-800 dark:text-blue-200">
          <i className="fas fa-receipt mr-2" />
          {title}
        </Label>
        <div className="text-sm text-blue-600 dark:text-blue-300">{subtitle}</div>
      </div>

      <Input
        type="file"
        id="receipt_file"
        name="receipt_file"
        accept={acceptedFileTypes}
        onChange={onReceiptFileChange}
        disabled={disabled || isParsingReceipt}
        className="block w-full text-sm file:mr-3 file:py-2 file:px-3 file:rounded-lg file:border-0 file:text-sm file:font-medium file:bg-blue-50 dark:file:bg-blue-900/30 file:text-blue-600 dark:file:text-blue-300 hover:file:bg-blue-100 dark:hover:file:bg-blue-900/50 disabled:opacity-50"
      />

      {/* Loading State */}
      {isParsingReceipt && (
        <div className="mt-3 flex items-center justify-center p-3 bg-blue-100 dark:bg-blue-900/30 rounded-lg">
          <div className="flex items-center space-x-3">
            <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-blue-600"></div>
            <p className="text-sm text-blue-700 dark:text-blue-300 font-medium">
              AI is parsing your receipt and extracting data...
            </p>
          </div>
        </div>
      )}

      {/* Error State */}
      {receiptParseError && (
        <div className="mt-3 p-3 bg-red-100 dark:bg-red-900/30 border border-red-200 dark:border-red-800 rounded-lg">
          <p className="text-sm text-red-700 dark:text-red-400">
            <i className="fas fa-exclamation-triangle mr-2" />
            Error: {receiptParseError}
          </p>
        </div>
      )}

      {/* Success State with Preview Toggle */}
      {currentReceiptUrl && !isParsingReceipt && !receiptParseError && (
        <div className="mt-3 flex items-center justify-between p-3 bg-green-100 dark:bg-green-900/30 border border-green-200 dark:border-green-800 rounded-lg">
          <div className="flex items-center space-x-2">
            <i className="fas fa-check-circle text-green-600" />
            <span className="text-sm text-green-700 dark:text-green-300 font-medium">
              Receipt parsed successfully! Review the extracted data below.
            </span>
          </div>
          <Button
            type="button"
            variant="secondary"
            onClick={() => setShowReceiptPreview(!showReceiptPreview)}
            className="text-sm py-1.5"
          >
            {showReceiptPreview ? (
              <>
                <i className="fas fa-eye-slash mr-2" />
                Hide Preview
              </>
            ) : (
              <>
                <i className="fas fa-eye mr-2" />
                Preview Receipt
              </>
            )}
          </Button>
        </div>
      )}

      {/* Receipt Preview */}
      <ReceiptPreview
        show={showReceiptPreview}
        receiptUrl={currentReceiptUrl}
      />
    </div>
  );
};

// Receipt Preview Component (can be used standalone or within ReceiptUploadAndPreview)
export const ReceiptPreview: React.FC<ReceiptPreviewProps> = ({
  show,
  receiptUrl,
  height = "24rem",
  className = "",
}) => {
  const [secureUrl, setSecureUrl] = useState<string | null>(null);
  const [isLoadingSecureUrl, setIsLoadingSecureUrl] = useState(false);

  // Fetch secure URL when receiptUrl changes (for private Azure containers)
  useEffect(() => {
    const fetchSecureUrl = async () => {
      if (!receiptUrl) {
        setSecureUrl(null);
        return;
      }

      // Check if it's an Azure blob URL that needs a SAS token
      if (receiptUrl.startsWith('https://') && receiptUrl.includes('blob.core.windows.net')) {
        // Only fetch secure URL if it doesn't already have a SAS token
        if (!receiptUrl.includes('?sv=')) {
          setIsLoadingSecureUrl(true);
          try {
            const { getSecureExpenseReceiptUrl, getSecurePaymentReceiptUrl } = await import('../../utils/api/accounting');
            
            // Try expense receipt first, then payment receipt as fallback
            let secureUrlData;
            try {
              secureUrlData = await getSecureExpenseReceiptUrl(receiptUrl);
            } catch (error: unknown) {
              // If expense fails with a 404, try payment as a fallback.
              // For other errors, we should fail fast.
              const status = (error as { response?: { status?: number } })?.response?.status;
              if (status === 404) {
                secureUrlData = await getSecurePaymentReceiptUrl(receiptUrl);
              } else {
                // Re-throw the original error if it's not a 404
                throw error;
              }
            }
            
            setSecureUrl(secureUrlData.secure_url);
          } catch (error: unknown) {
            console.error('Failed to fetch secure URL for receipt:', error);
            // Fallback to original URL (will likely fail but shows error)
            setSecureUrl(receiptUrl);
          } finally {
            setIsLoadingSecureUrl(false);
          }
        } else {
          // Already has SAS token
          setSecureUrl(receiptUrl);
        }
      } else {
        // Not an Azure URL or is a preview URL (blob:)
        setSecureUrl(receiptUrl);
      }
    };

    if (show && receiptUrl) {
      fetchSecureUrl();
    }
  }, [receiptUrl, show]);

  if (!receiptUrl) return null;

  const renderPreviewContent = () => {
    if (isLoadingSecureUrl || !secureUrl) {
      return (
        <div className="w-full h-full flex items-center justify-center bg-gray-100 dark:bg-gray-800">
          <div className="flex flex-col items-center gap-2">
            <div className="w-8 h-8 border-4 border-blue-200 dark:border-blue-800 border-t-blue-600 dark:border-t-blue-400 rounded-full animate-spin" />
            <p className="text-sm text-gray-500 dark:text-gray-400">Loading receipt...</p>
          </div>
        </div>
      );
    }

    const url = secureUrl;
    const lowerUrl = url.toLowerCase();

    if (
      lowerUrl.endsWith(".png") ||
      lowerUrl.endsWith(".jpg") ||
      lowerUrl.endsWith(".jpeg") ||
      lowerUrl.endsWith(".gif")
    ) {
      return (
        <img
          src={url}
          alt="Receipt Preview"
          className="w-full h-full object-contain p-1"
        />
      );
    } else if (lowerUrl.endsWith(".pdf")) {
      const pdfDisplayUrl = `${url}#view=FitH`;
      return (
        <iframe
          src={pdfDisplayUrl}
          title="Receipt Preview"
          className="w-full h-full border-0"
          sandbox="allow-same-origin allow-scripts"
        />
      );
    } else {
      return (
        <iframe
          src={url}
          title="Receipt Preview"
          className="w-full h-full border-0"
          sandbox="allow-same-origin allow-scripts"
        />
      );
    }
  };

  return (
    <AnimatePresence>
      {show && (
        <motion.div
          initial={{ opacity: 0, height: 0 }}
          animate={{ opacity: 1, height }}
          exit={{ opacity: 0, height: 0 }}
          transition={{ duration: 0.3, ease: "easeInOut" }}
          className={`mt-3 border rounded-lg overflow-hidden shadow bg-gray-50 ${className}`}
        >
          {renderPreviewContent()}
        </motion.div>
      )}
    </AnimatePresence>
  );
};

// Custom Hook for Receipt Upload State Management
export const useReceiptUpload = (initialReceiptUrl: string | null = null): ReceiptUploadState => {
  const [receiptFile, setReceiptFile] = useState<File | null>(null);
  const [isParsingReceipt, setIsParsingReceipt] = useState<boolean>(false);
  const [receiptParseError, setReceiptParseError] = useState<string | null>(null);
  const [currentReceiptUrl, setCurrentReceiptUrl] = useState<string | null>(initialReceiptUrl);
  const [showReceiptPreview, setShowReceiptPreview] = useState<boolean>(false);
  const receiptParseAbortControllerRef = useRef<AbortController | null>(null);

  // Reset all receipt-related state
  const resetReceiptState = () => {
    setReceiptFile(null);
    setIsParsingReceipt(false);
    setReceiptParseError(null);
    setCurrentReceiptUrl(initialReceiptUrl);
    setShowReceiptPreview(false);
    if (receiptParseAbortControllerRef.current) {
      receiptParseAbortControllerRef.current.abort();
      receiptParseAbortControllerRef.current = null;
    }
  };

  // Cleanup effect to abort receipt parsing on unmount
  useEffect(() => {
    return () => {
      if (receiptParseAbortControllerRef.current) {
        receiptParseAbortControllerRef.current.abort();
      }
    };
  }, []);

  return {
    // State
    receiptFile,
    isParsingReceipt,
    receiptParseError,
    currentReceiptUrl,
    showReceiptPreview,
    receiptParseAbortControllerRef,

    // Setters
    setReceiptFile,
    setIsParsingReceipt,
    setReceiptParseError,
    setCurrentReceiptUrl,
    setShowReceiptPreview,

    // Actions
    resetReceiptState,
  };
};

// Helper function to create a receipt file change handler
export const createReceiptFileChangeHandler = (
  parseReceiptAPI: ParseReceiptFunction,
  receiptState: ReceiptUploadState,
  onDataExtracted: OnDataExtractedCallback | null = null // Optional callback when data is successfully extracted
): React.ChangeEventHandler<HTMLInputElement> => {
  const {
    setReceiptFile,
    setIsParsingReceipt,
    setReceiptParseError,
    setCurrentReceiptUrl,
    setShowReceiptPreview,
    receiptParseAbortControllerRef,
  } = receiptState;

  return async (event: React.ChangeEvent<HTMLInputElement>) => {
    const inputEl = event.target;
    const file = inputEl.files?.[0];
    if (!file) return;

    // Validate file type and size
    const allowedTypes = ['image/jpeg', 'image/png', 'image/gif', 'application/pdf'];
    const maxSize = 10 * 1024 * 1024; // 10MB

    if (!allowedTypes.includes(file.type)) {
      setReceiptParseError('Please upload a valid image (JPG, PNG, GIF) or PDF file.');
      return;
    }
    
    if (file.size > maxSize) {
      setReceiptParseError('File size must be less than 10MB.');
      return;
    }

    // Clear input value so selecting the same file again triggers change
    inputEl.value = "";

    // Reset previous state
    setReceiptFile(file);
    setReceiptParseError(null);
    setIsParsingReceipt(true);
    setCurrentReceiptUrl(null);
    setShowReceiptPreview(false);

    // Abort previous request if it exists
    if (receiptParseAbortControllerRef.current) {
      receiptParseAbortControllerRef.current.abort();
    }

    const abortController = new AbortController();
    receiptParseAbortControllerRef.current = abortController;

    const formDataForApi = new FormData();
    formDataForApi.append("file", file);

    try {
      const response = await parseReceiptAPI(formDataForApi, {
        signal: abortController.signal,
      });

      if (abortController.signal.aborted) {
        return;
      }

      if (response && response.parsed_details) {
        const { parsed_details, receipt_url: parsedReceiptUrl } = response;

        setCurrentReceiptUrl(parsedReceiptUrl || null);
        setIsParsingReceipt(false);

        // Call the callback with extracted data if provided
        if (onDataExtracted && typeof onDataExtracted === "function") {
          // Only call the callback if we have a valid receipt URL
          // If no URL is available, the callback might not be able to handle operations that depend on it
          if (parsedReceiptUrl) {
            onDataExtracted(parsed_details, parsedReceiptUrl);
          } else {
            console.warn('Receipt parsed successfully but no receipt URL available. Skipping onDataExtracted callback.');
          }
        }
      } else {
        throw new Error("No parsed details received from API");
      }
    } catch (error: any) {
      if (abortController.signal.aborted) {
        return;
      }

      console.error("Receipt parsing error:", error);
      
      // Report receipt parsing errors with appropriate severity
      reportError(error, {
        component: 'SharedModalComponents',
        action: 'receipt_parsing',
        tags: {
          fileType: file?.type || 'unknown',
        },
        extra: {
          receipt: {
            fileName: file?.name,
            fileSize: file?.size,
            hasFile: !!file,
          }
        },
      }, 'error');
      
      setReceiptParseError(
        error.message || "Failed to parse receipt. Please try again."
      );
      setIsParsingReceipt(false);
      setCurrentReceiptUrl(null);
    } finally {
      receiptParseAbortControllerRef.current = null;
    }
  };
};
