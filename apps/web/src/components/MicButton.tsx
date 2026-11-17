import React, { ButtonHTMLAttributes } from 'react';
import { useTranslation } from '../i18n/LanguageContext';

export interface MicButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  isListening?: boolean;
  isProcessing?: boolean;
}

export const MicButton: React.FC<MicButtonProps> = ({
  isListening = false,
  isProcessing = false,
  className = '',
  disabled,
  onClick,
  ...props
}) => {
  const { t } = useTranslation();

  const label = isListening
    ? t('listening')
    : isProcessing
    ? t('processing')
    : t('hold_to_speak');

  return (
    <button
      type="button"
      aria-label={label}
      aria-pressed={isListening}
      disabled={disabled || isProcessing}
      onClick={onClick}
      className={`relative inline-flex items-center justify-center min-w-touch min-h-touch w-12 h-12 rounded-full transition-all focus-visible:outline focus-visible:outline-3 focus-visible:outline-focus-ring focus-visible:outline-offset-2 ${
        isListening
          ? 'bg-alert-red text-white shadow-lg scale-105 animate-pulse'
          : isProcessing
          ? 'bg-slate-300 dark:bg-slate-700 text-slate-500 cursor-wait'
          : 'bg-blue-600 hover:bg-blue-700 active:bg-blue-800 text-white shadow-md'
      } ${className}`}
      {...props}
    >
      {/* Ripple ring effect while listening */}
      {isListening && (
        <span
          className="absolute -inset-1 rounded-full border-2 border-red-500 animate-ping opacity-75 pointer-events-none"
          aria-hidden="true"
        />
      )}

      {isProcessing ? (
        <svg
          className="w-5 h-5 animate-spin"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
          aria-hidden="true"
        >
          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
          <path
            className="opacity-75"
            fill="currentColor"
            d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
          ></path>
        </svg>
      ) : (
        <svg
          className="w-6 h-6"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
          aria-hidden="true"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth="2"
            d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z"
          />
        </svg>
      )}
      <span className="sr-only">{label}</span>
    </button>
  );
};
