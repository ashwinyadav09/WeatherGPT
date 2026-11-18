import React, { useState, useEffect } from 'react';
import { useTranslation } from '../../i18n/LanguageContext';
import { LanguageSwitcher } from '../../i18n/LanguageSwitcher';
import { Card } from '../../components/Card';
import { Button } from '../../components/Button';

interface LicenceEntryModel {
  source_id: string;
  name: string;
  terms: string;
  limits: string;
  attribution_text: string;
}

const FALLBACK_LICENCES: LicenceEntryModel[] = [
  {
    source_id: 'open_meteo.forecast',
    name: 'Open-Meteo Weather Forecast API',
    terms: 'CC BY 4.0, Non-commercial use',
    limits: 'Under 10,000 calls/day, 5,000/hour, 600/minute',
    attribution_text: 'Weather data by Open-Meteo.com (CC BY 4.0)',
  },
  {
    source_id: 'sachet.cap',
    name: 'NDMA SACHET Alert Feed',
    terms: 'National public safety disaster alert feeds, relay as issued',
    limits: 'Periodic polling under 60 requests/hour',
    attribution_text: 'National Disaster Management Authority (NDMA) SACHET',
  },
  {
    source_id: 'imd.city_forecast',
    name: 'India Meteorological Department (IMD)',
    terms: 'Government of India public data, non-commercial public interest',
    limits: 'Cached 15m; rate limit backed off gracefully',
    attribution_text: 'India Meteorological Department (IMD), Ministry of Earth Sciences',
  },
  {
    source_id: 'ecmwf.ifs',
    name: 'ECMWF Open Data',
    terms: 'CC-BY-4.0',
    limits: 'Open data policy',
    attribution_text: 'European Centre for Medium-Range Weather Forecasts (ECMWF)',
  },
];

interface MorePageProps {
  onOpenAdmin?: () => void;
}

export const MorePage: React.FC<MorePageProps> = ({ onOpenAdmin }) => {
  const { t, language } = useTranslation();

  // Settings State persisted in localStorage
  const [dataSaver, setDataSaver] = useState<boolean>(() => {
    return localStorage.getItem('weathergpt_data_saver') === 'true';
  });
  const [voiceAutoplay, setVoiceAutoplay] = useState<boolean>(() => {
    return localStorage.getItem('weathergpt_voice_autoplay') === 'true';
  });
  const [textSize, setTextSize] = useState<'standard' | 'large' | 'xlarge'>(() => {
    return (localStorage.getItem('weathergpt_text_size') as any) || 'standard';
  });
  const [minAlertSeverity, setMinAlertSeverity] = useState<string>(() => {
    return localStorage.getItem('weathergpt_alert_severity') || 'yellow';
  });
  const [quietHours, setQuietHours] = useState<boolean>(() => {
    return localStorage.getItem('weathergpt_quiet_hours') === 'true';
  });

  // Licences State
  const [licences, setLicences] = useState<LicenceEntryModel[]>(FALLBACK_LICENCES);

  // Privacy State
  const [locationConsent, setLocationConsent] = useState(true);
  const [voiceConsent, setVoiceConsent] = useState(true);
  const [deleteStatus, setDeleteStatus] = useState<string | null>(null);

  // Install Prompt State
  const [installPrompt, setInstallPrompt] = useState<any>(null);
  const [installed, setInstalled] = useState(false);

  useEffect(() => {
    window.addEventListener('beforeinstallprompt', (e) => {
      e.preventDefault();
      setInstallPrompt(e);
    });

    window.addEventListener('appinstalled', () => {
      setInstalled(true);
      setInstallPrompt(null);
    });

    // Fetch licences from API
    fetch('/v1/sources')
      .then((res) => res.json())
      .then((data) => {
        if (Array.isArray(data) && data.length > 0) {
          setLicences(data);
        }
      })
      .catch(() => {
        setLicences(FALLBACK_LICENCES);
      });
  }, []);

  const handleToggleDataSaver = () => {
    const next = !dataSaver;
    setDataSaver(next);
    localStorage.setItem('weathergpt_data_saver', String(next));
    if (next) {
      setVoiceAutoplay(false);
      localStorage.setItem('weathergpt_voice_autoplay', 'false');
    }
  };

  const handleTextSizeChange = (size: 'standard' | 'large' | 'xlarge') => {
    setTextSize(size);
    localStorage.setItem('weathergpt_text_size', size);
    if (size === 'xlarge') {
      document.documentElement.style.fontSize = '22px';
    } else if (size === 'large') {
      document.documentElement.style.fontSize = '20px';
    } else {
      document.documentElement.style.fontSize = '18px';
    }
  };

  const handlePromptInstall = async () => {
    if (!installPrompt) {
      alert('To install: Tap the browser share/menu button and select "Add to Home Screen".');
      return;
    }
    installPrompt.prompt();
    const result = await installPrompt.userChoice;
    if (result.outcome === 'accepted') {
      setInstalled(true);
    }
    setInstallPrompt(null);
  };

  const handleDeleteMyData = async () => {
    try {
      const res = await fetch('/v1/privacy/delete-data', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: 'web_session' }),
      });
      const data = await res.json();
      localStorage.clear();
      setDeleteStatus(`Data permanently purged. Audit reference: ${data.audit_reference || 'del_ok'}`);
    } catch {
      localStorage.clear();
      setDeleteStatus('Device data cleared.');
    }
  };

  return (
    <div className="max-w-column mx-auto px-4 py-6 space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100">
          {t('more')}
        </h1>
        <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
          Settings, PWA install, sources & licences, and privacy controls
        </p>
      </div>

      {/* Install PWA Prompt */}
      {!installed && (
        <Card className="bg-gradient-to-r from-blue-600 to-indigo-700 text-white border-none shadow-md">
          <div className="flex items-center justify-between gap-4">
            <div>
              <h2 className="text-base font-bold text-white mb-1">
                Install WeatherGPT App
              </h2>
              <p className="text-xs text-blue-100 leading-relaxed">
                Add to your home screen for quick offline access and warnings.
              </p>
            </div>
            <Button
              type="button"
              variant="secondary"
              size="sm"
              onClick={handlePromptInstall}
              className="bg-white text-blue-700 hover:bg-blue-50 font-bold flex-shrink-0"
            >
              {t('install')}
            </Button>
          </div>
        </Card>
      )}

      {/* Settings Section */}
      <Card>
        <h2 className="text-lg font-bold text-slate-900 dark:text-slate-100 mb-4">
          {t('settings')}
        </h2>

        <div className="space-y-5">
          {/* Language selection */}
          <div className="flex items-center justify-between pb-3 border-b border-slate-100 dark:border-slate-800">
            <div>
              <span className="font-semibold text-sm text-slate-800 dark:text-slate-200 block">
                {t('language')}
              </span>
              <span className="text-xs text-slate-500">English / हिन्दी</span>
            </div>
            <LanguageSwitcher />
          </div>

          {/* Text Size */}
          <div className="flex items-center justify-between pb-3 border-b border-slate-100 dark:border-slate-800">
            <div>
              <span className="font-semibold text-sm text-slate-800 dark:text-slate-200 block">
                Text Size
              </span>
              <span className="text-xs text-slate-500">Accessible font scaling</span>
            </div>
            <div className="inline-flex rounded-lg bg-slate-200 dark:bg-slate-800 p-1">
              {(['standard', 'large', 'xlarge'] as const).map((sz) => (
                <button
                  key={sz}
                  type="button"
                  onClick={() => handleTextSizeChange(sz)}
                  className={`px-2.5 py-1 text-xs font-semibold rounded-md transition-all ${
                    textSize === sz
                      ? 'bg-white dark:bg-slate-700 text-blue-700 dark:text-blue-300 shadow-sm'
                      : 'text-slate-600 dark:text-slate-400'
                  }`}
                >
                  {sz === 'standard' ? '100%' : sz === 'large' ? '125%' : '150%'}
                </button>
              ))}
            </div>
          </div>

          {/* Data Saver Mode */}
          <div className="flex items-center justify-between pb-3 border-b border-slate-100 dark:border-slate-800">
            <div>
              <span className="font-semibold text-sm text-slate-800 dark:text-slate-200 block">
                Data-Saver Mode
              </span>
              <span className="text-xs text-slate-500">
                Skips optional background telemetry and audio autoplay
              </span>
            </div>
            <button
              type="button"
              role="switch"
              aria-checked={dataSaver}
              onClick={handleToggleDataSaver}
              className={`w-12 h-6 rounded-full transition-colors relative focus-visible:outline focus-visible:outline-3 focus-visible:outline-focus-ring ${
                dataSaver ? 'bg-blue-600' : 'bg-slate-300 dark:bg-slate-700'
              }`}
            >
              <span
                className={`w-4 h-4 rounded-full bg-white absolute top-1 transition-transform ${
                  dataSaver ? 'left-7' : 'left-1'
                }`}
              />
            </button>
          </div>

          {/* Notifications & Quiet hours */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <div>
                <span className="font-semibold text-sm text-slate-800 dark:text-slate-200 block">
                  Alert Severity Filter
                </span>
                <span className="text-xs text-slate-500">Minimum level for notifications</span>
              </div>
              <select
                value={minAlertSeverity}
                onChange={(e) => {
                  setMinAlertSeverity(e.target.value);
                  localStorage.setItem('weathergpt_alert_severity', e.target.value);
                }}
                className="text-xs rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 py-1.5 font-medium"
              >
                <option value="yellow">Yellow+ (Watch)</option>
                <option value="orange">Orange+ (Alert)</option>
                <option value="red">Red only (Warning)</option>
              </select>
            </div>

            <div className="flex items-center justify-between pt-2">
              <div>
                <span className="font-semibold text-sm text-slate-800 dark:text-slate-200 block">
                  Quiet Hours (22:00 - 07:00)
                </span>
                <span className="text-xs text-slate-500">
                  Red / Warning level alerts always pass through
                </span>
              </div>
              <button
                type="button"
                role="switch"
                aria-checked={quietHours}
                onClick={() => {
                  const next = !quietHours;
                  setQuietHours(next);
                  localStorage.setItem('weathergpt_quiet_hours', String(next));
                }}
                className={`w-12 h-6 rounded-full transition-colors relative focus-visible:outline focus-visible:outline-3 focus-visible:outline-focus-ring ${
                  quietHours ? 'bg-blue-600' : 'bg-slate-300 dark:bg-slate-700'
                }`}
              >
                <span
                  className={`w-4 h-4 rounded-full bg-white absolute top-1 transition-transform ${
                    quietHours ? 'left-7' : 'left-1'
                  }`}
                />
              </button>
            </div>
          </div>
        </div>
      </Card>

      {/* Sources and Licences */}
      <Card>
        <div className="flex items-center justify-between mb-2">
          <h2 className="text-lg font-bold text-slate-900 dark:text-slate-100">
            {t('sources_and_licences')}
          </h2>
          <span className="text-xs font-semibold bg-emerald-100 dark:bg-emerald-950/60 text-emerald-800 dark:text-emerald-300 px-2.5 py-1 rounded-md">
            Non-commercial Pilot
          </span>
        </div>

        <p className="text-xs text-slate-600 dark:text-slate-400 mb-4 leading-relaxed">
          WeatherGPT is a non-commercial, public-interest pilot for India. No ads, no commercial use, and no resale of data. All numbers carry attribution and authority tiers.
        </p>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs border-collapse">
            <thead>
              <tr className="border-b border-slate-200 dark:border-slate-800 text-slate-500">
                <th className="py-2 pr-3 font-semibold">Source</th>
                <th className="py-2 px-3 font-semibold">Terms</th>
                <th className="py-2 pl-3 font-semibold">Attribution</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-800 text-slate-700 dark:text-slate-300">
              {licences.map((lic) => (
                <tr key={lic.source_id}>
                  <td className="py-2.5 pr-3 font-medium text-slate-900 dark:text-slate-100">
                    {lic.name}
                  </td>
                  <td className="py-2.5 px-3 text-slate-500">
                    {lic.terms}
                  </td>
                  <td className="py-2.5 pl-3 text-slate-600 dark:text-slate-400">
                    {lic.attribution_text}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>

      {/* Privacy and Consent */}
      <Card>
        <h2 className="text-lg font-bold text-slate-900 dark:text-slate-100 mb-2">
          {t('privacy')}
        </h2>
        <p className="text-xs text-slate-600 dark:text-slate-400 mb-4 leading-relaxed">
          Compliant with the Digital Personal Data Protection (DPDP) Act 2023. We collect only what is strictly necessary to provide hyperlocal weather and warnings.
        </p>

        <div className="space-y-3 mb-5">
          <div className="p-3 bg-slate-50 dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 flex items-start justify-between gap-3">
            <div>
              <span className="font-semibold text-xs text-slate-900 dark:text-slate-100 block">
                {language === 'hi' ? 'स्थान (Location) डेटा' : 'Location Data'}
              </span>
              <span className="text-[11px] text-slate-500 block mt-0.5">
                {language === 'hi'
                  ? 'सटीक मौसम और आपदा चेतावनी देने के लिए उपयोग होता है।'
                  : 'Used only to fetch hyperlocal forecasts and warnings.'}
              </span>
            </div>
            <button
              type="button"
              role="switch"
              aria-checked={locationConsent}
              onClick={() => setLocationConsent(!locationConsent)}
              className={`w-10 h-5 rounded-full transition-colors relative focus-visible:outline focus-visible:outline-3 focus-visible:outline-focus-ring ${
                locationConsent ? 'bg-blue-600' : 'bg-slate-300 dark:bg-slate-700'
              }`}
            >
              <span
                className={`w-3.5 h-3.5 rounded-full bg-white absolute top-0.5 transition-transform ${
                  locationConsent ? 'left-5' : 'left-1'
                }`}
              />
            </button>
          </div>

          <div className="p-3 bg-slate-50 dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 flex items-start justify-between gap-3">
            <div>
              <span className="font-semibold text-xs text-slate-900 dark:text-slate-100 block">
                {language === 'hi' ? 'आवाज़ (Voice) ऑडियो' : 'Voice Query Audio'}
              </span>
              <span className="text-[11px] text-slate-500 block mt-0.5">
                {language === 'hi'
                  ? 'रियल-टाइम आवाज़ पहचान के लिए उपयोग होता है। स्थायी रूप से कोई ऑडियो नहीं रखा जाता।'
                  : 'Streamed in real-time for speech-to-text. Raw audio is immediately discarded.'}
              </span>
            </div>
            <button
              type="button"
              role="switch"
              aria-checked={voiceConsent}
              onClick={() => setVoiceConsent(!voiceConsent)}
              className={`w-10 h-5 rounded-full transition-colors relative focus-visible:outline focus-visible:outline-3 focus-visible:outline-focus-ring ${
                voiceConsent ? 'bg-blue-600' : 'bg-slate-300 dark:bg-slate-700'
              }`}
            >
              <span
                className={`w-3.5 h-3.5 rounded-full bg-white absolute top-0.5 transition-transform ${
                  voiceConsent ? 'left-5' : 'left-1'
                }`}
              />
            </button>
          </div>
        </div>

        <div className="border-t border-slate-100 dark:border-slate-800 pt-4 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
          <div>
            <span className="text-xs font-semibold text-slate-700 dark:text-slate-300 block">
              Grievance Officer: Ashwin Yadav
            </span>
            <span className="text-[11px] text-slate-400">
              privacy@weathergpt.in • 72h turnaround
            </span>
          </div>

          <Button
            type="button"
            variant="danger"
            size="sm"
            onClick={handleDeleteMyData}
          >
            {t('delete_my_data')}
          </Button>
        </div>

        {deleteStatus && (
          <div role="status" className="mt-3 p-2.5 rounded-lg bg-emerald-50 dark:bg-emerald-950/40 text-emerald-800 dark:text-emerald-300 text-xs font-medium border border-emerald-200 dark:border-emerald-900">
            {deleteStatus}
          </div>
        )}
      </Card>

      {/* Admin Link */}
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
