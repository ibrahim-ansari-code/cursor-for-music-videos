import React, { useState, useEffect } from "react";
import {
  submitLease,
  fetchProperties,
  fetchPropertyUnits,
  fetchLeases,
  createLease,
} from "../utils/api";
import { motion, AnimatePresence } from "framer-motion"; // Add framer-motion for animations
import {
  Label,
  Input,
  Select,
  Button,
  ErrorMessage,
  FormSection,
} from "./ui/SharedModalComponents"; // Import all required shared components

const ConfirmLeaseModal = ({
  isOpen,
  onClose,
  leaseData,
  tenant,
  onSubmit,
  availableUnits: initialAvailableUnits = [],
}) => {
  const [formData, setFormData] = useState({
    property_id: "",
    unit_id: "",
    unit: "",
    start_date: "",
    end_date: "",
    monthly_rent: "",
    security_deposit: "",
    tenant_id: "",
    rent_due_day: 1,
    late_fee_amount: null,
    late_fee_after_days: null,
    special_terms: null,
  });
  const [properties, setProperties] = useState([]);
  const [fieldErrors, setFieldErrors] = useState({});
  const [isLoading, setIsLoading] = useState(false);
  const [isLoadingProperties, setIsLoadingProperties] = useState(false);
  const [error, setError] = useState(null);
  const [formSubmitted, setFormSubmitted] = useState(false);
  const [selectedProperty, setSelectedProperty] = useState(null);
  const [isUnitEditable, setIsUnitEditable] = useState(true);
  const [allUnitsForProperty, setAllUnitsForProperty] = useState(
    initialAvailableUnits || []
  );
  const [filteredAvailableUnits, setFilteredAvailableUnits] = useState([]);
  const [isLoadingUnits, setIsLoadingUnits] = useState(false);
  const [isLoadingLeases, setIsLoadingLeases] = useState(false);
  const [selectedUnit, setSelectedUnit] = useState(leaseData.unit || "");
  const [selectedUnitId, setSelectedUnitId] = useState(null);
  const [showLeasePreview, setShowLeasePreview] = useState(false);

  // Initialize allUnitsForProperty from prop
  useEffect(() => {
    if (initialAvailableUnits && initialAvailableUnits.length > 0) {
      setAllUnitsForProperty(initialAvailableUnits);
      console.log("Using provided available units:", initialAvailableUnits);
      // Filter units initially if prop is provided
      filterUnits(initialAvailableUnits, formData.property_id);
    }
  }, [initialAvailableUnits]);

  // Load properties on component mount
  useEffect(() => {
    const loadProperties = async () => {
      setIsLoadingProperties(true);
      try {
        const data = await fetchProperties();
        setProperties(data);

        if (leaseData?.property_id) {
          const propertyId = Number.parseInt(leaseData.property_id, 10);
          const property = data.find((p) => p.id === propertyId);
          if (property) {
            setSelectedProperty(property);
          }
        }
      } catch (error) {
        console.error("Failed to fetch properties:", error);
        setError("Failed to load properties. Please try again.");
      } finally {
        setIsLoadingProperties(false);
      }
    };

    if (isOpen) {
      loadProperties();
    }
  }, [isOpen, leaseData?.property_id]); // Removed isUnitEditable dependency

  // Helper function to load units and active leases, then filter
  const loadUnitsAndFilter = async (propertyId) => {
    if (!propertyId) {
      setAllUnitsForProperty([]);
      setFilteredAvailableUnits([]);
      return;
    }
    setIsLoadingUnits(true);
    setIsLoadingLeases(true);
    try {
      // Fetch all units for the property
      const unitsData = await fetchPropertyUnits(propertyId);
      const allUnits = unitsData || [];
      setAllUnitsForProperty(allUnits);
      console.log("All units loaded:", allUnits);

      // Fetch active leases for the property to filter units
      await filterUnits(allUnits, propertyId);
    } catch (err) {
      console.error(
        "Failed to load units/leases for property:",
        propertyId,
        err
      );
      setError("Failed to load unit information for the selected property.");
      setAllUnitsForProperty([]);
      setFilteredAvailableUnits([]);
    } finally {
      setIsLoadingUnits(false);
      setIsLoadingLeases(false);
    }
  };

  // Function to filter units based on active leases
  const filterUnits = async (unitsToFilter, propertyId) => {
    if (!propertyId) {
      setFilteredAvailableUnits(unitsToFilter); // No property, show all fetched/provided units
      return;
    }
    setIsLoadingLeases(true);
    try {
      const activeLeases = await fetchLeases({
        property_id: propertyId,
        status: "ACTIVE",
      });
      const activeLeaseUnitIds = new Set(
        activeLeases.map((lease) => lease.unit_id).filter((id) => id != null)
      );
      console.log("Active lease unit IDs:", activeLeaseUnitIds);

      const filteredUnits = unitsToFilter.filter(
        (unit) => !activeLeaseUnitIds.has(unit.id)
      );
      setFilteredAvailableUnits(filteredUnits);
      console.log("Filtered available units:", filteredUnits);
    } catch (leaseError) {
      console.error("Failed to fetch active leases for filtering:", leaseError);
      setError("Failed to determine unit availability. Displaying all units.");
      setFilteredAvailableUnits(unitsToFilter); // Fallback to showing all units on error
    } finally {
      setIsLoadingLeases(false);
    }
  };

  // Populate form data and check unit editability - consolidated effect
  useEffect(() => {
    if (leaseData && tenant && properties.length > 0) {
      const wasTenantPreAssigned = tenant.current_property_id && tenant.unit_id;
      const shouldLockFields = wasTenantPreAssigned;
      setIsUnitEditable(!shouldLockFields);

      const propertyIdToUse = shouldLockFields
        ? tenant.current_property_id
        : leaseData.property_id || tenant.current_property_id || "";

      const unitIdToUse = shouldLockFields ? tenant.unit_id : "";
      const unitNameToUse = shouldLockFields
        ? tenant.unit?.name || tenant.unit || ""
        : leaseData.unit || "";

      setFormData((prev) => ({
        ...prev,
        tenant_id: tenant.id,
        property_id: propertyIdToUse,
        unit_id: unitIdToUse,
        unit: unitNameToUse,
        start_date: leaseData.start_date || "",
        end_date: leaseData.end_date || "",
        monthly_rent: leaseData.monthly_rent || "",
        security_deposit: leaseData.security_deposit || "0",
        rent_due_day: leaseData.rent_due_day || 1,
        late_fee_amount: leaseData.late_fee_amount || null,
        late_fee_after_days: leaseData.late_fee_after_days || null,
        special_terms: leaseData.special_terms || null,
      }));

      if (propertyIdToUse) {
        const property = properties.find(
          (p) => p.id === Number.parseInt(propertyIdToUse, 10)
        );
        setSelectedProperty(property);

        // Only load and filter units if not locked
        if (!shouldLockFields) {
          loadUnitsAndFilter(propertyIdToUse);
        }
      }
    }
  }, [leaseData, tenant, properties]); // Simplified dependencies

  // Separate effect for unit matching when filtered units are available
  useEffect(() => {
    if (
      isUnitEditable &&
      formData.unit &&
      !formData.unit_id &&
      filteredAvailableUnits.length > 0
    ) {
      console.log(
        `Attempting to match unit name '${formData.unit}' to available units.`
      );
      const matchingUnit = filteredAvailableUnits.find(
        (unit) =>
          unit.name &&
          formData.unit &&
          unit.name.toLowerCase() === formData.unit.toLowerCase()
      );
      if (matchingUnit) {
        console.log(`Auto-selected unit ID ${matchingUnit.id} based on name.`);
        setFormData((prev) => ({ ...prev, unit_id: matchingUnit.id }));
      }
    }
  }, [isUnitEditable, formData.unit, formData.unit_id, filteredAvailableUnits]); // Added formData.unit_id to prevent continuous updates

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({
      ...prev,
      [name]: value,
    }));

    if (name === "unit_id" && value) {
      // Match against allUnitsForProperty to get the name correctly even if filtered out
      const selectedUnit = allUnitsForProperty.find(
        (u) => u.id === Number.parseInt(value, 10)
      );
      if (selectedUnit) {
        setFormData((prev) => ({ ...prev, unit: selectedUnit.name }));
      }
    }

    if (fieldErrors[name]) {
      setFieldErrors((prev) => {
        const updated = { ...prev };
        delete updated[name];
        return updated;
      });
    }
  };

  const handlePropertyChange = (e) => {
    const propertyId = e.target.value;
    setFormData((prev) => ({
      ...prev,
      property_id: propertyId,
      unit_id: "",
      unit: "",
    }));

    setAllUnitsForProperty([]); // Clear previous units
    setFilteredAvailableUnits([]); // Clear filtered units

    if (fieldErrors.property_id) {
      setFieldErrors((prev) => {
        const updated = { ...prev };
        delete updated.property_id;
        return updated;
      });
    }

    const property = properties.find(
      (p) => p.id === Number.parseInt(propertyId, 10)
    );
    setSelectedProperty(property);

    if (isUnitEditable && propertyId) {
      loadUnitsAndFilter(propertyId); // Load and filter units for new property
    }
  };

  const validateForm = () => {
    const errors = {};

    // Required fields
    if (!formData.property_id) errors.property_id = "Property is required";
    if (!formData.start_date)
      errors.start_date = "Lease Start Date is required";
    if (!formData.end_date) errors.end_date = "Lease End Date is required";
    if (!formData.monthly_rent)
      errors.monthly_rent = "Monthly Rent is required";
    if (
      formData.security_deposit === undefined ||
      formData.security_deposit === ""
    ) {
      errors.security_deposit = "Security Deposit is required";
    }
    if (!formData.tenant_id) errors.tenant_id = "Tenant is required";

    // Require unit_id if editable, otherwise unit text must exist
    if (isUnitEditable) {
      // Use filteredAvailableUnits for validation if editable
      if (!formData.unit_id) {
        errors.unit_id = "Please select an available unit";
      } else if (
        !filteredAvailableUnits.some(
          (u) => u.id === Number.parseInt(formData.unit_id, 10)
        )
      ) {
        errors.unit_id = "Selected unit is not available (already leased)";
      }
    } else {
      if (!formData.unit) {
        errors.unit = "Unit information is required"; // Should not happen if locked correctly
      }
    }

    // Dates validation
    if (formData.start_date && formData.end_date) {
      const start = new Date(formData.start_date);
      const end = new Date(formData.end_date);
      if (start > end) {
        errors.end_date = "End date must be after start date";
      }
    }

    return errors;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setFormSubmitted(true);

    // Validate form
    const validationErrors = validateForm();
    if (Object.keys(validationErrors).length > 0) {
      setFieldErrors(validationErrors);
      setError("Please correct the validation errors below.");
      return;
    }

    setIsLoading(true);
    setError(null);
    setFieldErrors({});

    try {
      // Format data for API, removing renewable fields
      const leaseSubmitData = {
        property_id: Number.parseInt(formData.property_id, 10),
        unit_id: formData.unit_id
          ? Number.parseInt(formData.unit_id, 10)
          : null,
        // unit name is not needed if unit_id is provided, backend should handle linking
        start_date: formData.start_date,
        end_date: formData.end_date,
        monthly_rent: Number.parseFloat(formData.monthly_rent),
        security_deposit: Number.parseFloat(formData.security_deposit),
        tenant_id: Number.parseInt(formData.tenant_id, 10),
        rent_due_day: Number.parseInt(formData.rent_due_day || 1, 10),
        late_fee_amount: formData.late_fee_amount
          ? Number.parseFloat(formData.late_fee_amount)
          : null,
        late_fee_after_days: formData.late_fee_after_days
          ? Number.parseInt(formData.late_fee_after_days, 10)
          : null,
        special_terms: formData.special_terms,
        status: "ACTIVE", // Default status for new lease
      };

      // Remove null values if backend prefers absence over null
      Object.keys(leaseSubmitData).forEach((key) => {
        if (
          leaseSubmitData[key] === null ||
          leaseSubmitData[key] === undefined
        ) {
          // delete leaseSubmitData[key]; // Option 1: delete null keys
        }
      });

      console.log("Submitting lease data:", leaseSubmitData);

      // Submit to backend
      const response = await submitLease(leaseSubmitData);
      console.log("Lease created successfully:", response);

      if (onSubmit) {
        onSubmit(response);
      }

      onClose();
    } catch (err) {
      console.error("Failed to create lease:", err);
      setError(err.message || "Failed to create lease. Please try again.");
    } finally {
      setIsLoading(false);
    }
  };

  const handleCreateLease = async () => {
    try {
      setIsLoading(true);
      setError(null);

      // Validate form first
      const validationErrors = validateForm();
      if (Object.keys(validationErrors).length > 0) {
        setFieldErrors(validationErrors);
        setError("Please correct the validation errors below.");
        return;
      }

      // Prepare lease data using form data instead of original leaseData
      const leaseSubmitData = {
        property_id: Number.parseInt(formData.property_id, 10),
        unit_id: formData.unit_id
          ? Number.parseInt(formData.unit_id, 10)
          : null,
        tenant_id: Number.parseInt(formData.tenant_id, 10),
        start_date: formData.start_date,
        end_date: formData.end_date,
        monthly_rent: Number.parseFloat(formData.monthly_rent),
        security_deposit: Number.parseFloat(formData.security_deposit),
        rent_due_day: Number.parseInt(formData.rent_due_day || 1, 10),
        late_fee_amount: formData.late_fee_amount
          ? Number.parseFloat(formData.late_fee_amount)
          : null,
        late_fee_after_days: formData.late_fee_after_days
          ? Number.parseInt(formData.late_fee_after_days, 10)
          : null,
        special_terms: formData.special_terms || null,
        status: "ACTIVE", // Create as active lease
        file_url: leaseData.file_url, // Include the document URL from original leaseData
      };

      // Log if we have a document URL to include
      if (leaseData.file_url) {
        console.log(
          `Including document URL in lease creation: ${leaseData.file_url}`
        );
      }

      console.log("Creating lease with data:", leaseSubmitData);

      // Call API to create the lease (this will automatically activate it)
      const createdLease = await createLease(leaseSubmitData);
      console.log("Lease created successfully:", createdLease);

      // Call the onSubmit callback with the created lease
      onSubmit(createdLease);
    } catch (error) {
      console.error("Error creating lease:", error);
      setError(error.message || "Failed to create lease. Please try again.");
    } finally {
      setIsLoading(false);
    }
  };

  // Attempt to find the unit ID based on name if we have a unit name
  useEffect(() => {
    if (
      leaseData.unit &&
      initialAvailableUnits &&
      initialAvailableUnits.length > 0
    ) {
      const matchedUnit = initialAvailableUnits.find(
        (unit) => unit.name.toLowerCase() === leaseData.unit.toLowerCase()
      );
      if (matchedUnit) {
        setSelectedUnitId(matchedUnit.id);
        console.log(
          `Found matching unit ID ${matchedUnit.id} for unit name ${leaseData.unit}`
        );
      }
    }
  }, [leaseData.unit, initialAvailableUnits]);

  const handleUnitChange = (e) => {
    const unitId = Number.parseInt(e.target.value, 10);
    setSelectedUnitId(unitId);

    if (unitId) {
      const unit = initialAvailableUnits.find((u) => u.id === unitId);
      if (unit) {
        setSelectedUnit(unit.name);
      }
    } else {
      setSelectedUnit("");
    }
  };

  if (!isOpen) return null;

  // Modal animations
  const overlayVariants = {
    hidden: { opacity: 0 },
    visible: { opacity: 1, transition: { duration: 0.2 } },
  };

  const modalVariants = {
    hidden: { opacity: 0, scale: 0.95, y: -10 },
    visible: {
      opacity: 1,
      scale: 1,
      y: 0,
      transition: {
        type: "spring",
        stiffness: 300,
        damping: 30,
        duration: 0.3,
      },
    },
    exit: {
      opacity: 0,
      scale: 0.95,
      y: 10,
      transition: { duration: 0.2 },
    },
  };

  const renderPreviewContent = (url) => {
    if (!url) return null;
    const lowerUrl = url.toLowerCase();
    if (
      lowerUrl.endsWith(".png") ||
      lowerUrl.endsWith(".jpg") ||
      lowerUrl.endsWith(".jpeg") ||
      lowerUrl.endsWith(".gif") ||
      lowerUrl.endsWith(".webp") ||
      lowerUrl.endsWith(".bmp") ||
      lowerUrl.endsWith(".svg")
    ) {
      return (
        <img
          src={url}
          alt="Lease Document Preview"
          className="w-full h-full object-contain p-1"
        />
      );
    } else if (lowerUrl.endsWith(".pdf")) {
      const pdfDisplayUrl = `${url}#view=FitH`;
      return (
        <iframe
          src={pdfDisplayUrl}
          title="Lease Document Preview"
          className="w-full h-full border-0"
          sandbox="allow-same-origin"
          referrerPolicy="no-referrer"
        />
      );
    } else {
      // Fallback for other types or if type detection fails
      return (
        <iframe
          src={url}
          title="Lease Document Preview"
          className="w-full h-full border-0"
          sandbox="allow-same-origin"
          referrerPolicy="no-referrer"
        />
      );
    }
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <motion.div
          initial="hidden"
          animate="visible"
          exit="hidden"
          variants={overlayVariants}
          className="fixed inset-0 bg-black bg-opacity-30 backdrop-blur-sm overflow-y-auto h-full w-full z-50 flex items-center justify-center p-4"
        >
          <motion.div
            initial="hidden"
            animate="visible"
            exit="exit"
            variants={modalVariants}
            className="relative w-full max-w-3xl bg-white rounded-xl shadow-2xl overflow-hidden"
          >
            {/* Header */}
            <div className="sticky top-0 z-10 px-6 py-4 bg-white border-b border-gray-200 flex justify-between items-center">
              <h2 className="text-xl font-semibold text-gray-900">
                Confirm Lease Details
              </h2>
              <button
                onClick={onClose}
                className="text-gray-500 hover:text-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 rounded-full p-1 transition-colors duration-200"
                aria-label="Close modal"
              >
                <svg
                  className="h-6 w-6"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M6 18L18 6M6 6l12 12"
                  />
                </svg>
              </button>
            </div>

            {/* Body */}
            <div className="p-6 max-h-[calc(100vh-12rem)] overflow-y-auto">
              <AnimatePresence>
                {error && <ErrorMessage message={error} />}
              </AnimatePresence>

              {/* Document Preview Section - Refactored */}
              {leaseData.file_url && (
                <FormSection
                  title="Lease Document"
                  containerClass="space-y-6"
                  titleClass="text-lg font-semibold text-gray-900 pb-1 border-b border-gray-200"
                >
                  <div className="col-span-full mb-4">
                    <Button
                      type="button"
                      variant="secondary"
                      onClick={() => setShowLeasePreview(!showLeasePreview)}
                      className="text-sm py-1.5"
                    >
                      {showLeasePreview ? (
                        <>
                          <i className="fas fa-eye-slash mr-2" />Hide Document
                        </>
                      ) : (
                        <>
                          <i className="fas fa-eye mr-2" />Show Document
                        </>
                      )}
                    </Button>
                  </div>
                  <AnimatePresence>
                    {showLeasePreview && leaseData.file_url && (
                      <motion.div
                        initial={{ opacity: 0, height: 0 }}
                        animate={{ opacity: 1, height: "24rem" }} // Consistent height
                        exit={{ opacity: 0, height: 0 }}
                        transition={{ duration: 0.3, ease: "easeInOut" }}
                        className="col-span-full mt-1 mb-4 border rounded-lg overflow-hidden shadow bg-gray-50" // Consistent styling
                      >
                        {renderPreviewContent(leaseData.file_url)}
                      </motion.div>
                    )}
                  </AnimatePresence>
                </FormSection>
              )}

              <form onSubmit={handleCreateLease} className="space-y-8" id="confirm-lease-form">
                <FormSection
                  title="Tenant Information"
                  containerClass="space-y-6"
                  titleClass="text-lg font-semibold text-gray-900 pb-1 border-b border-gray-200"
                >
                  <div className="bg-gray-50 p-4 rounded-lg border border-gray-200">
                    <div className="flex flex-col sm:flex-row justify-between">
                      <div>
                        <h4 className="font-medium text-gray-900">
                          {tenant?.first_name} {tenant?.last_name}
                        </h4>
                        <p className="text-sm text-gray-600">{tenant?.email}</p>
                      </div>
                      <div className="mt-2 sm:mt-0">
                        <p className="text-sm text-gray-600">{tenant?.phone}</p>
                      </div>
                    </div>
                  </div>
                </FormSection>

                <FormSection
                  title="Property & Unit Details"
                  containerClass="space-y-6"
                  titleClass="text-lg font-semibold text-gray-900 pb-1 border-b border-gray-200"
                >
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    {/* Property Information */}
                    <div>
                      <Label htmlFor="property_id" required>
                        Property
                      </Label>
                      <Select
                        id="property_id"
                        name="property_id"
                        value={formData.property_id}
                        onChange={handlePropertyChange}
                        disabled={!isUnitEditable || isLoadingProperties}
                        required
                        emptyMessage="Select a property"
                        isLoading={isLoadingProperties}
                        options={properties}
                      />
                      {!isUnitEditable && (
                        <p className="mt-1 text-xs text-gray-500">
                          Tenant already assigned to this property.
                        </p>
                      )}
                      {fieldErrors.property_id && (
                        <p className="mt-1 text-sm text-red-600">
                          {fieldErrors.property_id}
                        </p>
                      )}
                    </div>

                    {/* Unit Information - Conditional Rendering */}
                    <div>
                      <Label
                        htmlFor={isUnitEditable ? "unit_id" : "unit"}
                        required
                      >
                        Unit
                      </Label>
                      {isUnitEditable ? (
                        <Select
                          id="unit_id"
                          name="unit_id"
                          value={formData.unit_id}
                          onChange={handleChange}
                          disabled={
                            isLoadingUnits ||
                            isLoadingLeases ||
                            !formData.property_id
                          }
                          required
                          isLoading={isLoadingUnits || isLoadingLeases}
                          emptyMessage={
                            !formData.property_id
                              ? "Select property first"
                              : isLoadingUnits || isLoadingLeases
                              ? "Loading available units..."
                              : filteredAvailableUnits.length === 0
                              ? "No available units for this property"
                              : "Select an available unit"
                          }
                          options={filteredAvailableUnits}
                        />
                      ) : (
                        <Input
                          type="text"
                          id="unit"
                          name="unit"
                          value={formData.unit}
                          readOnly
                          disabled
                        />
                      )}
                      {!isUnitEditable && (
                        <p className="mt-1 text-xs text-gray-500">
                          Tenant already assigned to this unit.
                        </p>
                      )}
                      {fieldErrors.unit_id && isUnitEditable && (
                        <p className="mt-1 text-sm text-red-600">
                          {fieldErrors.unit_id}
                        </p>
                      )}
                      {fieldErrors.unit && !isUnitEditable && (
                        <p className="mt-1 text-sm text-red-600">
                          {fieldErrors.unit}
                        </p>
                      )}
                    </div>
                  </div>
                </FormSection>

                <FormSection
                  title="Lease Details"
                  containerClass="space-y-6"
                  titleClass="text-lg font-semibold text-gray-900 pb-1 border-b border-gray-200"
                >
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <div>
                      <Label htmlFor="start_date" required>
                        Lease Start Date
                      </Label>
                      <Input
                        type="date"
                        id="start_date"
                        name="start_date"
                        value={formData.start_date}
                        onChange={handleChange}
                        required
                      />
                      {fieldErrors.start_date && (
                        <p className="mt-1 text-sm text-red-600">
                          {fieldErrors.start_date}
                        </p>
                      )}
                    </div>

                    <div>
                      <Label htmlFor="end_date" required>
                        Lease End Date
                      </Label>
                      <Input
                        type="date"
                        id="end_date"
                        name="end_date"
                        value={formData.end_date}
                        onChange={handleChange}
                        required
                      />
                      {fieldErrors.end_date && (
                        <p className="mt-1 text-sm text-red-600">
                          {fieldErrors.end_date}
                        </p>
                      )}
                    </div>

                    <div>
                      <Label htmlFor="monthly_rent" required>
                        Monthly Rent
                      </Label>
                      <div className="relative">
                        <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                          <span className="text-gray-500 sm:text-sm">$</span>
                        </div>
                        <Input
                          type="number"
                          id="monthly_rent"
                          name="monthly_rent"
                          value={formData.monthly_rent}
                          onChange={handleChange}
                          step="0.01"
                          min="0"
                          className="pl-7"
                          required
                        />
                      </div>
                      {fieldErrors.monthly_rent && (
                        <p className="mt-1 text-sm text-red-600">
                          {fieldErrors.monthly_rent}
                        </p>
                      )}
                    </div>

                    <div>
                      <Label htmlFor="security_deposit" required>
                        Security Deposit
                      </Label>
                      <div className="relative">
                        <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                          <span className="text-gray-500 sm:text-sm">$</span>
                        </div>
                        <Input
                          type="number"
                          id="security_deposit"
                          name="security_deposit"
                          value={formData.security_deposit}
                          onChange={handleChange}
                          step="0.01"
                          min="0"
                          className="pl-7"
                          required
                        />
                      </div>
                      {fieldErrors.security_deposit && (
                        <p className="mt-1 text-sm text-red-600">
                          {fieldErrors.security_deposit}
                        </p>
                      )}
                    </div>

                    <div>
                      <Label htmlFor="rent_due_day">Rent Due Day</Label>
                      <Input
                        type="number"
                        id="rent_due_day"
                        name="rent_due_day"
                        value={formData.rent_due_day}
                        onChange={handleChange}
                        min="1"
                        max="31"
                      />
                      <p className="mt-1 text-xs text-gray-500">
                        Day of the month when rent is due
                      </p>
                      {fieldErrors.rent_due_day && (
                        <p className="mt-1 text-sm text-red-600">
                          {fieldErrors.rent_due_day}
                        </p>
                      )}
                    </div>

                    <div>
                      <Label htmlFor="special_terms">Special Terms</Label>
                      <textarea
                        id="special_terms"
                        name="special_terms"
                        value={formData.special_terms || ""}
                        onChange={handleChange}
                        rows={2}
                        className="w-full px-4 py-2.5 text-gray-900 border border-gray-300 rounded-lg shadow-sm focus:ring-2 focus:ring-blue-500/30 focus:border-blue-500 focus:outline-none transition-all duration-200"
                      />
                      <p className="mt-1 text-xs text-gray-500">
                        Any special conditions for this lease
                      </p>
                    </div>
                  </div>
                </FormSection>
              </form>
            </div>

            {/* Footer */}
            <div className="sticky bottom-0 z-10 px-6 py-4 bg-white border-t border-gray-200 flex justify-end space-x-3">
              <Button type="button" variant="secondary" onClick={onClose}>
                Cancel
              </Button>
              <Button
                type="submit"
                form="confirm-lease-form"
                variant="primary"
                disabled={
                  isLoading ||
                  isLoadingUnits ||
                  isLoadingProperties ||
                  isLoadingLeases
                }
              >
                {isLoading ? (
                  <>
                    <svg
                      className="animate-spin -ml-1 mr-2 h-4 w-4 text-white"
                      xmlns="http://www.w3.org/2000/svg"
                      fill="none"
                      viewBox="0 0 24 24"
                    >
                      <circle
                        className="opacity-25"
                        cx="12"
                        cy="12"
                        r="10"
                        stroke="currentColor"
                        strokeWidth="4"
                      ></circle>
                      <path
                        className="opacity-75"
                        fill="currentColor"
                        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                      ></path>
                    </svg>
                    Creating Lease
                  </>
                ) : (
                  "Create Lease"
                )}
              </Button>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
};

export default ConfirmLeaseModal;
