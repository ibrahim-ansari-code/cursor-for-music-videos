import { useContext } from 'react';
import { AuthContext } from './AuthContext';
import type { AuthContextValue } from '@/types';

export const useAuth = (): AuthContextValue => {
  const ctx = useContext(AuthContext);
  if (ctx == null) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return ctx;
};

export default useAuth;

