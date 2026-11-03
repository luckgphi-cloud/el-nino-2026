import { GeoJSONSource, ImageSource, Map as MlMap, NavigationControl, Popup, setWorkerUrl, type MapLayerMouseEvent } from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
// Le worker MapLibre est autonome : on le sert tel quel (sinon Vite casse son URL relative).
import workerUrl from "maplibre-gl/dist/maplibre-gl-worker.mjs?url";

setWorkerUrl(workerUrl);
import { absoluteUrl, assetUrl, dataUrl, type ClimateEvent, type EventType, type SstIndex } from "./data";
import { EVENT_STYLE, eventCard, shapeSvg, toGeoJSON } from "./events";

export type Projection = "globe" | "mercator";

const EMPTY: GeoJSON.FeatureCollection = { type: "FeatureCollection", features: [] };
// Vue d'ouverture : Pacifique équatorial, là où se trouve le réchauffement.
export const PACIFIC_VIEW = { center: [-150, 2] as [number, number], zoom: 1.55 };

function svgImage(svg: string, size: number): Promise<HTMLImageElement> {
  return new Promise((resolve, reject) => {
    const img = new Image(size, size);
    img.onload = () => resolve(img);
    img.onerror = reject;
    img.src = `data:image/svg+xml;charset=utf-8,${encodeURIComponent(svg.replace('class="shape" ', 'xmlns="http://www.w3.org/2000/svg" '))}`;
  });
}

function hatchPattern(color: string, kind: "lines" | "dots"): ImageData {
  const s = 12;
  const c = document.createElement("canvas");
  c.width = c.height = s;
  const g = c.getContext("2d")!;
  g.strokeStyle = g.fillStyle = color;
  g.lineWidth = 1.6;
  if (kind === "lines") {
    g.beginPath();
    g.moveTo(0, s); g.lineTo(s, 0);
    g.moveTo(-s / 2, s / 2); g.lineTo(s / 2, -s / 2);
    g.moveTo(s / 2, s * 1.5); g.lineTo(s * 1.5, s / 2);
    g.stroke();
  } else {
    g.beginPath(); g.arc(3, 3, 1.6, 0, Math.PI * 2); g.arc(9, 9, 1.6, 0, Math.PI * 2); g.fill();
  }
  return g.getImageData(0, 0, s, s);
}

export interface MapView {
  map: MlMap;
  setWeek(week: string): void;
  setEvents(events: ClimateEvent[], all: ClimateEvent[]): void;
  setTrends(fc: GeoJSON.FeatureCollection | null, visible: boolean): void;
  setSstVisible(v: boolean): void;
  setProjection(p: Projection): void;
  onHover(cb: (lngLat: { lng: number; lat: number } | null) => void): void;
}

export async function createMap(container: HTMLElement, sst: SstIndex | null, initialWeek: string | null): Promise<MapView> {
  const [w, s, e, n] = sst?.image.bounds ?? [-180, -85.0511, 180, 85.0511];
  const coords: [[number, number], [number, number], [number, number], [number, number]] = [[w, n], [e, n], [e, s], [w, s]];

  const map = new MlMap({
    container,
    style: {
      version: 8,
      projection: { type: "globe" },
      sky: { "atmosphere-blend": ["interpolate", ["linear"], ["zoom"], 0, 0.8, 4, 0] },
      sources: {
        land: { type: "geojson", data: absoluteUrl(assetUrl("basemap/land.geojson")) },
        borders: { type: "geojson", data: absoluteUrl(assetUrl("basemap/borders.geojson")) },
        events: { type: "geojson", data: EMPTY },
        trends: { type: "geojson", data: EMPTY },
        ...(sst && initialWeek ? { sst: { type: "image" as const, url: absoluteUrl(dataUrl(`sst/${initialWeek}.png`)), coordinates: coords } } : {}),
      },
      layers: [
        { id: "ocean", type: "background", paint: { "background-color": "#1d2733" } },
        ...(sst && initialWeek
          ? [{ id: "sst", type: "raster" as const, source: "sst", paint: { "raster-resampling": "nearest" as const, "raster-fade-duration": 0 } }]
          : []),
        { id: "land", type: "fill", source: "land", paint: { "fill-color": "#585d66" } },
        { id: "borders", type: "line", source: "borders", paint: { "line-color": "#8a909a", "line-width": 0.6 } },
        { id: "trends-fill", type: "fill", source: "trends", layout: { visibility: "none" }, paint: { "fill-pattern": ["get", "pattern"] } },
        { id: "trends-line", type: "line", source: "trends", layout: { visibility: "none" },
          paint: { "line-color": ["get", "stroke"], "line-width": 1.6, "line-dasharray": [3, 2] } },
        // Niveau d'alerte : anneaux (sans couleur rouge, pour ne pas se confondre avec l'échelle des températures).
        // Rouge = double anneau épais, orange = anneau fin, vert = aucun.
        { id: "events-ring-outer", type: "circle", source: "events", filter: ["==", ["get", "level"], "Red"],
          paint: { "circle-radius": 16, "circle-color": "rgba(0,0,0,0)", "circle-stroke-color": "#111", "circle-stroke-width": 2 } },
        { id: "events-ring", type: "circle", source: "events", filter: ["in", ["get", "level"], ["literal", ["Red", "Orange"]]],
          paint: { "circle-radius": ["match", ["get", "level"], "Red", 14, 11], "circle-color": "rgba(0,0,0,0)",
            "circle-stroke-color": "#ffffff", "circle-stroke-width": ["match", ["get", "level"], "Red", 2.5, 1.2] } },
        { id: "events", type: "symbol", source: "events",
          layout: { "icon-image": ["get", "icon"], "icon-size": ["get", "size"], "icon-allow-overlap": true,
            "symbol-sort-key": ["match", ["get", "level"], "Red", 3, "Orange", 2, 1] } },
      ],
    },
    center: PACIFIC_VIEW.center,
    zoom: PACIFIC_VIEW.zoom,
    attributionControl: { compact: true, customAttribution: "Fond : Natural Earth · Données : NOAA, GDACS" },
    maxPitch: 0,
  });
  map.addControl(new NavigationControl({ showCompass: false }), "top-left");
  if (import.meta.env.DEV) (window as unknown as { __map: MlMap }).__map = map; // inspection en développement
  map.on("error", (e) => console.error("Carte :", e.error?.message ?? e));
  await new Promise<void>((resolve) => map.once("load", () => resolve()));

  for (const t of Object.keys(EVENT_STYLE) as EventType[]) {
    map.addImage(`ev-${t}`, await svgImage(shapeSvg(t, 36), 36), { pixelRatio: 2 });
  }
  map.addImage("hatch-wet", hatchPattern("#4fc3f7", "lines"));
  map.addImage("hatch-dry", hatchPattern("#d7b98e", "dots"));
  map.addImage("hatch-warm", hatchPattern("#ff8a65", "lines"));

  // Préchargement des PNG hebdomadaires pour une lecture sans saccade.
  const images = new Map<string, Promise<HTMLImageElement>>();
  const preload = (week: string) => {
    let p = images.get(week);
    if (!p) {
      p = new Promise((res, rej) => {
        const img = new Image();
        img.onload = () => res(img);
        img.onerror = rej;
        img.src = dataUrl(`sst/${week}.png`);
      });
      images.set(week, p);
    }
    return p;
  };
  sst?.weeks.forEach((wk, i) => setTimeout(() => preload(wk.week_center).catch(() => undefined), 200 + i * 40));

  let wanted = initialWeek;
  const popup = new Popup({ closeButton: true, maxWidth: "300px", className: "event-popup" });
  let eventsById = new Map<string, ClimateEvent>();

  map.on("click", "events", (ev: MapLayerMouseEvent) => {
    const f = ev.features?.[0];
    const e = f && eventsById.get(String(f.properties?.id));
    if (e) popup.setLngLat([e.lon, e.lat]).setHTML(eventCard(e)).addTo(map);
  });
  map.on("click", "trends-fill", (ev: MapLayerMouseEvent) => {
    if (map.queryRenderedFeatures(ev.point, { layers: ["events"] }).length) return; // l'événement a priorité
    const label = ev.features?.[0]?.properties?.label_fr;
    if (!label) return;
    const p = document.createElement("p");
    p.textContent = String(label);
    const card = document.createElement("div");
    card.className = "card";
    card.innerHTML = `<div class="card-type">Tendance statistique — ni prévision, ni causalité</div>`;
    card.append(p);
    popup.setLngLat(ev.lngLat).setDOMContent(card).addTo(map);
  });
  map.on("mouseenter", "events", () => (map.getCanvas().style.cursor = "pointer"));
  map.on("mouseleave", "events", () => (map.getCanvas().style.cursor = ""));

  return {
    map,
    setWeek(week) {
      wanted = week;
      const src = map.getSource("sst") as ImageSource | undefined;
      if (!src) return;
      preload(week)
        .then((img) => {
          if (wanted === week) src.updateImage({ image: img });
        })
        .catch(() => undefined);
    },
    setEvents(events, all) {
      eventsById = new Map(all.map((e) => [e.id, e]));
      (map.getSource("events") as GeoJSONSource).setData(toGeoJSON(events));
    },
    setTrends(fc, visible) {
      (map.getSource("trends") as GeoJSONSource).setData(fc ?? EMPTY);
      for (const id of ["trends-fill", "trends-line"]) map.setLayoutProperty(id, "visibility", visible ? "visible" : "none");
    },
    setSstVisible(v) {
      if (map.getLayer("sst")) map.setLayoutProperty("sst", "visibility", v ? "visible" : "none");
    },
    setProjection(p) {
      map.setProjection({ type: p });
    },
    onHover(cb) {
      map.on("mousemove", (ev) => cb(ev.lngLat));
      map.on("mouseout", () => cb(null));
    },
  };
}
