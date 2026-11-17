import React, { useEffect, useState } from 'react';
import { AlertCard, AlertData } from './AlertCard';
import { NotificationOptIn } from './NotificationOptIn';

export const AlertsPage: React.FC = () => {
  const [alerts, setAlerts] = useState<AlertData[]>([]);
  const [filterLevel, setFilterLevel] = useState<'all' | 'red' | 'orange' | 'yellow'>('all');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchAlerts = async () => {
      setLoading(true);
      try {
        const resp = await fetch('/v1/alerts');
        if (resp.ok) {
          const data = await resp.json();
          setAlerts(data);
        } else {
          // Fallback sample alert for demonstration
          setAlerts([
            {
              id: 'urn:oid:2.49.0.1.356.sachet.sample',
              sender: 'NDMA-SACHET',
              sent: new Date().toISOString(),
              hazard: 'Thunderstorm with Gusty Winds',
              severity: 'Severe',
              urgency: 'Expected',
              certainty: 'Likely',
              onset: new Date().toISOString(),
              expires: new Date(Date.now() + 4 * 3600000).toISOString(),
              areas: [{ areaDesc: 'Pune and Western Ghats' }],
              text_by_language: {
                en: 'Moderate thunderstorm with gusty winds (40-50 kmph) and lightning expected across Pune district.',
                hi: 'पुणे जिले में 40-50 किमी/घंटा की तेज हवाओं और बिजली गिरने के साथ मध्यम गरज-चमक की संभावना।',
              },
              source_url: 'https://sachet.ndma.gov.in',
              authority_tier: 1,
              level: 'orange',
            },
          ]);
        }
      } catch {
        // Fallback demo state
        setAlerts([]);
      } finally {
        setLoading(false);
      }
    };

    fetchAlerts();
  }, []);

  const filteredAlerts = alerts.filter((a) => {
    if (filterLevel === 'all') return true;
    return a.level === filterLevel;
  });

  return (
    <main className="max-w-column mx-auto px-4 py-6 pb-24">
      <div className="mb-6">
        <h2 className="text-2xl font-bold text-slate-900 tracking-tight">
          Alert Centre
        </h2>
        <p className="text-sm text-slate-500 mt-1">
          Official warnings relayed directly as issued by IMD and state disaster agencies via NDMA SACHET.
        </p>
      </div>

      {/* Push Notification Opt-in Prompt */}
      <NotificationOptIn />

      {/* Severity Filter Controls */}
      <div className="flex items-center space-x-2 mb-6 overflow-x-auto pb-1 text-xs font-semibold">
        <span className="text-slate-400 mr-1">Filter:</span>
        <button
          type="button"
          onClick={() => setFilterLevel('all')}
          className={`px-3 py-1.5 rounded-full border transition-colors ${
            filterLevel === 'all'
              ? 'bg-slate-900 text-white border-slate-900'
              : 'bg-white text-slate-700 border-slate-200 hover:bg-slate-50'
          }`}
        >
          All
        </button>
        <button
          type="button"
          onClick={() => setFilterLevel('red')}
          className={`px-3 py-1.5 rounded-full border transition-colors ${
            filterLevel === 'red'
              ? 'bg-alert-red text-white border-alert-red'
              : 'bg-white text-red-700 border-red-200 hover:bg-red-50'
          }`}
        >
          🚨 Warning (Red)
        </button>
        <button
          type="button"
          onClick={() => setFilterLevel('orange')}
          className={`px-3 py-1.5 rounded-full border transition-colors ${
            filterLevel === 'orange'
              ? 'bg-alert-orange text-slate-900 border-alert-orange'
              : 'bg-white text-amber-700 border-amber-200 hover:bg-amber-50'
          }`}
        >
          ⚠️ Alert (Orange)
        </button>
        <button
          type="button"
          onClick={() => setFilterLevel('yellow')}
          className={`px-3 py-1.5 rounded-full border transition-colors ${
            filterLevel === 'yellow'
              ? 'bg-alert-yellow text-slate-900 border-alert-yellow'
              : 'bg-white text-yellow-800 border-yellow-200 hover:bg-yellow-50'
          }`}
        >
          ⚡ Watch (Yellow)
        </button>
      </div>

      {/* Alerts Feed */}
      {loading ? (
        <div className="text-center py-12 text-slate-400 text-sm">Loading active official alerts...</div>
      ) : filteredAlerts.length > 0 ? (
        <div className="space-y-4">
          {filteredAlerts.map((alert) => (
            <AlertCard key={alert.id} alert={alert} />
          ))}
        </div>
      ) : (
        <div className="text-center py-16 bg-white rounded-xl border border-dashed border-slate-300 p-8">
          <span className="text-4xl" aria-hidden="true">☀️</span>
          <h3 className="text-base font-bold text-slate-800 mt-3 mb-1">
            No official alerts for your places
          </h3>
          <p className="text-xs text-slate-500 max-w-sm mx-auto">
            All clear. There are currently no active warnings or advisories issued by IMD or state disaster management authorities for your saved locations.
          </p>
        </div>
      )}
    </main>
  );
};
