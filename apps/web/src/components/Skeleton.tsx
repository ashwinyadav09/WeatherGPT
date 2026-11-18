import React from 'react';
import { useTranslation } from '../i18n/LanguageContext';

export interface SkeletonProps {
  lines?: number;
  className?: string;
  message?: string;
}

export const Skeleton: React.FC<SkeletonProps> = ({
  lines = 3,
  className = '',
  message,
}) => {
  const { t } = useTranslation();
  const displayMsg = message || t('fetching');

  return (
    <div
      role="status"
      aria-busy="true"
      aria-live="polite"
      className={`bg-white dark:bg-slate-900 rounded-spec border border-slate-200 dark:border-slate-800 p-5 shadow-sm animate-pulse max-w-column w-full ${className}`}
    >
      <div className="flex items-center gap-2 mb-4">
        <div className="h-4 w-4 rounded-full bg-blue-300 dark:bg-blue-700 animate-spin" />
        <span className="text-xs font-semibold text-blue-700 dark:text-blue-300">
          {displayMsg}
        </span>
      </div>

      <div className="h-7 bg-slate-200 dark:bg-slate-800 rounded-lg w-3/4 mb-4"></div>
      <div className="space-y-2.5">
        {Array.from({ length: lines }).map((_, i) => (
          <div
            key={i}
            className="h-4 bg-slate-100 dark:bg-slate-800 rounded-md"
            style={{ width: `${85 - i * 15}%` }}
          />
        ))}
      </div>
      <span className="sr-only">{displayMsg}</span>
    </div>
  );
};
