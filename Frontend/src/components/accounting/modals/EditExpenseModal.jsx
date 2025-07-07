import React, { useState, useEffect, useMemo } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { toast } from "react-toastify";
import Decimal from "decimal.js";
import {
  updateExpense,
  fetchProperties,
  parseExpenseReceipt,
} from "../../../utils/api";
import {
  useReceiptUpload,
  createReceiptFileChangeHandler,
  ReceiptPreview,
} from "../../ui/SharedModalComponents";
import { extractExpenseReceiptDataForEdit } from "../../../utils/receiptUtils";
import { filterValidTaxes } from "../../../utils/taxValidation";
import { PAYMENT_METHODS, EXPENSE_CATEGORIES } from "../../../utils/constants";

const EditExpenseModal = ({ isOpen, onClose, onSuccess, expenseData }) => {
  const initialFormData = {
    category: "",
    amount: "",
    expense_date: "",
    description: "",
    receipt_url: null,
    property_id: "",
    property_name: "",
    payment_method: "Other",
    taxes: [{ tax_name: "", tax_rate: "" }],
  };
  const [formData, setFormData] = useState(initialFormData);
  const [properties, setProperties] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);

  // Receipt upload state using shared hook
  const receiptState = useReceiptUpload();

  useEffect(() => {
    if (isOpen && expenseData) {
      const loadPropertiesAndSetForm = async () => {
        let currentPropertyName = `Property ID ${expenseData.property_id}`;
        try {
          const props = await fetchProperties();
          setProperties(props);
          const currentProp = props.find(
            (p) => p.id === expenseData.property_id
          );
          if (currentProp) {
            currentPropertyName = currentProp.name;
          }
        } catch (err) {
          console.error("Failed to load properties for EditExpenseModal:", err);
        }

        setFormData({
          category: expenseData.category || "",
          amount: expenseData.subtotal_amount?.toString() || "0",
          expense_date: expenseData.expense_date
            ? new Date(expenseData.expense_date).toISOString().split("T")[0]
            : new Date().toISOString().split("T")[0],
          description: expenseData.description || "",
          receipt_url: expenseData.receipt_url || null,
          property_id: expenseData.property_id || "",
          property_name: currentPropertyName,
          payment_method: expenseData.payment_method || "Other",
          taxes:
            expenseData.taxes && expenseData.taxes.length > 0
              ? expenseData.taxes.map((tax) => ({
                  tax_name: tax.tax_name || "",
                  tax_rate: tax.tax_rate?.toString() || "",
                }))
              : [{ tax_name: "", tax_rate: "" }],
        });
        receiptState.resetReceiptState();
        if (expenseData.receipt_url) {
          receiptState.setCurrentReceiptUrl(expenseData.receipt_url);
        }
        setError(null);
      };
      loadPropertiesAndSetForm();
    } else if (!isOpen) {
      setFormData(initialFormData);
      receiptState.resetReceiptState();
      setError(null);
    }
  }, [isOpen, expenseData]);

  const { totalTax, totalAmount } = useMemo(() => {
    const subtotal = new Decimal(formData.amount || 0);
    let newTotalTax = new Decimal(0);
    
    if (subtotal.gt(0)) {
      formData.taxes.forEach((tax) => {
        const rate = new Decimal(tax.tax_rate || 0);
        if (tax.tax_name && rate.gte(0) && rate.lte(100)) {
          const taxAmount = subtotal.mul(rate).div(100);
          newTotalTax = newTotalTax.add(taxAmount);
        }
      });
    }
    
    const finalTotalTax = newTotalTax.toNumber();
    const finalTotalAmount = subtotal.add(newTotalTax).toNumber();
    
    return {
      totalTax: finalTotalTax,
      totalAmount: finalTotalAmount,
    };
  }, [formData.amount, formData.taxes]);

  const decimalFormatter = useMemo(
    () =>
      new Intl.NumberFormat("en-US", {
        style: "decimal",
        minimumFractionDigits: 2,
        maximumFractionDigits: 2,
      }),
    []
  );

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
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

  const handleReceiptFileChange = createReceiptFileChangeHandler(
    parseExpenseReceipt,
    receiptState,
    (parsedDetails, receiptUrl) => {
      const extractedData = extractExpenseReceiptDataForEdit(
        parsedDetails,
        formData
      );

      setFormData((prev) => ({
        ...prev,
        ...extractedData,
        receipt_url: receiptUrl,
      }));

      toast.success("New receipt parsed and ready to save.");
    }
  );

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    // Prevent submission during receipt parsing to avoid race conditions
    if (receiptState.isParsingReceipt) {
      toast.error("Please wait for receipt parsing to complete before submitting.");
      return;
    }
    
    if (!expenseData || !expenseData.id) {
      setError("Original expense data is missing. Cannot update.");
      return;
    }
    setError(null);
    setIsLoading(true);

    const payload = {
      category: formData.category || undefined,
      subtotal_amount: Number.parseFloat(formData.amount) || undefined,
      expense_date: formData.expense_date
        ? `${formData.expense_date}T00:00:00Z`
        : undefined,
      description: formData.description || undefined,
      receipt_url: receiptState.currentReceiptUrl || formData.receipt_url,
      payment_method: formData.payment_method || undefined,
      taxes: filterValidTaxes(formData.taxes)
          .map((tax) => ({
            tax_name: tax.tax_name.trim(),
            tax_rate: Number.parseFloat(tax.tax_rate),
          })),
    };

    const cleanedPayload = Object.entries(payload).reduce(
      (acc, [key, value]) => {
        if (value !== undefined) acc[key] = value;
        return acc;
      },
      {}
    );

    try {
      await updateExpense(expenseData.id, cleanedPayload);
      onSuccess?.();
      onClose();
    } catch (err) {
      const errorDetail =
        err.data?.detail || err.message || "Failed to update expense.";
      setError(
        typeof errorDetail === "string"
          ? errorDetail
          : JSON.stringify(errorDetail)
      );
      toast.error(
        typeof errorDetail === "string"
          ? errorDetail
          : "Error updating expense."
      );
    } finally {
      setIsLoading(false);
    }
  };

  const modalTitle =
    expenseData?.category && formData.property_name
      ? `Edit ${
          expenseData.category.charAt(0).toUpperCase() +
          expenseData.category.slice(1)
        } for ${formData.property_name}`
      : `Edit Expense`;

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
                  <h2 className="text-xl font-semibold text-white">{modalTitle}</h2>
                  <p className="text-white/80 mt-0.5 text-sm">
                    Update expense details and receipt
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
            <form 
              onSubmit={handleSubmit} 
              onKeyDown={(e) => {
                if (e.key === 'Enter' && receiptState.isParsingReceipt) {
                  e.preventDefault();
                  toast.error("Please wait for receipt parsing to complete before submitting.");
                }
              }}
              className="flex-1 overflow-y-auto bg-gray-50"
            >
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

                {/* Property Information */}
                {formData.property_name && (
                  <div className="bg-white rounded-lg p-5 shadow-sm border border-gray-100">
                    <div className="flex items-center mb-3">
                      <div className="w-9 h-9 bg-blue-50 rounded-lg flex items-center justify-center mr-3">
                        <svg className="w-4 h-4 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                          <path strokeLinecap="round" strokeLinejoin="round" d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" />
                        </svg>
                      </div>
                      <div>
                        <h3 className="text-base font-medium text-gray-900">Property Information</h3>
                        <p className="text-sm text-blue-700 font-medium">{formData.property_name}</p>
                      </div>
                    </div>
                  </div>
                )}

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
                        Category <span className="text-red-500">*</span>
                      </label>
                      <select
                        name="category"
                        value={formData.category}
                        onChange={handleInputChange}
                        required
                        className="w-full px-4 py-2.5 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all bg-white"
                      >
                        <option value="">Select Category</option>
                        {EXPENSE_CATEGORIES.map((cat) => (
                          <option key={cat} value={cat}>
                            {cat.charAt(0).toUpperCase() + cat.slice(1)}
                          </option>
                        ))}
                      </select>
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
                          required
                          min="0.01"
                          step="0.01"
                          placeholder="0.00"
                          className="w-full px-4 py-2.5 pl-7 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all bg-white"
                        />
                      </div>
                    </div>

                    <div className="md:col-span-2">
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        Description
                      </label>
                      <textarea
                        name="description"
                        value={formData.description}
                        onChange={handleInputChange}
                        rows="2"
                        placeholder="Optional description of the expense"
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
                            title="Remove Tax Item"
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
                          value={decimalFormatter.format(totalTax)}
                          readOnly
                          className="w-full px-4 py-2.5 pl-7 border border-gray-200 rounded-lg bg-gray-100 text-gray-700"
                          title={`Exact value: $${totalTax}`}
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
                          value={decimalFormatter.format(totalAmount)}
                          readOnly
                          className="w-full px-4 py-2.5 pl-7 border border-gray-200 rounded-lg bg-gray-100 text-gray-700"
                          title={`Exact value: $${totalAmount}`}
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
                      Updating...
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
                    'Update Expense'
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

export default EditExpenseModal; 