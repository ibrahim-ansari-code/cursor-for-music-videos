import React, { useEffect, useState, type ReactNode } from 'react';
import { AuthContext } from './AuthContext';
import { supabase } from '@/utils/supabaseClient';
import { getCurrentUser } from '@/utils/api/auth';
import { retryApiCall } from '@/utils/retryLogic';
import type { User, AuthContextValue } from '@/types';

interface AuthProviderProps {
  children: ReactNode;
}

export const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [isAuthenticated, setIsAuthenticated] = useState<boolean>(false);

  useEffect(() => {
    const initializeAuth = async () => {
      try {
        const { data: { session }, error: sessionError } = await supabase.auth.getSession();
        if (sessionError) { setLoading(false); return; }
        if (session?.user) {
          localStorage.setItem('token', session.access_token);
          try {
            const userData = await retryApiCall(
              getCurrentUser,
              'fetch user profile',
              { maxRetries: 2, baseDelay: 500, userFriendlyMessage: 'Failed to load user profile. Please refresh the page.' }
            );
            if (userData.user_type !== 'TENANT') {
              throw new Error('Access denied. This portal is for tenants only.');
            }
            setUser(userData);
            setIsAuthenticated(true);
          } catch (apiError) {
            console.error('Failed to fetch user profile:', apiError);
            await supabase.auth.signOut();
            localStorage.removeItem('token');
            localStorage.removeItem('user_type');
            localStorage.removeItem('user');
            setError('Failed to load user profile. Please try logging in again.');
          }
        }
      } catch (e) {
        console.error('Auth initialization error:', e);
        setError((e as Error).message);
      } finally {
        setLoading(false);
      }
    };

    initializeAuth();

    const { data: { subscription } } = supabase.auth.onAuthStateChange(async (event, session) => {
      if (event === 'SIGNED_IN' && session?.user) {
        localStorage.setItem('token', session.access_token);
        try {
          const userData = await getCurrentUser();
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
        localStorage.removeItem('token');
        localStorage.removeItem('user_type');
        localStorage.removeItem('user');
        setUser(null);
        setIsAuthenticated(false);
        setError(null);
        setLoading(false);
      }
    });

    return () => subscription.unsubscribe();
  }, []);

  const signIn = async (email: string, password: string): Promise<{ data: unknown; error: Error | null }> => {
    try {
      setError(null);
      setLoading(true);
      const { data, error } = await supabase.auth.signInWithPassword({ email, password });
      if (error) {
        setLoading(false);
        throw error;
      }
      return { data, error: null };
    } catch (err) {
      console.error('Sign in error:', err);
      setError((err as Error).message);
      setLoading(false);
      return { data: null, error: err as Error };
    }
  };

  const signOut = async (): Promise<void> => {
    try {
      setError(null);
      const { error } = await supabase.auth.signOut();
      if (error) throw error;
    } catch (err) {
      console.error('Sign out error:', err);
      setError((err as Error).message);
    }
  };

  const value: AuthContextValue = {
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

export default AuthProvider;

