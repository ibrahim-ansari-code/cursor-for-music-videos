import React, { useState, useEffect } from "react";
import { Label, Checkbox, Select, Button } from "../ui/SharedModalComponents";
import { toast } from "react-toastify";

const NotificationSettings = ({ user, onNotificationUpdate }) => {
  const [notifications, setNotifications] = useState({
    emailEnabled: true,
    categories: {
      rentReminders: true,
      paymentReceived: true,
      leaseExpiring: true,
      maintenanceUpdates: true,
      newTenantApplications: false,
      systemUpdates: false,
    },
    frequency: "immediate",
  });

  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    // In a real app, these would come from user notification preferences API
    const userNotifications = {
      emailEnabled: user?.notifications?.emailEnabled ?? true,
      categories: {
        rentReminders: user?.notifications?.categories?.rentReminders ?? true,
        paymentReceived: user?.notifications?.categories?.paymentReceived ?? true,
        leaseExpiring: user?.notifications?.categories?.leaseExpiring ?? true,
        maintenanceUpdates: user?.notifications?.categories?.maintenanceUpdates ?? true,
        newTenantApplications: user?.notifications?.categories?.newTenantApplications ?? false,
        systemUpdates: user?.notifications?.categories?.systemUpdates ?? false,
      },
      frequency: user?.notifications?.frequency ?? "immediate",
    };
    setNotifications(userNotifications);
  }, [user]);

  const handleToggle = (category) => {
    setNotifications(prev => ({
      ...prev,
      categories: {
        ...prev.categories,
        [category]: !prev.categories[category],
      },
    }));
  };

  const handleEmailToggle = () => {
    setNotifications(prev => ({
      ...prev,
      emailEnabled: !prev.emailEnabled,
    }));
  };

  const handleFrequencyChange = (e) => {
    setNotifications(prev => ({
      ...prev,
      frequency: e.target.value,
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsLoading(true);

    try {
      // ========================================================================
      // 🚧 TEMPORARY SCAFFOLDING - REMOVE WHEN API IS IMPLEMENTED
      // ========================================================================
      // This setTimeout simulates an API call for demo purposes only.
      // Replace this entire block with the actual API call:
      // await updateNotificationPreferences(user.id, notifications);
      // ========================================================================
      
      await new Promise(resolve => setTimeout(resolve, 1000));
      
      // ======================================================================== 
      // END TEMPORARY SCAFFOLDING
      // ========================================================================
      
      toast.success("Notification preferences updated successfully!");
      
      if (onNotificationUpdate) {
        onNotificationUpdate(notifications);
      }
    } catch (error) {
      console.error("Error updating notifications:", error);
      toast.error("Failed to update notification preferences. Please try again.");
    } finally {
      setIsLoading(false);
    }
  };



  return (
    <div>
      <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-6 transition-colors duration-300">Notification Settings</h2>
      
      <form onSubmit={handleSubmit} className="space-y-5">
        {/* Email Notifications Toggle */}
        <div className="bg-gray-50 dark:bg-gray-800 rounded-lg p-4 transition-colors duration-300">
          <Checkbox
            id="emailEnabled"
            name="emailEnabled"
            checked={notifications.emailEnabled}
            onChange={handleEmailToggle}
            disabled
            className="opacity-70"
          >
            <span className="font-medium text-gray-800 dark:text-gray-200 transition-colors duration-300">Enable Email Notifications</span>
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
                checked={notifications.categories.rentReminders}
                onChange={() => handleToggle('rentReminders')}
                disabled
                className="opacity-70"
              >
                <div>
                  <span className="font-medium text-gray-800 dark:text-gray-200 transition-colors duration-300">Rent Reminders</span>
                  <p className="text-sm text-gray-600 dark:text-gray-400 transition-colors duration-300">Get notified about upcoming and overdue rent payments</p>
                </div>
              </Checkbox>

              <Checkbox
                id="paymentReceived"
                checked={notifications.categories.paymentReceived}
                onChange={() => handleToggle('paymentReceived')}
                disabled
                className="opacity-70"
              >
                <div>
                  <span className="font-medium text-gray-800 dark:text-gray-200 transition-colors duration-300">Payment Received</span>
                  <p className="text-sm text-gray-600 dark:text-gray-400 transition-colors duration-300">Notification when tenants make payments</p>
                </div>
              </Checkbox>

              <Checkbox
                id="leaseExpiring"
                checked={notifications.categories.leaseExpiring}
                onChange={() => handleToggle('leaseExpiring')}
                disabled
                className="opacity-70"
              >
                <div>
                  <span className="font-medium text-gray-800 dark:text-gray-200 transition-colors duration-300">Lease Expiring</span>
                  <p className="text-sm text-gray-600 dark:text-gray-400 transition-colors duration-300">Alerts for leases expiring within 60 days</p>
                </div>
              </Checkbox>

              <Checkbox
                id="maintenanceUpdates"
                checked={notifications.categories.maintenanceUpdates}
                onChange={() => handleToggle('maintenanceUpdates')}
                disabled
                className="opacity-70"
              >
                <div>
                  <span className="font-medium text-gray-800 dark:text-gray-200 transition-colors duration-300">Maintenance Updates</span>
                  <p className="text-sm text-gray-600 dark:text-gray-400 transition-colors duration-300">Updates on maintenance requests and work orders</p>
                </div>
              </Checkbox>

              <Checkbox
                id="newTenantApplications"
                checked={notifications.categories.newTenantApplications}
                onChange={() => handleToggle('newTenantApplications')}
                disabled
                className="opacity-70"
              >
                <div>
                  <span className="font-medium text-gray-800 dark:text-gray-200 transition-colors duration-300">New Applications</span>
                  <p className="text-sm text-gray-600 dark:text-gray-400 transition-colors duration-300">Notifications for new rental applications</p>
                </div>
              </Checkbox>

              <Checkbox
                id="systemUpdates"
                checked={notifications.categories.systemUpdates}
                onChange={() => handleToggle('systemUpdates')}
                disabled
                className="opacity-70"
              >
                <div>
                  <span className="font-medium text-gray-800 dark:text-gray-200 transition-colors duration-300">System Updates</span>
                  <p className="text-sm text-gray-600 dark:text-gray-400 transition-colors duration-300">Important announcements and updates</p>
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
            value={notifications.frequency}
            onChange={handleFrequencyChange}
            disabled
            className="max-w-xs"
          >
            <option value="immediate">Immediate</option>
            <option value="daily" disabled>Daily Digest (Coming Soon)</option>
            <option value="weekly" disabled>Weekly Summary (Coming Soon)</option>
          </Select>
          <p className="mt-1.5 text-sm text-gray-600 dark:text-gray-400 transition-colors duration-300">
            Choose how often you want to receive notification emails.
          </p>
        </div>

        {/* Info Box */}
        <div className="bg-amber-50 dark:bg-amber-900/50 border border-amber-200 dark:border-amber-800 rounded-lg p-4 transition-colors duration-300">
          <p className="text-sm text-amber-800 dark:text-amber-200 transition-colors duration-300">
            <i className="fas fa-info-circle mr-2"></i>
            Email notifications are coming soon. You'll be able to customize which updates you receive and how often.
          </p>
        </div>

        <div className="flex justify-end pt-4 border-t border-gray-200 dark:border-gray-700 transition-colors duration-300">
          <Button
            type="submit"
            variant="primary"
            disabled={true}
            title="Notifications are coming soon"
          >
            Save Notifications
          </Button>
        </div>
      </form>
    </div>
  );
};

export default NotificationSettings;