import type { AlertLevel, ClimateEvent, EventType } from "./data";
import { frDate } from "./format";

// Couleurs Okabe-Ito choisies hors de l'échelle bleu-rouge des températures ; chaque type a aussi sa forme.
export const EVENT_STYLE: Record<EventType, { label: string; color: string; shape: "triangle" | "circle" | "spiral" | "square" }> = {
  fire: { label: "Incendie", color: "#F0E442", shape: "triangle" },
  flood: { label: "Inondation", color: "#009E73", shape: "circle" },
  cyclone: { label: "Cyclone / typhon", color: "#CC79A7", shape: "spiral" },
  drought: { label: "Sécheresse", color: "#E69F00", shape: "square" },
};

export const LEVEL_FR: Record<AlertLevel, string> = { Green: "vert", Orange: "orange", Red: "rouge" };
export const LEVEL_SIZE: Record<AlertLevel, number> = { Green: 0.7, Orange: 0.95, Red: 1.25 };

export interface EventFilter {
  types: Set<EventType>;
  levels: Set<AlertLevel>;
  mode: "week" | "cumulative";
  weekStart: string;
  weekEnd: string;
  periodStart: string;
}

/** Événements à afficher : actifs pendant la semaine, ou survenus depuis le début de la période (cumul). */
export function filterEvents(events: ClimateEvent[], f: EventFilter): ClimateEvent[] {
  const from = f.mode === "week" ? f.weekStart : f.periodStart;
  return events.filter(
    (e) => f.types.has(e.type) && f.levels.has(e.level) && e.from.slice(0, 10) <= f.weekEnd && e.to.slice(0, 10) >= from,
  );
}

export function toGeoJSON(events: ClimateEvent[]): GeoJSON.FeatureCollection<GeoJSON.Point> {
  return {
    type: "FeatureCollection",
    features: events.map((e) => ({
      type: "Feature",
      geometry: { type: "Point", coordinates: [e.lon, e.lat] },
      properties: { id: e.id, type: e.type, level: e.level, size: LEVEL_SIZE[e.level], icon: `ev-${e.type}` },
    })),
  };
}

function esc(s: string): string {
  return s.replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]!);
}

/** Fiche d'un événement (HTML échappé). Aucune mention causale. */
export function eventCard(e: ClimateEvent): string {
  const st = EVENT_STYLE[e.type];
  const dates = e.from.slice(0, 10) === e.to.slice(0, 10) ? frDate(e.from) : `${frDate(e.from)} → ${frDate(e.to)}`;
  return `<div class="card">
  <div class="card-type">${shapeSvg(e.type, 16)} ${st.label}</div>
  <h3>${esc(e.name)}</h3>
  <dl>
    <dt>Dates</dt><dd>${dates}</dd>
    <dt>Lieu</dt><dd>${e.country ? esc(e.country) : "non précisé"}</dd>
    <dt>Alerte GDACS</dt><dd>niveau ${LEVEL_FR[e.level]}</dd>
    <dt>Intensité</dt><dd>${e.severity ? esc(e.severity) : "indisponible"}</dd>
  </dl>
  ${e.url ? `<a href="${esc(e.url)}" target="_blank" rel="noopener">Rapport GDACS ↗</a>` : ""}
  <p class="card-note">Événement observé. Sa présence ici n'implique pas qu'il soit dû à El Niño.</p>
</div>`;
}

/** Pictogramme SVG d'un type d'événement (légende, filtres, fiches). */
export function shapeSvg(type: EventType, size = 18): string {
  const { color, shape } = EVENT_STYLE[type];
  const s = 'stroke="#111" stroke-width="1.6"';
  const body = {
    triangle: `<path d="M9 2 L16.5 15.5 H1.5 Z" fill="${color}" ${s}/>`,
    circle: `<circle cx="9" cy="9" r="6.5" fill="${color}" ${s}/>`,
    square: `<rect x="2.8" y="2.8" width="12.4" height="12.4" fill="${color}" ${s}/>`,
    spiral: `<circle cx="9" cy="9" r="7" fill="${color}" ${s}/><path d="M9 9 m-3.5 0 a3.5 3.5 0 1 1 3.5 3.5 M9 9 a1.5 1.5 0 1 0 -1.5 -1.5" fill="none" stroke="#111" stroke-width="1.5"/>`,
  }[shape];
  return `<svg class="shape" width="${size}" height="${size}" viewBox="0 0 18 18" aria-hidden="true">${body}</svg>`;
}
