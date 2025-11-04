import React from 'react';

interface ModeSelectorProps {
  mode: 'file' | 'manual';
  onModeChange: (mode: 'file' | 'manual') => void;
}

export const ModeSelector: React.FC<ModeSelectorProps> = ({ mode, onModeChange }) => {
  return (
    <div className="p-6 border-b border-gray-200 dark:border-gray-700">
      <div className="grid grid-cols-2 gap-4">
        <div 
          onClick={() => onModeChange('file')} 
          role="button"
          tabIndex={0}
          onKeyDown={(e) => { if (e.key === 'Enter') onModeChange('file'); }}
          className={`p-4 border-2 rounded-lg cursor-pointer text-center transition-colors ${
            mode === 'file' 
              ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20' 
              : 'border-gray-300 dark:border-gray-600 hover:border-gray-400 dark:hover:border-gray-500'
          }`}
        >
          <i className="fas fa-file-upload text-2xl text-blue-600 dark:text-blue-400 mb-2"></i>
          <h3 className="font-semibold text-gray-900 dark:text-gray-100">File Upload</h3>
          <p className="text-xs text-gray-500 dark:text-gray-400">Upload lease PDF to parse</p>
        </div>
        <div 
          onClick={() => onModeChange('manual')} 
          role="button"
          tabIndex={0}
          onKeyDown={(e) => { if (e.key === 'Enter') onModeChange('manual'); }}
          className={`p-4 border-2 rounded-lg cursor-pointer text-center transition-colors ${
            mode === 'manual' 
              ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20' 
              : 'border-gray-300 dark:border-gray-600 hover:border-gray-400 dark:hover:border-gray-500'
          }`}
        >
          <i className="fas fa-keyboard text-2xl text-blue-600 dark:text-blue-400 mb-2"></i>
          <h3 className="font-semibold text-gray-900 dark:text-gray-100">Manual Entry</h3>
          <p className="text-xs text-gray-500 dark:text-gray-400">Enter lease details directly</p>
        </div>
      </div>
    </div>
  );
};

