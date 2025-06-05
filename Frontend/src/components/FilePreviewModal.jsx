import React from "react";

const FilePreviewModal = ({
  isOpen,
  onClose,
  fileUrl,
  fileName = "File Preview",
}) => {
  if (!isOpen || !fileUrl) {
    return null;
  }

  const isImage = (url) => {
    const extension = url.split(".").pop()?.toLowerCase();
    return ["png", "jpg", "jpeg", "gif", "webp", "bmp", "svg"].includes(
      extension
    );
  };

  const renderContent = () => {
    if (isImage(fileUrl)) {
      return (
        <div className="w-full h-full flex justify-center items-center overflow-hidden p-1 md:p-2">
          <img
            src={fileUrl}
            alt={fileName}
            className="max-w-full max-h-full object-contain"
          />
        </div>
      );
    } else {
      // Fallback to iframe for PDFs and other document types
      return (
        <iframe
          src={fileUrl}
          title={fileName}
          className="w-full h-full border-0"
          allowFullScreen
          // sandbox="allow-scripts allow-same-origin" // Consider sandbox for security if files are from untrusted sources
        >
          Your browser does not support iframes. You can{" "}
          <a href={fileUrl} target="_blank" rel="noopener noreferrer">
            download the file
          </a>{" "}
          instead.
        </iframe>
      );
    }
  };

  return (
    <div
      className="fixed inset-0 bg-gray-600 bg-opacity-75 overflow-y-auto h-full w-full z-50 flex justify-center items-center p-4"
      onClick={onClose}
    >
      <div
        className="relative bg-white rounded-lg shadow-xl w-full max-w-3xl h-full max-h-[90vh] flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Modal Header */}
        <div className="flex justify-between items-center p-4 border-b">
          <h2
            className="text-xl font-semibold text-gray-800 truncate pr-2"
            title={fileName}
          >
            {fileName}
          </h2>
          <button
            onClick={onClose}
            className="text-gray-500 hover:text-gray-700 p-1 rounded-full focus:outline-none focus:ring-2 focus:ring-gray-400"
            aria-label="Close modal"
          >
            <svg
              className="w-6 h-6"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
              xmlns="http://www.w3.org/2000/svg"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth="2"
                d="M6 18L18 6M6 6l12 12"
              ></path>
            </svg>
          </button>
        </div>

        {/* Modal Body - Content based on type */}
        <div className="flex-grow p-1 md:p-2 bg-gray-100 overflow-auto">
          {renderContent()}
        </div>

        {/* Modal Footer (Optional) */}
        <div className="flex justify-end p-4 border-t">
          <a
            href={fileUrl}
            target="_blank"
            rel="noopener noreferrer"
            download // Suggest download
            className="px-4 py-2 text-sm font-medium text-white bg-blue-600 border border-transparent rounded-md shadow-sm hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 mr-2"
          >
            Download
          </a>
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md shadow-sm hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-gray-400"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};

export default FilePreviewModal;
