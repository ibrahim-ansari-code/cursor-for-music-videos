import React, { useState, useEffect } from "react";
import {
  fetchProperties,
  fetchPropertyUnits,
  fetchTenantsByProperty,
  uploadMaintenancePhoto,
} from "../../utils/api";
import {
  ModalShell,
  Label,
  Input,
  Select,
  Button,
} from "../ui/SharedModalComponents";
import LoadingSpinner from "../LoadingSpinner";
import { AnimatePresence, motion } from "framer-motion";

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
  const [formData, setFormData] = useState({});
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
    }
  }, [request, isOpen]);

  useEffect(() => {
    const loadProperties = async () => {
      setIsLoadingProperties(true);
      try {
        const props = await fetchProperties();
        setProperties(props);
      } catch (error) {
        console.error("Failed to load properties", error);
      }
      setIsLoadingProperties(false);
    };
    if (isOpen) {
      loadProperties();
    }
  }, [isOpen]);

  useEffect(() => {
    const loadUnitsAndTenants = async () => {
      if (formData.property_id) {
        setIsLoadingUnits(true);
        setIsLoadingTenants(true);
        try {
          const [unitData, tenantData] = await Promise.all([
            fetchPropertyUnits(formData.property_id),
            fetchTenantsByProperty(formData.property_id),
          ]);
          setUnits(unitData);
          setTenants(tenantData);

          const prevPropId = String(request?.property?.id ?? "");
          if (prevPropId !== String(formData.property_id)) {
            setFormData((f) => ({ ...f, unit_id: "", tenant_id: "" }));
          }
        } catch (error) {
          console.error("Failed to load units or tenants", error);
          setUnits([]);
          setTenants([]);
        }
        setIsLoadingUnits(false);
        setIsLoadingTenants(false);
      } else {
        setUnits([]);
        setTenants([]);
        setFormData((f) => ({ ...f, unit_id: "", tenant_id: "" }));
      }
    };
    if (isOpen && formData.property_id) {
      loadUnitsAndTenants();
    }
  }, [isOpen, formData.property_id, request]);

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData({ ...formData, [name]: value });
  };

  const handleFileChange = async (e) => {
    const files = Array.from(e.target.files);
    setSelectedFiles(files);
    setPhotoUploadError(null);
    setPhotoUploadProgress(Array(files.length).fill("pending"));
    setUploadingPhotos(true);
    
    try {
      // Create upload promises for all files simultaneously
      const uploadPromises = files.map((file, index) => 
        uploadMaintenancePhoto(file)
          .then(url => {
            // Update progress for this specific file on success
            setPhotoUploadProgress(prev => {
              const next = [...prev];
              next[index] = "done";
              return next;
            });
            return { success: true, url, index };
          })
          .catch(err => {
            // Update progress for this specific file on error
            setPhotoUploadProgress(prev => {
              const next = [...prev];
              next[index] = "error";
              return next;
            });
            return { success: false, error: err.message || "Failed to upload photo", index };
          })
      );
      
      // Wait for all uploads to complete (both successful and failed)
      const results = await Promise.all(uploadPromises);
      
      // Extract successful URLs and collect errors
      const successfulUrls = [];
      const errors = [];
      
      results.forEach(result => {
        if (result.success) {
          successfulUrls.push(result.url);
        } else {
          errors.push(`File ${result.index + 1}: ${result.error}`);
        }
      });
      
      // Set the successful URLs
      setFormData(prev => ({ ...prev, photos: successfulUrls }));
      
      // Show errors if any occurred
      if (errors.length > 0) {
        setPhotoUploadError(`Upload errors: ${errors.join(', ')}`);
      }
      
    } catch (error) {
      // Handle unexpected errors
      setPhotoUploadError(error.message || "Unexpected error during upload");
    } finally {
      setUploadingPhotos(false);
    }
  };

  const handleRemoveFile = (idx) => {
    setSelectedFiles((prev) => prev.filter((_, i) => i !== idx));
    setFormData((prev) => ({
      ...prev,
      photos: (prev.photos ?? []).filter((_, i) => i !== idx),
    }));
  };

  const validateForm = () => {
    const errors = {};
    // Required fields
    if (!formData.property_id) errors.property_id = "Property is required";
    if (!formData.unit_id) errors.unit_id = "Unit is required";
    if (!formData.issue_title || formData.issue_title.trim() === "")
      errors.issue_title = "Issue title is required";
    if (!formData.scheduled_date)
      errors.scheduled_date = "Scheduled date is required";

    // Check if estimated_cost is positive
    if (formData.estimated_cost && Number(formData.estimated_cost) <= 0) {
      errors.estimated_cost = "Estimated cost must be a positive number";
    }

    // Check if scheduled_date is not in the past
    if (formData.scheduled_date) {
      const today = new Date();
      today.setHours(0, 0, 0, 0);
      const scheduledDate = new Date(formData.scheduled_date);

      if (scheduledDate < today) {
        errors.scheduled_date = "Scheduled date cannot be in the past";
      }
    }

    return errors;
  };

  const handleBlur = (e) => {
    const { name } = e.target;
    setTouched((prev) => ({ ...prev, [name]: true }));
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    setError(null);
    const errors = validateForm();
    setFieldErrors(errors);
    setTouched((prev) => ({
      ...prev,
      ...Object.keys(errors).reduce((acc, k) => {
        acc[k] = true;
        return acc;
      }, {}),
    }));
    if (Object.keys(errors).length > 0) {
      setError("Please correct the highlighted fields.");
      return;
    }
    if (uploadingPhotos) {
      setError("Please wait for all photos to finish uploading.");
      return;
    }
    if (!isViewing) {
      onSubmit(formData).catch((err) => {
        setError(err?.message || "Failed to save the request.");
      });
    } else {
      onClose();
    }
  };

  if (!isOpen) return null;

  const renderField = (label, value) => (
    <div className="flex flex-col gap-1">
      <Label>{label}</Label>
      <div className="bg-gray-50 border border-gray-200 rounded-md px-3 py-2 text-gray-700 min-h-[40px]">
        {value || <span className="text-gray-400">—</span>}
      </div>
    </div>
  );

  const formContent = isViewing ? (
    <div className="space-y-5 w-full">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {renderField(
          "Property",
          properties.find((p) => String(p.id) === String(formData.property_id))?.name
        )}
        {renderField(
          "Unit",
          units.find((u) => u.id === formData.unit_id)?.unit_number ||
            units.find((u) => u.id === formData.unit_id)?.name
        )}
        {renderField("Issue Title", formData.issue_title)}
        {renderField("Description", formData.description)}
        {renderField("Priority", formData.priority)}
        {renderField("Status", formData.status)}
        {renderField("Assign To", formData.assigned_to)}
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
              (tenants.find((t) => t.id === formData.tenant_id)?.first_name ||
                "") +
              " " +
              (tenants.find((t) => t.id === formData.tenant_id)?.last_name ||
                "")
            ).trim()
        )}
        {formData.photos && formData.photos.length > 0
          ? renderField(
              "Photos",
              <ul className="space-y-1">
                {formData.photos.map((url, idx) => (
                  <li key={idx} className="flex items-center gap-2">
                    <a
                      href={typeof url === "string" ? url : "#"}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-blue-600 underline"
                    >
                      Photo {idx + 1}
                    </a>
                    <Button
                      type="button"
                      variant="secondary"
                      className="text-xs py-1 px-2"
                      onClick={() =>
                        setShowPhotoPreviewIdx(
                          idx === showPhotoPreviewIdx ? null : idx
                        )
                      }
                    >
                      {showPhotoPreviewIdx === idx ? (
                        <>
                          <i className="fas fa-eye-slash mr-1" /> Hide Preview
                        </>
                      ) : (
                        <>
                          <i className="fas fa-eye mr-1" /> Preview
                        </>
                      )}
                    </Button>
                  </li>
                ))}
              </ul>
            )
          : renderField("Photos", null)}
      </div>
      <AnimatePresence>
        {showPhotoPreviewIdx !== null &&
          formData.photos &&
          formData.photos[showPhotoPreviewIdx] && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: "24rem" }}
              exit={{ opacity: 0, height: 0 }}
              transition={{ duration: 0.3, ease: "easeInOut" }}
              className="mt-3 border rounded-lg overflow-hidden shadow bg-gray-50"
            >
              {(() => {
                const url = formData.photos[showPhotoPreviewIdx];
                const lowerUrl = url.toLowerCase();
                if (
                  lowerUrl.endsWith(".png") ||
                  lowerUrl.endsWith(".jpg") ||
                  lowerUrl.endsWith(".jpeg") ||
                  lowerUrl.endsWith(".gif")
                ) {
                  return (
                    <img
                      src={url}
                      alt={`Photo Preview ${showPhotoPreviewIdx + 1}`}
                      className="w-full h-full object-contain p-1"
                    />
                  );
                } else if (lowerUrl.endsWith(".pdf")) {
                  const pdfDisplayUrl = `${url}#view=FitH`;
                  return (
                    <iframe
                      src={pdfDisplayUrl}
                      title={`Photo Preview ${showPhotoPreviewIdx + 1}`}
                      className="w-full h-full border-0"
                    />
                  );
                } else {
                  return (
                    <iframe
                      src={url}
                      title={`Photo Preview ${showPhotoPreviewIdx + 1}`}
                      className="w-full h-full border-0"
                    />
                  );
                }
              })()}
            </motion.div>
          )}
      </AnimatePresence>
    </div>
  ) : (
    <form
      onSubmit={handleSubmit}
      className="space-y-5 w-full"
      id="maintenance-request-form"
    >
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Property Dropdown */}
        <div>
          <Label htmlFor="property_id" required>
            Property
          </Label>
          <Select
            name="property_id"
            id="property_id"
            value={formData.property_id || ""}
            onChange={handleChange}
            onBlur={handleBlur}
            required
            disabled={isViewing || isLoadingProperties}
            className={
              fieldErrors.property_id && touched.property_id
                ? "border-red-500"
                : ""
            }
          >
            <option value="">
              {isLoadingProperties ? "Loading..." : "Select Property"}
            </option>
            {properties.map((p) => (
              <option key={p.id} value={p.id}>
                {p.name}
              </option>
            ))}
          </Select>
          {fieldErrors.property_id && touched.property_id && (
            <p className="mt-1 text-sm text-red-600">
              {fieldErrors.property_id}
            </p>
          )}
        </div>
        {/* Unit Dropdown */}
        <div>
          <Label htmlFor="unit_id" required>
            Unit
          </Label>
          <Select
            name="unit_id"
            id="unit_id"
            value={formData.unit_id || ""}
            onChange={handleChange}
            onBlur={handleBlur}
            required
            disabled={isViewing || !formData.property_id || isLoadingUnits}
            className={
              fieldErrors.unit_id && touched.unit_id ? "border-red-500" : ""
            }
          >
            <option value="">
              {isLoadingUnits ? "Loading..." : "Select Unit"}
            </option>
            {units.map((u) => (
              <option key={u.id} value={u.id}>
                {u.unit_number || u.name}
              </option>
            ))}
          </Select>
          {fieldErrors.unit_id && touched.unit_id && (
            <p className="mt-1 text-sm text-red-600">{fieldErrors.unit_id}</p>
          )}
        </div>
        {/* Issue Title */}
        <div className="md:col-span-2">
          <Label htmlFor="issue_title" required>
            Issue Title
          </Label>
          <Input
            type="text"
            name="issue_title"
            id="issue_title"
            value={formData.issue_title || ""}
            onChange={handleChange}
            onBlur={handleBlur}
            required
            disabled={isViewing || isLoadingProperties}
            className={
              fieldErrors.issue_title && touched.issue_title
                ? "border-red-500"
                : ""
            }
          />
          {fieldErrors.issue_title && touched.issue_title && (
            <p className="mt-1 text-sm text-red-600">
              {fieldErrors.issue_title}
            </p>
          )}
        </div>
        {/* Description */}
        <div className="md:col-span-2">
          <Label htmlFor="description">Description</Label>
          <Input
            as="textarea"
            name="description"
            id="description"
            value={formData.description || ""}
            onChange={handleChange}
            rows={3}
            disabled={isViewing || isLoadingProperties}
          />
        </div>
        {/* Priority */}
        <div>
          <Label htmlFor="priority">Priority</Label>
          <Select
            name="priority"
            id="priority"
            value={formData.priority || ""}
            onChange={handleChange}
            disabled={isViewing || isLoadingProperties}
          >
            <option value="Low">Low</option>
            <option value="Medium">Medium</option>
            <option value="High">High</option>
          </Select>
        </div>
        {/* Status */}
        <div>
          <Label htmlFor="status">Status</Label>
          <Select
            name="status"
            id="status"
            value={formData.status || ""}
            onChange={handleChange}
            disabled={isViewing || isLoadingProperties}
          >
            <option value="Pending">Pending</option>
            <option value="In Progress">In Progress</option>
            <option value="Scheduled">Scheduled</option>
            <option value="Completed">Completed</option>
            <option value="Cancelled">Cancelled</option>
          </Select>
        </div>
        {/* Assigned To */}
        <div>
          <Label htmlFor="assigned_to">Assign To</Label>
          <Input
            type="text"
            name="assigned_to"
            id="assigned_to"
            value={formData.assigned_to || ""}
            onChange={handleChange}
            placeholder="Name of person or company"
            disabled={isViewing || isLoadingProperties}
          />
        </div>
        {/* Scheduled Date */}
        <div>
          <Label htmlFor="scheduled_date">Scheduled Date</Label>
          <Input
            type="date"
            name="scheduled_date"
            id="scheduled_date"
            value={formData.scheduled_date || ""}
            onChange={handleChange}
            onBlur={handleBlur}
            disabled={isViewing || isLoadingProperties}
            className={
              fieldErrors.scheduled_date && touched.scheduled_date
                ? "border-red-500"
                : ""
            }
          />
          {fieldErrors.scheduled_date && touched.scheduled_date && (
            <p className="mt-1 text-sm text-red-600">
              {fieldErrors.scheduled_date}
            </p>
          )}
        </div>
        {/* Estimated Cost */}
        <div>
          <Label htmlFor="estimated_cost">Estimated Cost</Label>
          <Input
            type="number"
            name="estimated_cost"
            id="estimated_cost"
            value={formData.estimated_cost || ""}
            onChange={handleChange}
            placeholder="$"
            disabled={isViewing || isLoadingProperties}
          />
        </div>
        {/* Tenant */}
        <div>
          <Label htmlFor="tenant_id">Tenant</Label>
          <Select
            name="tenant_id"
            id="tenant_id"
            value={formData.tenant_id || ""}
            onChange={handleChange}
            disabled={isViewing || !formData.property_id || isLoadingTenants}
          >
            <option value="">
              {isLoadingTenants ? "Loading..." : "Select Tenant"}
            </option>
            {tenants.map((t) => (
              <option key={t.id} value={t.id}>
                {t.name ||
                  ((t.first_name || "") + " " + (t.last_name || "")).trim()}
              </option>
            ))}
          </Select>
        </div>
        {/* Photos - improved file input */}
        <div className="md:col-span-2">
          <Label htmlFor="photos">Photos</Label>
          <Input
            type="file"
            name="photos"
            id="photos"
            multiple
            className="block w-full text-sm file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100"
            disabled={isViewing || isLoadingProperties || uploadingPhotos}
            onChange={handleFileChange}
          />
          {uploadingPhotos && (
            <div className="mt-2 text-blue-600 text-sm">
              Uploading photos...
            </div>
          )}
          {photoUploadError && (
            <div className="mt-2 text-red-600 text-sm">{photoUploadError}</div>
          )}
          {formData.photos && formData.photos.length > 0 && (
            <ul className="mt-2 space-y-1">
              {formData.photos.map((url, idx) => (
                <li
                  key={idx}
                  className="flex items-center gap-2 bg-gray-50 px-3 py-1 rounded"
                >
                  <a
                    href={typeof url === "string" ? url : "#"}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="truncate max-w-xs text-blue-600 underline"
                  >
                    Photo {idx + 1}
                  </a>
                  <Button
                    type="button"
                    variant="secondary"
                    className="text-xs py-1 px-2"
                    onClick={() =>
                      setShowPhotoPreviewIdx(
                        idx === showPhotoPreviewIdx ? null : idx
                      )
                    }
                  >
                    {showPhotoPreviewIdx === idx ? (
                      <>
                        <i className="fas fa-eye-slash mr-1" /> Hide Preview
                      </>
                    ) : (
                      <>
                        <i className="fas fa-eye mr-1" /> Preview
                      </>
                    )}
                  </Button>
                </li>
              ))}
            </ul>
          )}
          <AnimatePresence>
            {showPhotoPreviewIdx !== null &&
              formData.photos &&
              formData.photos[showPhotoPreviewIdx] && (
                <motion.div
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: "24rem" }}
                  exit={{ opacity: 0, height: 0 }}
                  transition={{ duration: 0.3, ease: "easeInOut" }}
                  className="mt-3 border rounded-lg overflow-hidden shadow bg-gray-50"
                >
                  {(() => {
                    const url = formData.photos[showPhotoPreviewIdx];
                    const lowerUrl = url.toLowerCase();
                    if (
                      lowerUrl.endsWith(".png") ||
                      lowerUrl.endsWith(".jpg") ||
                      lowerUrl.endsWith(".jpeg") ||
                      lowerUrl.endsWith(".gif")
                    ) {
                      return (
                        <img
                          src={url}
                          alt={`Photo Preview ${showPhotoPreviewIdx + 1}`}
                          className="w-full h-full object-contain p-1"
                        />
                      );
                    } else if (lowerUrl.endsWith(".pdf")) {
                      const pdfDisplayUrl = `${url}#view=FitH`;
                      return (
                        <iframe
                          src={pdfDisplayUrl}
                          title={`Photo Preview ${showPhotoPreviewIdx + 1}`}
                          className="w-full h-full border-0"
                        />
                      );
                    } else {
                      return (
                        <iframe
                          src={url}
                          title={`Photo Preview ${showPhotoPreviewIdx + 1}`}
                          className="w-full h-full border-0"
                        />
                      );
                    }
                  })()}
                </motion.div>
              )}
          </AnimatePresence>
        </div>
      </div>
    </form>
  );

  const modalTitle = isViewing
    ? "View Maintenance Request"
    : request
    ? "Edit Maintenance Request"
    : "New Maintenance Request";

  const footerContent = isViewing ? (
    <Button
      type="button"
      variant="secondary"
      onClick={onClose}
      aria-label="Close modal"
    >
      Close
    </Button>
  ) : (
    <>
      <Button
        type="button"
        variant="secondary"
        onClick={onClose}
        disabled={isSubmitting || isLoadingProperties}
        aria-label="Cancel and close modal"
      >
        Cancel
      </Button>
      <Button
        type="submit"
        form="maintenance-request-form"
        variant="primary"
        isLoading={isSubmitting}
        loadingText={request ? "Updating..." : "Saving..."}
        disabled={isSubmitting || isLoadingProperties}
        aria-label={request ? "Update request" : "Create request"}
      >
        {request ? "Update Request" : "Create Request"}
      </Button>
    </>
  );

  return (
    <ModalShell
      isOpen={isOpen}
      onClose={onClose}
      title={modalTitle}
      aria-label={modalTitle}
      error={error}
      footerContent={footerContent}
    >
      {formContent}
    </ModalShell>
  );
};

export default MaintenanceRequestModal;
