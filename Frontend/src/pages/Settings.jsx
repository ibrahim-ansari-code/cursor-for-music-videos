import React, { useState, useContext } from "react";
import { AuthContext } from "../contexts/AuthContext";
import { toast } from "react-toastify";
import SettingsSkeleton from "../components/ui/skeletons/SettingsSkeleton";

// Import settings components
import ProfileCard from "../components/settings/ProfileCard";
import ProfileForm from "../components/settings/ProfileForm";
import SecurityForm from "../components/settings/SecurityForm";
import PreferencesForm from "../components/settings/PreferencesForm";
import NotificationSettings from "../components/settings/NotificationSettings";

const Settings = () => {
  const { user: authUser, setUser: setAuthUser } = useContext(AuthContext);
  const [activeTab, setActiveTab] = useState('profile');

  // Tab configuration
  const tabs = [
    { id: 'profile', label: 'Profile', icon: 'fa-user' },
    { id: 'security', label: 'Security', icon: 'fa-lock' },
    { id: 'preferences', label: 'Preferences', icon: 'fa-cog' },
    { id: 'notifications', label: 'Notifications', icon: 'fa-bell' },
  ];

  // Handle avatar update from ProfileCard
  const handleAvatarUpdate = (newImageUrl) => {
    setAuthUser(prev => ({ ...prev, profile_image_url: newImageUrl }));
  };

  // Handle profile update from ProfileForm
  const handleProfileUpdate = (updatedData) => {
    setAuthUser(prev => ({ ...prev, ...updatedData }));
  };

  // Handle preferences update
  const handlePreferencesUpdate = (preferences) => {
    // Update user preferences in context if needed
    // TODO: Implement preference updates in auth context when backend supports it
  };

  // Handle notification update
  const handleNotificationUpdate = (notifications) => {
    // Update notification preferences in context if needed
    // TODO: Implement notification updates in auth context when backend supports it
  };

  // Loading state
  if (!authUser) {
    return <SettingsSkeleton />;
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        {/* Tab Navigation */}
        <div className="bg-white rounded-lg shadow-sm">
          <div className="border-b border-gray-200">
            <nav className="flex space-x-8 px-6" aria-label="Settings tabs" role="tablist">
              {tabs.map(tab => (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`
                    py-4 px-1 border-b-2 font-medium text-sm flex items-center gap-2 transition-all duration-200
                    ${activeTab === tab.id 
                      ? 'border-blue-500 text-blue-600' 
                      : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'}
                  `}
                  role="tab"
                  aria-selected={activeTab === tab.id}
                  aria-controls={`${tab.id}-panel`}
                  aria-label={`${tab.label} settings`}
                >
                  <i className={`fas ${tab.icon}`}></i>
                  {tab.label}
                </button>
              ))}
            </nav>
          </div>

          {/* Content Area */}
          <div className="p-6">
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
              {/* Left Sidebar - Profile Card */}
              <div className="lg:col-span-4 xl:col-span-3">
                <ProfileCard 
                  user={authUser} 
                  onAvatarUpdate={handleAvatarUpdate}
                />
              </div>

              {/* Right Content Area */}
              <div className="lg:col-span-8 xl:col-span-9">
                <div className="min-h-[600px]" role="tabpanel" id={`${activeTab}-panel`}>
                  {activeTab === 'profile' && (
                    <ProfileForm 
                      user={authUser} 
                      onProfileUpdate={handleProfileUpdate}
                    />
                  )}
                  
                  {activeTab === 'security' && (
                    <SecurityForm user={authUser} />
                  )}
                  
                  {activeTab === 'preferences' && (
                    <PreferencesForm 
                      user={authUser} 
                      onPreferencesUpdate={handlePreferencesUpdate}
                    />
                  )}
                  
                  {activeTab === 'notifications' && (
                    <NotificationSettings 
                      user={authUser} 
                      onNotificationUpdate={handleNotificationUpdate}
                    />
                  )}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Settings;
