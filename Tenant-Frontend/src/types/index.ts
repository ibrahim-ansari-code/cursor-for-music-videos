import type { ReactNode, SyntheticEvent } from 'react';

// Export payment types
export * from './payments';

// User and Auth Types
export interface User {
  id: string;
  email: string;
  first_name: string | null;
  last_name: string | null;
  user_type: 'TENANT' | 'LANDLORD' | 'ADMIN';
  profile_image_url: string | null;
  created_at: string;
  updated_at: string;
}

export interface AuthContextValue {
  user: User | null;
  loading: boolean;
  error: string | null;
  isAuthenticated: boolean;
  signIn: (email: string, password: string) => Promise<{ data: unknown; error: Error | null }>;
  signOut: () => Promise<void>;
  clearError: () => void;
}

// Payment Types
export interface PaymentMethod {
  id: string;
  type: 'card' | 'bank';
  last4: string;
  brand?: string;
  bankName?: string;
  expiryDate?: string;
  expMonth?: number;
  expYear?: number;
  isDefault?: boolean;
  isVerified?: boolean;
}

export interface PaymentHistoryItem {
  id: string;
  date: string;
  description: string;
  paymentMethod: string;
  amount: number;
  status: 'Paid' | 'Pending' | 'Failed' | 'Refunded';
  receiptUrl?: string;
}

// Component Props Types
export interface LoadingSkeletonProps {
  className?: string;
  width?: string;
  height?: string;
  rounded?: string;
}

export interface TextSkeletonProps {
  lines?: number;
  className?: string;
}

export interface ButtonSkeletonProps {
  className?: string;
}

export interface LazyImageProps {
  src: string;
  alt: string;
  className?: string;
  placeholder?: ReactNode;
  onLoad?: () => void;
  onError?: (e: SyntheticEvent<HTMLImageElement, Event>) => void;
}

// API Types
export interface ApiError extends Error {
  status?: number;
  statusText?: string;
  url?: string;
  data?: unknown;
  rawResponse?: string;
  rawResponseError?: string;
}

// Retry Options
export interface RetryOptions {
  maxRetries?: number;
  baseDelay?: number;
  retryOn?: number[];
  userFriendlyMessage?: string;
}

