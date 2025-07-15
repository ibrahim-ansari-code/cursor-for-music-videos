import React, { useState, useEffect } from "react";
import PropTypes from "prop-types";
import { AnimatePresence, motion } from "framer-motion";
import { v4 as uuidv4 } from "uuid";
import {
  fetchProperties,
  fetchPropertyUnits,
  fetchTenantsByProperty,
  uploadMaintenancePhoto,
} from "../../utils/api";
import LoadingSpinner from "../LoadingSpinner";

const initialFormState = {
  issue_title: "",
  description: "",
  priority: "Medium",
  status: "Pending",
  property_id: "",
  unit_id: "",
  tenant_id: "",
  assigned_to: "",
  scheduled_date: "",
  estimated_cost: "",
};

const MaintenanceRequestModal = ({
  isOpen,
  onClose,
  onSubmit,
  request,
  isViewing,
  isSubmitting,
}) => {
  const [formData, setFormData] = useState(initialFormState);
  const [properties, setProperties] = useState([]);
  const [units, setUnits] = useState([]);
  const [tenants, setTenants] = useState([]);
  const [isLoadingProperties, setIsLoadingProperties] = useState(false);
  const [isLoadingUnits, setIsLoadingUnits] = useState(false);
  const [isLoadingTenants, setIsLoadingTenants] = useState(false);
  const [error, setError] = useState(null);
  const [selectedFiles, setSelectedFiles] = useState([]);
  const [uploadingPhotos, setUploadingPhotos] = useState(false);
  const [photoUploadProgress, setPhotoUploadProgress] = useState([]);
  const [photoUploadError, setPhotoUploadError] = useState(null);
  const [showPhotoPreviewIdx, setShowPhotoPreviewIdx] = useState(null);
  const [fieldErrors, setFieldErrors] = useState({});
  const [touched, setTouched] = useState({});

  // Initialize form data
  useEffect(() => {
    if (isOpen) {
      if (request) {
        const scheduledDate = request.scheduled_date
          ? new Date(request.scheduled_date).toISOString().split("T")[0]
          : "";
        setFormData({
          ...initialFormState,
          ...request,
          property_id: request.property?.id || "",
          unit_id: request.unit?.id || "",
          tenant_id: request.tenant?.id || "",
          scheduled_date: scheduledDate,
        });
      } else {
        setFormData(initialFormState);
      }
      setFieldErrors({});
      setError(null);
      setTouched({});
      setSelectedFiles([]);
      setPhotoUploadProgress([]);
      setPhotoUploadError(null);
      setShowPhotoPreviewIdx(null);
    }
  }, [request, isOpen]);

  // Load properties
  useEffect(() => {
    const loadProperties = async () => {
      if (!isOpen) return;
      
      setIsLoadingProperties(true);
      try {
        const props = await fetchProperties();
        setProperties(props);
      } catch (error) {
        console.error("Failed to load properties", error);
        setError("Failed to load properties. Please try again.");
      } finally {
        setIsLoadingProperties(false);
      }
    };
    
    loadProperties();
  }, [isOpen]);

  // Load units and tenants when property changes
  useEffect(() => {
    const loadUnitsAndTenants = async () => {
      if (!formData.property_id) {
        setUnits([]);
        setTenants([]);
        setFormData((prev) => ({ ...prev, unit_id: "", tenant_id: "" }));
        return;
      }

      setIsLoadingUnits(true);
      setIsLoadingTenants(true);
      
      try {
        const [unitData, tenantData] = await Promise.all([
          fetchPropertyUnits(formData.property_id),
          fetchTenantsByProperty(formData.property_id),
        ]);
        
        setUnits(unitData);
        setTenants(tenantData);

        // Reset unit and tenant if property changed
        const prevPropId = String(request?.property?.id ?? "");
        if (prevPropId !== String(formData.property_id)) {
          setFormData((prev) => ({ ...prev, unit_id: "", tenant_id: "" }));
        }
      } catch (error) {
        console.error("Failed to load units or tenants", error);
        setUnits([]);
        setTenants([]);
      } finally {
        setIsLoadingUnits(false);
        setIsLoadingTenants(false);
      }
    };

    if (isOpen && formData.property_id) {
      loadUnitsAndTenants();
    }
  }, [isOpen, formData.property_id, request]);

  const validateField = (name, value) => {
    switch (name) {
      case "issue_title":
        if (!value || value.trim() === "") {
          return "Issue title is required";
        }
        break;
      case "property_id":
        if (!value) {
          return "Property is required";
        }
        break;
      case "estimated_cost":
        if (value) {
          const numValue = Number(value);
          if (isNaN(numValue) || numValue <= 0) {
            return "Estimated cost must be a positive number";
          }
        }
        break;
      case "scheduled_date":
        if (value) {
          const today = new Date();
          today.setHours(0, 0, 0, 0);
          const scheduledDate = new Date(`${value}T00:00:00`);
          
          if (isNaN(scheduledDate.getTime())) {
            return "Invalid date format";
          }
          if (scheduledDate < today) {
            return "Scheduled date cannot be in the past";
          }
        }
        break;
      default:
        break;
    }
    return null;
  };

  const handleBlur = (e) => {
    const { name, value } = e.target;
    setTouched((prev) => ({ ...prev, [name]: true }));
    
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
    setFormData((prev) => ({ ...prev, [name]: value }));
    
    // Clear error when user starts typing if field was touched
    if (touched[name]) {
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
    }
  };

  const handleFileChange = async (e) => {
    const files = Array.from(e.target.files);
    
    if (files.length === 0) return;
    
    // Validate files
    const maxFileSize = 10 * 1024 * 1024; // 10MB
    const allowedTypes = ['image/jpeg', 'image/png', 'image/gif', 'application/pdf'];
    const allowedExtensions = ['.jpg', '.jpeg', '.png', '.gif', '.pdf'];
    
    const invalidFiles = files.filter(file => {
      const fileExtension = file.name.toLowerCase().substring(file.name.lastIndexOf('.'));
      return file.size > maxFileSize || 
             !allowedTypes.includes(file.type) ||
             !allowedExtensions.includes(fileExtension);
    });
    
    if (invalidFiles.length > 0) {
      setPhotoUploadError('Some files are too large (max 10MB) or have invalid formats (JPG, PNG, GIF, PDF only)');
      return;
    }

    // Assign unique IDs to files
    const filesWithIds = files.map((file) => ({
      id: uuidv4(),
      file,
      name: file.name,
      size: file.size,
    }));
    
    setSelectedFiles((prev) => [...prev, ...filesWithIds]);
    setPhotoUploadError(null);
    setPhotoUploadProgress((prev) => [
      ...prev,
      ...filesWithIds.map((f) => ({ id: f.id, status: "pending" })),
    ]);
    setUploadingPhotos(true);

    try {
      // Upload files in parallel
      const uploadPromises = filesWithIds.map((fileObj) =>
        uploadMaintenancePhoto(fileObj.file)
          .then((url) => ({ id: fileObj.id, url, status: "done" }))
          .catch((err) => ({ id: fileObj.id, error: err.message || "Failed to upload", status: "error" }))
      );
      
      const results = await Promise.all(uploadPromises);
      
      // Process results
      const newPhotos = [];
      const errors = [];
      
      setPhotoUploadProgress((prevProgress) => {
        const updatedProgress = [...prevProgress];
        results.forEach((result) => {
          if (result.status === "done") {
            newPhotos.push({ id: result.id, url: result.url });
          } else {
            errors.push(`${result.error}`);
          }
        });
        return updatedProgress;
      });
      
      // Add successful uploads to form data
      if (newPhotos.length > 0) {
        setFormData((prev) => ({
          ...prev,
          photos: [...(prev.photos ?? []), ...newPhotos.map((p) => p.url)],
        }));
      }
      
      // Show errors if any
      if (errors.length > 0) {
        setPhotoUploadError(`Upload errors: ${errors.join(", ")}`);
      }
    } catch (error) {
      setPhotoUploadError(error.message || "Unexpected error during upload");
    } finally {
      setUploadingPhotos(false);
    }
  };

  const handleRemovePhoto = (identifier) => {
    setSelectedFiles((prev) => prev.filter((f) => f.id !== identifier && f.url !== identifier));
    setPhotoUploadProgress((prev) => prev.filter((p) => p.id !== identifier));
    setFormData((prev) => ({
      ...prev,
      photos: (prev.photos ?? []).filter((url) => url !== identifier),
    }));
  };

  const validateForm = () => {
    let isValid = true;
    const newErrors = {};

    // Required fields
    const requiredFields = ["issue_title", "property_id"];
    
    requiredFields.forEach((fieldName) => {
      const error = validateField(fieldName, formData[fieldName]);
      if (error) {
        newErrors[fieldName] = error;
        isValid = false;
      }
    });
    
    // Validate optional fields that have values
    ["estimated_cost", "scheduled_date"].forEach((fieldName) => {
      if (formData[fieldName]) {
        const error = validateField(fieldName, formData[fieldName]);
        if (error) {
          newErrors[fieldName] = error;
          isValid = false;
        }
      }
    });
    
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
    setError(null);
    
    if (!validateForm()) {
      return;
    }
    
    if (uploadingPhotos) {
      setError("Please wait for all photos to finish uploading.");
      return;
    }
    
    if (!isViewing) {
      try {
        // Prepare payload
        const payload = {
          issue_title: formData.issue_title.trim(),
          description: formData.description && formData.description.trim() !== "" 
            ? formData.description.trim() 
            : null,
          priority: formData.priority,
          status: formData.status,
          property_id: formData.property_id ? Number(formData.property_id) : null,
          unit_id: formData.unit_id && formData.unit_id !== "" && formData.unit_id !== "common_area"
            ? Number(formData.unit_id) 
            : null,
          tenant_id: formData.tenant_id && formData.tenant_id !== "" 
            ? Number(formData.tenant_id) 
            : null,
          assigned_to: formData.assigned_to && formData.assigned_to.trim() !== "" 
            ? formData.assigned_to.trim() 
            : null,
          scheduled_date: formData.scheduled_date && formData.scheduled_date.trim() !== "" 
            ? formData.scheduled_date 
            : null,
          estimated_cost: formData.estimated_cost && formData.estimated_cost !== "" 
            ? Number(formData.estimated_cost) 
            : null,
          photos: formData.photos && formData.photos.length > 0 
            ? formData.photos 
            : null,
        };
        
        await onSubmit(payload);
      } catch (err) {
        setError(err?.message || "Failed to save the request.");
      }
    } else {
      onClose();
    }
  };

  if (!isOpen) return null;

  const renderField = (label, value) => (
    <div className="flex flex-col gap-1">
      <label className="block text-sm font-medium text-gray-700">{label}</label>
      <div className="bg-gray-50 border border-gray-200 rounded-md px-3 py-2 text-gray-700 min-h-[40px] flex items-center">
        {value || <span className="text-gray-400">—</span>}
      </div>
    </div>
  );

  const modalTitle = isViewing
    ? "View Maintenance Request"
    : request
    ? "Edit Maintenance Request"
    : "New Maintenance Request";

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="fixed inset-0 bg-black bg-opacity-50 backdrop-blur-sm z-[9999] flex items-center justify-center p-4"
        onClick={onClose}
      >
        <motion.div 
          initial={{ scale: 0.9, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          exit={{ scale: 0.9, opacity: 0 }}
          transition={{ type: "spring", damping: 25, stiffness: 400 }}
          className="relative w-full max-w-4xl bg-white rounded-xl shadow-xl max-h-[90vh] overflow-hidden flex flex-col z-[10000]"
          onClick={(e) => e.stopPropagation()}
        >
          {/* Header */}
          <div className="relative px-6 py-4 bg-gradient-to-br from-brand-green to-brand-teal text-white">
            <div className="flex justify-between items-center">
              <div>
                <h2 className="text-xl font-semibold text-white">{modalTitle}</h2>
                <p className="text-white/80 mt-0.5 text-sm">
                  {isViewing 
                    ? "View maintenance request details" 
                    : request 
                    ? "Update maintenance request information"
                    : "Create a new maintenance request for your property"
                  }
                </p>
              </div>
              <button
                onClick={onClose}
                className="text-white/70 hover:text-white hover:bg-white/10 p-1.5 rounded-lg transition-all"
              >
                <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
          </div>

          {/* Content */}
          <div className="flex-1 overflow-y-auto bg-gray-50">
            {error && (
              <motion.div 
                initial={{ opacity: 0, y: -10 }}
                animate={{ opacity: 1, y: 0 }}
                className="mx-6 mt-4 p-3 bg-red-50 border border-red-100 text-red-700 rounded-lg"
              >
                <div className="flex">
                  <svg className="h-5 w-5 text-red-400 mr-2 flex-shrink-0 mt-0.5" viewBox="0 0 20 20" fill="currentColor">
                    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                  </svg>
                  <span className="text-sm">{error}</span>
                </div>
              </motion.div>
            )}

            {isViewing ? (
              <div className="p-6 space-y-4">
                {/* Property and Unit Information */}
                <div className="bg-white rounded-lg p-5 shadow-sm border border-gray-100">
                  <div className="flex items-center mb-3">
                    <div className="w-9 h-9 bg-blue-50 rounded-lg flex items-center justify-center mr-3">
                      <svg className="w-4 h-4 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" />
                      </svg>
                    </div>
                    <h3 className="text-base font-medium text-gray-900">Location Information</h3>
                  </div>
                  
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {renderField(
                      "Property",
                      properties.find((p) => String(p.id) === String(formData.property_id))?.name
                    )}
                    {renderField(
                      "Unit",
                      formData.unit_id && formData.unit_id !== "common_area"
                        ? units.find((u) => u.id === formData.unit_id)?.unit_number ||
                          units.find((u) => u.id === formData.unit_id)?.name
                        : "Common Area / Building-wide"
                    )}
                  </div>
                </div>

                {/* Request Details */}
                <div className="bg-white rounded-lg p-5 shadow-sm border border-gray-100">
                  <div className="flex items-center mb-3">
                    <div className="w-9 h-9 bg-orange-50 rounded-lg flex items-center justify-center mr-3">
                      <svg className="w-4 h-4 text-orange-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                      </svg>
                    </div>
                    <h3 className="text-base font-medium text-gray-900">Request Details</h3>
                  </div>
                  
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {renderField("Issue Title", formData.issue_title)}
                    {renderField("Priority", formData.priority)}
                    {renderField("Status", formData.status)}
                    {renderField("Assign To", formData.assigned_to)}
                  </div>
                  
                  <div className="mt-4">
                    {renderField("Description", formData.description)}
                  </div>
                </div>

                {/* Additional Information */}
                <div className="bg-white rounded-lg p-5 shadow-sm border border-gray-100">
                  <div className="flex items-center mb-3">
                    <div className="w-9 h-9 bg-green-50 rounded-lg flex items-center justify-center mr-3">
                      <svg className="w-4 h-4 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M9 7h6m0 10v-3m-3 3h.01M9 17h.01M9 14h.01M12 14h.01M15 11h.01M12 11h.01M9 11h.01M7 21h10a2 2 0 002-2V5a2 2 0 00-2-2H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
                      </svg>
                    </div>
                    <h3 className="text-base font-medium text-gray-900">Additional Information</h3>
                  </div>
                  
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {renderField(
                      "Scheduled Date",
                      formData.scheduled_date
                        ? new Date(formData.scheduled_date).toLocaleDateString()
                        : ""
                    )}
                    {renderField(
                      "Estimated Cost",
                      formData.estimated_cost ? `$${formData.estimated_cost}` : ""
                    )}
                    {renderField(
                      "Tenant",
                      tenants.find((t) => t.id === formData.tenant_id)?.name ||
                        (
                          (tenants.find((t) => t.id === formData.tenant_id)?.first_name || "") +
                          " " +
                          (tenants.find((t) => t.id === formData.tenant_id)?.last_name || "")
                        ).trim()
                    )}
                  </div>
                </div>

                {/* Photos */}
                {formData.photos && formData.photos.length > 0 && (
                  <div className="bg-white rounded-lg p-5 shadow-sm border border-gray-100">
                    <div className="flex items-center mb-3">
                      <div className="w-9 h-9 bg-purple-50 rounded-lg flex items-center justify-center mr-3">
                        <svg className="w-4 h-4 text-purple-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                          <path strokeLinecap="round" strokeLinejoin="round" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
                        </svg>
                      </div>
                      <h3 className="text-base font-medium text-gray-900">Photos</h3>
                    </div>
                    
                    <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                      {formData.photos.map((url, idx) => (
                        <div key={idx} className="relative group">
                          <div className="aspect-square bg-gray-100 rounded-lg overflow-hidden">
                            {url.toLowerCase().includes('.pdf') ? (
                              <div className="w-full h-full flex items-center justify-center bg-gray-100">
                                <svg className="w-8 h-8 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                                </svg>
                              </div>
                            ) : (
                              <img 
                                src={url} 
                                alt={`Photo ${idx + 1}`}
                                className="w-full h-full object-cover"
                              />
                            )}
                          </div>
                          <div className="absolute inset-0 bg-black bg-opacity-0 group-hover:bg-opacity-30 transition-all duration-200 rounded-lg flex items-center justify-center">
                            <a
                              href={url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="opacity-0 group-hover:opacity-100 text-white bg-black bg-opacity-50 px-3 py-1 rounded text-sm transition-opacity"
                            >
                              View Full
                            </a>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <form onSubmit={handleSubmit} className="p-6 space-y-4" id="maintenance-request-form">
                {/* Property and Unit Section */}
                <div className="bg-white rounded-lg p-5 shadow-sm border border-gray-100">
                  <div className="flex items-center mb-3">
                    <div className="w-9 h-9 bg-blue-50 rounded-lg flex items-center justify-center mr-3">
                      <svg className="w-4 h-4 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" />
                      </svg>
                    </div>
                    <h3 className="text-base font-medium text-gray-900">Location Information</h3>
                  </div>
                  
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        Property <span className="text-red-500">*</span>
                      </label>
                      <select
                        name="property_id"
                        value={formData.property_id || ""}
                        onChange={handleChange}
                        onBlur={handleBlur}
                        required
                        disabled={isLoadingProperties}
                        className={`w-full px-4 py-2.5 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all bg-white ${
                          fieldErrors.property_id && touched.property_id ? 'border-red-300' : 'border-gray-200'
                        }`}
                      >
                        <option value="">
                          {isLoadingProperties ? "Loading..." : "Select Property"}
                        </option>
                        {properties.map((p) => (
                          <option key={p.id} value={p.id}>
                            {p.name}
                          </option>
                        ))}
                      </select>
                      {fieldErrors.property_id && touched.property_id && (
                        <p className="mt-2 text-sm text-red-600">{fieldErrors.property_id}</p>
                      )}
                    </div>
                    
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        Unit
                      </label>
                      <select
                        name="unit_id"
                        value={formData.unit_id || ""}
                        onChange={handleChange}
                        onBlur={handleBlur}
                        disabled={!formData.property_id || isLoadingUnits}
                        className="w-full px-4 py-2.5 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all bg-white"
                      >
                        <option value="">
                          {isLoadingUnits ? "Loading..." : "Select Unit or leave blank for common area"}
                        </option>
                        <option value="common_area">
                          Common Area / Building-wide
                        </option>
                        {units.map((u) => (
                          <option key={u.id} value={u.id}>
                            {u.unit_number || u.name}
                          </option>
                        ))}
                      </select>
                      <p className="mt-1 text-xs text-gray-500">
                        Select "Common Area" for property-wide maintenance like parking lots, building exterior, etc.
                      </p>
                    </div>
                  </div>
                </div>

                {/* Request Details Section */}
                <div className="bg-white rounded-lg p-5 shadow-sm border border-gray-100">
                  <div className="flex items-center mb-3">
                    <div className="w-9 h-9 bg-orange-50 rounded-lg flex items-center justify-center mr-3">
                      <svg className="w-4 h-4 text-orange-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                      </svg>
                    </div>
                    <h3 className="text-base font-medium text-gray-900">Request Details</h3>
                  </div>
                  
                  <div className="space-y-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        Issue Title <span className="text-red-500">*</span>
                      </label>
                      <input
                        type="text"
                        name="issue_title"
                        value={formData.issue_title || ""}
                        onChange={handleChange}
                        onBlur={handleBlur}
                        required
                        placeholder="Brief description of the issue"
                        className={`w-full px-4 py-2.5 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all bg-white ${
                          fieldErrors.issue_title && touched.issue_title ? 'border-red-300' : 'border-gray-200'
                        }`}
                      />
                      {fieldErrors.issue_title && touched.issue_title && (
                        <p className="mt-2 text-sm text-red-600">{fieldErrors.issue_title}</p>
                      )}
                    </div>
                    
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        Description
                      </label>
                      <textarea
                        name="description"
                        value={formData.description || ""}
                        onChange={handleChange}
                        rows={3}
                        placeholder="Detailed description of the maintenance issue..."
                        className="w-full px-4 py-2.5 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all bg-white resize-none"
                      />
                    </div>
                    
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-2">
                          Priority
                        </label>
                        <select
                          name="priority"
                          value={formData.priority || ""}
                          onChange={handleChange}
                          className="w-full px-4 py-2.5 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all bg-white"
                        >
                          <option value="Low">Low</option>
                          <option value="Medium">Medium</option>
                          <option value="High">High</option>
                        </select>
                      </div>
                      
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-2">
                          Status
                        </label>
                        <select
                          name="status"
                          value={formData.status || ""}
                          onChange={handleChange}
                          className="w-full px-4 py-2.5 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all bg-white"
                        >
                          <option value="Pending">Pending</option>
                          <option value="In Progress">In Progress</option>
                          <option value="Scheduled">Scheduled</option>
                          <option value="Completed">Completed</option>
                          <option value="Cancelled">Cancelled</option>
                        </select>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Additional Information Section */}
                <div className="bg-white rounded-lg p-5 shadow-sm border border-gray-100">
                  <div className="flex items-center mb-3">
                    <div className="w-9 h-9 bg-green-50 rounded-lg flex items-center justify-center mr-3">
                      <svg className="w-4 h-4 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M9 7h6m0 10v-3m-3 3h.01M9 17h.01M9 14h.01M12 14h.01M15 11h.01M12 11h.01M9 11h.01M7 21h10a2 2 0 002-2V5a2 2 0 00-2-2H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
                      </svg>
                    </div>
                    <h3 className="text-base font-medium text-gray-900">Additional Information</h3>
                  </div>
                  
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        Assign To
                      </label>
                      <input
                        type="text"
                        name="assigned_to"
                        value={formData.assigned_to || ""}
                        onChange={handleChange}
                        placeholder="Name of person or company"
                        className="w-full px-4 py-2.5 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all bg-white"
                      />
                    </div>
                    
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        Scheduled Date
                      </label>
                      <input
                        type="date"
                        name="scheduled_date"
                        value={formData.scheduled_date || ""}
                        onChange={handleChange}
                        onBlur={handleBlur}
                        className={`w-full px-4 py-2.5 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all bg-white ${
                          fieldErrors.scheduled_date && touched.scheduled_date ? 'border-red-300' : 'border-gray-200'
                        }`}
                      />
                      {fieldErrors.scheduled_date && touched.scheduled_date && (
                        <p className="mt-2 text-sm text-red-600">{fieldErrors.scheduled_date}</p>
                      )}
                    </div>
                    
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        Estimated Cost
                      </label>
                      <input
                        type="number"
                        name="estimated_cost"
                        value={formData.estimated_cost || ""}
                        onChange={handleChange}
                        onBlur={handleBlur}
                        placeholder="0.00"
                        min="0"
                        step="0.01"
                        className={`w-full px-4 py-2.5 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all bg-white ${
                          fieldErrors.estimated_cost && touched.estimated_cost ? 'border-red-300' : 'border-gray-200'
                        }`}
                      />
                      {fieldErrors.estimated_cost && touched.estimated_cost && (
                        <p className="mt-2 text-sm text-red-600">{fieldErrors.estimated_cost}</p>
                      )}
                    </div>
                  </div>
                  
                  <div className="mt-4">
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Tenant
                    </label>
                    <select
                      name="tenant_id"
                      value={formData.tenant_id || ""}
                      onChange={handleChange}
                      disabled={!formData.property_id || isLoadingTenants}
                      className="w-full px-4 py-2.5 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all bg-white"
                    >
                      <option value="">
                        {isLoadingTenants ? "Loading..." : "Select Tenant (optional)"}
                      </option>
                      {tenants.map((t) => (
                        <option key={t.id} value={t.id}>
                          {t.name || ((t.first_name || "") + " " + (t.last_name || "")).trim()}
                        </option>
                      ))}
                    </select>
                  </div>
                </div>

                {/* Photos Section */}
                <div className="bg-white rounded-lg p-5 shadow-sm border border-gray-100">
                  <div className="flex items-center mb-3">
                    <div className="w-9 h-9 bg-purple-50 rounded-lg flex items-center justify-center mr-3">
                      <svg className="w-4 h-4 text-purple-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
                      </svg>
                    </div>
                    <h3 className="text-base font-medium text-gray-900">Photos</h3>
                  </div>
                  
                  <div>
                    <input
                      type="file"
                      name="photos"
                      multiple
                      accept="image/*,.pdf"
                      className="block w-full text-sm file:mr-4 file:py-2.5 file:px-4 file:rounded-lg file:border-0 file:text-sm file:font-medium file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100 file:cursor-pointer cursor-pointer border border-gray-200 rounded-lg"
                      disabled={uploadingPhotos}
                      onChange={handleFileChange}
                    />
                    <p className="mt-1 text-xs text-gray-500">
                      Upload images or PDFs (max 10MB each). Supported formats: JPG, PNG, GIF, PDF
                    </p>
                    
                    {uploadingPhotos && (
                      <div className="mt-2 text-blue-600 text-sm flex items-center">
                        <LoadingSpinner className="mr-2 h-4 w-4" />
                        Uploading photos...
                      </div>
                    )}
                    
                    {photoUploadError && (
                      <div className="mt-2 text-red-600 text-sm">{photoUploadError}</div>
                    )}
                    
                    {formData.photos && formData.photos.length > 0 && (
                      <div className="mt-4">
                        <h4 className="text-sm font-medium text-gray-700 mb-2">Uploaded Photos</h4>
                        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                          {formData.photos.map((url, idx) => (
                            <div key={idx} className="relative group">
                              <div className="aspect-square bg-gray-100 rounded-lg overflow-hidden border border-gray-200">
                                {url.toLowerCase().includes('.pdf') ? (
                                  <div className="w-full h-full flex items-center justify-center bg-gray-50">
                                    <svg className="w-6 h-6 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                                    </svg>
                                  </div>
                                ) : (
                                  <img 
                                    src={url} 
                                    alt={`Photo ${idx + 1}`}
                                    className="w-full h-full object-cover"
                                  />
                                )}
                              </div>
                              <button
                                type="button"
                                onClick={() => handleRemovePhoto(url)}
                                className="absolute -top-2 -right-2 bg-red-500 text-white rounded-full w-6 h-6 flex items-center justify-center text-xs hover:bg-red-600 transition-colors"
                              >
                                ×
                              </button>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              </form>
            )}
          </div>

          {/* Footer */}
          <div className="px-6 py-5 bg-gray-50 border-t border-gray-200">
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
              <div className="text-sm text-gray-500 flex items-start flex-1 sm:max-w-md">
                <svg className="w-4 h-4 mr-2 text-gray-400 mt-0.5 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                <span>
                  {isViewing ? (
                    "Viewing maintenance request details"
                  ) : (
                    <>
                      <span className="text-red-600 font-bold">*</span> Required fields. 
                      Unit selection is optional for common area maintenance.
                    </>
                  )}
                </span>
              </div>
              <div className="flex gap-3 flex-shrink-0 sm:items-center">
                <button
                  type="button"
                  onClick={onClose}
                  className="px-4 py-2.5 border border-gray-300 rounded-md text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-gray-500 focus:ring-offset-2 transition-all text-sm font-medium"
                  disabled={isSubmitting}
                >
                  {isViewing ? "Close" : "Cancel"}
                </button>
                {!isViewing && (
                  <button
                    onClick={handleSubmit}
                    className="px-5 py-2.5 bg-gradient-to-br from-brand-green to-brand-teal text-white rounded-md hover:from-brand-green/90 hover:to-brand-teal/90 focus:outline-none focus:ring-2 focus:ring-brand-green focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed transition-all text-sm font-medium flex items-center gap-2 min-w-[140px] justify-center shadow-sm"
                    disabled={isSubmitting || uploadingPhotos}
                  >
                    {isSubmitting ? (
                      <>
                        <svg className="animate-spin h-4 w-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                        </svg>
                        {request ? "Updating..." : "Creating..."}
                      </>
                    ) : (
                      request ? "Update Request" : "Create Request"
                    )}
                  </button>
                )}
              </div>
            </div>
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
};

MaintenanceRequestModal.propTypes = {
  isOpen: PropTypes.bool.isRequired,
  onClose: PropTypes.func.isRequired,
  onSubmit: PropTypes.func.isRequired,
  request: PropTypes.object,
  isViewing: PropTypes.bool,
  isSubmitting: PropTypes.bool,
};

export default MaintenanceRequestModal;
