import React, { useState, useEffect, useMemo, useRef } from "react";
import { toast } from "react-toastify";
import {
  updateExpense,
  fetchProperties,
  parseExpenseReceipt,
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
import { extractExpenseReceiptDataForEdit } from "../utils/receiptUtils";
import { filterValidTaxes } from "../utils/taxValidation";

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
    amount: "",
    expense_date: "",
    description: "",
    receipt_url: null,
    property_id: "",
    property_name: "",
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
          property_name: currentPropertyName,
          taxes:
            expenseData.taxes && expenseData.taxes.length > 0
              ? expenseData.taxes.map((tax) => ({
                  tax_name: tax.tax_name || "",
                  tax_rate: tax.tax_rate?.toString() || "",
                }))
              : [{ tax_name: "", tax_rate: "" }],
        });
        receiptState.resetReceiptState();
        // Set the current receipt URL if editing existing expense with receipt
        if (expenseData.receipt_url) {
          receiptState.setCurrentReceiptUrl(expenseData.receipt_url);
        }
        setError(null); // Clear any previous errors
      };
      loadPropertiesAndSetForm();
    } else if (!isOpen) {
      // Reset form if modal is closed
      setFormData(initialFormData);
      receiptState.resetReceiptState();
      setError(null);
    }
  }, [isOpen, expenseData]);

  const { totalTax, totalAmount } = useMemo(() => {
    const subtotal = Number.parseFloat(formData.amount) || 0;
    let newTotalTax = 0;
    
    if (subtotal > 0) {
      formData.taxes.forEach((tax) => {
        const rate = Number.parseFloat(tax.tax_rate);
        // Validate tax rate is numeric and within bounds before calculation
        if (tax.tax_name && !isNaN(rate) && rate >= 0 && rate <= 100) {
          newTotalTax += (subtotal * rate) / 100;
        }
      });
    }
    
    // Ensure calculated values are reasonable and round to 2 decimal places to avoid floating point issues
    const finalTotalTax = parseFloat(Math.max(0, newTotalTax).toFixed(2));
    const finalTotalAmount = parseFloat((subtotal + finalTotalTax).toFixed(2));
    
    return {
      totalTax: finalTotalTax,
      totalAmount: finalTotalAmount,
    };
  }, [formData.amount, formData.taxes]);

  // Currency formatter for better display

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

  // Create receipt file change handler using shared components
  const handleReceiptFileChange = createReceiptFileChangeHandler(
    parseExpenseReceipt,
    receiptState,
    (parsedDetails, receiptUrl) => {
      // Use utility functions for conservative edit mode data extraction
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
      receipt_url: receiptState.currentReceiptUrl || formData.receipt_url,
      // property_id: formData.property_id ? parseInt(formData.property_id) : undefined, // Property ID is not editable
      taxes: filterValidTaxes(formData.taxes)
          .map((tax) => ({
            tax_name: tax.tax_name.trim(),
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
      await updateExpense(expenseData.id, cleanedPayload);
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
      {/* Receipt Upload with Parse Option - At top of form */}
      <ReceiptUploadAndPreview
        {...receiptState}
        onReceiptFileChange={handleReceiptFileChange}
        title="Upload and Parse Receipt (Optional)"
        subtitle="Auto-extracts tax, amount, date & description"
        disabled={isLoading}
      />

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
                max="100"
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
            value={decimalFormatter.format(totalTax)}
            readOnly
            className="bg-gray-100 pl-7"
            title={`Exact value: $${totalTax}`}
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
            value={decimalFormatter.format(totalAmount)}
            readOnly
            className="bg-gray-100 pl-7"
            title={`Exact value: $${totalAmount}`}
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
        isLoading={isLoading || receiptState.isParsingReceipt}
        loadingText={
          isLoading
            ? "Updating..."
            : receiptState.isParsingReceipt
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
