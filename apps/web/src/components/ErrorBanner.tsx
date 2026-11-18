import React from 'react';
import { useTranslation } from '../i18n/LanguageContext';
import { Button } from './Button';

export interface ErrorBannerProps {
  message?: string;
  onRetry?: () => void;
  className?: string;
}

export const ErrorBanner: React.FC<ErrorBannerProps> = ({
  message,
  onRetry,
  className = '',
}) => {
  const { t } = useTranslation();
  const displayMsg = message || 'Something went wrong while connecting to weather services.';

  return (
    <div
      role="alert"
      className={`rounded-spec p-4 border border-red-300 dark:border-red-900 bg-red-50 dark:bg-red-950/40 text-red-900 dark:text-red-200 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 shadow-sm ${className}`}
    >
      <div className="flex items-start gap-2.5">
        <svg
          className="w-5 h-5 text-red-600 dark:text-red-400 mt-0.5 flex-shrink-0"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
          aria-hidden="true"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth="2"
            d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
          />
        </svg>
        <span className="text-sm font-medium">{displayMsg}</span>
      </div>

      {onRetry && (
        <Button
          type="button"
          variant="secondary"
          size="sm"
          onClick={onRetry}
          className="self-end sm:self-auto bg-red-100 dark:bg-red-900 hover:bg-red-200 dark:hover:bg-red-800 text-red-900 dark:text-red-100"
        >
          {t('retry')}
        </Button>
      )}
    </div>
  );
};
