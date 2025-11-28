import { createClient, SupabaseClient } from '@supabase/supabase-js';

// Validate required environment variables
const supabaseUrl = import.meta.env.VITE_SUPABASE_URL;
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY;

if (!supabaseUrl) {
  throw new Error("CRITICAL: VITE_SUPABASE_URL environment variable is not defined! Cannot initialize Supabase client.");
}

if (!supabaseAnonKey) {
  throw new Error("CRITICAL: VITE_SUPABASE_ANON_KEY environment variable is not defined! Cannot initialize Supabase client.");
}

// Create Supabase client with proper configuration
export const supabase: SupabaseClient = createClient(supabaseUrl, supabaseAnonKey, {
  auth: {
    persistSession: true,
    storageKey: 'brikli-tenant-auth',
    storage: window.localStorage,
    autoRefreshToken: true,
    detectSessionInUrl: true,
  },
});

