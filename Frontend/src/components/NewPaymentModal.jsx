import React, { useState, useEffect, useRef } from "react";
import { toast } from "react-toastify";
import {
  fetchProperties,
  fetchTenantsByProperty,
  createPayment,
  fetchLeases,
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

const NewPaymentModal = ({ isOpen, onClose, onSuccess }) => {
  const initialFormData = {
    property_id: "",
    property_name: "",
    tenant_id: "",
    tenant_name: "",
    amount: "",
    payment_date: new Date().toISOString().split("T")[0],
    payment_method: "Other",
    status: "Paid",
    notes: "",
    receipt_url: null,
    transaction_reference: "",
  };
  const [formData, setFormData] = useState(initialFormData);
  const [properties, setProperties] = useState([]);
  const [tenants, setTenants] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [lease, setLease] = useState(null);
  const [isParsingReceipt, setIsParsingReceipt] = useState(false);
  const [receiptParseError, setReceiptParseError] = useState(null);
  const [showReceiptPreview, setShowReceiptPreview] = useState(false);
  const [dropdownOpen, setDropdownOpen] = useState("");

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
      setFormData(initialFormData);
      setError(null);
      setLease(null);
      setTenants([]);
      setIsParsingReceipt(false);
      setReceiptParseError(null);
      setShowReceiptPreview(false);
      setDropdownOpen("");
    }
  }, [isOpen]);

  useEffect(() => {
    const loadTenants = async () => {
      if (formData.property_id) {
        try {
          const data = await fetchTenantsByProperty(formData.property_id);
          setTenants(data);
          setFormData((prev) => ({ ...prev, tenant_id: "", tenant_name: "" }));
          setLease(null);
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
  }, [formData.property_id]);

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
              l.property_id === parseInt(formData.property_id) &&
              l.status.toLowerCase() === "active"
          );

          if (activeLease) {
            setLease(activeLease);
            setError(null);
          } else {
            setError(
              "No active lease found for this tenant on the selected property."
            );
            setLease(null);
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

  const handleReceiptFileChange = async (e) => {
    const file = e.target.files[0];
    if (file) {
      setReceiptParseError(null);
      setIsParsingReceipt(true);

      const formDataForApi = new FormData();
      formDataForApi.append("file", file);

      try {
        const response = await parsePaymentReceiptAPI(formDataForApi);
        if (response?.parsed_details) {
          const { parsed_details, receipt_url: parsedReceiptUrl } = response;
          setFormData((prev) => ({
            ...prev,
            amount: parsed_details.total_amount?.toString() || prev.amount,
            payment_date: parsed_details.payment_date || prev.payment_date,
            payment_method:
              parsed_details.payment_method || prev.payment_method,
            notes: parsed_details.description_notes || prev.notes,
            receipt_url: parsedReceiptUrl,
            transaction_reference: parsed_details.transaction_reference || prev.transaction_reference,
          }));
          toast.success(response.message || "Receipt parsed successfully!");
        } else {
          throw new Error("Invalid response from receipt parser.");
        }
      } catch (err) {
        setReceiptParseError(err.message || "Failed to parse receipt.");
        toast.error(
          err.message ||
            "Failed to parse receipt. Please enter details manually."
        );
      } finally {
        setIsParsingReceipt(false);
      }
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);

    if (!formData.property_id) {
      setError("Please select a property.");
      return;
    }
    if (!formData.tenant_id) {
      setError("Please select a tenant.");
      return;
    }
    if (!lease) {
      setError(
        "No active lease found for this tenant and property. Cannot create payment."
      );
      return;
    }
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

    setIsLoading(true);
    try {
      const paymentPayload = {
        lease_id: lease.id,
        tenant_name: formData.tenant_name,
        amount: Number.parseFloat(formData.amount),
        payment_date: formData.payment_date
          ? `${formData.payment_date}T00:00:00Z`
          : null,
        payment_method: formData.payment_method,
        status: formData.status,
        description: formData.notes || "",
        receipt_url: formData.receipt_url,
        transaction_reference: formData.transaction_reference || null,
      };

      await createPayment(paymentPayload);
      toast.success("Payment created successfully!");
      onSuccess?.();
      onClose();
    } catch (err) {
      console.error("Failed to create payment:", err);
      const errorMsg =
        err.data?.detail ||
        err.message ||
        "Failed to create payment. Please try again.";
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
    if (event.key === 'Enter' || event.key === ' ') {
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
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault();
      handleTenantSelect(tenant);
    }
  };

  const formContent = (
    <form onSubmit={handleSubmit} className="space-y-5 w-full">
      <div ref={propertyDropdownRef}>
        <Label htmlFor="property_search" required>
          Property
        </Label>
        <Input
          type="text"
          id="property_search"
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
          role="combobox"
          aria-haspopup="listbox"
          aria-expanded={dropdownOpen === "property"}
          aria-controls="property-listbox"
          aria-autocomplete="list"
        />
        {dropdownOpen === "property" && properties.length > 0 && (
          <div className="absolute z-20 mt-1 w-full bg-white border border-gray-300 rounded-lg shadow-lg max-h-60 overflow-y-auto">
            <ul role="listbox" id="property-listbox" className="py-1">
              {properties
                .filter((p) =>
                  p.name
                    .toLowerCase()
                    .includes(formData.property_name.toLowerCase())
                )
                .map((p) => (
                  <li
                    key={p.id}
                    role="option"
                    tabIndex={0}
                    aria-selected={formData.property_id === p.id.toString()}
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

      <div ref={tenantDropdownRef}>
        <Label htmlFor="tenant_search" required>
          Tenant
        </Label>
        <Input
          type="text"
          id="tenant_search"
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
          role="combobox"
          aria-haspopup="listbox"
          aria-expanded={dropdownOpen === "tenant"}
          aria-controls="tenant-listbox"
          aria-autocomplete="list"
          className={
            !formData.property_id || tenants.length === 0
              ? "bg-gray-100 cursor-not-allowed"
              : ""
          }
        />
        {dropdownOpen === "tenant" && tenants.length > 0 && (
          <div className="absolute z-20 mt-1 w-full bg-white border border-gray-300 rounded-lg shadow-lg max-h-60 overflow-y-auto">
            <ul role="listbox" id="tenant-listbox" className="py-1">
              {tenants
                .filter((t) =>
                  (t.full_name || "")
                    .toLowerCase()
                    .includes(formData.tenant_name.toLowerCase())
                )
                .map((t) => (
                  <li
                    key={t.id}
                    role="option"
                    tabIndex={0}
                    aria-selected={formData.tenant_id === t.id}
                    className="px-4 py-2.5 text-sm text-gray-700 hover:bg-blue-500 hover:text-white cursor-pointer transition-colors duration-150"
                    onClick={() => handleTenantSelect(t)}
                    onKeyDown={(e) => handleTenantSelectKeyDown(e, t)}
                  >
                    {t.full_name} (Property Unit: {t.unit_name || "N/A"})
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
        {formData.property_id && tenants.length === 0 && (
          <p className="mt-1 text-xs text-gray-500">
            No tenants found for this property.
          </p>
        )}
      </div>

      {lease && (
        <div className="p-3 bg-green-50 border border-green-200 rounded-lg text-sm text-green-700">
          Active lease found: ID {lease.id}, Rent: $
          {lease.monthly_rent?.toLocaleString()}
        </div>
      )}
      {!lease && formData.property_id && formData.tenant_id && !error && (
        <div className="p-3 bg-yellow-50 border border-yellow-300 rounded-lg text-sm text-yellow-700">
          Verifying lease information...
        </div>
      )}

      <div>
        <Label htmlFor="amount" required>
          Amount
        </Label>
        <div className="relative">
          <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
            <span className="text-gray-500 sm:text-sm">$</span>
          </div>
          <Input
            type="number"
            name="amount"
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
        <Label htmlFor="payment_date" required>
          Payment Date
        </Label>
        <Input
          type="date"
          name="payment_date"
          value={formData.payment_date}
          onChange={handleInputChange}
          required
        />
      </div>
      <div>
        <Label htmlFor="payment_method" required>
          Payment Method
        </Label>
        <Select
          name="payment_method"
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
        <Label htmlFor="status" required>
          Status
        </Label>
        <Select
          name="status"
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
        <Label htmlFor="transaction_reference">Transaction Reference (Optional)</Label>
        <Input
          type="text"
          name="transaction_reference"
          value={formData.transaction_reference}
          onChange={handleInputChange}
          placeholder="e.g., Bank transaction ID"
        />
      </div>
      <div>
        <Label htmlFor="notes">Notes</Label>
        <TextArea
          name="notes"
          value={formData.notes}
          onChange={handleInputChange}
          rows="2"
          placeholder="Optional payment notes..."
        />
      </div>
      <div>
        <Label>Payment Receipt (Optional)</Label>
        <Input
          type="file"
          accept=".pdf,.png,.jpg,.jpeg"
          onChange={handleReceiptFileChange}
          disabled={isParsingReceipt}
          className="block w-full text-sm file:mr-3 file:py-2 file:px-3 file:rounded-lg file:border-0 file:text-sm file:font-medium file:bg-blue-50 file:text-blue-600 hover:file:bg-blue-100 disabled:opacity-50"
        />
        {isParsingReceipt && (
          <p className="mt-1.5 text-sm text-blue-600">Parsing receipt...</p>
        )}
        {receiptParseError && (
          <p className="mt-1.5 text-sm text-red-600">
            Error: {receiptParseError}
          </p>
        )}
        <div className="mt-2">
          <Button
            type="button"
            variant="secondary"
            onClick={() => setShowReceiptPreview(!showReceiptPreview)}
            className="text-sm py-1.5"
          >
            {showReceiptPreview ? (
              <>
                <i className="fas fa-eye-slash mr-2"></i>Hide Preview
              </>
            ) : (
              <>
                <i className="fas fa-eye mr-2"></i>Preview Receipt
              </>
            )}
          </Button>
        </div>
      </div>
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
                  ></iframe>
                );
              }
            })()}
          </motion.div>
        )}
      </AnimatePresence>
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
            ? "Creating..."
            : isParsingReceipt
            ? "Parsing..."
            : "Saving..."
        }
        onClick={handleSubmit}
        disabled={!lease || isLoading || isParsingReceipt}
      >
        Create Payment
      </Button>
    </>
  );

  return (
    <ModalShell
      isOpen={isOpen}
      onClose={onClose}
      title="Log New Payment"
      error={error}
      footerContent={footerButtons}
      maxWidth="max-w-xl"
    >
      {formContent}
    </ModalShell>
  );
};

export default NewPaymentModal;
