import React, { useState, useEffect, useCallback } from "react";
import { createTenant, fetchProperties } from "../utils/api";
import { ModalShell, Label, Input, Button } from "./ui/SharedModalComponents";

const TenantModal = ({
  isOpen,
  onClose,
  onSave,
  source,
  tenant = {},
  propertyId = null,
  unitId = null,
  unitName = "",
}) => {
  const [formData, setFormData] = useState({
    first_name: "",
    last_name: "",
    phone: "",
    email: "",
    status: "active",
    current_property_id: propertyId || null,
    unit: unitName || "",
    unit_id: unitId || null,
  });

  const [properties, setProperties] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isLoadingProperties, setIsLoadingProperties] = useState(false);
  const [error, setError] = useState(null); // General error for ModalShell
  const [fieldErrors, setFieldErrors] = useState({});
  const [touched, setTouched] = useState({});

  const loadProperties = useCallback(async (signal) => {
    setIsLoadingProperties(true);
    try {
      const propertiesData = await fetchProperties({}, { signal });
      setProperties(propertiesData || []);
    } catch (err) {
      if (err.name !== "AbortError") {
        console.error("Failed to load properties:", err);
        // Don't show error to user as properties are optional
      }
    } finally {
      setIsLoadingProperties(false);
    }
  }, []);

  // Populate form when tenant data is provided
  useEffect(() => {
    if (isOpen) {
      // tenant prop check is now more robust inside
      let firstName = tenant?.first_name || "";
      let lastName = tenant?.last_name || "";

      if (tenant?.full_name && (!firstName || !lastName)) {
        const nameParts = tenant.full_name.split(" ");
        firstName = nameParts[0] || "";
        lastName = nameParts.slice(1).join(" ") || "";
      }

      setFormData({
        first_name: firstName,
        last_name: lastName,
        phone: tenant?.phone || "",
        email: tenant?.email || "",
        status: tenant?.status || "active",
        current_property_id: propertyId || tenant?.current_property_id || null,
        unit: unitName || tenant?.unit || "",
        unit_id: unitId || tenant?.unit_id || null,
      });

      setFieldErrors({});
      setError(null);
      setTouched({});
      
      const abortController = new AbortController();
      // Load properties when modal opens
      loadProperties(abortController.signal);

      return () => {
        abortController.abort();
      };
    }
  }, [isOpen, propertyId, unitId, unitName, tenant?.id, loadProperties]);
  
  const validateField = (name, value) => {
    switch (name) {
      case "first_name":
        if (!value || value.trim() === "") return "First name is required";
        break;
      case "last_name":
        if (!value || value.trim() === "") return "Last name is required";
        break;
      case "email":
        if (!value || value.trim() === "") return "Email is required";
        const emailRegex = /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/;
        if (!emailRegex.test(value.trim())) {
          return "Please enter a valid email address";
        }
        break;
      case "phone":
        if (!value || value.trim() === "") return "Phone number is required";
        const digitsOnly = value.replace(/[^0-9]/g, "");
        if (digitsOnly.length < 10 || digitsOnly.length > 15) {
          return "Phone number must contain 10-15 digits";
        }
        break;
      default:
        break;
    }
    return null;
  };

  const handleBlur = (e) => {
    const { name, value } = e.target;
    setTouched((prev) => ({
      ...prev,
      [name]: true,
    }));
    
    // Validate on blur
    const error = validateField(name, value);
    if (error) {
      setFieldErrors((prev) => ({ ...prev, [name]: error }));
    } else {
      setFieldErrors((prev) => {
        const updated = { ...prev };
        delete updated[name];
        return updated;
      });
    }
  };

  const handleChange = (e) => {
    const { name, value } = e.target;
    let finalValue = value;
    if (name === "current_property_id") {
      if (value) {
        const parsed = parseInt(value, 10);
        finalValue = isNaN(parsed) ? null : parsed;
      } else {
        finalValue = null;
      }
    }
    setFormData((prev) => ({ ...prev, [name]: finalValue }));
    
    // Clear error when user starts typing if field was touched
    if (touched[name]) {
      // Use finalValue for validation consistency, but validateField only handles text fields anyway
      const valueToValidate = name === "current_property_id" ? finalValue : value;
      const error = validateField(name, valueToValidate);
      if (error) {
        setFieldErrors((prev) => ({ ...prev, [name]: error }));
      } else {
        setFieldErrors((prev) => {
          const updated = { ...prev };
          delete updated[name];
          return updated;
        });
      }
    }
  };

  const validateForm = () => {
    let isValid = true;
    const newErrors = {};

    for (const fieldName of ["first_name", "last_name", "email", "phone"]) {
      const error = validateField(fieldName, formData[fieldName]);
      if (error) {
        newErrors[fieldName] = error;
        isValid = false;
      }
    }
    
    setFieldErrors(newErrors);
    if (!isValid) {
      setError("Please correct the highlighted fields.");
    } else {
      setError(null);
    }
    return isValid;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    // setError(null); // Handled by validateForm or API call
    // setFieldErrors({}); // Reset at start of validation

    if (!validateForm()) {
      return;
    }
    setIsLoading(true);
    try {
      const tenantToCreate = {
        ...formData,
        status: formData.status.charAt(0).toUpperCase() + formData.status.slice(1),
        current_property_id: formData.current_property_id || propertyId || null,
        unit: formData.unit || unitName || "",
        unit_id: formData.unit_id || unitId || null,
      };
      const response = await createTenant(tenantToCreate);
      if (onSave) {
        const tenantResponse = {
          ...response,
          unit: formData.unit || unitName || "",
          unit_id: formData.unit_id || unitId || null,
          current_property_id:
            formData.current_property_id || propertyId || null,
        };
        onSave(tenantResponse);
      }
      if (!source || source !== "importLeaseModal") {
        onClose(); // This will also reset form state via useEffect on isOpen
      }
    } catch (err) {
      console.error("Failed to create tenant:", err);
      let errorMessage = "Failed to create tenant. Please try again.";

      // Handle specific HTTP status codes
      if (err.status === 409) {
        errorMessage =
          err.data?.detail || "A tenant with this email already exists.";
        setFieldErrors((prev) => ({
          ...prev,
          email: "This email is already in use.",
        }));
        setTouched((prev) => ({ ...prev, email: true }));
      }
      // Handle structured validation errors from backend
      else if (err.data?.detail && Array.isArray(err.data.detail)) {
        const validationErrors = {};
        const generalErrors = [];
        
        err.data.detail.forEach((errorItem) => {
          if (errorItem.loc && errorItem.loc.length > 1) {
            const fieldName = errorItem.loc[errorItem.loc.length - 1];
            validationErrors[fieldName] = errorItem.msg;
          } else {
            generalErrors.push(errorItem.msg || errorItem);
          }
        });
        
        // Apply field-specific errors
        if (Object.keys(validationErrors).length > 0) {
          setFieldErrors((prev) => ({ ...prev, ...validationErrors }));
          errorMessage = "Please correct the validation errors below.";
        }
        
        // Show general errors if any
        if (generalErrors.length > 0) {
          errorMessage = generalErrors.join(". ");
        }
      } else if (err.message) {
        errorMessage = err.message;
      }
      
      setError(errorMessage);
    } finally {
      setIsLoading(false);
    }
  };

  const formContent = (
    <form id="tenant-form" onSubmit={handleSubmit} className="space-y-5">
      <div className="space-y-4">
        <div>
          <Label htmlFor="first_name" required>
            First Name
          </Label>
          <Input
            id="first_name"
            name="first_name"
            value={formData.first_name}
            onChange={handleChange}
            onBlur={handleBlur}
            placeholder="Enter first name"
            required
            className={
              fieldErrors.first_name && touched.first_name
                ? "border-red-500"
                : ""
            }
          />
          {fieldErrors.first_name && touched.first_name && (
            <p className="mt-1 text-sm text-red-600">
              {fieldErrors.first_name}
            </p>
          )}
        </div>

        <div>
          <Label htmlFor="last_name" required>
            Last Name
          </Label>
          <Input
            id="last_name"
            name="last_name"
            value={formData.last_name}
            onChange={handleChange}
            onBlur={handleBlur}
            placeholder="Enter last name"
            required
            className={
              fieldErrors.last_name && touched.last_name ? "border-red-500" : ""
            }
          />
          {fieldErrors.last_name && touched.last_name && (
            <p className="mt-1 text-sm text-red-600">{fieldErrors.last_name}</p>
          )}
        </div>

        <div>
          <Label htmlFor="phone" required>
            Phone Number
          </Label>
          <Input
            id="phone"
            name="phone"
            type="tel"
            value={formData.phone}
            onChange={handleChange}
            onBlur={handleBlur}
            placeholder="Enter phone number"
            required
            className={
              fieldErrors.phone && touched.phone ? "border-red-500" : ""
            }
          />
          {fieldErrors.phone && touched.phone && (
            <p className="mt-1 text-sm text-red-600">{fieldErrors.phone}</p>
          )}
        </div>

        <div>
          <Label htmlFor="email" required>
            Email
          </Label>
          <Input
            id="email"
            name="email"
            type="email"
            value={formData.email}
            onChange={handleChange}
            onBlur={handleBlur}
            placeholder="Enter email"
            required
            className={
              fieldErrors.email && touched.email ? "border-red-500" : ""
            }
          />
          {fieldErrors.email && touched.email && (
            <p className="mt-1 text-sm text-red-600">{fieldErrors.email}</p>
          )}
        </div>

        {/* Show property dropdown only when not already assigned to a property */}
        {!propertyId && (
          <div>
            <Label htmlFor="current_property_id">
              Assign to Property (Optional)
            </Label>
            <select
              id="current_property_id"
              name="current_property_id"
              value={formData.current_property_id || ""}
              onChange={handleChange}
              disabled={isLoadingProperties}
              className="w-full px-3 py-2 text-gray-900 bg-white border border-gray-300 rounded-md shadow-sm focus:ring-1 focus:ring-blue-500 focus:border-blue-500 focus:outline-none transition-all duration-200 disabled:bg-gray-100 disabled:cursor-not-allowed"
            >
              {isLoadingProperties ? (
                <option>Loading properties...</option>
              ) : (
                <>
                  <option value="">Do not assign to a property</option>
                  {properties.map((property) => (
                    <option key={property.id} value={property.id}>
                      {property.name}
                    </option>
                  ))}
                </>
              )}
            </select>
          </div>
        )}
      </div>

      <div className="mt-2 mb-4 text-sm text-gray-500">
        <span className="text-red-600 font-bold">*</span> Required fields
      </div>
      {/* Submit button is now part of footerContent */}
    </form>
  );

  const footer = (
    <>
      <Button type="button" variant="secondary" onClick={onClose}>
        Cancel
      </Button>
      <Button
        type="submit"
        form="tenant-form"
        variant="primary"
        isLoading={isLoading}
        loadingText="Creating..."
        disabled={isLoading}
      >
        Save Tenant
      </Button>
    </>
  );

  return (
    <ModalShell
      isOpen={isOpen}
      onClose={onClose}
      title="Add New Tenant"
      footerContent={footer}
      error={error} // Pass general error to ModalShell
    >
      {/* AnimatePresence for field errors can be kept if needed, or remove if ErrorMessage in ModalShell is sufficient */}
      {/* <AnimatePresence>
         {error && !Object.keys(fieldErrors).length && <ErrorMessage message={error} />}
      </AnimatePresence> */}
      {formContent}
    </ModalShell>
  );
};

export default TenantModal;
