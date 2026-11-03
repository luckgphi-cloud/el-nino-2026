import "./styles.css";
import { createChart } from "./chart";
import {
  loadJSON, loadReadout, readoutAt,
  type AlertLevel, type EventsData, type EventType, type ForecastData, type Manifest, type NinoData, type SstIndex, type TrendsData,
} from "./data";
import { EVENT_STYLE, filterEvents, shapeSvg } from "./events";
import { addDays, frDate, frMonthYear, signedC, weekRange } from "./format";
import { createMap, type Projection } from "./map";

const $ = <T extends HTMLElement>(sel: string) => document.querySelector(sel) as T;

interface Week { center: string; start: string; end: string; provisional: boolean; hasMap: boolean }

async function main() {
  const [manifest, nino, forecast, sst, events, trends] = await Promise.all([
    loadJSON<Manifest>("manifest.json"),
    loadJSON<NinoData>("nino.json"),
    loadJSON<ForecastData>("forecast.json"),
    loadJSON<SstIndex>("sst/index.json"),
    loadJSON<EventsData>("events.json"),
    loadJSON<TrendsData>("trends.json"),
  ]);

  const missing: string[] = [];
  if (!sst) missing.push("carte des températures");
  if (!nino) missing.push("indice Niño-3.4");
  if (!forecast) missing.push("prévision");
  if (!events) missing.push("événements");
  if (missing.length) {
    const b = $("#status-banner");
    b.hidden = false;
    b.textContent = `Données indisponibles : ${missing.join(", ")}.`;
  }

  // Semaines : celles de la carte ; à défaut, celles de l'indice hebdomadaire.
  const weeks: Week[] = sst
    ? sst.weeks.map((w) => ({ center: w.week_center, start: w.start, end: w.end, provisional: w.provisional, hasMap: true }))
    : (nino?.weekly.data ?? []).map((w) => ({ center: w.week_center, start: addDays(w.week_center, -3), end: addDays(w.week_center, 3), provisional: false, hasMap: false }));
  const start = manifest?.start_date ?? weeks[0]?.start ?? "2026-01-01";
  let idx = Math.max(0, weeks.length - 1); // ouverture sur la semaine la plus récente

  // La courbe s'affiche sans attendre la carte (fond de carte et worker plus lourds à charger).
  const mapReady = createMap($("#map"), sst, weeks[idx]?.hasMap ? weeks[idx].center : null);
  let ready = false;
  const chart = createChart({
    container: $("#chart"), nino, forecast, start: weeks[0]?.start ?? start,
    onPick: (iso) => {
      if (!ready) return;
      let best = 0;
      weeks.forEach((w, i) => { if (Math.abs(+new Date(w.center) - +new Date(iso)) < Math.abs(+new Date(weeks[best].center) - +new Date(iso))) best = i; });
      setWeek(best);
    },
  });
  if (weeks[idx]) {
    chart.setCursor(weeks[idx].center);
    $("#week-label").textContent = `Semaine ${weekRange(weeks[idx].start, weeks[idx].end)}`;
  }
  const view = await mapReady;
  ready = true;

  // --- Légende (repliée par défaut sur petit écran, le titre reste visible) ---
  if (window.matchMedia("(max-width: 760px)").matches) ($("#legend") as HTMLDetailsElement).open = false;
  if (sst) {
    const { edges, colors } = sst.palette;
    $("#legend-sst").innerHTML = `<div class="legend-title">Anomalie de température de surface (°C, observé)</div>
      <div class="ramp">${colors.map((c, i) => `<span style="background:${c}" title="${i === 0 ? `< ${edges[0]}` : i === colors.length - 1 ? `≥ ${edges[edges.length - 1]}` : `${edges[i - 1]} à ${edges[i]}`} °C"></span>`).join("")}</div>
      <div class="ramp-ticks"><span>−4</span><span>−2</span><span>0</span><span>+2</span><span>+4</span></div>
      <div class="legend-note">Bleu = plus froid, rouge = plus chaud que 1991-2020 · gris = terre ou glace</div>`;
  } else {
    $("#legend-sst").innerHTML = `<div class="legend-title">Températures de surface : indisponible</div>`;
  }
  $("#legend-events").innerHTML = `<div class="legend-title">Événements (GDACS)</div>` +
    (Object.keys(EVENT_STYLE) as EventType[]).map((t) => `<div class="legend-item">${shapeSvg(t)} ${EVENT_STYLE[t].label}</div>`).join("") +
    `<div class="legend-note">Taille = niveau d'alerte (vert, orange, rouge)</div>`;

  // --- Filtres d'événements ---
  const types = new Set<EventType>(Object.keys(EVENT_STYLE) as EventType[]);
  $("#event-types").innerHTML = (Object.keys(EVENT_STYLE) as EventType[])
    .map((t) => `<label class="row"><input type="checkbox" name="evtype" value="${t}" checked /> ${shapeSvg(t)} ${EVENT_STYLE[t].label}</label>`).join("");
  const levels = new Set<AlertLevel>(["Orange", "Red"]);
  let mode: "week" | "cumulative" = "week";

  // Les alertes vertes (plusieurs milliers) sont dans un fichier à part, chargé seulement si on les active.
  let allEvents = events?.events ?? [];
  let green: "absent" | "loading" | "ok" | "unavailable" = "absent";
  async function ensureGreen() {
    if (green !== "absent") return;
    green = "loading";
    const g = await loadJSON<EventsData>("events_green.json");
    green = g ? "ok" : "unavailable";
    if (g) allEvents = allEvents.concat(g.events);
    refreshEvents();
  }

  function refreshEvents() {
    const w = weeks[idx];
    if (!events || !w) {
      $("#event-count").textContent = "Événements : indisponible";
      return;
    }
    const shown = filterEvents(allEvents, { types, levels, mode, weekStart: w.start, weekEnd: w.end, periodStart: weeks[0].start });
    view.setEvents(shown, allEvents);
    const note = levels.has("Green") && green === "loading" ? " (chargement des alertes vertes…)"
      : levels.has("Green") && green === "unavailable" ? " (alertes vertes : indisponible)" : "";
    $("#event-count").textContent = `${shown.length} événement${shown.length > 1 ? "s" : ""} affiché${shown.length > 1 ? "s" : ""}${note}`;
  }
  document.querySelectorAll<HTMLInputElement>("input[name=evtype]").forEach((el) =>
    el.addEventListener("change", () => { el.checked ? types.add(el.value as EventType) : types.delete(el.value as EventType); refreshEvents(); }));
  document.querySelectorAll<HTMLInputElement>("input[name=lvl]").forEach((el) =>
    el.addEventListener("change", () => {
      el.checked ? levels.add(el.value as AlertLevel) : levels.delete(el.value as AlertLevel);
      if (el.checked && el.value === "Green") void ensureGreen();
      refreshEvents();
    }));
  document.querySelectorAll<HTMLInputElement>("input[name=evmode]").forEach((el) =>
    el.addEventListener("change", () => { mode = el.value as typeof mode; refreshEvents(); }));

  // --- Couches ---
  $<HTMLInputElement>("#lyr-sst").addEventListener("change", (e) => view.setSstVisible((e.target as HTMLInputElement).checked));
  const trendsBox = $<HTMLInputElement>("#lyr-trends");
  if (!trends) {
    trendsBox.disabled = true;
    trendsBox.parentElement!.append(" — indisponible");
  }
  let trendSeason = "DJF";
  function refreshTrends() {
    const fc = trends
      ? { ...trends.features, features: trends.features.features.filter((f) => f.properties?.season === trendSeason) }
      : null;
    view.setTrends(fc, trendsBox.checked);
    const lg = $("#legend-trends");
    lg.hidden = !trendsBox.checked;
    lg.innerHTML = `<div class="legend-title">Tendance El Niño, ${trendSeason === "DJF" ? "déc.–févr." : "juin–août"} (statistique, pas causalité)</div>
      <div class="legend-item"><i class="pat pat-wet"></i> Plus humide (parfois aussi plus chaud ou plus frais)</div>
      <div class="legend-item"><i class="pat pat-dry"></i> Plus sec (parfois aussi plus chaud ou plus frais)</div>
      <div class="legend-item"><i class="pat pat-warm"></i> Plus chaud</div>
      <div class="legend-note">Contours schématiques d'après la NOAA (CPC). Cliquez une zone pour le détail.</div>`;
  }
  trendsBox.addEventListener("change", refreshTrends);
  document.querySelectorAll<HTMLInputElement>("input[name=trseason]").forEach((el) =>
    el.addEventListener("change", () => { trendSeason = el.value; refreshTrends(); }));

  // --- Projection ---
  document.querySelectorAll<HTMLButtonElement>("[data-proj]").forEach((b) => b.addEventListener("click", () => {
    view.setProjection(b.dataset.proj as Projection);
    document.querySelectorAll("[data-proj]").forEach((o) => o.setAttribute("aria-pressed", String(o === b)));
  }));

  // --- Panneaux ---
  document.querySelectorAll<HTMLButtonElement>("[data-open]").forEach((b) =>
    b.addEventListener("click", () => ($(`#${b.dataset.open}`) as HTMLDialogElement).showModal()));
  const panelBtn = $(".panel-toggle");
  panelBtn.addEventListener("click", () => {
    const open = document.body.classList.toggle("layers-open");
    panelBtn.setAttribute("aria-expanded", String(open));
  });

  // --- Lecture de l'anomalie sous le curseur ---
  view.onHover(async (ll) => {
    const el = $("#readout");
    const w = weeks[idx];
    if (!ll || !sst || !w) return;
    const grid = await loadReadout(w.center);
    if (!grid) { el.textContent = "Lecture : indisponible"; return; }
    const v = readoutAt(grid, ll.lng, ll.lat, sst.readout.cols, sst.readout.rows, sst.readout.scale, sst.readout.nodata);
    const lng = ((ll.lng + 540) % 360) - 180;
    const deg = (v: number) => Math.abs(v).toFixed(1).replace(".", ",");
    const pos = `${deg(ll.lat)}°${ll.lat >= 0 ? "N" : "S"} ${deg(lng)}°${lng >= 0 ? "E" : "O"}`;
    el.textContent = v === null ? `${pos} : pas de donnée (terre ou glace)` : `${pos} : anomalie ${signedC(v)} (maille 1°)`;
  });

  // --- Semaine courante ---
  const slider = $<HTMLInputElement>("#slider");
  slider.max = String(Math.max(0, weeks.length - 1));
  function setWeek(i: number) {
    idx = Math.min(Math.max(0, i), weeks.length - 1);
    const w = weeks[idx];
    if (!w) return;
    slider.value = String(idx);
    slider.setAttribute("aria-valuetext", `Semaine ${weekRange(w.start, w.end)}`);
    $("#week-label").textContent = `Semaine ${weekRange(w.start, w.end)}`;
    const badge = $("#week-badge");
    badge.textContent = w.provisional ? "Observé (provisoire)" : "Observé";
    badge.className = `badge observed${w.provisional ? " provisional" : ""}`;
    if (w.hasMap) view.setWeek(w.center);
    chart.setCursor(w.center);
    refreshEvents();
  }
  slider.addEventListener("input", () => { stop(); setWeek(+slider.value); });

  let timer: number | null = null;
  const playBtn = $<HTMLButtonElement>("#play");
  function stop() {
    if (timer !== null) clearInterval(timer);
    timer = null;
    playBtn.textContent = "▶";
    playBtn.setAttribute("aria-label", "Lecture");
  }
  function play() {
    if (idx >= weeks.length - 1) setWeek(0);
    playBtn.textContent = "❚❚";
    playBtn.setAttribute("aria-label", "Pause");
    timer = window.setInterval(() => (idx >= weeks.length - 1 ? stop() : setWeek(idx + 1)), +$<HTMLSelectElement>("#speed").value);
  }
  playBtn.addEventListener("click", () => (timer === null ? play() : stop()));
  $<HTMLSelectElement>("#speed").addEventListener("change", () => { if (timer !== null) { stop(); play(); } });
  document.addEventListener("keydown", (e) => {
    if ((e.target as HTMLElement).closest("input, select, textarea, dialog[open]")) return;
    if (e.key === "ArrowRight") setWeek(idx + 1);
    if (e.key === "ArrowLeft") setWeek(idx - 1);
    if (e.key === " ") { e.preventDefault(); timer === null ? play() : stop(); }
  });

  // --- Méthodologie : vérification ; Sources ---
  if (sst?.validation.weeks_compared) {
    const v = sst.validation;
    $("#validation-text").textContent = `Contrôle automatique : la moyenne de nos anomalies sur la zone Niño-3.4 est comparée chaque semaine à l'indice officiel de la NOAA. Sur ${v.weeks_compared} semaines, l'écart moyen est de ${String(v.mean_abs_diff).replace(".", ",")} °C et l'écart maximal de ${String(v.max_abs_diff).replace(".", ",")} °C.`;
  }
  const src: string[] = [];
  if (sst) src.push(`<li><strong>Températures de surface</strong> : ${sst.source}. Domaine public (données du gouvernement des États-Unis). <a href="${sst.url}" target="_blank" rel="noopener">NOAA PSL</a>. Dernier jour observé : ${frDate(sst.last_obs_day)}.</li>`);
  if (nino) src.push(`<li><strong>Indices</strong> : ${nino.weekly.source} ; ${nino.roni.source}. Domaine public. <a href="${nino.roni.threshold_source}" target="_blank" rel="noopener">Définition du RONI</a>.</li>`);
  if (forecast) src.push(`<li><strong>Prévision</strong> : ${forecast.source}, émise en ${frMonthYear(`${forecast.categories.issued}-01`)}, bulletin du ${frDate(forecast.discussion.date)}. <a href="${forecast.categories.url}" target="_blank" rel="noopener">Probabilités</a> · <a href="${forecast.discussion.url}" target="_blank" rel="noopener">Bulletin</a>.</li>`);
  if (events) src.push(`<li><strong>Événements</strong> : ${events.source}. <a href="${events.terms_url}" target="_blank" rel="noopener">Conditions d'utilisation GDACS</a>.</li>`);
  if (trends) src.push(`<li><strong>Zones de tendance</strong> : ${trends.source}. ${trends.note} <a href="${trends.url}" target="_blank" rel="noopener">Page NOAA</a>.</li>`);
  src.push(`<li><strong>Fond de carte</strong> : Natural Earth (domaine public). Carte : MapLibre GL JS (licence BSD-3).</li>`);
  if (manifest) src.push(`<li class="muted">Dernière collecte : ${frDate(manifest.updated_at)}.</li>`);
  $("#sources-list").innerHTML = src.join("");

  setWeek(idx);
}

main();
