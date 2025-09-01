// Type declarations for API module
export * from './properties';
export * from './core';
export * from './auth';
export * from './dashboard';
export * from './accounting';
export * from './units';
export * from './tenants';
export * from './leases';
export * from './maintenance';
export * from './vendors';
export * from './ai';
export * from './messages';
export * from './reports';
export * from './rentTracker';
export * from './users';
export * from './quickbooks';
export * from './propertyImages';

// Re-export specific functions that Properties.tsx needs
export { fetchPropertyById } from './properties';