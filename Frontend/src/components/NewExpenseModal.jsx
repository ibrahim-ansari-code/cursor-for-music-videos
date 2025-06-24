import React, { useState, useEffect, useRef } from "react";
import { toast } from "react-toastify";
import {
  fetchProperties,
  createExpense,
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
import { extractExpenseReceiptData } from "../utils/receiptUtils";
import { filterValidTaxes } from "../utils/taxValidation";

const EXPENSE_CATEGORIES = [
  "maintenance",
  "utilities",
  "taxes",
  "insurance",
  "administrative",
  "other",
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
    taxes: [{ tax_name: "", tax_rate: "" }],
  };
  const [formData, setFormData] = useState(initialFormData);
  const [calculatedTotalTaxAmount, setCalculatedTotalTaxAmount] = useState(0);
  const [calculatedTotalAmount, setCalculatedTotalAmount] = useState(0);
  const [properties, setProperties] = useState([]);
  const [isLoading, setIsLoading] = useState(false); // For main form submission
  const [error, setError] = useState(null); // General modal error
  const [dropdownOpen, setDropdownOpen] = useState("");

  // Receipt upload state using shared hook
  const receiptState = useReceiptUpload();

  const propertySearchInputRef = useRef(null);
  const receiptParseAbortControllerRef = useRef(null);

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
    return () => {
      if (receiptParseAbortControllerRef.current) {
        receiptParseAbortControllerRef.current.abort();
        receiptParseAbortControllerRef.current = null;
      }
    };
  }, []);

  useEffect(() => {
    if (!isOpen && receiptParseAbortControllerRef.current) {
      receiptParseAbortControllerRef.current.abort();
      receiptParseAbortControllerRef.current = null;
    }
  }, [isOpen]);

  useEffect(() => {
    const subtotal = Number.parseFloat(formData.amount) || 0;
    let newTotalTax = 0;
    
    if (subtotal > 0) {
      formData.taxes.forEach((tax) => {
        const rate = Number.parseFloat(tax.tax_rate);
        // Validate tax rate is numeric and within bounds before calculation
        if (tax.tax_name && tax.tax_name.trim() && !isNaN(rate) && rate > 0 && rate <= 100) {
          newTotalTax += (subtotal * rate) / 100;
        }
      });
    }
    
    // Ensure calculated values are reasonable
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
      // Use functional form of setFormData to access latest state and avoid stale closure
      setFormData((prev) => {
        // Use utility functions for clean, maintainable data extraction with latest form state
        const extractedData = extractExpenseReceiptData(parsedDetails, prev);

        // Show success message using extracted data
        toast.success(extractedData.successMessage);

        // Return updated form data with extracted information
        return {
          ...prev,
          amount: extractedData.amount,
          taxes: extractedData.taxes,
          expense_date: extractedData.expense_date,
          description: extractedData.description,
        };
      });
    }
  );

  const handleExpensePropertySelect = (property) => {
    setFormData((prev) => ({
      ...prev,
      property_id: property.id.toString(),
      property_name: property.name,
    }));
    setDropdownOpen("");
  };

  const handleExpensePropertySelectKeyDown = (event, property) => {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      handleExpensePropertySelect(property);
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

    setIsLoading(true);
    try {
      const expenseData = {
        property_id: Number.parseInt(formData.property_id, 10),
        category: formData.category,
        subtotal_amount: Number.parseFloat(formData.amount),
        expense_date: formData.expense_date,
        description: formData.description || "",
        receipt_url: receiptState.currentReceiptUrl,
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
      toast.success("Expense created successfully!");
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

  useEffect(() => {
    function handleClickOutside(event) {
      if (
        propertySearchInputRef.current &&
        !propertySearchInputRef.current.contains(event.target)
      ) {
        setDropdownOpen("");
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, [propertySearchInputRef]);

  const formContent = (
    <form
      id="new-expense-form"
      onSubmit={handleSubmit}
      className="space-y-5 w-full"
    >
      {/* Receipt Upload with Parse Option - Moved to top of form */}
      <ReceiptUploadAndPreview
        {...receiptState}
        onReceiptFileChange={handleReceiptFileChange}
        title="Upload and Parse Receipt (Optional)"
        subtitle="Auto-extracts tax, amount, date & description"
        disabled={isLoading}
      />
      <div>
        <Label htmlFor="property_id" required>
          Property
        </Label>
        <div className="relative" ref={propertySearchInputRef}>
          <Input
            type="text"
            id="property_search"
            name="property_search"
            placeholder="Search and select a property..."
            value={formData.property_name} // Display selected property name
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
          />
          {dropdownOpen === "property" && properties.length > 0 && (
            <div className="absolute z-20 mt-1 w-full bg-white border border-gray-300 rounded-lg shadow-lg max-h-60 overflow-auto">
              <ul className="py-1" role="listbox">
                {properties
                  .filter((property) =>
                    property.name
                      .toLowerCase()
                      .includes(formData.property_name.toLowerCase())
                  )
                  .map((property) => (
                    <li
                      key={property.id}
                      role="option"
                      tabIndex={0}
                      aria-selected={
                        formData.property_id === property.id.toString()
                      }
                      className="px-4 py-2.5 text-sm text-gray-700 hover:bg-blue-500 hover:text-white cursor-pointer transition-colors duration-150"
                      onClick={() => handleExpensePropertySelect(property)}
                      onKeyDown={(e) =>
                        handleExpensePropertySelectKeyDown(e, property)
                      }
                    >
                      {property.name}
                    </li>
                  ))}
              </ul>
            </div>
          )}
        </div>
      </div>

      <div>
        <Label htmlFor="category" required>
          Category
        </Label>
        <Select
          id="category"
          name="category"
          value={formData.category}
          onChange={handleInputChange}
          required
        >
          <option value="">Select a category</option>
          {EXPENSE_CATEGORIES.map((cat) => (
            <option key={cat} value={cat}>
              {cat.charAt(0).toUpperCase() + cat.slice(1)}
            </option>
          ))}
        </Select>
      </div>

      <div>
        <Label htmlFor="amount" required>
          Subtotal (before tax)
        </Label>
        <div className="relative">
          <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
            <span className="text-gray-500 sm:text-sm">$</span>
          </div>
          <Input
            type="number"
            id="amount"
            name="amount"
            value={formData.amount}
            onChange={handleInputChange}
            min="0.01" // Typically expenses should be positive
            step="0.01"
            required
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
                id={`tax_name_${index}`}
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
                id={`tax_rate_${index}`}
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
                title="Remove Tax"
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
        <Label htmlFor="expense_date" required>
          Date
        </Label>
        <Input
          type="date"
          id="expense_date"
          name="expense_date"
          value={formData.expense_date}
          onChange={handleInputChange}
          required
        />
      </div>

      <div>
        <Label htmlFor="description">Description</Label>
        <TextArea
          id="description"
          name="description"
          value={formData.description}
          onChange={handleInputChange}
          rows="2"
          placeholder="Optional description of the expense..."
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
        form="new-expense-form"
        variant="primary"
        isLoading={isLoading || receiptState.isParsingReceipt}
        loadingText={isLoading ? "Creating..." : "Parsing..."}
      >
        Create Expense
      </Button>
    </>
  );

  return (
    <ModalShell
      isOpen={isOpen}
      onClose={onClose}
      title="Add New Expense"
      error={error} // General error for the modal
      footerContent={footerButtons}
      maxWidth="max-w-lg" // Slightly wider for more complex form
    >
      {formContent}
    </ModalShell>
  );
};

export default NewExpenseModal;
