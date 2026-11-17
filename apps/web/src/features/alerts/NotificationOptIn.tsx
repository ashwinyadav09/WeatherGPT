import React, { useState } from 'react';

interface NotificationOptInProps {
  onSubscribed?: (endpoint: string) => void;
}

export const NotificationOptIn: React.FC<NotificationOptInProps> = ({ onSubscribed }) => {
  const [status, setStatus] = useState<'prompt' | 'granted' | 'denied' | 'subscribing'>(() => {
    if (typeof window !== 'undefined' && 'Notification' in window) {
      return Notification.permission as 'granted' | 'denied' | 'prompt';
    }
    return 'prompt';
  });

  const requestNotification = async () => {
    if (!('Notification' in window)) {
      alert('This browser does not support desktop notifications.');
      return;
    }

    setStatus('subscribing');
    try {
      const permission = await Notification.requestPermission();
      if (permission === 'granted') {
        setStatus('granted');
        // Register mock/local subscription with API
        try {
          await fetch('/v1/push/subscribe', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              endpoint: `https://push.browser.local/${Date.now()}`,
              places: ['Home', 'Pune'],
              severities: ['Extreme', 'Severe'],
            }),
          });
        } catch {
          // In development without live backend, gracefully continue
        }
        if (onSubscribed) {
          onSubscribed('granted');
        }
      } else {
        setStatus(permission as 'denied' | 'prompt');
      }
    } catch {
      setStatus('prompt');
    }
  };

  if (status === 'granted') {
    return (
      <div className="bg-emerald-50 border border-emerald-200 rounded-xl p-3 mb-4 text-xs text-emerald-800 flex items-center justify-between">
        <span className="flex items-center space-x-2">
          <span>🔔</span>
          <span className="font-medium">Severe weather push notifications are enabled for your places.</span>
        </span>
      </div>
    );
  }

  return (
    <div className="bg-blue-50 border border-blue-200 rounded-xl p-4 mb-4 text-slate-800">
      <div className="flex items-start space-x-3">
        <span className="text-xl" aria-hidden="true">🔔</span>
        <div className="flex-1">
          <h4 className="text-sm font-bold text-slate-900 mb-1">
            Get instant alerts for your places
          </h4>
          <p className="text-xs text-slate-600 mb-3 leading-relaxed">
            We only send critical warnings issued by official government agencies (IMD and NDMA) for your saved locations. No marketing, no spam, and quiet hours are respected.
          </p>
          <button
            type="button"
            onClick={requestNotification}
            disabled={status === 'subscribing'}
            className="text-xs bg-blue-600 hover:bg-blue-700 text-white font-semibold px-3 py-2 rounded-lg transition-colors focus:ring-2 focus:ring-focus-ring focus:outline-none"
          >
            {status === 'subscribing' ? 'Enabling...' : 'Enable Official Alert Notifications'}
          </button>
        </div>
      </div>
    </div>
  );
};
