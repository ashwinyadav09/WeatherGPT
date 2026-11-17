/**
 * Mock data conforming strictly to packages/contracts/schemas
 */

export interface PlaceModel {
  id: string;
  kind: 'district' | 'block' | 'gp' | 'village' | 'station' | 'point';
  names: Record<string, string>;
  lat: number;
  lon: number;
  elevation?: number | null;
  state?: string | null;
  district?: string | null;
}

export interface AlertModel {
  id: string;
  sender: string;
  sent: string;
  status: string;
  msg_type: string;
  hazard: string;
  severity: 'Extreme' | 'Severe' | 'Moderate' | 'Minor' | 'Unknown';
  urgency: 'Immediate' | 'Expected' | 'Future' | 'Past' | 'Unknown';
  certainty: 'Observed' | 'Likely' | 'Possible' | 'Unlikely' | 'Unknown';
  onset: string;
  expires: string;
  areas: Array<Record<string, unknown>>;
  text_by_language: Record<string, string>;
  source_url: string;
  authority_tier: number;
  level: 'green' | 'yellow' | 'orange' | 'red';
}

export const MOCK_PLACES: PlaceModel[] = [
  {
    id: 'place_pune',
    kind: 'district',
    names: {
      en: 'Pune',
      hi: 'पुणे',
      mr: 'पुणे',
    },
    lat: 18.5204,
    lon: 73.8567,
    elevation: 560,
    state: 'Maharashtra',
    district: 'Pune',
  },
  {
    id: 'place_mumbai',
    kind: 'district',
    names: {
      en: 'Mumbai',
      hi: 'मुंबई',
      mr: 'मुंबई',
    },
    lat: 19.076,
    lon: 72.8777,
    elevation: 14,
    state: 'Maharashtra',
    district: 'Mumbai Suburban',
  },
  {
    id: 'place_nagpur',
    kind: 'district',
    names: {
      en: 'Nagpur',
      hi: 'नागपुर',
      mr: 'नागपूर',
    },
    lat: 21.1458,
    lon: 79.0882,
    elevation: 310,
    state: 'Maharashtra',
    district: 'Nagpur',
  },
  {
    id: 'place_baramati',
    kind: 'block',
    names: {
      en: 'Baramati',
      hi: 'बारामती',
      mr: 'बारामती',
    },
    lat: 18.1517,
    lon: 74.5774,
    elevation: 538,
    state: 'Maharashtra',
    district: 'Pune',
  },
];

export const MOCK_ALERTS: AlertModel[] = [
  {
    id: 'alert_imd_2026_01',
    sender: 'imd.sachet.ndma.gov.in',
    sent: '2026-11-17T06:00:00Z',
    status: 'Actual',
    msg_type: 'Alert',
    hazard: 'Heavy Rainfall',
    severity: 'Severe',
    urgency: 'Expected',
    certainty: 'Likely',
    onset: '2026-11-17T09:00:00Z',
    expires: '2026-11-18T18:00:00Z',
    areas: [
      {
        areaDesc: 'Pune district',
        circle: '18.5204,73.8567,25.0',
      },
    ],
    text_by_language: {
      en: 'Heavy to very heavy rainfall expected in isolated ghat areas of Pune district. Stay indoors during thunderstorms.',
      hi: 'पुणे जिले के अलग-अलग घाट क्षेत्रों में भारी से बहुत भारी बारिश की संभावना है। गरज के दौरान घरों में रहें।',
    },
    source_url: 'https://sachet.ndma.gov.in/alerts/alert_imd_2026_01',
    authority_tier: 1,
    level: 'orange',
  },
];

export const MOCK_EVIDENCE_PACKETS = [
  {
    id: 'ev_mock_om_01',
    source: 'open_meteo.forecast',
    authority_tier: 5,
    provenance: 'documented-sample',
    issued_at: '2026-11-17T00:00:00Z',
    valid_from: '2026-11-17T00:00:00Z',
    valid_to: '2026-11-24T00:00:00Z',
    place: {
      id: 'pt_18.5204_73.8567',
      name: 'Pune',
      lat: 18.5204,
      lon: 73.8567,
    },
    values: [
      { variable: 'temperature', value: 27.5, unit: 'degC', step: null },
      { variable: 'rain', value: 12.4, unit: 'mm', step: null },
      { variable: 'rain_probability_max', value: 85, unit: '%', step: null },
    ],
    attribution: 'Weather data by Open-Meteo.com (CC BY 4.0)',
    fetched_at: '2026-11-17T06:00:00Z',
  },
];
