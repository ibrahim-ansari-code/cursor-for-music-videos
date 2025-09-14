import React, { useState, useEffect, useRef, useMemo } from "react";
import { toast } from "react-toastify";
import { reportError } from "../utils/error-reporting";
import ImportLeaseModal from "../components/leases/ImportLeaseModal";
import UpdateLeaseStatusModal from "../components/leases/UpdateLeaseStatusModal";
import FilePreviewModal from "../components/FilePreviewModal";
import EditLeaseModal from "../components/leases/EditLeaseModal";
import { LeasesTableSkeleton } from "../components/ui/skeletons";
import { 
  useLeasesWithDocuments, 
  useDeleteLease, 
  useUploadLeaseDocument 
} from "../hooks/useLeases";

const Leases = () => {
  // Local UI state
  const [selectedLease, setSelectedLease] = useState(null);
  const [showModal, setShowModal] = useState(false);
  const [modalType, setModalType] = useState(null);
  const [statusFilter, setStatusFilter] = useState("all");
  const [uploadFile, setUploadFile] = useState(null);
  const [uploadDocumentType, setUploadDocumentType] = useState("contract");
  const [openDocumentDropdown, setOpenDocumentDropdown] = useState(null);
  const [dropdownPositionClass, setDropdownPositionClass] = useState("top-full mt-2");
  const documentButtonRefs = useRef({});
  const [fileToPreviewUrl, setFileToPreviewUrl] = useState(null);
  const [filePreviewName, setFilePreviewName] = useState("");
  const [showFilePreviewModal, setShowFilePreviewModal] = useState(false);
  const tableScrollContainerRef = useRef(null);

  // Build query parameters
  const queryParams = useMemo(() => {
    const params = {};
    if (statusFilter !== "all") {
      params.status = statusFilter;
    }
    return params;
  }, [statusFilter]);

  // TanStack Query hooks
  const { data: leases = [], isLoading: loading, error } = useLeasesWithDocuments(queryParams);
  const deleteLeaseMutation = useDeleteLease();
  const uploadDocumentMutation = useUploadLeaseDocument();

  // Helper function for dropdown positioning
  const calculateDropdownPosition = (
    buttonRect,
    scrollContainerRect,
    itemCount
  ) => {
    if (!buttonRect || !scrollContainerRect) {
      return "top-full mt-2"; // Default position if refs are not available
    }

    const spaceBelowInContainer =
      scrollContainerRect.bottom - buttonRect.bottom;
    const spaceAboveInContainer = buttonRect.top - scrollContainerRect.top;

    const itemHeight = 36; // Approximate height of a dropdown item
    const dropdownPaddingAndBorder = 10; // Approximate padding and border height
    const dynamicDropdownApproxHeight =
      itemCount * itemHeight + dropdownPaddingAndBorder;
    const buffer = 10; // Buffer to prevent cutting off

    if (
      spaceBelowInContainer - buffer < dynamicDropdownApproxHeight &&
      (spaceAboveInContainer - buffer > dynamicDropdownApproxHeight ||
        spaceAboveInContainer > spaceBelowInContainer)
    ) {
      return "bottom-0 mb-1"; // Position above if not enough space below
    }
    return "top-full mt-2"; // Default position below
  };



  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (openDocumentDropdown && !event.target.closest(".document-dropdown")) {
        setOpenDocumentDropdown(null);
      }
    };

    document.addEventListener("mousedown", handleClickOutside);
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, [openDocumentDropdown]);



  const handleShowModal = (type, lease = null) => {
    setModalType(type);
    setSelectedLease(lease);
    setShowModal(true);
  };

  const handleCloseModal = () => {
    setShowModal(false);
    setSelectedLease(null);
    setUploadFile(null);
    setUploadDocumentType("contract");
    setShowFilePreviewModal(false);
    setFileToPreviewUrl(null);
    setFilePreviewName("");
  };

  const handleFileChange = (e) => {
    const files = e.target?.files;
    if (files && files.length > 0) {
      setUploadFile(files[0]);
    } else {
      setUploadFile(null);
    }
  };

  const handleUploadDocument = async (e) => {
    e.preventDefault();

    if (!uploadFile || !selectedLease) return;

    try {
      const formData = new FormData();
      formData.append("file", uploadFile);
      formData.append("document_type", uploadDocumentType);

      await uploadDocumentMutation.mutateAsync({ 
        leaseId: selectedLease.id, 
        formData 
      });

      handleCloseModal();
    } catch (err) {
      console.error("Error uploading document:", err);
    }
  };

  const getStatusBadgeClass = (status) => {
    switch (status.toLowerCase()) {
      case "active":
        return "badge-success";
      case "pending":
        return "badge-warning";
      case "expired":
      case "terminated":
        return "badge-danger";
      case "draft":
        return "badge-info";
      default:
        return "badge-info";
    }
  };

  const handleImport = () => {
    handleCloseModal();
  };

  // Get the tenant's full name or construct it from first and last name
  const getTenantName = (tenant) => {
    if (!tenant) return "No tenant assigned";
    if (tenant.full_name) return tenant.full_name;
    if (tenant.first_name || tenant.last_name) {
      return `${tenant.first_name || ""} ${tenant.last_name || ""}`.trim();
    }
    return `Tenant #${tenant.id}`;
  };

  // Get tenant initials for the avatar
  const getTenantInitials = (tenant) => {
    if (!tenant) return "T";

    if (tenant.full_name) {
      return tenant.full_name
        .split(" ")
        .map((n) => n[0])
        .join("")
        .toUpperCase();
    }

    if (tenant.first_name && tenant.last_name) {
      return (tenant.first_name[0] + tenant.last_name[0]).toUpperCase();
    }

    if (tenant.first_name) return tenant.first_name[0].toUpperCase();
    if (tenant.last_name) return tenant.last_name[0].toUpperCase();

    return "T";
  };

  const handleShowFilePreviewModal = (lease) => {
    if (lease?.file_url) {
      setFileToPreviewUrl(lease.file_url);
      const tenantName = getTenantName(lease.tenant) || "N/A";
      const propertyName =
        lease.property?.name || `Property #${lease.property_id}`;
      setFilePreviewName(`Lease: ${tenantName} - ${propertyName}`);
      setShowFilePreviewModal(true);
    }
  };

  const handlePreviewDocument = (lease, document) => {
    if (!document || !document.file_path) {
      console.error(
        "[handlePreviewDocument] Document or file_path is missing:",
        document
      );
      const errorMessage = "Cannot preview document: file path is missing.";
      setError(errorMessage);
      toast.error(errorMessage);
      setOpenDocumentDropdown(null);
      return;
    }

    const fileUrl = document.file_path;
    console.log('[handlePreviewDocument] Attempting to preview URL:', fileUrl);
    
    // Check if the URL is just the backend URL without a proper file path
    if (fileUrl === window.location.origin || fileUrl === import.meta.env.VITE_API_URL || fileUrl.includes('localhost:') || fileUrl === fileUrl.match(/^https?:\/\/[^\/]+\/?$/)) {
      console.error('Invalid file URL - appears to be just the backend URL:', fileUrl);
      toast.error('Document URL is invalid. Please re-upload the document.');
      setOpenDocumentDropdown(null);
      return;
    }

    // Open the preview modal with the document
    setFileToPreviewUrl(document.file_path);
    const tenantName = getTenantName(lease.tenant) || "N/A";
    const propertyName =
      lease.property?.name || `Property #${lease.property_id}`;
    const docType =
      document.document_type.charAt(0).toUpperCase() +
      document.document_type.slice(1);
    setFilePreviewName(`${docType}: ${tenantName} - ${propertyName}`);
    setShowFilePreviewModal(true);
    setOpenDocumentDropdown(null);
  };

  const toggleDocumentDropdown = (event, lease) => {
    const leaseId = lease.id;
    const currentButton = event.currentTarget;

    if (openDocumentDropdown === leaseId) {
      setOpenDocumentDropdown(null);
    } else {
      const positionClass = calculateDropdownPosition(
        currentButton?.getBoundingClientRect(),
        tableScrollContainerRef.current?.getBoundingClientRect(),
        lease.documents ? lease.documents.length : 1
      );
      setDropdownPositionClass(positionClass);
      setOpenDocumentDropdown(leaseId);
    }
  };

  const handleCloseFilePreviewModal = () => {
    setShowFilePreviewModal(false);
    setFileToPreviewUrl(null);
    setFilePreviewName("");
  };

  const handleLeaseUpdated = (updatedLease) => {
    setShowModal(false);
  };

  const handleDeleteLease = async (leaseId) => {
    if (
      !window.confirm(
        "Are you sure you want to delete this lease? This action cannot be undone. Associated payment records will be kept but unlinked from this lease."
      )
    ) {
      return;
    }

    try {
      await deleteLeaseMutation.mutateAsync(leaseId);
      toast.success("Lease deleted successfully.");
    } catch (err) {
      console.error("Error deleting lease:", err);
      const errorMessage =
        err.data?.detail ||
        err.message ||
        "Failed to delete lease. Please try again.";
      toast.error(errorMessage);
      reportError(err, {
        component: 'Leases',
        action: 'delete_lease',
        tags: { 
          feature: "leases", 
          operation: "delete" 
        },
        extra: { leaseId },
      }, 'error');
    }
  };

  if (loading && leases.length === 0) {
    return (
      <div className="p-6 flex flex-col">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-end mb-6">
          <div className="mt-3 sm:mt-0 flex flex-col sm:flex-row space-y-2 sm:space-y-0 sm:space-x-3">
            <div className="animate-pulse h-9 w-48 bg-gray-200 rounded"></div>
            <div className="animate-pulse h-9 w-32 bg-gray-200 rounded"></div>
          </div>
        </div>
        <LeasesTableSkeleton rowCount={8} />
      </div>
    );
  }

  return (
    <div className="p-6 flex flex-col">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-end mb-6">
        <div className="mt-3 sm:mt-0 flex flex-col sm:flex-row space-y-2 sm:space-y-0 sm:space-x-3">
          <div className="relative">
            <select
              className="block w-full rounded-md border-gray-300 pr-10 py-2 text-base focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
            >
              <option value="all">All Statuses</option>
              <option value="DRAFT">Draft</option>
              <option value="PENDING">Pending</option>
              <option value="ACTIVE">Active</option>
              <option value="EXPIRED">Expired</option>
              <option value="TERMINATED">Terminated</option>
              <option value="RENEWED">Renewed</option>
            </select>
          </div>

          <button
            onClick={() => handleShowModal("create")}
            className="inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
          >
            <i className="fas fa-plus mr-2"></i>
            New Lease
          </button>
        </div>
      </div>

      {error && (
        <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4">
          <p>{error}</p>
          <button
            onClick={() => window.location.reload()}
            className="mt-2 bg-red-500 hover:bg-red-700 text-white font-bold py-1 px-2 rounded text-sm"
          >
            Retry
          </button>
        </div>
      )}

      <div className="bg-white shadow rounded-lg overflow-hidden relative">
        <div
          ref={tableScrollContainerRef}
          className="overflow-x-auto overflow-y-auto max-h-[calc(100vh-300px)] sm:max-h-[calc(100vh-250px)] lg:max-h-[calc(100vh-200px)]"
        >
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th
                  scope="col"
                  className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
                >
                  Tenant
                </th>
                <th
                  scope="col"
                  className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
                >
                  Property
                </th>
                <th
                  scope="col"
                  className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
                >
                  Dates
                </th>
                <th
                  scope="col"
                  className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
                >
                  Rent
                </th>
                <th
                  scope="col"
                  className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider"
                >
                  Status
                </th>
                <th
                  scope="col"
                  className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider"
                >
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {leases.length > 0 ? (
                leases.map((lease) => (
                  <tr key={lease.id} className="hover:bg-gray-50">
                    <td className="px-6 py-4 whitespace-nowrap text-left">
                      <div className="flex items-center">
                        <div className="flex-shrink-0 h-10 w-10 rounded-full bg-gray-200 flex items-center justify-center text-gray-600">
                          {/* Tenant initials */}
                          {getTenantInitials(lease.tenant)}
                        </div>
                        <div className="ml-4">
                          <div className="text-sm font-medium text-gray-900">
                            {getTenantName(lease.tenant)}
                          </div>
                          <div className="text-sm text-gray-500">
                            {lease.tenant?.email || ""}
                          </div>
                        </div>
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-left">
                      <div className="text-sm text-gray-900">
                        {lease.property?.name ||
                          `Property #${lease.property_id}`}
                      </div>
                      <div className="text-sm text-gray-500">
                        {lease.unit?.name
                          ? `Unit: ${lease.unit.name}`
                          : lease.unit_id
                          ? `Unit ID: ${lease.unit_id}`
                          : "No unit specified"}
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-left">
                      <div className="text-sm text-gray-900">
                        {new Date(lease.start_date).toLocaleDateString()} -{" "}
                        {new Date(lease.end_date).toLocaleDateString()}
                      </div>
                      <div className="text-sm text-gray-500">
                        {Math.round(
                          (new Date(lease.end_date) -
                            new Date(lease.start_date)) /
                            (1000 * 60 * 60 * 24 * 30)
                        )}{" "}
                        months
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-left">
                      <div className="text-sm text-gray-900">
                        ${Number(lease.monthly_rent).toFixed(2)}/month
                      </div>
                      <div className="text-sm text-gray-500">
                        Due: Day {lease.rent_due_day}
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="flex items-center justify-center">
                        <span
                          className={`badge ${getStatusBadgeClass(lease.status)}`}
                        >
                          {lease.status.charAt(0).toUpperCase() +
                            lease.status.slice(1).toLowerCase()}
                        </span>
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-center text-sm font-medium">
                      <div className="flex items-center justify-center space-x-2">
                        {/* Documents dropdown or upload button */}
                        {lease.documents && lease.documents.length > 0 ? (
                          <div className="relative document-dropdown">
                            <button
                              type="button"
                              ref={(el) =>
                                (documentButtonRefs.current[lease.id] = el)
                              }
                              onClick={(e) => toggleDocumentDropdown(e, lease)}
                              className="text-purple-600 hover:text-purple-800 p-1 rounded-md focus:outline-none focus:ring-2 focus:ring-purple-500 focus:ring-offset-1 transition-colors duration-150"
                              title={`View ${lease.documents.length} document${
                                lease.documents.length > 1 ? "s" : ""
                              }`}
                            >
                              <i className="fas fa-eye"></i>
                              {lease.documents.length > 1 && (
                                <span className="ml-1 text-xs bg-purple-100 text-purple-800 px-1.5 py-0.5 rounded-full">
                                  {lease.documents.length}
                                </span>
                              )}
                            </button>

                            {/* Dropdown menu */}
                            {openDocumentDropdown === lease.id && (
                              <div
                                className={`absolute right-0 w-56 rounded-md shadow-lg bg-white ring-1 ring-black ring-opacity-5 z-20 ${dropdownPositionClass}`}
                              >
                                <div className="py-1" role="menu">
                                  {lease.documents.map((doc, index) => (
                                    <button
                                      key={doc.id || index}
                                      type="button"
                                      onClick={() =>
                                        handlePreviewDocument(lease, doc)
                                      }
                                      className="w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 hover:text-gray-900 flex items-center justify-between"
                                      role="menuitem"
                                    >
                                      <span className="truncate">
                                        {doc.document_type
                                          .charAt(0)
                                          .toUpperCase() +
                                          doc.document_type.slice(1)}
                                      </span>
                                      <i className="fas fa-external-link-alt text-gray-400 text-xs"></i>
                                    </button>
                                  ))}
                                </div>
                              </div>
                            )}
                          </div>
                        ) : (
                          <button
                            type="button"
                            onClick={() => handleShowModal("upload", lease)}
                            className="text-green-600 hover:text-green-800 p-1 rounded-md focus:outline-none focus:ring-2 focus:ring-green-500 focus:ring-offset-1 transition-colors duration-150"
                            title="Upload document"
                          >
                            <i className="fas fa-file-upload"></i>
                          </button>
                        )}

                        {/* Edit button */}
                        <button
                          type="button"
                          onClick={() => handleShowModal("edit", lease)}
                          className="text-indigo-600 hover:text-indigo-800 p-1 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-1 transition-colors duration-150"
                          title="Edit lease"
                        >
                          <i className="fas fa-edit"></i>
                        </button>

                        {/* Status update button */}
                        <button
                          type="button"
                          onClick={() => handleShowModal("status", lease)}
                          className="text-blue-600 hover:text-blue-800 p-1 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-1 transition-colors duration-150"
                          title="Update status"
                        >
                          <i className="fas fa-tasks"></i>
                        </button>

                        {/* Delete button */}
                        <button
                          type="button"
                          onClick={() => handleDeleteLease(lease.id)}
                          className="text-red-600 hover:text-red-800 p-1 rounded-md focus:outline-none focus:ring-2 focus:ring-red-500 focus:ring-offset-1 transition-colors duration-150"
                          title="Delete lease"
                        >
                          <i className="fas fa-trash"></i>
                        </button>
                      </div>
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td
                    colSpan="6"
                    className="px-6 py-4 text-center text-sm text-gray-500"
                  >
                    No leases found
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Upload Document Modal */}
      {showModal && modalType === "upload" && selectedLease && (
        <div className="fixed inset-0 overflow-y-auto z-50 flex items-center justify-center">
          <div className="fixed inset-0 bg-black bg-opacity-50"></div>
          <div className="relative bg-white rounded-lg max-w-md w-full mx-auto p-6">
            <div className="flex justify-between items-center mb-4">
              <h3 className="text-lg font-medium">Upload Lease Document</h3>
              <button
                onClick={handleCloseModal}
                className="text-gray-400 hover:text-gray-500"
              >
                <i className="fas fa-times"></i>
              </button>
            </div>

            <form onSubmit={handleUploadDocument}>
              <div className="mb-4">
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Document Type
                </label>
                <select
                  className="block w-full border-gray-300 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
                  value={uploadDocumentType}
                  onChange={(e) => setUploadDocumentType(e.target.value)}
                  required
                >
                  <option value="contract">Lease Contract</option>
                  <option value="addendum">Addendum</option>
                  <option value="notice">Notice</option>
                  <option value="inspection">Inspection Report</option>
                  <option value="other">Other</option>
                </select>
              </div>

              <div className="mb-4">
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  File
                </label>
                <input
                  type="file"
                  className="block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:text-sm file:font-medium file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100"
                  onChange={handleFileChange}
                  required
                />
              </div>

              <div className="mt-6 flex justify-end space-x-3">
                <button
                  type="button"
                  onClick={handleCloseModal}
                  className="inline-flex justify-center px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md shadow-sm hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={!uploadFile || uploadDocumentMutation.isPending}
                  className="inline-flex justify-center px-4 py-2 text-sm font-medium text-white bg-blue-600 border border-transparent rounded-md shadow-sm hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50"
                >
                  {uploadDocumentMutation.isPending ? "Uploading..." : "Upload"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Status Change Modal - Using the new component */}
      {showModal && modalType === "status" && selectedLease && (
        <UpdateLeaseStatusModal
          isOpen={true}
          onClose={handleCloseModal}
          lease={selectedLease}
          onUpdate={handleLeaseUpdated}
        />
      )}

      {/* Import Lease Modal */}
      {showModal && modalType === "create" && (
        <ImportLeaseModal
          isOpen={showModal}
          onClose={handleCloseModal}
          onImport={handleImport}
        />
      )}

      {/* Edit Lease Modal */}
      {showModal && modalType === "edit" && selectedLease && (
        <EditLeaseModal
          isOpen={showModal}
          onClose={handleCloseModal}
          lease={selectedLease}
          onLeaseUpdated={handleLeaseUpdated}
        />
      )}

      {/* Document Preview Modal - Updated to use FilePreviewModal */}
      {showFilePreviewModal && fileToPreviewUrl && (
        <FilePreviewModal
          isOpen={showFilePreviewModal}
          onClose={handleCloseFilePreviewModal}
          fileUrl={fileToPreviewUrl}
          fileName={filePreviewName}
        />
      )}
    </div>
  );
};

export default Leases;
