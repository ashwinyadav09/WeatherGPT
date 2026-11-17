import React from 'react';
import { useTranslation } from '../../i18n/LanguageContext';
import { LanguageSwitcher } from '../../i18n/LanguageSwitcher';
import { Card } from '../../components/Card';
import { Button } from '../../components/Button';

interface MorePageProps {
  onOpenAdmin?: () => void;
}

export const MorePage: React.FC<MorePageProps> = ({ onOpenAdmin }) => {
  const { t } = useTranslation();

  return (
    <div className="max-w-column mx-auto px-4 py-6 space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100">
          {t('more')}
        </h1>
        <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
          Settings, sources, licences, privacy and administration
        </p>
      </div>

      {/* Language Setting */}
      <Card>
        <h2 className="text-base font-bold text-slate-900 dark:text-slate-100 mb-3">
          {t('language')}
        </h2>
        <div className="flex items-center justify-between">
          <span className="text-sm text-slate-600 dark:text-slate-400">
            Select application language
          </span>
          <LanguageSwitcher />
        </div>
      </Card>

      {/* About & Public Interest */}
      <Card>
        <h2 className="text-base font-bold text-slate-900 dark:text-slate-100 mb-2">
          About WeatherGPT
        </h2>
        <p className="text-sm text-slate-600 dark:text-slate-400 leading-relaxed mb-4">
          A grounded, multilingual, voice-first weather assistant for India. A non-commercial, public-interest pilot. The LLM explains; tools supply facts; official warnings are relayed as issued.
        </p>
        <div className="inline-block bg-blue-50 dark:bg-blue-950/40 text-blue-800 dark:text-blue-300 px-3 py-1.5 rounded-lg text-xs font-semibold">
          {t('non_commercial')}
        </div>
      </Card>

      {/* Sources & Licences */}
      <Card>
        <h2 className="text-base font-bold text-slate-900 dark:text-slate-100 mb-3">
          {t('sources_and_licences')}
        </h2>
        <div className="space-y-3 text-xs text-slate-600 dark:text-slate-400">
          <div className="flex justify-between py-1.5 border-b border-slate-100 dark:border-slate-800">
            <span className="font-semibold text-slate-800 dark:text-slate-200">Open-Meteo</span>
            <span>CC BY 4.0 (Model data)</span>
          </div>
          <div className="flex justify-between py-1.5 border-b border-slate-100 dark:border-slate-800">
            <span className="font-semibold text-slate-800 dark:text-slate-200">India Meteorological Department (IMD)</span>
            <span>Government of India (Official data)</span>
          </div>
          <div className="flex justify-between py-1.5 border-b border-slate-100 dark:border-slate-800">
            <span className="font-semibold text-slate-800 dark:text-slate-200">NDMA SACHET</span>
            <span>National Disaster Management Authority</span>
          </div>
          <div className="flex justify-between py-1.5">
            <span className="font-semibold text-slate-800 dark:text-slate-200">OpenStreetMap</span>
            <span>ODbL</span>
          </div>
        </div>
      </Card>

      {/* Privacy & Consent */}
      <Card>
        <h2 className="text-base font-bold text-slate-900 dark:text-slate-100 mb-2">
          {t('privacy')}
        </h2>
        <p className="text-xs text-slate-600 dark:text-slate-400 leading-relaxed mb-4">
          No raw voice audio is retained. Location data is stored only on your device or linked to your explicit session. You can purge all saved data at any time.
        </p>
        <Button
          type="button"
          variant="secondary"
          size="sm"
          onClick={() => {
            localStorage.clear();
            alert('Local data cleared.');
          }}
        >
          {t('delete_my_data')}
        </Button>
      </Card>

      {/* Admin console link */}
      {onOpenAdmin && (
        <Card>
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-sm font-bold text-slate-900 dark:text-slate-100">
                Admin Console
              </h2>
              <p className="text-xs text-slate-500">
                Manage glossary, alert templates, and audit logs
              </p>
            </div>
            <Button type="button" variant="primary" size="sm" onClick={onOpenAdmin}>
              Open
            </Button>
          </div>
        </Card>
      )}
    </div>
  );
};
