import { describe, expect, it } from "vitest";
import { readoutAt, type ClimateEvent } from "./data";
import { eventCard, filterEvents } from "./events";
import { addDays, frDate, signedC, weekRange } from "./format";

// FIXTURE_ : événements de test construits à la main, pas des données réelles.
const FIXTURE_EVENTS: ClimateEvent[] = [
  { id: "a", type: "fire", name: "FIXTURE feu", from: "2026-10-20T00:00:00", to: "2026-10-26T00:00:00", lon: 0, lat: 0, level: "Orange", severity: null, country: null, url: null, magnitude: 60000, magnitude_unit: "ha", intensity: "extreme" },
  { id: "b", type: "flood", name: "FIXTURE crue", from: "2026-03-01T00:00:00", to: "2026-03-05T00:00:00", lon: 0, lat: 0, level: "Red", severity: "x", country: "Y", url: "https://example.org/?a=1&b=2", magnitude: null, magnitude_unit: "km²", intensity: null },
  { id: "c", type: "drought", name: "FIXTURE sécheresse", from: "2022-09-21T00:00:00", to: "2026-11-01T00:00:00", lon: 0, lat: 0, level: "Green", severity: null, country: null, url: null, magnitude: 150000, magnitude_unit: "km²", intensity: "moderate" },
];

const base = {
  types: new Set(["fire", "flood", "cyclone", "drought"] as const),
  intensities: new Set(["extreme", "strong", "moderate", "unknown"] as const),
  weekStart: "2026-10-25",
  weekEnd: "2026-10-31",
  periodStart: "2025-12-28",
};

describe("filterEvents", () => {
  it("garde les événements actifs pendant la semaine (chevauchement)", () => {
    const r = filterEvents(FIXTURE_EVENTS, { ...base, types: new Set(base.types), intensities: new Set(base.intensities), mode: "week" });
    expect(r.map((e) => e.id)).toEqual(["a", "c"]);
  });
  it("cumul depuis le début de la période", () => {
    const r = filterEvents(FIXTURE_EVENTS, { ...base, types: new Set(base.types), intensities: new Set(base.intensities), mode: "cumulative" });
    expect(r.map((e) => e.id)).toEqual(["a", "b", "c"]);
  });
  it("applique les filtres de type et d'intensité (non mesurée = « unknown »)", () => {
    const r = filterEvents(FIXTURE_EVENTS, { ...base, types: new Set(["fire", "flood", "drought"] as const), intensities: new Set(["extreme", "unknown"] as const), mode: "cumulative" });
    expect(r.map((e) => e.id)).toEqual(["a", "b"]);
  });
  it("l'intensité ne dépend pas du niveau d'alerte GDACS", () => {
    const r = filterEvents(FIXTURE_EVENTS, { ...base, types: new Set(base.types), intensities: new Set(["moderate"] as const), mode: "cumulative" });
    expect(r.map((e) => e.id)).toEqual(["c"]);
  });
  it("n'affiche pas un événement futur par rapport à la semaine", () => {
    const r = filterEvents(FIXTURE_EVENTS, { ...base, types: new Set(base.types), intensities: new Set(base.intensities), weekStart: "2026-02-01", weekEnd: "2026-02-07", mode: "cumulative" });
    expect(r.map((e) => e.id)).toEqual(["c"]);
  });
});

describe("eventCard", () => {
  it("échappe le HTML et affiche la mesure physique", () => {
    const html = eventCard({ ...FIXTURE_EVENTS[0], name: "<b>x</b>" });
    expect(html).toContain("&lt;b&gt;x&lt;/b&gt;");
    expect(html).toContain("Extrême");
    expect(html).toMatch(/surface brûlée : 60\s000 ha/);
    expect(html).not.toMatch(/caus[ée] par El Ni/);
  });
  it("signale une mesure absente", () => {
    expect(eventCard(FIXTURE_EVENTS[1])).toContain("mesure physique indisponible");
  });
  it("échappe l'URL", () => {
    expect(eventCard(FIXTURE_EVENTS[1])).toContain("a=1&amp;b=2");
  });
});

describe("format", () => {
  it("dates françaises", () => {
    expect(frDate("2026-10-28")).toBe("28 oct. 2026");
    expect(weekRange("2026-10-25", "2026-10-31")).toBe("du 25 au 31 oct. 2026");
    expect(weekRange("2025-12-28", "2026-01-03")).toBe("du 28 déc. 2025 au 3 janv. 2026");
    expect(weekRange("2026-09-27", "2026-10-03")).toBe("du 27 sept. au 3 oct. 2026");
    expect(addDays("2026-12-30", 3)).toBe("2027-01-02");
  });
  it("températures signées", () => {
    expect(signedC(3.4)).toBe("+3,4 °C");
    expect(signedC(-0.04, 2)).toBe("−0,04 °C");
    expect(signedC(null)).toBe("indisponible");
  });
});

describe("readoutAt", () => {
  it("indexe la grille 1° depuis le nord-ouest", () => {
    const g = new Int8Array(180 * 360).fill(-128);
    g[0] = 12; // 89-90°N, 180-179°O
    g[90 * 360 + 30] = -5; // 0..-1°N... ligne 90 = 0°-1°S, colonne 30 = 150-149°O
    expect(readoutAt(g, -179.5, 89.5)).toBeCloseTo(1.2);
    expect(readoutAt(g, -149.5, -0.5)).toBeCloseTo(-0.5);
    expect(readoutAt(g, 10, 45)).toBeNull();
    expect(readoutAt(g, 180.5, 89.5)).toBeCloseTo(1.2); // longitude repliée
  });
});
