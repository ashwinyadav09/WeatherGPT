import React from 'react';
import { useTranslation } from '../i18n/LanguageContext';

export interface OfflineBannerProps {
  lastSavedAt?: string;
  className?: string;
}

export const OfflineBanner: React.FC<OfflineBannerProps> = ({
  lastSavedAt,
  className = '',
}) => {
  const { t } = useTranslation();

  return (
    <div
      role="status"
      className={`rounded-spec p-3.5 border border-slate-300 dark:border-slate-700 bg-slate-100 dark:bg-slate-800 text-slate-800 dark:text-slate-200 flex items-center gap-2.5 text-xs font-medium shadow-sm ${className}`}
    >
      <svg
        className="w-4 h-4 text-slate-500 dark:text-slate-400 flex-shrink-0"
        fill="none"
        stroke="currentColor"
        viewBox="0 0 24 24"
        aria-hidden="true"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth="2"
          d="M18.364 5.636a9 9 0 010 12.728m0 0l-2.829-2.829m2.829 2.829L21 21M15.536 8.464a5 5 0 010 7.072m0 0l-2.829-2.829m-4.243 4.243a9 9 0 01-12.728-12.728m0 0l2.829 2.829m-2.829-2.829L3 3"
        />
      </svg>
      <div>
        <span>{t('offline_notice')}</span>
        {lastSavedAt && (
          <span className="block text-[11px] text-slate-500 dark:text-slate-400 mt-0.5">
            {t('issued')}: {lastSavedAt}
          </span>
        )}
      </div>
    </div>
  );
};
