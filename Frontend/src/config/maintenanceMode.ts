/**
 * Maintenance Mode Configuration
 * 
 * Set MAINTENANCE_MODE to true to block all access to the application.
 * This will:
 * - Sign out all logged-in users
 * - Show maintenance page for all routes
 * - Block login and registration
 * 
 * To re-enable the app, set MAINTENANCE_MODE to false
 */

export const MAINTENANCE_MODE = true;

export interface MaintenanceMessage {
  title: string;
  message: string;
  expectedResume: string;
  apology: string;
}

export const MAINTENANCE_MESSAGE: MaintenanceMessage = {
  title: "Scheduled Maintenance",
  message: "We're currently performing maintenance to prepare for our Tenant Portal Launch. During this time, the Landlord Portal will be unavailable.",
  expectedResume: "Monday, December 23, 2025",
  apology: "We apologize for any inconvenience. Please check back on Monday."
};

