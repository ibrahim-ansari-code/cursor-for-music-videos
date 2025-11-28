import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

/**
 * Utility function to merge Tailwind CSS classes with proper precedence
 * This follows the industry standard approach of using clsx for conditional classes
 * and tailwind-merge to handle Tailwind's class conflicts properly
 * 
 * @param inputs - Class names, objects, or arrays to merge
 * @returns Merged class string
 */
export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs));
}

