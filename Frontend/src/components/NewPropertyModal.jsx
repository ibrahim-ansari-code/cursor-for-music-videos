import React, { useState, useEffect, useCallback, useRef } from "react";
import debounce from "lodash.debounce";
import { AnimatePresence, motion } from "framer-motion";
import {
  ModalShell,
  Label,
  Input,
  TextArea,
  Select,
  Checkbox,
  Button,
  FormSection,
  // ErrorMessage is implicitly used by ModalShell via its error prop
} from "./ui/SharedModalComponents";
import { toast } from "react-toastify"; // Using react-toastify for success messages

// --- Helper Function for Azure Maps API ---
const AZURE_MAPS_API_KEY = import.meta.env.VITE_AZURE_MAPS_KEY;

/**
 * Fetches address suggestions from the Azure Maps API based on a query string.
 *
 * Returns up to 5 address suggestions for Canadian addresses matching the input query. If the query is less than 3 characters, the API key is missing, or an error occurs, an empty array is returned.
 *
 * @param {string} query - The address search input.
 * @returns {Promise<Array>} A promise that resolves to an array of address suggestion objects.
 *
 * @remark Logs errors to the console if the API key is missing or if the API request fails.
 */
async function fetchAddressSuggestions(query) {
  if (!query || query.length < 3) return [];
  if (!AZURE_MAPS_API_KEY) {
    console.error("Azure Maps API key is missing.");
    return [];
  }
  const url = `https://atlas.microsoft.com/search/address/json?api-version=1.0&typeahead=true&query=${encodeURIComponent(
    query
  )}&countrySet=CA&limit=5&subscription-key=${AZURE_MAPS_API_KEY}`;
  try {
    const response = await fetch(url);
    if (!response.ok) {
      const errorText = await response.text();
      console.error("Azure Maps API error:", response.status, errorText);
      return [];
    }
    const data = await response.json();
    return data.results || [];
  } catch (error) {
    console.error("Error fetching address suggestions:", error);
    return [];
  }
}

/**
 * Generates an array of unit objects for an apartment complex based on the number of floors and units per floor.
 *
 * Each unit is named by concatenating the floor number with a zero-padded unit number (e.g., "101", "102").
 *
 * @param {number|string} numFloors - The total number of floors in the building.
 * @param {number|string} unitsPerFloor - The number of units on each floor.
 * @returns {Array<{name: string, floor: number}>} An array of unit objects, or an empty array if inputs are invalid or non-positive.
 */
function generateUnits(numFloors, unitsPerFloor) {
  const units = [];
  const floors = parseInt(numFloors, 10);
  const perFloor = parseInt(unitsPerFloor, 10);
  if (isNaN(floors) || isNaN(perFloor) || floors <= 0 || perFloor <= 0)
    return [];
  for (let floor = 1; floor <= floors; floor++) {
    for (let unitNum = 1; unitNum <= perFloor; unitNum++) {
      const unitName = `${floor}${String(unitNum).padStart(2, "0")}`;
      units.push({ name: unitName, floor: floor });
    }
  }
  return units;
}

const NewPropertyModal = ({
  isOpen,
  onClose,
  onSubmit, // This is expected to be createProperty or updateProperty API call
  isLoading: parentIsLoading, // Renamed to avoid conflict with internal loading states
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
    num_floors: "",
    units_per_floor: "",
    auto_generate_units: true,
    manual_units: "",
  };

  const [formData, setFormData] = useState(initialFormData);
  const [error, setError] = useState(""); // General error for ModalShell
  const [suggestions, setSuggestions] = useState([]);
  const [isSuggestionLoading, setIsSuggestionLoading] = useState(false);
  const [showSuggestions, setShowSuggestions] = useState(false);
  // const [isSubmittingUnits, setIsSubmittingUnits] = useState(false); // Unit submission is part of main submit now

  const suggestionsRef = useRef(null);
  // modalRef is now managed by ModalShell

  useEffect(() => {
    if (isOpen) {
      if (isEditing && propertyData) {
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
          num_floors: "", // Not loading unit structure for edit
          units_per_floor: "",
          auto_generate_units: true,
          manual_units: "",
        });
      } else {
        setFormData(initialFormData);
      }
      setError(""); // Clear error when modal opens/resets
      setSuggestions([]);
      setShowSuggestions(false);
    }
  }, [isEditing, propertyData, isOpen]); // Added isOpen to reset form for new entries

  const hasUnsavedChanges = () => {
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
            // Exclude unit fields from comparison for existing properties
          }
        : initialFormData;

    for (const key in formData) {
      if (
        [
          "num_floors",
          "units_per_floor",
          "auto_generate_units",
          "manual_units",
        ].includes(key) &&
        isEditing
      ) {
        continue; // Don't compare these for existing properties being edited
      }
      if (
        formData[key] !== compareData[key] &&
        Object.hasOwn(compareData, key)
      ) {
        // ensure key exists on compareData
        return true;
      }
    }
    return false;
  };

  const handleCloseAttempt = () => {
    if (hasUnsavedChanges()) {
      if (
        !window.confirm(
          "You have unsaved changes. Are you sure you want to close?"
        )
      ) {
        return;
      }
    }
    onClose(); // This will set isOpen to false in parent
  };

  const debouncedFetch = useCallback(
    debounce(async (query) => {
      setIsSuggestionLoading(true);
      try {
        const results = await fetchAddressSuggestions(query);
        setSuggestions(results);
        setShowSuggestions(results.length > 0);
      } catch (fetchError) {
        console.error("Error in debounced fetch:", fetchError);
        setSuggestions([]);
      } finally {
        setIsSuggestionLoading(false);
      }
    }, 350),
    []
  );

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target;
    const val = type === "checkbox" ? checked : value;
    setFormData((prev) => ({ ...prev, [name]: val }));
    if (name === "address") {
      if (value.length >= 3) {
        debouncedFetch(value);
      } else {
        setSuggestions([]);
        setShowSuggestions(false);
        debouncedFetch.cancel();
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

  const handleSuggestionKeyDown = (event, suggestion) => {
    if (
      event.key === "Enter" ||
      event.key === " " ||
      event.key === "Spacebar" ||
      event.code === "Space"
    ) {
      event.preventDefault(); // Prevent default action (e.g., scrolling on space)
      handleSuggestionClick(suggestion);
    }
  };

  useEffect(() => {
    /**
     * Hides the address suggestions dropdown when a click occurs outside of it.
     *
     * @param {MouseEvent} event - The mouse event triggered by the user's click.
     */
    function handleClickOutsideSuggestions(event) {
      if (
        suggestionsRef.current &&
        !suggestionsRef.current.contains(event.target)
      ) {
        setShowSuggestions(false);
      }
    }
    if (showSuggestions) {
      document.addEventListener("mousedown", handleClickOutsideSuggestions);
    }
    return () => {
      document.removeEventListener("mousedown", handleClickOutsideSuggestions);
      debouncedFetch.cancel();
    };
  }, [showSuggestions, suggestionsRef, debouncedFetch]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");

    let requiredFields = [
      "name",
      "address",
      "city",
      "province",
      "postal_code",
      "property_type",
    ];
    if (formData.property_type === "apartment-complex" && !isEditing) {
      requiredFields = [...requiredFields, "num_floors", "units_per_floor"];
      if (!formData.auto_generate_units) {
        requiredFields.push("manual_units");
      }
    }
    const missingFields = requiredFields.filter((field) => !formData[field]);
    if (missingFields.length > 0) {
      setError(
        `Please fill in all required fields: ${missingFields.join(", ")}`
      );
      return;
    }

    try {
      const propertyPayloadBase = {
        name: formData.name,
        address: formData.address,
        city: formData.city,
        province: formData.province,
        postal_code: formData.postal_code,
        property_type: formData.property_type,
        status: formData.status ? formData.status.toUpperCase() : "ACTIVE",
        year_built: formData.year_built === "" ? null : formData.year_built,
        description: formData.description === "" ? null : formData.description,
      };

      let cleanPayload;

      if (isEditing) {
        // For editing, exclude property_type and units
        const { property_type, ...editableFields } = propertyPayloadBase;
        cleanPayload = editableFields;
      } else {
        cleanPayload = { ...propertyPayloadBase };
        if (formData.property_type === "apartment-complex") {
          let units = [];
          if (formData.auto_generate_units) {
            units = generateUnits(
              formData.num_floors,
              formData.units_per_floor
            ).map((unit) => unit.name);
          } else if (formData.manual_units) {
            units = formData.manual_units
              .split(",")
              .map((unit) => unit.trim())
              .filter(Boolean);
          }
          cleanPayload.units = units;
        }
      }

      // The onSubmit function will receive the cleanPayload
      await onSubmit(cleanPayload);

      toast.success(
        `Property ${isEditing ? "updated" : "created"} successfully!`,
        {
          position: "bottom-right",
          autoClose: 3000,
          hideProgressBar: false,
          closeOnClick: true,
          pauseOnHover: true,
          draggable: true,
          progress: undefined,
        }
      );
      onClose(); // This will reset the form via useEffect on isOpen
    } catch (err) {
      let errorMessage = `Failed to ${
        isEditing ? "update" : "create"
      } property.`;
      if (err.response?.data?.detail) {
        errorMessage = Array.isArray(err.response.data.detail)
          ? err.response.data.detail
              .map((d) => `${d.loc ? `${d.loc.join(" -> ")}: ` : ""}${d.msg}`)
              .join("; ")
          : err.response.data.detail;
      } else if (err.message) {
        errorMessage = err.message;
      }
      setError(errorMessage);
      toast.error(errorMessage);
    }
  };

  const isApartmentComplex = formData.property_type === "apartment-complex";

  const formContent = (
    <form onSubmit={handleSubmit} className="space-y-8">
      <FormSection
        title="Property Information"
        containerClass="space-y-6"
        titleClass="text-lg font-semibold text-gray-900 pb-2 mb-4 border-b border-gray-200"
      >
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
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
              disabled={isEditing}
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
            {isSuggestionLoading && (
              <div className="absolute right-3 top-1/2 transform -translate-y-1/2">
                <svg
                  aria-hidden="true"
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
                  />
                  <path
                    className="opacity-75"
                    fill="currentColor"
                    d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                  />
                </svg>
              </div>
            )}
            <AnimatePresence>
              {showSuggestions && formData.address.length >= 3 && (
                <motion.div
                  initial={{ opacity: 0, y: -10 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -10 }}
                  transition={{ duration: 0.15 }}
                  ref={suggestionsRef}
                  className="absolute z-40 w-full mt-1 bg-white border border-gray-300 rounded-lg shadow-lg max-h-60 overflow-y-auto"
                  role="listbox"
                >
                  {suggestions.length > 0 ? (
                    suggestions.map((suggestion, index) => (
                      <button
                        key={suggestion.id || index}
                        type="button"
                        onClick={() => handleSuggestionClick(suggestion)}
                        onKeyDown={(e) =>
                          handleSuggestionKeyDown(e, suggestion)
                        }
                        className="w-full text-left px-4 py-2.5 text-sm text-gray-700 hover:bg-blue-500 hover:text-white focus:bg-blue-500 focus:text-white focus:outline-none transition-colors duration-150 border-b border-gray-100 last:border-b-0"
                        role="option"
                      >
                        <div className="font-medium">
                          {suggestion.address.freeformAddress}
                        </div>
                        <div className="text-xs text-gray-500 hover:text-gray-100">
                          {suggestion.address.municipality},{" "}
                          {suggestion.address.countrySubdivisionName},{" "}
                          {suggestion.address.countryCode}
                        </div>
                      </button>
                    ))
                  ) : (
                    <div className="px-4 py-2.5 text-sm text-gray-500">
                      No suggestions found
                    </div>
                  )}
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        </div>
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
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mt-6">
          <div>
            <Label htmlFor="year_built">Year Built (Optional)</Label>
            <Input
              id="year_built"
              name="year_built"
              type="number"
              value={formData.year_built}
              onChange={handleChange}
              placeholder="e.g., 1990"
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

      <AnimatePresence>
        {!isEditing && isApartmentComplex && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.3 }}
          >
            <FormSection
              title="Apartment Details"
              containerClass="space-y-6 pt-6 mt-6 border-t border-gray-200"
              titleClass="text-lg font-semibold text-gray-900 pb-2 mb-4 border-b border-gray-200"
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
                    required={isApartmentComplex && !isEditing}
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
                    required={isApartmentComplex && !isEditing}
                  />
                </div>
              </div>
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
                        rows={3}
                        placeholder="Enter unit numbers separated by commas (e.g., 101, 102, Lobby, PH1)"
                        required={
                          !formData.auto_generate_units &&
                          isApartmentComplex &&
                          !isEditing
                        }
                      />
                      <p className="mt-1.5 text-xs text-gray-500 flex items-center">
                        <svg
                          aria-hidden="true"
                          className="w-4 h-4 mr-1.5 text-gray-400"
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
  );

  const footerButtons = (
    <>
      <Button type="button" variant="secondary" onClick={handleCloseAttempt}>
        Cancel
      </Button>
      <Button
        type="submit" // This will be picked up by the form's onSubmit
        variant="primary"
        isLoading={parentIsLoading} // Use parentIsLoading
        loadingText={isEditing ? "Updating..." : "Creating..."}
      >
        {isEditing ? "Update Property" : "Create Property"}
      </Button>
    </>
  );

  return (
    <ModalShell
      isOpen={isOpen}
      onClose={handleCloseAttempt} // Use the new handler
      title={isEditing ? "Edit Property" : "Add New Property"}
      error={error}
      footerContent={footerButtons}
      maxWidth="max-w-3xl" // This modal is wider
    >
      {formContent}
    </ModalShell>
  );
};

export default NewPropertyModal;
