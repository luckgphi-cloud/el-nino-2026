import { bisector, max as d3max, min as d3min } from "d3-array";
import { axisBottom, axisLeft } from "d3-axis";
import { scaleLinear, scaleUtc } from "d3-scale";
import { select } from "d3-selection";
import { line } from "d3-shape";
import { utcMonth } from "d3-time";
import type { ForecastData, NinoData } from "./data";
import { addDays, frDate, parseISO, SEASON_FR, signedC } from "./format";

const MONTH_ABBR = ["janv.", "févr.", "mars", "avr.", "mai", "juin", "juil.", "août", "sept.", "oct.", "nov.", "déc."];
const STATUS_FR: Record<string, string> = {
  "La Niña Advisory": "La Niña",
  "La Niña Advisory / El Niño Watch": "La Niña · veille El Niño",
  "Final La Niña Advisory / El Niño Watch": "Neutre · veille El Niño",
  "El Niño Watch": "Veille El Niño",
  "El Niño Advisory": "El Niño",
  "Final El Niño Advisory": "Fin d'El Niño",
  "Not Active": "Neutre",
};

export function statusFr(s: string): string {
  return STATUS_FR[s] ?? s;
}

export interface ChartOptions {
  container: HTMLElement;
  nino: NinoData | null;
  forecast: ForecastData | null;
  start: string;
  onPick: (isoDate: string) => void;
}

export function createChart(opts: ChartOptions) {
  const { container, nino, forecast } = opts;
  const svg = select(container).append("svg").attr("class", "chart-svg").attr("role", "img")
    .attr("aria-label", "Courbe de l'indice Niño-3.4 hebdomadaire, du RONI et de la prévision NOAA");
  let current: string | null = null;

  const weekly = nino?.weekly.data ?? [];
  const roni = nino?.roni.data ?? [];
  const strengths = forecast?.strengths.data ?? [];
  const cats = new Map((forecast?.categories.data ?? []).map((c) => [c.season + c.center, c]));
  const lastObs = weekly.length ? weekly[weekly.length - 1].week_center : opts.start;
  const end = strengths.length ? addDays(strengths[strengths.length - 1].center, 50) : addDays(lastObs, 30);

  function draw() {
    const W = container.clientWidth || 800;
    const H = container.clientHeight || 220;
    const m = { top: 34, right: 14, bottom: 34, left: 40 };
    const narrow = W < 600;
    svg.attr("viewBox", `0 0 ${W} ${H}`).attr("width", W).attr("height", H);
    svg.selectAll("*").remove();

    const x = scaleUtc().domain([parseISO(opts.start), parseISO(end)]).range([m.left, W - m.right]);
    const vals = [...weekly.map((d) => d.nino34_anom), ...roni.map((d) => d.value)];
    const y = scaleLinear()
      .domain([Math.min(-1.5, (d3min(vals) ?? 0) - 0.3), Math.max(3.5, (d3max(vals) ?? 0) + 0.4)])
      .nice().range([H - m.bottom, m.top]);

    const defs = svg.append("defs");
    defs.append("pattern").attr("id", "fc-hatch").attr("width", 6).attr("height", 6)
      .attr("patternUnits", "userSpaceOnUse").attr("patternTransform", "rotate(45)")
      .append("line").attr("x1", 0).attr("y1", 0).attr("x2", 0).attr("y2", 6).attr("class", "fc-hatch-line");

    // Zone de prévision
    if (strengths.length) {
      // La zone hachurée commence après la dernière semaine observée ; les barres restent à leur saison.
      const x0 = x(parseISO(addDays(lastObs, 4)));
      const fz = svg.append("g").attr("class", "forecast-zone");
      fz.append("rect").attr("x", x0).attr("y", m.top).attr("width", W - m.right - x0).attr("height", H - m.top - m.bottom)
        .attr("fill", "url(#fc-hatch)").attr("class", "fc-bg");
      fz.append("text").attr("x", x0 + 4).attr("y", m.top - 6).attr("class", "fc-label")
        .text(narrow ? "PRÉVISION NOAA" : `PRÉVISION NOAA CPC · émise le ${forecast ? frDate(forecast.discussion.date) : "?"}`);
      const top = y.domain()[1];
      const bot = y.domain()[0];
      const halfW = Math.max(6, (x(parseISO(addDays(opts.start, 30))) - x(parseISO(opts.start))) * 0.42);
      for (const sres of strengths) {
        const cx = x(parseISO(sres.center));
        for (const b of sres.bins) {
          if (b.p <= 0) continue;
          const lo = Math.max(b.lo ?? bot, bot);
          const hi = Math.min(b.hi ?? top, top);
          const g = fz.append("g").attr("class", "fc-bin");
          g.append("rect").attr("x", cx - halfW).attr("width", halfW * 2).attr("y", y(hi)).attr("height", Math.max(1, y(lo) - y(hi)))
            .attr("fill-opacity", 0.12 + 0.8 * (b.p / 100));
          if (b.p >= 15 && halfW >= 11) {
            g.append("text").attr("x", cx).attr("y", (y(lo) + y(hi)) / 2 + 3.5).attr("class", "fc-p")
              .text(`${b.p}%`);
          }
          g.append("title").text(`${SEASON_FR[sres.season] ?? sres.season} : ${b.p} % de chances que le RONI soit ${
            b.lo === null ? `≤ ${b.hi}` : b.hi === null ? `≥ ${b.lo}` : `entre ${b.lo} et ${b.hi}`} °C`);
        }
        const c = cats.get(sres.season + sres.center);
        if (c && !narrow) {
          fz.append("text").attr("x", cx).attr("y", H - 3).attr("class", "fc-cat").text(`${c.el_nino}%`)
            .append("title").text(`${SEASON_FR[c.season] ?? c.season} : El Niño ${c.el_nino} %, neutre ${c.neutral} %, La Niña ${c.la_nina} %`);
        }
      }
    }

    // Axes
    svg.append("g").attr("class", "axis").attr("transform", `translate(0,${H - m.bottom})`)
      .call(axisBottom(x).ticks(utcMonth.every(W < 600 ? 3 : W < 1000 ? 2 : 1)).tickFormat((d) => {
        const dt = d as Date;
        return dt.getUTCMonth() === 0 ? String(dt.getUTCFullYear()) : MONTH_ABBR[dt.getUTCMonth()];
      }));
    svg.append("g").attr("class", "axis").attr("transform", `translate(${m.left},0)`)
      .call(axisLeft(y).ticks(6).tickFormat((d) => `${(+d).toLocaleString("fr-FR")}°`));

    // Seuils (rattachés au RONI)
    const thr = nino?.roni.threshold_el_nino ?? 0.5;
    const thrLa = nino?.roni.threshold_la_nina ?? -0.5;
    svg.append("line").attr("class", "zero").attr("x1", m.left).attr("x2", W - m.right).attr("y1", y(0)).attr("y2", y(0));
    for (const [v, label] of [[thr, "Seuil El Niño : RONI > +0,5 °C"], [thrLa, "Seuil La Niña : RONI < −0,5 °C"]] as const) {
      svg.append("line").attr("class", "threshold").attr("x1", m.left).attr("x2", W - m.right).attr("y1", y(v)).attr("y2", y(v));
      svg.append("text").attr("class", "threshold-label").attr("x", m.left + 4).attr("y", y(v) + (v > 0 ? -4 : 11)).text(label);
    }

    // Indice hebdomadaire
    const lw = line<{ week_center: string; nino34_anom: number }>()
      .x((d) => x(parseISO(d.week_center))).y((d) => y(d.nino34_anom));
    svg.append("path").attr("class", "weekly").attr("d", lw(weekly) ?? "");

    // RONI (moyenne 3 mois) avec marqueurs carrés ; valeurs provisoires creuses
    const lr = line<{ center: string; value: number }>().x((d) => x(parseISO(d.center))).y((d) => y(d.value));
    svg.append("path").attr("class", "roni").attr("d", lr(roni) ?? "");
    svg.selectAll("rect.roni-pt").data(roni).join("rect")
      .attr("class", (d) => `roni-pt${d.provisional ? " provisional" : ""}`)
      .attr("x", (d) => x(parseISO(d.center)) - 3.5).attr("y", (d) => y(d.value) - 3.5).attr("width", 7).attr("height", 7)
      .append("title").text((d) => `RONI ${d.season} ${d.year} : ${signedC(d.value, 2)}${d.provisional ? " (provisoire)" : ""}`);

    // Statut officiel CPC, mois par mois
    const hist = forecast?.status_history ?? [];
    hist.forEach((h, i) => {
      const x0 = Math.max(m.left, x(parseISO(h.date)));
      const next = hist[i + 1]?.date ?? (forecast ? addDays(forecast.discussion.date, 35) : h.date);
      const x1 = Math.min(W - m.right, x(parseISO(next)));
      if (x1 <= x0) return;
      const cls = /El Niño Advisory/.test(h.status) && !/Final/.test(h.status) ? "st-nino" : /La Niña Advisory/.test(h.status) && !/Final/.test(h.status) ? "st-nina" : "st-neutral";
      const g = svg.append("g").attr("class", `status ${cls}`);
      g.append("rect").attr("x", x0).attr("y", 2).attr("width", x1 - x0 - 1).attr("height", 12);
      if (x1 - x0 > 52) g.append("text").attr("x", x0 + 3).attr("y", 11).text(statusFr(h.status));
      g.append("title").text(`Statut NOAA au ${frDate(h.date)} : ${h.status}`);
    });

    // Curseur
    if (current) {
      const cx = x(parseISO(current));
      svg.append("line").attr("class", "cursor").attr("x1", cx).attr("x2", cx).attr("y1", m.top).attr("y2", H - m.bottom);
      const i = bisector((d: { week_center: string }) => d.week_center).left(weekly, current);
      const wv = weekly[i]?.week_center === current ? weekly[i] : null;
      if (wv) {
        svg.append("circle").attr("class", "cursor-dot").attr("cx", cx).attr("cy", y(wv.nino34_anom)).attr("r", 4);
        const right = cx > W - 150;
        svg.append("text").attr("class", "cursor-label").attr("text-anchor", right ? "end" : "start")
          .attr("x", cx + (right ? -6 : 6)).attr("y", y(wv.nino34_anom) - 7).text(`Niño-3.4 ${signedC(wv.nino34_anom)}`);
      }
    }

    // Clic = choisir une semaine
    svg.append("rect").attr("class", "hit").attr("x", m.left).attr("y", m.top).attr("width", Math.max(0, x(parseISO(lastObs)) - m.left + 4))
      .attr("height", H - m.top - m.bottom)
      .on("click", (ev: MouseEvent) => {
        const pt = (ev.currentTarget as SVGRectElement).ownerSVGElement!.getBoundingClientRect();
        const px = ((ev.clientX - pt.left) / pt.width) * W;
        opts.onPick(x.invert(px).toISOString().slice(0, 10));
      });
  }

  new ResizeObserver(() => draw()).observe(container);
  draw();
  return {
    setCursor(week: string) {
      current = week;
      draw();
    },
  };
}
