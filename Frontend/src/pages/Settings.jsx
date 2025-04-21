import React, { useState, useEffect, useContext, useRef } from 'react';
import { AuthContext } from '../App';
import { updateUserProfile, changeUserPassword, uploadUserAvatar } from '../utils/api';
import { motion, AnimatePresence } from 'framer-motion';
import { toast } from 'react-toastify'; // Using react-toastify for notifications

// UI Components (Could be moved to shared components)
const Card = ({ children, className = "" }) => (
    <div className={`bg-white rounded-2xl shadow-sm p-6 mb-6 ${className}`}>
        {children}
    </div>
);

const SectionTitle = ({ children }) => (
    <h2 className="text-xl font-semibold text-gray-800 mb-4 pb-3 border-b border-gray-200">
        {children}
    </h2>
);

const Label = ({ htmlFor, children, required }) => (
    <label
        htmlFor={htmlFor}
        className={`block text-sm font-medium text-gray-700 mb-1.5 ${required ? 'after:content-["*"] after:ml-0.5 after:text-red-500' : ''}`}
    >
        {children}
    </label>
);

const Input = ({ id, name, type = "text", value, onChange, required, disabled, readOnly, placeholder, error }) => (
    <input
        id={id || name}
        name={name}
        type={type}
        value={value}
        onChange={onChange}
        required={required}
        disabled={disabled}
        readOnly={readOnly}
        placeholder={placeholder}
        className={`w-full px-4 py-2.5 text-gray-900 bg-white border ${readOnly || disabled ? 'bg-gray-100 cursor-not-allowed' : error ? 'border-red-500' : 'border-gray-300'} rounded-lg shadow-sm focus:ring-2 ${error ? 'focus:ring-red-500/30 focus:border-red-500' : 'focus:ring-blue-500/30 focus:border-blue-500'} focus:outline-none transition-all duration-200`}
    />
);

const Button = ({ children, onClick, type = "button", variant = "primary", disabled, isLoading, className = "" }) => {
    const baseClasses = "px-4 py-2.5 rounded-lg font-medium text-sm focus:outline-none focus:ring-2 focus:ring-offset-2 transition-all duration-200 inline-flex items-center justify-center gap-2 disabled:opacity-60 disabled:cursor-not-allowed";
    const variants = {
        primary: "bg-blue-600 hover:bg-blue-700 text-white border border-transparent focus:ring-blue-500",
        secondary: "bg-white hover:bg-gray-50 text-gray-700 border border-gray-300 focus:ring-blue-500",
    };
    return (
        <button
            type={type}
            onClick={onClick}
            disabled={disabled || isLoading}
            className={`${baseClasses} ${variants[variant]} ${className}`}
        >
            {isLoading ? (
                <>
                    <svg className="animate-spin -ml-1 mr-2 h-4 w-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                    Processing...
                </>
            ) : (
                children
            )}
        </button>
    );
};

const InputError = ({ message }) => (
    message ? <p className="mt-1 text-sm text-red-600">{message}</p> : null
);

// Settings Page Component
const Settings = () => {
    const { user: authUser, setUser: setAuthUser } = useContext(AuthContext);
    const [profileData, setProfileData] = useState({ first_name: '', last_name: '', email: '', phone: '' });
    const [initialProfileData, setInitialProfileData] = useState({});
    const [passwordData, setPasswordData] = useState({ newPassword: '', confirmPassword: '' });
    const [errors, setErrors] = useState({});
    const [avatarPreview, setAvatarPreview] = useState(null);
    const [avatarFile, setAvatarFile] = useState(null);
    const [isProfileLoading, setIsProfileLoading] = useState(false);
    const [isPasswordLoading, setIsPasswordLoading] = useState(false);
    const [isAvatarLoading, setIsAvatarLoading] = useState(false);
    const [avatarLoadError, setAvatarLoadError] = useState(false);
    const fileInputRef = useRef(null);

    // Get initials helper
    const getInitials = (firstName, lastName) => `${firstName?.charAt(0) || ''}${lastName?.charAt(0) || ''}`.toUpperCase();

    // Fetch user data on mount or when authUser changes
    useEffect(() => {
        if (authUser) {
            const initialData = {
                first_name: authUser.first_name || '',
                last_name: authUser.last_name || '',
                email: authUser.email || '',
                phone: authUser.phone || '',
                profile_image_url: authUser.profile_image_url
            };
            setProfileData(initialData);
            setInitialProfileData(initialData);
            setAvatarPreview(authUser.profile_image_url); // Use context value
            setAvatarLoadError(false);
        } else {
             // Handle case where authUser is null (e.g., loading or error)
             // Optionally show a loading state or redirect
             console.log("Waiting for user data...");
        }
    }, [authUser]);

    const handleProfileChange = (e) => {
        setProfileData({ ...profileData, [e.target.name]: e.target.value });
        if (errors[e.target.name]) {
            setErrors(prev => ({ ...prev, [e.target.name]: null }));
        }
    };

    const handlePasswordChange = (e) => {
        setPasswordData({ ...passwordData, [e.target.name]: e.target.value });
        if (errors.password || errors.confirmPassword) {
            setErrors(prev => ({ ...prev, password: null, confirmPassword: null }));
        }
    };

    const handleAvatarChange = (e) => {
        const file = e.target.files[0];
        setAvatarLoadError(false);
        if (file && ['image/jpeg', 'image/png', 'image/jpg'].includes(file.type)) {
            if (file.size > 5 * 1024 * 1024) { // 5MB limit
                toast.error("Image size must be less than 5MB.");
                return;
            }
            setAvatarFile(file);
            const reader = new FileReader();
            reader.onloadend = () => {
                setAvatarPreview(reader.result);
            };
            reader.readAsDataURL(file);
            setErrors(prev => ({ ...prev, avatar: null }));
        } else if (file) {
            toast.error("Invalid file type. Please select JPG, JPEG, or PNG.");
            setAvatarFile(null);
            setAvatarPreview(authUser?.profile_image_url);
        } else {
            setAvatarFile(null);
            setAvatarPreview(authUser?.profile_image_url);
        }
    };

    const triggerAvatarUpload = () => {
        fileInputRef.current?.click();
    };

    // API Handlers with Error Handling & Notifications
    const handleAvatarUpload = async () => {
        if (!avatarFile || !authUser?.id) return;
        setIsAvatarLoading(true);
        setErrors({});
        // Don't reset avatarLoadError here, only on successful load or new selection

        const formData = new FormData();
        formData.append('file', avatarFile);

        try {
            const response = await uploadUserAvatar(authUser.id, formData);
            console.log("Avatar Upload Response:", response); // Log the response
            
            // Ensure the response has the expected field
            const newImageUrl = response?.profile_image_url;
            if (!newImageUrl) {
                throw new Error("Invalid response from server after avatar upload.");
            }

            toast.success('Avatar updated successfully!');
            setAvatarFile(null); // Clear the selected file
            
            // Update context and local state
            setAuthUser(prev => ({ ...prev, profile_image_url: newImageUrl }));
            setInitialProfileData(prev => ({ ...prev, profile_image_url: newImageUrl }));
            setAvatarPreview(newImageUrl); // Update preview to the final URL
            setAvatarLoadError(false); // Reset load error *only* on successful upload and state update

        } catch (error) {
            console.error("Error uploading avatar:", error);
            const errorMsg = error?.status === 404
                ? "Upload endpoint not found. Please contact support."
                : error?.message || 'Server error';
            toast.error(`Avatar upload failed: ${errorMsg}`);
            setErrors(prev => ({ ...prev, avatar: 'Upload failed. Please try again.' }));
            
            // Revert preview to the last known good URL from context on failure
            setAvatarPreview(authUser?.profile_image_url);
            // We don't set avatarLoadError here because the upload failed, 
            // not necessarily the loading of the existing image.
        } finally {
            setIsAvatarLoading(false);
        }
    };

    const handleProfileSubmit = async (e) => {
        e.preventDefault();
        if (!isProfileChanged) return; // Prevent submission if no changes
        setIsProfileLoading(true);
        setErrors({});

        const dataToUpdate = {
            first_name: profileData.first_name.trim(),
            last_name: profileData.last_name.trim(),
            phone: profileData.phone.trim(),
        };

        // Basic validation (can be expanded)
        let validationErrors = {};
        if (!dataToUpdate.first_name) validationErrors.first_name = "First name is required.";
        if (!dataToUpdate.last_name) validationErrors.last_name = "Last name is required.";
        // Add phone validation if needed

        if (Object.keys(validationErrors).length > 0) {
            setErrors(validationErrors);
            setIsProfileLoading(false);
            return;
        }

        try {
            const response = await updateUserProfile(authUser.id, dataToUpdate);
            toast.success('Profile updated successfully!');
            // Update AuthContext
            setAuthUser(prev => ({ ...prev, ...dataToUpdate }));
            // Update initial data to reset changed state
            setInitialProfileData(prev => ({ ...prev, ...dataToUpdate }));
        } catch (error) {
            console.error("Error updating profile:", error);
            toast.error(`Profile update failed: ${error.message || 'Server error'}`);
            setErrors(prev => ({ ...prev, form: 'Failed to update profile.' }));
        } finally {
            setIsProfileLoading(false);
        }
    };

    const handlePasswordSubmit = async (e) => {
        e.preventDefault();
        setErrors({});

        let validationErrors = {};
        if (passwordData.newPassword.length < 8) {
            validationErrors.password = 'Password must be at least 8 characters long.';
        }
        if (passwordData.newPassword !== passwordData.confirmPassword) {
            validationErrors.confirmPassword = 'Passwords do not match.';
        }

        if (Object.keys(validationErrors).length > 0) {
            setErrors(validationErrors);
            return;
        }

        setIsPasswordLoading(true);
        try {
            await changeUserPassword(authUser.id, passwordData.newPassword);
            toast.success('Password updated successfully!');
            setPasswordData({ newPassword: '', confirmPassword: '' }); // Clear fields
        } catch (error) {
            console.error("Error changing password:", error);
            toast.error(`Password update failed: ${error.message || 'Server error'}`);
            setErrors(prev => ({ ...prev, form: 'Failed to update password.' }));
        } finally {
            setIsPasswordLoading(false);
        }
    };

    const isProfileChanged = JSON.stringify({
        first_name: profileData.first_name,
        last_name: profileData.last_name,
        phone: profileData.phone
    }) !== JSON.stringify({
        first_name: initialProfileData.first_name,
        last_name: initialProfileData.last_name,
        phone: initialProfileData.phone
    });

    // Loading state for initial data
    if (!authUser) {
        return (
            <div className="max-w-3xl mx-auto py-6 px-4 sm:px-6 lg:px-8">
                <Card>
                    <div className="animate-pulse flex flex-col items-center">
                        <div className="h-36 w-36 rounded-full bg-gray-300 mb-4"></div>
                        <div className="h-8 w-24 bg-gray-300 rounded"></div>
                    </div>
                </Card>
                <Card>
                    <div className="h-8 w-1/3 bg-gray-300 rounded mb-6"></div>
                    <div className="space-y-4">
                         <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                             <div className="h-16 bg-gray-300 rounded"></div>
                             <div className="h-16 bg-gray-300 rounded"></div>
                         </div>
                         <div className="h-16 bg-gray-300 rounded"></div>
                         <div className="h-16 bg-gray-300 rounded"></div>
                         <div className="flex justify-end"><div className="h-10 w-24 bg-gray-300 rounded"></div></div>
                    </div>
                </Card>
             </div>
        );
    }

    // Determine the source for the image tag
    const imageSource = avatarPreview || authUser?.profile_image_url;

    return (
        <div className="max-w-3xl mx-auto py-6 px-4 sm:px-6 lg:px-8">

            {/* Profile Picture Section */}
            <Card>
                <div className="flex flex-col items-center">
                    {/* Display initials only if avatarLoadError is true */}
                    {avatarLoadError ? (
                        <div className="h-36 w-36 rounded-full bg-gray-200 flex items-center justify-center text-gray-500 text-4xl font-semibold mb-4 border-4 border-gray-100 shadow-sm">
                            {getInitials(authUser.first_name, authUser.last_name)}
                        </div>
                    ) : (
                        <motion.img
                            key={imageSource || 'initials'} // Use a consistent key source
                            initial={{ opacity: 0, scale: 0.8 }}
                            animate={{ opacity: 1, scale: 1 }}
                            transition={{ duration: 0.3 }}
                            src={imageSource || undefined} // Use determined source, pass undefined if nullish
                            alt="Profile Avatar"
                            className="h-36 w-36 rounded-full object-cover mb-4 border-4 border-gray-100 shadow-sm"
                            // Set error state ONLY if the determined imageSource fails
                            onError={() => {
                                console.warn('Image failed to load:', imageSource);
                                setAvatarLoadError(true);
                            }} 
                        />
                    )}
                    <input
                        type="file"
                        ref={fileInputRef}
                        onChange={handleAvatarChange} // Reset avatarLoadError in handleAvatarChange
                        accept=".jpg,.jpeg,.png"
                        style={{ display: 'none' }}
                        id="avatar-upload"
                    />
                    <Button variant="secondary" onClick={triggerAvatarUpload} disabled={isAvatarLoading} className="mb-3">
                        Change Photo
                    </Button>
                    {avatarFile && (
                        <Button
                            onClick={handleAvatarUpload}
                            variant="primary"
                            disabled={isAvatarLoading}
                            isLoading={isAvatarLoading}
                        >
                            Save Photo
                        </Button>
                    )}
                    <AnimatePresence>
                         {errors.avatar && (
                            <motion.p
                                initial={{ opacity: 0, y: -10 }}
                                animate={{ opacity: 1, y: 0 }}
                                exit={{ opacity: 0 }}
                                className="mt-2 text-sm text-red-600"
                            >
                                {errors.avatar}
                             </motion.p>
                        )}
                    </AnimatePresence>
                 </div>
            </Card>

            {/* Profile Info Section */}
            <Card>
                <SectionTitle>Profile Information</SectionTitle>
                <form onSubmit={handleProfileSubmit} className="space-y-4">
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-x-4 gap-y-4">
                        <div>
                            <Label htmlFor="first_name" required>First Name</Label>
                            <Input id="first_name" name="first_name" value={profileData.first_name} onChange={handleProfileChange} error={errors.first_name} />
                            <InputError message={errors.first_name} />
                        </div>
                        <div>
                            <Label htmlFor="last_name" required>Last Name</Label>
                            <Input id="last_name" name="last_name" value={profileData.last_name} onChange={handleProfileChange} error={errors.last_name} />
                             <InputError message={errors.last_name} />
                        </div>
                    </div>
                    <div>
                        <Label htmlFor="email">Email</Label>
                        <Input id="email" name="email" type="email" value={profileData.email} readOnly disabled />
                        <p className="mt-1 text-xs text-gray-500">Email address cannot be changed.</p>
                    </div>
                    <div>
                        <Label htmlFor="phone">Phone Number</Label>
                        <Input id="phone" name="phone" type="tel" value={profileData.phone} onChange={handleProfileChange} placeholder="e.g., 123-456-7890" error={errors.phone}/>
                        <InputError message={errors.phone} />
                    </div>
                    <div className="pt-2 flex justify-end">
                        <Button type="submit" disabled={!isProfileChanged || isProfileLoading} isLoading={isProfileLoading}>
                            Save Changes
                        </Button>
                    </div>
                    {errors.form && <p className="mt-2 text-sm text-red-600 text-right">{errors.form}</p>}
                </form>
            </Card>

            {/* Password Reset Section */}
            <Card>
                <SectionTitle>Change Password</SectionTitle>
                <form onSubmit={handlePasswordSubmit} className="space-y-4">
                    <div>
                        <Label htmlFor="newPassword" required>New Password</Label>
                        <Input id="newPassword" name="newPassword" type="password" value={passwordData.newPassword} onChange={handlePasswordChange} required error={errors.password} />
                        <p className="mt-1 text-xs text-gray-500">Must be at least 8 characters long.</p>
                        <InputError message={errors.password} />
                    </div>
                    <div>
                        <Label htmlFor="confirmPassword" required>Confirm New Password</Label>
                        <Input id="confirmPassword" name="confirmPassword" type="password" value={passwordData.confirmPassword} onChange={handlePasswordChange} required error={errors.confirmPassword} />
                        <InputError message={errors.confirmPassword} />
                    </div>

                    <div className="pt-2 flex justify-end">
                        <Button type="submit" disabled={!passwordData.newPassword || !passwordData.confirmPassword || isPasswordLoading} isLoading={isPasswordLoading}>
                            Update Password
                        </Button>
                    </div>
                     {errors.form && <p className="mt-2 text-sm text-red-600 text-right">{errors.form}</p>} {/* Re-use form error for password section */}
                </form>
            </Card>
        </div>
    );
};

export default Settings; 