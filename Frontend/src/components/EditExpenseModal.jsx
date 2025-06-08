import React, { useState, useEffect } from "react";
import { toast } from "react-toastify";
import {
  updateExpenseAPI,
  fetchProperties,
  parseExpenseReceiptAPI,
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

// Reusing PAYMENT_METHODS and PAYMENT_STATUSES if expense categories/statuses are similar,
// otherwise define EXPENSE_CATEGORIES, EXPENSE_STATUSES
const EXPENSE_CATEGORIES = [
  "maintenance",
  "utilities",
  "taxes",
  "insurance",
  "administrative",
  "other",
];

const EditExpenseModal = ({ isOpen, onClose, onSuccess, expenseData }) => {
  const initialFormData = {
    category: "",
    amount: "", // Subtotal (before tax)
    expense_date: "",
    description: "",
    receipt_url: null,
    property_id: "",
    property_name: "", // For displaying property name
    taxes: [{ tax_name: "", tax_rate: "" }],
  };
  const [formData, setFormData] = useState(initialFormData);
  const [calculatedTotalTaxAmount, setCalculatedTotalTaxAmount] = useState(0);
  const [calculatedTotalAmount, setCalculatedTotalAmount] = useState(0);
  const [properties, setProperties] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [isParsingReceipt, setIsParsingReceipt] = useState(false);
  const [receiptParseError, setReceiptParseError] = useState(null);
  const [currentReceiptUrl, setCurrentReceiptUrl] = useState(null);
  const [showReceiptPreview, setShowReceiptPreview] = useState(false);

  useEffect(() => {
    if (isOpen && expenseData) {
      // Fetch properties to find the name for the given property_id
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
          // Potentially show a toast or minor error, but don't block form population
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
          property_name: currentPropertyName, // Set fetched or default property name
          taxes:
            expenseData.taxes && expenseData.taxes.length > 0
              ? expenseData.taxes.map((tax) => ({
                  tax_name: tax.tax_name || "",
                  tax_rate: tax.tax_rate?.toString() || "",
                }))
              : [{ tax_name: "", tax_rate: "" }],
        });
        setCurrentReceiptUrl(expenseData.receipt_url || null);
        setError(null); // Clear any previous errors
        setReceiptParseError(null);
        setShowReceiptPreview(false);
      };
      loadPropertiesAndSetForm();
    } else if (!isOpen) {
      // Reset form if modal is closed (e.g. if not saved)
      setFormData(initialFormData);
      setCurrentReceiptUrl(null);
      setCalculatedTotalAmount(0);
      setCalculatedTotalTaxAmount(0);
      setError(null);
      setReceiptParseError(null);
      setShowReceiptPreview(false);
    }
  }, [isOpen, expenseData]);

  useEffect(() => {
    const subtotal = Number.parseFloat(formData.amount) || 0;
    let totalTax = 0;
    if (subtotal > 0) {
      formData.taxes.forEach((tax) => {
        const rate = Number.parseFloat(tax.tax_rate);
        if (tax.tax_name && !isNaN(rate) && rate > 0) {
          totalTax += (subtotal * rate) / 100;
        }
      });
    }
    setCalculatedTotalTaxAmount(totalTax);
    setCalculatedTotalAmount(subtotal + totalTax);
  }, [formData.amount, formData.taxes]);

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

  const handleReceiptFileChange = async (e) => {
    const file = e.target.files[0];
    if (file) {
      setReceiptParseError(null);
      setIsParsingReceipt(true);
      // setCurrentReceiptUrl(null); // Keep existing URL until new one is confirmed
      // setShowReceiptPreview(false);
      const formDataForApi = new FormData();
      formDataForApi.append("file", file);
      try {
        const response = await parseExpenseReceiptAPI(formDataForApi);
        if (response?.parsed_details) {
          const { parsed_details, receipt_url: parsedReceiptUrl } = response;
          setCurrentReceiptUrl(parsedReceiptUrl); // Set new receipt URL immediately
          setFormData((prev) => ({ ...prev, receipt_url: parsedReceiptUrl })); // Keep formData in sync
          toast.success(
            response.message || "New receipt parsed and ready to save."
          );
        } else {
          throw new Error("Invalid response from receipt parser.");
        }
      } catch (err) {
        setReceiptParseError(err.message || "Failed to parse new receipt.");
        toast.error(err.message || "Failed to parse new receipt.");
      } finally {
        setIsParsingReceipt(false);
      }
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
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
        : undefined, // Ensure UTC for backend
      description: formData.description || undefined,
      receipt_url: currentReceiptUrl,
      // property_id: formData.property_id ? parseInt(formData.property_id) : undefined, // Property ID is not editable
      taxes: formData.taxes
        .filter(
          (tax) =>
            tax.tax_name &&
            tax.tax_rate !== "" &&
            !isNaN(Number.parseFloat(tax.tax_rate)) &&
            Number.parseFloat(tax.tax_rate) >= 0
        )
        .map((tax) => ({
          tax_name: tax.tax_name,
          tax_rate: Number.parseFloat(tax.tax_rate),
        })),
    };

    // Clean payload: remove undefined fields to avoid overwriting with nothing
    const cleanedPayload = Object.entries(payload).reduce(
      (acc, [key, value]) => {
        if (value !== undefined) acc[key] = value;
        return acc;
      },
      {}
    );

    try {
      await updateExpenseAPI(expenseData.id, cleanedPayload);
      toast.success("Expense updated successfully!");
      onSuccess?.();
      onClose(); // This will trigger form reset via useEffect on isOpen change
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

  const formContent = (
    <form onSubmit={handleSubmit} className="space-y-5 w-full">
      {formData.property_name && (
        <div className="mb-3 p-3 bg-blue-50 border border-blue-200 rounded-lg">
          <p className="text-sm text-blue-700">
            <span className="font-semibold">Property:</span>{" "}
            {formData.property_name}
          </p>
        </div>
      )}
      <div>
        <Label htmlFor={`category_edit-${expenseData?.id}`} required>
          Category
        </Label>
        <Select
          name="category"
          id={`category_edit-${expenseData?.id}`}
          value={formData.category}
          onChange={handleInputChange}
          required
        >
          <option value="">Select Category</option>
          {EXPENSE_CATEGORIES.map((cat) => (
            <option key={cat} value={cat}>
              {cat.charAt(0).toUpperCase() + cat.slice(1)}
            </option>
          ))}
        </Select>
      </div>
      <div>
        <Label htmlFor={`amount_edit-${expenseData?.id}`} required>
          Subtotal (before tax)
        </Label>
        <div className="relative">
          <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
            <span className="text-gray-500 sm:text-sm">$</span>
          </div>
          <Input
            type="number"
            name="amount"
            id={`amount_edit-${expenseData?.id}`}
            value={formData.amount}
            onChange={handleInputChange}
            required
            min="0.01"
            step="0.01"
            placeholder="0.00"
            className="pl-7"
          />
        </div>
      </div>

      <div className="space-y-3 pt-2">
        <Label>Taxes</Label>
        {formData.taxes.map((tax, index) => (
          <div
            key={index}
            className="flex items-center space-x-2 p-3 border border-gray-200 rounded-lg bg-gray-50/50"
          >
            <div className="flex-grow">
              <Input
                type="text"
                name="tax_name"
                id={`edit_tax_name_${index}_${expenseData?.id}`}
                value={tax.tax_name}
                onChange={(e) => handleTaxInputChange(index, e)}
                placeholder="Tax Name (e.g., GST)"
                className="text-sm py-2"
              />
            </div>
            <div className="w-1/3 relative">
              <Input
                type="number"
                name="tax_rate"
                id={`edit_tax_rate_${index}_${expenseData?.id}`}
                value={tax.tax_rate}
                onChange={(e) => handleTaxInputChange(index, e)}
                min="0"
                step="0.01"
                placeholder="Rate"
                className="text-sm py-2 pr-6"
              />
              <div className="absolute inset-y-0 right-0 pr-2.5 flex items-center pointer-events-none">
                <span className="text-gray-500 text-sm">%</span>
              </div>
            </div>
            {formData.taxes.length > 1 && (
              <Button
                type="button"
                variant="danger"
                onClick={() => removeTaxItem(index)}
                className="p-2 text-xs h-9 w-9 flex items-center justify-center bg-red-50 text-red-500 hover:bg-red-100 hover:text-red-600 border-none shadow-none"
                title="Remove Tax Item"
              >
                <i className="fas fa-trash-alt" />
              </Button>
            )}
          </div>
        ))}
        <Button
          type="button"
          variant="secondary"
          onClick={addTaxItem}
          className="mt-1 text-sm py-2 border-gray-300 hover:border-gray-400"
        >
          <i className="fas fa-plus mr-2" /> Add Tax Item
        </Button>
      </div>

      <div>
        <Label>Total Tax Amount</Label>
        <div className="relative">
          <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
            <span className="text-gray-500 sm:text-sm">$</span>
          </div>
          <Input
            type="text"
            value={calculatedTotalTaxAmount.toFixed(2)}
            readOnly
            className="bg-gray-100 pl-7"
          />
        </div>
      </div>
      <div>
        <Label>Total Amount (incl. tax)</Label>
        <div className="relative">
          <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
            <span className="text-gray-500 sm:text-sm">$</span>
          </div>
          <Input
            type="text"
            value={calculatedTotalAmount.toFixed(2)}
            readOnly
            className="bg-gray-100 pl-7"
          />
        </div>
      </div>
      <div>
        <Label htmlFor={`expense_date_edit-${expenseData?.id}`} required>
          Expense Date
        </Label>
        <Input
          type="date"
          name="expense_date"
          id={`expense_date_edit-${expenseData?.id}`}
          value={formData.expense_date}
          onChange={handleInputChange}
          required
        />
      </div>
      <div>
        <Label htmlFor={`description_edit-${expenseData?.id}`}>
          Description
        </Label>
        <TextArea
          name="description"
          id={`description_edit-${expenseData?.id}`}
          value={formData.description}
          onChange={handleInputChange}
          rows="3"
          placeholder="Optional description of the expense"
        />
      </div>
      <div>
        <Label>Receipt (Optional)</Label>
        <Input
          type="file"
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
        {currentReceiptUrl && !isParsingReceipt && (
          <div className="mt-2">
            <Button
              type="button"
              variant="secondary"
              onClick={() => setShowReceiptPreview(!showReceiptPreview)}
              className="text-sm py-1.5"
              disabled={isParsingReceipt}
            >
              {showReceiptPreview ? (
                <>
                  <i className="fas fa-eye-slash mr-2" />
                  Hide Preview
                </>
              ) : (
                <>
                  <i className="fas fa-eye mr-2" />
                  Preview Current
                </>
              )}
            </Button>
          </div>
        )}
        <AnimatePresence>
          {showReceiptPreview && currentReceiptUrl && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: "24rem" }}
              exit={{ opacity: 0, height: 0 }}
              transition={{ duration: 0.3, ease: "easeInOut" }}
              className="mt-3 border rounded-lg overflow-hidden shadow bg-gray-50"
            >
              {(() => {
                const url = currentReceiptUrl;
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
                    ></iframe>
                  );
                } else {
                  return (
                    <iframe
                      src={url}
                      title="Receipt Preview"
                      className="w-full h-full border-0"
                      sandbox="allow-same-origin"
                    ></iframe>
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
        onClick={handleSubmit}
      >
        Update Expense
      </Button>
    </>
  );

  return (
    <ModalShell
      isOpen={isOpen}
      onClose={onClose} // The internal handleClose for reset is triggered by useEffect on isOpen and expenseData change
      title={modalTitle}
      error={error}
      footerContent={footerButtons}
      maxWidth="max-w-lg"
    >
      {formContent}
    </ModalShell>
  );
};

export default EditExpenseModal;
