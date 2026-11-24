import React, { useState } from 'react';
import { EvidencePacket } from './AnswerCard';

export interface TraceModel {
  id: string;
  version: string;
  used: boolean;
}

export interface TraceTool {
  name: string;
  args?: Record<string, any> | string;
  latency_ms: number;
  source?: string;
  provenance?: string;
}

export interface TraceVerifier {
  passed: boolean;
  checked_numbers: Array<number | string>;
  failures: string[];
  fallback_used?: boolean;
}

export interface TraceLLM {
  provider: string;
  model: string;
  tokens_in: number;
  tokens_out: number;
}

export interface TraceEventData {
  intent: string;
  confidence: number | null;
  router_path: string;
  tools: TraceTool[];
  models: TraceModel[];
  verifier: TraceVerifier;
  llm: TraceLLM;
}

interface TracePanelProps {
  trace?: TraceEventData;
  evidencePackets?: EvidencePacket[];
  language?: string;
}

export const TracePanel: React.FC<TracePanelProps> = ({
  trace,
  evidencePackets = [],
  language = 'en',
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const [activeTab, setActiveTab] = useState<'overview' | 'models' | 'evidence'>('overview');

  const isHindi = language === 'hi';

  if (!trace && evidencePackets.length === 0) {
    return null;
  }

  // Format router path for humans
  const formatRouterPath = (path: string) => {
    switch (path) {
      case 'intent_model_auto':
        return isHindi ? 'इंटेंट मॉडल (स्वतः रूटेड)' : 'Intent Model (Auto-routed)';
      case 'intent_model':
        return isHindi ? 'इंटेंट मॉडल (थ्रेशोल्ड नीचे, कीवर्ड आधारित)' : 'Intent Model (Below threshold, keyword fallback)';
      case 'deterministic':
        return isHindi ? 'नियम-आधारित (डिटर्मिनिस्टिक)' : 'Rule-based (Deterministic)';
      case 'safety_guard':
        return isHindi ? 'सुरक्षा प्री-गार्ड' : 'Safety Pre-Guard (Emergency Policy)';
      case 'policy_check':
        return isHindi ? 'नीति निर्देश' : 'Public Policy Check';
      case 'location_resolver':
        return isHindi ? 'स्थान समाधान' : 'Location Resolver Prompt';
      default:
        return path;
    }
  };

  // Check if bias correction evidence is present
  const biasCorrectionPacket = evidencePackets.find((p) => p.id.includes('corrected'));
  const rawForecastPacket = evidencePackets.find((p) => p.id.includes('open_meteo') && !p.id.includes('corrected'));

  // Extract raw and corrected values if available
  const rawTemp = rawForecastPacket?.values.find((v) => v.variable === 'tmax' || v.variable === 'temperature')?.value;
  const correctedTemp = biasCorrectionPacket?.values.find((v) => v.variable === 'corrected_tmax' || v.variable === 'temperature')?.value;
  const p10Temp = biasCorrectionPacket?.values.find((v) => v.variable === 'p10')?.value;
  const p90Temp = biasCorrectionPacket?.values.find((v) => v.variable === 'p90')?.value;

  // Check if risk outlook evidence is present
  const riskPacket = evidencePackets.find((p) => p.source.includes('risk') || p.id.includes('risk'));
  const riskLevel = riskPacket?.values.find((v) => v.variable === 'risk_level')?.value;
  const topDrivers = riskPacket?.values.find((v) => v.variable === 'top_drivers')?.value;

  // Check if RAG knowledge retrieval is present
  const retrievedPassages = evidencePackets.filter((p) => p.provenance === 'documented-sample' || p.source.includes('NDMA') || p.source.includes('ICAR'));

  return (
    <div className="mt-4 border border-slate-200 dark:border-slate-800 rounded-xl overflow-hidden bg-white dark:bg-slate-900 shadow-sm">
      {/* Collapsible toggle header */}
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        aria-expanded={isOpen}
        aria-controls="trace-panel-content"
        className="w-full flex items-center justify-between px-4 py-3 bg-slate-50 dark:bg-slate-800/60 hover:bg-slate-100 dark:hover:bg-slate-800 text-left transition"
      >
        <div className="flex items-center gap-2 flex-wrap">
          <span className="font-semibold text-xs tracking-wider uppercase text-blue-700 dark:text-blue-300 flex items-center gap-1.5">
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
            </svg>
            {isHindi ? 'यह जवाब कैसे बना (ट्रेस व सत्यापन)' : 'How this answer was made (Trace & Verification)'}
          </span>

          {trace?.intent && (
            <span className="px-2 py-0.5 rounded text-[11px] font-medium bg-blue-100 dark:bg-blue-950 text-blue-800 dark:text-blue-300">
              {trace.intent}
            </span>
          )}

          {trace?.confidence !== null && trace?.confidence !== undefined ? (
            <span className="px-2 py-0.5 rounded text-[11px] font-medium bg-emerald-100 dark:bg-emerald-950 text-emerald-800 dark:text-emerald-300">
              {(trace.confidence * 100).toFixed(1)}% conf
            </span>
          ) : (
            <span className="px-2 py-0.5 rounded text-[11px] font-medium bg-slate-200 dark:bg-slate-700 text-slate-700 dark:text-slate-300">
              {isHindi ? 'नियम-आधारित' : 'Deterministic'}
            </span>
          )}

          {trace?.verifier?.passed && (
            <span className="px-2 py-0.5 rounded text-[11px] font-medium bg-green-100 dark:bg-green-950 text-green-800 dark:text-green-300 flex items-center gap-1">
              ✓ {isHindi ? 'सत्यापित' : 'Grounded'}
            </span>
          )}
        </div>

        <svg
          className={`w-5 h-5 text-slate-500 transform transition-transform ${isOpen ? 'rotate-180' : ''}`}
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {/* Expanded panel body */}
      {isOpen && (
        <div id="trace-panel-content" className="p-4 text-xs space-y-4 border-t border-slate-200 dark:border-slate-800">
          {/* Subtabs: Overview, Models & Figures, Evidence Packets */}
          <div className="flex border-b border-slate-200 dark:border-slate-800 gap-2 pb-2">
            <button
              type="button"
              onClick={() => setActiveTab('overview')}
              className={`px-3 py-1.5 rounded-lg font-medium transition ${
                activeTab === 'overview'
                  ? 'bg-blue-600 text-white'
                  : 'text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800'
              }`}
            >
              {isHindi ? 'सारांश व सत्यापन' : 'Overview & Verification'}
            </button>
            <button
              type="button"
              onClick={() => setActiveTab('models')}
              className={`px-3 py-1.5 rounded-lg font-medium transition ${
                activeTab === 'models'
                  ? 'bg-blue-600 text-white'
                  : 'text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800'
              }`}
            >
              {isHindi ? 'एआई व एमएल मॉडल' : 'AI & ML Models'}
            </button>
            <button
              type="button"
              onClick={() => setActiveTab('evidence')}
              className={`px-3 py-1.5 rounded-lg font-medium transition ${
                activeTab === 'evidence'
                  ? 'bg-blue-600 text-white'
                  : 'text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800'
              }`}
            >
              {isHindi ? 'कच्चे साक्ष्य पैकेट' : 'Evidence Packets'} ({evidencePackets.length})
            </button>
          </div>

          {activeTab === 'overview' && (
            <div className="space-y-3">
              {/* Routing & Intent */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3 bg-slate-50 dark:bg-slate-800/40 p-3 rounded-lg border border-slate-200 dark:border-slate-800">
                <div>
                  <span className="font-semibold text-slate-500 uppercase text-[10px] block">
                    {isHindi ? 'रूटिंग पथ' : 'Routing Path'}
                  </span>
                  <span className="font-medium text-slate-800 dark:text-slate-200">
                    {trace ? formatRouterPath(trace.router_path) : 'Deterministic'}
                  </span>
                </div>
                <div>
                  <span className="font-semibold text-slate-500 uppercase text-[10px] block">
                    {isHindi ? 'इंटेंट व विश्वास स्तर' : 'Intent & Confidence'}
                  </span>
                  <span className="font-medium text-slate-800 dark:text-slate-200">
                    {trace?.intent || 'forecast'}
                    {trace?.confidence !== null && trace?.confidence !== undefined
                      ? ` (${(trace.confidence * 100).toFixed(1)}%)`
                      : ' (Null / No model probability)'}
                  </span>
                </div>
              </div>

              {/* Bias Correction: Raw vs Corrected with p10-p90 band */}
              {(rawTemp !== undefined || correctedTemp !== undefined) && (
                <div className="p-3 bg-blue-50 dark:bg-blue-950/40 rounded-lg border border-blue-200 dark:border-blue-900 space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-blue-900 dark:text-blue-300">
                      {isHindi ? 'तापमान बायस सुधार (NWP_BiasCorrection_v1)' : 'Temperature Bias Correction (NWP_BiasCorrection_v1)'}
                    </span>
                    <span className="text-[10px] bg-blue-200 dark:bg-blue-900 text-blue-900 dark:text-blue-200 px-2 py-0.5 rounded font-mono">
                      Ridge + LightGBM
                    </span>
                  </div>
                  <div className="grid grid-cols-3 gap-2 text-center pt-1">
                    <div className="bg-white dark:bg-slate-900 p-2 rounded border border-blue-100 dark:border-blue-950">
                      <div className="text-[10px] text-slate-500 uppercase">{isHindi ? 'कच्चा NWP' : 'Raw NWP'}</div>
                      <div className="font-bold text-slate-700 dark:text-slate-300 text-sm">
                        {rawTemp !== undefined ? `${rawTemp} °C` : 'N/A'}
                      </div>
                    </div>
                    <div className="bg-white dark:bg-slate-900 p-2 rounded border border-blue-200 dark:border-blue-800 ring-1 ring-blue-400">
                      <div className="text-[10px] text-blue-700 dark:text-blue-300 uppercase font-semibold">
                        {isHindi ? 'सुधारा गया' : 'Corrected'}
                      </div>
                      <div className="font-bold text-blue-700 dark:text-blue-300 text-sm">
                        {correctedTemp !== undefined ? `${correctedTemp} °C` : rawTemp !== undefined ? `${rawTemp} °C` : 'N/A'}
                      </div>
                    </div>
                    <div className="bg-white dark:bg-slate-900 p-2 rounded border border-blue-100 dark:border-blue-950">
                      <div className="text-[10px] text-slate-500 uppercase">{isHindi ? 'अनिश्चितता बैंड' : 'p10 - p90 Band'}</div>
                      <div className="font-semibold text-slate-600 dark:text-slate-400 text-xs mt-0.5">
                        {p10Temp !== undefined && p90Temp !== undefined ? `[${p10Temp}, ${p90Temp}] °C` : 'NOT MEASURED'}
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {/* Extreme-Event Risk with SHAP drivers */}
              {riskPacket && (
                <div className="p-3 bg-amber-50 dark:bg-amber-950/40 rounded-lg border border-amber-200 dark:border-amber-900 space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-amber-900 dark:text-amber-300">
                      {isHindi ? 'चरम मौसम जोखिम (extreme_event_risk_v1)' : 'Extreme-Event Risk Classifier (v1.0)'}
                    </span>
                    <span className="text-[10px] bg-amber-200 dark:bg-amber-900 text-amber-900 dark:text-amber-200 px-2 py-0.5 rounded font-mono">
                      SHAP Explainable
                    </span>
                  </div>
                  <div className="text-slate-700 dark:text-slate-300">
                    <span className="font-medium">{isHindi ? 'जोखिम स्तर:' : 'Risk Level:'}</span>{' '}
                    <span className="font-bold text-amber-800 dark:text-amber-300">{String(riskLevel || 'Low')}</span>
                  </div>
                  {topDrivers && (
                    <div className="bg-white dark:bg-slate-900 p-2 rounded border border-amber-200 dark:border-amber-900/60">
                      <span className="text-[10px] uppercase text-slate-500 block font-semibold">
                        {isHindi ? 'शीर्ष SHAP कारक:' : 'Top SHAP Drivers:'}
                      </span>
                      <span className="font-mono text-slate-700 dark:text-slate-300 text-[11px]">{String(topDrivers)}</span>
                    </div>
                  )}
                </div>
              )}

              {/* RAG Knowledge Retrieval */}
              {retrievedPassages.length > 0 && (
                <div className="p-3 bg-purple-50 dark:bg-purple-950/40 rounded-lg border border-purple-200 dark:border-purple-900 space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-purple-900 dark:text-purple-300">
                      {isHindi ? 'आधिकारिक ज्ञान पुनर्प्राप्ति (RAG Advisory Engine)' : 'Official Knowledge Retrieval (RAG Advisory Engine)'}
                    </span>
                    <span className="text-[10px] bg-purple-200 dark:bg-purple-900 text-purple-900 dark:text-purple-200 px-2 py-0.5 rounded font-mono">
                      BM25 + Dense RRF
                    </span>
                  </div>
                  <div className="space-y-1.5">
                    {retrievedPassages.map((p, idx) => (
                      <div key={idx} className="bg-white dark:bg-slate-900 p-2 rounded border border-purple-100 dark:border-purple-950 flex items-center justify-between">
                        <span className="font-mono text-[11px] text-purple-800 dark:text-purple-300 font-semibold">{p.id}</span>
                        <span className="text-slate-500 text-[11px]">{p.source} ({p.attribution})</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Grounding Verifier Result */}
              <div className="p-3 bg-slate-50 dark:bg-slate-800/40 rounded-lg border border-slate-200 dark:border-slate-800 space-y-1.5">
                <div className="flex items-center justify-between">
                  <span className="font-semibold text-slate-700 dark:text-slate-300">
                    {isHindi ? 'ग्राउंडिंग सत्यापनकर्ता:' : 'Grounding Verifier:'}
                  </span>
                  <span
                    className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                      trace?.verifier?.passed
                        ? 'bg-green-100 dark:bg-green-950 text-green-800 dark:text-green-300'
                        : 'bg-amber-100 dark:bg-amber-950 text-amber-800 dark:text-amber-300'
                    }`}
                  >
                    {trace?.verifier?.passed ? (isHindi ? 'पास (सत्यापित)' : 'PASSED') : (isHindi ? 'असफल (टेम्पलेट फॉलबैक)' : 'FAILED')}
                  </span>
                </div>
                <div className="text-slate-600 dark:text-slate-400 text-[11px]">
                  <span>{isHindi ? 'जांचे गए साक्ष्य संख्याएं: ' : 'Numbers checked against evidence: '}</span>
                  <span className="font-mono font-medium text-slate-800 dark:text-slate-200">
                    {trace?.verifier?.checked_numbers?.length ? trace.verifier.checked_numbers.join(', ') : 'None'}
                  </span>
                </div>
                {trace?.verifier?.fallback_used && (
                  <div className="text-amber-700 dark:text-amber-400 text-[11px] bg-amber-50 dark:bg-amber-950/60 p-1.5 rounded">
                    ⚠️ {isHindi ? 'प्राथमिक उत्तर अस्वीकृत; टेम्पलेट फॉलबैक से उत्तर दिया गया।' : 'Primary output rejected by verifier; safe template fallback used.'}
                  </div>
                )}
              </div>

              {/* LLM & Tools Execution */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-[11px] text-slate-600 dark:text-slate-400">
                <div className="bg-slate-50 dark:bg-slate-800/40 p-2.5 rounded-lg border border-slate-200 dark:border-slate-800">
                  <span className="font-semibold text-slate-700 dark:text-slate-300 block mb-1">
                    {isHindi ? 'भाषा मॉडल (LLM):' : 'Language Model (LLM):'}
                  </span>
                  <div>Provider: <span className="font-medium text-slate-800 dark:text-slate-200">{trace?.llm?.provider || 'None'}</span></div>
                  <div>Model: <span className="font-medium text-slate-800 dark:text-slate-200">{trace?.llm?.model || 'None'}</span></div>
                  <div>Tokens: <span className="font-mono text-slate-800 dark:text-slate-200">{trace?.llm?.tokens_in || 0} in / {trace?.llm?.tokens_out || 0} out</span></div>
                </div>

                <div className="bg-slate-50 dark:bg-slate-800/40 p-2.5 rounded-lg border border-slate-200 dark:border-slate-800">
                  <span className="font-semibold text-slate-700 dark:text-slate-300 block mb-1">
                    {isHindi ? 'निष्पादित टूल्स:' : 'Executed Tools:'}
                  </span>
                  {trace?.tools && trace.tools.length > 0 ? (
                    <div className="space-y-1">
                      {trace.tools.map((t, idx) => (
                        <div key={idx} className="flex justify-between font-mono text-[10px]">
                          <span className="text-slate-800 dark:text-slate-200">{t.name}</span>
                          <span>{t.latency_ms}ms</span>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <span className="italic text-slate-400">No external tool calls</span>
                  )}
                </div>
              </div>
            </div>
          )}

          {activeTab === 'models' && (
            <div className="space-y-3">
              <h5 className="font-bold text-slate-800 dark:text-slate-200">
                {isHindi ? 'सक्रिय मशीन लर्निंग मॉडल्स' : 'Active Machine Learning Models in Trace'}
              </h5>
              {trace?.models && trace.models.length > 0 ? (
                <div className="divide-y divide-slate-200 dark:divide-slate-800 border border-slate-200 dark:border-slate-800 rounded-lg overflow-hidden">
                  {trace.models.map((m, idx) => (
                    <div key={idx} className="p-3 bg-white dark:bg-slate-900 flex items-center justify-between">
                      <div>
                        <div className="font-mono font-bold text-blue-700 dark:text-blue-300">{m.id}</div>
                        <div className="text-[11px] text-slate-500">Version: {m.version}</div>
                      </div>
                      <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-green-100 dark:bg-green-950 text-green-800 dark:text-green-300">
                        {m.used ? 'INVOKED' : 'NOT USED'}
                      </span>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="p-3 bg-slate-50 dark:bg-slate-800/40 rounded-lg text-slate-500 italic">
                  {isHindi
                    ? 'इस उत्तर के लिए कोई न्यूरल मॉडल सक्रिय नहीं था (केवल डिटर्मिनिस्टिक नियम व आधिकारिक फ़ीड्स)।'
                    : 'No machine learning models were invoked for this query (pure rule routing & official weather feeds).'}
                </div>
              )}
            </div>
          )}

          {activeTab === 'evidence' && (
            <div className="space-y-2">
              <h5 className="font-bold text-slate-800 dark:text-slate-200">
                {isHindi ? 'अंतर्निहित साक्ष्य पैकेट (Authority Ladder)' : 'Underlying Evidence Packets (Authority Ladder)'}
              </h5>
              {evidencePackets.length > 0 ? (
                evidencePackets.map((ep) => (
                  <div key={ep.id} className="bg-white dark:bg-slate-900 p-3 rounded-lg border border-slate-200 dark:border-slate-800 text-[11px] space-y-1">
                    <div className="flex justify-between items-center border-b border-slate-100 dark:border-slate-800 pb-1">
                      <span className="font-bold text-slate-800 dark:text-slate-200">{ep.source} (Tier {ep.authority_tier})</span>
                      <span className="font-mono text-slate-500 text-[10px]">{ep.provenance}</span>
                    </div>
                    <div className="text-slate-600 dark:text-slate-400">
                      Place: {ep.place.name} ({ep.place.lat.toFixed(2)}, {ep.place.lon.toFixed(2)})
                    </div>
                    <div className="text-slate-800 dark:text-slate-200 font-mono text-[10px]">
                      Values: {ep.values.map((v) => `${v.variable}: ${v.value} ${v.unit}`).join(', ')}
                    </div>
                    <div className="text-slate-400 text-[10px] flex justify-between">
                      <span>Attribution: {ep.attribution}</span>
                      <span>Issued: {ep.issued_at ? new Date(ep.issued_at).toLocaleTimeString() : 'N/A'}</span>
                    </div>
                  </div>
                ))
              ) : (
                <p className="text-slate-500 italic">No evidence packets attached.</p>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
};
