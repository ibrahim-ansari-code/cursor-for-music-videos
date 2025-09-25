import React, { useState, useRef } from "react";
import { Button } from "../ui/SharedModalComponents";
import { uploadUserAvatar } from "../../utils/api/users";
import { toast } from "react-toastify";

const ProfileCard = ({ user, onAvatarUpdate }) => {
  const [avatarPreview, setAvatarPreview] = useState(user?.profile_image_url);
  const [avatarFile, setAvatarFile] = useState(null);
  const [isAvatarLoading, setIsAvatarLoading] = useState(false);
  const [avatarLoadError, setAvatarLoadError] = useState(false);
  const fileInputRef = useRef(null);

  // Get initials helper
  const getInitials = (firstName, lastName) =>
    `${firstName?.charAt(0) || ""}${lastName?.charAt(0) || ""}`.toUpperCase();

  // Format date helper
  const formatDate = (dateString) => {
    if (!dateString) return "N/A";
    const date = new Date(dateString);
    return date.toLocaleDateString("en-US", { month: "long", year: "numeric" });
  };

  // Format phone number for display
  const formatPhoneDisplay = (phone) => {
    if (!phone) return '';
    const cleaned = phone.replace(/\D/g, '');
    if (cleaned.length === 10) {
      return `(${cleaned.slice(0, 3)}) ${cleaned.slice(3, 6)}-${cleaned.slice(6)}`;
    }
    return phone;
  };

  const handleAvatarChange = (e) => {
    const files = e.target?.files;
    const file = files && files.length > 0 ? files[0] : null;
    setAvatarLoadError(false);
    
    if (file && ["image/jpeg", "image/png"].includes(file.type)) {
      if (file.size > 5 * 1024 * 1024) {
        toast.error("Image size must be less than 5MB.");
        return;
      }
      setAvatarFile(file);
      const reader = new FileReader();
      reader.onloadend = () => {
        setAvatarPreview(reader.result);
      };
      reader.readAsDataURL(file);
    } else if (file) {
      toast.error("Invalid file type. Please select JPEG or PNG.");
      setAvatarFile(null);
      setAvatarPreview(user?.profile_image_url);
    }
  };

  const handleAvatarUpload = async () => {
    if (!avatarFile || !user?.id) return;
    setIsAvatarLoading(true);

    const formData = new FormData();
    formData.append("file", avatarFile);

    try {
      const response = await uploadUserAvatar(user.id, formData);
      const newImageUrl = response?.profile_image_url;
      
      if (!newImageUrl) {
        throw new Error("Invalid response from server after avatar upload.");
      }

      // Upload succeeded - update local state
      setAvatarFile(null);
      setAvatarPreview(newImageUrl);
      setAvatarLoadError(false);
      
      try {
        // Notify parent component
        if (onAvatarUpdate) {
          onAvatarUpdate(newImageUrl);
        }
        // Show success toast only if context update succeeds
        toast.success("Avatar updated successfully!");
      } catch (contextError) {
        // If context update fails, keep the new avatar but warn the user
        // Note: This shows a warning toast instead of success to indicate partial completion
        console.error("Error updating context after avatar upload:", contextError);
        toast.warning("Avatar uploaded but may not appear everywhere immediately. Please refresh the page.");
      }
    } catch (error) {
      console.error("Error uploading avatar:", error);
      toast.error(`Avatar upload failed: ${error.message || "Server error"}`);
      // Reset to original state on upload failure
      setAvatarFile(null);
      setAvatarPreview(user?.profile_image_url);
    } finally {
      setIsAvatarLoading(false);
    }
  };

  const imageSource = avatarPreview || user?.profile_image_url;

  return (
    <div className="h-full pr-8 lg:border-r lg:border-gray-200 dark:lg:border-gray-700 transition-colors duration-300">
      <div className="flex flex-col items-center sticky top-6">
        {/* Avatar Section */}
        <div className="relative group mb-4">
          {avatarLoadError || !imageSource ? (
            <div className="h-32 w-32 rounded-full bg-gray-200 dark:bg-gray-700 flex items-center justify-center text-gray-500 dark:text-gray-400 text-3xl font-semibold transition-colors duration-300">
              {getInitials(user?.first_name, user?.last_name)}
            </div>
          ) : (
            <img
              src={imageSource}
              alt="Profile"
              className="h-32 w-32 rounded-full object-cover border-4 border-gray-100 dark:border-gray-600 transition-colors duration-300"
              onError={() => setAvatarLoadError(true)}
            />
          )}
          <label className="absolute inset-0 flex items-center justify-center bg-black bg-opacity-50 rounded-full opacity-0 group-hover:opacity-100 cursor-pointer transition-opacity">
            <input
              ref={fileInputRef}
              type="file"
              className="hidden"
              onChange={handleAvatarChange}
              accept=".jpeg,.png"
            />
            <i className="fas fa-camera text-white text-2xl" />
          </label>
        </div>

        {/* Upload Button (shown when file selected) */}
        {avatarFile && (
          <Button
            onClick={handleAvatarUpload}
            variant="primary"
            disabled={isAvatarLoading}
            isLoading={isAvatarLoading}
            className="mb-4 w-full"
          >
            Save Photo
          </Button>
        )}

        {/* User Info */}
        <h3 className="text-xl font-semibold text-gray-900 dark:text-white text-center transition-colors duration-300">
          {user?.first_name} {user?.last_name}
        </h3>
        <p className="text-sm text-gray-500 dark:text-gray-400 text-center transition-colors duration-300">{user?.email}</p>

        {/* Stats */}
        <div className="mt-6 w-full space-y-3">
          {/* Basic Info */}
          <div className="flex justify-between items-center py-2.5">
            <span className="text-sm text-gray-500 dark:text-gray-400 transition-colors duration-300">Role</span>
            <span className="text-sm font-medium text-gray-900 dark:text-white capitalize transition-colors duration-300">
              {user?.user_type?.toLowerCase() || "Landlord"}
            </span>
          </div>
          
          <div className="flex justify-between items-center py-2.5">
            <span className="text-sm text-gray-500 dark:text-gray-400 transition-colors duration-300">Member Since</span>
            <span className="text-sm font-medium text-gray-900 dark:text-white transition-colors duration-300">
              {formatDate(user?.created_at)}
            </span>
          </div>
          
          {/* Divider */}
          <div className="border-t border-gray-100 dark:border-gray-700 my-3 transition-colors duration-300"></div>
          
          {/* Status Section */}
          <div className="flex justify-between items-center py-2.5">
            <span className="text-sm text-gray-500 dark:text-gray-400 transition-colors duration-300">Email Status</span>
            <span className={`text-sm font-medium flex items-center ${user?.is_email_verified ? 'text-green-600' : 'text-amber-600'}`}>
              <i className={`fas ${user?.is_email_verified ? 'fa-check-circle' : 'fa-exclamation-circle'} mr-1.5`}></i>
              {user?.is_email_verified ? 'Verified' : 'Unverified'}
            </span>
          </div>
          
          <div className="flex justify-between items-center py-2.5">
            <span className="text-sm text-gray-500 dark:text-gray-400 transition-colors duration-300">Account Status</span>
            <span className={`text-sm font-medium flex items-center ${user?.is_active ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'} transition-colors duration-300`}>
              <i className={`fas ${user?.is_active ? 'fa-check-circle' : 'fa-times-circle'} mr-1.5`}></i>
              {user?.is_active ? 'Active' : 'Inactive'}
            </span>
          </div>
          
          {user?.is_admin && (
            <div className="flex justify-between items-center py-2.5">
              <span className="text-sm text-gray-500 dark:text-gray-400 transition-colors duration-300">Admin</span>
              <span className="text-sm font-medium text-purple-600 dark:text-purple-400 flex items-center transition-colors duration-300">
                <i className="fas fa-shield-alt mr-1.5"></i>
                Administrator
              </span>
            </div>
          )}
          
          {/* Contact Info */}
          {(user?.city || user?.province || user?.phone) && (
            <>
              <div className="border-t border-gray-100 dark:border-gray-700 my-3 transition-colors duration-300"></div>
              
              {(user?.city || user?.province) && (
                <div className="flex justify-between items-center py-2.5">
                  <span className="text-sm text-gray-500 dark:text-gray-400 transition-colors duration-300">Location</span>
                  <span className="text-sm font-medium text-gray-900 dark:text-white text-right transition-colors duration-300">
                    {[user?.city, user?.province].filter(Boolean).join(', ')}
                  </span>
                </div>
              )}
              
              {user?.phone && (
                <div className="flex justify-between items-center py-2.5">
                  <span className="text-sm text-gray-500 dark:text-gray-400 transition-colors duration-300">Phone</span>
                  <span className="text-sm font-medium text-gray-900 dark:text-white text-right transition-colors duration-300">
                    {formatPhoneDisplay(user.phone)}
                  </span>
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
};

export default ProfileCard;