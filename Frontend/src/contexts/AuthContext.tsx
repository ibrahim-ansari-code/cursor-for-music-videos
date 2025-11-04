import { createContext } from 'react';

export interface User {
  id: string;
  email: string;
  name?: string;
  user_type: string;
  [key: string]: any;
}

export interface AuthContextType {
  user: User | null;
  setUser: (user: User | null) => void;
  signIn: (email: string, password: string) => Promise<boolean>;
  signOut: () => Promise<void>;
  isAuthenticated: boolean;
}

export const AuthContext = createContext<AuthContextType | null>(null);
