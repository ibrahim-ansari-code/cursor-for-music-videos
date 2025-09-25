import React, { memo } from 'react';
import { ErrorMessageProps } from '../../types/integrations';

const ErrorMessage: React.FC<ErrorMessageProps> = memo(({ error, onRetry }) => {
  if (!error) return null;

  return (
    <div
      className="bg-red-100 dark:bg-red-900/20 border border-red-400 dark:border-red-600 text-red-700 dark:text-red-400 px-4 py-3 rounded-md mb-6"
      role="alert"
      aria-live="assertive"
    >
      <div className="flex items-center">
        <i className="fas fa-exclamation-circle mr-3 text-red-500" aria-hidden="true" />
        <span className="flex-grow" id="error-message">{error}</span>
        <button
          type="button"
          onClick={onRetry}
          className="ml-4 bg-red-600 dark:bg-red-700 hover:bg-red-700 dark:hover:bg-red-600 focus:bg-red-700 dark:focus:bg-red-600 text-white font-bold py-1 px-3 rounded text-sm transition-colors focus:outline-none focus:ring-2 focus:ring-red-500 focus:ring-offset-2 dark:focus:ring-offset-gray-800"
          aria-describedby="error-message"
          aria-label="Retry loading integrations"
        >
          Retry
        </button>
      </div>
    </div>
  );
});

ErrorMessage.displayName = 'ErrorMessage';

export default ErrorMessage;