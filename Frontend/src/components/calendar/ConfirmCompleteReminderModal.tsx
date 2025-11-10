import React from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { X, CheckCircle, AlertCircle } from 'lucide-react';
import { formatDateForDisplay, getTodayDateString } from '../../utils/dateHelpers';

interface ConfirmCompleteReminderModalProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: () => void;
  reminderTitle: string;
  reminderDate?: string;
  isSubmitting?: boolean;
}

/**
 * Secure confirmation modal for marking custom reminder as complete
 * Provides explicit context to mitigate social engineering risks
 * Replaces direct API call for critical state changes
 */
const ConfirmCompleteReminderModal: React.FC<ConfirmCompleteReminderModalProps> = ({
  isOpen,
  onClose,
  onConfirm,
  reminderTitle,
  reminderDate,
  isSubmitting = false,
}) => {
  if (!isOpen) return null;

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
          transition={{ type: 'spring', damping: 25, stiffness: 400 }}
          className="relative w-full max-w-md bg-white dark:bg-gray-800 rounded-2xl shadow-2xl overflow-hidden flex flex-col z-[10000]"
          onClick={(e) => e.stopPropagation()}
          role="dialog"
          aria-modal="true"
          aria-labelledby="confirm-complete-reminder-modal-title"
          aria-describedby="confirm-complete-reminder-modal-description"
        >
          {/* Header */}
          <div className="relative bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 px-6 py-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-3">
                <div className="p-2 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
                  <CheckCircle className="h-5 w-5 text-blue-600 dark:text-blue-400" />
                </div>
                <div>
                  <h2 id="confirm-complete-reminder-modal-title" className="text-lg font-semibold text-gray-900 dark:text-gray-100">
                    Mark Reminder as Complete
                  </h2>
                  <p id="confirm-complete-reminder-modal-description" className="text-sm text-gray-500 dark:text-gray-400 mt-0.5">
                    Confirm completion of this reminder
                  </p>
                </div>
              </div>
              <button
                onClick={onClose}
                className="p-1.5 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors disabled:opacity-50"
                disabled={isSubmitting}
                aria-label="Close"
              >
                <X className="h-5 w-5 text-gray-500 dark:text-gray-400" />
              </button>
            </div>
          </div>

          {/* Content */}
          <div className="p-6 space-y-4">
            {/* Warning message */}
            <div className="flex items-start space-x-3 p-3 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-700 rounded-lg">
              <AlertCircle className="h-5 w-5 text-amber-600 dark:text-amber-400 flex-shrink-0 mt-0.5" />
              <div className="flex-1">
                <p className="text-sm font-medium text-amber-900 dark:text-amber-100">
                  Are you sure you want to mark this reminder as complete?
                </p>
                <p className="text-xs text-amber-700 dark:text-amber-300 mt-1">
                  This will mark the reminder as completed and it will no longer appear in your calendar.
                </p>
              </div>
            </div>

            {/* Reminder Details */}
            <div className="space-y-2">
              <div>
                <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">
                  Reminder
                </label>
                <p className="text-sm font-medium text-gray-900 dark:text-gray-100 bg-gray-50 dark:bg-gray-700 px-3 py-2 rounded-lg">
                  {reminderTitle}
                </p>
              </div>

              {reminderDate && (
                <div>
                  <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">
                    Reminder Date
                  </label>
                  <p className="text-sm text-gray-700 dark:text-gray-300 bg-gray-50 dark:bg-gray-700 px-3 py-2 rounded-lg">
                    {formatDateForDisplay(reminderDate)}
                  </p>
                </div>
              )}

              <div>
                <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">
                  Completed On
                </label>
                <p className="text-sm text-gray-700 dark:text-gray-300 bg-gray-50 dark:bg-gray-700 px-3 py-2 rounded-lg">
                  {formatDateForDisplay(getTodayDateString())}
                </p>
              </div>
            </div>
          </div>

          {/* Footer */}
          <div className="border-t border-gray-200 dark:border-gray-700 px-6 py-4 flex items-center justify-end space-x-3 bg-gray-50 dark:bg-gray-800/50">
            <button
              type="button"
              onClick={onClose}
              disabled={isSubmitting}
              className="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-600 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 transition-colors"
            >
              Cancel
            </button>
            <button
              type="button"
              onClick={onConfirm}
              disabled={isSubmitting}
              className={`px-5 py-2 text-sm font-medium text-white rounded-lg transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed flex items-center space-x-2 ${
                isSubmitting
                  ? 'bg-gray-400 dark:bg-gray-600'
                  : 'bg-blue-600 dark:bg-blue-700 hover:bg-blue-700 dark:hover:bg-blue-600'
              }`}
            >
              {isSubmitting ? (
                <>
                  <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                  <span>Marking Complete...</span>
                </>
              ) : (
                <>
                  <CheckCircle className="w-4 h-4" />
                  <span>Mark as Complete</span>
                </>
              )}
            </button>
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
};

export default ConfirmCompleteReminderModal;
