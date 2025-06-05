import React, { useState, useEffect, useRef } from "react";
import { createTenant } from "../utils/api";
import { AnimatePresence } from "framer-motion"; // motion is now in ModalShell
import {
  ModalShell,
  Label,
  Input,
  Button,
  ErrorMessage,
} from "./ui/SharedModalComponents";

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

  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null); // General error for ModalShell
  const [fieldErrors, setFieldErrors] = useState({});
  const [touched, setTouched] = useState({});
  // const [submitAttempted, setSubmitAttempted] = useState(false); // Can be inferred from touched object keys

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
      // setSubmitAttempted(false);
    }
  }, [isOpen, propertyId, unitId, unitName, tenant]); // tenant itself is a dependency

  const handleBlur = (e) => {
    const { name } = e.target;
    setTouched((prev) => ({
      ...prev,
      [name]: true,
    }));
    // Optional: validate on blur
    // validateField(name, formData[name]);
  };

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
    if (fieldErrors[name]) {
      setFieldErrors((prev) => {
        const updated = { ...prev };
        delete updated[name];
        return updated;
      });
    }
    // No need to set touched on change, blur will handle it.
  };

  const validateForm = () => {
    const newErrors = {};
    let isValid = true;
    const fieldsToTouch = {};

    if (!formData.first_name || formData.first_name.trim() === "") {
      newErrors.first_name = "First name is required";
      isValid = false;
      fieldsToTouch.first_name = true;
    }
    if (!formData.last_name || formData.last_name.trim() === "") {
      newErrors.last_name = "Last name is required";
      isValid = false;
      fieldsToTouch.last_name = true;
    }
    if (!formData.email || formData.email.trim() === "") {
      newErrors.email = "Email is required";
      isValid = false;
      fieldsToTouch.email = true;
    } else {
      const emailRegex = /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/;
      if (!emailRegex.test(formData.email.trim())) {
        newErrors.email = "Please enter a valid email address";
        isValid = false;
        fieldsToTouch.email = true;
      }
    }
    if (!formData.phone || formData.phone.trim() === "") {
      newErrors.phone = "Phone number is required";
      isValid = false;
      fieldsToTouch.phone = true;
    } else if (!/^[0-9]{10,15}$/.test(formData.phone.replace(/[^0-9]/g, ""))) {
      newErrors.phone =
        "Invalid phone number format (must contain 10-15 digits)";
      isValid = false;
      fieldsToTouch.phone = true;
    }

    setFieldErrors(newErrors);
    setTouched((prev) => ({ ...prev, ...fieldsToTouch })); // Merge with existing touched fields
    // setSubmitAttempted(true); // Can be inferred if newErrors is not empty after this

    if (!isValid) {
      setError("Please correct the highlighted fields.");
    } else {
      setError(null); // Clear general error if form is valid now
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
      if (err.data?.detail) {
        if (Array.isArray(err.data.detail)) {
          const validationErrors = {};
          const backendErrorMessages = [];
          err.data.detail.forEach((errorItem) => {
            if (errorItem.loc && errorItem.loc.length > 1) {
              validationErrors[errorItem.loc[1]] = errorItem.msg;
            } else {
              backendErrorMessages.push(errorItem.msg);
            }
          });
          setFieldErrors((prev) => ({ ...prev, ...validationErrors }));
          if (backendErrorMessages.length > 0) {
            errorMessage = backendErrorMessages.join(" ");
          } else if (Object.keys(validationErrors).length > 0) {
            errorMessage = "Please correct the validation errors below.";
          }
        } else if (typeof err.data.detail === "string") {
          errorMessage = err.data.detail;
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
