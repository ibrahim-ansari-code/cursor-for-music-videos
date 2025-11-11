import React, { useState, useMemo, useEffect } from "react";
import { toast } from "react-toastify";
import * as Sentry from "@sentry/react";
import LeasesTable from "../components/leases/LeasesTable";
import LeaseFilters from "../components/leases/LeaseFilters";
import ImportLeaseModal from "../components/leases/ImportLeaseModal";
import UpdateLeaseStatusModal from "../components/leases/UpdateLeaseStatusModal";
import UploadLeaseDocumentModal from "../components/leases/UploadLeaseDocumentModal";
import DeleteLeaseConfirmationModal from "../components/leases/DeleteLeaseConfirmationModal";
import FilePreviewModal from "../components/FilePreviewModal";
import EditLeaseModal from "../components/leases/EditLeaseModal";
import {
  useLeasesWithDocuments,
  useDeleteLease,
  useBulkDeleteLeases,
} from "../hooks/useLeasesQueries";
import { getSecureDocumentUrl } from "../utils/api/leases";
import type {
  LeaseWithDocuments,
  LeaseDocument,
  LeaseActionHandlers,
  LeasesQueryParams,
} from "../types/lease";

type ModalType = "create" | "edit" | "status" | "upload" | null;

const LeasesContent: React.FC = () => {
  // Local UI state
  const [selectedLease, setSelectedLease] = useState<LeaseWithDocuments | null>(
    null
  );
  const [showModal, setShowModal] = useState(false);
  const [modalType, setModalType] = useState<ModalType>(null);
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [fileToPreviewUrl, setFileToPreviewUrl] = useState<string | null>(null);
  const [filePreviewName, setFilePreviewName] = useState("");
  const [showFilePreviewModal, setShowFilePreviewModal] = useState(false);
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [leaseToDelete, setLeaseToDelete] = useState<LeaseWithDocuments | null>(
    null
  );
  const [selectedLeaseIds, setSelectedLeaseIds] = useState<Set<number>>(
    new Set()
  );
  const [showBulkDeleteModal, setShowBulkDeleteModal] = useState(false);

  // Build query parameters
  const queryParams: LeasesQueryParams = useMemo(() => {
    const params: LeasesQueryParams = {};
    if (statusFilter !== "all") {
      params.status = statusFilter;
    }
    return params;
  }, [statusFilter]);

  // TanStack Query hooks
  const {
    data: leases = [],
    isLoading: loading,
    error,
  } = useLeasesWithDocuments(queryParams);
  const deleteLeaseMutation = useDeleteLease();
  const bulkDeleteLeasesMutation = useBulkDeleteLeases();

  // Clear selection when leases change (e.g., after filter changes or deletion)
  useEffect(() => {
    const currentLeaseIds = new Set(leases.map((l) => l.id));
    setSelectedLeaseIds((prev) => {
      const filtered = Array.from(prev).filter((id) => currentLeaseIds.has(id));
      return filtered.length !== prev.size ? new Set(filtered) : prev;
    });
  }, [leases]);

  // Modal handlers
  const handleShowModal = (
    type: ModalType,
    lease: LeaseWithDocuments | null = null
  ) => {
    Sentry.logger.trace("Opening modal", {
      modalType: type,
      leaseId: lease?.id,
    });
    setModalType(type);
    setSelectedLease(lease);
    setShowModal(true);
  };

  const handleCloseModal = () => {
    Sentry.logger.trace("Closing modal", { modalType });
    setShowModal(false);
    setSelectedLease(null);
    setShowFilePreviewModal(false);
    setFileToPreviewUrl(null);
    setFilePreviewName("");
  };

  const handleCloseFilePreviewModal = () => {
    Sentry.logger.trace("Closing file preview modal");
    setShowFilePreviewModal(false);
    setFileToPreviewUrl(null);
    setFilePreviewName("");
  };

  // Helper: Get tenant name
  const getTenantName = (lease: LeaseWithDocuments): string => {
    const { tenant } = lease;
    if (!tenant) return "No tenant assigned";
    if (tenant.full_name) return tenant.full_name;
    if (tenant.first_name || tenant.last_name) {
      return `${tenant.first_name || ""} ${tenant.last_name || ""}`.trim();
    }
    return `Tenant #${tenant.id}`;
  };

  // Action handlers for table
  const actionHandlers: LeaseActionHandlers = {
    onEdit: (lease) => {
      Sentry.startSpan(
        {
          op: "ui.click",
          name: "Edit Lease Button",
        },
        (span) => {
          span.setAttribute("leaseId", lease.id);
          span.setAttribute("leaseStatus", lease.status);
          handleShowModal("edit", lease);
        }
      );
    },

    onDelete: async (leaseId: number) => {
      // Find the full lease object for the confirmation modal
      const lease = leases.find((l) => l.id === leaseId);
      if (!lease) {
        Sentry.logger.error("Attempted to delete non-existent lease", {
          leaseId,
        });
        toast.error("Lease not found");
        return;
      }

      Sentry.logger.debug("Opening delete confirmation modal", {
        leaseId,
        tenantId: lease.tenant_id,
        propertyId: lease.property_id,
      });

      // Open secure confirmation modal instead of window.confirm
      setLeaseToDelete(lease);
      setShowDeleteModal(true);
    },

    onStatusChange: (lease) => {
      Sentry.startSpan(
        {
          op: "ui.click",
          name: "Change Lease Status Button",
        },
        (span) => {
          span.setAttribute("leaseId", lease.id);
          span.setAttribute("currentStatus", lease.status);
          handleShowModal("status", lease);
        }
      );
    },

    onDocumentUpload: (lease) => {
      Sentry.startSpan(
        {
          op: "ui.click",
          name: "Upload Lease Document Button",
        },
        (span) => {
          span.setAttribute("leaseId", lease.id);
          span.setAttribute("hasDocuments", (lease.documents || []).length > 0);
          handleShowModal("upload", lease);
        }
      );
    },

    onDocumentPreview: async (
      lease: LeaseWithDocuments,
      document: LeaseDocument
    ) => {
      if (!document || !document.id) {
        const error = new Error("Document or ID is missing");
        Sentry.logger.error("Document preview failed - missing data", {
          leaseId: lease.id,
          documentId: document?.id,
        });

        Sentry.captureException(error, {
          tags: {
            component: "Leases",
            action: "preview_document_validation",
            feature: "leases",
          },
          contexts: {
            document: {
              provided: !!document,
              hasId: !!document?.id,
            },
          },
        });

        toast.error(
          "Cannot preview document: document information is missing."
        );
        return;
      }

      return Sentry.startSpan(
        {
          op: "lease.document.preview",
          name: "Generate Secure Document Preview URL",
        },
        async (span) => {
          span.setAttribute("leaseId", lease.id);
          span.setAttribute("documentId", document.id);
          span.setAttribute("documentType", document.document_type);

          try {
            // Show loading toast
            const loadingToast = toast.info(
              "Generating secure preview link...",
              {
                autoClose: false,
              }
            );

            Sentry.logger.debug("Fetching secure URL for document", {
              leaseId: lease.id,
              documentId: document.id,
              documentType: document.document_type,
            });

            // Fetch secure, time-limited URL with authentication
            const { secure_url, expires_at, expires_in_seconds } =
              await getSecureDocumentUrl(lease.id, document.id);

            span.setAttribute("urlExpiresIn", expires_in_seconds);

            // Dismiss loading toast
            toast.dismiss(loadingToast);

            Sentry.logger.info("Secure URL generated successfully", {
              leaseId: lease.id,
              documentId: document.id,
              expiresAt: expires_at,
              expiresInSeconds: expires_in_seconds,
            });

            // Log expiration for debugging
            console.log(
              `[DocumentPreview] Generated SAS URL, expires at: ${expires_at}`
            );

            // Open the preview modal with the secure URL
            setFileToPreviewUrl(secure_url);
            const tenantName = getTenantName(lease);
            const propertyName =
              lease.property?.name || `Property #${lease.property_id}`;
            const docType =
              document.document_type.charAt(0).toUpperCase() +
              document.document_type.slice(1);
            setFilePreviewName(`${docType}: ${tenantName} - ${propertyName}`);
            setShowFilePreviewModal(true);
          } catch (error: any) {
            Sentry.logger.error("Failed to generate secure preview URL", {
              error: error.message,
              leaseId: lease.id,
              documentId: document.id,
              errorStatus: error?.status,
              errorDetail: error?.data?.detail,
            });

            const errorMessage =
              error?.data?.detail ||
              error?.message ||
              "Unable to preview document. Please try downloading instead.";

            toast.error(errorMessage);

            Sentry.captureException(error, {
              tags: {
                component: "Leases",
                action: "preview_document",
                feature: "leases",
                operation: "preview_document",
              },
              contexts: {
                lease: {
                  leaseId: lease.id,
                  propertyId: lease.property_id,
                  tenantId: lease.tenant_id,
                },
                document: {
                  documentId: document.id,
                  documentType: document.document_type,
                  documentName: document.name,
                },
              },
            });
          }
        }
      );
    },
  };

  const handleLeaseUpdated = () => {
    Sentry.logger.debug("Lease updated successfully");
    setShowModal(false);
  };

  const handleImport = () => {
    Sentry.logger.debug("Lease imported successfully");
    handleCloseModal();
  };

  // Handle confirmed deletion (called from DeleteLeaseConfirmationModal)
  const handleConfirmDelete = async () => {
    if (!leaseToDelete) return;

    return Sentry.startSpan(
      {
        op: "lease.delete",
        name: "Delete Lease",
      },
      async (span) => {
        span.setAttribute("leaseId", leaseToDelete.id);
        span.setAttribute(
          "confirmationMethod",
          "modal_with_typed_confirmation"
        );

        try {
          Sentry.logger.info("Deleting lease after confirmation", {
            leaseId: leaseToDelete.id,
          });

          await deleteLeaseMutation.mutateAsync(leaseToDelete.id);

          toast.success("Lease deleted successfully.");
          Sentry.logger.info("Lease deleted successfully", {
            leaseId: leaseToDelete.id,
          });

          setShowDeleteModal(false);
          setLeaseToDelete(null);
        } catch (err: any) {
          Sentry.logger.error("Failed to delete lease", {
            error: err.message,
            leaseId: leaseToDelete.id,
            errorCode: err?.status,
          });

          const errorMessage =
            err.data?.detail ||
            err.message ||
            "Failed to delete lease. Please try again.";
          toast.error(errorMessage);

          Sentry.captureException(err, {
            tags: {
              component: "Leases",
              action: "delete_lease",
              feature: "leases",
              operation: "delete",
            },
            contexts: {
              lease: {
                leaseId: leaseToDelete.id,
                propertyId: leaseToDelete.property_id,
                tenantId: leaseToDelete.tenant_id,
              },
            },
          });

          throw err;
        }
      }
    );
  };

  const handleCloseDeleteModal = () => {
    if (!deleteLeaseMutation.isPending) {
      setShowDeleteModal(false);
      setLeaseToDelete(null);
    }
  };

  // Handle status filter changes with tracking
  const handleStatusFilterChange = (newStatus: string) => {
    Sentry.startSpan(
      {
        op: "ui.filter",
        name: "Change Lease Status Filter",
      },
      (span) => {
        span.setAttribute("filterValue", newStatus);
        span.setAttribute("previousFilter", statusFilter);
        Sentry.logger.debug("Lease status filter changed", {
          from: statusFilter,
          to: newStatus,
        });
        setStatusFilter(newStatus);
      }
    );
  };

  // Handle new lease button with tracking
  const handleNewLease = () => {
    Sentry.startSpan(
      {
        op: "ui.click",
        name: "New Lease Button",
      },
      (span) => {
        span.setAttribute("totalLeases", leases.length);
        Sentry.logger.debug("Opening new lease modal", {
          currentLeaseCount: leases.length,
        });
        handleShowModal("create");
      }
    );
  };

  // Handle lease selection
  const handleSelectLease = (leaseId: number, selected: boolean) => {
    setSelectedLeaseIds((prev) => {
      const newSet = new Set(prev);
      if (selected) {
        newSet.add(leaseId);
      } else {
        newSet.delete(leaseId);
      }
      return newSet;
    });
  };

  // Handle select all
  const handleSelectAll = (selected: boolean) => {
    if (selected) {
      setSelectedLeaseIds(new Set(leases.map((lease) => lease.id)));
    } else {
      setSelectedLeaseIds(new Set());
    }
  };

  // Handle bulk delete
  const handleBulkDelete = () => {
    if (selectedLeaseIds.size === 0) return;
    setShowBulkDeleteModal(true);
  };

  // Handle confirmed bulk deletion
  const handleConfirmBulkDelete = async () => {
    if (selectedLeaseIds.size === 0) return;

    const leaseIdsArray = Array.from(selectedLeaseIds);

    return Sentry.startSpan(
      {
        op: "lease.bulk_delete",
        name: "Bulk Delete Leases",
      },
      async (span) => {
        span.setAttribute("leaseCount", leaseIdsArray.length);
        span.setAttribute("leaseIds", leaseIdsArray.join(","));

        try {
          Sentry.logger.info("Bulk deleting leases after confirmation", {
            leaseCount: leaseIdsArray.length,
            leaseIds: leaseIdsArray,
          });

          await bulkDeleteLeasesMutation.mutateAsync(leaseIdsArray);

          toast.success(
            `${leaseIdsArray.length} lease(s) deleted successfully.`
          );
          Sentry.logger.info("Leases bulk deleted successfully", {
            leaseCount: leaseIdsArray.length,
          });

          setShowBulkDeleteModal(false);
          setSelectedLeaseIds(new Set());
        } catch (err: any) {
          Sentry.logger.error("Failed to bulk delete leases", {
            error: err.message,
            leaseIds: leaseIdsArray,
            errorCode: err?.status,
          });

          const errorMessage =
            err.data?.detail ||
            err.message ||
            "Failed to delete selected leases. Please try again.";
          toast.error(errorMessage);

          Sentry.captureException(err, {
            tags: {
              component: "Leases",
              action: "bulk_delete_leases",
              feature: "leases",
              operation: "bulk_delete",
            },
            contexts: {
              bulkDelete: {
                leaseCount: leaseIdsArray.length,
                leaseIds: leaseIdsArray,
              },
            },
          });

          throw err;
        }
      }
    );
  };

  const handleCloseBulkDeleteModal = () => {
    if (!bulkDeleteLeasesMutation.isPending) {
      setShowBulkDeleteModal(false);
    }
  };

  if (error && leases.length === 0) {
    Sentry.logger.error("Leases page failed to load", {
      error: error instanceof Error ? error.message : String(error),
    });

    Sentry.captureException(error, {
      tags: {
        component: "Leases",
        feature: "leases",
        errorType: "page_load_failure",
      },
    });

    return (
      <div className="p-6 flex flex-col dark-bg">
        <div className="bg-red-100 dark:bg-red-900 border border-red-400 dark:border-red-600 text-red-700 dark:text-red-200 px-4 py-3 rounded mb-4">
          <p>{error instanceof Error ? error.message : String(error)}</p>
          <button
            onClick={() => {
              Sentry.logger.info("User clicked retry after page load failure");
              window.location.reload();
            }}
            className="mt-2 bg-red-500 hover:bg-red-700 text-white font-bold py-1 px-2 rounded text-sm"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  // Log successful page load
  if (!loading && leases.length > 0) {
    Sentry.logger.trace("Leases page loaded successfully", {
      leaseCount: leases.length,
      statusFilter,
    });
  }

  return (
    <div className="p-6 flex flex-col dark-bg">
      <LeaseFilters
        statusFilter={statusFilter}
        onStatusFilterChange={handleStatusFilterChange}
        onNewLease={handleNewLease}
        onBulkDelete={handleBulkDelete}
        selectedCount={selectedLeaseIds.size}
      />

      {error && leases.length > 0 && (
        <div className="bg-red-100 dark:bg-red-900 border border-red-400 dark:border-red-600 text-red-700 dark:text-red-200 px-4 py-3 rounded mb-4">
          <p>{error instanceof Error ? error.message : String(error)}</p>
        </div>
      )}

      <LeasesTable
        leases={leases}
        isLoading={loading}
        actionHandlers={actionHandlers}
        selectedLeaseIds={selectedLeaseIds}
        onSelectLease={handleSelectLease}
        onSelectAll={handleSelectAll}
      />

      {/* Upload Document Modal */}
      {showModal && modalType === "upload" && selectedLease && (
        <UploadLeaseDocumentModal
          isOpen={true}
          onClose={handleCloseModal}
          lease={selectedLease}
          onUploadSuccess={handleCloseModal}
        />
      )}

      {/* Status Change Modal */}
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

      {/* Document Preview Modal */}
      {showFilePreviewModal && fileToPreviewUrl && (
        <FilePreviewModal
          isOpen={showFilePreviewModal}
          onClose={handleCloseFilePreviewModal}
          fileUrl={fileToPreviewUrl}
          fileName={filePreviewName}
        />
      )}

      {/* Delete Confirmation Modal */}
      {showDeleteModal && leaseToDelete && (
        <DeleteLeaseConfirmationModal
          isOpen={showDeleteModal}
          onClose={handleCloseDeleteModal}
          lease={leaseToDelete}
          onConfirm={handleConfirmDelete}
        />
      )}

      {/* Bulk Delete Confirmation Modal */}
      {showBulkDeleteModal && selectedLeaseIds.size > 0 && (
        <DeleteLeaseConfirmationModal
          isOpen={showBulkDeleteModal}
          onClose={handleCloseBulkDeleteModal}
          lease={null}
          onConfirm={handleConfirmBulkDelete}
          bulkDeleteCount={selectedLeaseIds.size}
        />
      )}
    </div>
  );
};

// Wrap entire page with Sentry Error Boundary for comprehensive error tracking
const Leases: React.FC = () => {
  return (
    <Sentry.ErrorBoundary
      fallback={({ error, resetError }) => {
        const errorMessage =
          error instanceof Error
            ? error.message
            : "An unexpected error occurred while loading the Leases page.";

        return (
          <div className="p-6 flex flex-col items-center justify-center min-h-screen dark-bg">
            <div className="max-w-md w-full bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-700 rounded-lg p-6">
              <div className="flex items-center mb-4">
                <div className="flex-shrink-0">
                  <svg
                    className="h-8 w-8 text-red-600 dark:text-red-400"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
                    />
                  </svg>
                </div>
                <h3 className="ml-3 text-lg font-medium text-red-800 dark:text-red-200">
                  Something went wrong
                </h3>
              </div>
              <p className="text-sm text-red-700 dark:text-red-300 mb-4">
                {errorMessage}
              </p>
              <div className="flex space-x-3">
                <button
                  onClick={() => {
                    Sentry.logger.info(
                      "User clicked reset after error boundary triggered"
                    );
                    resetError();
                  }}
                  className="flex-1 bg-red-600 hover:bg-red-700 text-white font-medium py-2 px-4 rounded-lg transition-colors"
                >
                  Try Again
                </button>
                <button
                  onClick={() => {
                    Sentry.logger.info(
                      "User clicked reload after error boundary triggered"
                    );
                    window.location.reload();
                  }}
                  className="flex-1 bg-gray-600 hover:bg-gray-700 text-white font-medium py-2 px-4 rounded-lg transition-colors"
                >
                  Reload Page
                </button>
              </div>
            </div>
          </div>
        );
      }}
      onError={(error, componentStack, eventId) => {
        Sentry.logger.error("Leases page error boundary triggered", {
          error: error instanceof Error ? error.message : String(error),
          stack: error instanceof Error ? error.stack : undefined,
          componentStack,
          eventId,
        });
      }}
      beforeCapture={(scope) => {
        scope.setTag("component", "LeasesPage");
        scope.setTag("feature", "leases");
        scope.setTag("errorBoundary", true);
      }}
    >
      <LeasesContent />
    </Sentry.ErrorBoundary>
  );
};

export default Leases;
