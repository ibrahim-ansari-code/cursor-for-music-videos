import { clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

/**
 * Utility function to merge Tailwind CSS classes with proper precedence
 * This follows the industry standard approach of using clsx for conditional classes
 * and tailwind-merge to handle Tailwind's class conflicts properly
 * 
 * @param {...any} inputs - Class names, objects, or arrays to merge
 * @returns {string} - Merged class string
 */
export function cn(...inputs) {
  return twMerge(clsx(inputs));
} 