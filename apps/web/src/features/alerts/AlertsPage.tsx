import React, { useState, useEffect } from 'react';
import { useTranslation } from '../../i18n/LanguageContext';
import { AlertBadge } from '../../components/AlertBadge';
import { Card } from '../../components/Card';
import { AlertModel, MOCK_ALERTS } from '../../mocks/mockData';

export const AlertsPage: React.FC = () => {
  const { t, language } = useTranslation();
  const [alerts, setAlerts] = useState<AlertModel[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch('/v1/alerts')
      .then((res) => res.json())
      .then((data) => {
        setAlerts(data);
        setLoading(false);
      })
      .catch(() => {
        setAlerts(MOCK_ALERTS);
        setLoading(false);
      });
  }, []);

  return (
    <div className="max-w-column mx-auto px-4 py-6" aria-live="polite">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100">
            {t('alerts')}
          </h1>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
            Official warnings from IMD and NDMA SACHET
          </p>
        </div>
      </div>

      {loading ? (
        <div className="text-center py-12 text-slate-500 text-sm">
          {t('fetching')}
        </div>
      ) : alerts.length === 0 ? (
        <div className="text-center py-12 bg-white dark:bg-slate-900 rounded-spec border border-slate-200 dark:border-slate-800 p-8">
          <svg className="w-12 h-12 mx-auto text-slate-400 mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <h2 className="text-base font-semibold text-slate-800 dark:text-slate-200 mb-1">
            {t('no_alerts')}
          </h2>
          <p className="text-xs text-slate-500">All saved districts and places are currently normal.</p>
        </div>
      ) : (
        <div className="space-y-4">
          {alerts.map((alert) => {
            const desc =
              language === 'hi' && alert.text_by_language?.hi
                ? alert.text_by_language.hi
                : alert.text_by_language?.en || alert.hazard;

            return (
              <Card key={alert.id} className="border-l-4" style={{ borderLeftColor: alert.level === 'red' ? '#C62828' : alert.level === 'orange' ? '#E8710A' : '#F2C200' }}>
                <div className="flex items-center justify-between mb-3">
                  <AlertBadge level={alert.level} />
                  <span className="text-xs text-slate-400">
                    {alert.severity} • {alert.urgency}
                  </span>
                </div>

                <h2 className="text-lg font-bold text-slate-900 dark:text-slate-100 mb-1">
                  {alert.hazard}
                </h2>

                <p className="text-sm text-slate-700 dark:text-slate-300 leading-relaxed mb-4">
                  {desc}
                </p>

                <div className="border-t border-slate-100 dark:border-slate-800 pt-3 text-xs text-slate-500 flex flex-wrap justify-between gap-2">
                  <span>Issued by IMD via SACHET</span>
                  <span>Expires: {new Date(alert.expires).toLocaleDateString()}</span>
                </div>
              </Card>
            );
          })}
        </div>
      )}
    </div>
  );
};
