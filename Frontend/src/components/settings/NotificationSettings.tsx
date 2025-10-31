import React, { useState, useEffect } from "react";
import { Label, Checkbox, Select, Button } from "../ui/SharedModalComponents";
import { toast } from "react-toastify";
import * as Sentry from "@sentry/react";
import { getPreferences, updatePreferences, sendTestEmail, type NotificationPreferenceResponse } from "../../utils/api/notifications";
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

const NotificationSettings: React.FC<NotificationSettingsProps> = ({ onNotificationUpdate }) => {
  const [preferences, setPreferences] = useState<NotificationPreferenceResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isFetchLoading, setIsFetchLoading] = useState(true);
  const [isSendingTest, setIsSendingTest] = useState(false);

  // Fetch user preferences on mount
  useEffect(() => {
    const fetchPreferences = async () => {
      setIsFetchLoading(true);
      try {
        const prefs = await getPreferences();
        setPreferences(prefs);
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

  const handleToggleCategory = (category: string) => {
    if (!preferences) return;

    setPreferences((prev: NotificationPreferenceResponse | null) => {
      if (!prev) return prev;
      return {
        ...prev,
        preferences: {
          ...prev.preferences,
          [category]: {
            ...prev.preferences[category],
            enabled: !prev.preferences[category]?.enabled,
          },
        },
      };
    });
  };

  const handleToggleEmail = () => {
    if (!preferences) return;

    setPreferences((prev: NotificationPreferenceResponse | null) => {
      if (!prev) return prev;
      return {
        ...prev,
        enabled: !prev.enabled,
      };
    });
  };

  const handleFrequencyChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    if (!preferences) return;

    setPreferences((prev: NotificationPreferenceResponse | null) => {
      if (!prev) return prev;
      return {
        ...prev,
        email_digest_frequency: e.target.value as NotificationPreferenceResponse['email_digest_frequency'],
      };
    });
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!preferences) {
      toast.error("No preferences to save");
      return;
    }

    setIsLoading(true);

    try {
      await updatePreferences({
        enabled: preferences.enabled,
        preferences: preferences.preferences,
        email_digest_frequency: preferences.email_digest_frequency,
      });
      
      toast.success("Notification preferences updated successfully!");
      
      if (onNotificationUpdate) {
        onNotificationUpdate(preferences);
      }
    } catch (error) {
      console.error("Error updating notifications:", error);
      Sentry.captureException(error, {
        tags: {
          component: 'NotificationSettings',
          action: 'update_preferences',
        },
      });
      toast.error("Failed to update notification preferences. Please try again.");
    } finally {
      setIsLoading(false);
    }
  };

  const handleSendTestEmail = async () => {
    setIsSendingTest(true);
    try {
      await sendTestEmail();
      toast.success("Test email sent! Check your inbox.");
    } catch (error) {
      console.error("Error sending test email:", error);
      Sentry.captureException(error, {
        tags: {
          component: 'NotificationSettings',
          action: 'send_test_email',
        },
      });
      toast.error("Failed to send test email. Please try again.");
    } finally {
      setIsSendingTest(false);
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
      <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-6 transition-colors duration-300">
        Notification Settings
      </h2>
      
      <form onSubmit={handleSubmit} className="space-y-5">
        {/* Email Notifications Toggle */}
        <div className="bg-gray-50 dark:bg-gray-800 rounded-lg p-4 transition-colors duration-300">
          <Checkbox
            id="emailEnabled"
            name="emailEnabled"
            checked={preferences.enabled}
            onChange={handleToggleEmail}
          >
            <span className="font-medium text-gray-800 dark:text-gray-200 transition-colors duration-300">
              Enable Email Notifications
            </span>
          </Checkbox>
          <p className="text-sm text-gray-600 dark:text-gray-400 ml-6 mt-1 transition-colors duration-300">
            Receive important updates and reminders via email.
          </p>
        </div>

        {/* Notification Categories */}
        <div>
          <Label className="text-base font-medium text-gray-900 dark:text-white mb-4 block transition-colors duration-300">
            <i className="fas fa-bell mr-2 text-gray-500 dark:text-gray-400 transition-colors duration-300"></i>
            Notification Categories
          </Label>
          
          <div className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <Checkbox
                id="rentReminders"
                checked={preferences.preferences.rent_reminder?.enabled ?? true}
                onChange={() => handleToggleCategory('rent_reminder')}
              >
                <div>
                  <span className="font-medium text-gray-800 dark:text-gray-200 transition-colors duration-300">
                    💰 Rent Reminders
                  </span>
                  <p className="text-sm text-gray-600 dark:text-gray-400 transition-colors duration-300">
                    Get notified about upcoming rent payments 3 days before they're due
                  </p>
                </div>
              </Checkbox>

              <Checkbox
                id="leaseExpiring"
                checked={preferences.preferences.lease_expiring?.enabled ?? true}
                onChange={() => handleToggleCategory('lease_expiring')}
              >
                <div>
                  <span className="font-medium text-gray-800 dark:text-gray-200 transition-colors duration-300">
                    📅 Lease Expiring
                  </span>
                  <p className="text-sm text-gray-600 dark:text-gray-400 transition-colors duration-300">
                    Alerts for leases expiring within 30 and 60 days
                  </p>
                </div>
              </Checkbox>

              <Checkbox
                id="systemUpdates"
                checked={preferences.preferences.system_update?.enabled ?? false}
                onChange={() => handleToggleCategory('system_update')}
              >
                <div>
                  <span className="font-medium text-gray-800 dark:text-gray-200 transition-colors duration-300">
                    🔔 System Updates
                  </span>
                  <p className="text-sm text-gray-600 dark:text-gray-400 transition-colors duration-300">
                    Important platform announcements and new features
                  </p>
                </div>
              </Checkbox>
            </div>
          </div>
        </div>

        {/* Notification Frequency */}
        <div>
          <Label htmlFor="frequency">
            <i className="fas fa-clock mr-2 text-gray-500 dark:text-gray-400 transition-colors duration-300"></i>
            Notification Frequency
          </Label>
          <Select
            id="frequency"
            name="frequency"
            value={preferences.email_digest_frequency}
            onChange={handleFrequencyChange}
            className="max-w-xs"
          >
            <option value="immediate">Immediate</option>
            <option value="hourly">Hourly Digest</option>
            <option value="daily">Daily Digest</option>
            <option value="weekly">Weekly Summary</option>
            <option value="never">Never</option>
          </Select>
          <p className="mt-1.5 text-sm text-gray-600 dark:text-gray-400 transition-colors duration-300">
            Choose how often you want to receive notification emails.
          </p>
        </div>

        {/* Test Email Button */}
        <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4 transition-colors duration-300">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-blue-900 dark:text-blue-200">
                <i className="fas fa-envelope mr-2"></i>
                Test Email Notifications
              </p>
              <p className="text-xs text-blue-700 dark:text-blue-300 mt-1">
                Send a test email to verify your settings
              </p>
            </div>
            <Button
              type="button"
              variant="secondary"
              onClick={handleSendTestEmail}
              disabled={isSendingTest || !preferences.enabled}
            >
              {isSendingTest ? "Sending..." : "Send Test"}
            </Button>
          </div>
        </div>

        <div className="flex justify-end pt-4 border-t border-gray-200 dark:border-gray-700 transition-colors duration-300">
          <Button
            type="submit"
            variant="primary"
            disabled={isLoading}
          >
            {isLoading ? "Saving..." : "Save Notifications"}
          </Button>
        </div>
      </form>
    </div>
  );
};

export default NotificationSettings;

