import React, { useState, useContext, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import { AuthContext } from '../contexts/AuthContext';
import type { User, AvatarUpdateHandler, ProfileUpdateHandler } from '../types/user';
import SettingsSkeleton from '../components/ui/skeletons/SettingsSkeleton';

// Import settings components
import ProfileCard from '../components/settings/ProfileCard';
import ProfileForm from '../components/settings/ProfileForm';
import SecurityForm from '../components/settings/SecurityForm';
import PreferencesForm from '../components/settings/PreferencesForm';
import NotificationSettings from '../components/settings/NotificationSettings';
import OwnershipEntitiesSettings from '../components/settings/OwnershipEntitiesSettings';
import BillingSettings from '../components/settings/BillingSettings';

interface Tab {
  id: 'profile' | 'security' | 'preferences' | 'notifications' | 'ownership' | 'billing';
  label: string;
  icon: string;
}

type TabId = Tab['id'];

interface AuthContextValue {
  user: User | null;
  setUser: React.Dispatch<React.SetStateAction<User | null>>;
}

const Settings: React.FC = () => {
  const authContext = useContext(AuthContext) as AuthContextValue | null;
  const authUser = authContext?.user;
  const setAuthUser = authContext?.setUser;
  
  const [searchParams] = useSearchParams();
  const [activeTab, setActiveTab] = useState<TabId>('profile');

  // Set active tab from URL query parameter
  useEffect(() => {
    const tabParam = searchParams.get('tab');
    if (tabParam && ['profile', 'security', 'preferences', 'notifications', 'ownership', 'billing'].includes(tabParam)) {
      setActiveTab(tabParam as TabId);
    }
  }, [searchParams]);

  // Tab configuration
  const tabs: Tab[] = [
    { id: 'profile', label: 'Profile', icon: 'fa-user' },
    { id: 'security', label: 'Security', icon: 'fa-lock' },
    { id: 'billing', label: 'Billing', icon: 'fa-credit-card' },
    { id: 'preferences', label: 'Preferences', icon: 'fa-cog' },
    { id: 'notifications', label: 'Notifications', icon: 'fa-bell' },
    { id: 'ownership', label: 'Ownership Entities', icon: 'fa-briefcase' },
  ];

  // Handle avatar update from ProfileCard
  const handleAvatarUpdate: AvatarUpdateHandler = (newImageUrl: string) => {
    if (setAuthUser) {
      setAuthUser(prev => prev ? { ...prev, profile_image_url: newImageUrl } : prev);
    }
  };

  // Handle profile update from ProfileForm
  const handleProfileUpdate: ProfileUpdateHandler = (updatedData: Partial<User>) => {
    if (setAuthUser) {
      setAuthUser(prev => prev ? { ...prev, ...updatedData } : prev);
    }
  };

  // Handle preferences update
  const handlePreferencesUpdate = (preferences: Record<string, unknown>) => {
    // Update user preferences in context if needed
    // TODO: Implement preference updates in auth context when backend supports it
    console.log('Preferences update:', preferences);
  };

  // Handle notification update
  const handleNotificationUpdate = (notifications: unknown) => {
    // Update notification preferences in context if needed
    // Notification preferences are managed by the NotificationContext
    console.log('Notifications update:', notifications);
  };

  // Loading state
  if (!authUser) {
    return <SettingsSkeleton />;
  }

  return (
    <div className="min-h-screen dark-bg transition-colors duration-300">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        {/* Tab Navigation */}
        <div className="dark-panel dark-shadow rounded-lg transition-colors duration-300">
          <div className="dark-divider border-b">
            <nav className="flex space-x-8 px-6" aria-label="Settings tabs" role="tablist">
              {tabs.map(tab => (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`
                    py-4 px-1 border-b-2 font-medium text-sm flex items-center gap-2 transition-all duration-200
                    ${activeTab === tab.id 
                      ? 'border-blue-500 text-blue-600 dark:text-blue-400' 
                      : 'border-transparent text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300 hover:border-gray-300 dark:hover:border-gray-600'}
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

                  {activeTab === 'ownership' && (
                    <OwnershipEntitiesSettings />
                  )}

                  {activeTab === 'billing' && (
                    <BillingSettings />
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
