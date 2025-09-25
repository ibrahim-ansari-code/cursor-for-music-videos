import React from "react";
import { useTheme } from "../../contexts/ThemeSwitch";

/**
 * ThemeToggle component for quick theme switching
 * Displays a button that cycles through light, dark, and system themes
 */
const ThemeToggle = ({ className = "", showLabel = false }) => {
  const { theme, setTheme, effectiveTheme, isSystemTheme } = useTheme();

  const getNextTheme = () => {
    switch (theme) {
      case 'light':
        return 'dark';
      case 'dark':
        return 'system';
      case 'system':
        return 'light';
      default:
        return 'light';
    }
  };

  const handleToggle = () => {
    const nextTheme = getNextTheme();
    setTheme(nextTheme);
  };

  const getThemeIcon = () => {
    if (isSystemTheme) {
      return 'fa-laptop';
    }
    return effectiveTheme === 'light' ? 'fa-sun' : 'fa-moon';
  };

  const getThemeLabel = () => {
    if (isSystemTheme) {
      return `System (${effectiveTheme})`;
    }
    return effectiveTheme === 'light' ? 'Light' : 'Dark';
  };

  return (
    <button
      onClick={handleToggle}
      className={`
        inline-flex items-center gap-2 px-3 py-2 rounded-md text-sm font-medium 
        transition-all duration-200 hover:scale-105
        bg-gray-100 hover:bg-gray-200 dark:bg-gray-800 dark:hover:bg-gray-700
        text-gray-700 dark:text-gray-300 hover:text-gray-900 dark:hover:text-gray-100
        border border-gray-300 dark:border-gray-600
        focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 
        dark:focus:ring-offset-gray-800
        ${className}
      `}
      title={`Switch to ${getNextTheme()} theme`}
      aria-label={`Current theme: ${getThemeLabel()}. Click to switch to ${getNextTheme()} theme.`}
    >
      <i className={`fas ${getThemeIcon()} transition-transform duration-200`}></i>
      {showLabel && (
        <span className="hidden sm:inline">
          {getThemeLabel()}
        </span>
      )}
    </button>
  );
};

export default ThemeToggle;