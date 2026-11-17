import React, { useState, useEffect } from 'react';

interface Subscription {
  id: string;
  subscriber_name: string;
  place_id: string;
  webhook_url: string;
  thresholds: {
    heat_index_c?: number | null;
    rain_rate_mm_hr?: number | null;
    lightning_warning?: boolean | null;
    wind_gust_kmh?: number | null;
  };
  cooldown_minutes: number;
  last_triggered_at?: string | null;
  is_active: boolean;
}

interface DeliveryLog {
  id: string;
  subscription_id: string;
  subscriber_name: string;
  place_id: string;
  webhook_url: string;
  triggered_thresholds: string[];
  dispatched_at: string;
  status_code: number | null;
  success: boolean;
  latency_ms: number;
}

export const SmartCityPage: React.FC = () => {
  const [subscriptions, setSubscriptions] = useState<Subscription[]>([]);
  const [deliveries, setDeliveries] = useState<DeliveryLog[]>([]);
  const [loading, setLoading] = useState(false);
  const [statusMsg, setStatusMsg] = useState<string | null>(null);

  // New Subscription Form State
  const [subscriberName, setSubscriberName] = useState('Pune Smart City Command Center');
  const [placeId, setPlaceId] = useState('pune');
  const [webhookUrl, setWebhookUrl] = useState('https://smartcity.example.gov.in/webhooks/weather');
  const [heatIndexThreshold, setHeatIndexThreshold] = useState('40.0');
  const [rainThreshold, setRainThreshold] = useState('20.0');
  const [lightningThreshold, setLightningThreshold] = useState(true);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    setLoading(true);
    try {
      const [subsResp, delivResp] = await Promise.all([
        fetch('/v1/smart-city/subscriptions'),
        fetch('/v1/smart-city/deliveries'),
      ]);
      if (subsResp.ok) {
        const subsJson = await subsResp.json();
        setSubscriptions(subsJson);
      }
      if (delivResp.ok) {
        const delivJson = await delivResp.json();
        setDeliveries(delivJson);
      }
    } catch {
      // offline / mock fallback
    } finally {
      setLoading(false);
    }
  };

  const handleCreateSubscription = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const payload = {
        subscriber_name: subscriberName,
        place_id: placeId,
        webhook_url: webhookUrl,
        thresholds: {
          heat_index_c: heatIndexThreshold ? parseFloat(heatIndexThreshold) : null,
          rain_rate_mm_hr: rainThreshold ? parseFloat(rainThreshold) : null,
          lightning_warning: lightningThreshold,
        },
        cooldown_minutes: 15,
      };

      const resp = await fetch('/v1/smart-city/subscriptions', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      if (resp.ok) {
        setStatusMsg('Subscription created successfully!');
        fetchData();
      } else {
        setStatusMsg('Failed to create subscription.');
      }
    } catch {
      setStatusMsg('Error creating subscription.');
    }
  };

  const handleSimulateSensorTrigger = async () => {
    try {
      const obs = {
        place_id: placeId,
        temperature_c: 38.0,
        relative_humidity_pct: 65.0,
        rain_rate_mm_hr: 25.0,
        lightning_detected: true,
        wind_gust_kmh: 45.0,
      };

      const resp = await fetch('/v1/smart-city/evaluate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(obs),
      });

      if (resp.ok) {
        const res = await resp.json();
        setStatusMsg(`Evaluated: Heat Index ${res.heat_index_c}°C. Dispatched ${res.triggered_deliveries} webhooks.`);
        fetchData();
      }
    } catch {
      setStatusMsg('Error simulating sensor trigger.');
    }
  };

  return (
    <div className="max-w-4xl mx-auto px-4 py-6 space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-900 flex items-center gap-2">
          <span>🏙️</span> Smart-City Threshold Webhooks
        </h1>
        <p className="text-sm text-slate-500">
          Subscribe municipal dashboards to real-time threshold alerts (heat index, rain intensity, lightning) with rate limiting
        </p>
      </div>

      {statusMsg && (
        <div className="p-3 bg-blue-50 border border-blue-200 text-blue-800 text-xs rounded-lg">
          {statusMsg}
        </div>
      )}

      {/* Subscription Creation Form */}
      <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm space-y-4">
        <h2 className="text-base font-bold text-slate-800">Add Webhook Subscription</h2>
        <form onSubmit={handleCreateSubscription} className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <label className="block text-xs font-medium text-slate-700">Subscriber Name</label>
            <input
              type="text"
              value={subscriberName}
              onChange={(e) => setSubscriberName(e.target.value)}
              className="mt-1 w-full border border-slate-300 rounded-lg px-3 py-1.5 text-sm"
              required
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-700">City / Place ID</label>
            <input
              type="text"
              value={placeId}
              onChange={(e) => setPlaceId(e.target.value)}
              className="mt-1 w-full border border-slate-300 rounded-lg px-3 py-1.5 text-sm"
              required
            />
          </div>

          <div className="sm:col-span-2">
            <label className="block text-xs font-medium text-slate-700">Webhook POST URL</label>
            <input
              type="url"
              value={webhookUrl}
              onChange={(e) => setWebhookUrl(e.target.value)}
              className="mt-1 w-full border border-slate-300 rounded-lg px-3 py-1.5 text-sm font-mono text-xs"
              required
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-700">Heat Index Threshold (°C)</label>
            <input
              type="number"
              step="0.5"
              value={heatIndexThreshold}
              onChange={(e) => setHeatIndexThreshold(e.target.value)}
              className="mt-1 w-full border border-slate-300 rounded-lg px-3 py-1.5 text-sm"
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-700">Rain Rate Threshold (mm/hr)</label>
            <input
              type="number"
              step="1"
              value={rainThreshold}
              onChange={(e) => setRainThreshold(e.target.value)}
              className="mt-1 w-full border border-slate-300 rounded-lg px-3 py-1.5 text-sm"
            />
          </div>

          <div className="flex items-center gap-2 mt-4">
            <input
              type="checkbox"
              id="lightning"
              checked={lightningThreshold}
              onChange={(e) => setLightningThreshold(e.target.checked)}
              className="rounded text-blue-600"
            />
            <label htmlFor="lightning" className="text-xs font-medium text-slate-700">
              Notify on Lightning / Thunderstorm
            </label>
          </div>

          <div className="sm:col-span-2 flex justify-end gap-3 pt-2">
            <button
              type="button"
              onClick={handleSimulateSensorTrigger}
              className="px-4 py-2 border border-slate-300 rounded-lg text-xs font-semibold text-slate-700 hover:bg-slate-50"
            >
              Simulate Severe Sensor Reading
            </button>
            <button
              type="submit"
              className="px-4 py-2 bg-blue-600 text-white rounded-lg text-xs font-semibold hover:bg-blue-700 shadow-sm"
            >
              Register Webhook
            </button>
          </div>
        </form>
      </div>

      {/* Active Subscriptions List */}
      <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm space-y-3">
        <h2 className="text-base font-bold text-slate-800">Active Subscriptions ({subscriptions.length})</h2>
        {subscriptions.length === 0 ? (
          <p className="text-xs text-slate-500">No active subscriptions yet.</p>
        ) : (
          <div className="divide-y divide-slate-100">
            {subscriptions.map((s) => (
              <div key={s.id} className="py-3 flex flex-wrap items-center justify-between gap-2">
                <div>
                  <div className="text-sm font-semibold text-slate-900">{s.subscriber_name}</div>
                  <div className="text-xs text-slate-500 font-mono mt-0.5">{s.place_id} • {s.webhook_url}</div>
                  <div className="text-xs text-slate-600 mt-1 flex gap-2">
                    {s.thresholds.heat_index_c && <span className="bg-amber-50 text-amber-800 px-1.5 py-0.5 rounded">HI ≥ {s.thresholds.heat_index_c}°C</span>}
                    {s.thresholds.rain_rate_mm_hr && <span className="bg-blue-50 text-blue-800 px-1.5 py-0.5 rounded">Rain ≥ {s.thresholds.rain_rate_mm_hr} mm/h</span>}
                    {s.thresholds.lightning_warning && <span className="bg-purple-50 text-purple-800 px-1.5 py-0.5 rounded">Lightning</span>}
                  </div>
                </div>
                <div className="text-xs text-slate-400">
                  Cooldown: {s.cooldown_minutes}m
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Delivery Audit Logs */}
      <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm space-y-3">
        <h2 className="text-base font-bold text-slate-800">Recent Webhook Deliveries ({deliveries.length})</h2>
        {deliveries.length === 0 ? (
          <p className="text-xs text-slate-500">No deliveries recorded yet.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="border-b border-slate-200 text-slate-500 bg-slate-50 font-semibold">
                  <th className="py-2 px-3">Time</th>
                  <th className="py-2 px-3">Subscriber</th>
                  <th className="py-2 px-3">Triggered Reason</th>
                  <th className="py-2 px-3">Status</th>
                  <th className="py-2 px-3">Latency</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 font-mono">
                {deliveries.map((d) => (
                  <tr key={d.id}>
                    <td className="py-2 px-3 text-slate-500">{new Date(d.dispatched_at).toLocaleTimeString()}</td>
                    <td className="py-2 px-3 font-sans text-slate-800 font-medium">{d.subscriber_name}</td>
                    <td className="py-2 px-3 font-sans text-slate-600">{d.triggered_thresholds.join('; ')}</td>
                    <td className="py-2 px-3">
                      <span className={`px-2 py-0.5 rounded text-xs font-bold ${d.success ? 'bg-emerald-100 text-emerald-800' : 'bg-rose-100 text-rose-800'}`}>
                        {d.status_code || 'ERR'}
                      </span>
                    </td>
                    <td className="py-2 px-3 text-slate-500">{d.latency_ms} ms</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};
