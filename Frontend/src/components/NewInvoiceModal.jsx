import React, { useState, useEffect, useRef, useMemo } from "react";
import { toast } from "react-toastify";
import {
  fetchProperties,
  fetchTenants,
  createInvoice,
} from "../utils/api";
import {
  ModalShell,
  Label,
  Input,
  Select,
  TextArea,
  Button,
} from "./ui/SharedModalComponents";
import { INVOICE_STATUSES } from "../utils/constants";

const NewInvoiceModal = ({ isOpen, onClose, onSuccess }) => {
  const initialFormData = {
    invoice_number: "",
    amount: "",
    description: "",
    issue_date: new Date().toISOString().split("T")[0],
    due_date: "",
    status: "Pending",
    property_id: "",
    property_name: "",
    tenant_id: "",
    tenant_name: "",
  };

  const [formData, setFormData] = useState(initialFormData);
  const [properties, setProperties] = useState([]);
  const [tenants, setTenants] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [dropdownOpen, setDropdownOpen] = useState("");
  const [filteredProperties, setFilteredProperties] = useState([]);
  const [filteredTenants, setFilteredTenants] = useState([]);

  const propertyDropdownRef = useRef(null);
  const tenantDropdownRef = useRef(null);

  useEffect(() => {
    const loadData = async () => {
      try {
        const [propertiesData, tenantsData] = await Promise.all([
          fetchProperties(),
          fetchTenants(),
        ]);
        setProperties(propertiesData || []);
        setTenants(tenantsData || []);
        setFilteredProperties(propertiesData || []);
        setFilteredTenants(tenantsData || []);
      } catch (err) {
        console.error("Failed to load data:", err);
        toast.error("Failed to load properties and tenants.");
      }
    };

    if (isOpen) {
      loadData();
      setFormData(initialFormData);
      setError(null);
      setDropdownOpen("");
      
      // Generate default invoice number with timestamp to reduce collision risk
      const now = new Date();
      const timestamp = now.getTime().toString().slice(-6); // Last 6 digits of timestamp
      const invoiceNumber = `INV-${now.getFullYear()}${(now.getMonth() + 1)
        .toString()
        .padStart(2, "0")}${now.getDate().toString().padStart(2, "0")}-${timestamp}`;
      
      setFormData(prev => ({
        ...prev,
        invoice_number: invoiceNumber,
      }));
    }
  }, [isOpen]);

  useEffect(() => {
    // Set default due date 30 days from issue date
    if (formData.issue_date && !formData.due_date) {
      const issueDate = new Date(formData.issue_date);
      const dueDate = new Date(issueDate);
      dueDate.setDate(dueDate.getDate() + 30);
      setFormData(prev => ({
        ...prev,
        due_date: dueDate.toISOString().split("T")[0],
      }));
    }
  }, [formData.issue_date, formData.due_date]);

  useEffect(() => {
    // Filter tenants by selected property
    if (formData.property_id) {
      const propertyTenants = tenants.filter(tenant => 
        tenant.property_units?.some(unit => 
          unit.property_id === parseInt(formData.property_id, 10)
        )
      );
      setFilteredTenants(propertyTenants);
      
      // Reset tenant selection if not in filtered list
      if (formData.tenant_id && !propertyTenants.some(t => t.id === parseInt(formData.tenant_id, 10))) {
        setFormData(prev => ({ ...prev, tenant_id: "", tenant_name: "" }));
      }
    } else {
      setFilteredTenants(tenants);
    }
  }, [formData.property_id, tenants]);

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

    document.addEventListener("mousedown", handleClickOutside);
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, [dropdownOpen]);

  // Memoize the property-filtered tenants to avoid recalculation on every render
  const propertyFilteredTenants = useMemo(() => {
    return formData.property_id 
      ? tenants.filter(tenant => 
          tenant.property_units?.some(unit => 
            unit.property_id === parseInt(formData.property_id, 10)
          )
        )
      : tenants;
  }, [formData.property_id, tenants]);

  const handleInputChange = (field, value) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
    setError(null);
  };

  const handlePropertySelect = (property) => {
    setFormData((prev) => ({
      ...prev,
      property_id: property.id,
      property_name: property.name,
      tenant_id: "", // Reset tenant selection
      tenant_name: "",
    }));
    setDropdownOpen("");
  };

  const handleTenantSelect = (tenant) => {
    setFormData((prev) => ({
      ...prev,
      tenant_id: tenant.id,
      tenant_name: tenant.full_name,
    }));
    setDropdownOpen("");
  };

  const handlePropertySearch = (searchTerm) => {
    const filtered = properties.filter((property) =>
      property.name.toLowerCase().includes(searchTerm.toLowerCase())
    );
    setFilteredProperties(filtered);
    setFormData((prev) => ({ ...prev, property_name: searchTerm }));
  };

  const handleTenantSearch = (searchTerm) => {
    const tenantsToFilter = propertyFilteredTenants;
      
    const filtered = tenantsToFilter.filter((tenant) =>
      tenant.full_name.toLowerCase().includes(searchTerm.toLowerCase())
    );
    setFilteredTenants(filtered);
    setFormData((prev) => ({ ...prev, tenant_name: searchTerm }));
  };

  const validateForm = () => {
    if (!formData.invoice_number?.trim()) {
      setError("Invoice number is required.");
      return false;
    }
    if (!formData.amount || parseFloat(formData.amount) <= 0) {
      setError("Amount must be greater than 0.");
      return false;
    }
    if (!formData.description?.trim()) {
      setError("Description is required.");
      return false;
    }
    if (!formData.issue_date) {
      setError("Issue date is required.");
      return false;
    }
    if (!formData.due_date) {
      setError("Due date is required.");
      return false;
    }
    if (new Date(formData.due_date) < new Date(formData.issue_date)) {
      setError("Due date cannot be earlier than issue date.");
      return false;
    }
    return true;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!validateForm()) return;

    setIsLoading(true);
    setError(null);

    try {
      const invoiceData = {
        invoice_number: formData.invoice_number.trim(),
        amount: parseFloat(formData.amount),
        description: formData.description.trim(),
        issue_date: formData.issue_date,
        due_date: formData.due_date,
        status: formData.status,
        property_id: formData.property_id ? parseInt(formData.property_id, 10) : null,
        tenant_id: formData.tenant_id ? parseInt(formData.tenant_id, 10) : null,
      };

      await createInvoice(invoiceData);
      
      onSuccess?.();
    } catch (err) {
      console.error("Failed to create invoice:", err);
      setError(
        err.message || "Failed to create invoice. Please try again."
      );
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <ModalShell
      isOpen={isOpen}
      onClose={onClose}
      title="Create New Invoice"
      maxWidth="max-w-2xl"
    >
      <form onSubmit={handleSubmit} className="space-y-5">
        {error && (
          <div className="bg-red-50 border border-red-200 text-red-600 px-4 py-3 rounded-md text-sm">
            {error}
          </div>
        )}

        {/* Invoice Number and Amount */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <Label required>Invoice Number</Label>
            <Input
              type="text"
              value={formData.invoice_number}
              onChange={(e) => handleInputChange("invoice_number", e.target.value)}
              placeholder="INV-2024-001"
              required
            />
          </div>
          <div>
            <Label required>Amount</Label>
            <Input
              type="number"
              step="0.01"
              min="0.01"
              value={formData.amount}
              onChange={(e) => handleInputChange("amount", e.target.value)}
              placeholder="0.00"
              required
            />
          </div>
        </div>

        {/* Description */}
        <div>
          <Label required>Description</Label>
          <TextArea
            value={formData.description}
            onChange={(e) => handleInputChange("description", e.target.value)}
            placeholder="Brief description of the invoice..."
            rows={3}
            required
          />
        </div>

        {/* Dates */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <Label required>Issue Date</Label>
            <Input
              type="date"
              value={formData.issue_date}
              onChange={(e) => handleInputChange("issue_date", e.target.value)}
              required
            />
          </div>
          <div>
            <Label required>Due Date</Label>
            <Input
              type="date"
              value={formData.due_date}
              onChange={(e) => handleInputChange("due_date", e.target.value)}
              required
            />
          </div>
        </div>

        {/* Status */}
        <div>
          <Label>Status</Label>
          <Select
            value={formData.status}
            onChange={(e) => handleInputChange("status", e.target.value)}
          >
            {INVOICE_STATUSES.map((status) => (
              <option key={status} value={status}>
                {status.charAt(0).toUpperCase() + status.slice(1).toLowerCase()}
              </option>
            ))}
          </Select>
        </div>

        {/* Property Selection */}
        <div className="relative" ref={propertyDropdownRef}>
          <Label>Property (Optional)</Label>
          <Input
            type="text"
            value={formData.property_name}
            onChange={(e) => {
              handlePropertySearch(e.target.value);
              if (!e.target.value) {
                setFormData(prev => ({ ...prev, property_id: "", property_name: "" }));
              }
            }}
            onFocus={() => setDropdownOpen("property")}
            placeholder="Search properties..."
          />
          {dropdownOpen === "property" && filteredProperties.length > 0 && (
            <div className="absolute z-10 w-full mt-1 bg-white border border-gray-300 rounded-md shadow-lg max-h-48 overflow-y-auto">
              {filteredProperties.map((property) => (
                <div
                  key={property.id}
                  className="px-4 py-2 hover:bg-gray-100 cursor-pointer"
                  onClick={() => handlePropertySelect(property)}
                >
                  <div className="font-medium">{property.name}</div>
                  {property.address && (
                    <div className="text-sm text-gray-600">{property.address}</div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Tenant Selection */}
        <div className="relative" ref={tenantDropdownRef}>
          <Label>Tenant (Optional)</Label>
          <Input
            type="text"
            value={formData.tenant_name}
            onChange={(e) => {
              handleTenantSearch(e.target.value);
              if (!e.target.value) {
                setFormData(prev => ({ ...prev, tenant_id: "", tenant_name: "" }));
              }
            }}
            onFocus={() => setDropdownOpen("tenant")}
            placeholder="Search tenants..."
          />
          {dropdownOpen === "tenant" && filteredTenants.length > 0 && (
            <div className="absolute z-10 w-full mt-1 bg-white border border-gray-300 rounded-md shadow-lg max-h-48 overflow-y-auto">
              {filteredTenants.map((tenant) => (
                <div
                  key={tenant.id}
                  className="px-4 py-2 hover:bg-gray-100 cursor-pointer"
                  onClick={() => handleTenantSelect(tenant)}
                >
                  <div className="font-medium">{tenant.full_name}</div>
                  {tenant.email && (
                    <div className="text-sm text-gray-600">{tenant.email}</div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Form Actions */}
        <div className="flex justify-end space-x-3 pt-4">
          <Button
            type="button"
            variant="secondary"
            onClick={onClose}
            disabled={isLoading}
          >
            Cancel
          </Button>
          <Button
            type="submit"
            variant="primary"
            disabled={isLoading}
            loading={isLoading}
          >
            Create Invoice
          </Button>
        </div>
      </form>
    </ModalShell>
  );
};

export default NewInvoiceModal;