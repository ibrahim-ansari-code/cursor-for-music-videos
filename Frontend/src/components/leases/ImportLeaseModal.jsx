import { AnimatePresence, motion } from "framer-motion";
import React, { useEffect, useState, useCallback, useRef } from "react";
import {
  fetchProperties,
  fetchTenants,
  parseLease,
  uploadLeasePDF,
  fetchPropertyUnits,
  fetchLeases,
  createLease,
} from "../../utils/api";
import TenantModal from "../tenants/TenantModal";
import {
  Label,
  Input,
  Button,
  ErrorMessage,
  FormSection,
  Select,
  TextArea,
} from "../ui/SharedModalComponents";

const ImportLeaseModal = ({
  isOpen,
  onClose,
  onImport,
  initialMode = 'file',
  propertyId: initialPropertyId = null,
  unitId: initialUnitId = null,
  unitName: initialUnitName = "",
}) => {
  const [mode, setMode] = useState(initialMode);
  const [showParsedResults, setShowParsedResults] = useState(false);

  // Common State
  const [properties, setProperties] = useState([]);
  const [units, setUnits] = useState([]);
  const [availableUnits, setAvailableUnits] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isLoadingUnits, setIsLoadingUnits] = useState(false);
  const [error, setError] = useState(null);
  const [fieldErrors, setFieldErrors] = useState({});
  
  // File Upload Mode State
  const [file, setFile] = useState(null);
  const [parsedFileUrl, setParsedFileUrl] = useState(null);

  // Form Data - Used for both modes
  const [formData, setFormData] = useState({
    property_id: initialPropertyId || "",
    unit_id: initialUnitId || "",
    unit_name: initialUnitName || "",
    tenant_id: null,
    monthly_rent: "",
    security_deposit: "",
    start_date: "",
    end_date: "",
    rent_due_day: "1",
    late_fee_amount: "",
    late_fee_after_days: "",
    special_terms: "",
  });

  // Tenant Management
  const [availableTenants, setAvailableTenants] = useState([]);
  const [isLoadingTenants, setIsLoadingTenants] = useState(false);
  const [selectedTenant, setSelectedTenant] = useState(null);
  const [tenantSearchTerm, setTenantSearchTerm] = useState("");
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);
  const dropdownRef = useRef(null);

  // Child Modals State
  const [showTenantModal, setShowTenantModal] = useState(false);

  // Reset state when modal opens
  useEffect(() => {
    if (isOpen) {
      setMode(initialMode);
      setFile(null);
      setParsedFileUrl(null);
      setShowParsedResults(false);
      setError(null);
      setFieldErrors({});
      setSelectedTenant(null);
      setTenantSearchTerm("");
      setFormData({
        property_id: initialPropertyId || "",
        unit_id: initialUnitId || "",
        unit_name: initialUnitName || "",
        tenant_id: null,
        monthly_rent: "",
        security_deposit: "",
        start_date: "",
        end_date: "",
        rent_due_day: "1",
        late_fee_amount: "",
        late_fee_after_days: "",
        special_terms: "",
      });
      loadProperties();
      if (initialPropertyId) {
        loadTenantsForProperty(initialPropertyId);
        loadUnitsForProperty(initialPropertyId);
      }
    }
  }, [isOpen, initialMode, initialPropertyId, initialUnitId, initialUnitName]);

  const loadProperties = async () => {
    try {
      const data = await fetchProperties();
      setProperties(data || []);
    } catch (err) {
      console.error("Failed to fetch properties:", err);
      setError("Could not load properties.");
    }
  };

  const loadTenantsForProperty = async (propertyId) => {
    if (!propertyId) {
        setAvailableTenants([]);
        return [];
    }
    setIsLoadingTenants(true);
    try {
      const tenants = await fetchTenants({ unassigned_only: true });
      setAvailableTenants(tenants || []);
      return tenants || [];
    } catch (err) {
      console.error("Failed to load available tenants:", err);
      setError("Could not load available tenants.");
      setAvailableTenants([]);
      return [];
    } finally {
      setIsLoadingTenants(false);
    }
  };

  const loadUnitsForProperty = async (propertyId) => {
    if (!propertyId) {
      setUnits([]);
      setAvailableUnits([]);
      return;
    }
    setIsLoadingUnits(true);
    try {
      // Fetch all units for the property
      const unitsData = await fetchPropertyUnits(propertyId);
      setUnits(unitsData || []);

      // Fetch active leases to filter available units
      const activeLeases = await fetchLeases({
        property_id: propertyId,
        status: "ACTIVE",
      });
      const activeLeaseUnitIds = new Set(
        activeLeases.map((lease) => lease.unit_id).filter((id) => id != null)
      );

      const available = unitsData.filter(
        (unit) => !activeLeaseUnitIds.has(unit.id)
      );
      setAvailableUnits(available);
    } catch (err) {
      console.error("Failed to load units:", err);
      setError("Failed to load unit information.");
      setUnits([]);
      setAvailableUnits([]);
    } finally {
      setIsLoadingUnits(false);
    }
  };

  const handleFormChange = (e) => {
    const { name, value } = e.target;
    
    // Clear field error when user starts typing
    if (fieldErrors[name]) {
      setFieldErrors(prev => {
        const updated = { ...prev };
        delete updated[name];
        return updated;
      });
    }

    // Handle property change and update form data atomically
    if (name === "property_id" && value) {
      loadTenantsForProperty(value);
      loadUnitsForProperty(value);
      setFormData(prev => ({ ...prev, [name]: value, unit_id: "", unit_name: "" }));
    } else {
      setFormData(prev => ({ ...prev, [name]: value }));
    }
  };

  const handleSelectTenant = (tenant) => {
    setSelectedTenant(tenant);
    setFormData(prev => ({...prev, tenant_id: tenant.id}));
    setTenantSearchTerm(`${tenant.first_name} ${tenant.last_name}`);
    setIsDropdownOpen(false);
  };

  const handleCreateNewTenant = () => {
    setIsDropdownOpen(false);
    setShowTenantModal(true);
  };

  const handleTenantSaved = (newTenant) => {
    setShowTenantModal(false);
    setAvailableTenants(prev => [newTenant, ...prev]);
    handleSelectTenant(newTenant);
  };

  // FILE UPLOAD MODE: Parse the lease file
  const handleAnalyzeLease = async () => {
    if (!file || !formData.property_id) {
      setError("Please select a property and upload a lease file.");
      return;
    }

      setIsLoading(true);
      setError(null);

    try {
      // Create FormData for file upload
      const uploadFormData = new FormData();
      uploadFormData.append('file', file);

      // Parse the lease file
      const parsedData = await parseLease(uploadFormData);
      console.log("Parsed lease data:", parsedData);

      // Upload PDF to blob storage if it's a PDF
      let fileUrl = null;
      if (file.type === 'application/pdf') {
        fileUrl = await uploadLeasePDF(file);
        setParsedFileUrl(fileUrl);
      }

      // Load available tenants for matching
      const tenantsForMatching = await loadTenantsForProperty(formData.property_id);

      // Try to find a matching tenant by name
      let matchedTenant = null;
      if (parsedData.tenant_name) {
        const nameToMatch = parsedData.tenant_name.toLowerCase();
        matchedTenant = tenantsForMatching.find(tenant => {
          const fullName = `${tenant.first_name} ${tenant.last_name}`.toLowerCase();
          return fullName.includes(nameToMatch) || nameToMatch.includes(fullName);
        });
      }

      // Update form with parsed data
      setFormData(prev => ({
        ...prev,
        monthly_rent: parsedData.monthly_rent || prev.monthly_rent,
        security_deposit: parsedData.security_deposit || prev.security_deposit,
        start_date: parsedData.start_date || prev.start_date,
        end_date: parsedData.end_date || prev.end_date,
        tenant_id: matchedTenant?.id || prev.tenant_id,
      }));

      if (matchedTenant) {
        setSelectedTenant(matchedTenant);
        setTenantSearchTerm(`${matchedTenant.first_name} ${matchedTenant.last_name}`);
      }

      // Try to match unit if parsed
      if (parsedData.unit && availableUnits.length > 0) {
        const matchedUnit = availableUnits.find(
          unit => unit.name.toLowerCase() === parsedData.unit.toLowerCase()
        );
        if (matchedUnit) {
          setFormData(prev => ({...prev, unit_id: matchedUnit.id}));
        }
      }

      setShowParsedResults(true);
    } catch (err) {
      console.error("Failed to analyze lease:", err);
      
      // Provide more user-friendly error messages
      let errorMessage = "Failed to analyze lease file. Please try again.";
      
      if (err.message) {
        if (err.message.includes("No text could be extracted")) {
          errorMessage = "This PDF appears to be an image or doesn't contain selectable text. Please try uploading a different PDF file with selectable text.";
        } else if (err.message.includes("document could not be processed")) {
          errorMessage = err.message; // Already user-friendly
        } else if (err.message.includes("Failed to parse JSON")) {
          errorMessage = "The document analysis service is temporarily unavailable. Please try again in a few moments.";
        } else if (err.message.includes("Authentication") || err.message.includes("401")) {
          errorMessage = "Session expired. Please refresh the page and try again.";
        } else {
          errorMessage = err.message;
        }
      }
      
      setError(errorMessage);
    } finally {
      setIsLoading(false);
    }
  };

  const validateForm = () => {
    const errors = {};

    if (!formData.property_id) errors.property_id = "Property is required";
    if (!formData.unit_id && mode !== 'manual') errors.unit_id = "Unit is required";
    if (!formData.tenant_id) errors.tenant_id = "Tenant is required";
    if (!formData.start_date) errors.start_date = "Start date is required";
    if (!formData.end_date) errors.end_date = "End date is required";
    if (!formData.monthly_rent) errors.monthly_rent = "Monthly rent is required";
    if (!formData.security_deposit) errors.security_deposit = "Security deposit is required";

    // Date validation
    if (formData.start_date && formData.end_date) {
      const start = new Date(formData.start_date);
      const end = new Date(formData.end_date);
      if (start > end) {
        errors.end_date = "End date must be after start date";
      }
    }

    return errors;
  };

  const handleSubmitLease = async () => {
    // Validate form
    const errors = validateForm();
    if (Object.keys(errors).length > 0) {
      setFieldErrors(errors);
      setError("Please correct the validation errors below.");
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      // Prepare lease data with NaN checks
      const parseIntSafe = (value) => {
        const parsed = Number.parseInt(value);
        return isNaN(parsed) ? null : parsed;
      };
      
      const parseFloatSafe = (value) => {
        const parsed = Number.parseFloat(value);
        return isNaN(parsed) ? null : parsed;
      };

      const leaseData = {
        property_id: parseIntSafe(formData.property_id),
        unit_id: formData.unit_id ? parseIntSafe(formData.unit_id) : null,
        tenant_id: parseIntSafe(formData.tenant_id),
        start_date: formData.start_date,
        end_date: formData.end_date,
        monthly_rent: parseFloatSafe(formData.monthly_rent),
        security_deposit: parseFloatSafe(formData.security_deposit),
        rent_due_day: parseIntSafe(formData.rent_due_day || 1),
        late_fee_amount: formData.late_fee_amount ? parseFloatSafe(formData.late_fee_amount) : null,
        late_fee_after_days: formData.late_fee_after_days ? parseIntSafe(formData.late_fee_after_days) : null,
        special_terms: formData.special_terms || null,
        status: "ACTIVE",
        file_url: parsedFileUrl,
      };

      console.log("Creating lease with data:", leaseData);
      const createdLease = await createLease(leaseData);
      console.log("Lease created successfully:", createdLease);

      // Call the onImport callback
      onImport(createdLease);
      onClose();
    } catch (err) {
      console.error("Failed to create lease:", err);
      setError(err.message || "Failed to create lease. Please try again.");
    } finally {
      setIsLoading(false);
    }
  };

  const filteredTenants = availableTenants.filter(
    (t) =>
      `${t.first_name} ${t.last_name}`.toLowerCase().includes(tenantSearchTerm.toLowerCase()) ||
      (t.email && t.email.toLowerCase().includes(tenantSearchTerm.toLowerCase()))
  );

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setIsDropdownOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const renderFormFields = () => (
    <div className="space-y-4">
      {/* Property Selection */}
      <div>
        <Label htmlFor="property_id" required>Property</Label>
        <Select 
          name="property_id" 
          id="property_id" 
          value={formData.property_id} 
          onChange={handleFormChange}
          disabled={initialPropertyId && mode === 'manual'}
          required
        >
          <option value="">Choose a property</option>
          {properties.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
        </Select>
        {fieldErrors.property_id && (
          <p className="mt-1 text-sm text-red-600">{fieldErrors.property_id}</p>
        )}
      </div>

      {/* Unit Selection */}
      <div>
        <Label htmlFor="unit_id" required={mode !== 'manual'}>Unit</Label>
        {mode === 'manual' && initialUnitId ? (
          <Input 
            value={initialUnitName} 
            disabled 
            className="bg-gray-50"
          />
        ) : (
          <div className="relative">
            <Select
              id="unit_id"
              name="unit_id"
              value={formData.unit_id}
              onChange={handleFormChange}
              disabled={isLoadingUnits || !formData.property_id}
              required={mode !== 'manual'}
              className={isLoadingUnits ? "pr-12" : ""}
            >
              <option value="">
                {isLoadingUnits 
                  ? "Loading units..." 
                  : !formData.property_id 
                    ? "Select property first" 
                    : availableUnits.length === 0
                      ? "No available units"
                      : "Select a unit"
                }
              </option>
              {availableUnits.map(unit => (
                <option key={unit.id} value={unit.id}>
                  {unit.name || unit.unit_number || `Unit ${unit.id}`}
                </option>
              ))}
            </Select>
            {isLoadingUnits && (
              <div className="absolute inset-y-0 right-2 flex items-center">
                <svg className="animate-spin h-4 w-4 text-gray-500" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
              </div>
            )}
          </div>
        )}
        {fieldErrors.unit_id && (
          <p className="mt-1 text-sm text-red-600">{fieldErrors.unit_id}</p>
        )}
      </div>

      {/* Tenant Selection */}
      <div ref={dropdownRef}>
        <Label htmlFor="tenant-search" required>Tenant</Label>
        <div className="relative">
          <Input 
            id="tenant-search" 
            type="text" 
            placeholder="Search for existing tenant or create new" 
            value={tenantSearchTerm} 
            onChange={(e) => {
              setTenantSearchTerm(e.target.value);
              setIsDropdownOpen(true);
            }} 
            onFocus={() => setIsDropdownOpen(true)}
          />
          {isDropdownOpen && (
            <div className="absolute z-10 mt-1 w-full bg-white shadow-lg rounded-md border max-h-48 overflow-y-auto">
              {isLoadingTenants ? (
                <div className="p-2 text-sm text-gray-500 dark:text-gray-400 transition-colors flex items-center">
                  <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-gray-500 dark:text-gray-400" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                  Loading tenants...
                </div>
              ) : (
                <ul>
                  {filteredTenants.map(t => (
                    <li 
                      key={t.id} 
                      onClick={() => handleSelectTenant(t)} 
                      className="p-2 hover:bg-gray-100 cursor-pointer text-sm"
                    >
                      {t.first_name} {t.last_name}
                      {t.email && <span className="text-gray-500 ml-2">({t.email})</span>}
                    </li>
                  ))}
                  <li 
                    onClick={handleCreateNewTenant} 
                    className="p-2 hover:bg-gray-100 cursor-pointer text-sm font-semibold text-blue-600 border-t"
                  >
                    + Create New Tenant
                  </li>
                </ul>
              )}
            </div>
          )}
        </div>
        {fieldErrors.tenant_id && (
          <p className="mt-1 text-sm text-red-600">{fieldErrors.tenant_id}</p>
        )}
      </div>

      {/* Lease Terms */}
      <div className="grid grid-cols-2 gap-4">
        <div>
          <Label htmlFor="start_date" required>Start Date</Label>
          <Input 
            name="start_date" 
            id="start_date" 
            type="date" 
            value={formData.start_date} 
            onChange={handleFormChange}
          />
          {fieldErrors.start_date && (
            <p className="mt-1 text-sm text-red-600">{fieldErrors.start_date}</p>
          )}
        </div>
        <div>
          <Label htmlFor="end_date" required>End Date</Label>
          <Input 
            name="end_date" 
            id="end_date" 
            type="date" 
            value={formData.end_date} 
            onChange={handleFormChange}
          />
          {fieldErrors.end_date && (
            <p className="mt-1 text-sm text-red-600">{fieldErrors.end_date}</p>
          )}
        </div>
      </div>

      {/* Financial Terms */}
      <div className="grid grid-cols-2 gap-4">
        <div>
          <Label htmlFor="monthly_rent" required>Monthly Rent ($)</Label>
          <Input 
            name="monthly_rent" 
            id="monthly_rent" 
            type="number" 
            step="0.01"
            placeholder="1500" 
            value={formData.monthly_rent} 
            onChange={handleFormChange}
          />
          {fieldErrors.monthly_rent && (
            <p className="mt-1 text-sm text-red-600">{fieldErrors.monthly_rent}</p>
          )}
        </div>
        <div>
          <Label htmlFor="security_deposit" required>Security Deposit ($)</Label>
          <Input 
            name="security_deposit" 
            id="security_deposit" 
            type="number" 
            step="0.01"
            placeholder="1500" 
            value={formData.security_deposit} 
            onChange={handleFormChange}
          />
          {fieldErrors.security_deposit && (
            <p className="mt-1 text-sm text-red-600">{fieldErrors.security_deposit}</p>
          )}
        </div>
      </div>

      {/* Additional Terms */}
      <div className="grid grid-cols-3 gap-4">
        <div>
          <Label htmlFor="rent_due_day">Rent Due Day</Label>
          <Input 
            name="rent_due_day" 
            id="rent_due_day" 
            type="number" 
            min="1" 
            max="31"
            value={formData.rent_due_day} 
            onChange={handleFormChange}
          />
        </div>
        <div>
          <Label htmlFor="late_fee_amount">Late Fee ($)</Label>
          <Input 
            name="late_fee_amount" 
            id="late_fee_amount" 
            type="number" 
            step="0.01"
            placeholder="50" 
            value={formData.late_fee_amount} 
            onChange={handleFormChange}
          />
        </div>
        <div>
          <Label htmlFor="late_fee_after_days">Late After (Days)</Label>
          <Input 
            name="late_fee_after_days" 
            id="late_fee_after_days" 
            type="number" 
            min="1"
            placeholder="5" 
            value={formData.late_fee_after_days} 
            onChange={handleFormChange}
          />
        </div>
      </div>

      {/* Special Terms */}
      <div>
        <Label htmlFor="special_terms">Special Terms</Label>
        <TextArea 
          name="special_terms" 
          id="special_terms" 
          rows={3}
          placeholder="Any special conditions or notes..."
          value={formData.special_terms} 
          onChange={handleFormChange}
        />
      </div>
    </div>
  );

  return (
    <>
      <AnimatePresence>
        {isOpen && !showTenantModal && (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black bg-opacity-50 backdrop-blur-sm z-[9999] flex items-center justify-center p-4"
            onClick={onClose}
          >
            <motion.div 
              className="relative w-full max-w-3xl bg-white dark:bg-gray-800 rounded-xl shadow-2xl max-h-[90vh] overflow-hidden flex flex-col z-[10000]"
              onClick={(e) => e.stopPropagation()}
            >
              {/* Header */}
              <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700 flex justify-between items-center">
                <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-100">Create New Lease</h2>
              <button
                  onClick={onClose}
                  type="button"
                  aria-label="Close"
                  className="text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 dark:focus:ring-offset-gray-800 rounded-full p-1"
                >
                  <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" role="img">
                    <title>Close modal</title>
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
              </button>
            </div>

              {/* Mode Selector - Only show if not locked to a specific mode */}
              {!initialPropertyId && (
                <div className="p-6 border-b border-gray-200 dark:border-gray-700">
                  <div className="grid grid-cols-2 gap-4">
                    <div 
                      onClick={() => {setMode('file'); setShowParsedResults(false);}} 
                      role="button"
                      tabIndex={0}
                      onKeyDown={(e) => { if (e.key === 'Enter') { setMode('file'); setShowParsedResults(false); } }}
                      className={`p-4 border-2 rounded-lg cursor-pointer text-center ${
                        mode === 'file' ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20' : 'border-gray-300 dark:border-gray-600 hover:border-gray-400 dark:hover:border-gray-500'
                      }`}
                    >
                      <i className="fas fa-file-upload text-2xl text-blue-600 dark:text-blue-400 mb-2"></i>
                      <h3 className="font-semibold text-gray-900 dark:text-gray-100">File Upload</h3>
                      <p className="text-xs text-gray-500 dark:text-gray-400">Upload lease PDF to parse</p>
                    </div>
                    <div 
                      onClick={() => {setMode('manual'); setShowParsedResults(false);}} 
                      role="button"
                      tabIndex={0}
                      onKeyDown={(e) => { if (e.key === 'Enter') { setMode('manual'); setShowParsedResults(false); } }}
                      className={`p-4 border-2 rounded-lg cursor-pointer text-center ${
                        mode === 'manual' ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20' : 'border-gray-300 dark:border-gray-600 hover:border-gray-400 dark:hover:border-gray-500'
                      }`}
                    >
                      <i className="fas fa-keyboard text-2xl text-blue-600 dark:text-blue-400 mb-2"></i>
                      <h3 className="font-semibold text-gray-900 dark:text-gray-100">Manual Entry</h3>
                      <p className="text-xs text-gray-500 dark:text-gray-400">Enter lease details directly</p>
                    </div>
                  </div>
                </div>
              )}
              
              {/* Form Area */}
              <div className="flex-1 overflow-y-auto p-6 bg-white dark:bg-gray-800">
                {error && <ErrorMessage message={error} />}

                {/* File Upload Mode */}
                {mode === 'file' && !showParsedResults && (
                  <div className="space-y-4">
                    <div>
                      <Label htmlFor="file-property_id" required>Property</Label>
                      <Select 
                        name="property_id" 
                        id="file-property_id" 
                        value={formData.property_id} 
                        onChange={handleFormChange}
                        required
                      >
                        <option value="">Choose a property</option>
                        {properties.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
                      </Select>
                    </div>

                      <div>
                      <Label htmlFor="lease-file" required>Lease Document</Label>
                      <input
                        id="lease-file"
                        type="file"
                        accept=".pdf"
                        onChange={(e) => {
                          const files = e.target?.files;
                          setFile(files && files.length > 0 ? files[0] : null);
                        }}
                        className="w-full border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 rounded-md px-3 py-2 text-sm file:mr-4 file:py-1 file:px-4 file:rounded-md file:border-0 file:text-sm file:font-medium file:bg-blue-50 dark:file:bg-blue-900/20 file:text-blue-700 dark:file:text-blue-400 hover:file:bg-blue-100 dark:hover:file:bg-blue-900/30"
                      />
                      {file && (
                        <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">
                          Selected: {file.name}
                        </p>
                          )}
                        </div>

                  </div>
                )}

                {/* Show parsed results or manual entry form */}
                {(mode === 'manual' || showParsedResults) && renderFormFields()}
                  </div>

              {/* Footer */}
              <div className="px-6 py-4 bg-gray-50 dark:bg-gray-700 border-t border-gray-200 dark:border-gray-600 flex justify-end space-x-3">
                <Button variant="secondary" onClick={onClose}>Cancel</Button>
                {mode === 'file' && !showParsedResults ? (
                  <Button 
                    variant="primary" 
                    onClick={handleAnalyzeLease} 
                    disabled={!file || !formData.property_id || isLoading}
                    isLoading={isLoading}
                  >
                    Parse Lease
              </Button>
                ) : (
                  <Button 
                    variant="primary" 
                    onClick={handleSubmitLease} 
                    disabled={!formData.tenant_id || isLoading}
                    isLoading={isLoading}
                  >
                    Create Lease
                  </Button>
                )}
            </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Tenant Modal */}
      <AnimatePresence>
        {showTenantModal && (
          <TenantModal
            isOpen={true} 
            onClose={() => setShowTenantModal(false)}
            onSave={handleTenantSaved} 
            propertyId={formData.property_id}
          />
        )}
      </AnimatePresence>
    </>
  );
};

export default ImportLeaseModal;
