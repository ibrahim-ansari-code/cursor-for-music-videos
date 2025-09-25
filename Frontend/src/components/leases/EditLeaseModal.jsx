import React, { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { toast } from "react-toastify";
import {
  fetchProperties,
  fetchTenants,
  updateLease,
  fetchUnitById,
} from "../../utils/api";
import {
  Label,
  Input,
  TextArea,
  Button,
  FormSection,
} from "../ui/SharedModalComponents";

const MIN_RENT_DUE_DAY = 1;
const MAX_RENT_DUE_DAY = 28;

const EditLeaseModal = ({ isOpen, onClose, lease, onLeaseUpdated }) => {
  const [formData, setFormData] = useState({});
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [propertyDetails, setPropertyDetails] = useState(null);
  const [unitDetails, setUnitDetails] = useState(null);
  const [tenantDetails, setTenantDetails] = useState(null);

  useEffect(() => {
    if (lease) {
      // Format dates for input[type=\"date\"]
      const formattedLease = {
        ...lease,
        start_date: lease.start_date
          ? new Date(lease.start_date).toISOString().split("T")[0]
          : "",
        end_date: lease.end_date
          ? new Date(lease.end_date).toISOString().split("T")[0]
          : "",
        monthly_rent: lease.monthly_rent || "",
        security_deposit: lease.security_deposit || "",
        rent_due_day: lease.rent_due_day || "",
        late_fee_amount: lease.late_fee_amount || "",
        late_fee_after_days: lease.late_fee_after_days || "",
        special_terms: lease.special_terms || "",
      };
      setFormData(formattedLease);

      // Fetch related details for display in parallel
      const propertyPromise = lease.property_id
        ? fetchProperties({ id: lease.property_id })
        : Promise.resolve(null);
      const unitPromise = lease.unit_id && !lease.unit
        ? fetchUnitById(lease.unit_id)
        : Promise.resolve(lease.unit || null);
      const tenantPromise = lease.tenant_id
        ? fetchTenants({ id: lease.tenant_id })
        : Promise.resolve(null);

      let isMounted = true;

      Promise.all([propertyPromise, unitPromise, tenantPromise])
        .then(([props, unit, tenants]) => {
          if (!isMounted) return; // Prevent state update on unmounted component
          // Property
          if (props && props.length > 0) setPropertyDetails(props[0]);
          else if (lease.property) setPropertyDetails(lease.property);
          else setPropertyDetails(null);

          // Unit
          if (unit?.name) setUnitDetails(unit);
          else if (lease.unit) setUnitDetails(lease.unit);
          else setUnitDetails({ name: "N/A" });

          // Tenant
          if (tenants && tenants.length > 0) setTenantDetails(tenants[0]);
          else if (lease.tenant) setTenantDetails(lease.tenant);
          else setTenantDetails(null);
        })
        .catch((err) => {
          console.error("Failed to fetch lease details in parallel", err);
          // Fallbacks
          if (lease.property) setPropertyDetails(lease.property);
          if (lease.unit) setUnitDetails(lease.unit);
          if (lease.tenant) setTenantDetails(lease.tenant);
        });

      return () => {
        isMounted = false; // Cleanup function to set the flag
      };
    }
  }, [lease]);

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target;
  
    setFormData((prev) => {
      let processedValue = value;
      if (type === "checkbox") {
        processedValue = checked;
      }
      // For number inputs, store the raw string value directly
      // Parsing will be done only during form submission
      return { ...prev, [name]: processedValue };
    });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsLoading(true);
    setError(null);

    // Validate rent_due_day is within allowed range
    const rentDueDay = Number.parseInt(formData.rent_due_day, 10);
    if (formData.rent_due_day && (isNaN(rentDueDay) || rentDueDay < MIN_RENT_DUE_DAY || rentDueDay > MAX_RENT_DUE_DAY)) {
      setError(`Rent due day must be between ${MIN_RENT_DUE_DAY} and ${MAX_RENT_DUE_DAY}.`);
      setIsLoading(false);
      return;
    }

    const parseFloatOrNull = (value) => {
      const parsed = Number.parseFloat(value);
      return isNaN(parsed) ? null : parsed;
    };
    
    const parseIntOrNull = (value) => {
      const parsed = Number.parseInt(value, 10);
      return isNaN(parsed) ? null : parsed;
    };

    const updateData = {
      start_date: formData.start_date || null,
      end_date: formData.end_date || null,
      monthly_rent: parseFloatOrNull(formData.monthly_rent),
      security_deposit: parseFloatOrNull(formData.security_deposit),
      rent_due_day: rentDueDay || null,
      late_fee_amount: parseFloatOrNull(formData.late_fee_amount),
      late_fee_after_days: parseIntOrNull(formData.late_fee_after_days),
      special_terms: formData.special_terms || null,
    };

    // Filter out null values explicitly if backend expects only provided fields
    // For now, sending null for empty/cleared fields is fine with `exclude_unset=True` on backend.

    try {
      const updatedLease = await updateLease(lease.id, updateData);
      onClose();
      // Call onLeaseUpdated after closing to avoid race conditions
      try {
        onLeaseUpdated(updatedLease);
      } catch (callbackError) {
        console.error("Error in onLeaseUpdated callback:", callbackError);
        // Optionally, inform the user that the list might not be up-to-date
        toast.error("Could not refresh the lease list automatically.");
      }
    } catch (err) {
      setError(err.message || "Failed to update lease. Please try again.");
      console.error("Update lease error:", err);
    } finally {
      setIsLoading(false);
    }
  };

  const modalVariants = {
    hidden: { opacity: 0, scale: 0.95 },
    visible: {
      opacity: 1,
      scale: 1,
      transition: { type: "spring", stiffness: 300, damping: 30 },
    },
    exit: { opacity: 0, scale: 0.95, transition: { duration: 0.15 } },
  };

  if (!isOpen) return null;

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
              className="fixed inset-0 bg-black bg-opacity-50 backdrop-blur-sm overflow-y-auto h-full w-full z-[9999] flex items-center justify-center p-4"
      onClick={onClose} // Close if backdrop is clicked
    >
      <motion.div
        variants={modalVariants}
        initial="hidden"
        animate="visible"
        exit="exit"
        className="relative w-full max-w-2xl bg-white dark:bg-gray-800 rounded-lg shadow-xl overflow-hidden"
        onClick={(e) => e.stopPropagation()} // Prevent close when clicking inside modal
      >
        <div className="px-6 py-4 bg-gray-50 dark:bg-gray-700 border-b border-gray-200 dark:border-gray-600 flex justify-between items-center">
          <h2 className="text-xl font-semibold text-gray-800 dark:text-gray-100">Edit Lease</h2>
          <button
            type="button"
            onClick={onClose}
            className="text-gray-400 dark:text-gray-500 hover:text-gray-600 dark:hover:text-gray-300 p-1 rounded-full focus:outline-none focus:ring-2 focus:ring-gray-400 dark:focus:ring-gray-500"
            aria-label="Close modal"
          >
            <svg
              className="h-6 w-6"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              aria-hidden="true"
            >
              <title>Close modal</title>
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M6 18L18 6M6 6l12 12"
              />
            </svg>
          </button>
        </div>

        <form onSubmit={handleSubmit}>
          <div className="p-6 space-y-2 max-h-[calc(100vh-15rem)] overflow-y-auto bg-white dark:bg-gray-800">
            <AnimatePresence>
              {error && (
                <motion.div
                  initial={{ opacity: 0, y: -10 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0 }}
                  className="mb-4 p-3 bg-red-100 dark:bg-red-900/20 border border-red-300 dark:border-red-700 text-red-700 dark:text-red-400 rounded-md text-sm"
                >
                  {error}
                </motion.div>
              )}
            </AnimatePresence>

            <FormSection title="Property & Tenant (Read-only)">
              <div className="sm:col-span-3">
                <Label htmlFor="property_name">Property</Label>
                <Input
                  name="property_name"
                  value={
                    propertyDetails?.name ||
                    lease?.property?.name ||
                    "Loading..."
                  }
                  readOnly
                />
              </div>
              <div className="sm:col-span-3">
                <Label htmlFor="unit_name">Unit</Label>
                <Input
                  name="unit_name"
                  value={unitDetails?.name || lease?.unit?.name || "N/A"}
                  readOnly
                />
              </div>
              <div className="sm:col-span-6">
                <Label htmlFor="tenant_name">Tenant</Label>
                <Input
                  name="tenant_name"
                  value={
                    tenantDetails?.full_name ||
                    tenantDetails?.name ||
                    lease?.tenant?.full_name ||
                    lease?.tenant?.name ||
                    "Loading..."
                  }
                  readOnly
                />
              </div>
            </FormSection>

            <FormSection title="Lease Terms">
              <div className="sm:col-span-3">
                <Label htmlFor="start_date" required>
                  Start Date
                </Label>
                <Input
                  name="start_date"
                  type="date"
                  value={formData.start_date}
                  onChange={handleChange}
                  required
                />
              </div>
              <div className="sm:col-span-3">
                <Label htmlFor="end_date" required>
                  End Date
                </Label>
                <Input
                  name="end_date"
                  type="date"
                  value={formData.end_date}
                  onChange={handleChange}
                  required
                />
              </div>
              <div className="sm:col-span-3">
                <Label htmlFor="monthly_rent" required>
                  Monthly Rent ($)
                </Label>
                <Input
                  name="monthly_rent"
                  type="number"
                  value={formData.monthly_rent}
                  onChange={handleChange}
                  required
                  placeholder="e.g., 1500.00"
                />
              </div>
              <div className="sm:col-span-3">
                <Label htmlFor="security_deposit">Security Deposit ($)</Label>
                <Input
                  name="security_deposit"
                  type="number"
                  value={formData.security_deposit}
                  onChange={handleChange}
                  placeholder="e.g., 1500.00"
                />
              </div>
            </FormSection>

            <FormSection title="Rent Collection & Fees">
              <div className="sm:col-span-2">
                <Label htmlFor="rent_due_day">Rent Due Day (1-28)</Label>
                <Input
                  name="rent_due_day"
                  type="number"
                  value={formData.rent_due_day}
                  onChange={handleChange}
                  placeholder="e.g., 1"
                  min={MIN_RENT_DUE_DAY}
                  max={MAX_RENT_DUE_DAY}
                />
              </div>
              <div className="sm:col-span-2">
                <Label htmlFor="late_fee_amount">Late Fee Amount ($)</Label>
                <Input
                  name="late_fee_amount"
                  type="number"
                  value={formData.late_fee_amount}
                  onChange={handleChange}
                  placeholder="e.g., 50.00"
                />
              </div>
              <div className="sm:col-span-2">
                <Label htmlFor="late_fee_after_days">
                  Late Fee After (Days)
                </Label>
                <Input
                  name="late_fee_after_days"
                  type="number"
                  value={formData.late_fee_after_days}
                  onChange={handleChange}
                  placeholder="e.g., 5"
                />
              </div>
            </FormSection>

            <FormSection title="Additional Information">
              <div className="sm:col-span-6">
                <Label htmlFor="special_terms">Special Terms / Notes</Label>
                <TextArea
                  name="special_terms"
                  value={formData.special_terms}
                  onChange={handleChange}
                  placeholder="Enter any special terms or notes for this lease..."
                />
              </div>
            </FormSection>
          </div>

          <div className="px-6 py-4 bg-gray-50 dark:bg-gray-700 border-t border-gray-200 dark:border-gray-600 flex justify-end space-x-3">
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
              isLoading={isLoading}
              loadingText="Saving..."
            >
              Save Changes
            </Button>
          </div>
        </form>
      </motion.div>
    </motion.div>
  );
};

export default EditLeaseModal;
