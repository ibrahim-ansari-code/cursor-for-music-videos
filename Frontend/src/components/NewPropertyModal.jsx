import React, { useState, useEffect, useCallback, useRef } from "react";
import debounce from "lodash.debounce";
import { AnimatePresence, motion } from "framer-motion"; // For smooth animations

// --- Helper Function for Azure Maps API ---
const AZURE_MAPS_API_KEY = import.meta.env.VITE_AZURE_MAPS_KEY;

async function fetchAddressSuggestions(query) {
  if (!query || query.length < 3) {
    return [];
  }

  if (!AZURE_MAPS_API_KEY) {
    console.error(
      "Azure Maps API key is missing. Please check your environment variables."
    );
    return [];
  }

  console.log("Fetching address suggestions for:", query);
  const url = `https://atlas.microsoft.com/search/address/json?api-version=1.0&typeahead=true&query=${encodeURIComponent(
    query
  )}&countrySet=CA&limit=5&subscription-key=${AZURE_MAPS_API_KEY}`;

  try {
    console.log(
      "Calling Azure Maps API:",
      url.replace(AZURE_MAPS_API_KEY, "API_KEY_HIDDEN")
    );
    const response = await fetch(url);

    if (!response.ok) {
      console.error(
        "Azure Maps API error:",
        response.status,
        response.statusText
      );
      const errorText = await response.text();
      console.error("Error details:", errorText);
      return [];
    }

    const data = await response.json();
    console.log("Azure Maps API response:", data);
    return data.results || [];
  } catch (error) {
    console.error("Error fetching address suggestions:", error);
    return [];
  }
}

// --- Helper Function for Unit Generation ---
function generateUnits(numFloors, unitsPerFloor) {
  const units = [];
  const floors = parseInt(numFloors, 10);
  const perFloor = parseInt(unitsPerFloor, 10);

  if (isNaN(floors) || isNaN(perFloor) || floors <= 0 || perFloor <= 0) {
    return [];
  }

  for (let floor = 1; floor <= floors; floor++) {
    for (let unitNum = 1; unitNum <= perFloor; unitNum++) {
      // Format: floor number followed by 2-digit unit number (e.g., 101, 102, 201, etc.)
      const unitName = `${floor}${String(unitNum).padStart(2, "0")}`;
      units.push({ name: unitName, floor: floor });
    }
  }
  return units;
}

// --- Helper Function to POST Units ---
async function createUnitsForProperty(propertyId, units) {
  if (!propertyId || !units || units.length === 0) return;

  const unitCreationPromises = units.map((unit) => {
    const apiUrl =
      import.meta.env.VITE_API_URL || "https://brikli.azurewebsites.net"; // Get API URL from env
    return fetch(`${apiUrl}/api/properties/${propertyId}/units`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        // Assuming you have a way to get the auth token
        // 'Authorization': `Bearer ${getAuthToken()}`
      },
      body: JSON.stringify({
        name: unit.name,
        floor: unit.floor,
        // Add other default unit fields if needed by backend, e.g.:
        // description: '',
        // is_rented: false,
      }),
    });
  });

  try {
    const responses = await Promise.all(unitCreationPromises);
    const errors = responses.filter((res) => !res.ok);

    if (errors.length > 0) {
      console.error("Some units failed to create:", errors);
      // Optionally aggregate error messages
      throw new Error(`Failed to create ${errors.length} unit(s).`);
    }
    console.log(
      `${units.length} units created successfully for property ${propertyId}`
    );
  } catch (error) {
    console.error("Error creating units:", error);
    throw error; // Re-throw to be caught by handleSubmit
  }
}

// UI Components
const Label = ({ htmlFor, required, children }) => (
  <label
    htmlFor={htmlFor}
    className={`block text-sm font-medium text-gray-700 mb-1.5 ${
      required ? 'after:content-["*"] after:ml-0.5 after:text-red-500' : ""
    }`}
  >
    {children}
  </label>
);

const Input = ({
  id,
  name,
  value,
  onChange,
  placeholder,
  required,
  readOnly,
  type = "text",
  min,
  className = "",
  ...props
}) => (
  <input
    id={id || name}
    name={name}
    type={type}
    value={value}
    onChange={onChange}
    min={min}
    placeholder={placeholder}
    required={required}
    readOnly={readOnly}
    className={`w-full px-4 py-2.5 text-gray-900 bg-white border ${
      readOnly ? "bg-gray-50 border-gray-200" : "border-gray-300"
    } rounded-lg shadow-sm focus:ring-2 focus:ring-blue-500/30 focus:border-blue-500 focus:outline-none transition-all duration-200 ${className}`}
    {...props}
  />
);

const TextArea = ({
  id,
  name,
  value,
  onChange,
  placeholder,
  required,
  rows = 3,
  className = "",
  ...props
}) => (
  <textarea
    id={id || name}
    name={name}
    value={value}
    onChange={onChange}
    rows={rows}
    placeholder={placeholder}
    required={required}
    className={`w-full px-4 py-2.5 text-gray-900 border border-gray-300 rounded-lg shadow-sm focus:ring-2 focus:ring-blue-500/30 focus:border-blue-500 focus:outline-none transition-all duration-200 ${className}`}
    {...props}
  />
);

const Select = ({
  id,
  name,
  value,
  onChange,
  required,
  children,
  className = "",
  ...props
}) => (
  <div className="relative">
    <select
      id={id || name}
      name={name}
      value={value}
      onChange={onChange}
      required={required}
      className={`w-full px-4 py-2.5 text-gray-900 bg-white border border-gray-300 rounded-lg shadow-sm appearance-none focus:ring-2 focus:ring-blue-500/30 focus:border-blue-500 focus:outline-none transition-all duration-200 ${className}`}
      {...props}
    >
      {children}
    </select>
    <div className="absolute inset-y-0 right-0 flex items-center px-2 pointer-events-none">
      <svg
        className="w-5 h-5 text-gray-500"
        fill="currentColor"
        viewBox="0 0 20 20"
      >
        <path
          fillRule="evenodd"
          d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z"
          clipRule="evenodd"
        />
      </svg>
    </div>
  </div>
);

const Checkbox = ({ id, name, checked, onChange, children }) => (
  <div className="flex items-center">
    <input
      id={id || name}
      name={name}
      type="checkbox"
      checked={checked}
      onChange={onChange}
      className="h-4 w-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500 transition duration-150 ease-in-out"
    />
    <label htmlFor={id || name} className="ml-2 block text-sm text-gray-700">
      {children}
    </label>
  </div>
);

const Button = ({
  type,
  onClick,
  variant = "primary",
  disabled,
  children,
  className = "",
  ...props
}) => {
  const baseClasses =
    "px-4 py-2.5 rounded-lg font-medium text-sm focus:outline-none focus:ring-2 focus:ring-offset-2 transition-all duration-200 inline-flex items-center justify-center gap-2 disabled:opacity-60 disabled:cursor-not-allowed";

  const variants = {
    primary:
      "bg-blue-600 hover:bg-blue-700 text-white border border-transparent focus:ring-blue-500",
    secondary:
      "bg-white hover:bg-gray-50 text-gray-700 border border-gray-300 focus:ring-blue-500",
    danger:
      "bg-red-600 hover:bg-red-700 text-white border border-transparent focus:ring-red-500",
  };

  return (
    <button
      type={type}
      onClick={onClick}
      disabled={disabled}
      className={`${baseClasses} ${variants[variant]} ${className}`}
      {...props}
    >
      {children}
    </button>
  );
};

const FormSection = ({ title, children, className = "" }) => (
  <div className={`space-y-6 ${className}`}>
    {title && (
      <h3 className="text-lg font-semibold text-gray-900 pb-1 border-b border-gray-200">
        {title}
      </h3>
    )}
    {children}
  </div>
);

const ErrorMessage = ({ message }) => (
  <motion.div
    initial={{ opacity: 0, y: -10 }}
    animate={{ opacity: 1, y: 0 }}
    exit={{ opacity: 0 }}
    className="mb-6 p-3 bg-red-50 border border-red-200 text-red-600 rounded-lg flex items-start gap-2"
  >
    <svg
      xmlns="http://www.w3.org/2000/svg"
      className="h-5 w-5 mt-0.5 flex-shrink-0"
      viewBox="0 0 20 20"
      fill="currentColor"
    >
      <path
        fillRule="evenodd"
        d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zm-1 9a1 1 0 100-2 1 1 0 000 2z"
        clipRule="evenodd"
      />
    </svg>
    <span>{message}</span>
  </motion.div>
);

// --- Component ---
const NewPropertyModal = ({
  isOpen,
  onClose,
  onSubmit,
  isLoading,
  propertyData,
  isEditing,
}) => {
  const initialFormData = {
    name: "",
    address: "",
    city: "",
    province: "",
    postal_code: "",
    property_type: "",
    description: "",
    year_built: "",
    status: "ACTIVE",
    // Apartment specific fields
    num_floors: "",
    units_per_floor: "",
    auto_generate_units: true,
    manual_units: "", // Store as comma-separated string for simplicity for now
  };

  const [formData, setFormData] = useState(initialFormData);
  const [error, setError] = useState("");
  const [suggestions, setSuggestions] = useState([]);
  const [isSuggestionLoading, setIsSuggestionLoading] = useState(false);
  const [showSuggestions, setShowSuggestions] = useState(false); // Control visibility
  const [isSubmittingUnits, setIsSubmittingUnits] = useState(false); // Loading state for unit creation

  // Ref for the suggestions dropdown to detect outside clicks
  const suggestionsRef = useRef(null);
  const modalRef = useRef(null);

  // Load propertyData for editing
  useEffect(() => {
    if (isEditing && propertyData) {
      // Transform propertyData for the form
      setFormData({
        name: propertyData.name || "",
        address: propertyData.address || "",
        city: propertyData.city || "",
        province: propertyData.province || "",
        postal_code: propertyData.postal_code || "",
        property_type: propertyData.property_type || "",
        description: propertyData.description || "",
        year_built: propertyData.year_built || "",
        status: propertyData.status || "ACTIVE",
        // For apartment properties, we'd need to fetch unit details separately
        // or pass them with the propertyData
        num_floors: "",
        units_per_floor: "",
        auto_generate_units: true,
        manual_units: "",
      });
    } else {
      // Reset form for new properties
      setFormData(initialFormData);
    }
  }, [isEditing, propertyData, isOpen]);

  // Helper function to check for unsaved changes
  const hasUnsavedChanges = () => {
    // For editing, compare with propertyData; for new properties, compare with initialFormData
    const compareData =
      isEditing && propertyData
        ? {
            name: propertyData.name || "",
            address: propertyData.address || "",
            city: propertyData.city || "",
            province: propertyData.province || "",
            postal_code: propertyData.postal_code || "",
            property_type: propertyData.property_type || "",
            description: propertyData.description || "",
            year_built: propertyData.year_built || "",
            status: propertyData.status || "ACTIVE",
          }
        : initialFormData;

    // Compare each field in formData with compareData
    for (const key in formData) {
      // Skip apartment-specific fields if not an apartment
      if (
        [
          "num_floors",
          "units_per_floor",
          "auto_generate_units",
          "manual_units",
        ].includes(key) &&
        !(formData.property_type === "apartment-complex")
      ) {
        continue;
      }

      if (formData[key] !== compareData[key]) {
        return true;
      }
    }
    return false;
  };

  // Handler for closing the modal with confirmation if needed
  const handleCloseWithConfirmation = () => {
    if (hasUnsavedChanges()) {
      const confirmed = window.confirm(
        "You will lose your progress. Are you sure you want to close this form?"
      );
      if (!confirmed) return;
    }
    // Reset form and close modal
    setFormData(initialFormData);
    onClose();
  };

  // Debounced fetch function
  const debouncedFetch = useCallback(
    debounce(async (query) => {
      console.log("Debounced search triggered for:", query);
      setIsSuggestionLoading(true);
      try {
        const results = await fetchAddressSuggestions(query);
        console.log(
          `Got ${results.length} suggestions for "${query}":`,
          results
        );
        setSuggestions(results);
        setShowSuggestions(results.length > 0); // Only show if we have results
      } catch (error) {
        console.error("Error in debounced fetch:", error);
        setSuggestions([]);
      } finally {
        setIsSuggestionLoading(false);
      }
    }, 300), // 300ms debounce delay
    []
  );

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target;
    const val = type === "checkbox" ? checked : value;

    setFormData((prev) => ({
      ...prev,
      [name]: val,
    }));

    // Handle address input for suggestions
    if (name === "address") {
      if (value.length >= 3) {
        console.log(
          `Address input changed: "${value}" (${value.length} chars). Triggering search...`
        );
        debouncedFetch(value);
      } else {
        console.log(
          `Address too short: "${value}" (${value.length} chars). Need at least 3 chars.`
        );
        setSuggestions([]); // Clear suggestions if query is too short
        setShowSuggestions(false);
        debouncedFetch.cancel(); // Cancel any pending debounced calls
      }
    }
  };

  const handleSuggestionClick = (suggestion) => {
    setFormData((prev) => ({
      ...prev,
      address:
        suggestion.address.streetNameAndNumber ||
        suggestion.address.freeformAddress ||
        "",
      city: suggestion.address.municipality || "",
      province: suggestion.address.countrySubdivisionName || "",
      postal_code: suggestion.address.postalCode || "",
    }));
    setSuggestions([]);
    setShowSuggestions(false);
  };

  // Handle Escape key to close modal
  useEffect(() => {
    const handleEscapeKey = (e) => {
      if (e.key === "Escape") {
        handleCloseWithConfirmation();
      }
    };

    document.addEventListener("keydown", handleEscapeKey);
    return () => {
      document.removeEventListener("keydown", handleEscapeKey);
    };
  }, [formData]); // Add formData as dependency to check for unsaved changes

  // Close suggestions when clicking outside
  useEffect(() => {
    function handleClickOutside(event) {
      if (
        suggestionsRef.current &&
        !suggestionsRef.current.contains(event.target)
      ) {
        setShowSuggestions(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
      debouncedFetch.cancel(); // Clean up debounce on unmount
    };
  }, [suggestionsRef, debouncedFetch]);

  // Click outside modal to close it
  useEffect(() => {
    function handleClickOutsideModal(event) {
      if (modalRef.current && !modalRef.current.contains(event.target)) {
        handleCloseWithConfirmation();
      }
    }

    if (isOpen) {
      document.addEventListener("mousedown", handleClickOutsideModal);
    }

    return () => {
      document.removeEventListener("mousedown", handleClickOutsideModal);
    };
  }, [isOpen, formData]); // Add formData as dependency to check for unsaved changes

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setIsSubmittingUnits(false); // Reset unit submission state

    // Only include essential fields in required validation
    let requiredFields = [
      "name",
      "address",
      "city",
      "province",
      "postal_code",
      "property_type",
    ];

    // Add apartment-specific fields ONLY when creating, not editing
    if (formData.property_type === "apartment-complex" && !isEditing) {
      requiredFields = [...requiredFields, "num_floors", "units_per_floor"];
      if (!formData.auto_generate_units) {
        requiredFields.push("manual_units");
      }
    }
    // Note: 'year_built' and 'description' are deliberately excluded from required fields

    const missingFields = requiredFields.filter((field) => !formData[field]);

    if (missingFields.length > 0) {
      setError(
        `Please fill in all required fields: ${missingFields.join(", ")}`
      );
      return;
    }

    try {
      // Prepare property payload
      const propertyPayload = { ...formData };

      // Ensure status is uppercase
      if (propertyPayload.status) {
        propertyPayload.status = propertyPayload.status.toUpperCase();
      }

      // Convert empty optional fields to null for backend validation
      if (propertyPayload.year_built === "") {
        propertyPayload.year_built = null;
      }
      if (propertyPayload.description === "") {
        propertyPayload.description = null;
      }

      // Handle units for apartment complex
      if (formData.property_type === "apartment-complex" && !isEditing) {
        // Only handle units on create
        // Generate units if auto-generate is enabled
        let units = [];

        if (formData.auto_generate_units) {
          // Generate units based on num_floors and units_per_floor
          units = generateUnits(
            formData.num_floors,
            formData.units_per_floor
          ).map((unit) => unit.name);
        } else if (formData.manual_units) {
          // Parse manual units from comma-separated string
          units = formData.manual_units
            .split(",")
            .map((unit) => unit.trim())
            .filter(Boolean);
        }

        // Add units array to payload
        propertyPayload.units = units;
      }

      // Remove apartment configuration fields from payload, ESPECIALLY for updates
      delete propertyPayload.num_floors;
      delete propertyPayload.units_per_floor;
      delete propertyPayload.auto_generate_units;
      delete propertyPayload.manual_units;
      if (isEditing) {
        // Also remove units array if editing
        delete propertyPayload.units;
        delete propertyPayload.property_type; // Don't send property_type on updates
      }

      // Call the onSubmit passed from parent (will call createProperty or updateProperty)
      const savedProperty = await onSubmit(propertyPayload);

      // Unit creation is now handled by the backend (or ignored on update)
      console.log(
        `Property ${
          isEditing ? "updated" : "created/units created"
        } successfully:`,
        savedProperty
      );

      // Reset form and close modal on overall success
      setFormData(initialFormData);

      // Create toast notification for success feedback
      const toast = document.createElement("div");
      toast.className =
        "fixed bottom-4 right-4 bg-green-100 border-l-4 border-green-500 text-green-700 p-4 rounded shadow-lg";
      toast.innerHTML = `
        <div className="flex items-center">
          <svg className="w-6 h-6 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path>
          </svg>
          <p>Property ${isEditing ? "updated" : "created"} successfully!</p>
        </div>
      `;
      document.body.appendChild(toast);

      // Remove toast after 3 seconds
      setTimeout(() => {
        toast.remove();
      }, 3000);

      onClose();
    } catch (err) {
      // Improved error handling
      let errorMessage = `Failed to ${
        isEditing ? "update" : "create"
      } property`;
      // Attempt to get a more specific message from the backend response
      if (err.response && err.response.data && err.response.data.detail) {
        // Handle FastAPI validation errors (often an array)
        if (Array.isArray(err.response.data.detail)) {
          errorMessage = err.response.data.detail
            .map((d) => `${d.loc ? d.loc.join(" -> ") + ": " : ""}${d.msg}`)
            .join("; ");
        } else {
          errorMessage = err.response.data.detail; // Standard string detail
        }
      } else if (err.message) {
        errorMessage = err.message; // Fallback to generic JS error message
      }
      setError(errorMessage);
    }
  };

  if (!isOpen) return null;

  const isApartmentComplex = formData.property_type === "apartment-complex";

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 bg-black bg-opacity-30 backdrop-blur-sm overflow-y-auto h-full w-full z-50 flex items-center justify-center p-4"
    >
      <motion.div
        initial={{ scale: 0.95, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        exit={{ scale: 0.95, opacity: 0 }}
        transition={{ type: "spring", stiffness: 300, damping: 30 }}
        ref={modalRef}
        className="relative w-full max-w-3xl bg-white rounded-xl shadow-2xl overflow-hidden"
      >
        {/* Header */}
        <div className="sticky top-0 z-10 px-6 py-4 bg-white border-b border-gray-200 flex justify-between items-center">
          <h2 className="text-xl font-semibold text-gray-900">
            {isEditing ? "Edit Property" : "Add New Property"}
          </h2>
          <button
            onClick={handleCloseWithConfirmation}
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

          <form onSubmit={handleSubmit} className="space-y-8">
            <FormSection title="Property Information">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {/* Name & Type - Side by side */}
                <div>
                  <Label htmlFor="name" required>
                    Property Name
                  </Label>
                  <Input
                    id="name"
                    name="name"
                    value={formData.name}
                    onChange={handleChange}
                    placeholder="Enter property name"
                    required
                  />
                </div>

                <div>
                  <Label htmlFor="property_type" required>
                    Property Type
                  </Label>
                  <Select
                    id="property_type"
                    name="property_type"
                    value={formData.property_type}
                    onChange={handleChange}
                    required
                  >
                    <option value="">Select type</option>
                    <option value="residential">Residential</option>
                    <option value="commercial">Commercial</option>
                    <option value="industrial">Industrial</option>
                    <option value="mixed-use">Mixed Use</option>
                    <option value="apartment-complex">Apartment Complex</option>
                  </Select>
                </div>
              </div>

              {/* Address with Autocomplete */}
              <div className="mt-6">
                <Label htmlFor="address" required>
                  Address
                </Label>
                <div className="relative">
                  <Input
                    id="address"
                    name="address"
                    value={formData.address}
                    onChange={handleChange}
                    onFocus={() =>
                      formData.address.length >= 3 && setShowSuggestions(true)
                    }
                    placeholder="Enter street address (e.g., 123 Main St)"
                    required
                    autoComplete="off"
                  />

                  {/* Loading indicator */}
                  {isSuggestionLoading && (
                    <div className="absolute right-3 top-3">
                      <svg
                        className="animate-spin h-5 w-5 text-blue-500"
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
                    </div>
                  )}

                  {/* Suggestions Dropdown */}
                  <AnimatePresence>
                    {showSuggestions && formData.address.length >= 3 && (
                      <motion.ul
                        initial={{ opacity: 0, y: -10 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0, y: -10 }}
                        transition={{ duration: 0.15 }}
                        ref={suggestionsRef}
                        className="absolute z-40 w-full mt-1 bg-white border border-gray-200 rounded-md shadow-lg max-h-60 overflow-auto"
                      >
                        {suggestions.length > 0 ? (
                          suggestions.map((suggestion, index) => (
                            <li
                              key={suggestion.id || index}
                              onClick={() => handleSuggestionClick(suggestion)}
                              className="px-4 py-3 cursor-pointer hover:bg-blue-50 transition-colors duration-150 border-b border-gray-100 last:border-0"
                            >
                              <div className="font-medium text-gray-800">
                                {suggestion.address.freeformAddress}
                              </div>
                              <div className="text-sm text-gray-500">
                                {suggestion.address.countrySubdivisionName},{" "}
                                {suggestion.address.country}
                              </div>
                            </li>
                          ))
                        ) : (
                          <li className="px-4 py-3 text-gray-500">
                            No suggestions found
                          </li>
                        )}
                      </motion.ul>
                    )}
                  </AnimatePresence>
                </div>
              </div>

              {/* Location Details */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mt-6">
                <div>
                  <Label htmlFor="city" required>
                    City
                  </Label>
                  <Input
                    id="city"
                    name="city"
                    value={formData.city}
                    onChange={handleChange}
                    placeholder="Enter city"
                    required
                  />
                </div>

                <div>
                  <Label htmlFor="province" required>
                    Province
                  </Label>
                  <Input
                    id="province"
                    name="province"
                    value={formData.province}
                    onChange={handleChange}
                    placeholder="Enter province"
                    required
                  />
                </div>

                <div>
                  <Label htmlFor="postal_code" required>
                    Postal Code
                  </Label>
                  <Input
                    id="postal_code"
                    name="postal_code"
                    value={formData.postal_code}
                    onChange={handleChange}
                    placeholder="Enter postal code"
                    required
                  />
                </div>
              </div>

              {/* Additional Details */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mt-6">
                <div>
                  <Label htmlFor="year_built">Year Built (Optional)</Label>
                  <Input
                    id="year_built"
                    name="year_built"
                    type="number"
                    value={formData.year_built}
                    onChange={handleChange}
                    placeholder="Enter year built"
                  />
                </div>

                <div>
                  <Label htmlFor="status">Status</Label>
                  <Select
                    id="status"
                    name="status"
                    value={formData.status}
                    onChange={handleChange}
                  >
                    <option value="ACTIVE">Active</option>
                    <option value="MAINTENANCE">Maintenance</option>
                    <option value="VACANT">Vacant</option>
                  </Select>
                </div>
              </div>

              {/* Description */}
              <div className="mt-6">
                <Label htmlFor="description">Description (Optional)</Label>
                <TextArea
                  id="description"
                  name="description"
                  value={formData.description}
                  onChange={handleChange}
                  rows={3}
                  placeholder="Enter property description"
                />
              </div>
            </FormSection>

            {/* --- Apartment Complex Specific Fields --- */}
            <AnimatePresence>
              {/* Only show apartment details section when CREATING a new apartment complex */}
              {!isEditing && isApartmentComplex && (
                <motion.div
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: "auto" }}
                  exit={{ opacity: 0, height: 0 }}
                  transition={{ duration: 0.3 }}
                >
                  <FormSection
                    title="Apartment Details"
                    className="pt-4 border-t border-gray-200"
                  >
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                      <div>
                        <Label htmlFor="num_floors" required>
                          Number of Floors
                        </Label>
                        <Input
                          id="num_floors"
                          name="num_floors"
                          type="number"
                          value={formData.num_floors}
                          onChange={handleChange}
                          min="1"
                          placeholder="e.g., 5"
                          required={isApartmentComplex}
                        />
                      </div>

                      <div>
                        <Label htmlFor="units_per_floor" required>
                          Units Per Floor
                        </Label>
                        <Input
                          id="units_per_floor"
                          name="units_per_floor"
                          type="number"
                          value={formData.units_per_floor}
                          onChange={handleChange}
                          min="1"
                          placeholder="e.g., 10"
                          required={isApartmentComplex}
                        />
                      </div>
                    </div>

                    {/* Unit Generation Options */}
                    <div className="mt-6 p-4 bg-gray-50 rounded-lg border border-gray-200">
                      <Checkbox
                        id="auto_generate_units"
                        name="auto_generate_units"
                        checked={formData.auto_generate_units}
                        onChange={handleChange}
                      >
                        Auto-generate unit numbers (e.g., 101, 102, 201...)
                      </Checkbox>

                      <AnimatePresence>
                        {!formData.auto_generate_units && (
                          <motion.div
                            initial={{ opacity: 0, height: 0 }}
                            animate={{ opacity: 1, height: "auto" }}
                            exit={{ opacity: 0, height: 0 }}
                            transition={{ duration: 0.2 }}
                            className="mt-4"
                          >
                            <Label htmlFor="manual_units" required>
                              Enter Unit Numbers
                            </Label>
                            <TextArea
                              id="manual_units"
                              name="manual_units"
                              value={formData.manual_units}
                              onChange={handleChange}
                              rows={4}
                              placeholder="Enter unit numbers separated by commas (e.g., 101, 102, Lobby, PH1)"
                              required={
                                !formData.auto_generate_units &&
                                isApartmentComplex
                              }
                            />
                            <p className="mt-1.5 text-xs text-gray-500 flex items-center">
                              <svg
                                className="w-4 h-4 mr-1 text-gray-400"
                                fill="currentColor"
                                viewBox="0 0 20 20"
                              >
                                <path
                                  fillRule="evenodd"
                                  d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zm-1 9a1 1 0 100-2 1 1 0 000 2z"
                                  clipRule="evenodd"
                                />
                              </svg>
                              Separate each unit number with a comma.
                            </p>
                          </motion.div>
                        )}
                      </AnimatePresence>
                    </div>
                  </FormSection>
                </motion.div>
              )}
            </AnimatePresence>
          </form>
        </div>

        {/* Footer */}
        <div className="sticky bottom-0 z-10 px-6 py-4 bg-white border-t border-gray-200 flex justify-end space-x-3">
          <Button
            type="button"
            variant="secondary"
            onClick={handleCloseWithConfirmation}
          >
            Cancel
          </Button>
          <Button
            type="submit"
            variant="primary"
            onClick={handleSubmit}
            disabled={isLoading || isSubmittingUnits}
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
                {isEditing ? "Updating Property" : "Creating Property"}
              </>
            ) : isSubmittingUnits ? (
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
                Creating Units
              </>
            ) : isEditing ? (
              "Update Property"
            ) : (
              "Create Property"
            )}
          </Button>
        </div>
      </motion.div>
    </motion.div>
  );
};

export default NewPropertyModal;
