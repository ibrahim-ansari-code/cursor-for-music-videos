import { AnimatePresence, motion } from "framer-motion";
import React, { useEffect, useState } from "react";
import {
  fetchProperties,
  fetchPropertyUnits,
  fetchTenants,
  getCurrentUser,
  parseLease,
  uploadLeasePDF,
} from "../utils/api";
import ConfirmLeaseModal from "./ConfirmLeaseModal";
import TenantModal from "./TenantModal";
import {
  Label,
  Input,
  Button,
  ErrorMessage,
  FormSection,
} from "./ui/SharedModalComponents";
import LoadingSpinner from "./LoadingSpinner";

const ImportLeaseModal = ({ isOpen, onClose, onImport }) => {
  const [properties, setProperties] = useState([]);
  const [selectedProperty, setSelectedProperty] = useState("");
  const [tenants, setTenants] = useState([]);
  const [selectedTenant, setSelectedTenant] = useState(null);
  const [searchTerm, setSearchTerm] = useState("");
  const [file, setFile] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [leaseData, setLeaseData] = useState({
    monthly_rent: "",
    start_date: "",
    end_date: "",
    security_deposit: "",
    tenant_name: "",
    unit: "",
  });
  const [isCreatingNewTenant, setIsCreatingNewTenant] = useState(false);
  const [isLoadingTenants, setIsLoadingTenants] = useState(false);
  const [tenantLoadError, setTenantLoadError] = useState(null);
  const [showTenantModal, setShowTenantModal] = useState(false);
  const [showConfirmLeaseModal, setShowConfirmLeaseModal] = useState(false);
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const [propertySearchTerm, setPropertySearchTerm] = useState("");
  const [tenantData, setTenantData] = useState({});
  const [createdTenant, setCreatedTenant] = useState(null);
  const [availableUnits, setAvailableUnits] = useState([]);
  const [isLoadingUnits, setIsLoadingUnits] = useState(false);

  // Load properties on component mount
  useEffect(() => {
    const loadProperties = async () => {
      try {
        const data = await fetchProperties();
        setProperties(data);
      } catch (error) {
        console.error("Failed to fetch properties:", error);
        setError("Failed to load properties. Please try again.");
      }
    };

    const validateUserPermissions = async () => {
      try {
        // Check current user permissions from server
        const userInfo = await getCurrentUser();

        // Get and log the user type we got from the server
        const userType = userInfo.user_type?.toUpperCase();
        console.log("Current user type from server:", userType);

        // Also check what we have in localStorage
        const localUserType = localStorage.getItem("user_type");
        const localUser = JSON.parse(localStorage.getItem("user") || "{}");
        console.log("User type from localStorage:", localUserType);
        console.log("User object from localStorage:", localUser);

        // Validate against uppercase values to match the enum
        if (userType !== "LANDLORD" && userType !== "ADMIN") {
          setError(
            "Your account doesn't have permission to create leases. Please contact an administrator."
          );
        } else {
          // Ensure we have the correct uppercase value in localStorage
          localStorage.setItem("user_type", userType);

          // Update the user object too if it exists
          if (localUser && localUser.id) {
            localUser.user_type = userType;
            localStorage.setItem("user", JSON.stringify(localUser));
          }
        }
      } catch (error) {
        console.error("Failed to validate user permissions:", error);
        setError(
          "Unable to verify your permissions. Please refresh the page and try again."
        );
      }
    };

    if (isOpen) {
      loadProperties();
      validateUserPermissions();
    }
  }, [isOpen]);

  // Load tenants when property is selected
  useEffect(() => {
    const loadTenants = async () => {
      if (selectedProperty) {
        setIsLoadingTenants(true);
        setTenantLoadError(null);
        try {
          // Fetch ALL tenants the user can see, not just by selectedProperty for the dropdown
          const data = await fetchTenants({});
          setTenants(data);
          setError(null); // Clear any previous general errors

          // Now fetch units for this property
          await loadUnits(selectedProperty);
        } catch (error) {
          console.error("Failed to fetch tenants:", error);
          setTenantLoadError("Failed to load tenants. Please try again.");
        } finally {
          setIsLoadingTenants(false);
        }
      } else {
        setTenants([]);
        setSelectedTenant(null);
        setTenantLoadError(null);
        setAvailableUnits([]);
      }
    };

    loadTenants();
  }, [selectedProperty]);

  // Fetch available units for a property
  const loadUnits = async (propertyId) => {
    if (!propertyId) return;

    setIsLoadingUnits(true);
    try {
      const units = await fetchPropertyUnits(propertyId);
      console.log("Available units:", units);
      setAvailableUnits(units || []);
    } catch (error) {
      console.error("Failed to fetch units for property:", error);
      // Don't set an error for the user, just log it
    } finally {
      setIsLoadingUnits(false);
    }
  };

  useEffect(() => {
    const handleClickOutside = (event) => {
      if (dropdownOpen && !event.target.closest(".tenant-dropdown")) {
        setDropdownOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, [dropdownOpen]);

  const handleFileSelect = (e) => {
    const selectedFile = e.target.files[0];
    if (selectedFile && selectedFile.type === "application/pdf") {
      setFile(selectedFile);
      setError(null);
    } else {
      alert("Please select a PDF file");
      setFile(null);
    }
  };

  const handleFileDrop = (e) => {
    e.preventDefault();
    const selectedFile = e.dataTransfer.files[0];
    if (selectedFile && selectedFile.type === "application/pdf") {
      setFile(selectedFile);
      setError(null);
    } else {
      alert("Please drop a PDF file");
      setFile(null);
    }
  };

  const handleImportClick = async () => {
    try {
      setIsLoading(true);
      setError(null);

      // First, upload the PDF file to Azure Blob Storage
      console.log("Uploading lease PDF to Azure Blob Storage...");
      const fileUrl = await uploadLeasePDF(file);
      console.log("Lease PDF uploaded successfully, URL:", fileUrl);

      // Analyze the lease to get LLM data
      const formData = new FormData();
      formData.append("file", file);
      formData.append("property_id", selectedProperty);

      console.log("Calling parseLease API endpoint...");
      const response = await parseLease(formData);
      console.log("Lease parse successful:", response);

      // Store the complete lease data needed for creation
      const extractedLeaseData = {
        monthly_rent: parseFloat(response.monthly_rent || 0),
        security_deposit: parseFloat(response.security_deposit || 0),
        start_date: response.start_date,
        end_date: response.end_date,
        property_id: parseInt(selectedProperty),
        is_renewable: true,
        auto_renew: false,
        rent_due_day: 1,
        late_fee_amount: null,
        late_fee_after_days: null,
        special_terms: null,
        unit: response.unit || "",
        file_url: fileUrl, // Add the file URL to lease data
      };
      console.log("Storing lease data:", extractedLeaseData);
      setLeaseData(extractedLeaseData);

      // Set tenant data from LLM extracted information
      const tenantData = {
        full_name: response.tenant_name,
        first_name: "",
        last_name: "",
        phone: "", // This will be filled in by the user in TenantModal
        email: "", // This will be filled in by the user in TenantModal
        current_property_id: parseInt(selectedProperty),
        unit: response.unit || "",
        lease_start: response.start_date,
        lease_end: response.end_date,
        monthly_rent: response.monthly_rent?.toString() || "0",
        status: "Active",
      };

      // Split the full name into first and last name
      if (response.tenant_name) {
        const nameParts = response.tenant_name.split(" ");
        tenantData.first_name = nameParts[0] || "";
        tenantData.last_name = nameParts.slice(1).join(" ") || "";
      }

      // Find unitId based on unit name if available
      let unitId = null;
      if (response.unit && availableUnits && availableUnits.length > 0) {
        const matchedUnit = availableUnits.find(
          (unit) => unit.name.toLowerCase() === response.unit.toLowerCase()
        );
        if (matchedUnit) {
          unitId = matchedUnit.id;
          tenantData.unit_id = unitId;
          console.log(
            `Found matching unit ID ${unitId} for unit name ${response.unit}`
          );
        }
      }

      console.log("Setting tenant data:", tenantData);
      setTenantData(tenantData);

      // If creating a new tenant, show the tenant modal first
      if (isCreatingNewTenant) {
        setShowTenantModal(true);
      } else if (selectedTenant) {
        // If an existing tenant is selected, show the confirm lease modal
        setCreatedTenant(selectedTenant);
        setShowConfirmLeaseModal(true);
      }
    } catch (error) {
      console.error("Error analyzing lease:", error);
      setError(error.message || "Failed to analyze lease. Please try again.");
    } finally {
      setIsLoading(false);
    }
  };

  const handleTenantSave = (tenant) => {
    console.log("Received created tenant from TenantModal:", tenant);
    setError(null);
    setCreatedTenant(tenant);
    setShowTenantModal(false);

    // Show the confirm lease modal after tenant is created
    setShowConfirmLeaseModal(true);
  };

  const handleLeaseSubmit = (lease) => {
    console.log("Lease created successfully:", lease);
    onImport();
    onClose();
  };

  const filteredTenants = tenants.filter((tenant) => {
    // Check if tenant has any active leases
    const hasActiveLease =
      tenant.leases && tenant.leases.some((lease) => lease.status === "ACTIVE");

    // If tenant has an active lease, exclude them
    if (hasActiveLease) {
      return false;
    }

    // Existing search term filtering
    const tenantName = tenant.name || tenant.full_name || "";
    const tenantEmail = tenant.email || "";

    return (
      tenantName.toLowerCase().includes(searchTerm.toLowerCase()) ||
      tenantEmail.toLowerCase().includes(searchTerm.toLowerCase())
    );
  });

  // Handle closing the modal with cleanup
  const handleClose = () => {
    // Reset states when closing
    setError(null);
    setTenantLoadError(null);
    setSelectedTenant(null);
    setCreatedTenant(null);
    setShowTenantModal(false);
    setShowConfirmLeaseModal(false);

    // Call the parent's onClose
    onClose();
  };

  if (!isOpen) return null;

  // Define animation variants for modal transitions
  const modalVariants = {
    hidden: { opacity: 0, scale: 0.95 },
    visible: {
      opacity: 1,
      scale: 1,
      transition: {
        type: "spring",
        stiffness: 300,
        damping: 30,
      },
    },
    exit: {
      opacity: 0,
      scale: 0.95,
      transition: {
        duration: 0.15,
      },
    },
  };

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 bg-black bg-opacity-30 backdrop-blur-sm overflow-y-auto h-full w-full z-50 flex items-center justify-center p-4"
    >
      <AnimatePresence mode="wait">
        {!showTenantModal && !showConfirmLeaseModal && (
          <motion.div
            key="importModal"
            variants={modalVariants}
            initial="hidden"
            animate="visible"
            exit="exit"
            className="relative w-full max-w-2xl bg-white rounded-xl shadow-2xl overflow-hidden"
          >
            <div className="sticky top-0 z-10 px-6 py-4 bg-white border-b border-gray-200 flex justify-between items-center">
              <h2 className="text-xl font-semibold text-gray-900">
                Import Lease
              </h2>
              <button
                onClick={handleClose}
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

            <div className="p-6 max-h-[calc(100vh-12rem)] overflow-y-auto">
              <AnimatePresence>
                {error && <ErrorMessage message={error} />}
              </AnimatePresence>

              <form className="space-y-6">
                <FormSection
                  title="Property & Tenant Selection"
                  containerClass="space-y-6"
                  titleClass="text-lg font-semibold text-gray-900 pb-1 border-b border-gray-200"
                >
                  <div className="space-y-4">
                    <div>
                      <Label htmlFor="property" required>
                        Select Property
                      </Label>
                      <div className="relative tenant-dropdown">
                        <Input
                          type="text"
                          placeholder="Search or select property..."
                          value={propertySearchTerm}
                          onChange={(e) => {
                            setPropertySearchTerm(e.target.value);
                            setDropdownOpen("property");
                          }}
                        />
                        {dropdownOpen === "property" && (
                          <div className="absolute z-10 mt-1 w-full bg-white shadow-lg rounded-lg border border-gray-200">
                            <ul className="max-h-60 overflow-auto rounded-md py-1 text-base ring-1 ring-black ring-opacity-5 focus:outline-none sm:text-sm">
                              {properties
                                .filter((property) =>
                                  property.name
                                    .toLowerCase()
                                    .includes(propertySearchTerm.toLowerCase())
                                )
                                .map((property) => (
                                  <li
                                    key={property.id}
                                    className="cursor-pointer select-none relative py-2 pl-3 pr-9 hover:bg-blue-50 transition-colors"
                                    onClick={() => {
                                      setSelectedProperty(property.id);
                                      setPropertySearchTerm(property.name);
                                      setDropdownOpen(false);
                                    }}
                                  >
                                    <span className="font-normal block truncate">
                                      {property.name}
                                    </span>
                                  </li>
                                ))}
                            </ul>
                          </div>
                        )}
                      </div>
                    </div>

                    {selectedProperty && (
                      <div>
                        <Label htmlFor="tenant" required>
                          Select or Create Tenant
                        </Label>
                        <div className="relative tenant-dropdown">
                          <Input
                            type="text"
                            placeholder="Search or create tenant..."
                            value={searchTerm}
                            onChange={(e) => {
                              setSearchTerm(e.target.value);
                              setDropdownOpen("tenant");
                            }}
                          />
                          {dropdownOpen === "tenant" && (
                            <div className="absolute z-10 mt-1 w-full bg-white shadow-lg rounded-lg border border-gray-200">
                              <ul className="max-h-60 overflow-auto rounded-md py-1 text-base ring-1 ring-black ring-opacity-5 focus:outline-none sm:text-sm">
                                {isLoadingTenants ? (
                                  <li className="text-gray-500 py-2 px-3 flex items-center">
                                    <LoadingSpinner message="Loading tenants..." />
                                  </li>
                                ) : filteredTenants.length > 0 ? (
                                  filteredTenants.map((tenant) => (
                                    <li
                                      key={tenant.id}
                                      className="cursor-pointer select-none relative py-2 pl-3 pr-9 hover:bg-blue-50 transition-colors"
                                      onClick={() => {
                                        setSelectedTenant(tenant);
                                        setSearchTerm(
                                          tenant.name || tenant.full_name
                                        );
                                        setIsCreatingNewTenant(false);
                                        setDropdownOpen(false);
                                      }}
                                    >
                                      <span className="font-normal block truncate">
                                        {tenant.name || tenant.full_name}{" "}
                                        {tenant.email
                                          ? `(${tenant.email})`
                                          : ""}
                                      </span>
                                    </li>
                                  ))
                                ) : (
                                  <li className="text-gray-500 py-2 px-3">
                                    No tenants found
                                  </li>
                                )}
                                <li
                                  className="cursor-pointer select-none relative py-2 pl-3 pr-9 hover:bg-blue-50 transition-colors border-t border-gray-100"
                                  onClick={() => {
                                    setIsCreatingNewTenant(true);
                                    setSelectedTenant(null);
                                    setSearchTerm("Create New Tenant");
                                    setDropdownOpen(false);
                                  }}
                                >
                                  <span className="font-normal block truncate text-blue-600">
                                    + Create New Tenant
                                  </span>
                                </li>
                              </ul>
                            </div>
                          )}
                        </div>
                      </div>
                    )}
                  </div>
                </FormSection>

                <FormSection
                  title="Upload Lease Document"
                  containerClass="space-y-6"
                  titleClass="text-lg font-semibold text-gray-900 pb-1 border-b border-gray-200"
                >
                  <div
                    onDrop={handleFileDrop}
                    onDragOver={(e) => e.preventDefault()}
                    className="border-2 border-dashed border-gray-300 rounded-lg p-8 text-center cursor-pointer hover:bg-gray-50 transition-colors"
                    onClick={() => document.getElementById("fileInput").click()}
                  >
                    {file ? (
                      <div className="flex flex-col items-center">
                        <svg
                          className="h-12 w-12 text-green-500 mb-2"
                          xmlns="http://www.w3.org/2000/svg"
                          fill="none"
                          viewBox="0 0 24 24"
                          stroke="currentColor"
                        >
                          <path
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            strokeWidth={2}
                            d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
                          />
                        </svg>
                        <span className="text-sm font-medium text-gray-900">
                          {file.name}
                        </span>
                        <span className="text-xs text-gray-500 mt-1">
                          Click to change file
                        </span>
                      </div>
                    ) : (
                      <div className="flex flex-col items-center">
                        <svg
                          className="h-12 w-12 text-gray-400 mb-2"
                          xmlns="http://www.w3.org/2000/svg"
                          fill="none"
                          viewBox="0 0 24 24"
                          stroke="currentColor"
                        >
                          <path
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            strokeWidth={2}
                            d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"
                          />
                        </svg>
                        <span className="text-sm font-medium text-gray-900">
                          Click to select or drop lease PDF here
                        </span>
                        <span className="text-xs text-gray-500 mt-1">
                          Only PDF files are accepted
                        </span>
                      </div>
                    )}
                    <input
                      type="file"
                      id="fileInput"
                      accept=".pdf"
                      onChange={handleFileSelect}
                      style={{ display: "none" }}
                    />
                  </div>
                </FormSection>
              </form>
            </div>

            <div className="sticky bottom-0 z-10 px-6 py-4 bg-white border-t border-gray-200 flex justify-end space-x-3">
              <Button type="button" variant="secondary" onClick={handleClose}>
                Cancel
              </Button>
              <Button
                type="button"
                variant="primary"
                onClick={handleImportClick}
                disabled={
                  !file ||
                  !selectedProperty ||
                  (!selectedTenant && !isCreatingNewTenant) ||
                  isLoading
                }
              >
                {isLoading ? (
                  <>
                    <LoadingSpinner message="Importing..." />
                  </>
                ) : (
                  "Import"
                )}
              </Button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Tenant Modal for creating a new tenant */}
      <AnimatePresence>
        {showTenantModal && (
          <TenantModal
            isOpen={showTenantModal}
            onClose={() => setShowTenantModal(false)}
            tenant={tenantData}
            onSave={handleTenantSave}
            source="importLeaseModal"
            propertyId={parseInt(selectedProperty)}
            unitId={tenantData.unit_id}
            unitName={tenantData.unit}
          />
        )}
      </AnimatePresence>

      {/* Confirm Lease Modal */}
      <AnimatePresence>
        {showConfirmLeaseModal && (
          <ConfirmLeaseModal
            isOpen={showConfirmLeaseModal}
            onClose={() => setShowConfirmLeaseModal(false)}
            leaseData={leaseData}
            tenant={createdTenant}
            onSubmit={handleLeaseSubmit}
            availableUnits={availableUnits}
          />
        )}
      </AnimatePresence>

      {/* Loading overlay */}
      <AnimatePresence>
        {isLoading && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="absolute inset-0 bg-white bg-opacity-75 flex items-center justify-center"
          >
            <LoadingSpinner message="Processing lease..." />
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
};

export default ImportLeaseModal;
