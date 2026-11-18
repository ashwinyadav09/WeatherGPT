import React, { useState, useEffect } from 'react';
import { Card } from '../../components/Card';

interface AgrometResponse {
  status: string;
  district: string;
  crop: string;
  crop_display: string;
  stage: string;
  stage_display: string;
  advisory_text: string;
  recommended_actions: string[];
  source: string;
  issue_date: string;
  safety_note: string;
}

interface MarineResponse {
  status: string;
  area_name: string;
  weather: string;
  wind: string;
  sea_condition: string;
  port_warning: string;
  fishermen_warning: {
    status: string;
    level: string;
    warning_en: string;
    warning_hi?: string;
    squall_speed_kmph?: string | null;
  };
  safety_banner: {
    text_en: string;
    text_hi: string;
  };
  source: string;
}

export const AdvisoriesPage: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'agro' | 'marine'>('agro');

  // Agromet states
  const [district, setDistrict] = useState('Ludhiana');
  const [crop, setCrop] = useState('wheat');
  const [stage, setStage] = useState('sowing');
  const [agroData, setAgroData] = useState<AgrometResponse | null>(null);
  const [agroLoading, setAgroLoading] = useState(false);

  // Marine states
  const [coastalArea, setCoastalArea] = useState('konkan_goa');
  const [marineData, setMarineData] = useState<MarineResponse | null>(null);
  const [marineLoading, setMarineLoading] = useState(false);

  useEffect(() => {
    if (activeTab === 'agro') {
      fetchAgromet();
    } else {
      fetchMarine();
    }
  }, [activeTab, district, crop, stage, coastalArea]);

  const fetchAgromet = async () => {
    setAgroLoading(true);
    try {
      const res = await fetch(`/v1/advisory/agromet?district=${encodeURIComponent(district)}&crop=${crop}&stage=${stage}&language=en`);
      if (res.ok) {
        const data = await res.json();
        setAgroData(data);
      }
    } catch {
      // offline / fallback handling
    } finally {
      setAgroLoading(false);
    }
  };

  const fetchMarine = async () => {
    setMarineLoading(true);
    try {
      const res = await fetch(`/v1/advisory/marine?area=${encodeURIComponent(coastalArea)}&language=en`);
      if (res.ok) {
        const data = await res.json();
        setMarineData(data);
      }
    } catch {
      // offline / fallback handling
    } finally {
      setMarineLoading(false);
    }
  };

  return (
    <div className="space-y-6 max-w-xl mx-auto">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-slate-900 dark:text-white">
          Official Advisories & Bulletins
        </h1>
        <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
          IMD Gramin Krishi Mausam Sewa (Agromet) & Coastal Marine Bulletins
        </p>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-slate-200 dark:border-slate-800">
        <button
          onClick={() => setActiveTab('agro')}
          className={`py-2 px-4 font-medium text-sm border-b-2 transition-colors ${
            activeTab === 'agro'
              ? 'border-blue-600 text-blue-600 dark:text-blue-400'
              : 'border-transparent text-slate-500 hover:text-slate-700 dark:text-slate-400'
          }`}
        >
          Agromet Advisory (कृषि)
        </button>
        <button
          onClick={() => setActiveTab('marine')}
          className={`py-2 px-4 font-medium text-sm border-b-2 transition-colors ${
            activeTab === 'marine'
              ? 'border-blue-600 text-blue-600 dark:text-blue-400'
              : 'border-transparent text-slate-500 hover:text-slate-700 dark:text-slate-400'
          }`}
        >
          Coastal & Marine (तटीय)
        </button>
      </div>

      {/* Agromet Tab */}
      {activeTab === 'agro' && (
        <div className="space-y-4">
          <div className="grid grid-cols-3 gap-3">
            <div>
              <label className="block text-xs font-semibold text-slate-600 dark:text-slate-300 mb-1">
                District
              </label>
              <select
                value={district}
                onChange={(e) => setDistrict(e.target.value)}
                className="w-full text-sm rounded-lg border border-slate-300 dark:border-slate-700 p-2 bg-white dark:bg-slate-800"
              >
                <option value="Ludhiana">Ludhiana (Punjab)</option>
                <option value="Karnal">Karnal (Haryana)</option>
                <option value="Varanasi">Varanasi (UP)</option>
                <option value="Burdwan">Burdwan (WB)</option>
              </select>
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-600 dark:text-slate-300 mb-1">
                Crop
              </label>
              <select
                value={crop}
                onChange={(e) => setCrop(e.target.value)}
                className="w-full text-sm rounded-lg border border-slate-300 dark:border-slate-700 p-2 bg-white dark:bg-slate-800"
              >
                <option value="wheat">Wheat (गेहूं)</option>
                <option value="rice">Rice / Paddy (धान)</option>
              </select>
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-600 dark:text-slate-300 mb-1">
                Stage
              </label>
              <select
                value={stage}
                onChange={(e) => setStage(e.target.value)}
                className="w-full text-sm rounded-lg border border-slate-300 dark:border-slate-700 p-2 bg-white dark:bg-slate-800"
              >
                <option value="sowing">Sowing (बुवाई)</option>
                <option value="vegetative">Vegetative (कल्ले)</option>
                <option value="flowering">Flowering (फूल)</option>
                <option value="maturity">Maturity (कटाई)</option>
              </select>
            </div>
          </div>

          {/* Pesticide Warning Notice */}
          <div className="p-3 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-lg text-xs text-amber-800 dark:text-amber-200 flex items-start space-x-2">
            <span className="font-bold">Notice:</span>
            <span>
              WeatherGPT strictly refuses chemical pesticide doses. For approved prescriptions, consult your local Krishi Vigyan Kendra (KVK) or call Kisan Call Centre at 1800-180-1551.
            </span>
          </div>

          {agroLoading ? (
            <div className="p-6 text-center text-slate-500">Loading agromet advisory...</div>
          ) : agroData ? (
            <Card
              headline={`${agroData.crop_display} Advisory - ${agroData.stage_display}`}
              sourceLine={agroData.source}
              caveat={agroData.safety_note}
              style="guidance-card"
            >
              <div className="space-y-3 mt-2 text-sm text-slate-700 dark:text-slate-300">
                <p className="leading-relaxed">{agroData.advisory_text}</p>
                {agroData.recommended_actions?.length > 0 && (
                  <div>
                    <h4 className="font-semibold text-xs text-slate-900 dark:text-white uppercase tracking-wider mb-1">
                      Recommended Field Actions:
                    </h4>
                    <ul className="list-disc pl-5 space-y-1">
                      {agroData.recommended_actions.map((act, i) => (
                        <li key={i}>{act}</li>
                      ))}
                    </ul>
                  </div>
                )}
                <div className="text-xs text-slate-400 pt-2 border-t border-slate-100 dark:border-slate-800 flex justify-between">
                  <span>District: {agroData.district}</span>
                  <span>Issued: {agroData.issue_date}</span>
                </div>
              </div>
            </Card>
          ) : null}
        </div>
      )}

      {/* Marine Tab */}
      {activeTab === 'marine' && (
        <div className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-slate-600 dark:text-slate-300 mb-1">
              Coastal Sector
            </label>
            <select
              value={coastalArea}
              onChange={(e) => setCoastalArea(e.target.value)}
              className="w-full text-sm rounded-lg border border-slate-300 dark:border-slate-700 p-2 bg-white dark:bg-slate-800"
            >
              <option value="konkan_goa">Konkan-Goa Coast (Maharashtra / Goa)</option>
              <option value="north_gujarat">North Gujarat Coast</option>
              <option value="south_gujarat">South Gujarat Coast</option>
              <option value="tamil_nadu">Tamil Nadu & Puducherry Coast</option>
              <option value="west_bengal">West Bengal Coast</option>
              <option value="kerala">Kerala & Lakshadweep Coast</option>
            </select>
          </div>

          {marineLoading ? (
            <div className="p-6 text-center text-slate-500">Loading marine bulletin...</div>
          ) : marineData ? (
            <div className="space-y-4">
              {/* Mandatory Safety Notice Banner */}
              <div className="p-4 bg-blue-50 dark:bg-blue-900/20 border-l-4 border-blue-600 rounded-r-lg text-xs text-blue-900 dark:text-blue-200">
                <p className="font-bold mb-1">SAFETY NOTICE</p>
                <p>{marineData.safety_banner?.text_en}</p>
              </div>

              {/* Bulletin Card */}
              <Card
                headline={`Coastal Bulletin: ${marineData.area_name}`}
                sourceLine={marineData.source}
                caveat="Official Marine Weather Bulletin | INCOIS Collaborative Product"
                style="guidance-card"
              >
                <div className="space-y-3 mt-2 text-sm text-slate-700 dark:text-slate-300">
                  <div className="grid grid-cols-2 gap-3 text-xs">
                    <div className="p-2 bg-slate-50 dark:bg-slate-800 rounded">
                      <span className="text-slate-400 block">Sea Condition</span>
                      <span className="font-bold text-slate-800 dark:text-slate-100">{marineData.sea_condition}</span>
                    </div>
                    <div className="p-2 bg-slate-50 dark:bg-slate-800 rounded">
                      <span className="text-slate-400 block">Wind</span>
                      <span className="font-bold text-slate-800 dark:text-slate-100">{marineData.wind}</span>
                    </div>
                  </div>

                  <div>
                    <span className="text-xs text-slate-400 block">Weather</span>
                    <p className="text-sm">{marineData.weather}</p>
                  </div>

                  {marineData.port_warning && (
                    <div>
                      <span className="text-xs text-slate-400 block">Port Signals</span>
                      <p className="text-xs font-semibold text-amber-700 dark:text-amber-400">{marineData.port_warning}</p>
                    </div>
                  )}

                  {/* Fishermen Warning Box */}
                  <div className={`p-3 rounded-lg border ${
                    marineData.fishermen_warning?.level === 'red'
                      ? 'bg-red-50 dark:bg-red-900/20 border-red-300 text-red-900 dark:text-red-200'
                      : marineData.fishermen_warning?.level === 'orange'
                      ? 'bg-orange-50 dark:bg-orange-900/20 border-orange-300 text-orange-900 dark:text-orange-200'
                      : 'bg-green-50 dark:bg-green-900/20 border-green-300 text-green-900 dark:text-green-200'
                  }`}>
                    <span className="font-bold block text-xs uppercase mb-1">
                      Fishermen Warning ({marineData.fishermen_warning?.level || 'Active'})
                    </span>
                    <p className="text-xs">{marineData.fishermen_warning?.warning_en}</p>
                  </div>
                </div>
              </Card>
            </div>
          ) : null}
        </div>
      )}
    </div>
  );
};

export default AdvisoriesPage;
