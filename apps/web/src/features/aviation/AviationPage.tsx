import React, { useState, useEffect } from 'react';

interface WindCalc {
  runway: string;
  runway_heading: number;
  wind_direction: number;
  wind_speed_kt: number;
  wind_gust_kt: number | null;
  relative_angle: number;
  crosswind_kt: number;
  crosswind_component_side: string;
  headwind_kt: number;
  is_tailwind: boolean;
}

interface DecodedMetar {
  station: string;
  raw: string;
  observation_time_ist: string;
  flight_category: 'VFR' | 'MVFR' | 'IFR' | 'LIFR';
  wind_dir: number | null;
  wind_speed_kt: number;
  wind_gust_kt: number | null;
  visibility_meters: number;
  weather_conditions: string[];
  ceiling_ft: number | null;
  temperature_c: number;
  dewpoint_c: number;
  qnh_hpa: number;
  source: string;
  banner: string;
}

interface DecodedTaf {
  station: string;
  raw: string;
  summary: string;
  source: string;
}

interface OverviewData {
  station: string;
  name: string;
  metar: DecodedMetar;
  taf: DecodedTaf;
  wind_calculations: WindCalc[];
  primary_runway_recommendation: string | null;
  banner: string;
}

const SAMPLE_AERODROMES = [
  { icao: 'VIDP', name: 'Delhi / Indira Gandhi (VIDP)' },
  { icao: 'VABB', name: 'Mumbai / Chhatrapati Shivaji (VABB)' },
  { icao: 'VOBL', name: 'Bengaluru / Kempegowda (VOBL)' },
  { icao: 'VOMM', name: 'Chennai International (VOMM)' },
  { icao: 'VECC', name: 'Kolkata / Netaji Subhash Chandra Bose (VECC)' },
];

export const AviationPage: React.FC = () => {
  const [station, setStation] = useState('VIDP');
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState<OverviewData | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchAviationData(station);
  }, [station]);

  const fetchAviationData = async (icao: string) => {
    setLoading(true);
    setError(null);
    try {
      const resp = await fetch(`/v1/aviation/overview?station=${icao}`);
      if (!resp.ok) {
        throw new Error(`Aerodrome data unavailable (HTTP ${resp.status})`);
      }
      const json = await resp.json();
      setData(json);
    } catch (e: any) {
      setError(e.message || 'Failed to load aviation data');
    } finally {
      setLoading(false);
    }
  };

  const getFlightCategoryBadge = (cat: string) => {
    switch (cat) {
      case 'VFR':
        return <span className="px-2.5 py-1 text-xs font-bold rounded-full bg-emerald-100 text-emerald-800 border border-emerald-300">VFR</span>;
      case 'MVFR':
        return <span className="px-2.5 py-1 text-xs font-bold rounded-full bg-blue-100 text-blue-800 border border-blue-300">MVFR</span>;
      case 'IFR':
        return <span className="px-2.5 py-1 text-xs font-bold rounded-full bg-rose-100 text-rose-800 border border-rose-300">IFR</span>;
      case 'LIFR':
        return <span className="px-2.5 py-1 text-xs font-bold rounded-full bg-purple-100 text-purple-800 border border-purple-300">LIFR</span>;
      default:
        return <span className="px-2.5 py-1 text-xs font-bold rounded-full bg-slate-100 text-slate-800">{cat}</span>;
    }
  };

  return (
    <div className="max-w-4xl mx-auto px-4 py-6 space-y-6">
      {/* Header & Station Selector */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 flex items-center gap-2">
            <span>✈️</span> Aviation Weather (METAR & TAF)
          </h1>
          <p className="text-sm text-slate-500">Decoded aerodrome observations and crosswind calculation</p>
        </div>

        <div className="flex items-center gap-2">
          <label htmlFor="station-select" className="text-sm font-medium text-slate-700">Aerodrome:</label>
          <select
            id="station-select"
            value={station}
            onChange={(e) => setStation(e.target.value)}
            className="border border-slate-300 rounded-lg px-3 py-1.5 text-sm font-semibold bg-white text-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            {SAMPLE_AERODROMES.map((a) => (
              <option key={a.icao} value={a.icao}>{a.name}</option>
            ))}
          </select>
        </div>
      </div>

      {/* Mandatory Non-Briefing Safety Banner */}
      <div className="p-4 rounded-xl border border-amber-300 bg-amber-50 text-amber-900 text-xs md:text-sm leading-relaxed flex items-start gap-3 shadow-sm" role="alert">
        <span className="text-amber-600 text-lg flex-shrink-0">⚠️</span>
        <div>
          <p className="font-bold">INFORMATIONAL ONLY — NOT AN OFFICIAL PRE-FLIGHT BRIEFING</p>
          <p className="mt-0.5 text-amber-800">
            WeatherGPT aviation data is for general situational awareness only and DOES NOT constitute an official pre-flight briefing.
            Pilots in command must obtain an official weather briefing from India Meteorological Department (IMD) / DGCA / AAI approved channels before flight.
          </p>
        </div>
      </div>

      {loading && (
        <div className="p-12 text-center text-slate-500 font-medium animate-pulse">
          Fetching aerodrome METAR and TAF...
        </div>
      )}

      {error && (
        <div className="p-4 rounded-lg bg-rose-50 border border-rose-200 text-rose-800 text-sm">
          {error}
        </div>
      )}

      {!loading && data && (
        <div className="space-y-6">
          {/* Aerodrome Overview Card */}
          <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm space-y-4">
            <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-100 pb-3">
              <div>
                <h2 className="text-lg font-bold text-slate-900">{data.name}</h2>
                <span className="text-xs text-slate-400 font-mono">ICAO: {data.station}</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-xs text-slate-500">Flight Category:</span>
                {getFlightCategoryBadge(data.metar.flight_category)}
              </div>
            </div>

            {/* METAR: Raw alongside Decoded */}
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-bold text-slate-800 uppercase tracking-wide">Current METAR Observation</h3>
                <span className="text-xs text-slate-500">{data.metar.observation_time_ist}</span>
              </div>

              {/* Raw METAR Text Box */}
              <div className="p-3 bg-slate-900 text-emerald-400 rounded-lg font-mono text-xs md:text-sm overflow-x-auto select-all">
                {data.metar.raw}
              </div>

              {/* Decoded METAR Metrics Grid */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 pt-2">
                <div className="p-3 bg-slate-50 rounded-lg border border-slate-200">
                  <div className="text-xs text-slate-500 font-medium">Wind</div>
                  <div className="text-sm font-bold text-slate-900 mt-1">
                    {data.metar.wind_dir ? `${data.metar.wind_dir}°` : 'VRB'} @ {data.metar.wind_speed_kt} kt
                    {data.metar.wind_gust_kt ? ` (Gust ${data.metar.wind_gust_kt} kt)` : ''}
                  </div>
                </div>

                <div className="p-3 bg-slate-50 rounded-lg border border-slate-200">
                  <div className="text-xs text-slate-500 font-medium">Visibility</div>
                  <div className="text-sm font-bold text-slate-900 mt-1">
                    {data.metar.visibility_meters >= 9999 ? '10+ km' : `${data.metar.visibility_meters} m`}
                  </div>
                </div>

                <div className="p-3 bg-slate-50 rounded-lg border border-slate-200">
                  <div className="text-xs text-slate-500 font-medium">Ceiling / Clouds</div>
                  <div className="text-sm font-bold text-slate-900 mt-1">
                    {data.metar.ceiling_ft ? `${data.metar.ceiling_ft} ft AGL` : 'No Ceiling'}
                  </div>
                </div>

                <div className="p-3 bg-slate-50 rounded-lg border border-slate-200">
                  <div className="text-xs text-slate-500 font-medium">Temp / QNH</div>
                  <div className="text-sm font-bold text-slate-900 mt-1">
                    {data.metar.temperature_c}°C / {data.metar.qnh_hpa} hPa
                  </div>
                </div>
              </div>

              {data.metar.weather_conditions.length > 0 && (
                <div className="text-xs text-slate-600 bg-slate-50 p-2.5 rounded-lg border border-slate-200">
                  <span className="font-semibold text-slate-800">Significant Weather: </span>
                  {data.metar.weather_conditions.join(', ')}
                </div>
              )}
            </div>
          </div>

          {/* Runway Wind & Crosswind Analysis */}
          <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm space-y-4">
            <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-100 pb-3">
              <div>
                <h3 className="text-base font-bold text-slate-900">Runway Wind & Crosswind Components</h3>
                <p className="text-xs text-slate-500">Calculated relative wind for all active runways</p>
              </div>
              {data.primary_runway_recommendation && (
                <div className="text-xs px-3 py-1 bg-blue-50 text-blue-700 font-semibold rounded-full border border-blue-200">
                  Favorable: {data.primary_runway_recommendation}
                </div>
              )}
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead>
                  <tr className="border-b border-slate-200 text-xs font-semibold text-slate-500 bg-slate-50">
                    <th className="py-2.5 px-3">Runway</th>
                    <th className="py-2.5 px-3">Heading</th>
                    <th className="py-2.5 px-3">Crosswind</th>
                    <th className="py-2.5 px-3">Headwind / Tailwind</th>
                    <th className="py-2.5 px-3">Relative Angle</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {data.wind_calculations.map((w, idx) => (
                    <tr key={idx} className={w.runway === data.primary_runway_recommendation ? 'bg-blue-50/50' : ''}>
                      <td className="py-2.5 px-3 font-bold text-slate-900">{w.runway}</td>
                      <td className="py-2.5 px-3 text-slate-600">{w.runway_heading}°</td>
                      <td className="py-2.5 px-3">
                        <span className={`font-semibold ${w.crosswind_kt >= 15 ? 'text-rose-600' : 'text-slate-800'}`}>
                          {w.crosswind_kt} kt
                        </span>
                        <span className="text-xs text-slate-400 ml-1">
                          {w.crosswind_component_side === 'right' ? 'from right' : w.crosswind_component_side === 'left' ? 'from left' : ''}
                        </span>
                      </td>
                      <td className="py-2.5 px-3">
                        {w.is_tailwind ? (
                          <span className="text-amber-700 font-medium text-xs bg-amber-100 px-2 py-0.5 rounded">
                            Tailwind: {Math.abs(w.headwind_kt)} kt
                          </span>
                        ) : (
                          <span className="text-emerald-700 font-medium">
                            Headwind: {w.headwind_kt} kt
                          </span>
                        )}
                      </td>
                      <td className="py-2.5 px-3 text-xs text-slate-500">
                        {Math.abs(w.relative_angle)}° off runway
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* TAF Card */}
          <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm space-y-3">
            <h3 className="text-sm font-bold text-slate-800 uppercase tracking-wide">Terminal Aerodrome Forecast (TAF)</h3>
            
            <div className="p-3 bg-slate-900 text-emerald-400 rounded-lg font-mono text-xs md:text-sm overflow-x-auto select-all">
              {data.taf.raw}
            </div>

            <div className="text-xs text-slate-600 bg-slate-50 p-3 rounded-lg border border-slate-200">
              <span className="font-semibold text-slate-800">Decoded Forecast Summary: </span>
              {data.taf.summary}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
