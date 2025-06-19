import React, { useState, useEffect } from "react";
import { toast } from "react-toastify";
import {
  updatePayment, // To update the payment
  parsePaymentReceiptAPI,
} from "../utils/api";
import {
  ModalShell,
  Label,
  Input,
  Select,
  TextArea,
  Button,
  ReceiptUploadAndPreview,
  useReceiptUpload,
  createReceiptFileChangeHandler,
} from "./ui/SharedModalComponents";
import { extractPaymentReceiptDataForEdit } from "../utils/receiptUtils";

import { PAYMENT_METHODS, PAYMENT_STATUSES } from "../utils/constants";

const EditPaymentModal = ({ isOpen, onClose, onSuccess, paymentData }) => {
  const initialFormData = {
    amount: "",
    payment_date: new Date().toISOString().split("T")[0],
    payment_method: "",
    status: "Paid",
    notes: "", // Maps to description in backend
    receipt_url: null,
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
    parsePaymentReceiptAPI,
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
    };

    const cleanedPayload = Object.entries(payload).reduce(
      (acc, [key, value]) => {
        if (value !== undefined) acc[key] = value;
        return acc;
      },
      {}
    );

    try {
      await updatePayment(paymentData.id, cleanedPayload);
      toast.success("Payment updated successfully!");
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

  const modalTitle = `Edit Payment for ${
    paymentData?.tenant_name || "Tenant"
  } (ID: ${paymentData?.id || "N/A"})`;

  const formContent = (
    <form
      id="edit-payment-form"
      onSubmit={handleSubmit}
      className="space-y-5 w-full"
    >
      {/* Receipt Upload with Parse Option - At top of form */}
      <ReceiptUploadAndPreview
        {...receiptState}
        onReceiptFileChange={handleReceiptFileChange}
        title="Upload and Parse Receipt (Optional)"
        subtitle="Auto-extracts amount, date & payment method"
        disabled={isLoading}
      />

      {(paymentData?.tenant_name || paymentData?.property_name) && (
        <div className="mb-3 p-3 bg-blue-50 border border-blue-200 rounded-lg text-sm">
          {paymentData?.tenant_name && (
            <p className="text-blue-700">
              <span className="font-semibold">Tenant:</span>{" "}
              {paymentData.tenant_name}
            </p>
          )}
          {paymentData?.property_name && (
            <p className="text-blue-600 mt-1">
              <span className="font-semibold">Property:</span>{" "}
              {paymentData.property_name}
            </p>
          )}
        </div>
      )}
      <div>
        <Label htmlFor={`amount-${paymentData?.id}`} required>
          Amount
        </Label>
        <div className="relative">
          <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
            <span className="text-gray-500 sm:text-sm">$</span>
          </div>
          <Input
            type="number"
            name="amount"
            id={`amount-${paymentData?.id}`}
            value={formData.amount}
            onChange={handleInputChange}
            min="0.01"
            step="0.01"
            required
            placeholder="0.00"
            className="pl-7"
          />
        </div>
      </div>
      <div>
        <Label htmlFor={`payment_date-${paymentData?.id}`} required>
          Payment Date
        </Label>
        <Input
          type="date"
          name="payment_date"
          id={`payment_date-${paymentData?.id}`}
          value={formData.payment_date}
          onChange={handleInputChange}
          required
        />
      </div>
      <div>
        <Label htmlFor={`payment_method-${paymentData?.id}`} required>
          Payment Method
        </Label>
        <Select
          name="payment_method"
          id={`payment_method-${paymentData?.id}`}
          value={formData.payment_method}
          onChange={handleInputChange}
          required
        >
          <option value="">Select a method</option>
          {PAYMENT_METHODS.map((method) => (
            <option key={method} value={method}>
              {method}
            </option>
          ))}
        </Select>
      </div>
      <div>
        <Label htmlFor={`status-${paymentData?.id}`} required>
          Status
        </Label>
        <Select
          name="status"
          id={`status-${paymentData?.id}`}
          value={formData.status}
          onChange={handleInputChange}
          required
        >
          {PAYMENT_STATUSES.map((s) => (
            <option key={s} value={s}>
              {s}
            </option>
          ))}
        </Select>
      </div>
      <div>
        <Label htmlFor={`notes-${paymentData?.id}`}>Notes</Label>
        <TextArea
          name="notes"
          id={`notes-${paymentData?.id}`}
          value={formData.notes}
          onChange={handleInputChange}
          rows="3"
          placeholder="Optional payment notes..."
        />
      </div>
    </form>
  );

  const footerButtons = (
    <>
      <Button type="button" variant="secondary" onClick={onClose}>
        Cancel
      </Button>
      <Button
        type="submit"
        form="edit-payment-form"
        variant="primary"
        isLoading={isLoading || receiptState.isParsingReceipt}
        loadingText={
          isLoading
            ? "Updating..."
            : receiptState.isParsingReceipt
            ? "Parsing..."
            : "Saving..."
        }
      >
        Update Payment
      </Button>
    </>
  );

  return (
    <ModalShell
      isOpen={isOpen}
      onClose={onClose} // onClose from props will trigger reset via useEffect
      title={modalTitle}
      error={error}
      footerContent={footerButtons}
      maxWidth="max-w-lg"
    >
      {formContent}
    </ModalShell>
  );
};

export default EditPaymentModal;
