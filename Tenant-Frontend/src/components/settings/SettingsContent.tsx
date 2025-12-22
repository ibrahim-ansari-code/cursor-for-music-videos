import React, { useState, useContext } from 'react';
import { AuthContext } from '@/contexts/AuthContext';
import { useMutation } from '@tanstack/react-query';
import { toast } from 'react-toastify';
import { supabase } from '@/utils/supabaseClient';
import {
  updateProfile,
  type ProfileUpdateRequest,
} from '@/utils/api/settings';
import type { AuthContextValue } from '@/types';
import {
  FiFileText,
  FiShield,
  FiLogOut,
  FiEye,
  FiEyeOff,
  FiLoader,
  FiCheck,
  FiX,
} from 'react-icons/fi';

/**
 * Format phone number as user types: (XXX) XXX-XXXX
 */
const formatPhoneNumber = (value: string): string => {
  // Remove all non-digit characters
  const digits = value.replace(/\D/g, '');

  // Limit to 10 digits
  const limitedDigits = digits.slice(0, 10);

  // Format based on length
  if (limitedDigits.length === 0) {
    return '';
  } else if (limitedDigits.length <= 3) {
    return `(${limitedDigits}`;
  } else if (limitedDigits.length <= 6) {
    return `(${limitedDigits.slice(0, 3)}) ${limitedDigits.slice(3)}`;
  } else {
    return `(${limitedDigits.slice(0, 3)}) ${limitedDigits.slice(3, 6)}-${limitedDigits.slice(6)}`;
  }
};

/**
 * Strip formatting from phone number for API submission
 */
const stripPhoneFormatting = (value: string): string => {
  return value.replace(/\D/g, '');
};

/**
 * Calculate password strength
 */
const getPasswordStrength = (password: string): { strength: number; label: string } => {
  if (!password) return { strength: 0, label: '' };

  let strength = 0;
  if (password.length >= 8) strength++;
  if (password.match(/[A-Z]/)) strength++;
  if (password.match(/[a-z]/)) strength++;
  if (password.match(/[0-9]/)) strength++;
  if (password.match(/[^A-Za-z0-9]/)) strength++;

  const labels = ['', 'Weak', 'Fair', 'Good', 'Strong', 'Very Strong'];
  return { strength, label: labels[strength] };
};

/**
 * Get color class for password strength
 */
const getStrengthColor = (strength: number): string => {
  const colors = ['', 'bg-red-500', 'bg-orange-500', 'bg-yellow-500', 'bg-green-500', 'bg-green-600'];
  return colors[strength];
};

/**
 * SettingsContent Component
 *
 * Main settings page content following the Replit mock design.
 * Layout: Left side (Personal Info + Password) | Right side (Preferences + Account)
 */
const SettingsContent: React.FC = () => {
  const authContext = useContext(AuthContext) as AuthContextValue | null;
  const user = authContext?.user;
  const signOut = authContext?.signOut;
  const refreshUser = authContext?.refreshUser;

  // Form state for personal information
  const [firstName, setFirstName] = useState(user?.first_name || '');
  const [lastName, setLastName] = useState(user?.last_name || '');
  const [email] = useState(user?.email || '');
  const [phone, setPhone] = useState(formatPhoneNumber(user?.phone || ''));

  // Password form state
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showCurrentPassword, setShowCurrentPassword] = useState(false);
  const [showNewPassword, setShowNewPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);

  // Profile update mutation
  const profileMutation = useMutation({
    mutationFn: (data: ProfileUpdateRequest) => {
      if (!user?.id) throw new Error('User not found');
      return updateProfile(user.id, data);
    },
    onSuccess: async () => {
      toast.success('Profile updated successfully');
      // Refresh user data in context
      try {
        if (refreshUser) {
          await refreshUser();
        }
      } catch (e) {
        console.error('Failed to refresh user data:', e);
      }
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Failed to update profile');
    },
  });

  // Password change mutation (using Supabase directly)
  const passwordMutation = useMutation({
    mutationFn: async ({ newPassword }: { newPassword: string }) => {
      const { error } = await supabase.auth.updateUser({
        password: newPassword,
      });
      if (error) throw error;
      return { message: 'Password updated successfully' };
    },
    onSuccess: () => {
      toast.success('Password updated successfully');
      setCurrentPassword('');
      setNewPassword('');
      setConfirmPassword('');
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Failed to change password');
    },
  });

  const handleProfileSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    // Strip formatting from phone number before submitting
    const rawPhone = stripPhoneFormatting(phone);
    profileMutation.mutate({
      first_name: firstName || null,
      last_name: lastName || null,
      phone: rawPhone || null,
    });
  };

  const handlePasswordSubmit = (e: React.FormEvent) => {
    e.preventDefault();

    if (newPassword !== confirmPassword) {
      toast.error('Passwords do not match');
      return;
    }

    if (newPassword.length < 8) {
      toast.error('Password must be at least 8 characters');
      return;
    }

    passwordMutation.mutate({ newPassword });
  };

  const handleLogout = async () => {
    if (signOut) {
      await signOut();
    }
  };

  return (
    <div className="bg-white rounded-lg shadow border border-gray-200">
      <div className="p-6">
        {/* Page Header */}
        <div className="mb-6">
          <h1 className="text-2xl font-semibold text-gray-800">Settings</h1>
          <p className="text-gray-600">Manage your account preferences and information</p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left Column - Forms */}
          <div className="lg:col-span-2 space-y-6">
            {/* Personal Information Card */}
            <div className="border border-gray-200 rounded-lg p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-6">
              Personal Information
            </h2>

            <form onSubmit={handleProfileSubmit}>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
                <div>
                  <label
                    htmlFor="firstName"
                    className="block text-sm font-medium text-gray-700 mb-1"
                  >
                    First Name
                  </label>
                  <input
                    type="text"
                    id="firstName"
                    value={firstName}
                    onChange={(e) => setFirstName(e.target.value)}
                    className="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-teal-500 focus:border-teal-500 outline-none transition-colors"
                    placeholder="Enter your first name"
                  />
                </div>

                <div>
                  <label
                    htmlFor="lastName"
                    className="block text-sm font-medium text-gray-700 mb-1"
                  >
                    Last Name
                  </label>
                  <input
                    type="text"
                    id="lastName"
                    value={lastName}
                    onChange={(e) => setLastName(e.target.value)}
                    className="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-teal-500 focus:border-teal-500 outline-none transition-colors"
                    placeholder="Enter your last name"
                  />
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
                <div>
                  <label
                    htmlFor="email"
                    className="block text-sm font-medium text-gray-700 mb-1"
                  >
                    Email Address
                  </label>
                  <input
                    type="email"
                    id="email"
                    value={email}
                    disabled
                    className="w-full px-4 py-2.5 border border-gray-200 rounded-lg bg-gray-50 text-gray-500 cursor-not-allowed"
                  />
                </div>

                <div>
                  <label
                    htmlFor="phone"
                    className="block text-sm font-medium text-gray-700 mb-1"
                  >
                    Phone Number
                  </label>
                  <input
                    type="tel"
                    id="phone"
                    value={phone}
                    onChange={(e) => setPhone(formatPhoneNumber(e.target.value))}
                    className="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-teal-500 focus:border-teal-500 outline-none transition-colors"
                    placeholder="(555) 123-4567"
                  />
                </div>
              </div>

              <button
                type="submit"
                disabled={profileMutation.isPending}
                className="px-6 py-2.5 bg-gray-900 text-white rounded-lg font-medium hover:bg-gray-800 transition-colors cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
              >
                {profileMutation.isPending ? (
                  <>
                    <FiLoader className="w-4 h-4 animate-spin" />
                    Saving...
                  </>
                ) : (
                  'Save Changes'
                )}
              </button>
            </form>
          </div>

          {/* Password & Security Card */}
          <div className="border border-gray-200 rounded-lg p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-6">
              Password & Security
            </h2>

            <form onSubmit={handlePasswordSubmit}>
              <div className="space-y-4 mb-6">
                <div>
                  <label
                    htmlFor="currentPassword"
                    className="block text-sm font-medium text-gray-700 mb-1"
                  >
                    Current Password
                  </label>
                  <div className="relative">
                    <input
                      type={showCurrentPassword ? 'text' : 'password'}
                      id="currentPassword"
                      value={currentPassword}
                      onChange={(e) => setCurrentPassword(e.target.value)}
                      className="w-full px-4 py-2.5 pr-10 border border-gray-300 rounded-lg focus:ring-2 focus:ring-teal-500 focus:border-teal-500 outline-none transition-colors"
                      placeholder="Enter your current password"
                      autoComplete="current-password"
                    />
                    <button
                      type="button"
                      onClick={() => setShowCurrentPassword(!showCurrentPassword)}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
                    >
                      {showCurrentPassword ? (
                        <FiEyeOff className="w-5 h-5" />
                      ) : (
                        <FiEye className="w-5 h-5" />
                      )}
                    </button>
                  </div>
                </div>

                <div>
                  <label
                    htmlFor="newPassword"
                    className="block text-sm font-medium text-gray-700 mb-1"
                  >
                    New Password
                  </label>
                  <div className="relative">
                    <input
                      type={showNewPassword ? 'text' : 'password'}
                      id="newPassword"
                      value={newPassword}
                      onChange={(e) => setNewPassword(e.target.value)}
                      className="w-full px-4 py-2.5 pr-10 border border-gray-300 rounded-lg focus:ring-2 focus:ring-teal-500 focus:border-teal-500 outline-none transition-colors"
                      placeholder="Enter a new password"
                      autoComplete="new-password"
                    />
                    <button
                      type="button"
                      onClick={() => setShowNewPassword(!showNewPassword)}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
                    >
                      {showNewPassword ? (
                        <FiEyeOff className="w-5 h-5" />
                      ) : (
                        <FiEye className="w-5 h-5" />
                      )}
                    </button>
                  </div>

                  {/* Password strength indicator */}
                  {newPassword && (
                    <div className="mt-2">
                      <div className="flex items-center gap-2">
                        <div className="flex-1 bg-gray-200 rounded-full h-1.5 overflow-hidden">
                          <div
                            className={`h-full transition-all duration-300 ${getStrengthColor(getPasswordStrength(newPassword).strength)}`}
                            style={{ width: `${(getPasswordStrength(newPassword).strength / 5) * 100}%` }}
                          />
                        </div>
                        <span className="text-xs text-gray-500 min-w-[70px] text-right">
                          {getPasswordStrength(newPassword).label}
                        </span>
                      </div>
                    </div>
                  )}
                </div>

                <div>
                  <label
                    htmlFor="confirmPassword"
                    className="block text-sm font-medium text-gray-700 mb-1"
                  >
                    Confirm New Password
                  </label>
                  <div className="relative">
                    <input
                      type={showConfirmPassword ? 'text' : 'password'}
                      id="confirmPassword"
                      value={confirmPassword}
                      onChange={(e) => setConfirmPassword(e.target.value)}
                      className="w-full px-4 py-2.5 pr-10 border border-gray-300 rounded-lg focus:ring-2 focus:ring-teal-500 focus:border-teal-500 outline-none transition-colors"
                      placeholder="Confirm your new password"
                      autoComplete="new-password"
                    />
                    <button
                      type="button"
                      onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
                    >
                      {showConfirmPassword ? (
                        <FiEyeOff className="w-5 h-5" />
                      ) : (
                        <FiEye className="w-5 h-5" />
                      )}
                    </button>
                  </div>
                </div>

                {/* Password requirements */}
                <div className="bg-gray-50 rounded-lg p-3">
                  <p className="text-xs font-medium text-gray-600 mb-2">Password must contain:</p>
                  <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-xs">
                    <div className={`flex items-center gap-1.5 ${newPassword.length >= 8 ? 'text-green-600' : 'text-gray-400'}`}>
                      {newPassword.length >= 8 ? <FiCheck className="w-3 h-3" /> : <FiX className="w-3 h-3" />}
                      8+ characters
                    </div>
                    <div className={`flex items-center gap-1.5 ${newPassword.match(/[A-Z]/) ? 'text-green-600' : 'text-gray-400'}`}>
                      {newPassword.match(/[A-Z]/) ? <FiCheck className="w-3 h-3" /> : <FiX className="w-3 h-3" />}
                      Uppercase letter
                    </div>
                    <div className={`flex items-center gap-1.5 ${newPassword.match(/[a-z]/) ? 'text-green-600' : 'text-gray-400'}`}>
                      {newPassword.match(/[a-z]/) ? <FiCheck className="w-3 h-3" /> : <FiX className="w-3 h-3" />}
                      Lowercase letter
                    </div>
                    <div className={`flex items-center gap-1.5 ${newPassword.match(/[0-9]/) ? 'text-green-600' : 'text-gray-400'}`}>
                      {newPassword.match(/[0-9]/) ? <FiCheck className="w-3 h-3" /> : <FiX className="w-3 h-3" />}
                      Number
                    </div>
                    <div className={`flex items-center gap-1.5 col-span-2 ${newPassword.match(/[^A-Za-z0-9]/) ? 'text-green-600' : 'text-gray-400'}`}>
                      {newPassword.match(/[^A-Za-z0-9]/) ? <FiCheck className="w-3 h-3" /> : <FiX className="w-3 h-3" />}
                      Special character
                    </div>
                  </div>
                </div>
              </div>

              <button
                type="submit"
                disabled={
                  passwordMutation.isPending ||
                  !currentPassword ||
                  !newPassword ||
                  !confirmPassword ||
                  newPassword.length < 8
                }
                className="px-6 py-2.5 bg-gray-900 text-white rounded-lg font-medium hover:bg-gray-800 transition-colors cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
              >
                {passwordMutation.isPending ? (
                  <>
                    <FiLoader className="w-4 h-4 animate-spin" />
                    Updating...
                  </>
                ) : (
                  'Update Password'
                )}
              </button>
            </form>
          </div>
        </div>

        {/* Right Column - Sidebars */}
        <div className="space-y-6">
          {/* Account Card */}
          <div className="border border-gray-200 rounded-lg p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">Account</h2>

            <div className="space-y-1">
              <a
                href="https://brikli.com/terms-and-conditions"
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-3 px-3 py-2.5 text-sm text-gray-700 hover:bg-gray-50 rounded-lg transition-colors"
              >
                <FiFileText className="w-4 h-4 text-gray-400" />
                Terms of Service
              </a>

              <a
                href="https://brikli.com/privacy-policy"
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-3 px-3 py-2.5 text-sm text-gray-700 hover:bg-gray-50 rounded-lg transition-colors"
              >
                <FiShield className="w-4 h-4 text-gray-400" />
                Privacy Policy
              </a>

              <button
                type="button"
                onClick={handleLogout}
                className="flex items-center gap-3 px-3 py-2.5 text-sm text-red-600 hover:bg-red-50 rounded-lg transition-colors w-full text-left cursor-pointer"
              >
                <FiLogOut className="w-4 h-4" />
                Log Out
              </button>
            </div>
          </div>
        </div>
      </div>
      </div>
    </div>
  );
};

export default SettingsContent;
