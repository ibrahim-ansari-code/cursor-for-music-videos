import React, { memo } from 'react';
import { ModalShell, Button } from '../ui/SharedModalComponents';
import { ConfirmationModalProps } from '../../types/integrations';

const ConfirmationModal: React.FC<ConfirmationModalProps> = memo(({
  isOpen,
  onClose,
  onConfirm,
  title,
  message,
  confirmText = "Confirm",
  cancelText = "Cancel",
  variant = "danger",
  isLoading = false
}) => {
  if (!isOpen) return null;

  const footerContent = (
    <>
      <Button
        type="button"
        variant="secondary"
        onClick={onClose}
        disabled={isLoading}
        aria-label={cancelText}
      >
        {cancelText}
      </Button>
      <Button
        type="button"
        variant={variant}
        onClick={onConfirm}
        disabled={isLoading}
        isLoading={isLoading}
        loadingText="Processing..."
        aria-label={confirmText}
      >
        {confirmText}
      </Button>
    </>
  );

  return (
    <ModalShell
      isOpen={isOpen}
      onClose={isLoading ? () => {} : onClose} // Prevent closing during operation
      title={title}
      footerContent={footerContent}
      maxWidth="max-w-md"
    >
      <div className="py-4">
        <p className="text-gray-700 dark:text-gray-300 leading-relaxed">
          {message}
        </p>
      </div>
    </ModalShell>
  );
});

ConfirmationModal.displayName = 'ConfirmationModal';

export default ConfirmationModal;