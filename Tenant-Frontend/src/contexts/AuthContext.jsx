import React, { createContext, useContext, useState, useEffect } from 'react';
import { supabase } from '../utils/supabaseClient';
import { getCurrentUser } from '../utils/api/auth';

const AuthContext = createContext({});

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [isAuthenticated, setIsAuthenticated] = useState(false);

  useEffect(() => {
    // Initialize authentication on app start
    const initializeAuth = async () => {
      try {
        // Check for existing Supabase session
        const { data: { session }, error: sessionError } = await supabase.auth.getSession();
        
        if (sessionError) {
          console.error('Session error:', sessionError);
          setLoading(false);
          return;
        }
        
        if (session?.user) {
          // Store the JWT token for API calls
          localStorage.setItem('token', session.access_token);
          
          try {
            // Fetch user profile from backend API
            const userData = await getCurrentUser();
            
            // Verify user is a tenant
            if (userData.user_type !== 'TENANT') {
              throw new Error('Access denied. This portal is for tenants only.');
            }
            
            setUser(userData);
            setIsAuthenticated(true);
          } catch (apiError) {
            console.error('Failed to fetch user profile:', apiError);
            
            // If API call fails, sign out from Supabase
            await supabase.auth.signOut();
            localStorage.removeItem('token');
            localStorage.removeItem('user_type');
            localStorage.removeItem('user');
            
            setError('Failed to load user profile. Please try logging in again.');
          }
        }
      } catch (error) {
        console.error('Auth initialization error:', error);
        setError(error.message);
      } finally {
        setLoading(false);
      }
    };

    initializeAuth();

    // Listen for Supabase auth state changes
    const { data: { subscription } } = supabase.auth.onAuthStateChange(
      async (event, session) => {
        if (event === 'SIGNED_IN' && session?.user) {
          // Loading is already set to true by signIn function
          // Store JWT token
          localStorage.setItem('token', session.access_token);
          
          try {
            // Fetch user profile from backend
            const userData = await getCurrentUser();
            
            // Verify tenant access
            if (userData.user_type !== 'TENANT') {
              await supabase.auth.signOut();
              localStorage.removeItem('token');
              setError('Access denied. This portal is for tenants only.');
              setLoading(false);
              return;
            }
            
            setUser(userData);
            setIsAuthenticated(true);
            setError(null);
            setLoading(false);
          } catch (apiError) {
            console.error('Failed to fetch user profile on sign in:', apiError);
            await supabase.auth.signOut();
            localStorage.removeItem('token');
            setError('Failed to load user profile. Please try logging in again.');
            setLoading(false);
          }
        } else if (event === 'SIGNED_OUT') {
          // Clear all authentication data
          localStorage.removeItem('token');
          localStorage.removeItem('user_type');
          localStorage.removeItem('user');
          
          setUser(null);
          setIsAuthenticated(false);
          setError(null);
          setLoading(false);
        }
      }
    );

    return () => subscription.unsubscribe();
  }, []);

  const signIn = async (email, password) => {
    try {
      setError(null);
      setLoading(true);
      
      // Authenticate with Supabase
      const { data, error } = await supabase.auth.signInWithPassword({
        email,
        password,
      });

      if (error) {
        setLoading(false);
        throw error;
      }

      // The onAuthStateChange listener will handle the rest and manage loading state
      return { data, error: null };
    } catch (error) {
      console.error('Sign in error:', error);
      setError(error.message);
      setLoading(false);
      return { data: null, error };
    }
  };

  const signOut = async () => {
    try {
      setError(null);
      
      // Sign out from Supabase (this will trigger the auth state change)
      const { error } = await supabase.auth.signOut();
      if (error) throw error;
      
    } catch (error) {
      console.error('Sign out error:', error);
      setError(error.message);
    }
  };

  const value = {
    user,
    loading,
    error,
    isAuthenticated,
    signIn,
    signOut,
    clearError: () => setError(null),
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

