import React, { useEffect, useState } from 'react';
import { useTranslation } from '../../i18n/LanguageContext';

export interface ModelMetadata {
  id: string;
  name: string;
  version: string;
  task: string;
  status: string;
  enabled_in_production: boolean;
  data_sources?: string[];
  dates?: string;
  split?: Record<string, any>;
  metrics?: Record<string, any>;
  baseline_metrics?: Record<string, any>;
  improvement?: Record<string, any>;
  confidence_interval?: Record<string, any>;
  reports_path?: string;
  card_path?: string;
}

export interface EvalSummary {
  timestamp: string;
  status: string;
  models_evaluated: number;
  models: Record<string, any>;
  audited_result_files?: number;
}

export interface ModelCardData {
  model_id: string;
  model_card: string;
  metrics: Record<string, any>;
  enabled_in_production: boolean;
}

export const MLLabPage: React.FC = () => {
  const { language } = useTranslation();
  const isHindi = language === 'hi';

  const [models, setModels] = useState<ModelMetadata[]>([]);
  const [evalSummary, setEvalSummary] = useState<EvalSummary | null>(null);
  const [selectedModelId, setSelectedModelId] = useState<string>('summary');
  const [activeSubTab, setActiveSubTab] = useState<'overview' | 'split' | 'metrics' | 'card' | 'try_it'>('overview');
  const [modelCard, setModelCard] = useState<ModelCardData | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [cardLoading, setCardLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  // Try-It inference state
  const [tryItPayload, setTryItPayload] = useState<Record<string, any>>({});
  const [tryItResult, setTryItResult] = useState<any>(null);
  const [tryItLoading, setTryItLoading] = useState<boolean>(false);
  const [tryItError, setTryItError] = useState<string | null>(null);

  // Load models and eval summary on mount
  useEffect(() => {
    const fetchData = async () => {
      setLoading(true);
      setError(null);
      try {
        const [modelsRes, summaryRes] = await Promise.all([
          fetch('/v1/ml/models'),
          fetch('/v1/ml/eval/summary'),
        ]);

        if (modelsRes.ok) {
          const modelsData = await modelsRes.json();
          setModels(modelsData);
        } else {
          setModels([]);
        }

        if (summaryRes.ok) {
          const summaryData = await summaryRes.json();
          setEvalSummary(summaryData);
        }
      } catch (err: any) {
        setError(err.message || 'Failed to connect to /v1/ml endpoints');
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, []);

  // Load model card when a specific model is selected
  useEffect(() => {
    if (selectedModelId === 'summary') {
      setModelCard(null);
      return;
    }

    const fetchCard = async () => {
      setCardLoading(true);
      try {
        const res = await fetch(`/v1/ml/models/${selectedModelId}/card`);
        if (res.ok) {
          const data = await res.json();
          setModelCard(data);
        } else {
          setModelCard(null);
        }
      } catch {
        setModelCard(null);
      } finally {
        setCardLoading(false);
      }
    };

    fetchCard();
    // Reset Try-it states
    setTryItResult(null);
    setTryItError(null);
    setDefaultTryItPayload(selectedModelId);
  }, [selectedModelId]);

  const setDefaultTryItPayload = (modelId: string) => {
    switch (modelId) {
      case 'intent':
        setTryItPayload({ text: 'Will it rain tomorrow in Pune?', language: 'en' });
        break;
      case 'bias_correction':
        setTryItPayload({ raw_temp: 32.5, lead_day: 1, lat: 18.52, lon: 73.85, elev: 560.0 });
        break;
      case 'extreme_event':
        setTryItPayload({ lat: 18.52, lon: 73.85, elev: 560.0, lead_day: 1, forecast_tmax: 43.5 });
        break;
      case 'climate':
        setTryItPayload({ place_id: 'pune', metric: 'rain', lat: 18.52, lon: 73.85 });
        break;
      case 'rag':
        setTryItPayload({ query: 'What precautions should I take during a severe heatwave?', language: 'en', top_k: 3 });
        break;
      default:
        setTryItPayload({});
    }
  };

  const handleRunInference = async () => {
    if (!selectedModelId || selectedModelId === 'summary') return;
    setTryItLoading(true);
    setTryItError(null);
    setTryItResult(null);

    try {
      const res = await fetch(`/v1/ml/predict/${selectedModelId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(tryItPayload),
      });

      const data = await res.json();
      if (!res.ok) {
        const msg = data.error?.message || data.detail || `HTTP ${res.status}`;
        setTryItError(msg);
      } else {
        setTryItResult(data);
      }
    } catch (err: any) {
      setTryItError(err.message || 'Inference request failed');
    } finally {
      setTryItLoading(false);
    }
  };

  const selectedModel = models.find((m) => m.id === selectedModelId);

  // Helper to format values truthfully (T2: missing = NOT MEASURED)
  const formatVal = (val: any) => {
    if (val === null || val === undefined || val === '') return 'NOT MEASURED';
    if (typeof val === 'number') {
      return Number.isInteger(val) ? val.toString() : val.toFixed(4);
    }
    return String(val);
  };

  return (
    <div className="max-w-column mx-auto px-4 py-6 space-y-6">
      {/* Header */}
      <div className="border-b border-slate-200 dark:border-slate-800 pb-4">
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-xl bg-blue-100 dark:bg-blue-950 text-blue-700 dark:text-blue-300">
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19.428 15.428a2 2 0 00-1.022-.547l-2.387-.477a6 6 0 00-3.86.517l-.318.158a6 6 0 01-3.86.517L6.05 15.21a2 2 0 00-1.806.547M8 4h8l-1 1v5.172a2 2 0 00.586 1.414l5 5c1.26 1.26.367 3.414-1.415 3.414H4.828c-1.782 0-2.674-2.154-1.414-3.414l5-5A2 2 0 009 10.172V5L8 4z" />
            </svg>
          </div>
          <div>
            <h1 className="text-xl md:text-2xl font-bold text-slate-900 dark:text-slate-100">
              {isHindi ? 'मौसमजीपीटी एमएल लैब' : 'WeatherGPT ML Lab'}
            </h1>
            <p className="text-xs md:text-sm text-slate-600 dark:text-slate-400">
              {isHindi
                ? 'सत्यापित न्यूरल व सांख्यिकीय मॉडल्स, मॉडल कार्ड्स, और लाइव इंटरएक्टिव परीक्षण'
                : 'Audited Neural & Statistical Models, Official Model Cards, Metrics, and Interactive Playground'}
            </p>
          </div>
        </div>
      </div>

      {/* Model Selector Navigation Tabs */}
      <div className="flex flex-wrap gap-2 border-b border-slate-200 dark:border-slate-800 pb-3" role="tablist">
        <button
          type="button"
          role="tab"
          aria-selected={selectedModelId === 'summary'}
          onClick={() => {
            setSelectedModelId('summary');
            setActiveSubTab('overview');
          }}
          className={`px-3.5 py-2 rounded-lg text-xs font-semibold transition min-h-[40px] ${
            selectedModelId === 'summary'
              ? 'bg-blue-600 text-white shadow-sm'
              : 'bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-700'
          }`}
        >
          📊 {isHindi ? 'समग्र मूल्यांकन' : 'Evaluation Summary'}
        </button>

        {models.map((m) => {
          const isSelected = selectedModelId === m.id;
          return (
            <button
              key={m.id}
              type="button"
              role="tab"
              aria-selected={isSelected}
              onClick={() => {
                setSelectedModelId(m.id);
                setActiveSubTab('overview');
              }}
              className={`px-3.5 py-2 rounded-lg text-xs font-semibold transition flex items-center gap-1.5 min-h-[40px] ${
                isSelected
                  ? 'bg-blue-600 text-white shadow-sm'
                  : 'bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-700'
              }`}
            >
              <span>{m.name}</span>
              <span
                className={`w-2 h-2 rounded-full ${
                  m.enabled_in_production ? 'bg-emerald-400' : 'bg-slate-400'
                }`}
                title={m.enabled_in_production ? 'Production Active' : 'Offline / Standalone'}
              />
            </button>
          );
        })}
      </div>

      {loading ? (
        <div className="p-8 text-center text-slate-500">
          <div className="animate-spin w-6 h-6 border-2 border-blue-600 border-t-transparent rounded-full mx-auto mb-2" />
          <span>{isHindi ? 'एमएल रजिस्ट्री लोड हो रही है...' : 'Loading ML registry from /v1/ml/models...'}</span>
        </div>
      ) : error ? (
        <div className="p-4 bg-red-50 dark:bg-red-950/50 border border-red-200 dark:border-red-900 rounded-xl text-red-800 dark:text-red-300 text-sm">
          {error}
        </div>
      ) : selectedModelId === 'summary' ? (
        /* ================= OVERALL EVALUATION SUMMARY TAB ================= */
        <div className="space-y-6">
          <div className="bg-white dark:bg-slate-900 p-5 rounded-xl border border-slate-200 dark:border-slate-800 shadow-sm space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-base font-bold text-slate-900 dark:text-slate-100">
                {isHindi ? 'ऑडिटेड मॉडल रजिस्ट्री स्थिति' : 'Audited Models Verification Register'}
              </h2>
              <span className="text-xs font-mono text-slate-500">
                {evalSummary?.timestamp ? new Date(evalSummary.timestamp).toLocaleString() : 'Live'}
              </span>
            </div>

            <p className="text-xs text-slate-600 dark:text-slate-400">
              {isHindi
                ? 'नियम T1-T8: कोई भी संख्या सिम्युलेटेड या हार्डकोडेड नहीं है। सभी आंकड़े सीधे ml/*/reports/metrics.json से पढ़े गए हैं।'
                : 'Truthfulness Rules (T1-T8): No number is simulated, hardcoded, or estimated. Every metric is loaded strictly from audited reports/metrics.json.'}
            </p>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs border border-slate-200 dark:border-slate-800 rounded-lg">
                <thead className="bg-slate-50 dark:bg-slate-800/60 font-semibold text-slate-700 dark:text-slate-300">
                  <tr>
                    <th className="p-2.5">Model ID</th>
                    <th className="p-2.5">Task</th>
                    <th className="p-2.5">Production Status</th>
                    <th className="p-2.5">Key Metric</th>
                    <th className="p-2.5">Baseline</th>
                    <th className="p-2.5">Confidence Interval (95%)</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-200 dark:divide-slate-800 font-mono">
                  {models.map((m) => {
                    const metricKeys = m.metrics ? Object.keys(m.metrics) : [];
                    const primaryKey = metricKeys[0] || 'N/A';
                    const primaryVal = m.metrics ? m.metrics[primaryKey] : null;
                    const baselineVal = m.baseline_metrics ? m.baseline_metrics[primaryKey] : null;
                    const ciVal = m.confidence_interval ? m.confidence_interval[primaryKey] : null;

                    return (
                      <tr key={m.id} className="hover:bg-slate-50 dark:hover:bg-slate-800/30">
                        <td className="p-2.5 font-bold text-blue-700 dark:text-blue-300 font-sans">{m.name} ({m.id})</td>
                        <td className="p-2.5 font-sans text-slate-600 dark:text-slate-400">{m.task}</td>
                        <td className="p-2.5 font-sans">
                          <span
                            className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                              m.enabled_in_production
                                ? 'bg-emerald-100 dark:bg-emerald-950 text-emerald-800 dark:text-emerald-300'
                                : 'bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400'
                            }`}
                          >
                            {m.enabled_in_production ? 'ENABLED' : 'OFFLINE'}
                          </span>
                        </td>
                        <td className="p-2.5 text-slate-900 dark:text-slate-100">
                          {primaryKey}: {formatVal(primaryVal)}
                        </td>
                        <td className="p-2.5 text-slate-500">
                          {baselineVal !== null && baselineVal !== undefined ? formatVal(baselineVal) : 'NOT MEASURED'}
                        </td>
                        <td className="p-2.5 text-slate-600 dark:text-slate-400">
                          {Array.isArray(ciVal) ? `[${formatVal(ciVal[0])}, ${formatVal(ciVal[1])}]` : 'NOT MEASURED'}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      ) : selectedModel ? (
        /* ================= INDIVIDUAL MODEL TAB ================= */
        <div className="space-y-4">
          {/* Subtabs for current model */}
          <div className="flex border-b border-slate-200 dark:border-slate-800 gap-1 pb-1">
            <button
              type="button"
              onClick={() => setActiveSubTab('overview')}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition ${
                activeSubTab === 'overview'
                  ? 'bg-slate-200 dark:bg-slate-700 text-blue-700 dark:text-blue-300'
                  : 'text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800'
              }`}
            >
              {isHindi ? 'समस्या व परिचय' : 'Problem & Overview'}
            </button>
            <button
              type="button"
              onClick={() => setActiveSubTab('split')}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition ${
                activeSubTab === 'split'
                  ? 'bg-slate-200 dark:bg-slate-700 text-blue-700 dark:text-blue-300'
                  : 'text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800'
              }`}
            >
              {isHindi ? 'डेटा स्रोत व विभाजन' : 'Data & Split'}
            </button>
            <button
              type="button"
              onClick={() => setActiveSubTab('metrics')}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition ${
                activeSubTab === 'metrics'
                  ? 'bg-slate-200 dark:bg-slate-700 text-blue-700 dark:text-blue-300'
                  : 'text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800'
              }`}
            >
              {isHindi ? 'मापे गए परिणाम' : 'Metrics & CIs'}
            </button>
            <button
              type="button"
              onClick={() => setActiveSubTab('card')}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition ${
                activeSubTab === 'card'
                  ? 'bg-slate-200 dark:bg-slate-700 text-blue-700 dark:text-blue-300'
                  : 'text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800'
              }`}
            >
              {isHindi ? 'मॉडल कार्ड' : 'Model Card'}
            </button>
            <button
              type="button"
              onClick={() => setActiveSubTab('try_it')}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition ${
                activeSubTab === 'try_it'
                  ? 'bg-blue-600 text-white'
                  : 'text-blue-700 dark:text-blue-400 hover:bg-blue-50 dark:hover:bg-blue-950/50'
              }`}
            >
              🚀 {isHindi ? 'लाइव चलाएं (Try it)' : 'Try It (Live Inference)'}
            </button>
          </div>

          {/* Model Production State Banner */}
          <div
            className={`p-3 rounded-xl border text-xs flex items-center justify-between ${
              selectedModel.enabled_in_production
                ? 'bg-emerald-50 dark:bg-emerald-950/40 border-emerald-200 dark:border-emerald-900 text-emerald-900 dark:text-emerald-300'
                : 'bg-amber-50 dark:bg-amber-950/40 border-amber-200 dark:border-amber-900 text-amber-900 dark:text-amber-300'
            }`}
          >
            <div className="flex items-center gap-2">
              <span className="font-bold uppercase tracking-wider text-[10px]">
                {selectedModel.enabled_in_production ? 'Production Status: Active' : 'Production Status: Offline'}
              </span>
              <span>•</span>
              <span>{selectedModel.name} ({selectedModel.version})</span>
            </div>
            <span className="font-mono text-[11px]">
              {selectedModel.enabled_in_production ? 'enabled_in_production=true' : 'enabled_in_production=false'}
            </span>
          </div>

          {/* Subtab 1: Problem & Overview */}
          {activeSubTab === 'overview' && (
            <div className="bg-white dark:bg-slate-900 p-5 rounded-xl border border-slate-200 dark:border-slate-800 shadow-sm space-y-4">
              <h3 className="text-base font-bold text-slate-900 dark:text-slate-100">
                {selectedModel.name}
              </h3>
              <p className="text-xs text-slate-700 dark:text-slate-300 leading-relaxed">
                Task: <span className="font-semibold">{selectedModel.task}</span>
              </p>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs pt-2">
                <div className="bg-slate-50 dark:bg-slate-800/40 p-3 rounded-lg border border-slate-200 dark:border-slate-800 space-y-1">
                  <span className="font-bold text-slate-500 uppercase text-[10px] block">Data Sources & Period</span>
                  <div className="font-medium text-slate-800 dark:text-slate-200">
                    {selectedModel.data_sources?.join(', ') || 'NOT MEASURED'}
                  </div>
                  <div className="text-slate-500 text-[11px]">Period: {selectedModel.dates || 'NOT MEASURED'}</div>
                </div>

                <div className="bg-slate-50 dark:bg-slate-800/40 p-3 rounded-lg border border-slate-200 dark:border-slate-800 space-y-1">
                  <span className="font-bold text-slate-500 uppercase text-[10px] block">Audited Reports Path</span>
                  <div className="font-mono text-[11px] text-blue-700 dark:text-blue-300">
                    {selectedModel.reports_path || 'ml/<model>/reports/metrics.json'}
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Subtab 2: Data Sources & Dataset Split */}
          {activeSubTab === 'split' && (
            <div className="bg-white dark:bg-slate-900 p-5 rounded-xl border border-slate-200 dark:border-slate-800 shadow-sm space-y-4">
              <h3 className="text-base font-bold text-slate-900 dark:text-slate-100">
                {isHindi ? 'डेटा स्रोत एवं विभाजन (Split)' : 'Data Sources & Dataset Split'}
              </h3>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-xs">
                <div className="p-3 bg-slate-50 dark:bg-slate-800/40 rounded-lg border border-slate-200 dark:border-slate-800">
                  <div className="font-bold uppercase text-[10px] text-slate-500">Train Set</div>
                  <div className="text-slate-800 dark:text-slate-200 mt-1 font-mono">
                    {selectedModel.split?.train ? JSON.stringify(selectedModel.split.train) : 'NOT MEASURED'}
                  </div>
                </div>
                <div className="p-3 bg-slate-50 dark:bg-slate-800/40 rounded-lg border border-slate-200 dark:border-slate-800">
                  <div className="font-bold uppercase text-[10px] text-slate-500">Validation Set</div>
                  <div className="text-slate-800 dark:text-slate-200 mt-1 font-mono">
                    {selectedModel.split?.val ? JSON.stringify(selectedModel.split.val) : 'NOT MEASURED'}
                  </div>
                </div>
                <div className="p-3 bg-slate-50 dark:bg-slate-800/40 rounded-lg border border-slate-200 dark:border-slate-800">
                  <div className="font-bold uppercase text-[10px] text-slate-500">Held-Out Test Set</div>
                  <div className="text-slate-800 dark:text-slate-200 mt-1 font-mono">
                    {selectedModel.split?.test ? JSON.stringify(selectedModel.split.test) : 'NOT MEASURED'}
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Subtab 3: Metrics Against Baselines with Confidence Intervals */}
          {activeSubTab === 'metrics' && (
            <div className="bg-white dark:bg-slate-900 p-5 rounded-xl border border-slate-200 dark:border-slate-800 shadow-sm space-y-4">
              <h3 className="text-base font-bold text-slate-900 dark:text-slate-100">
                {isHindi ? 'मापे गए परिणाम बनाम बेसलाइन' : 'Measured Performance vs Baseline (with 95% CIs)'}
              </h3>
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs border border-slate-200 dark:border-slate-800 rounded-lg">
                  <thead className="bg-slate-50 dark:bg-slate-800/60 font-semibold text-slate-700 dark:text-slate-300">
                    <tr>
                      <th className="p-2.5">Metric</th>
                      <th className="p-2.5">Model Value</th>
                      <th className="p-2.5">Baseline Value</th>
                      <th className="p-2.5">Improvement (Δ)</th>
                      <th className="p-2.5">Bootstrap 95% Confidence Interval</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-200 dark:divide-slate-800 font-mono">
                    {selectedModel.metrics &&
                      Object.entries(selectedModel.metrics).map(([key, val]) => {
                        const baseVal = selectedModel.baseline_metrics?.[key];
                        const impVal = selectedModel.improvement?.[key];
                        const ciVal = selectedModel.confidence_interval?.[key];

                        return (
                          <tr key={key}>
                            <td className="p-2.5 font-bold text-slate-900 dark:text-slate-100">{key}</td>
                            <td className="p-2.5 text-blue-700 dark:text-blue-300 font-bold">{formatVal(val)}</td>
                            <td className="p-2.5 text-slate-500">{baseVal !== undefined ? formatVal(baseVal) : 'NOT MEASURED'}</td>
                            <td className="p-2.5 text-emerald-700 dark:text-emerald-400">
                              {impVal !== undefined ? (typeof impVal === 'number' ? (impVal >= 0 ? `+${impVal.toFixed(4)}` : impVal.toFixed(4)) : String(impVal)) : 'NOT MEASURED'}
                            </td>
                            <td className="p-2.5 text-slate-600 dark:text-slate-400">
                              {Array.isArray(ciVal) ? `[${formatVal(ciVal[0])}, ${formatVal(ciVal[1])}]` : 'NOT MEASURED'}
                            </td>
                          </tr>
                        );
                      })}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Subtab 4: Model Card */}
          {activeSubTab === 'card' && (
            <div className="bg-white dark:bg-slate-900 p-5 rounded-xl border border-slate-200 dark:border-slate-800 shadow-sm space-y-4">
              <h3 className="text-base font-bold text-slate-900 dark:text-slate-100">
                {isHindi ? 'आधिकारिक मॉडल कार्ड (MODEL_CARD.md)' : 'Official Model Card (MODEL_CARD.md)'}
              </h3>
              {cardLoading ? (
                <div className="text-slate-500 py-4 text-center">Loading model card...</div>
              ) : modelCard?.model_card ? (
                <div className="bg-slate-50 dark:bg-slate-950 p-4 rounded-lg font-mono text-[11px] whitespace-pre-wrap border border-slate-200 dark:border-slate-800 text-slate-800 dark:text-slate-200 max-h-[500px] overflow-y-auto">
                  {modelCard.model_card}
                </div>
              ) : (
                <div className="text-slate-500 italic py-4">No model card found for {selectedModelId}.</div>
              )}
            </div>
          )}

          {/* Subtab 5: Interactive Try It Playground */}
          {activeSubTab === 'try_it' && (
            <div className="bg-white dark:bg-slate-900 p-5 rounded-xl border border-slate-200 dark:border-slate-800 shadow-sm space-y-4">
              <div className="flex items-center justify-between">
                <h3 className="text-base font-bold text-slate-900 dark:text-slate-100">
                  {isHindi ? 'लाइव मॉडल परीक्षण (Try It)' : 'Live Interactive Model Playground'}
                </h3>
                <span className="text-xs font-mono text-slate-500">POST /v1/ml/predict/{selectedModelId}</span>
              </div>

              {/* Input Form Fields tailored per model */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
                {Object.entries(tryItPayload).map(([key, val]) => (
                  <div key={key} className="space-y-1">
                    <label className="font-semibold text-slate-700 dark:text-slate-300 uppercase text-[10px]">
                      {key}
                    </label>
                    <input
                      type={typeof val === 'number' ? 'number' : 'text'}
                      value={val}
                      step="any"
                      onChange={(e) => {
                        const v = typeof val === 'number' ? parseFloat(e.target.value) || 0 : e.target.value;
                        setTryItPayload((prev) => ({ ...prev, [key]: v }));
                      }}
                      className="w-full px-3 py-2 border border-slate-300 dark:border-slate-700 rounded-lg bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100"
                    />
                  </div>
                ))}
              </div>

              <div className="pt-2">
                <button
                  type="button"
                  onClick={handleRunInference}
                  disabled={tryItLoading}
                  className="px-5 py-2.5 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-xs font-bold shadow-sm transition disabled:opacity-50 min-h-[44px]"
                >
                  {tryItLoading
                    ? (isHindi ? 'मॉडल चल रहा है...' : 'Running live inference...')
                    : (isHindi ? 'अनुमान लगाएं' : 'Execute Prediction')}
                </button>
              </div>

              {/* Try It Output View */}
              {tryItError && (
                <div className="p-3 bg-red-50 dark:bg-red-950/60 border border-red-200 dark:border-red-900 rounded-lg text-red-800 dark:text-red-300 text-xs">
                  <span className="font-bold">Error:</span> {tryItError}
                </div>
              )}

              {tryItResult && (
                <div className="p-4 bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 rounded-lg space-y-2">
                  <div className="flex justify-between items-center border-b border-slate-200 dark:border-slate-800 pb-2">
                    <span className="font-bold text-xs text-slate-800 dark:text-slate-200">
                      {isHindi ? 'लाइव परिणाम' : 'Live Inference Output'}
                    </span>
                    <span className="text-[10px] font-mono text-emerald-600 dark:text-emerald-400 font-bold">200 OK</span>
                  </div>
                  <pre className="font-mono text-[11px] text-slate-800 dark:text-slate-200 overflow-x-auto">
                    {JSON.stringify(tryItResult, null, 2)}
                  </pre>
                </div>
              )}
            </div>
          )}
        </div>
      ) : null}
    </div>
  );
};

export default MLLabPage;
