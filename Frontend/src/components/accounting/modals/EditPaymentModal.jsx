import React, { useState, useEffect } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { toast } from "react-toastify";
import {
  updatePayment, // To update the payment
  parsePaymentReceipt,
} from "../../../utils/api";
import {
  useReceiptUpload,
  createReceiptFileChangeHandler,
  ReceiptPreview,
} from "../../ui/SharedModalComponents";
import { extractPaymentReceiptDataForEdit } from "../../../utils/receiptUtils";

import { PAYMENT_METHODS, PAYMENT_STATUSES } from "../../../utils/constants";

const EditPaymentModal = ({ isOpen, onClose, onSuccess, paymentData }) => {
  const initialFormData = {
    amount: "",
    payment_date: new Date().toISOString().split("T")[0],
    payment_method: "",
    status: "Paid",
    notes: "", // Maps to description in backend
    receipt_url: null,
    transaction_reference: "",
    reduction: "",
    reduction_reason: "",
  };
  const [formData, setFormData] = useState(initialFormData);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);

  // Receipt upload state using shared hook
  const receiptState = useReceiptUpload();

  useEffect(() => {
    if (isOpen && paymentData) {
      setFormData({
        amount: paymentData.amount?.toString() || "",
        payment_date: paymentData.payment_date
          ? new Date(paymentData.payment_date).toISOString().split("T")[0]
          : new Date().toISOString().split("T")[0],
        payment_method: paymentData.payment_method || "",
        status: paymentData.status || "Paid",
        notes: paymentData.description || "",
        receipt_url: paymentData.receipt_url || null,
        transaction_reference: paymentData.transaction_reference || "",
        reduction: paymentData.reduction_amount?.toString() || "",
        reduction_reason: paymentData.reduction_reason || "",
      });
      setError(null);
      receiptState.resetReceiptState();
      // Set the current receipt URL if editing existing payment with receipt
      if (paymentData.receipt_url) {
        receiptState.setCurrentReceiptUrl(paymentData.receipt_url);
      }
    } else if (!isOpen) {
      // Reset form when modal is closed
      setFormData(initialFormData);
      setError(null);
      receiptState.resetReceiptState();
    }
  }, [isOpen, paymentData]); // Re-run if isOpen or paymentData changes

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
  };

  // Create receipt file change handler using shared components
  const handleReceiptFileChange = createReceiptFileChangeHandler(
    parsePaymentReceipt,
    receiptState,
    (parsedDetails, receiptUrl) => {
      // Use utility functions for conservative edit mode data extraction
      const extractedData = extractPaymentReceiptDataForEdit(
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
    if (!paymentData || !paymentData.id) {
      setError("Original payment data is missing. Cannot update.");
      return;
    }
    setError(null);
    setIsLoading(true);

    const parsedAmount = Number.parseFloat(formData.amount);

    const payload = {
      amount:
        formData.amount !== "" && !isNaN(parsedAmount)
          ? parsedAmount
          : undefined,
      payment_date: formData.payment_date
        ? `${formData.payment_date}T00:00:00Z`
        : undefined, // Ensure UTC
      payment_method: formData.payment_method || undefined,
      status: formData.status || undefined,
      description: formData.notes || undefined,
      receipt_url: receiptState.currentReceiptUrl || formData.receipt_url, // Use shared state with fallback
      transaction_reference: formData.transaction_reference || undefined,
      reduction_amount: formData.reduction ? parseFloat(formData.reduction) : undefined,
      reduction_reason: formData.reduction_reason || undefined,
    };

    const cleanedPayload = Object.entries(payload).reduce(
      (acc, [key, value]) => {
        // Exclude reduction fields if reduction amount is 0
        if (key === 'reduction_amount' && (!value || value === 0)) {
          return acc;
        }
        if (key === 'reduction_reason' && (!payload.reduction_amount || payload.reduction_amount === 0)) {
          return acc;
        }
        if (value !== undefined) acc[key] = value;
        return acc;
      },
      {}
    );

    try {
      await updatePayment(paymentData.id, cleanedPayload);
      onSuccess?.();
      onClose(); // Triggers form reset via useEffect
    } catch (err) {
      const errorDetail =
        err.data?.detail || err.message || "Failed to update payment.";
      setError(
        typeof errorDetail === "string"
          ? errorDetail
          : JSON.stringify(errorDetail)
      );
      toast.error(
        typeof errorDetail === "string"
          ? errorDetail
          : "Error updating payment."
      );
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
          className="fixed inset-0 bg-black bg-opacity-50 dark:bg-opacity-70 backdrop-blur-sm z-[9999] flex items-center justify-center p-4"
          onClick={onClose}
        >
          <motion.div 
            initial={{ scale: 0.9, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            exit={{ scale: 0.9, opacity: 0 }}
            transition={{ type: "spring", damping: 25, stiffness: 400 }}
            className="relative w-full max-w-2xl bg-white dark:bg-gray-800 rounded-xl shadow-xl max-h-[85vh] overflow-hidden flex flex-col z-[10000] transition-colors duration-300"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Header */}
            <div className="relative px-6 py-4 bg-gradient-to-br from-brand-green to-brand-teal dark:from-gray-700 dark:to-gray-600 text-white transition-colors duration-300">
              <div className="flex justify-between items-center">
                <div>
                  <h2 className="text-xl font-semibold text-white">Edit Payment</h2>
                  <p className="text-white/80 mt-0.5 text-sm">
                    Update payment details for {paymentData?.tenant_name || "Tenant"}
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
            <form onSubmit={handleSubmit} className="flex-1 overflow-y-auto bg-gray-50 dark:bg-gray-900 transition-colors duration-300">
              {error && (
                <motion.div 
                  initial={{ opacity: 0, y: -10 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="mx-6 mt-4 p-3 bg-red-50 dark:bg-red-900/20 border border-red-100 dark:border-red-700 text-red-700 dark:text-red-300 rounded-lg transition-colors duration-300"
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
                <div className="bg-white dark:bg-gray-800 rounded-lg p-5 shadow-sm border border-gray-100 dark:border-gray-700 transition-colors duration-300">
                  <div className="flex items-start mb-3">
                    <div className="w-9 h-9 bg-purple-50 dark:bg-purple-900/20 rounded-lg flex items-center justify-center mr-3 flex-shrink-0 transition-colors duration-300">
                      <svg className="w-4 h-4 text-purple-600 dark:text-purple-400 transition-colors duration-300" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                      </svg>
                    </div>
                    <div>
                      <h3 className="text-base font-medium text-gray-900 dark:text-gray-100 transition-colors duration-300">Upload New Receipt (Optional)</h3>
                      <p className="text-sm text-gray-500 dark:text-gray-400 mt-0.5 transition-colors duration-300">Auto-extracts amount, date & payment method</p>
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
                      className="block w-full text-sm text-gray-500 dark:text-gray-400 file:mr-3 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-sm file:font-medium file:bg-purple-50 dark:file:bg-purple-900/20 file:text-purple-600 dark:file:text-purple-400 hover:file:bg-purple-100 dark:hover:file:bg-purple-900/30 disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer transition-colors duration-300"
                    />

                    {/* Loading State */}
                    {receiptState.isParsingReceipt && (
                      <div className="mt-3 flex items-center p-3 bg-purple-50 dark:bg-purple-900/20 rounded-lg transition-colors duration-300">
                        <svg className="animate-spin h-4 w-4 text-purple-600 mr-3" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                        </svg>
                        <p className="text-sm text-purple-700 dark:text-purple-300 font-medium transition-colors duration-300">
                          AI is parsing your receipt...
                        </p>
                      </div>
                    )}

                    {/* Error State */}
                    {receiptState.receiptParseError && (
                      <div className="mt-3 p-3 bg-red-50 dark:bg-red-900/20 border border-red-100 dark:border-red-700 rounded-lg transition-colors duration-300">
                        <p className="text-sm text-red-700 dark:text-red-300 transition-colors duration-300">
                          <svg className="w-4 h-4 inline mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                            <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                          </svg>
                          {receiptState.receiptParseError}
                        </p>
                      </div>
                    )}

                    {/* Success State with Preview Toggle */}
                    {receiptState.currentReceiptUrl && !receiptState.isParsingReceipt && !receiptState.receiptParseError && (
                      <div className="mt-3 flex items-center justify-between p-3 bg-green-50 dark:bg-green-900/20 border border-green-100 dark:border-green-700 rounded-lg transition-colors duration-300">
                        <div className="flex items-center">
                          <svg className="w-4 h-4 text-green-600 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                            <path strokeLinecap="round" strokeLinejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                          </svg>
                          <span className="text-sm text-green-700 dark:text-green-300 font-medium transition-colors duration-300">
                            Receipt parsed successfully!
                          </span>
                        </div>
                        <button
                          type="button"
                          onClick={() => receiptState.setShowReceiptPreview(!receiptState.showReceiptPreview)}
                          className="text-sm text-green-700 dark:text-green-300 hover:text-green-800 dark:hover:text-green-200 font-medium transition-colors duration-300"
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

                {/* Payment Info Section */}
      {(paymentData?.tenant_name || paymentData?.property_name) && (
                  <div className="bg-white dark:bg-gray-800 rounded-lg p-5 shadow-sm border border-gray-100 dark:border-gray-700 transition-colors duration-300">
                    <div className="flex items-center mb-3">
                      <div className="w-9 h-9 bg-blue-50 dark:bg-blue-900/20 rounded-lg flex items-center justify-center mr-3">
                        <svg className="w-4 h-4 text-blue-600 dark:text-blue-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                          <path strokeLinecap="round" strokeLinejoin="round" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                        </svg>
                      </div>
                      <h3 className="text-base font-medium text-gray-900 dark:text-gray-100 transition-colors duration-300">Payment Information</h3>
                    </div>
                    <div className="space-y-2">
          {paymentData?.tenant_name && (
                        <div className="flex items-center text-sm">
                          <span className="font-medium text-gray-600 dark:text-gray-400 mr-2 transition-colors duration-300">Tenant:</span>
                          <span className="text-gray-900 dark:text-gray-100 transition-colors duration-300">{paymentData.tenant_name}</span>
                        </div>
          )}
          {paymentData?.property_name && (
                        <div className="flex items-center text-sm">
                          <span className="font-medium text-gray-600 dark:text-gray-400 mr-2 transition-colors duration-300">Property:</span>
                          <span className="text-gray-900 dark:text-gray-100 transition-colors duration-300">{paymentData.property_name}</span>
                        </div>
                      )}
                      {paymentData?.id && (
                        <div className="flex items-center text-sm">
                          <span className="font-medium text-gray-600 dark:text-gray-400 mr-2 transition-colors duration-300">Payment ID:</span>
                          <span className="text-gray-900 dark:text-gray-100 transition-colors duration-300">#{paymentData.id}</span>
                        </div>
                      )}
                    </div>
        </div>
      )}

                {/* Payment Details */}
                <div className="bg-white dark:bg-gray-800 rounded-lg p-5 shadow-sm border border-gray-100 dark:border-gray-700">
                  <div className="flex items-center mb-3">
                    <div className="w-9 h-9 bg-green-50 dark:bg-green-900/20 rounded-lg flex items-center justify-center mr-3">
                      <svg className="w-4 h-4 text-green-600 dark:text-green-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                      </svg>
                    </div>
                    <h3 className="text-base font-medium text-gray-900 dark:text-gray-100 transition-colors duration-300">Payment Details</h3>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2 transition-colors duration-300">
                        Amount <span className="text-red-500">*</span>
                      </label>
                      <div className="relative">
                        <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                          <span className="text-gray-500 dark:text-gray-400 sm:text-sm transition-colors duration-300">$</span>
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
                          className="w-full px-4 py-2.5 pl-7 border border-gray-200 dark:border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
                        />
                      </div>
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2 transition-colors duration-300">
                        Reduction (Optional)
                      </label>
                      <div className="relative">
                        <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                          <span className="text-gray-500 dark:text-gray-400 sm:text-sm transition-colors duration-300">$</span>
                        </div>
                        <input
                          type="number"
                          name="reduction"
                          value={formData.reduction}
                          onChange={handleInputChange}
                          min="0"
                          step="0.01"
                          placeholder="0.00"
                          className="w-full px-4 py-2.5 pl-7 border border-gray-200 dark:border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
                        />
                      </div>
                      <p className="mt-1 text-xs text-gray-500 dark:text-gray-400 transition-colors duration-300">
                        Enter any one-time discount or reduction
                      </p>
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2 transition-colors duration-300">
                        Payment Date <span className="text-red-500">*</span>
                      </label>
                      <input
                        type="date"
                        name="payment_date"
                        value={formData.payment_date}
                        onChange={handleInputChange}
                        required
                        className="w-full px-4 py-2.5 border border-gray-200 dark:border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
                      />
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2 transition-colors duration-300">
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
                      <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2 transition-colors duration-300">
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
                      <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2 transition-colors duration-300">
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
                        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2 transition-colors duration-300">
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
                        <p className="mt-1 text-xs text-gray-500 dark:text-gray-400 transition-colors duration-300">
                          Please provide a reason for the reduction
                        </p>
                      </div>
                    )}

                    <div className="md:col-span-2">
                      <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2 transition-colors duration-300">
                        Notes
                      </label>
                      <textarea
                        name="notes"
                        value={formData.notes}
                        onChange={handleInputChange}
                        rows="3"
                        placeholder="Optional payment notes..."
                        className="w-full px-4 py-2.5 border border-gray-200 dark:border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 resize-none"
                      />
                    </div>
                  </div>
                </div>
      </div>
    </form>

            {/* Footer */}
            <div className="px-6 py-5 bg-gray-50 dark:bg-gray-900 border-t border-gray-200 dark:border-gray-700 transition-colors duration-300">
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
                    'Update Payment'
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

export default EditPaymentModal;
