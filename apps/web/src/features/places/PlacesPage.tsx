import React, { useState, useEffect } from 'react';
import { useTranslation } from '../../i18n/LanguageContext';
import { Card } from '../../components/Card';
import { Chip } from '../../components/Chip';
import { PlaceModel, MOCK_PLACES } from '../../mocks/mockData';

export const PlacesPage: React.FC = () => {
  const { t, language } = useTranslation();
  const [places, setPlaces] = useState<PlaceModel[]>([]);
  const [search, setSearch] = useState('');
  const [selectedPlaceId, setSelectedPlaceId] = useState('place_pune');

  useEffect(() => {
    fetch('/v1/places/saved')
      .then((res) => res.json())
      .then((data) => setPlaces(data))
      .catch(() => setPlaces(MOCK_PLACES));
  }, []);

  const filteredPlaces = search
    ? places.filter(
        (p) =>
          p.names.en.toLowerCase().includes(search.toLowerCase()) ||
          p.names.hi?.includes(search) ||
          p.district?.toLowerCase().includes(search.toLowerCase())
      )
    : places;

  return (
    <div className="max-w-column mx-auto px-4 py-6">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100">
          {t('places')}
        </h1>
        <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
          Manage Home, Farm, Work and search village/district locations
        </p>
      </div>

      <div className="mb-6">
        <div className="relative">
          <input
            type="search"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search district, block, or village..."
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

      <div className="space-y-3">
        <h2 className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-2">
          Saved Places
        </h2>
        {filteredPlaces.map((place) => {
          const isSelected = selectedPlaceId === place.id;
          const name = (language === 'hi' && place.names.hi) ? place.names.hi : place.names.en;

          return (
            <Card
              key={place.id}
              className={`cursor-pointer transition-all ${
                isSelected ? 'ring-2 ring-blue-600 border-transparent' : ''
              }`}
              onClick={() => setSelectedPlaceId(place.id)}
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
                    {place.district ? `${place.district}, ` : ''}
                    {place.state || 'India'}
                  </span>
                </div>

                {isSelected ? (
                  <Chip active icon={<span className="text-xs">✓</span>}>Active</Chip>
                ) : (
                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation();
                      setSelectedPlaceId(place.id);
                    }}
                    className="text-xs text-blue-600 hover:text-blue-800 font-medium"
                  >
                    Select
                  </button>
                )}
              </div>
            </Card>
          );
        })}
      </div>
    </div>
  );
};
