import React, { useState, useEffect } from 'react';
import * as Dialog from '@radix-ui/react-dialog';
import { motion } from 'framer-motion';
import { X } from 'lucide-react';
import { Input, TextArea } from '../../../components/ui/SharedModalComponents';
import { UpcomingEvent } from '../../../utils/tenantMetrics';
import { EnrichedTenant } from '../../../types/tenant';

interface ReminderConfirmationModalProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: (customSubject: string | null, customMessage: string | null) => void;
  tenant: EnrichedTenant;
  event: UpcomingEvent;
  isLoading?: boolean;
}

const ReminderConfirmationModal: React.FC<ReminderConfirmationModalProps> = ({
  isOpen,
  onClose,
  onConfirm,
  tenant,
  event,
  isLoading = false,
}) => {
  // Generate default subject
  const getDefaultSubject = (): string => {
    return `Reminder: ${event.title}`;
  };

  // Generate default message based on event type
  const getDefaultMessage = (): string => {
    if (event.type === 'rent') {
      if (event.daysRemaining < 0) {
        return `This is a friendly reminder that your rent payment is ${Math.abs(event.daysRemaining)} day(s) overdue.`;
      } else if (event.daysRemaining === 0) {
        return 'This is a friendly reminder that your rent payment is due today.';
      } else {
        return `This is a friendly reminder that your rent payment is due in ${event.daysRemaining} day(s).`;
      }
    } else if (event.type === 'lease_expiry') {
      return `Your lease is expiring ${event.subtitle.toLowerCase()}.`;
    } else if (event.type === 'invoice') {
      if (event.daysRemaining !== null && event.daysRemaining < 0) {
        return `You have an invoice that is ${Math.abs(event.daysRemaining)} day(s) overdue.`;
      } else {
        return `You have an invoice that is ${event.subtitle.toLowerCase()}.`;
      }
    } else if (event.type === 'maintenance') {
      return `Maintenance is scheduled: ${event.subtitle}`;
    } else if (event.type === 'insurance') {
      return `Insurance reminder: ${event.subtitle}`;
    } else {
      return event.subtitle;
    }
  };

  const [subject, setSubject] = useState<string>(getDefaultSubject());
  const [message, setMessage] = useState<string>(getDefaultMessage());

  // Reset to defaults when modal opens or event changes
  useEffect(() => {
    if (isOpen) {
      setSubject(getDefaultSubject());
      setMessage(getDefaultMessage());
    }
  }, [isOpen, event]);

  if (!isOpen) return null;

  // Get tenant display name
  const tenantName = tenant.tenant_type === 'Company'
    ? tenant.company_name || 'Tenant'
    : `${tenant.first_name || ''} ${tenant.last_name || ''}`.trim() || 'Tenant';

  // Format date
  const formatDate = (date: Date): string => {
    return date.toLocaleDateString('en-US', {
      month: 'long',
      day: 'numeric',
      year: 'numeric',
    });
  };

  // Format currency
  const formatCurrency = (amount: number): string => {
    return `$${amount.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  };

  const handleConfirm = () => {
    // Always send the subject and message exactly as typed
    onConfirm(subject, message);
  };

  return (
    <Dialog.Root open={isOpen} onOpenChange={isLoading ? () => {} : onClose}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 bg-black/60 backdrop-blur-sm z-[60]">
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="fixed inset-0"
          />
        </Dialog.Overlay>

        <Dialog.Content className="fixed left-[50%] top-[50%] translate-x-[-50%] translate-y-[-50%] z-[70]">
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.95 }}
            transition={{
              duration: 0.2,
              type: 'spring',
              stiffness: 300,
              damping: 30,
            }}
            className="w-full max-w-lg bg-white dark:bg-gray-800 rounded-2xl shadow-2xl overflow-hidden flex flex-col max-h-[90vh]"
          >
            {/* Header */}
            <div className="bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 px-6 py-4">
              <div className="flex items-center justify-between">
                <Dialog.Title className="text-xl font-semibold text-gray-900 dark:text-gray-100">
                  Confirm Reminder Email
                </Dialog.Title>
                <Dialog.Close asChild>
                  <button
                    className="rounded-lg p-1.5 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
                    aria-label="Close"
                    disabled={isLoading}
                  >
                    <X className="h-5 w-5 text-gray-500 dark:text-gray-400" />
                  </button>
                </Dialog.Close>
              </div>
            </div>

            {/* Body */}
            <div className="p-6 flex-grow overflow-y-auto">
              <div className="space-y-6">
        {/* Tenant Info */}
        <div className="bg-gray-50 dark:bg-gray-700/50 rounded-lg p-4 space-y-2">
          <div className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide">
            Sending to
          </div>
          <div className="text-sm font-semibold text-gray-900 dark:text-gray-100">
            {tenantName}
          </div>
          {tenant.email && (
            <div className="text-sm text-gray-600 dark:text-gray-400">
              {tenant.email}
            </div>
          )}
        </div>

        {/* Event Details */}
        <div className="space-y-4">
          <div className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide">
            Reminder Details
          </div>
          
          <div className="space-y-3">
            <div>
              <div className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                {event.title}
              </div>
              <div className="text-sm text-gray-600 dark:text-gray-400">
                {event.subtitle}
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4 pt-2 border-t border-gray-200 dark:border-gray-700">
              {event.date && (
                <div>
                  <div className="text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">
                    Date
                  </div>
                  <div className="text-sm text-gray-900 dark:text-gray-100">
                    {formatDate(event.date)}
                  </div>
                </div>
              )}
              
              {event.daysRemaining !== null && (
                <div>
                  <div className="text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">
                    Days {event.daysRemaining < 0 ? 'Overdue' : 'Remaining'}
                  </div>
                  <div className={`text-sm font-medium ${
                    event.daysRemaining < 0 
                      ? 'text-red-600 dark:text-red-400' 
                      : event.daysRemaining === 0
                      ? 'text-orange-600 dark:text-orange-400'
                      : 'text-gray-900 dark:text-gray-100'
                  }`}>
                    {Math.abs(event.daysRemaining)} day{Math.abs(event.daysRemaining) !== 1 ? 's' : ''}
                  </div>
                </div>
              )}

              {event.amount !== undefined && event.amount !== null && (
                <div>
                  <div className="text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">
                    Amount
                  </div>
                  <div className="text-sm font-semibold text-gray-900 dark:text-gray-100">
                    {formatCurrency(event.amount)}
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Delivery Info */}
        <div className="bg-blue-50 dark:bg-blue-900/20 rounded-lg p-4 border border-blue-200 dark:border-blue-800">
          <div className="text-xs font-medium text-blue-800 dark:text-blue-300 mb-2 flex items-center gap-2">
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
            </svg>
            Sending via Email
          </div>
          <p className="text-sm text-blue-700 dark:text-blue-300">
            This reminder will be sent to <span className="font-medium">{tenant.email}</span>
          </p>
        </div>

        {/* Message Preview */}
        <div className="bg-blue-50 dark:bg-blue-900/20 rounded-lg p-4 border border-blue-200 dark:border-blue-800">
          <div className="text-xs font-medium text-blue-800 dark:text-blue-300 mb-3 flex items-center gap-2">
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
            </svg>
            Email Preview
          </div>
          <div className="space-y-2 text-sm">
            <div>
              <span className="font-medium text-blue-900 dark:text-blue-200">Subject: </span>
              <span className="text-blue-800 dark:text-blue-300">{subject}</span>
            </div>
            <div className="pt-2 border-t border-blue-200 dark:border-blue-700">
              <div className="font-medium text-blue-900 dark:text-blue-200 mb-1">Message:</div>
              <div className="text-blue-800 dark:text-blue-300 italic mb-2">
                "{message}"
              </div>
              <div className="text-xs text-blue-700 dark:text-blue-400 space-y-1">
                <div>• Property and unit information will be included</div>
                {event.date && (
                  <div>• Due Date: {formatDate(event.date)}</div>
                )}
                {event.amount !== undefined && event.amount !== null && (
                  <div>• Amount: {formatCurrency(event.amount)}</div>
                )}
                {event.daysRemaining !== null && (
                  <div>• Days {event.daysRemaining < 0 ? 'Overdue' : 'Remaining'}: {Math.abs(event.daysRemaining)}</div>
                )}
              </div>
            </div>
          </div>
        </div>

        {/* Editable Email Fields */}
        <div className="space-y-4">
          <div className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide">
            Edit Email Content
          </div>
          
          <div>
            <label htmlFor="email-subject" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">
              Subject Line
            </label>
            <Input
              id="email-subject"
              value={subject}
              onChange={(e) => setSubject(e.target.value)}
              placeholder="Enter email subject"
              disabled={isLoading}
              className="w-full"
            />
          </div>

          <div>
            <label htmlFor="email-message" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">
              Message
            </label>
            <TextArea
              id="email-message"
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              placeholder="Enter email message"
              disabled={isLoading}
              rows={4}
              className="w-full"
            />
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
              This message will appear in the main body of the email. Property, unit, due date, amount, and other metadata will be automatically included below.
            </p>
          </div>
        </div>
              </div>
            </div>

            {/* Footer */}
            <div className="border-t border-gray-200 dark:border-gray-700 px-6 py-4 bg-gray-50 dark:bg-gray-900 flex justify-end space-x-3">
              <button
                type="button"
                onClick={onClose}
                disabled={isLoading}
                className="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleConfirm}
                disabled={isLoading}
                className="flex items-center space-x-2 px-4 py-2 text-sm font-medium bg-blue-600 text-white hover:bg-blue-700 dark:bg-blue-700 dark:hover:bg-blue-600 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isLoading ? (
                  <>
                    <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                    <span>Sending...</span>
                  </>
                ) : (
                  <span>Send Reminder</span>
                )}
              </button>
            </div>
          </motion.div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
};

export default ReminderConfirmationModal;

