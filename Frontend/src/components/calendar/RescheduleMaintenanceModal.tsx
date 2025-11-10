import React, { useState, useEffect } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { X, Calendar } from 'lucide-react';
import { formatDateForDisplay } from '../../utils/dateHelpers';

interface RescheduleMaintenanceModalProps {
  isOpen: boolean;
  onClose: () => void;
  onReschedule: (newDate: string) => Promise<void>;
  currentDate?: string;
  maintenanceTitle: string;
}

/**
 * Simple modal for rescheduling maintenance appointments
 * Shows current date and allows selection of new date
 */
const RescheduleMaintenanceModal: React.FC<RescheduleMaintenanceModalProps> = ({
  isOpen,
  onClose,
  onReschedule,
  currentDate,
  maintenanceTitle,
}) => {
  const [newDate, setNewDate] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Reset form when modal opens
  useEffect(() => {
    if (isOpen) {
      setNewDate(currentDate || '');
      setError(null);
    }
  }, [isOpen, currentDate]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    // Validate new date is provided
    if (!newDate || newDate.trim() === '') {
      setError('Please select a new date');
      return;
    }

    // Validate new date is different from current
    if (newDate === currentDate) {
      setError(`The new date must be different from the current scheduled date (${formatDateForDisplay(currentDate)})`);
      return;
    }

    setIsSubmitting(true);
    try {
      await onReschedule(newDate);
      onClose();
    } catch (err: any) {
      setError(err?.message || 'Failed to reschedule maintenance');
    } finally {
      setIsSubmitting(false);
    }
  };

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
          aria-labelledby="reschedule-modal-title"
          aria-describedby="reschedule-modal-description"
        >
          {/* Header */}
          <div className="relative bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 px-6 py-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-3">
                <div className="p-2 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
                  <Calendar className="h-5 w-5 text-blue-600 dark:text-blue-400" />
                </div>
                <div>
                  <h2 id="reschedule-modal-title" className="text-lg font-semibold text-gray-900 dark:text-gray-100">
                    Reschedule Maintenance
                  </h2>
                  <p id="reschedule-modal-description" className="text-sm text-gray-500 dark:text-gray-400 mt-0.5">
                    Select a new date for this maintenance
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
          <form onSubmit={handleSubmit} className="p-6 space-y-4">
            {error && (
              <div
                className="p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-700 rounded-lg"
                role="alert"
                aria-live="polite"
              >
                <p className="text-sm text-red-600 dark:text-red-400">{error}</p>
              </div>
            )}

            {/* Maintenance Title */}
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Maintenance Request
              </label>
              <p className="text-sm text-gray-900 dark:text-gray-100 bg-gray-50 dark:bg-gray-700 px-3 py-2 rounded-lg">
                {maintenanceTitle}
              </p>
            </div>

            {/* Current Date */}
            {currentDate && (
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Current Scheduled Date
                </label>
                <p className="text-sm text-gray-600 dark:text-gray-400 bg-gray-50 dark:bg-gray-700 px-3 py-2 rounded-lg">
                  {formatDateForDisplay(currentDate)}
                </p>
              </div>
            )}

            {/* New Date Picker */}
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                New Scheduled Date <span className="text-red-500">*</span>
              </label>
              <input
                type="date"
                value={newDate}
                onChange={(e) => setNewDate(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 dark:focus:ring-blue-400 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
                min={new Date().toISOString().split('T')[0]} // Minimum today
                required
                disabled={isSubmitting}
              />
            </div>

            {/* Footer Buttons */}
            <div className="flex items-center justify-end space-x-3 pt-2">
              <button
                type="button"
                onClick={onClose}
                disabled={isSubmitting}
                className="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-600 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 transition-colors"
              >
                Cancel
              </button>
              <button
                type="submit"
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
                    <span>Rescheduling...</span>
                  </>
                ) : (
                  'Reschedule'
                )}
              </button>
            </div>
          </form>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
};

export default RescheduleMaintenanceModal;
