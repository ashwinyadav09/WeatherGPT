import React, { useState } from 'react';
import { AskPage } from './features/ask/AskPage';
import { AdminPage } from './features/admin/AdminPage';

export const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'ask' | 'alerts' | 'places' | 'more' | 'admin'>('ask');

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col font-sans">
      {/* Main Content Area */}
      <div className="flex-1">
        {activeTab === 'ask' && <AskPage />}
        {activeTab === 'alerts' && (
          <div className="max-w-column mx-auto px-4 py-8 text-center text-slate-500">
            <h2 className="text-xl font-bold text-slate-800 mb-2">Active Alerts</h2>
            <p>No official warnings or alerts in your areas right now.</p>
          </div>
        )}
        {activeTab === 'places' && (
          <div className="max-w-column mx-auto px-4 py-8 text-center text-slate-500">
            <h2 className="text-xl font-bold text-slate-800 mb-2">Saved Places</h2>
            <p className="text-sm">Manage Home, Farm, Work locations.</p>
          </div>
        )}
        {activeTab === 'admin' && <AdminPage />}
        {activeTab === 'more' && (
          <div className="max-w-column mx-auto px-4 py-8 text-slate-700">
            <h2 className="text-xl font-bold text-slate-900 mb-4">About WeatherGPT</h2>
            <p className="text-sm text-slate-600 mb-4 leading-relaxed">
              A grounded, multilingual, voice-first weather assistant for India. A non-commercial, public-interest pilot.
            </p>
            <div className="mb-4">
              <button
                type="button"
                onClick={() => setActiveTab('admin')}
                className="text-xs bg-slate-200 hover:bg-slate-300 text-slate-800 font-semibold px-3 py-1.5 rounded-lg transition-colors"
              >
                Open Admin Console
              </button>
            </div>
            <div className="border-t border-slate-200 pt-4 text-xs text-slate-500 space-y-2">
              <p>Sources: Open-Meteo (CC BY 4.0), IMD (official data), NDMA SACHET.</p>
              <p>© WeatherGPT Public Pilot. No ads, no commercial use.</p>
            </div>
          </div>
        )}
      </div>

      {/* Persistent Bottom Navigation Bar (docs/ui-spec.md) */}
      <nav
        className="fixed bottom-0 left-0 right-0 h-14 bg-white border-t border-slate-200 flex items-center justify-around z-20"
        aria-label="Main Navigation"
      >
        <button
          type="button"
          onClick={() => setActiveTab('ask')}
          className={`flex flex-col items-center justify-center w-full h-full text-xs font-semibold ${
            activeTab === 'ask' ? 'text-blue-600' : 'text-slate-500 hover:text-slate-800'
          }`}
        >
          <svg className="w-5 h-5 mb-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
          </svg>
          Ask
        </button>

        <button
          type="button"
          onClick={() => setActiveTab('alerts')}
          className={`flex flex-col items-center justify-center w-full h-full text-xs font-semibold ${
            activeTab === 'alerts' ? 'text-blue-600' : 'text-slate-500 hover:text-slate-800'
          }`}
        >
          <svg className="w-5 h-5 mb-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
          </svg>
          Alerts
        </button>

        <button
          type="button"
          onClick={() => setActiveTab('places')}
          className={`flex flex-col items-center justify-center w-full h-full text-xs font-semibold ${
            activeTab === 'places' ? 'text-blue-600' : 'text-slate-500 hover:text-slate-800'
          }`}
        >
          <svg className="w-5 h-5 mb-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
          </svg>
          Places
        </button>

        <button
          type="button"
          onClick={() => setActiveTab('more')}
          className={`flex flex-col items-center justify-center w-full h-full text-xs font-semibold ${
            activeTab === 'more' ? 'text-blue-600' : 'text-slate-500 hover:text-slate-800'
          }`}
        >
          <svg className="w-5 h-5 mb-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 6h16M4 12h16M4 18h16" />
          </svg>
          More
        </button>
      </nav>
    </div>
  );
};
export default App;
