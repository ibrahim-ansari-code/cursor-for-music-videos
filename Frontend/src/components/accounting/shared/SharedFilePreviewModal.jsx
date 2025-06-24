import React from "react";
import FilePreviewModal from "../../FilePreviewModal";
import { useAccounting } from "../AccountingContext";

const SharedFilePreviewModal = () => {
  const {
    showFilePreviewModal,
    fileToPreviewUrl,
    filePreviewName,
    closeFilePreview,
  } = useAccounting();

  if (!showFilePreviewModal || !fileToPreviewUrl) {
    return null;
  }

  return (
    <FilePreviewModal
      isOpen={showFilePreviewModal}
      onClose={closeFilePreview}
      fileUrl={fileToPreviewUrl}
      fileName={filePreviewName}
    />
  );
};

export default SharedFilePreviewModal;