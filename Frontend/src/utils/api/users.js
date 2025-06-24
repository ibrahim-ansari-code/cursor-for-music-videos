// User Settings API Functions
import { apiRequest, uploadFile } from './core';

/**
 * Update user profile information.
 * @param {string} userId - The ID of the user to update.
 * @param {object} profileData - Object containing first_name, last_name, phone.
 * @returns {Promise<object>} The updated user data.
 */
export const updateUserProfile = async (userId, profileData) => {
  if (!userId) throw new Error("User ID is required to update profile.");
  return apiRequest(`/users/${userId}/profile/`, {
    method: "PUT", // PUT for full resource replacement
    body: JSON.stringify(profileData),
  });
};

/**
 * Change the user's password.
 * @param {string} userId - The ID of the user.
 * @param {string} newPassword - The new password.
 * @returns {Promise<object>} Success message or error.
 */
export const changeUserPassword = async (userId, newPassword) => {
  if (!userId) throw new Error("User ID is required to change password.");
  return apiRequest(`/users/${userId}/password/`, {
    method: "PUT", // PUT for idempotent password updates
    body: JSON.stringify({ password: newPassword }),
  });
};

/**
 * Upload a new avatar for the user.
 * @param {string} userId - The ID of the user.
 * @param {FormData} formData - FormData object containing the avatar file under the key 'avatar'.
 *                               The FormData should be created as: formData.append('avatar', file)
 * @returns {Promise<object>} Object containing the new profile_image_url.
 */
export const uploadUserAvatar = async (userId, formData) => {
  if (!userId) throw new Error("User ID is required to upload avatar.");
  // FormData should contain the avatar file under the key 'avatar'
  return uploadFile(`/users/${userId}/avatar/`, formData, {
    errorMsg: "Failed to upload avatar.",
  });
};

// Landlord Management API Functions
export const fetchLandlords = async () => {
  return apiRequest("/landlords/");
};

export const fetchLandlord = async (landlordId) => {
  return apiRequest(`/landlords/${landlordId}/`);
};

export const createLandlord = async (landlordData) => {
  return apiRequest("/landlords/", {
    method: "POST",
    body: JSON.stringify(landlordData),
  });
};

export const updateLandlord = async (landlordId, landlordData) => {
  return apiRequest(`/landlords/${landlordId}/`, {
    method: "PUT",
    body: JSON.stringify(landlordData),
  });
}; 