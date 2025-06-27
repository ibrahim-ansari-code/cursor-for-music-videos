import React, { useState, useEffect } from "react";
import { Label, Select, Button } from "../ui/SharedModalComponents";
import { toast } from "react-toastify";

const PreferencesForm = ({ user, onPreferencesUpdate }) => {
  const [preferences, setPreferences] = useState({
    theme: "light",
    language: "en",
    dateFormat: "MM/DD/YYYY",
    timezone: "America/New_York",
  });
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    // In a real app, these would come from user preferences API
    const userPreferences = {
      theme: user?.preferences?.theme || "light",
      language: user?.preferences?.language || "en",
      dateFormat: user?.preferences?.dateFormat || "MM/DD/YYYY",
      timezone: user?.preferences?.timezone || "America/New_York",
    };
    setPreferences(userPreferences);
  }, [user?.preferences]);

  const handleChange = (e) => {
    const { name, value } = e.target;
    setPreferences(prev => ({ ...prev, [name]: value }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    // Since all fields are disabled and this feature is "coming soon", 
    // prevent form submission entirely
    return;
    
    // The code below is kept for future use when the feature is enabled
    /*
    // Prevent multiple submissions
    if (isSubmitting) return;
    
    setIsSubmitting(true);

    try {
      // In a real app, this would call an API to save preferences
      // await updateUserPreferences(user.id, preferences);
      
      // Removed artificial delay that could cause UI jank
      
      toast.success("Preferences updated successfully!");
      
      if (onPreferencesUpdate) {
        onPreferencesUpdate(preferences);
      }
    } catch (error) {
      console.error("Error updating preferences:", error);
      toast.error("Failed to update preferences. Please try again.");
    } finally {
      setIsSubmitting(false);
    }
    */
  };

  return (
    <div>
      <h2 className="text-xl font-semibold text-gray-900 mb-6">Preferences</h2>
      
      <form onSubmit={handleSubmit} className="space-y-5">
        {/* Display Preferences */}
        <div>
          <h3 className="text-base font-medium text-gray-900 mb-8 block">
            <i className="fas fa-palette mr-2 text-gray-500"></i>
            Display Settings
          </h3>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
            <div>
              <Label htmlFor="theme">Theme</Label>
              <Select
                id="theme"
                name="theme"
                value={preferences.theme}
                disabled
              >
                <option value="light">Light</option>
                <option value="dark" disabled>Dark (Coming Soon)</option>
                <option value="auto" disabled>Auto (Coming Soon)</option>
              </Select>
              <p className="mt-1.5 text-sm text-gray-600">
                Dark mode will be available in a future update.
              </p>
            </div>

            <div>
              <Label htmlFor="language">Language</Label>
              <Select
                id="language"
                name="language"
                value={preferences.language}
                disabled
              >
                <option value="en">English</option>
                <option value="es" disabled>Spanish (Coming Soon)</option>
                <option value="fr" disabled>French (Coming Soon)</option>
              </Select>
              <p className="mt-1.5 text-sm text-gray-600">
                Additional languages will be available soon.
              </p>
            </div>
          </div>
        </div>

        {/* Divider */}
        <div className="border-t border-gray-200"></div>

        {/* Regional Settings */}
        <div>
          <h3 className="text-base font-medium text-gray-900 mb-8 block">
            <i className="fas fa-globe mr-2 text-gray-500"></i>
            Regional Settings
          </h3>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
            <div>
              <Label htmlFor="dateFormat">
                <i className="fas fa-calendar mr-1.5 text-gray-500"></i>
                Date Format
              </Label>
              <Select
                id="dateFormat"
                name="dateFormat"
                value={preferences.dateFormat}
                disabled
              >
                <option value="MM/DD/YYYY">MM/DD/YYYY (Coming Soon)</option>
                <option value="DD/MM/YYYY">DD/MM/YYYY (Coming Soon)</option>
                <option value="YYYY-MM-DD">YYYY-MM-DD (Coming Soon)</option>
              </Select>
              <p className="mt-1.5 text-sm text-gray-600">
                Date formatting will be customizable soon.
              </p>
            </div>

            <div>
              <Label htmlFor="timezone">
                <i className="fas fa-clock mr-1.5 text-gray-500"></i>
                Timezone
              </Label>
              <Select
                id="timezone"
                name="timezone"
                value={preferences.timezone}
                disabled
              >
                <option value="America/New_York">Eastern Time (ET)</option>
                <option value="America/Chicago" disabled>Central Time (CT) - Coming Soon</option>
                <option value="America/Denver" disabled>Mountain Time (MT) - Coming Soon</option>
                <option value="America/Los_Angeles" disabled>Pacific Time (PT) - Coming Soon</option>
              </Select>
              <p className="mt-1.5 text-sm text-gray-600">
                Timezone support will be available soon.
              </p>
            </div>
          </div>
        </div>

        {/* Info Box */}
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
          <div className="flex items-start">
            <i className="fas fa-info-circle mr-2 text-blue-600 mt-0.5"></i>
            <div>
              <p className="text-sm text-blue-800 font-medium mb-1">
                Preferences Coming Soon
              </p>
              <p className="text-sm text-blue-700">
                We're working on bringing you customizable themes, multiple language support, and regional settings. 
                These features will help personalize your Brikli experience.
              </p>
            </div>
          </div>
        </div>

        <div className="flex justify-end pt-4 border-t border-gray-200">
          <Button
            type="submit"
            variant="primary"
            disabled={true}
            title="Preferences are coming soon"
          >
            {isSubmitting ? 'Saving...' : 'Save Preferences'}
          </Button>
        </div>
      </form>
    </div>
  );
};

export default PreferencesForm;