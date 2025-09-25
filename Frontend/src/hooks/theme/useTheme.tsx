import { useEffect, useState } from "react";

type Theme = 'light' | 'dark' | 'system';

/**
 * Custom hook for managing dark mode with system preference detection
 * Supports 'light', 'dark', and 'system' themes
 * Persists theme preference in localStorage
 * Automatically applies theme classes to document root
 */
export default function useTheme(): [Theme, (theme: Theme) => void] {
  const [theme, setThemeState] = useState<Theme>(() => {
    // Initialize from localStorage or default to 'system'
    if (typeof window !== "undefined") {
      const savedTheme = localStorage.getItem("theme") as Theme;
      if (savedTheme && ['light', 'dark', 'system'].includes(savedTheme)) {
        return savedTheme;
      }
    }
    return "system";
  });

  // Function to get the actual theme to apply (resolves 'system' to 'light' or 'dark')
  const getEffectiveTheme = (theme: Theme): 'light' | 'dark' => {
    if (theme === 'system') {
      if (typeof window !== "undefined" && window.matchMedia) {
        return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
      }
      return 'light'; // Fallback
    }
    return theme;
  };

  const setTheme = (newTheme: Theme) => {
    setThemeState(newTheme);
  };

  useEffect(() => {
    const root = window.document.documentElement;
    const body = window.document.body;
    
    // Get the effective theme (resolve 'system' to actual theme)
    const effectiveTheme = getEffectiveTheme(theme);

    // Remove all theme classes first
    root.classList.remove("light", "dark");
    body.classList.remove("light", "dark");

    // Add the current effective theme class
    root.classList.add(effectiveTheme);
    body.classList.add(effectiveTheme);

    // Save to localStorage
    localStorage.setItem("theme", theme);

    // Handle system theme changes when theme is set to 'system'
    const handleSystemThemeChange = (e: MediaQueryListEvent) => {
      if (theme === 'system') {
        const newEffectiveTheme = e.matches ? 'dark' : 'light';
        root.classList.remove("light", "dark");
        body.classList.remove("light", "dark");
        root.classList.add(newEffectiveTheme);
        body.classList.add(newEffectiveTheme);
      }
    };

    // Listen for system theme changes
    if (typeof window !== "undefined" && window.matchMedia) {
      const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
      mediaQuery.addEventListener('change', handleSystemThemeChange);
      
      return () => {
        mediaQuery.removeEventListener('change', handleSystemThemeChange);
      };
    }
  }, [theme]);

  return [theme, setTheme];
}
