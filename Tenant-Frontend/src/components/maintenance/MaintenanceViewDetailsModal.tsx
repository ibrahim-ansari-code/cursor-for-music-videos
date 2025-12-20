import React, { useState, useEffect } from "react";
import Modal from "react-modal";
import * as Sentry from "@sentry/react";
import {
  MaintenanceRequest,
  MaintenanceStatus,
} from "../../utils/api/maintenance/types";
import { getSecurePhotoUrl } from "../../utils/api/maintenance";
import {
  X,
  Calendar,
  Clock,
  AlertCircle,
  CheckCircle,
  XCircle,
  ExternalLink,
  Loader2,
  Bell,
} from "lucide-react";

interface MaintenanceViewDetailsModalProps {
  request: MaintenanceRequest | null;
  onClose: () => void;
}

interface LazyImageProps {
  src: string;
  alt: string;
}

const LazyImage: React.FC<LazyImageProps> = ({ src, alt }) => {
  const [isLoading, setIsLoading] = useState(true);
  const [hasError, setHasError] = useState(false);
  const [secureUrl, setSecureUrl] = useState<string>(src);

  const isPdf = src.toLowerCase().includes(".pdf");

  useEffect(() => {
    const loadSecureImage = async () => {
      try {
        // Generate secure URL for the photo
        const secureData = await getSecurePhotoUrl(src);
        setSecureUrl(secureData.secure_url);

        // For PDFs, skip image preloading
        if (isPdf) {
          setIsLoading(false);
          return;
        }

        // Preload the image
        const img = new Image();
        img.src = secureData.secure_url;
        img.onload = () => {
          setIsLoading(false);
        };
        img.onerror = () => {
          setIsLoading(false);
          setHasError(true);
        };
      } catch (error) {
        Sentry.captureException(error, {
          tags: {
            component: 'MaintenanceViewDetailsModal',
            action: 'load_secure_image',
          },
        });
        setIsLoading(false);
        setHasError(true);
      }
    };

    loadSecureImage();
  }, [src, isPdf]);

  return (
    <div className="relative w-full" style={{ paddingBottom: '100%' }}>
      <div className="absolute inset-0 bg-gray-100 rounded-lg overflow-hidden border border-gray-200 group">
        {isLoading ? (
          <div className="absolute inset-0 flex items-center justify-center">
            <Loader2 className="animate-spin h-8 w-8 text-teal-600" />
          </div>
        ) : hasError ? (
          <a
            href={src}
            target="_blank"
            rel="noopener noreferrer"
            className="absolute inset-0 flex flex-col items-center justify-center hover:bg-gray-200 transition-colors cursor-pointer"
          >
            <ExternalLink className="h-8 w-8 text-gray-500 mb-2" />
            <span className="text-xs font-medium text-gray-700">View File</span>
          </a>
        ) : isPdf ? (
          <a
            href={secureUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="absolute inset-0 flex flex-col items-center justify-center bg-red-50 hover:bg-red-100 transition-colors cursor-pointer"
          >
            <svg
              className="w-12 h-12 text-red-600 mb-2"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z"
              />
            </svg>
            <span className="text-xs font-medium text-red-600">PDF</span>
          </a>
        ) : (
          <>
            <img
              src={secureUrl}
              alt={alt}
              className="w-full h-full object-cover"
            />
            <a
              href={secureUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="absolute inset-0 flex items-center justify-center bg-black/50 opacity-0 group-hover:opacity-100 transition-opacity cursor-pointer"
            >
              <svg
                className="w-10 h-10 text-white"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
                />
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"
                />
              </svg>
            </a>
          </>
        )}
      </div>
    </div>
  );
};

const MaintenanceViewDetailsModal: React.FC<
  MaintenanceViewDetailsModalProps
> = ({ request, onClose }) => {
  if (!request) {
    return null;
  }

  const getStatusInfo = (status: MaintenanceStatus) => {
    switch (status) {
      case MaintenanceStatus.NEW:
        return {
          color: "text-blue-600",
          bgColor: "bg-blue-100",
          icon: <Bell className="w-5 h-5" />,
        };
      case MaintenanceStatus.PENDING:
        return {
          color: "text-yellow-600",
          bgColor: "bg-yellow-100",
          icon: <Clock className="w-5 h-5" />,
        };
      case MaintenanceStatus.IN_PROGRESS:
        return {
          color: "text-blue-600",
          bgColor: "bg-blue-100",
          icon: <AlertCircle className="w-5 h-5" />,
        };
      case MaintenanceStatus.SCHEDULED:
        return {
          color: "text-purple-600",
          bgColor: "bg-purple-100",
          icon: <Calendar className="w-5 h-5" />,
        };
      case MaintenanceStatus.COMPLETED:
        return {
          color: "text-green-600",
          bgColor: "bg-green-100",
          icon: <CheckCircle className="w-5 h-5" />,
        };
      case MaintenanceStatus.CANCELLED:
        return {
          color: "text-red-600",
          bgColor: "bg-red-100",
          icon: <XCircle className="w-5 h-5" />,
        };
      default:
        return {
          color: "text-gray-600",
          bgColor: "bg-gray-100",
          icon: <Clock className="w-5 h-5" />,
        };
    }
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    if (isNaN(date.getTime())) {
      return "Invalid Date";
    }
    return date.toLocaleDateString("en-US", {
      year: "numeric",
      month: "long",
      day: "numeric",
    });
  };

  // Format status label for tenant-facing display
  const formatStatusLabel = (status: MaintenanceStatus): string => {
    if (status === MaintenanceStatus.NEW) {
      return "Submitted";
    }
    return status;
  };

  const statusInfo = getStatusInfo(request.status);

  return (
    <Modal
      isOpen={!!request}
      onRequestClose={onClose}
      className="modal"
      overlayClassName="modal-overlay"
      contentLabel="Maintenance Request Details"
      ariaHideApp={false}
    >
      <div className="bg-white rounded-lg p-8 max-w-2xl mx-auto max-h-[90vh] overflow-y-auto transition-all duration-300">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h2 className="text-2xl font-bold text-gray-900">
              Maintenance Request Details
            </h2>
            <p className="text-sm text-gray-500 mt-1">
              View complete information about this maintenance request
            </p>
          </div>
          <button
            onClick={onClose}
            className="text-gray-500 hover:text-gray-700 transition-colors p-2 rounded-lg hover:bg-gray-100"
            aria-label="Close"
          >
            <X className="w-6 h-6" />
          </button>
        </div>

        <div className="space-y-6">
          <div>
            <h3 className="text-lg font-semibold text-gray-800">
              {request.issue_title}
            </h3>
            {/* <p className="text-sm text-gray-600 mt-1">
              Request ID: #{request.id}
            </p> */}
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="flex items-center p-4 bg-gray-50 rounded-lg border border-gray-200">
              <div className={`p-3 rounded-lg ${statusInfo.bgColor}`}>
                <div className={statusInfo.color}>{statusInfo.icon}</div>
              </div>
              <div className="ml-4">
                <p className="text-xs text-gray-600 uppercase tracking-wide font-medium">
                  Status
                </p>
                <p className={`font-semibold text-lg ${statusInfo.color}`}>
                  {formatStatusLabel(request.status)}
                </p>
              </div>
            </div>
            <div className="flex items-center p-4 bg-gray-50 rounded-lg border border-gray-200">
              <div className="p-3 rounded-lg bg-gray-200">
                <Calendar className="w-5 h-5 text-gray-600" />
              </div>
              <div className="ml-4">
                <p className="text-xs text-gray-600 uppercase tracking-wide font-medium">
                  Submitted On
                </p>
                <p className="font-semibold text-gray-900">
                  {formatDate(request.request_date)}
                </p>
              </div>
            </div>
            {request.preferred_time && (
              <div className="flex items-center p-4 bg-teal-50 rounded-lg border border-teal-200 md:col-span-2">
                <div className="p-3 rounded-lg bg-teal-100">
                  <Clock className="w-5 h-5 text-teal-600" />
                </div>
                <div className="ml-4">
                  <p className="text-xs text-teal-700 uppercase tracking-wide font-medium">
                    Preferred Time
                  </p>
                  <p className="font-semibold text-teal-900">
                    {request.preferred_time}
                  </p>
                </div>
              </div>
            )}
          </div>

          {request.description && (
            <div>
              <h4 className="text-md font-semibold text-gray-800 mb-2">
                Description
              </h4>
              <p className="text-gray-700 text-base">{request.description}</p>
            </div>
          )}

          {request.photos && request.photos.length > 0 && (
            <div>
              <h4 className="text-md font-semibold text-gray-800 mb-3">
                Photos ({request.photos.length})
              </h4>
              <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3 min-h-[120px]">
                {request.photos.map((photo, index) => (
                  <LazyImage
                    key={index}
                    src={photo}
                    alt={`Maintenance Photo ${index + 1}`}
                  />
                ))}
              </div>
            </div>
          )}

          <div className="pt-6">
            <button
              onClick={onClose}
              className="w-full px-6 py-3 bg-gray-900 text-white rounded-lg font-semibold hover:bg-gray-800 transition-colors cursor-pointer"
            >
              Close
            </button>
          </div>
        </div>
      </div>
    </Modal>
  );
};

export default MaintenanceViewDetailsModal;
