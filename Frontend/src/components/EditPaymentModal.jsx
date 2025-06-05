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
} from "./ui/SharedModalComponents";
import { AnimatePresence, motion } from "framer-motion";

const PAYMENT_METHODS = [
  "Credit Card",
  "Bank Transfer",
  "Cash",
  "Check",
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
  const [isParsingReceipt, setIsParsingReceipt] = useState(false);
  const [receiptParseError, setReceiptParseError] = useState(null);
  // currentReceiptUrl is now directly managed in formData.receipt_url for simplicity upon successful parse
  const [showReceiptPreview, setShowReceiptPreview] = useState(false);

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
        receipt_url: paymentData.receipt_url || null, // Initialize with existing URL
      });
      setError(null); // Clear previous errors
      setReceiptParseError(null);
      setShowReceiptPreview(false);
      setIsParsingReceipt(false); // Ensure parsing state is reset
    } else if (!isOpen) {
      // Reset form when modal is closed and not just re-rendered
      setFormData(initialFormData);
      setError(null);
      setReceiptParseError(null);
      setShowReceiptPreview(false);
      setIsParsingReceipt(false);
    }
  }, [isOpen, paymentData]); // Re-run if isOpen or paymentData changes

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
  };

  const handleReceiptFileChange = async (e) => {
    const file = e.target.files[0];
    if (file) {
      setReceiptParseError(null);
      setIsParsingReceipt(true);
      // No need to clear formData.receipt_url here, let it hold the old one until successful parse
      const formDataForApi = new FormData();
      formDataForApi.append("file", file);
      try {
        const response = await parsePaymentReceiptAPI(formDataForApi);
        if (response && response.parsed_details) {
          const { parsed_details, receipt_url: parsedReceiptUrl } = response;
          setFormData((prev) => ({
            ...prev,
            // Optionally update other fields if desired, e.g., amount, date from receipt
            // amount: parsed_details.total_amount?.toString() || prev.amount,
            // payment_date: parsed_details.payment_date || prev.payment_date,
            receipt_url: parsedReceiptUrl, // Update with the new URL
          }));
          toast.success(
            response.message || "New receipt parsed and ready to save."
          );
        } else {
          throw new Error("Invalid response from receipt parser.");
        }
      } catch (err) {
        setReceiptParseError(
          err.message || "Failed to parse new receipt. Please try again."
        );
        toast.error(err.message || "Failed to parse new receipt.");
      } finally {
        setIsParsingReceipt(false);
      }
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!paymentData || !paymentData.id) {
      setError("Original payment data is missing. Cannot update.");
      return;
    }
    setError(null);
    setIsLoading(true);

    const payload = {
      amount: formData.amount !== "" ? Number.parseFloat(formData.amount) : undefined,
      payment_date: formData.payment_date
        ? `${formData.payment_date}T00:00:00Z`
        : undefined, // Ensure UTC
      payment_method: formData.payment_method || undefined,
      status: formData.status || undefined,
      description: formData.notes || undefined,
      receipt_url: formData.receipt_url, // This now holds new or original URL
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
    <form id="edit-payment-form" onSubmit={handleSubmit} className="space-y-5 w-full">
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
      <div>
        <Label htmlFor={`payment-receipt-upload-${paymentData?.id}`}>Payment Receipt (Optional)</Label>
        <Input
          type="file"
          id={`payment-receipt-upload-${paymentData?.id}`}
          accept=".pdf,.png,.jpg,.jpeg"
          onChange={handleReceiptFileChange}
          disabled={isParsingReceipt}
          className="block w-full text-sm file:mr-3 file:py-2 file:px-3 file:rounded-lg file:border-0 file:text-sm file:font-medium file:bg-blue-50 file:text-blue-600 hover:file:bg-blue-100 disabled:opacity-50"
        />
        {isParsingReceipt && (
          <p className="mt-1.5 text-sm text-blue-600">Parsing new receipt...</p>
        )}
        {receiptParseError && (
          <p className="mt-1.5 text-sm text-red-600">
            Error: {receiptParseError}
          </p>
        )}
        {formData.receipt_url && !isParsingReceipt && (
          <div className="mt-2">
            <Button
              type="button"
              variant="secondary"
              onClick={() => setShowReceiptPreview(!showReceiptPreview)}
              className="text-sm py-1.5"
            >
              {showReceiptPreview ? (
                <>
                  <i className="fas fa-eye-slash mr-2" />Hide Preview
                </>
              ) : (
                <>
                  <i className="fas fa-eye mr-2" />Preview Current
                </>
              )}
            </Button>
          </div>
        )}
        <AnimatePresence>
          {showReceiptPreview && formData.receipt_url && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: "24rem" }}
              exit={{ opacity: 0, height: 0 }}
              transition={{ duration: 0.3, ease: "easeInOut" }}
              className="mt-3 border rounded-lg overflow-hidden shadow bg-gray-50"
            >
              {(() => {
                const url = formData.receipt_url;
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
                  // Try to hint the PDF viewer to fit the content
                  const pdfDisplayUrl = `${url}#view=FitH`; // Fit Height. Alternatives: FitW (Fit Width), page-fit
                  return (
                    <iframe
                      src={pdfDisplayUrl}
                      title="Receipt Preview"
                      className="w-full h-full border-0"
                    />
                  );
                } else {
                  return (
                    <iframe
                      src={url}
                      title="Receipt Preview"
                      className="w-full h-full border-0"
                    />
                  );
                }
              })()}
            </motion.div>
          )}
        </AnimatePresence>
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
        variant="primary"
        isLoading={isLoading || isParsingReceipt}
        loadingText={
          isLoading
            ? "Updating..."
            : isParsingReceipt
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
