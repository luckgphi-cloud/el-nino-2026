// Formatage français (dates en UTC, virgule décimale).

const MONTHS_SHORT = ["janv.", "févr.", "mars", "avr.", "mai", "juin", "juil.", "août", "sept.", "oct.", "nov.", "déc."];
const MONTHS_LONG = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre", "novembre", "décembre"];

export function parseISO(iso: string): Date {
  return new Date(`${iso.slice(0, 10)}T00:00:00Z`);
}

export function frDate(iso: string, long = false): string {
  const d = parseISO(iso);
  const months = long ? MONTHS_LONG : MONTHS_SHORT;
  return `${d.getUTCDate()} ${months[d.getUTCMonth()]} ${d.getUTCFullYear()}`;
}

export function frMonthYear(iso: string): string {
  const d = parseISO(iso);
  return `${MONTHS_LONG[d.getUTCMonth()]} ${d.getUTCFullYear()}`;
}

/** « du 25 au 31 oct. 2026 », « du 28 déc. 2025 au 3 janv. 2026 » */
export function weekRange(start: string, end: string): string {
  const a = parseISO(start);
  const b = parseISO(end);
  if (a.getUTCFullYear() !== b.getUTCFullYear()) return `du ${frDate(start)} au ${frDate(end)}`;
  if (a.getUTCMonth() !== b.getUTCMonth()) {
    return `du ${a.getUTCDate()} ${MONTHS_SHORT[a.getUTCMonth()]} au ${frDate(end)}`;
  }
  return `du ${a.getUTCDate()} au ${frDate(end)}`;
}

export function signedC(v: number | null | undefined, digits = 1): string {
  if (v === null || v === undefined || Number.isNaN(v)) return "indisponible";
  const s = Math.abs(v).toFixed(digits).replace(".", ",");
  const sign = v > 0 ? "+" : v < 0 ? "−" : "";
  return `${sign}${s} °C`;
}

export function addDays(iso: string, days: number): string {
  const d = parseISO(iso);
  d.setUTCDate(d.getUTCDate() + days);
  return d.toISOString().slice(0, 10);
}

export const SEASON_FR: Record<string, string> = {
  DJF: "déc.–févr.", JFM: "janv.–mars", FMA: "févr.–avr.", MAM: "mars–mai", AMJ: "avr.–juin", MJJ: "mai–juil.",
  JJA: "juin–août", JAS: "juil.–sept.", ASO: "août–oct.", SON: "sept.–nov.", OND: "oct.–déc.", NDJ: "nov.–janv.",
};
