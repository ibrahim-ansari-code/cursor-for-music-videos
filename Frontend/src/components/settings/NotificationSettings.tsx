import React, { useState, useEffect } from "react";
import { Button } from "../ui/SharedModalComponents";
import { toast } from "react-toastify";
import * as Sentry from "@sentry/react";
import { getPreferences, updatePreferences, sendTestNotification, sendTestEmail, type NotificationPreferenceData, type NotificationChannel } from "../../utils/api/notifications";
import type { User } from "../../types/user";

interface NotificationCategoryPreference {
  enabled: boolean;
  channels: string[];
  frequency: string;
}

interface NotificationUpdatePayload {
  id: string;
  user_id: string;
  enabled: boolean;
  preferences: Record<string, NotificationCategoryPreference>;
  email_digest_frequency: string;
  email_digest_time: string;
  timezone: string;
  quiet_hours_enabled: boolean;
  quiet_hours_start?: string | null;
  quiet_hours_end?: string | null;
  created_at: string;
  updated_at: string;
}

interface NotificationSettingsProps {
  user?: User;
  onNotificationUpdate?: (notifications: NotificationUpdatePayload) => void;
}

// Notification category configuration
const NOTIFICATION_CATEGORIES = [
  {
    key: 'rent_reminder',
    label: 'Rent Reminders',
    description: 'Upcoming rent payments 3 days before due',
    defaultEnabled: true,
  },
  {
    key: 'payment_received',
    label: 'Payment Received',
    description: 'When a tenant submits a rent payment',
    defaultEnabled: true,
  },
  {
    key: 'lease_expiring',
    label: 'Lease Expiring',
    description: 'Leases expiring within 30 and 60 days',
    defaultEnabled: true,
  },
  {
    key: 'maintenance_update',
    label: 'Maintenance Updates',
    description: 'New requests and status changes',
    defaultEnabled: true,
  },
  {
    key: 'system_update',
    label: 'System Updates',
    description: 'Platform announcements and new features',
    defaultEnabled: false,
  },
];

const NotificationSettings: React.FC<NotificationSettingsProps> = ({ onNotificationUpdate }) => {
  const [preferences, setPreferences] = useState<NotificationPreferenceData | null>(null);
  const [originalPreferences, setOriginalPreferences] = useState<NotificationPreferenceData | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isFetchLoading, setIsFetchLoading] = useState(true);
  const [isSendingTestNotification, setIsSendingTestNotification] = useState(false);
  const [isSendingTestEmail, setIsSendingTestEmail] = useState(false);

  // Fetch user preferences on mount
  useEffect(() => {
    const fetchPreferences = async () => {
      setIsFetchLoading(true);
      try {
        const prefs = await getPreferences();
        setPreferences(prefs);
        setOriginalPreferences(prefs);
      } catch (error) {
        console.error("Error fetching notification preferences:", error);
        Sentry.captureException(error, {
          tags: {
            component: 'NotificationSettings',
            action: 'fetch_preferences',
          },
        });
        toast.error("Failed to load notification preferences");
      } finally {
        setIsFetchLoading(false);
      }
    };

    fetchPreferences();
  }, []);

  // Check if there are unsaved changes
  const hasChanges = (): boolean => {
    if (!preferences || !originalPreferences) return false;
    return JSON.stringify(preferences) !== JSON.stringify(originalPreferences);
  };

  // Toggle email for a specific category (local state only)
  const handleToggleEmailForCategory = (category: string) => {
    if (!preferences) return;

    const currentPref = preferences.preferences[category];
    const hasEmail = currentPref?.channels?.includes('email') ?? true;
    const newChannels: NotificationChannel[] = hasEmail ? ['in_app'] : ['in_app', 'email'];

    setPreferences((prev: NotificationPreferenceData | null) => {
      if (!prev) return prev;
      return {
        ...prev,
        preferences: {
          ...prev.preferences,
          [category]: {
            enabled: true,
            channels: newChannels,
            frequency: currentPref?.frequency || 'immediate',
          },
        },
      };
    });
  };

  const handleSave = async () => {
    if (!preferences) return;

    setIsLoading(true);

    try {
      const result = await updatePreferences({
        preferences: preferences.preferences,
        email_digest_frequency: preferences.email_digest_frequency,
      });

      if (result?.preferences) {
        setPreferences(result.preferences);
        setOriginalPreferences(result.preferences);
      }

      toast.success("Notification preferences saved");

      if (onNotificationUpdate && result?.preferences) {
        onNotificationUpdate(result.preferences);
      }
    } catch (error) {
      console.error("Error saving notification preferences:", error);
      Sentry.captureException(error, {
        tags: {
          component: 'NotificationSettings',
          action: 'save_preferences',
        },
      });
      toast.error("Failed to save preferences");
    } finally {
      setIsLoading(false);
    }
  };

  const handleSendTestNotification = async () => {
    setIsSendingTestNotification(true);
    try {
      await sendTestNotification();
      toast.success("Test notification sent! Check your notifications.");
    } catch (error: any) {
      console.error("Error sending test notification:", error);
      Sentry.captureException(error, {
        tags: {
          component: 'NotificationSettings',
          action: 'send_test_notification',
        },
      });

      if (error?.status === 429) {
        toast.error("Rate limit exceeded. You can send up to 5 test notifications per hour.");
      } else {
        toast.error("Failed to send test notification. Please try again.");
      }
    } finally {
      setIsSendingTestNotification(false);
    }
  };

  const handleSendTestEmail = async () => {
    setIsSendingTestEmail(true);
    try {
      await sendTestEmail();
      toast.success("Test email sent! Check your inbox.");
    } catch (error: any) {
      console.error("Error sending test email:", error);
      Sentry.captureException(error, {
        tags: {
          component: 'NotificationSettings',
          action: 'send_test_email',
        },
      });

      if (error?.status === 429) {
        toast.error("Rate limit exceeded. You can send up to 5 test emails per hour.");
      } else {
        toast.error("Failed to send test email. Please try again.");
      }
    } finally {
      setIsSendingTestEmail(false);
    }
  };

  if (isFetchLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="w-8 h-8 border-4 border-blue-200 dark:border-blue-800 border-t-blue-600 dark:border-t-blue-400 rounded-full animate-spin" />
      </div>
    );
  }

  if (!preferences) {
    return (
      <div className="p-4 text-center text-sm text-red-600 dark:text-red-400">
        Failed to load notification preferences
      </div>
    );
  }

  return (
    <div>
      <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-2">
        Notification Settings
      </h2>
      <p className="text-sm text-gray-600 dark:text-gray-400 mb-6">
        In-app notifications are always on. Use the toggles to also receive email notifications.
      </p>

      <div className="space-y-6">
        {/* Email Notification Categories */}
        <div className="space-y-3">
          {NOTIFICATION_CATEGORIES.map((category) => {
            const pref = preferences.preferences[category.key];
            const hasEmail = pref?.channels?.includes('email') ?? category.defaultEnabled;

            return (
              <div
                key={category.key}
                className="flex items-center justify-between py-3 px-4 bg-gray-50 dark:bg-gray-800 rounded-lg"
              >
                <div className="flex-1 min-w-0 pr-4">
                  <p className="text-sm font-medium text-gray-900 dark:text-white">
                    {category.label}
                  </p>
                  <p className="text-xs text-gray-500 dark:text-gray-400">
                    {category.description}
                  </p>
                </div>
                <div className="flex items-center gap-2 shrink-0">
                  <span className="text-xs text-gray-500 dark:text-gray-400">Email</span>
                  <button
                    type="button"
                    onClick={() => handleToggleEmailForCategory(category.key)}
                    className={`relative inline-flex h-5 w-9 items-center rounded-full transition-colors cursor-pointer ${
                      hasEmail ? 'bg-blue-600' : 'bg-gray-300 dark:bg-gray-600'
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

        {/* Test Buttons */}
        <div className="pt-4 border-t border-gray-200 dark:border-gray-700 space-y-3">
          <div className="flex items-center justify-between py-3 px-4 bg-emerald-50 dark:bg-emerald-900/20 border border-emerald-200 dark:border-emerald-800 rounded-lg">
            <div>
              <p className="text-sm font-medium text-emerald-900 dark:text-emerald-200">
                Test In-App Notification
              </p>
              <p className="text-xs text-emerald-700 dark:text-emerald-300">
                Send a test notification to your notification center
              </p>
            </div>
            <Button
              type="button"
              variant="secondary"
              onClick={handleSendTestNotification}
              disabled={isSendingTestNotification}
            >
              {isSendingTestNotification ? "Sending..." : "Send Test"}
            </Button>
          </div>

          <div className="flex items-center justify-between py-3 px-4 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg">
            <div>
              <p className="text-sm font-medium text-blue-900 dark:text-blue-200">
                Test Email Notification
              </p>
              <p className="text-xs text-blue-700 dark:text-blue-300">
                Send a test email to verify your settings
              </p>
            </div>
            <Button
              type="button"
              variant="secondary"
              onClick={handleSendTestEmail}
              disabled={isSendingTestEmail}
            >
              {isSendingTestEmail ? "Sending..." : "Send Test"}
            </Button>
          </div>
        </div>

        {/* Save Button */}
        <div className="pt-4 border-t border-gray-200 dark:border-gray-700 flex justify-end">
          <Button
            type="button"
            variant="primary"
            onClick={handleSave}
            disabled={isLoading || !hasChanges()}
          >
            {isLoading ? "Saving..." : "Save Changes"}
          </Button>
        </div>
      </div>
    </div>
  );
};

export default NotificationSettings;

