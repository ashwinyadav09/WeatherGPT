import React, { useState, useEffect } from 'react';

interface AuditEntry {
  id: number;
  who: string;
  what: string;
  target: string;
  language: string;
  when: string;
  version: number;
  reviewer?: string;
}

export const AdminPage: React.FC = () => {
  const [adminToken, setAdminToken] = useState<string>(() => sessionStorage.getItem('weathergpt_admin_token') || '');
  const [tokenInput, setTokenInput] = useState<string>('');
  const [isAuthenticated, setIsAuthenticated] = useState<boolean>(false);
  const [authError, setAuthError] = useState<string>('');

  const [activeSection, setActiveSection] = useState<'glossary' | 'templates' | 'audit'>('glossary');
  const [selectedLang, setSelectedLang] = useState<string>('hi');

  // Glossary State
  const [terms, setTerms] = useState<Record<string, string>>({});
  const [editorName, setEditorName] = useState<string>('ashwin');
  const [glossaryMsg, setGlossaryMsg] = useState<string>('');

  // Templates State
  const [hazard, setHazard] = useState<string>('rain');
  const [severity, setSeverity] = useState<string>('orange');
  const [templateText, setTemplateText] = useState<string>('');
  const [reviewerName, setReviewerName] = useState<string>('');
  const [templateMsg, setTemplateMsg] = useState<string>('');

  // Audit State
  const [auditEntries, setAuditEntries] = useState<AuditEntry[]>([]);
  const [rollbackMsg, setRollbackMsg] = useState<string>('');

  const fetchWithAuth = async (url: string, options: RequestInit = {}) => {
    const headers = {
      ...(options.headers || {}),
      'Content-Type': 'application/json',
      'X-Admin-Token': adminToken,
    };
    return fetch(url, { ...options, headers });
  };

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setAuthError('');
    try {
      const res = await fetch(`/v1/admin/glossary/hi`, {
        headers: { 'X-Admin-Token': tokenInput.trim() },
      });
      if (res.ok) {
        setAdminToken(tokenInput.trim());
        sessionStorage.setItem('weathergpt_admin_token', tokenInput.trim());
        setIsAuthenticated(true);
      } else {
        setAuthError('Invalid admin token. Access denied.');
      }
    } catch {
      setAuthError('Connection error validating admin token.');
    }
  };

  useEffect(() => {
    if (adminToken) {
      fetchWithAuth(`/v1/admin/glossary/${selectedLang}`)
        .then((res) => {
          if (res.ok) {
            setIsAuthenticated(true);
            return res.json();
          } else {
            setIsAuthenticated(false);
          }
        })
        .then((data) => {
          if (data && data.terms) {
            setTerms(data.terms);
          }
        })
        .catch(() => setIsAuthenticated(false));
    }
  }, [adminToken, selectedLang]);

  const loadAuditLog = async () => {
    try {
      const res = await fetchWithAuth('/v1/admin/audit');
      if (res.ok) {
        const data = await res.json();
        setAuditEntries(data.entries || []);
      }
    } catch {
      // ignore
    }
  };

  useEffect(() => {
    if (isAuthenticated && activeSection === 'audit') {
      loadAuditLog();
    }
  }, [isAuthenticated, activeSection]);

  const handleSaveGlossary = async (e: React.FormEvent) => {
    e.preventDefault();
    setGlossaryMsg('');
    try {
      const res = await fetchWithAuth(`/v1/admin/glossary/${selectedLang}`, {
        method: 'POST',
        body: JSON.stringify({
          editor: editorName.trim(),
          terms,
        }),
      });
      if (res.ok) {
        const data = await res.json();
        setGlossaryMsg(`Saved version ${data.version} successfully.`);
      } else {
        setGlossaryMsg('Failed to save glossary.');
      }
    } catch {
      setGlossaryMsg('Network error saving glossary.');
    }
  };

  const handleSaveTemplate = async (e: React.FormEvent) => {
    e.preventDefault();
    setTemplateMsg('');
    if (!reviewerName.trim()) {
      setTemplateMsg('Error: A template cannot go live without a recorded reviewer name (human sign-off).');
      return;
    }
    try {
      const res = await fetchWithAuth(`/v1/admin/templates/${selectedLang}`, {
        method: 'POST',
        body: JSON.stringify({
          editor: editorName.trim(),
          reviewer: reviewerName.trim(),
          hazard,
          severity,
          template_text: templateText.trim(),
        }),
      });
      if (res.ok) {
        const data = await res.json();
        setTemplateMsg(`Template version ${data.version} saved with reviewer ${data.reviewer}.`);
      } else {
        const err = await res.json();
        setTemplateMsg(`Error: ${err.detail || 'Failed to save template.'}`);
      }
    } catch {
      setTemplateMsg('Network error saving template.');
    }
  };

  const handleRollback = async (target: 'glossary' | 'template', version: number) => {
    setRollbackMsg('');
    try {
      const res = await fetchWithAuth('/v1/admin/rollback', {
        method: 'POST',
        body: JSON.stringify({
          editor: editorName.trim(),
          target,
          language: selectedLang,
          target_version: version,
        }),
      });
      if (res.ok) {
        setRollbackMsg(`Successfully rolled back ${target} to version ${version}.`);
        loadAuditLog();
      } else {
        setRollbackMsg(`Failed to rollback ${target}.`);
      }
    } catch {
      setRollbackMsg(`Network error during rollback.`);
    }
  };

  if (!isAuthenticated) {
    return (
      <main className="max-w-column mx-auto px-4 py-8">
        <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6 max-w-md mx-auto">
          <div className="flex items-center space-x-2 text-slate-800 mb-4">
            <svg className="w-6 h-6 text-indigo-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
            </svg>
            <h1 className="text-xl font-bold">Admin Console</h1>
          </div>
          <p className="text-sm text-slate-600 mb-4">
            Protected area for managing glossary terms, alert templates, and reviewing the audit trail.
          </p>
          <form onSubmit={handleLogin} className="space-y-4">
            <div>
              <label htmlFor="token-input" className="block text-xs font-semibold text-slate-700 uppercase mb-1">
                Admin Token
              </label>
              <input
                id="token-input"
                type="password"
                value={tokenInput}
                onChange={(e) => setTokenInput(e.target.value)}
                placeholder="Enter secret token..."
                className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500 focus:outline-none"
                required
              />
            </div>
            {authError && <div className="text-xs text-red-600 font-medium">{authError}</div>}
            <button
              type="submit"
              className="w-full py-2 bg-indigo-600 hover:bg-indigo-700 text-white font-medium rounded-lg text-sm transition-colors"
            >
              Unlock Admin Area
            </button>
          </form>
        </div>
      </main>
    );
  }

  return (
    <main className="max-w-column mx-auto px-4 py-6 pb-20">
      <header className="flex items-center justify-between border-b border-slate-200 pb-4 mb-6">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Admin Console</h1>
          <p className="text-xs text-slate-500">Vetted terminology, alert templates & audit trail</p>
        </div>
        <div className="flex items-center space-x-2">
          <label htmlFor="lang-select" className="text-xs text-slate-500 font-medium">Language:</label>
          <select
            id="lang-select"
            value={selectedLang}
            onChange={(e) => setSelectedLang(e.target.value)}
            className="text-xs border border-slate-300 rounded px-2 py-1 bg-white font-medium"
          >
            <option value="hi">Hindi (hi)</option>
            <option value="en">English (en)</option>
          </select>
          <button
            type="button"
            onClick={() => {
              sessionStorage.removeItem('weathergpt_admin_token');
              setIsAuthenticated(false);
              setAdminToken('');
            }}
            className="text-xs text-red-600 hover:underline ml-2"
          >
            Lock
          </button>
        </div>
      </header>

      {/* Navigation Tabs */}
      <div className="flex space-x-2 border-b border-slate-200 mb-6">
        <button
          type="button"
          onClick={() => setActiveSection('glossary')}
          className={`pb-2 px-3 text-sm font-semibold border-b-2 transition-colors ${
            activeSection === 'glossary'
              ? 'border-indigo-600 text-indigo-600'
              : 'border-transparent text-slate-500 hover:text-slate-800'
          }`}
        >
          Glossary
        </button>
        <button
          type="button"
          onClick={() => setActiveSection('templates')}
          className={`pb-2 px-3 text-sm font-semibold border-b-2 transition-colors ${
            activeSection === 'templates'
              ? 'border-indigo-600 text-indigo-600'
              : 'border-transparent text-slate-500 hover:text-slate-800'
          }`}
        >
          Alert Templates
        </button>
        <button
          type="button"
          onClick={() => setActiveSection('audit')}
          className={`pb-2 px-3 text-sm font-semibold border-b-2 transition-colors ${
            activeSection === 'audit'
              ? 'border-indigo-600 text-indigo-600'
              : 'border-transparent text-slate-500 hover:text-slate-800'
          }`}
        >
          Audit Log & Rollback
        </button>
      </div>

      {/* Editor Info Bar */}
      <div className="mb-4 bg-slate-100 rounded-lg p-2.5 flex items-center justify-between text-xs">
        <div className="flex items-center space-x-2">
          <span className="font-semibold text-slate-700">Editor:</span>
          <input
            type="text"
            value={editorName}
            onChange={(e) => setEditorName(e.target.value)}
            className="border border-slate-300 rounded px-2 py-0.5 bg-white text-xs w-28"
          />
        </div>
        <span className="text-slate-500">Changes take effect immediately without restart</span>
      </div>

      {/* Section 1: Glossary */}
      {activeSection === 'glossary' && (
        <form onSubmit={handleSaveGlossary} className="space-y-4">
          <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm">
            <h2 className="text-sm font-bold text-slate-800 mb-3">Terminology ({selectedLang})</h2>
            <div className="grid grid-cols-1 gap-2.5 max-h-96 overflow-y-auto pr-1">
              {Object.entries(terms).map(([k, val]) => (
                <div key={k} className="flex items-center space-x-2 text-xs">
                  <span className="w-32 font-mono text-slate-600 font-medium truncate">{k}:</span>
                  <input
                    type="text"
                    value={val}
                    onChange={(e) => setTerms({ ...terms, [k]: e.target.value })}
                    className="flex-1 border border-slate-300 rounded px-2 py-1 text-xs focus:ring-1 focus:ring-indigo-500"
                  />
                </div>
              ))}
            </div>
          </div>
          {glossaryMsg && <div className="text-xs text-emerald-700 font-semibold">{glossaryMsg}</div>}
          <button
            type="submit"
            className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg text-xs font-semibold transition-colors"
          >
            Save Glossary Changes
          </button>
        </form>
      )}

      {/* Section 2: Alert Templates */}
      {activeSection === 'templates' && (
        <form onSubmit={handleSaveTemplate} className="space-y-4 bg-white rounded-xl border border-slate-200 p-4 shadow-sm">
          <h2 className="text-sm font-bold text-slate-800 mb-2">Vetted Alert Template Editor</h2>
          <div className="grid grid-cols-2 gap-3 text-xs">
            <div>
              <label htmlFor="hazard-select" className="block font-semibold text-slate-700 mb-1">Hazard</label>
              <select
                id="hazard-select"
                value={hazard}
                onChange={(e) => setHazard(e.target.value)}
                className="w-full border border-slate-300 rounded p-1.5 bg-white text-xs"
              >
                <option value="rain">Rain / Heavy Rain</option>
                <option value="cyclone">Cyclone</option>
                <option value="flood">Flood</option>
                <option value="heat_wave">Heat Wave</option>
                <option value="thunderstorm">Thunderstorm</option>
              </select>
            </div>
            <div>
              <label htmlFor="severity-select" className="block font-semibold text-slate-700 mb-1">Severity</label>
              <select
                id="severity-select"
                value={severity}
                onChange={(e) => setSeverity(e.target.value)}
                className="w-full border border-slate-300 rounded p-1.5 bg-white text-xs"
              >
                <option value="green">Green (No Warning)</option>
                <option value="yellow">Yellow (Be Aware)</option>
                <option value="orange">Orange (Be Prepared)</option>
                <option value="red">Red (Take Action)</option>
              </select>
            </div>
          </div>

          <div>
            <label htmlFor="template-text-area" className="block font-semibold text-xs text-slate-700 mb-1">Template Text</label>
            <textarea
              id="template-text-area"
              rows={3}
              value={templateText}
              onChange={(e) => setTemplateText(e.target.value)}
              placeholder="e.g. {place} में {hazard} को लेकर {severity} चेतावनी जारी की गई है।"
              className="w-full border border-slate-300 rounded-lg p-2 text-xs focus:ring-1 focus:ring-indigo-500"
              required
            />
          </div>

          <div className="bg-amber-50 border border-amber-200 rounded-lg p-2.5">
            <label htmlFor="reviewer-name-input" className="block font-bold text-xs text-amber-900 mb-1">
              Required Human Reviewer Name *
            </label>
            <input
              id="reviewer-name-input"
              type="text"
              value={reviewerName}
              onChange={(e) => setReviewerName(e.target.value)}
              placeholder="e.g. Pradeep Chhaba (Native Speaker Sign-off)"
              className="w-full border border-amber-300 rounded px-2 py-1 text-xs bg-white focus:ring-1 focus:ring-amber-500"
              required
            />
            <p className="text-[10px] text-amber-800 mt-1">
              Per project rules, alert templates cannot go live without a recorded reviewer name.
            </p>
          </div>

          {templateMsg && (
            <div className={`text-xs font-semibold ${templateMsg.startsWith('Error') ? 'text-red-600' : 'text-emerald-700'}`}>
              {templateMsg}
            </div>
          )}

          <button
            type="submit"
            className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg text-xs font-semibold transition-colors"
          >
            Save Vetted Template
          </button>
        </form>
      )}

      {/* Section 3: Audit Log & Rollback */}
      {activeSection === 'audit' && (
        <div className="space-y-4">
          {rollbackMsg && <div className="text-xs text-blue-700 font-semibold bg-blue-50 p-2 rounded">{rollbackMsg}</div>}
          <div className="bg-white rounded-xl border border-slate-200 overflow-hidden shadow-sm">
            <table className="min-w-full text-xs">
              <thead className="bg-slate-100 text-slate-700 font-semibold border-b border-slate-200">
                <tr>
                  <th className="py-2 px-3 text-left">Ver</th>
                  <th className="py-2 px-3 text-left">Who</th>
                  <th className="py-2 px-3 text-left">Action</th>
                  <th className="py-2 px-3 text-left">When</th>
                  <th className="py-2 px-3 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {auditEntries.length === 0 ? (
                  <tr>
                    <td colSpan={5} className="py-4 text-center text-slate-400">
                      No audit entries recorded yet.
                    </td>
                  </tr>
                ) : (
                  auditEntries.map((entry) => (
                    <tr key={entry.id} className="hover:bg-slate-50">
                      <td className="py-2 px-3 font-mono font-bold text-indigo-600">v{entry.version}</td>
                      <td className="py-2 px-3 text-slate-800">{entry.who}</td>
                      <td className="py-2 px-3 text-slate-600">
                        {entry.what} ({entry.target})
                        {entry.reviewer && <span className="block text-[10px] text-amber-700">Reviewer: {entry.reviewer}</span>}
                      </td>
                      <td className="py-2 px-3 text-slate-400 text-[10px]">{new Date(entry.when).toLocaleString()}</td>
                      <td className="py-2 px-3 text-right">
                        <button
                          type="button"
                          onClick={() => handleRollback(entry.target as 'glossary' | 'template', entry.version)}
                          className="text-[11px] text-indigo-600 hover:text-indigo-800 font-semibold underline"
                        >
                          Rollback
                        </button>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </main>
  );
};
