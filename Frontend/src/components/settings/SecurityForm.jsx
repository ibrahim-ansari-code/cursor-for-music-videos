import React, { useState, useEffect } from "react";
import { Label, Input, Button } from "../ui/SharedModalComponents";
import { supabase } from "../../supabaseClient";
import { toast } from "react-toastify";

/**
 * SecurityForm Component
 * 
 * Handles password changes with Supabase's "Secure password change" feature enabled.
 * 
 * Flow:
 * 1. First attempts to update password directly (works if user logged in within 24 hours)
 * 2. If reauthentication is required, verifies current password
 * 3. Sends a 6-digit verification code to the user's email
 * 4. Collects the code via modal and completes the password update
 * 
 * ⚠️ SECURITY WARNING: Current password verification uses signInWithPassword which creates 
 * a new session and may log out other devices. This is a temporary implementation.
 * 
 * TODO: Implement proper password verification:
 * 1. Create backend endpoint POST /api/auth/verify-password that validates password without creating session
 * 2. Add rate limiting to prevent brute force attacks
 * 3. Replace signInWithPassword call with the new endpoint
 */

const SecurityForm = ({ user }) => {
  const [passwordData, setPasswordData] = useState({
    currentPassword: "",
    newPassword: "",
    confirmPassword: "",
  });
  const [isLoading, setIsLoading] = useState(false);
  const [errors, setErrors] = useState({});
  const [showCurrentPassword, setShowCurrentPassword] = useState(false);
  const [showNewPassword, setShowNewPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [reauthNonce, setReauthNonce] = useState("");
  const [showReauthModal, setShowReauthModal] = useState(false);
  const [pendingPasswordData, setPendingPasswordData] = useState(null);

  // Handle escape key to close modal
  useEffect(() => {
    const handleEscape = (e) => {
      if (e.key === 'Escape' && showReauthModal) {
        setShowReauthModal(false);
        setReauthNonce("");
        setPendingPasswordData(null);
      }
    };

    if (showReauthModal) {
      document.addEventListener('keydown', handleEscape);
    }

    return () => {
      document.removeEventListener('keydown', handleEscape);
    };
  }, [showReauthModal]);

  const handlePasswordChange = (e) => {
    const { name, value } = e.target;
    setPasswordData(prev => ({ ...prev, [name]: value }));
    // Clear errors as user types
    if (errors[name]) {
      setErrors(prev => ({ ...prev, [name]: null }));
    }
  };

  const getPasswordStrength = (password) => {
    if (!password) return { strength: 0, label: "" };
    
    let strength = 0;
    if (password.length >= 8) strength++;
    if (password.match(/[A-Z]/)) strength++;
    if (password.match(/[a-z]/)) strength++;
    if (password.match(/[0-9]/)) strength++;
    if (password.match(/[^A-Za-z0-9]/)) strength++;

    const labels = ["", "Weak", "Fair", "Good", "Strong", "Very Strong"];
    return { strength, label: labels[strength] };
  };

  const passwordStrength = getPasswordStrength(passwordData.newPassword);

  const validateForm = () => {
    const newErrors = {};
    
    if (!passwordData.currentPassword) {
      newErrors.currentPassword = "Current password is required";
    }
    
    if (!passwordData.newPassword) {
      newErrors.newPassword = "New password is required";
    } else if (passwordData.newPassword.length < 8) {
      newErrors.newPassword = "Password must be at least 8 characters long";
    } else if (passwordData.newPassword === passwordData.currentPassword) {
      newErrors.newPassword = "New password must be different from current password";
    }
    
    if (!passwordData.confirmPassword) {
      newErrors.confirmPassword = "Please confirm your password";
    } else if (passwordData.newPassword !== passwordData.confirmPassword) {
      newErrors.confirmPassword = "Passwords do not match";
    }
    
    return newErrors;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    const validationErrors = validateForm();
    if (Object.keys(validationErrors).length > 0) {
      setErrors(validationErrors);
      return;
    }

    setIsLoading(true);
    setErrors({});

    try {
      // First, try to update the password directly
      // This will succeed if the user has recently logged in (within 24 hours)
      const { error: updateError } = await supabase.auth.updateUser({
        password: passwordData.newPassword
      });

      if (updateError) {
        // Check if reauthentication is required
        if (updateError.message && 
            (updateError.message.includes('reauthenticate') || 
             updateError.message.includes('New password should be different from the old password'))) {
          
          // Verify current password first
          // ⚠️ WARNING: This creates a new session and may log out other devices
          // TODO: Replace with backend password verification endpoint
          const { error: verifyError } = await supabase.auth.signInWithPassword({
            email: user.email,
            password: passwordData.currentPassword,
          });

          if (verifyError) {
            setErrors({ currentPassword: "Current password is incorrect" });
            setIsLoading(false);
            return;
          }

          // Send reauthentication nonce
          const { error: reauthError } = await supabase.auth.reauthenticate();
          
          if (reauthError) {
            throw new Error("Failed to send verification code. Please try again.");
          }

          // Save password data and show modal for nonce input
          setPendingPasswordData(passwordData);
          setShowReauthModal(true);
          setIsLoading(false);
          toast.info("A verification code has been sent to your email. Please check your inbox.");
          return;
        }
        throw updateError;
      }

      // Password updated successfully without needing reauthentication
      toast.success("Password updated successfully!");
      setPasswordData({ 
        currentPassword: "", 
        newPassword: "", 
        confirmPassword: "" 
      });
    } catch (error) {
      console.error("Error changing password:", error);
      const errorMessage = error.message || "Failed to update password";
      toast.error(errorMessage);
      setErrors({ form: errorMessage });
    } finally {
      setIsLoading(false);
    }
  };

  const handleReauthSubmit = async () => {
    if (!reauthNonce || reauthNonce.length !== 6) {
      toast.error("Please enter the 6-digit verification code");
      return;
    }

    setIsLoading(true);

    try {
      // Update password with the nonce
      const { error } = await supabase.auth.updateUser({
        password: pendingPasswordData.newPassword,
        nonce: reauthNonce
      });

      if (error) {
        throw error;
      }

      toast.success("Password updated successfully!");
      setPasswordData({ 
        currentPassword: "", 
        newPassword: "", 
        confirmPassword: "" 
      });
      setReauthNonce("");
      setShowReauthModal(false);
      setPendingPasswordData(null);
    } catch (error) {
      console.error("Error updating password with nonce:", error);
      toast.error(error.message || "Invalid verification code");
    } finally {
      setIsLoading(false);
    }
  };

  const getStrengthColor = (strength) => {
    const colors = ["", "bg-red-500", "bg-orange-500", "bg-yellow-500", "bg-green-500", "bg-green-600"];
    return colors[strength];
  };

  return (
    <div>
      <h2 className="text-xl font-semibold text-gray-900 mb-6">Security Settings</h2>
      
      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Current Password */}
        <div>
          <Label htmlFor="currentPassword" required>Current Password</Label>
          <div className="relative">
            <Input
              id="currentPassword"
              name="currentPassword"
              type={showCurrentPassword ? "text" : "password"}
              value={passwordData.currentPassword}
              onChange={handlePasswordChange}
              placeholder="Enter your current password"
              className="pr-10"
              autoComplete="current-password"
            />
            <button
              type="button"
              onClick={() => setShowCurrentPassword(!showCurrentPassword)}
              className="absolute inset-y-0 right-0 pr-3 flex items-center text-gray-400 hover:text-gray-600"
              aria-label={showCurrentPassword ? "Hide password" : "Show password"}
            >
              <i className={`fas ${showCurrentPassword ? "fa-eye-slash" : "fa-eye"}`}></i>
            </button>
          </div>
          {errors.currentPassword && (
            <p className="mt-1.5 text-sm text-red-600">{errors.currentPassword}</p>
          )}
        </div>

        {/* New Password */}
        <div>
          <Label htmlFor="newPassword" required>New Password</Label>
          <div className="relative">
            <Input
              id="newPassword"
              name="newPassword"
              type={showNewPassword ? "text" : "password"}
              value={passwordData.newPassword}
              onChange={handlePasswordChange}
              placeholder="Enter new password"
              className="pr-10"
              autoComplete="new-password"
            />
            <button
              type="button"
              onClick={() => setShowNewPassword(!showNewPassword)}
              className="absolute inset-y-0 right-0 pr-3 flex items-center text-gray-400 hover:text-gray-600"
              aria-label={showNewPassword ? "Hide password" : "Show password"}
            >
              <i className={`fas ${showNewPassword ? "fa-eye-slash" : "fa-eye"}`}></i>
            </button>
          </div>
          
          {/* Password strength indicator */}
          {passwordData.newPassword && (
            <div className="mt-3">
              <div className="flex items-center space-x-3">
                <div className="flex-1 bg-gray-200 rounded-full h-2 overflow-hidden">
                  <div
                    className={`h-full transition-all duration-300 ${getStrengthColor(passwordStrength.strength)}`}
                    style={{ width: `${(passwordStrength.strength / 5) * 100}%` }}
                  />
                </div>
                <span className="text-sm text-gray-600 font-medium min-w-[80px] text-right">
                  {passwordStrength.label}
                </span>
              </div>
            </div>
          )}
          
          {errors.newPassword && (
            <p className="mt-1.5 text-sm text-red-600">{errors.newPassword}</p>
          )}
        </div>

        {/* Confirm Password */}
        <div>
          <Label htmlFor="confirmPassword" required>Confirm New Password</Label>
          <div className="relative">
            <Input
              id="confirmPassword"
              name="confirmPassword"
              type={showConfirmPassword ? "text" : "password"}
              value={passwordData.confirmPassword}
              onChange={handlePasswordChange}
              placeholder="Confirm new password"
              className="pr-10"
              autoComplete="new-password"
            />
            <button
              type="button"
              onClick={() => setShowConfirmPassword(!showConfirmPassword)}
              className="absolute inset-y-0 right-0 pr-3 flex items-center text-gray-400 hover:text-gray-600"
              aria-label={showConfirmPassword ? "Hide password" : "Show password"}
            >
              <i className={`fas ${showConfirmPassword ? "fa-eye-slash" : "fa-eye"}`}></i>
            </button>
          </div>
          {errors.confirmPassword && (
            <p className="mt-1.5 text-sm text-red-600">{errors.confirmPassword}</p>
          )}
        </div>

        {/* Password requirements - Compact version */}
        <div className="bg-gray-50 rounded-lg p-3">
          <p className="text-xs font-medium text-gray-700 mb-2">Password must contain:</p>
          <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-xs">
            <div className={`flex items-center ${passwordData.newPassword.length >= 8 ? 'text-green-600' : 'text-gray-500'}`}>
              <i className={`fas ${passwordData.newPassword.length >= 8 ? 'fa-check' : 'fa-times'} mr-1.5 text-xs`}></i>
              8+ characters
            </div>
            <div className={`flex items-center ${passwordData.newPassword.match(/[A-Z]/) ? 'text-green-600' : 'text-gray-500'}`}>
              <i className={`fas ${passwordData.newPassword.match(/[A-Z]/) ? 'fa-check' : 'fa-times'} mr-1.5 text-xs`}></i>
              Uppercase letter
            </div>
            <div className={`flex items-center ${passwordData.newPassword.match(/[a-z]/) ? 'text-green-600' : 'text-gray-500'}`}>
              <i className={`fas ${passwordData.newPassword.match(/[a-z]/) ? 'fa-check' : 'fa-times'} mr-1.5 text-xs`}></i>
              Lowercase letter
            </div>
            <div className={`flex items-center ${passwordData.newPassword.match(/[0-9]/) ? 'text-green-600' : 'text-gray-500'}`}>
              <i className={`fas ${passwordData.newPassword.match(/[0-9]/) ? 'fa-check' : 'fa-times'} mr-1.5 text-xs`}></i>
              Number
            </div>
            <div className={`flex items-center ${passwordData.newPassword.match(/[^A-Za-z0-9]/) ? 'text-green-600' : 'text-gray-500'} col-span-2`}>
              <i className={`fas ${passwordData.newPassword.match(/[^A-Za-z0-9]/) ? 'fa-check' : 'fa-times'} mr-1.5 text-xs`}></i>
              Special character
            </div>
          </div>
        </div>

        {errors.form && (
          <div className="p-3 bg-red-50 border border-red-200 rounded-lg">
            <p className="text-sm text-red-600 flex items-center">
              <i className="fas fa-exclamation-circle mr-2"></i>
              {errors.form}
            </p>
          </div>
        )}

        <div className="flex justify-between items-center pt-4 border-t border-gray-200">
          <p className="text-sm text-gray-600">
            Forgot your current password?{" "}
            <button
              type="button"
              onClick={async () => {
                try {
                  const { error } = await supabase.auth.resetPasswordForEmail(user.email);
                  if (error) throw error;
                  toast.success("Password reset email sent! Check your inbox.");
                } catch (error) {
                  toast.error("Failed to send reset email. Please try again.");
                }
              }}
              className="text-blue-600 hover:text-blue-700 font-medium"
            >
              Send reset email
            </button>
          </p>
          <Button
            type="submit"
            variant="primary"
            disabled={!passwordData.currentPassword || !passwordData.newPassword || !passwordData.confirmPassword || isLoading}
            isLoading={isLoading}
            loadingText="Updating Password..."
          >
            Update Password
          </Button>
        </div>
      </form>

      {/* Reauthentication Modal */}
      {showReauthModal && (
        <div 
          className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50"
          onClick={(e) => {
            // Close modal if clicking outside
            if (e.target === e.currentTarget) {
              setShowReauthModal(false);
              setReauthNonce("");
              setPendingPasswordData(null);
            }
          }}
        >
          <div className="bg-white rounded-lg p-6 max-w-md w-full mx-4">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">
              Enter Verification Code
            </h3>
            <p className="text-sm text-gray-600 mb-4">
              We've sent a 6-digit verification code to your email address. 
              Please enter it below to confirm your password change.
            </p>
            
            <div className="mb-4">
              <Label htmlFor="reauthNonce">Verification Code</Label>
              <Input
                id="reauthNonce"
                type="text"
                value={reauthNonce}
                onChange={(e) => {
                  // Only allow digits and limit to 6 characters
                  const value = e.target.value.replace(/\D/g, '').slice(0, 6);
                  setReauthNonce(value);
                }}
                placeholder="000000"
                className="text-center text-2xl tracking-widest"
                maxLength="6"
                autoComplete="one-time-code"
                autoFocus
              />
              <p className="mt-1 text-xs text-gray-500">
                Enter the 6-digit code from your email
              </p>
              <p className="mt-1 text-xs text-amber-600">
                <i className="fas fa-info-circle mr-1"></i>
                Code expires in 60 minutes
              </p>
            </div>

            <div className="flex gap-3">
              <Button
                type="button"
                variant="secondary"
                onClick={() => {
                  setShowReauthModal(false);
                  setReauthNonce("");
                  setPendingPasswordData(null);
                }}
                disabled={isLoading}
                className="flex-1"
              >
                Cancel
              </Button>
              <Button
                type="button"
                variant="primary"
                onClick={handleReauthSubmit}
                disabled={reauthNonce.length !== 6 || isLoading}
                isLoading={isLoading}
                className="flex-1"
              >
                Verify & Update
              </Button>
            </div>

            <p className="mt-4 text-xs text-gray-500 text-center">
              Didn't receive the code?{" "}
              <button
                type="button"
                onClick={async () => {
                  try {
                    const { error } = await supabase.auth.reauthenticate();
                    if (error) throw error;
                    toast.success("New verification code sent!");
                  } catch (error) {
                    toast.error("Failed to resend code. Please try again.");
                  }
                }}
                className="text-blue-600 hover:text-blue-700 font-medium"
                disabled={isLoading}
              >
                Resend code
              </button>
            </p>
          </div>
        </div>
      )}
    </div>
  );
};

export default SecurityForm;