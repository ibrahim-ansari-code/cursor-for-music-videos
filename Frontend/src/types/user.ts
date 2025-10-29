/**
 * User type definitions for the application
 */

export type UserType = 'ADMIN' | 'LANDLORD' | 'TENANT';

/**
 * Extended user profile from backend API
 * Combines Supabase auth user with custom profile fields
 */
export interface User {
  id: string;
  email: string;
  first_name?: string;
  last_name?: string;
  name?: string;
  phone?: string;
  profile_image_url?: string;
  user_type?: UserType;
  created_at?: string;
  updated_at?: string;
  // Allow for additional dynamic fields
  [key: string]: unknown;
}

/**
 * User profile update data
 */
export interface UserProfileUpdateData {
  first_name?: string;
  last_name?: string;
  phone?: string;
}

/**
 * Avatar update handler
 */
export type AvatarUpdateHandler = (newImageUrl: string) => void;

/**
 * Profile update handler
 */
export type ProfileUpdateHandler = (updatedData: Partial<User>) => void;

