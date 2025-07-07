import React, { useState, useEffect, useRef } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { toast } from "react-toastify";
import {
  fetchProperties,
  createExpense,
  parseExpenseReceipt,
} from "../../../utils/api";
import {
  useReceiptUpload,
  createReceiptFileChangeHandler,
  ReceiptPreview,
} from "../../ui/SharedModalComponents";
import { extractExpenseReceiptData } from "../../../utils/receiptUtils";
import { filterValidTaxes } from "../../../utils/taxValidation";

const EXPENSE_CATEGORIES = [
  "maintenance",
  "utilities",
  "taxes",
  "insurance",
  "administrative",
  "other",
];

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

const NewExpenseModal = ({ isOpen, onClose, onSuccess }) => {
  const initialFormData = {
    property_id: "",
    property_name: "",
    category: "",
    amount: "",
    expense_date: new Date().toISOString().split("T")[0],
    description: "",
    receipt_url: null,
    payment_method: "Other",
    taxes: [{ tax_name: "", tax_rate: "" }],
  };
  const [formData, setFormData] = useState(initialFormData);
  const [calculatedTotalTaxAmount, setCalculatedTotalTaxAmount] = useState(0);
  const [calculatedTotalAmount, setCalculatedTotalAmount] = useState(0);
  const [properties, setProperties] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [dropdownOpen, setDropdownOpen] = useState("");

  // Receipt upload state using shared hook
  const receiptState = useReceiptUpload();

  const propertyDropdownRef = useRef(null);

  useEffect(() => {
    const loadProperties = async () => {
      try {
        const data = await fetchProperties();
        setProperties(data);
      } catch (err) {
        console.error("Failed to load properties:", err);
        toast.error("Failed to load properties for dropdown.");
      }
    };
    if (isOpen) {
      loadProperties();
      setFormData(initialFormData);
      setCalculatedTotalTaxAmount(0);
      setCalculatedTotalAmount(0);
      setError(null);
      receiptState.resetReceiptState();
      setDropdownOpen("");
    }
  }, [isOpen]);

  useEffect(() => {
    const handleClickOutside = (event) => {
      if (
        dropdownOpen === "property" &&
        propertyDropdownRef.current &&
        !propertyDropdownRef.current.contains(event.target)
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

  useEffect(() => {
    const subtotal = Number.parseFloat(formData.amount) || 0;
    let newTotalTax = 0;
    
    if (subtotal > 0) {
      formData.taxes.forEach((tax) => {
        const rate = Number.parseFloat(tax.tax_rate);
        if (tax.tax_name && tax.tax_name.trim() && !isNaN(rate) && rate > 0 && rate <= 100) {
          newTotalTax += (subtotal * rate) / 100;
        }
      });
    }
    
    newTotalTax = Math.max(0, newTotalTax);
    const totalAmount = subtotal + newTotalTax;
    
    setCalculatedTotalTaxAmount(newTotalTax);
    setCalculatedTotalAmount(totalAmount);
  }, [formData.amount, formData.taxes]);

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({
      ...prev,
      [name]: value,
    }));
  };

  const handleTaxInputChange = (index, e) => {
    const { name, value } = e.target;
    const updatedTaxes = formData.taxes.map((tax, i) =>
      i === index ? { ...tax, [name]: value } : tax
    );
    setFormData((prev) => ({ ...prev, taxes: updatedTaxes }));
  };

  const addTaxItem = () => {
    setFormData((prev) => ({
      ...prev,
      taxes: [...prev.taxes, { tax_name: "", tax_rate: "" }],
    }));
  };

  const removeTaxItem = (index) => {
    setFormData((prev) => ({
      ...prev,
      taxes: prev.taxes.filter((_, i) => i !== index),
    }));
  };

  // Create receipt file change handler using shared components
  const handleReceiptFileChange = createReceiptFileChangeHandler(
    parseExpenseReceipt,
    receiptState,
    (parsedDetails, receiptUrl) => {
      setFormData((prev) => {
        const extractedData = extractExpenseReceiptData(parsedDetails, prev);
        // Remove duplicate toast - UI already shows success indicator

        return {
          ...prev,
          amount: extractedData.amount,
          taxes: extractedData.taxes,
          expense_date: extractedData.expense_date,
          description: extractedData.description,
          payment_method: extractedData.payment_method || prev.payment_method,
        };
      });
    }
  );

  const handlePropertySelect = (property) => {
    setFormData((prev) => ({
      ...prev,
      property_id: property.id.toString(),
      property_name: property.name,
    }));
    setDropdownOpen("");
  };

  const handlePropertySelectKeyDown = (event, property) => {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      handlePropertySelect(property);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);

    if (!formData.property_id) {
      setError("Please select a property.");
      return;
    }
    if (!formData.category) {
      setError("Please select a category.");
      return;
    }
    if (!formData.amount || Number.parseFloat(formData.amount) <= 0) {
      setError("Please enter a valid subtotal amount greater than 0.");
      return;
    }
    if (!formData.payment_method) {
      setError("Please select a payment method.");
      return;
    }

    setIsLoading(true);
    try {
      const expenseData = {
        property_id: Number.parseInt(formData.property_id, 10),
        category: formData.category,
        subtotal_amount: Number.parseFloat(formData.amount),
        expense_date: formData.expense_date,
        description: formData.description || "",
        receipt_url: receiptState.currentReceiptUrl,
        payment_method: formData.payment_method,
        taxes: filterValidTaxes(formData.taxes)
          .map((tax) => ({
            tax_name: tax.tax_name.trim(),
            tax_rate: Number.parseFloat(tax.tax_rate),
          }))
          .filter((tax) => {
            const rate = tax.tax_rate;
            return !isNaN(rate) && rate > 0 && rate <= 100;
          }),
      };

      await createExpense(expenseData);
      onSuccess?.();
      onClose();
    } catch (err) {
      console.error("Failed to create expense:", err);
      const errorMsg =
        err.data?.detail ||
        err.message ||
        "Failed to create expense. Please try again.";
      setError(errorMsg);
      toast.error(errorMsg);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="fixed inset-0 bg-black bg-opacity-50 backdrop-blur-sm z-[9999] flex items-center justify-center p-4"
          onClick={onClose}
        >
          <motion.div 
            initial={{ scale: 0.9, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            exit={{ scale: 0.9, opacity: 0 }}
            transition={{ type: "spring", damping: 25, stiffness: 400 }}
            className="relative w-full max-w-2xl bg-white rounded-xl shadow-xl max-h-[85vh] overflow-hidden flex flex-col z-[10000]"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Header */}
            <div className="relative px-6 py-4 bg-gradient-to-br from-brand-green to-brand-teal text-white">
              <div className="flex justify-between items-center">
                <div>
                  <h2 className="text-xl font-semibold text-white">Add New Expense</h2>
                  <p className="text-white/80 mt-0.5 text-sm">
                    Record a business expense with receipt parsing
                  </p>
                </div>
                <button
                  onClick={onClose}
                  className="text-white/70 hover:text-white hover:bg-white/10 p-1.5 rounded-lg transition-all"
                >
                  <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
            </div>

            {/* Content */}
            <form onSubmit={handleSubmit} className="flex-1 overflow-y-auto bg-gray-50">
              {error && (
                <motion.div 
                  initial={{ opacity: 0, y: -10 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="mx-6 mt-4 p-3 bg-red-50 border border-red-100 text-red-700 rounded-lg"
                >
                  <div className="flex">
                    <svg className="h-5 w-5 text-red-400 mr-2 flex-shrink-0 mt-0.5" viewBox="0 0 20 20" fill="currentColor">
                      <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                    </svg>
                    <span className="text-sm">{error}</span>
                  </div>
                </motion.div>
              )}

              <div className="p-6 space-y-4">
                {/* Receipt Upload Section */}
                <div className="bg-white rounded-lg p-5 shadow-sm border border-gray-100">
                  <div className="flex items-start mb-3">
                    <div className="w-9 h-9 bg-purple-50 rounded-lg flex items-center justify-center mr-3 flex-shrink-0">
                      <svg className="w-4 h-4 text-purple-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                      </svg>
                    </div>
                    <div>
                      <h3 className="text-base font-medium text-gray-900">Upload and Parse Receipt (Optional)</h3>
                      <p className="text-sm text-gray-500 mt-0.5">Auto-extracts tax, amount, date & description</p>
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

                {/* Property and Category Selection */}
                <div className="bg-white rounded-lg p-5 shadow-sm border border-gray-100">
                  <div className="flex items-center mb-3">
                    <div className="w-9 h-9 bg-blue-50 rounded-lg flex items-center justify-center mr-3">
                      <svg className="w-4 h-4 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" />
                      </svg>
                    </div>
                    <h3 className="text-base font-medium text-gray-900">Property & Category</h3>
                  </div>

                  <div className="space-y-4">
                    <div ref={propertyDropdownRef} className="relative">
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        Property <span className="text-red-500">*</span>
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
                        className="w-full px-4 py-2.5 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all bg-white"
                      />
                      {dropdownOpen === "property" && properties.length > 0 && (
                        <div className="absolute z-20 mt-1 w-full max-w-full bg-white border border-gray-300 rounded-lg shadow-lg max-h-60 overflow-y-auto">
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
                                  className="px-4 py-2.5 text-sm text-gray-700 hover:bg-blue-500 hover:text-white cursor-pointer transition-colors duration-150"
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

                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        Category <span className="text-red-500">*</span>
                      </label>
                      <select
                        name="category"
                        value={formData.category}
                        onChange={handleInputChange}
                        required
                        className="w-full px-4 py-2.5 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all bg-white"
                      >
                        <option value="">Select a category</option>
                        {EXPENSE_CATEGORIES.map((cat) => (
                          <option key={cat} value={cat}>
                            {cat.charAt(0).toUpperCase() + cat.slice(1)}
                          </option>
                        ))}
                      </select>
                    </div>
                  </div>
                </div>

                {/* Expense Details */}
                <div className="bg-white rounded-lg p-5 shadow-sm border border-gray-100">
                  <div className="flex items-center mb-3">
                    <div className="w-9 h-9 bg-green-50 rounded-lg flex items-center justify-center mr-3">
                      <svg className="w-4 h-4 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                      </svg>
                    </div>
                    <h3 className="text-base font-medium text-gray-900">Expense Details</h3>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        Subtotal (before tax) <span className="text-red-500">*</span>
                      </label>
                      <div className="relative">
                        <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                          <span className="text-gray-500 sm:text-sm">$</span>
                        </div>
                        <input
                          type="number"
                          name="amount"
                          value={formData.amount}
                          onChange={handleInputChange}
                          min="0.01"
                          step="0.01"
                          required
                          placeholder="0.00"
                          className="w-full px-4 py-2.5 pl-7 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all bg-white"
                        />
                      </div>
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        Payment Method <span className="text-red-500">*</span>
                      </label>
                      <select
                        name="payment_method"
                        value={formData.payment_method}
                        onChange={handleInputChange}
                        required
                        className="w-full px-4 py-2.5 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all bg-white"
                      >
                        {PAYMENT_METHODS.map((method) => (
                          <option key={method} value={method}>
                            {method}
                          </option>
                        ))}
                      </select>
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        Expense Date <span className="text-red-500">*</span>
                      </label>
                      <input
                        type="date"
                        name="expense_date"
                        value={formData.expense_date}
                        onChange={handleInputChange}
                        required
                        className="w-full px-4 py-2.5 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all bg-white"
                      />
                    </div>

                    <div className="md:col-span-3">
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        Description
                      </label>
                      <textarea
                        name="description"
                        value={formData.description}
                        onChange={handleInputChange}
                        rows="2"
                        placeholder="Optional description of the expense..."
                        className="w-full px-4 py-2.5 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all bg-white resize-none"
                      />
                    </div>
                  </div>

                  {/* Tax Section */}
                  <div className="mt-6 space-y-3">
                    <label className="block text-sm font-medium text-gray-700">Taxes</label>
                    {formData.taxes.map((tax, index) => (
                      <div
                        key={index}
                        className="flex items-center space-x-2 p-3 border border-gray-200 rounded-lg bg-gray-50/50"
                      >
                        <div className="flex-grow">
                          <input
                            type="text"
                            name="tax_name"
                            value={tax.tax_name}
                            onChange={(e) => handleTaxInputChange(index, e)}
                            placeholder="Tax Name (e.g., GST)"
                            className="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all bg-white"
                          />
                        </div>
                        <div className="w-1/3 relative">
                          <input
                            type="number"
                            name="tax_rate"
                            value={tax.tax_rate}
                            onChange={(e) => handleTaxInputChange(index, e)}
                            min="0"
                            max="100"
                            step="0.01"
                            placeholder="Rate"
                            className="w-full px-3 py-2 pr-6 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all bg-white"
                          />
                          <div className="absolute inset-y-0 right-0 pr-2.5 flex items-center pointer-events-none">
                            <span className="text-gray-500 text-sm">%</span>
                          </div>
                        </div>
                        {formData.taxes.length > 1 && (
                          <button
                            type="button"
                            onClick={() => removeTaxItem(index)}
                            className="p-2 text-xs h-9 w-9 flex items-center justify-center bg-red-50 text-red-500 hover:bg-red-100 hover:text-red-600 border border-red-200 rounded-lg transition-all"
                            title="Remove Tax"
                          >
                            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                              <path strokeLinecap="round" strokeLinejoin="round" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                            </svg>
                          </button>
                        )}
                      </div>
                    ))}
                    <button
                      type="button"
                      onClick={addTaxItem}
                      className="mt-1 px-4 py-2 text-sm border border-gray-300 rounded-lg hover:border-gray-400 bg-white hover:bg-gray-50 transition-all flex items-center"
                    >
                      <svg className="w-4 h-4 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
                      </svg>
                      Add Tax Item
                    </button>
                  </div>

                  {/* Tax Summary */}
                  <div className="mt-6 grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">Total Tax Amount</label>
                      <div className="relative">
                        <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                          <span className="text-gray-500 sm:text-sm">$</span>
                        </div>
                        <input
                          type="text"
                          value={calculatedTotalTaxAmount.toFixed(2)}
                          readOnly
                          className="w-full px-4 py-2.5 pl-7 border border-gray-200 rounded-lg bg-gray-100 text-gray-700"
                        />
                      </div>
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">Total Amount (incl. tax)</label>
                      <div className="relative">
                        <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                          <span className="text-gray-500 sm:text-sm">$</span>
                        </div>
                        <input
                          type="text"
                          value={calculatedTotalAmount.toFixed(2)}
                          readOnly
                          className="w-full px-4 py-2.5 pl-7 border border-gray-200 rounded-lg bg-gray-100 text-gray-700"
                        />
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </form>

            {/* Footer */}
            <div className="px-6 py-5 bg-gray-50 border-t border-gray-200">
              <div className="flex justify-end gap-3">
                <button
                  type="button"
                  onClick={onClose}
                  className="px-4 py-2.5 border border-gray-300 rounded-md text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-gray-500 focus:ring-offset-2 transition-all text-sm font-medium"
                  disabled={isLoading}
                >
                  Cancel
                </button>
                <button
                  onClick={handleSubmit}
                  className="px-5 py-2.5 bg-gradient-to-br from-brand-green to-brand-teal text-white rounded-md hover:from-brand-green/90 hover:to-brand-teal/90 focus:outline-none focus:ring-2 focus:ring-brand-green focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed transition-all text-sm font-medium flex items-center gap-2 min-w-[140px] justify-center shadow-sm"
                  disabled={isLoading || receiptState.isParsingReceipt}
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
                    'Create Expense'
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

export default NewExpenseModal; 