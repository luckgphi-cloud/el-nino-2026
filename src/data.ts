// Chargement des fichiers produits par la collecte (public/data). Un fichier absent ou invalide → null,
// et l'interface affiche « indisponible » : jamais de valeur de remplacement.

export interface Manifest {
  start_date: string;
  updated_at: string;
  steps: Record<string, { ok: boolean; at?: string; error?: string; failed_at?: string }>;
}

export interface WeeklyNino { week_center: string; nino34_sst: number; nino34_anom: number }
export interface SeasonValue { season: string; year: number; center: string; value: number; provisional?: boolean }

export interface NinoData {
  retrieved_at: string;
  weekly: { source: string; url: string; data: WeeklyNino[] };
  roni: { source: string; url: string; threshold_el_nino: number; threshold_la_nina: number; threshold_source: string; data: SeasonValue[] };
  oni: { source: string; url: string; data: SeasonValue[] };
}

export interface StrengthBin { lo: number | null; hi: number | null; p: number }
export interface ForecastData {
  retrieved_at: string;
  source: string;
  categories: { issued: string; url: string; data: { season: string; center: string; la_nina: number; neutral: number; el_nino: number }[] };
  strengths: { issued: string; url: string; data: { season: string; center: string; bins: StrengthBin[] }[] };
  discussion: { date: string; status: string; synopsis_en: string | null; url: string };
  status_history?: { date: string; status: string; url: string }[];
}

export interface SstWeek {
  week_center: string; start: string; end: string; provisional: boolean;
  nino34_box_mean: number; cpc_nino34: number | null; diff: number | null;
}
export interface SstIndex {
  retrieved_at: string;
  source: string;
  url: string;
  last_obs_day: string;
  palette: { edges: number[]; colors: string[]; unit: string };
  image: { projection: string; width: number; height: number; bounds: [number, number, number, number] };
  readout: { resolution_deg: number; rows: number; cols: number; scale: number; nodata: number };
  validation: { weeks_compared: number; max_abs_diff: number | null; mean_abs_diff: number | null; description: string };
  weeks: SstWeek[];
}

export type EventType = "fire" | "flood" | "cyclone" | "drought";
export type AlertLevel = "Green" | "Orange" | "Red";
export interface ClimateEvent {
  id: string; type: EventType; name: string; from: string; to: string;
  lon: number; lat: number; level: AlertLevel; severity: string | null; country: string | null; url: string | null;
}
export interface EventsData {
  retrieved_at: string; source: string; url: string; terms_url: string;
  period: { from: string; to: string };
  levels: AlertLevel[];
  events: ClimateEvent[];
}

export interface TrendsData {
  source: string; note: string; url: string;
  features: GeoJSON.FeatureCollection;
}

const base = import.meta.env.BASE_URL;
export const dataUrl = (path: string) => `${base}data/${path}`;
export const assetUrl = (path: string) => `${base}${path}`;
/** URL absolue : nécessaire pour les sources chargées par le worker MapLibre. */
export const absoluteUrl = (path: string) => new URL(path, window.location.href).href;

export async function loadJSON<T>(path: string): Promise<T | null> {
  try {
    const r = await fetch(dataUrl(path), { cache: "no-cache" });
    if (!r.ok) return null;
    return (await r.json()) as T;
  } catch {
    return null;
  }
}

const readoutCache = new Map<string, Promise<Int8Array | null>>();

export function loadReadout(week: string): Promise<Int8Array | null> {
  let p = readoutCache.get(week);
  if (!p) {
    p = fetch(dataUrl(`sst/${week}.bin`))
      .then(async (r) => (r.ok ? new Int8Array(await r.arrayBuffer()) : null))
      .catch(() => null);
    readoutCache.set(week, p);
  }
  return p;
}

/** Anomalie (°C) à une position, depuis la grille 1° (nord-ouest en premier). null = terre/glace/absent. */
export function readoutAt(grid: Int8Array, lon: number, lat: number, cols = 360, rows = 180, scale = 0.1, nodata = -128): number | null {
  const L = ((((lon + 180) % 360) + 360) % 360) - 180;
  const row = Math.min(rows - 1, Math.max(0, Math.floor(90 - lat)));
  const col = Math.min(cols - 1, Math.max(0, Math.floor(L + 180)));
  const v = grid[row * cols + col];
  return v === nodata ? null : v * scale;
}
