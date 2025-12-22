import React, { useState, useEffect } from 'react';
import { useMutation } from '@tanstack/react-query';
import { toast } from 'react-toastify';
import { FiX, FiLoader } from 'react-icons/fi';
import {
  getNotificationPreferences,
  updateNotificationPreferences,
  type NotificationPreferences,
  type NotificationPreferencesUpdateRequest,
} from '@/utils/api/settings';

interface NotificationSettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
}

/**
 * NotificationSettingsModal Component
 * Modal for managing notification preferences, accessible from the Notifications page.
 */
const NotificationSettingsModal: React.FC<NotificationSettingsModalProps> = ({
  isOpen,
  onClose,
}) => {
  const [isLoading, setIsLoading] = useState(true);
  const [prefs, setPrefs] = useState<NotificationPreferences | null>(null);

  // Fetch preferences when modal opens
  useEffect(() => {
    if (isOpen) {
      setIsLoading(true);
      getNotificationPreferences()
        .then((data) => setPrefs(data))
        .catch((err) => {
          console.error('Failed to fetch notification preferences:', err);
          toast.error('Failed to load notification preferences');
        })
        .finally(() => setIsLoading(false));
    }
  }, [isOpen]);

  // Update preferences mutation
  const updateMutation = useMutation({
    mutationFn: (data: NotificationPreferencesUpdateRequest) =>
      updateNotificationPreferences(data),
    onSuccess: (response) => {
      setPrefs(response.preferences);
      toast.success('Preferences updated');
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Failed to update preferences');
    },
  });

  // Handle email toggle - single toggle that controls email channel
  const handleEmailToggle = (type: string, includeEmail: boolean) => {
    if (!prefs) return;

    const currentPref = prefs.preferences[type as keyof typeof prefs.preferences];
    const channels = includeEmail
      ? (['in_app', 'email'] as const)
      : (['in_app'] as const);

    updateMutation.mutate({
      preferences: {
        [type]: {
          enabled: true, // Always enabled for in-app
          channels: [...channels],
          frequency: currentPref?.frequency || 'immediate',
        },
      },
    });
  };

  if (!isOpen) return null;

  const notificationTypes = [
    {
      key: 'rent_reminder',
      label: 'Rent Reminders',
      description: 'Get notified before rent is due',
    },
    {
      key: 'payment_received',
      label: 'Payment Confirmations',
      description: 'Confirmations when payments are received',
    },
    {
      key: 'maintenance_update',
      label: 'Maintenance Updates',
      description: 'Updates on your maintenance requests',
    },
    {
      key: 'lease_expiring',
      label: 'Lease Reminders',
      description: 'Alerts when your lease is expiring',
    },
  ];

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto">
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/50 transition-opacity"
        onClick={onClose}
      />

      {/* Modal */}
      <div className="flex min-h-full items-center justify-center p-4">
        <div className="relative bg-white rounded-xl shadow-xl w-full max-w-md transform transition-all">
          {/* Header */}
          <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200">
            <h2 className="text-lg font-semibold text-gray-900">
              Notification Settings
            </h2>
            <button
              onClick={onClose}
              className="p-1 text-gray-400 hover:text-gray-600 rounded-full hover:bg-gray-100 transition-colors cursor-pointer"
            >
              <FiX className="w-5 h-5" />
            </button>
          </div>

          {/* Content */}
          <div className="px-6 py-4">
            {isLoading ? (
              <div className="flex items-center justify-center py-8">
                <FiLoader className="w-6 h-6 animate-spin text-gray-400" />
              </div>
            ) : prefs ? (
              <div className="space-y-4">
                {notificationTypes.map((type) => {
                  const pref = prefs.preferences[type.key as keyof typeof prefs.preferences];
                  const hasEmail = pref?.channels?.includes('email') ?? true;

                  return (
                    <div
                      key={type.key}
                      className="flex items-center justify-between py-2"
                    >
                      <div className="flex-1 min-w-0 pr-4">
                        <p className="text-sm font-medium text-gray-700">
                          {type.label}
                        </p>
                        <p className="text-xs text-gray-500">{type.description}</p>
                      </div>
                      <div className="flex items-center gap-2">
                        <span className="text-xs text-gray-500">Email</span>
                        <button
                          type="button"
                          onClick={() => handleEmailToggle(type.key, !hasEmail)}
                          disabled={updateMutation.isPending}
                          className={`relative inline-flex h-5 w-9 items-center rounded-full transition-colors cursor-pointer ${
                            hasEmail ? 'bg-teal-600' : 'bg-gray-200'
                          }`}
                        >
                          <span
                            className={`inline-block h-3.5 w-3.5 transform rounded-full bg-white transition-transform ${
                              hasEmail ? 'translate-x-5' : 'translate-x-1'
                            }`}
                          />
                        </button>
                      </div>
                    </div>
                  );
                })}
              </div>
            ) : (
              <p className="text-center text-gray-500 py-8">
                Unable to load preferences
              </p>
            )}
          </div>

        </div>
      </div>
    </div>
  );
};

export default NotificationSettingsModal;
