import React from 'react';
import * as Dialog from '@radix-ui/react-dialog';
import { motion } from 'framer-motion';
import { X, Bell, Mail } from 'lucide-react';

export type ReminderMethod = 'portal' | 'email';

interface ReminderMethodModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSelect: (method: ReminderMethod) => void;
  tenantName: string;
  hasPortalAccess: boolean;
}

/**
 * ReminderMethodModal Component
 *
 * Modal asking the landlord how they want to send the reminder:
 * - Portal (in-app notification) - disabled if tenant doesn't have portal access
 * - Email - always available
 */
const ReminderMethodModal: React.FC<ReminderMethodModalProps> = ({
  isOpen,
  onClose,
  onSelect,
  tenantName,
  hasPortalAccess,
}) => {
  if (!isOpen) return null;

  return (
    <Dialog.Root open={isOpen} onOpenChange={onClose}>
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
            className="w-full max-w-md bg-white dark:bg-gray-800 rounded-2xl shadow-2xl overflow-hidden"
          >
            {/* Header */}
            <div className="bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 px-6 py-4">
              <div className="flex items-center justify-between">
                <Dialog.Title className="text-lg font-semibold text-gray-900 dark:text-gray-100">
                  Send Reminder
                </Dialog.Title>
                <Dialog.Close asChild>
                  <button
                    className="rounded-lg p-1.5 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors cursor-pointer"
                    aria-label="Close"
                  >
                    <X className="h-5 w-5 text-gray-500 dark:text-gray-400" />
                  </button>
                </Dialog.Close>
              </div>
            </div>

            {/* Body */}
            <div className="p-6">
              <p className="text-sm text-gray-600 dark:text-gray-400 mb-5">
                How would you like to send this reminder to <span className="font-medium text-gray-900 dark:text-gray-100">{tenantName}</span>?
              </p>

              <div className="space-y-3">
                {/* Portal Option - Disabled if tenant doesn't have access */}
                <button
                  onClick={() => hasPortalAccess && onSelect('portal')}
                  disabled={!hasPortalAccess}
                  className={`w-full flex items-center gap-4 p-4 rounded-xl transition-colors ${
                    hasPortalAccess
                      ? 'bg-emerald-50 dark:bg-emerald-900/20 border-2 border-emerald-200 dark:border-emerald-800 hover:border-emerald-400 dark:hover:border-emerald-600 cursor-pointer group'
                      : 'bg-gray-50 dark:bg-gray-900/20 border-2 border-gray-200 dark:border-gray-700 cursor-not-allowed opacity-60'
                  }`}
                >
                  <div className={`flex-shrink-0 w-12 h-12 rounded-lg flex items-center justify-center transition-colors ${
                    hasPortalAccess
                      ? 'bg-emerald-100 dark:bg-emerald-900/40 group-hover:bg-emerald-200 dark:group-hover:bg-emerald-900/60'
                      : 'bg-gray-100 dark:bg-gray-800'
                  }`}>
                    <Bell className={`w-6 h-6 ${hasPortalAccess ? 'text-emerald-600 dark:text-emerald-400' : 'text-gray-400 dark:text-gray-500'}`} />
                  </div>
                  <div className="flex-1 text-left">
                    <div className={`text-sm font-semibold ${hasPortalAccess ? 'text-gray-900 dark:text-gray-100' : 'text-gray-500 dark:text-gray-400'}`}>
                      Send via Portal
                    </div>
                    <div className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
                      {hasPortalAccess
                        ? 'Tenant will receive an in-app notification'
                        : 'Tenant hasn\'t activated their portal yet'}
                    </div>
                  </div>
                  <div className="flex-shrink-0">
                    {hasPortalAccess ? (
                      <span className="inline-flex items-center px-2 py-1 rounded-md text-xs font-medium bg-emerald-100 dark:bg-emerald-900/40 text-emerald-700 dark:text-emerald-300">
                        Recommended
                      </span>
                    ) : (
                      <span className="inline-flex items-center px-2 py-1 rounded-md text-xs font-medium bg-gray-100 dark:bg-gray-800 text-gray-500 dark:text-gray-400">
                        Unavailable
                      </span>
                    )}
                  </div>
                </button>

                {/* Email Option */}
                <button
                  onClick={() => onSelect('email')}
                  className="w-full flex items-center gap-4 p-4 bg-blue-50 dark:bg-blue-900/20 border-2 border-blue-200 dark:border-blue-800 rounded-xl hover:border-blue-400 dark:hover:border-blue-600 transition-colors cursor-pointer group"
                >
                  <div className="flex-shrink-0 w-12 h-12 bg-blue-100 dark:bg-blue-900/40 rounded-lg flex items-center justify-center group-hover:bg-blue-200 dark:group-hover:bg-blue-900/60 transition-colors">
                    <Mail className="w-6 h-6 text-blue-600 dark:text-blue-400" />
                  </div>
                  <div className="flex-1 text-left">
                    <div className="text-sm font-semibold text-gray-900 dark:text-gray-100">
                      Send via Email
                    </div>
                    <div className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
                      Tenant will receive an email notification
                    </div>
                  </div>
                </button>
              </div>

              {!hasPortalAccess && (
                <div className="mt-5 p-3 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-lg">
                  <p className="text-xs text-amber-800 dark:text-amber-300">
                    <span className="font-medium">Tip:</span> Invite this tenant to the portal for faster, in-app communication. Go to their profile and click "Invite to Portal".
                  </p>
                </div>
              )}
            </div>
          </motion.div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
};

export default ReminderMethodModal;
