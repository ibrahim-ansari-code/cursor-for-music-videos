import React, { createContext, useContext, ReactNode, useEffect } from "react";
import useThemeHook from "../hooks/theme/useTheme";

type Theme = 'light' | 'dark' | 'system';

type ThemeContextType = {
  theme: Theme;
  setTheme: (theme: Theme) => void;
  effectiveTheme: 'light' | 'dark'; // The actual theme being applied (resolves 'system')
  isSystemTheme: boolean;
};

const ThemeContext = createContext<ThemeContextType | undefined>(undefined);

interface ThemeProviderProps {
  children: ReactNode;
}

/**
 * ThemeProvider component that manages the application's theme state
 * Supports light, dark, and system themes with automatic system preference detection
 */
export const ThemeProvider: React.FC<ThemeProviderProps> = ({ children }) => {
  const [theme, setTheme] = useThemeHook();

  // Function to get the effective theme (resolves 'system' to actual theme)
  const getEffectiveTheme = (): 'light' | 'dark' => {
    if (theme === 'system') {
      if (typeof window !== "undefined" && window.matchMedia) {
        return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
      }
      return 'light'; // Fallback
    }
    return theme;
  };

  const effectiveTheme = getEffectiveTheme();
  const isSystemTheme = theme === 'system';

  // Update skeleton theme colors based on effective theme
  useEffect(() => {
    if (effectiveTheme === 'dark') {
      // Update CSS custom properties for react-loading-skeleton in dark mode
      document.documentElement.style.setProperty('--skeleton-base-color', 'rgb(55, 65, 81)'); // gray-700
      document.documentElement.style.setProperty('--skeleton-highlight-color', 'rgb(75, 85, 99)'); // gray-600
    } else {
      document.documentElement.style.setProperty('--skeleton-base-color', 'rgb(229, 231, 235)'); // gray-200
      document.documentElement.style.setProperty('--skeleton-highlight-color', 'rgb(243, 244, 246)'); // gray-100
    }
  }, [effectiveTheme]);

  const value: ThemeContextType = {
    theme,
    setTheme,
    effectiveTheme,
    isSystemTheme,
  };

  return (
    <ThemeContext.Provider value={value}>
      {children}
    </ThemeContext.Provider>
  );
};

/**
 * Custom hook to access theme context
 * Must be used within a ThemeProvider
 */
export const useTheme = () => {
  const context = useContext(ThemeContext);
  if (!context) {
    throw new Error("useTheme must be used within a ThemeProvider");
  }
  return context;
};
