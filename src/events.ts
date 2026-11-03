import type { AlertLevel, ClimateEvent, EventType, Intensity } from "./data";
import { frDate } from "./format";

// Couleurs Okabe-Ito choisies hors de l'échelle bleu-rouge des températures ; chaque type a aussi sa forme.
export const EVENT_STYLE: Record<EventType, { label: string; color: string; shape: "triangle" | "circle" | "spiral" | "square" }> = {
  fire: { label: "Incendie", color: "#F0E442", shape: "triangle" },
  flood: { label: "Inondation", color: "#009E73", shape: "circle" },
  cyclone: { label: "Cyclone / typhon", color: "#CC79A7", shape: "spiral" },
  drought: { label: "Sécheresse", color: "#E69F00", shape: "square" },
};

export const LEVEL_FR: Record<AlertLevel, string> = { Green: "vert", Orange: "orange", Red: "rouge" };

/** Intensité physique (vent, surface) → rendu : creux / plein / plein avec halo ; pointillé si non mesurée. */
export type IntensityKey = Intensity | "unknown";
export type SymbolStyle = "hollow" | "filled" | "halo" | "dashed";
export const INTENSITY: Record<IntensityKey, { label: string; size: number; style: SymbolStyle; rank: number; legend: string }> = {
  extreme: { label: "Extrême", size: 1.6, style: "halo", rank: 4, legend: "grand, plein, halo blanc" },
  strong: { label: "Forte", size: 1.05, style: "filled", rank: 3, legend: "moyen, plein" },
  moderate: { label: "Modérée", size: 0.75, style: "hollow", rank: 1, legend: "petit, creux" },
  unknown: { label: "Non mesurée", size: 0.95, style: "dashed", rank: 2, legend: "contour pointillé" },
};
export const intensityKey = (e: ClimateEvent): IntensityKey => e.intensity ?? "unknown";

export interface EventFilter {
  types: Set<EventType>;
  intensities: Set<IntensityKey>;
  mode: "week" | "cumulative";
  weekStart: string;
  weekEnd: string;
  periodStart: string;
}

/** Événements à afficher : actifs pendant la semaine, ou survenus depuis le début de la période (cumul). */
export function filterEvents(events: ClimateEvent[], f: EventFilter): ClimateEvent[] {
  const from = f.mode === "week" ? f.weekStart : f.periodStart;
  return events.filter(
    (e) => f.types.has(e.type) && f.intensities.has(intensityKey(e)) && e.from.slice(0, 10) <= f.weekEnd && e.to.slice(0, 10) >= from,
  );
}

export function toGeoJSON(events: ClimateEvent[]): GeoJSON.FeatureCollection<GeoJSON.Point> {
  return {
    type: "FeatureCollection",
    features: events.map((e) => {
      const it = INTENSITY[intensityKey(e)];
      return {
        type: "Feature",
        geometry: { type: "Point", coordinates: [e.lon, e.lat] },
        properties: { id: e.id, type: e.type, rank: it.rank, size: it.size, icon: `ev-${e.type}-${it.style}` },
      };
    }),
  };
}

function esc(s: string): string {
  return s.replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]!);
}

const MEASURE_FR: Record<EventType, string> = {
  cyclone: "vent maximal", fire: "surface brûlée", drought: "surface touchée", flood: "surface de la zone touchée (estimation)",
};

export function formatMagnitude(e: ClimateEvent): string {
  if (e.magnitude === null || e.magnitude === undefined) return "mesure physique indisponible";
  const n = Math.round(e.magnitude).toLocaleString("fr-FR");
  return `${MEASURE_FR[e.type]} : ${n} ${e.magnitude_unit}`;
}

/** Fiche d'un événement (HTML échappé). Aucune mention causale. */
export function eventCard(e: ClimateEvent): string {
  const st = EVENT_STYLE[e.type];
  const it = INTENSITY[intensityKey(e)];
  const dates = e.from.slice(0, 10) === e.to.slice(0, 10) ? frDate(e.from) : `${frDate(e.from)} → ${frDate(e.to)}`;
  return `<div class="card">
  <div class="card-type">${shapeSvg(e.type, 18, it.style)} ${st.label}</div>
  <h3>${esc(e.name)}</h3>
  <dl>
    <dt>Dates</dt><dd>${dates}</dd>
    <dt>Lieu</dt><dd>${e.country ? esc(e.country) : "non précisé"}</dd>
    <dt>Intensité</dt><dd><strong>${it.label}</strong> — ${formatMagnitude(e)}</dd>
    <dt>Description</dt><dd>${e.severity ? esc(e.severity) : "indisponible"}</dd>
    <dt>Alerte GDACS</dt><dd>niveau ${LEVEL_FR[e.level]} <span class="muted">(tient compte de la population exposée et des capacités du pays)</span></dd>
  </dl>
  ${e.url ? `<a href="${esc(e.url)}" target="_blank" rel="noopener">Rapport GDACS ↗</a>` : ""}
  <p class="card-note">Événement observé. Sa présence ici n'implique pas qu'il soit dû à El Niño.</p>
</div>`;
}

/** Pictogramme SVG d'un type d'événement dans un style d'intensité (carte, légende, filtres, fiches). */
export function shapeSvg(type: EventType, size = 18, style: SymbolStyle = "filled", color = EVENT_STYLE[type].color): string {
  const { shape } = EVENT_STYLE[type];
  const geom = {
    triangle: (a: string) => `<path d="M12 3.5 L20.5 19 H3.5 Z" ${a}/>`,
    circle: (a: string) => `<circle cx="12" cy="12" r="7.8" ${a}/>`,
    square: (a: string) => `<rect x="4.6" y="4.6" width="14.8" height="14.8" ${a}/>`,
    spiral: (a: string) => `<circle cx="12" cy="12" r="8" ${a}/>`,
  }[shape];
  const swirl = (stroke: string) =>
    shape === "spiral" ? `<path d="M12 12 m-3.8 0 a3.8 3.8 0 1 1 3.8 3.8 M12 12 a1.6 1.6 0 1 0 -1.6 -1.6" fill="none" stroke="${stroke}" stroke-width="1.6"/>` : "";
  let body: string;
  if (style === "hollow" || style === "dashed") {
    const dash = style === "dashed" ? ' stroke-dasharray="3 2.2"' : "";
    // contour sombre sous le contour coloré : lisible sur le bleu comme sur le rouge
    body = geom(`fill="none" stroke="#111" stroke-width="4.6"${dash}`) + geom(`fill="none" stroke="${color}" stroke-width="2.4"${dash}`) + swirl(color);
  } else {
    // halo : large anneau blanc bordé de noir, visible sur toutes les couleurs de fond
    const halo = style === "halo" ? geom('fill="#111" stroke="#111" stroke-width="10"') + geom('fill="#fff" stroke="#fff" stroke-width="7"') : "";
    body = halo + geom(`fill="${color}" stroke="#111" stroke-width="1.8"`) + swirl("#111");
  }
  return `<svg class="shape" width="${size}" height="${size}" viewBox="-3 -3 30 30" aria-hidden="true">${body}</svg>`;
}
