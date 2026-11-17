import React from 'react';
import { useTranslation } from '../i18n/LanguageContext';

export interface SourceLineProps {
  sourceName?: string;
  issuedAt?: string;
  validUntil?: string;
  attribution?: string;
  isImdConnected?: boolean;
  className?: string;
}

export const SourceLine: React.FC<SourceLineProps> = ({
  sourceName = 'Open-Meteo (model data)',
  issuedAt,
  validUntil,
  attribution,
  isImdConnected = false,
  className = '',
}) => {
  const { t } = useTranslation();

  return (
    <div className={`text-xs text-slate-500 dark:text-slate-400 space-y-1 ${className}`}>
      <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
        <span className="font-medium text-slate-700 dark:text-slate-300">
          {t('source')}: {sourceName}
        </span>
        {issuedAt && (
          <>
            <span aria-hidden="true">•</span>
            <span>
              {t('issued')}: {issuedAt}
            </span>
          </>
        )}
        {validUntil && (
          <>
            <span aria-hidden="true">•</span>
            <span>
              {t('valid_until')}: {validUntil}
            </span>
          </>
        )}
      </div>

      {!isImdConnected && (
        <div className="text-[11px] text-amber-700 dark:text-amber-400 flex items-center gap-1 font-medium">
          <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <span>{t('imd_not_connected')}</span>
        </div>
      )}

      {attribution && (
        <div className="text-[10px] text-slate-400 dark:text-slate-500">
          {attribution}
        </div>
      )}
    </div>
  );
};
