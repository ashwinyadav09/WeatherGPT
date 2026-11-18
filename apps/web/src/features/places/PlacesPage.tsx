import React, { useState, useEffect } from 'react';
import { useTranslation } from '../../i18n/LanguageContext';
import { Card } from '../../components/Card';
import { Chip } from '../../components/Chip';
import { Button } from '../../components/Button';
import { PlaceModel, MOCK_PLACES } from '../../mocks/mockData';

const STORAGE_KEY = 'weathergpt_saved_places';
const ACTIVE_PLACE_KEY = 'weathergpt_active_place_id';

const DEFAULT_PRESET_PLACES: PlaceModel[] = [
  {
    id: 'saved_home',
    kind: 'point',
    names: { en: 'Home (Pune)', hi: 'घर (पुणे)' },
    lat: 18.5204,
    lon: 73.8567,
    elevation: 560.0,
    state: 'Maharashtra',
    district: 'Pune',
  },
  {
    id: 'saved_farm',
    kind: 'point',
    names: { en: 'Farm (Baramati)', hi: 'खेत (बारामती)' },
    lat: 18.1517,
    lon: 74.5774,
    elevation: 538.0,
    state: 'Maharashtra',
    district: 'Pune',
  },
  {
    id: 'saved_work',
    kind: 'point',
    names: { en: 'Work (Mumbai)', hi: 'दफ्तर (मुंबई)' },
    lat: 19.0760,
    lon: 72.8777,
    elevation: 14.0,
    state: 'Maharashtra',
    district: 'Mumbai City',
  },
];

export const PlacesPage: React.FC = () => {
  const { t, language } = useTranslation();
  const [savedPlaces, setSavedPlaces] = useState<PlaceModel[]>(() => {
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      if (stored) {
        return JSON.parse(stored);
      }
    } catch {
      // Fallback
    }
    return DEFAULT_PRESET_PLACES;
  });

  const [activePlaceId, setActivePlaceId] = useState<string>(() => {
    return localStorage.getItem(ACTIVE_PLACE_KEY) || 'saved_home';
  });

  const [search, setSearch] = useState('');
  const [allPlaces, setAllPlaces] = useState<PlaceModel[]>(MOCK_PLACES);
  const [geoLoading, setGeoLoading] = useState(false);
  const [geoError, setGeoError] = useState<string | null>(null);

  // Persist saved places on change
  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(savedPlaces));
    } catch (err) {
      console.warn('Failed to save places to localStorage:', err);
    }
  }, [savedPlaces]);

  // Persist active place selection
  const selectActivePlace = (id: string) => {
    setActivePlaceId(id);
    localStorage.setItem(ACTIVE_PLACE_KEY, id);
  };

  // Search API / local list
  useEffect(() => {
    if (search.trim().length > 1) {
      fetch(`/v1/places/search?q=${encodeURIComponent(search)}&lang=${language}`)
        .then((res) => res.json())
        .then((data) => {
          if (Array.isArray(data) && data.length > 0) {
            setAllPlaces(data);
          }
        })
        .catch(() => {
          // local fallback
        });
    }
  }, [search, language]);

  // Handle GPS "Use My Location"
  const handleUseLocation = () => {
    if (!('geolocation' in navigator)) {
      setGeoError('Geolocation is not supported by your browser.');
      return;
    }

    setGeoLoading(true);
    setGeoError(null);

    navigator.geolocation.getCurrentPosition(
      (position) => {
        const lat = position.coords.latitude;
        const lon = position.coords.longitude;
        const gpsPlace: PlaceModel = {
          id: `gps_${lat.toFixed(4)}_${lon.toFixed(4)}`,
          kind: 'point',
          names: {
            en: `Current Location (${lat.toFixed(2)}, ${lon.toFixed(2)})`,
            hi: `वर्तमान स्थान (${lat.toFixed(2)}, ${lon.toFixed(2)})`,
          },
          lat,
          lon,
          elevation: null,
          state: 'GPS',
          district: 'hyperlocal',
        };

        setSavedPlaces((prev) => {
          const filtered = prev.filter((p) => p.id !== gpsPlace.id);
          return [gpsPlace, ...filtered];
        });
        selectActivePlace(gpsPlace.id);
        setGeoLoading(false);
      },
      (error) => {
        setGeoLoading(false);
        setGeoError(
          error.code === error.PERMISSION_DENIED
            ? 'Location permission was denied. You can search by name.'
            : 'Could not fetch your coordinates. Please retry or search by name.'
        );
      },
      { timeout: 10000, enableHighAccuracy: true }
    );
  };

  // Add place to saved places
  const handleSavePlace = (place: PlaceModel) => {
    if (!savedPlaces.some((p) => p.id === place.id)) {
      setSavedPlaces((prev) => [...prev, place]);
    }
    selectActivePlace(place.id);
    setSearch('');
  };

  // Remove saved place
  const handleRemovePlace = (placeId: string) => {
    setSavedPlaces((prev) => prev.filter((p) => p.id !== placeId));
    if (activePlaceId === placeId) {
      const remaining = savedPlaces.filter((p) => p.id !== placeId);
      if (remaining.length > 0) {
        selectActivePlace(remaining[0].id);
      }
    }
  };

  return (
    <div className="max-w-column mx-auto px-4 py-6 space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100">
          {t('places')}
        </h1>
        <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
          Hyperlocal resolution for districts, blocks, panchayats, and saved places
        </p>
      </div>

      {/* GPS button & Search Input */}
      <div className="space-y-3">
        <Button
          type="button"
          variant="secondary"
          size="sm"
          onClick={handleUseLocation}
          isLoading={geoLoading}
          className="w-full flex items-center justify-center gap-2"
        >
          <svg className="w-4 h-4 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <span>Use My Current Location (GPS)</span>
        </Button>

        {geoError && (
          <div role="status" className="text-xs text-amber-700 dark:text-amber-300 bg-amber-50 dark:bg-amber-950/40 p-2.5 rounded-lg border border-amber-200 dark:border-amber-900">
            {geoError}
          </div>
        )}

        <div className="relative">
          <input
            type="search"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search district, block, or village (e.g. Pune, बारामती)..."
            className="w-full px-4 py-2.5 pl-10 rounded-xl border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100 text-sm focus-visible:outline focus-visible:outline-3 focus-visible:outline-focus-ring"
            aria-label="Search places"
          />
          <svg
            className="w-4 h-4 text-slate-400 absolute left-3.5 top-3.5"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
            aria-hidden="true"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
        </div>
      </div>

      {/* Search Results Dropdown/List when typing */}
      {search.trim().length > 0 && (
        <div className="space-y-2 border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-3 rounded-xl shadow-md">
          <h2 className="text-xs font-bold uppercase tracking-wider text-slate-400">Search Results</h2>
          {allPlaces.map((place) => {
            const pName = (language === 'hi' && place.names.hi) ? place.names.hi : place.names.en;
            return (
              <div
                key={place.id}
                className="flex items-center justify-between py-2 border-b border-slate-100 dark:border-slate-800 last:border-none"
              >
                <div>
                  <span className="font-semibold text-sm text-slate-800 dark:text-slate-200">{pName}</span>
                  <span className="text-xs text-slate-400 block">
                    {place.kind} • {place.district ? `${place.district}, ` : ''}{place.state || 'India'}
                  </span>
                </div>
                <button
                  type="button"
                  onClick={() => handleSavePlace(place)}
                  className="text-xs bg-blue-50 hover:bg-blue-100 text-blue-700 font-semibold px-3 py-1.5 rounded-lg transition-colors"
                >
                  Save & Select
                </button>
              </div>
            );
          })}
        </div>
      )}

      {/* Saved Places List */}
      <div className="space-y-3">
        <h2 className="text-xs font-bold uppercase tracking-wider text-slate-500">
          Saved Places (Persisted on Device)
        </h2>
        {savedPlaces.map((place) => {
          const isSelected = activePlaceId === place.id;
          const name = (language === 'hi' && place.names.hi) ? place.names.hi : place.names.en;

          return (
            <Card
              key={place.id}
              className={`transition-all ${
                isSelected ? 'ring-2 ring-blue-600 border-transparent shadow-md' : ''
              }`}
            >
              <div className="flex items-center justify-between">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-bold text-slate-900 dark:text-slate-100">{name}</span>
                    <span className="text-[10px] uppercase font-bold px-1.5 py-0.5 rounded bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400">
                      {place.kind}
                    </span>
                  </div>
                  <span className="text-xs text-slate-500">
                    {place.lat.toFixed(4)}°N, {place.lon.toFixed(4)}°E
                    {place.district ? ` • ${place.district}` : ''}
                    {place.state ? `, ${place.state}` : ''}
                  </span>
                </div>

                <div className="flex items-center gap-2">
                  {isSelected ? (
                    <Chip active icon={<span className="text-xs">✓</span>}>Active</Chip>
                  ) : (
                    <button
                      type="button"
                      onClick={() => selectActivePlace(place.id)}
                      className="text-xs text-blue-600 hover:text-blue-800 font-semibold px-2 py-1"
                    >
                      Set Active
                    </button>
                  )}
                  {savedPlaces.length > 1 && (
                    <button
                      type="button"
                      aria-label={`Remove ${name}`}
                      onClick={() => handleRemovePlace(place.id)}
                      className="text-slate-400 hover:text-red-600 p-1 rounded transition-colors"
                    >
                      ✕
                    </button>
                  )}
                </div>
              </div>
            </Card>
          );
        })}
      </div>
    </div>
  );
};
