import React, { useState, useEffect, useRef, useMemo } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { toast } from "react-toastify";
import {
  fetchProperties,
  fetchTenantsByProperty,
  createPayment,
  fetchLeases,
  parsePaymentReceipt,
} from "../../../utils/api";
import {
  useReceiptUpload,
  createReceiptFileChangeHandler,
  ReceiptPreview,
} from "../../ui/SharedModalComponents";
import { extractPaymentReceiptData } from "../../../utils/receiptUtils";

const PAYMENT_METHODS = [
  "Credit Card",
  "Debit Card", 
  "Bank Transfer",
  "Wire Transfer",
  "Direct Deposit",
  "Interac e-Transfer",
  "Cash",
  "Check",
  "Bank Draft",
  "PayPal",
  "Internal Transfer",
  "Other",
];

const PAYMENT_STATUSES = [
  "Pending",
  "Paid",
  "Partial",
  "Overdue",
  "Cancelled",
  "Refunded",
];

const NewPaymentModal = ({ isOpen, onClose, onSuccess, initialData = {} }) => {
  // Handle both null and undefined initialData
  const safeInitialData = initialData || {};

  const memoizedInitialData = useMemo(() => ({
    property_id: safeInitialData.property_id || "",
    property_name: safeInitialData.property_name || "",
    tenant_id: safeInitialData.tenant_id || "",
    tenant_name: safeInitialData.tenant_name || "",
    invoice_id: safeInitialData.invoice_id || null,
    amount: safeInitialData.amount || "",
    payment_date: safeInitialData.payment_date || new Date().toISOString().split("T")[0],
    payment_method: safeInitialData.payment_method || "Other",
    status: safeInitialData.status || "Paid",
    notes: safeInitialData.notes || "",
    receipt_url: safeInitialData.receipt_url || null,
    transaction_reference: safeInitialData.transaction_reference || "",
    reduction: safeInitialData.reduction || "",
    reduction_reason: safeInitialData.reduction_reason || "",
    lease_id: safeInitialData.lease_id || null,
  }), [
    safeInitialData.property_id,
    safeInitialData.property_name,
    safeInitialData.tenant_id,
    safeInitialData.tenant_name,
    safeInitialData.invoice_id,
    safeInitialData.amount,
    safeInitialData.payment_date,
    safeInitialData.payment_method,
    safeInitialData.status,
    safeInitialData.notes,
    safeInitialData.receipt_url,
    safeInitialData.transaction_reference,
    safeInitialData.reduction,
    safeInitialData.reduction_reason,
    safeInitialData.lease_id
  ]);

  const getInitialFormData = () => memoizedInitialData;
  
  const [formData, setFormData] = useState(getInitialFormData());
  const [properties, setProperties] = useState([]);
  const [tenants, setTenants] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [lease, setLease] = useState(null);
  const [dropdownOpen, setDropdownOpen] = useState("");

  // Receipt upload state using shared hook
  const receiptState = useReceiptUpload(formData.receipt_url);

  const propertyDropdownRef = useRef(null);
  const tenantDropdownRef = useRef(null);

  useEffect(() => {
    const loadProperties = async () => {
      try {
        const data = await fetchProperties();
        setProperties(data);
      } catch (err) {
        console.error("Failed to load properties:", err);
        toast.error("Failed to load properties.");
      }
    };
    if (isOpen) {
      loadProperties();
      setFormData(getInitialFormData());
      setError(null);
      setLease(null);
      setTenants([]);
      receiptState.resetReceiptState();
      setDropdownOpen("");
    }
  }, [isOpen, memoizedInitialData]);

  useEffect(() => {
    const loadTenants = async () => {
      if (formData.property_id) {
        try {
          const data = await fetchTenantsByProperty(formData.property_id);
          setTenants(data);
          // Only reset tenant if it wasn't provided as initial data
          if (!safeInitialData.tenant_id) {
            setFormData((prev) => ({ ...prev, tenant_id: "", tenant_name: "" }));
            setLease(null);
          } else {
            // Validate preselected tenant exists in the loaded list
            const exists = Array.isArray(data) && data.some(t => String(t.id) === String(safeInitialData.tenant_id));
            if (!exists) {
              setFormData((prev) => ({ ...prev, tenant_id: "", tenant_name: "" }));
              setLease(null);
            }
          }
        } catch (err) {
          console.error("Failed to load tenants:", err);
          toast.error("Failed to load tenants for the selected property.");
          setTenants([]);
        }
      } else {
        setTenants([]);
      }
    };
    loadTenants();
  }, [formData.property_id, safeInitialData.tenant_id]);

  useEffect(() => {
    const findActiveLease = async () => {
      if (formData.property_id && formData.tenant_id) {
        try {
          const allLeases = await fetchLeases({
            property_id: formData.property_id,
            tenant_id: formData.tenant_id,
            status: "ACTIVE",
          });
          const activeLease = allLeases.find(
            (l) =>
              l.tenant_id === formData.tenant_id &&
              l.property_id === Number.parseInt(formData.property_id) &&
              l.status.toLowerCase() === "active"
          );

          if (activeLease) {
            setLease(activeLease);
            setError(null);
          } else {
            // No active lease found - this is OK, payments don't require leases
            setLease(null);
            setError(null);  // Don't show error - this is not a blocking issue
          }
        } catch (err) {
          console.error("Failed to find active lease:", err);
          toast.error("Error verifying lease information.");
          setLease(null);
        }
      } else {
        setLease(null);
      }
    };
    findActiveLease();
  }, [formData.property_id, formData.tenant_id]);

  useEffect(() => {
    const handleClickOutside = (event) => {
      if (
        dropdownOpen === "property" &&
        propertyDropdownRef.current &&
        !propertyDropdownRef.current.contains(event.target)
      ) {
        setDropdownOpen("");
      }
      if (
        dropdownOpen === "tenant" &&
        tenantDropdownRef.current &&
        !tenantDropdownRef.current.contains(event.target)
      ) {
        setDropdownOpen("");
      }
    };
    if (dropdownOpen) {
      document.addEventListener("mousedown", handleClickOutside);
    }
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, [dropdownOpen]);

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
  };

  // Create receipt file change handler using shared components
  const handleReceiptFileChange = createReceiptFileChangeHandler(
    parsePaymentReceipt,
    receiptState,
    (parsedDetails, receiptUrl) => {
      // Use utility functions for clean data extraction
      const extractedData = extractPaymentReceiptData(parsedDetails, formData);

      setFormData((prev) => ({
        ...prev,
        ...extractedData,
        receipt_url: receiptUrl,
      }));

      toast.success("Receipt parsed successfully!");
    }
  );

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);

    // Only validate the truly required fields
    if (!formData.amount || parseFloat(formData.amount) <= 0) {
      setError("Please enter a valid amount greater than 0.");
      return;
    }
    if (!formData.payment_method) {
      setError("Please select a payment method.");
      return;
    }
    if (!formData.status) {
      setError("Please select a payment status.");
      return;
    }
    if (formData.reduction > 0 && !formData.reduction_reason) {
      setError("Please provide a reason for the reduction.");
      return;
    }

    setIsLoading(true);
    try {
      const paymentPayload = {
        lease_id: lease?.id || null,  // Optional - can be null
        tenant_id: formData.tenant_id ? Number.parseInt(formData.tenant_id) : null,  // Optional
        property_id: formData.property_id ? Number.parseInt(formData.property_id) : null,  // Optional - for context
        invoice_id: formData.invoice_id ? Number.parseInt(formData.invoice_id) : null,  // Optional - for payment allocation
        tenant_name: formData.tenant_name || null,
        amount: Number.parseFloat(formData.amount),
        payment_date: formData.payment_date
          ? new Date(formData.payment_date).toISOString()
          : null,
        payment_method: formData.payment_method,
        status: formData.status,
        description: formData.notes || "",
        receipt_url: receiptState.currentReceiptUrl || formData.receipt_url,
        transaction_reference: formData.transaction_reference || null,
        reduction_amount: formData.reduction ? Number.parseFloat(formData.reduction) : null,
        reduction_reason: formData.reduction_reason || null,
      };

      await createPayment(paymentPayload);
      onSuccess?.();
      onClose();
    } catch (err) {
      console.error("Failed to create payment:", err);

      // Extract user-friendly error message
      let errorMsg = "Failed to create payment. Please try again.";

      if (err.data?.detail) {
        const detail = err.data.detail;
        // Handle common backend errors with user-friendly messages
        if (typeof detail === 'string') {
          if (detail.includes("data integrity")) {
            errorMsg = "Unable to save payment. Please ensure all required fields are filled correctly.";
          } else if (detail.includes("Invalid payment_method")) {
            errorMsg = "Invalid payment method selected. Please choose a valid option.";
          } else if (detail.includes("lease")) {
            errorMsg = "There was an issue with the lease information. Please verify property and tenant details.";
          } else if (detail.includes("tenant")) {
            errorMsg = "Invalid tenant information. Please select a valid tenant.";
          } else {
            errorMsg = detail;
          }
        }
      } else if (err.message) {
        errorMsg = err.message;
      }

      setError(errorMsg);
      toast.error(errorMsg);
    } finally {
      setIsLoading(false);
    }
  };

  const handlePropertySelect = (property) => {
    setFormData((prev) => ({
      ...prev,
      property_id: property.id.toString(),
      property_name: property.name,
      tenant_id: "", // Reset tenant when property changes
      tenant_name: "",
    }));
    setDropdownOpen("");
  };

  const handlePropertySelectKeyDown = (event, property) => {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      handlePropertySelect(property);
    }
  };

  const handleTenantSelect = (tenant) => {
    setFormData((prev) => ({
      ...prev,
      tenant_id: tenant.id,
      tenant_name: tenant.full_name,
    }));
    setDropdownOpen("");
  };

  const handleTenantSelectKeyDown = (event, tenant) => {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      handleTenantSelect(tenant);
    }
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="fixed inset-0 bg-black bg-opacity-50 dark:bg-opacity-70 backdrop-blur-sm z-[9999] flex items-center justify-center p-4"
          onClick={onClose}
        >
          <motion.div 
            initial={{ scale: 0.9, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            exit={{ scale: 0.9, opacity: 0 }}
            transition={{ type: "spring", damping: 25, stiffness: 400 }}
            className="relative w-full max-w-2xl bg-white dark:bg-gray-800 rounded-xl shadow-xl max-h-[85vh] overflow-hidden flex flex-col z-[10000]"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Header */}
            <div className="relative px-6 py-4 bg-brand-green dark:bg-gray-700 text-white">
              <div className="flex justify-between items-center">
                <div>
                  <h2 className="text-xl font-semibold text-white dark:text-gray-100">Log New Payment</h2>
                  <p className="text-white/80 dark:text-gray-300/80 mt-0.5 text-sm">
                    Record any payment - rent, deposit, utility, or other income
                  </p>
                </div>
                <button
                  onClick={onClose}
                  className="text-white/70 dark:text-gray-300/70 hover:text-white dark:hover:text-gray-100 hover:bg-white/10 dark:hover:bg-gray-700/50 p-1.5 rounded-lg transition-all"
                >
                  <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
            </div>

            {/* Content */}
            <form onSubmit={handleSubmit} className="flex-1 overflow-y-auto bg-gray-50 dark:bg-gray-900">
              {error && (
                <motion.div 
                  initial={{ opacity: 0, y: -10 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="mx-6 mt-4 p-3 bg-red-50 dark:bg-red-900/20 border border-red-100 dark:border-red-700 text-red-700 dark:text-red-300 rounded-lg"
                >
                  <div className="flex">
                    <svg className="h-5 w-5 text-red-400 dark:text-red-500 mr-2 flex-shrink-0 mt-0.5" viewBox="0 0 20 20" fill="currentColor">
                      <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                    </svg>
                    <span className="text-sm dark:text-red-300">{error}</span>
                  </div>
                </motion.div>
              )}

              <div className="p-6 space-y-4">
                {/* Receipt Upload Section */}
                <div className="bg-white dark:bg-gray-800 rounded-lg p-5 shadow-sm border border-gray-100 dark:border-gray-700">
                  <div className="flex items-start mb-3">
                    <div className="w-9 h-9 bg-purple-50 dark:bg-purple-900/20 rounded-lg flex items-center justify-center mr-3 flex-shrink-0">
                      <svg className="w-4 h-4 text-purple-600 dark:text-purple-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                      </svg>
                    </div>
                    <div>
                      <h3 className="text-base font-medium text-gray-900 dark:text-gray-100">Upload Receipt (Optional)</h3>
                      <p className="text-sm text-gray-500 dark:text-gray-400 mt-0.5">Auto-extracts amount, date & payment method</p>
                    </div>
                  </div>
                  <div className="ml-12">
                    <input
                      type="file"
                      id="receipt_file"
                      name="receipt_file"
                      accept=".pdf,.png,.jpg,.jpeg"
                      onChange={handleReceiptFileChange}
                      disabled={isLoading || receiptState.isParsingReceipt}
                      className="block w-full text-sm text-gray-500 file:mr-3 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-sm file:font-medium file:bg-purple-50 file:text-purple-600 hover:file:bg-purple-100 disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer"
                    />

                    {/* Loading State */}
                    {receiptState.isParsingReceipt && (
                      <div className="mt-3 flex items-center p-3 bg-purple-50 rounded-lg">
                        <svg className="animate-spin h-4 w-4 text-purple-600 mr-3" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                        </svg>
                        <p className="text-sm text-purple-700 font-medium">
                          AI is parsing your receipt...
                        </p>
                      </div>
                    )}

                    {/* Error State */}
                    {receiptState.receiptParseError && (
                      <div className="mt-3 p-3 bg-red-50 border border-red-100 rounded-lg">
                        <p className="text-sm text-red-700">
                          <svg className="w-4 h-4 inline mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                            <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                          </svg>
                          {receiptState.receiptParseError}
                        </p>
                      </div>
                    )}

                    {/* Success State with Preview Toggle */}
                    {receiptState.currentReceiptUrl && !receiptState.isParsingReceipt && !receiptState.receiptParseError && (
                      <div className="mt-3 flex items-center justify-between p-3 bg-green-50 border border-green-100 rounded-lg">
                        <div className="flex items-center">
                          <svg className="w-4 h-4 text-green-600 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                            <path strokeLinecap="round" strokeLinejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                          </svg>
                          <span className="text-sm text-green-700 font-medium">
                            Receipt parsed successfully!
                          </span>
                        </div>
                        <button
                          type="button"
                          onClick={() => receiptState.setShowReceiptPreview(!receiptState.showReceiptPreview)}
                          className="text-sm text-green-700 hover:text-green-800 font-medium"
                        >
                          {receiptState.showReceiptPreview ? 'Hide' : 'Show'} Preview
                        </button>
                      </div>
                    )}

                    {/* Receipt Preview */}
                    <ReceiptPreview
                      show={receiptState.showReceiptPreview}
                      receiptUrl={receiptState.currentReceiptUrl}
                    />
                  </div>
                </div>

                {/* Property and Tenant Selection */}
                <div className="bg-white dark:bg-gray-800 rounded-lg p-5 shadow-sm border border-gray-100 dark:border-gray-700">
                  <div className="flex items-center mb-3">
                    <div className="w-9 h-9 bg-blue-50 dark:bg-blue-900/20 rounded-lg flex items-center justify-center mr-3">
                      <svg className="w-4 h-4 text-blue-600 dark:text-blue-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" />
                      </svg>
                    </div>
                    <h3 className="text-base font-medium text-gray-900 dark:text-gray-100">Property & Tenant</h3>
                  </div>

                  <div className="space-y-4">
                    <div ref={propertyDropdownRef} className="relative">
                      <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                        Property
                      </label>
                      <input
                        type="text"
                        placeholder="Search and select a property..."
                        value={formData.property_name}
                        onChange={(e) => {
                          setFormData((prev) => ({
                            ...prev,
                            property_id: "",
                            property_name: e.target.value,
                          }));
                          setDropdownOpen("property");
                        }}
                        onFocus={() => setDropdownOpen("property")}
                        autoComplete="off"
                        className="w-full px-4 py-2.5 border border-gray-200 dark:border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
                      />
                      {dropdownOpen === "property" && properties.length > 0 && (
                        <div className="absolute z-20 mt-1 w-full max-w-full bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg shadow-lg max-h-60 overflow-y-auto">
                          <ul className="py-1">
                            {properties
                              .filter((p) =>
                                p.name
                                  .toLowerCase()
                                  .includes(formData.property_name.toLowerCase())
                              )
                              .map((p) => (
                                <li
                                  key={p.id}
                                  tabIndex={0}
                                  className="px-4 py-2.5 text-sm text-gray-700 dark:text-gray-300 hover:bg-blue-500 hover:text-white cursor-pointer transition-colors duration-150"
                                  onClick={() => handlePropertySelect(p)}
                                  onKeyDown={(e) => handlePropertySelectKeyDown(e, p)}
                                >
                                  {p.name}
                                </li>
                              ))}
                          </ul>
                        </div>
                      )}
                    </div>

                    <div ref={tenantDropdownRef} className="relative">
                      <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                        Tenant
                      </label>
                      <input
                        type="text"
                        placeholder="Search tenants..."
                        value={formData.tenant_name}
                        onChange={(e) => {
                          setFormData((prev) => ({
                            ...prev,
                            tenant_id: "",
                            tenant_name: e.target.value,
                          }));
                          setDropdownOpen("tenant");
                        }}
                        onFocus={() => setDropdownOpen("tenant")}
                        disabled={!formData.property_id || tenants.length === 0}
                        autoComplete="off"
                        className={`w-full px-4 py-2.5 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all ${
                          !formData.property_id || tenants.length === 0
                            ? "bg-gray-100 dark:bg-gray-600 cursor-not-allowed border-gray-200 dark:border-gray-500"
                            : "bg-white dark:bg-gray-700 border-gray-200 dark:border-gray-600 text-gray-900 dark:text-gray-100"
                        }`}
                      />
                      {dropdownOpen === "tenant" && tenants.length > 0 && (
                        <div className="absolute z-20 mt-1 w-full max-w-full bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg shadow-lg max-h-60 overflow-y-auto">
                          <ul className="py-1">
                            {tenants
                              .filter((t) =>
                                (t.full_name || "")
                                  .toLowerCase()
                                  .includes(formData.tenant_name.toLowerCase())
                              )
                              .map((t) => (
                                <li
                                  key={t.id}
                                  tabIndex={0}
                                  className="px-4 py-2.5 text-sm text-gray-700 dark:text-gray-300 hover:bg-blue-500 hover:text-white cursor-pointer transition-colors duration-150"
                                  onClick={() => handleTenantSelect(t)}
                                  onKeyDown={(e) => handleTenantSelectKeyDown(e, t)}
                                >
                                  <div className="flex justify-between items-center">
                                    <span>{t.full_name}</span>
                                    {t.unit?.name && (
                                      <span className="text-xs opacity-75 ml-2">
                                        Unit: {t.unit.name}
                                      </span>
                                    )}
                                  </div>
                                </li>
                              ))}
                          </ul>
                        </div>
                      )}
                      {!formData.property_id && (
                        <p className="mt-1 text-xs text-gray-500">
                          Please select a property first to see tenants.
                        </p>
                      )}
                    </div>
                  </div>

                  {lease && (
                    <div className="mt-4 p-3 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-700 rounded-lg">
                      <div className="flex items-start">
                        <svg className="w-5 h-5 text-blue-600 dark:text-blue-400 mr-2 flex-shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                          <path strokeLinecap="round" strokeLinejoin="round" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                        </svg>
                        <div className="text-sm text-blue-700 dark:text-blue-300">
                          <span className="font-medium">Active lease detected</span>
                          <span className="block mt-0.5">Monthly rent: ${lease.monthly_rent?.toLocaleString()}</span>
                        </div>
                      </div>
                    </div>
                  )}
                </div>

                {/* Payment Details */}
                <div className="bg-white dark:bg-gray-800 rounded-lg p-5 shadow-sm border border-gray-100 dark:border-gray-700">
                  <div className="flex items-center mb-3">
                    <div className="w-9 h-9 bg-green-50 dark:bg-green-900/20 rounded-lg flex items-center justify-center mr-3">
                      <svg className="w-4 h-4 text-green-600 dark:text-green-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                      </svg>
                    </div>
                    <h3 className="text-base font-medium text-gray-900 dark:text-gray-100">Payment Details</h3>
                  </div>

                  {/* Rent Calculation Display */}
                  {lease && (
                    <div className="mb-4 p-4 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-700 rounded-lg">
                      <div className="space-y-2">
                        <div className="flex justify-between items-center text-sm">
                          <span className="text-gray-700 dark:text-gray-300">Monthly Rent:</span>
                          <span className="font-medium text-gray-900 dark:text-gray-100">
                            ${lease.monthly_rent?.toLocaleString() || '0.00'}
                          </span>
                        </div>
                        {formData.reduction > 0 && (
                          <>
                            <div className="flex justify-between items-center text-sm">
                              <span className="text-red-600 dark:text-red-400">Reduction:</span>
                              <span className="font-medium text-red-600 dark:text-red-400">
                                -${parseFloat(formData.reduction).toLocaleString()}
                              </span>
                            </div>
                            <div className="border-t border-blue-200 dark:border-blue-600 pt-2 flex justify-between items-center">
                              <span className="text-sm font-medium text-gray-700 dark:text-gray-300">Total to Collect:</span>
                              <span className="font-semibold text-gray-900 dark:text-gray-100">
                                ${(lease.monthly_rent - parseFloat(formData.reduction || 0)).toLocaleString()}
                              </span>
                            </div>
                          </>
                        )}
                      </div>
                    </div>
                  )}

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                        Amount <span className="text-red-500">*</span>
                      </label>
                      <div className="relative">
                        <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                          <span className="text-gray-500 dark:text-gray-400 sm:text-sm">$</span>
                        </div>
                        <input
                          type="number"
                          name="amount"
                          value={formData.amount}
                          onChange={(e) => {
                            handleInputChange(e);
                            
                            const newAmount = parseFloat(e.target.value) || 0;
                            const currentReduction = parseFloat(formData.reduction) || 0;
                            
                            // Show warning if reduction exceeds new amount
                            if (currentReduction > 0 && newAmount > 0 && currentReduction > newAmount) {
                              toast.warn("Amount is less than the reduction amount");
                            }
                          }}
                          min="0.01"
                          step="0.01"
                          required
                          placeholder="0.00"
                          className="w-full px-4 py-2.5 pl-7 border border-gray-200 dark:border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
                        />
                      </div>
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                        Reduction (Optional)
                      </label>
                      <div className="relative">
                        <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                          <span className="text-gray-500 dark:text-gray-400 sm:text-sm">$</span>
                        </div>
                        <input
                          type="number"
                          name="reduction"
                          value={formData.reduction}
                          onChange={(e) => {
                            const reductionValue = e.target.value;
                            const reduction = parseFloat(reductionValue) || 0;
                            const currentAmount = parseFloat(formData.amount) || 0;

                            // Only auto-calculate amount if lease exists
                            if (lease) {
                              const newAmount = Math.max(0, lease.monthly_rent - reduction);
                              setFormData(prev => ({
                                ...prev,
                                reduction: reductionValue,
                                amount: newAmount.toFixed(2)
                              }));
                            } else {
                              // No lease - just update reduction, keep amount as-is
                              setFormData(prev => ({
                                ...prev,
                                reduction: reductionValue
                              }));
                            }

                            // Show warning if reduction exceeds current amount (but don't block input)
                            if (currentAmount > 0 && reduction > currentAmount) {
                              toast.warn("Reduction exceeds the payment amount");
                            }
                          }}
                          min="0"
                          step="0.01"
                          placeholder="0.00"
                          className="w-full px-4 py-2.5 pl-7 border border-gray-200 dark:border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
                        />
                      </div>
                      <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
                        Enter any one-time discount or reduction
                      </p>
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                        Payment Date <span className="text-red-500">*</span>
                      </label>
                      <input
                        type="date"
                        name="payment_date"
                        value={formData.payment_date}
                        onChange={handleInputChange}
                        required
                        className="w-full px-4 py-2.5 border border-gray-200 dark:border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 dark:[color-scheme:dark]"
                      />
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                        Payment Method <span className="text-red-500">*</span>
                      </label>
                      <select
                        name="payment_method"
                        value={formData.payment_method}
                        onChange={handleInputChange}
                        required
                        className="w-full px-4 py-2.5 border border-gray-200 dark:border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
                      >
                        <option value="">Select a method</option>
                        {PAYMENT_METHODS.map((method) => (
                          <option key={method} value={method}>
                            {method}
                          </option>
                        ))}
                      </select>
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                        Status <span className="text-red-500">*</span>
                      </label>
                      <select
                        name="status"
                        value={formData.status}
                        onChange={handleInputChange}
                        required
                        className="w-full px-4 py-2.5 border border-gray-200 dark:border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
                      >
                        {PAYMENT_STATUSES.map((s) => (
                          <option key={s} value={s}>
                            {s}
                          </option>
                        ))}
                      </select>
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                        Transaction Reference
                      </label>
                      <input
                        type="text"
                        name="transaction_reference"
                        value={formData.transaction_reference}
                        onChange={handleInputChange}
                        placeholder="e.g., Bank transaction ID"
                        className="w-full px-4 py-2.5 border border-gray-200 dark:border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
                      />
                    </div>

                    {formData.reduction > 0 && (
                      <div className="md:col-span-2">
                        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                          Reduction Reason <span className="text-red-500">*</span>
                        </label>
                        <input
                          type="text"
                          name="reduction_reason"
                          value={formData.reduction_reason}
                          onChange={handleInputChange}
                          placeholder="e.g., Tenant referred a friend, Holiday goodwill"
                          required={formData.reduction > 0}
                          className="w-full px-4 py-2.5 border border-gray-200 dark:border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
                        />
                        <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
                          Please provide a reason for the reduction
                        </p>
                      </div>
                    )}

                    <div className="md:col-span-2">
                      <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                        Notes
                      </label>
                      <textarea
                        name="notes"
                        value={formData.notes}
                        onChange={handleInputChange}
                        rows="2"
                        placeholder="Optional payment notes..."
                        className="w-full px-4 py-2.5 border border-gray-200 dark:border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 resize-none"
                      />
                    </div>
                  </div>
                </div>
              </div>
            </form>

            {/* Footer */}
            <div className="px-6 py-5 bg-gray-50 dark:bg-gray-900 border-t border-gray-200 dark:border-gray-700">
              <div className="flex justify-end gap-3">
                <button
                  type="button"
                  onClick={onClose}
                  className="px-4 py-2.5 border border-gray-300 dark:border-gray-600 rounded-md text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-700 hover:bg-gray-50 dark:hover:bg-gray-600 focus:outline-none focus:ring-2 focus:ring-gray-500 focus:ring-offset-2 dark:focus:ring-offset-gray-800 transition-all text-sm font-medium"
                  disabled={isLoading}
                >
                  Cancel
                </button>
                <button
                  onClick={handleSubmit}
                  className="px-5 py-2.5 bg-brand-green text-white rounded-md hover:bg-brand-green-hover focus:outline-none focus:ring-2 focus:ring-brand-green focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed transition-all text-sm font-medium flex items-center gap-2 min-w-[140px] justify-center shadow-sm"
                  disabled={isLoading || receiptState.isParsingReceipt || !formData.amount || parseFloat(formData.amount) <= 0}
                >
                  {isLoading ? (
                    <>
                      <svg className="animate-spin h-4 w-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                      </svg>
                      Creating...
                    </>
                  ) : receiptState.isParsingReceipt ? (
                    <>
                      <svg className="animate-spin h-4 w-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                      </svg>
                      Parsing...
                    </>
                  ) : (
                    'Create Payment'
                  )}
                </button>
              </div>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
};

export default NewPaymentModal;
