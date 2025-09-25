import React, { useState, useEffect } from "react";
import { Label, Select, Button } from "../ui/SharedModalComponents";
import { toast } from "react-toastify";
import { useTheme } from "../../contexts/ThemeSwitch";

const PreferencesForm = ({ user, onPreferencesUpdate }) => {
  const { theme, setTheme, effectiveTheme, isSystemTheme } = useTheme();

  const [preferences, setPreferences] = useState({
    theme: theme,
    language: "en",
    dateFormat: "MM/DD/YYYY",
    timezone: "America/New_York",
  });
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    setPreferences(prev => ({
      ...prev,
      theme: theme,
    }));

    // In a real app, these would come from user preferences API
    const userPreferences = {
      language: user?.preferences?.language || "en",
      dateFormat: user?.preferences?.dateFormat || "MM/DD/YYYY",
      timezone: user?.preferences?.timezone || "America/New_York",
    };
    setPreferences(prev => ({ ...prev, ...userPreferences }));
  }, [user?.preferences, theme]);

  const handleChange = (e) => {
    const { name, value } = e.target;
    setPreferences(prev => ({ ...prev, [name]: value }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    // Prevent multiple submissions
    if (isSubmitting) return;
    
    setIsSubmitting(true);

    try {
      // Apply theme change immediately
      if (preferences.theme !== theme) {
        setTheme(preferences.theme);
      }

      // In a real app, this would call an API to save preferences
      console.log("Saving preferences:", preferences);
      
      // Simulate API call delay
      await new Promise(resolve => setTimeout(resolve, 500));
      
      toast.success("Preferences updated successfully! Theme has been applied.", {
        position: "top-right",
        autoClose: 3000,
        hideProgressBar: false,
        closeOnClick: true,
        pauseOnHover: true,
        draggable: true,
      });
      
      if (onPreferencesUpdate) {
        onPreferencesUpdate(preferences);
      }
    } catch (error) {
      console.error("Error updating preferences:", error);
      toast.error("Failed to update preferences. Please try again.");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div>
      <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-100 mb-6">Preferences</h2>
      
      <form onSubmit={handleSubmit} className="space-y-5">
        {/* Display Preferences */}
        <div>
          <h3 className="text-base font-medium text-gray-900 dark:text-gray-100 mb-8 block">
            <i className="fas fa-palette mr-2 text-gray-500 dark:text-gray-400"></i>
            Display Settings
          </h3>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
            <div>
              <Label htmlFor="theme">Theme</Label>
              <Select
                id="theme"
                name="theme"
                value={preferences.theme}
                onChange={handleChange}
                className="bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 border-gray-300 dark:border-gray-600 focus:ring-blue-500 focus:border-blue-500"
              >
                <option value="light">Light</option>
                <option value="dark">Dark</option>
                <option value="system">System (Auto)</option>
              </Select>
              <p className="mt-1.5 text-sm text-gray-600 dark:text-gray-400">
                {isSystemTheme 
                  ? `System theme detected: ${effectiveTheme}. Changes automatically with your device settings.`
                  : "Choose your preferred theme. System option follows your device's theme."
                }
              </p>
            </div>

            <div>
              <Label htmlFor="language">Language</Label>
              <Select
                id="language"
                name="language"
                value={preferences.language}
                disabled
                className="bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 border-gray-300 dark:border-gray-600 opacity-50 cursor-not-allowed"
              >
                <option value="en">English</option>
                <option value="es" disabled>Spanish (Coming Soon)</option>
                <option value="fr" disabled>French (Coming Soon)</option>
              </Select>
              <p className="mt-1.5 text-sm text-gray-600 dark:text-gray-400">
                Additional languages will be available soon.
              </p>
            </div>
          </div>
        </div>

        {/* Divider */}
        <div className="border-t border-gray-200 dark:border-gray-700"></div>

        {/* Regional Settings */}
        <div>
          <h3 className="text-base font-medium text-gray-900 dark:text-gray-100 mb-8 block">
            <i className="fas fa-globe mr-2 text-gray-500 dark:text-gray-400"></i>
            Regional Settings
          </h3>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
            <div>
              <Label htmlFor="dateFormat">
                <i className="fas fa-calendar mr-1.5 text-gray-500 dark:text-gray-400"></i>
                Date Format
              </Label>
              <Select
                id="dateFormat"
                name="dateFormat"
                value={preferences.dateFormat}
                disabled
                className="bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 border-gray-300 dark:border-gray-600 opacity-50 cursor-not-allowed"
              >
                <option value="MM/DD/YYYY">MM/DD/YYYY (Coming Soon)</option>
                <option value="DD/MM/YYYY">DD/MM/YYYY (Coming Soon)</option>
                <option value="YYYY-MM-DD">YYYY-MM-DD (Coming Soon)</option>
              </Select>
              <p className="mt-1.5 text-sm text-gray-600 dark:text-gray-400">
                Date formatting will be customizable soon.
              </p>
            </div>

            <div>
              <Label htmlFor="timezone">
                <i className="fas fa-clock mr-1.5 text-gray-500 dark:text-gray-400"></i>
                Timezone
              </Label>
              <Select
                id="timezone"
                name="timezone"
                value={preferences.timezone}
                disabled
                className="bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 border-gray-300 dark:border-gray-600 opacity-50 cursor-not-allowed"
              >
                <option value="America/New_York">Eastern Time (ET)</option>
                <option value="America/Chicago" disabled>Central Time (CT) - Coming Soon</option>
                <option value="America/Denver" disabled>Mountain Time (MT) - Coming Soon</option>
                <option value="America/Los_Angeles" disabled>Pacific Time (PT) - Coming Soon</option>
              </Select>
              <p className="mt-1.5 text-sm text-gray-600 dark:text-gray-400">
                Timezone support will be available soon.
              </p>
            </div>
          </div>
        </div>

        {/* Current Theme Status */}
        <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4">
          <div className="flex items-start">
            <i className="fas fa-info-circle mr-2 text-blue-600 dark:text-blue-400 mt-0.5"></i>
            <div>
              <p className="text-sm text-blue-800 dark:text-blue-200 font-medium mb-1">
                Current Theme: {effectiveTheme === 'light' ? '☀️ Light' : '🌙 Dark'}
                {isSystemTheme && ' (System)'}
              </p>
              <p className="text-sm text-blue-700 dark:text-blue-300">
                {isSystemTheme 
                  ? 'Your theme automatically changes based on your device settings. You can override this by selecting Light or Dark above.'
                  : 'Theme preferences are saved and will persist across sessions. Select "System (Auto)" to follow your device settings.'
                }
              </p>
            </div>
          </div>
        </div>

        <div className="flex justify-end pt-4 border-t border-gray-200 dark:border-gray-700">
          <Button
            type="submit"
            variant="primary"
            disabled={isSubmitting}
            title="Save your preferences"
            className={`
              px-6 py-2 rounded-md font-medium transition-all duration-200
              ${isSubmitting 
                ? 'bg-blue-400 dark:bg-blue-600 cursor-not-allowed' 
                : 'bg-blue-600 hover:bg-blue-700 dark:bg-blue-500 dark:hover:bg-blue-600 hover:shadow-md'
              } 
              text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 dark:focus:ring-offset-gray-800
            `}
          >
            {isSubmitting ? (
              <>
                <i className="fas fa-spinner fa-spin mr-2"></i>
                Saving...
              </>
            ) : (
              <>
                <i className="fas fa-save mr-2"></i>
                Save Preferences
              </>
            )}
          </Button>
        </div>
      </form>
    </div>
  );
};

export default PreferencesForm;