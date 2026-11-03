"""Prévision officielle NOAA CPC : probabilités par saison (catégories ENSO et classes d'intensité du RONI)."""
import html
import re
from datetime import date

from . import config
from .common import fetch_text, now_iso
from .nino import SEASONS

MONTH_NAMES = {m: i + 1 for i, m in enumerate(
    "January February March April May June July August September October November December".split())}

# Classes d'intensité du tableau CPC « strengths », dans l'ordre des colonnes (bornes en °C, None = ouvert).
STRENGTH_BINS = [
    (None, -2.0), (-2.0, -1.5), (-1.5, -1.0), (-1.0, -0.5), (-0.5, 0.5),
    (0.5, 1.0), (1.0, 1.5), (1.5, 2.0), (2.0, None),
]


def _strip(fragment: str) -> str:
    return html.unescape(re.sub(r"<[^>]+>", "", fragment)).strip()


def _clean(page: str) -> str:
    # Les pages CPC laissent d'anciens libellés en commentaire (« <!--Issued April 2026--> ») : à retirer.
    page = re.sub(r"(?s)<!--.*?-->", "", page)
    return re.sub(r"(?s)<(style|script)\b.*?</\1>", "", page)


def parse_issued(page: str) -> tuple[int, int]:
    m = re.search(r"Issued\s+([A-Z][a-z]+)\s+(\d{4})", _clean(page))
    if not m:
        raise ValueError("Date d'émission introuvable")
    return int(m.group(2)), MONTH_NAMES[m.group(1)]


def parse_table(page: str) -> list[tuple[str, list[int]]]:
    """Renvoie [(saison, [probabilités...])] depuis le tableau de données de la page."""
    rows = []
    for tr in re.findall(r"(?s)<tr\b.*?</tr>", _clean(page)):
        cells = [_strip(c) for c in re.findall(r"(?s)<t[hd]\b[^>]*>(.*?)</t[hd]>", tr)]
        if not cells or not cells[0][:3] in SEASONS:
            continue
        rows.append((cells[0][:3], [int(c) for c in cells[1:] if c != ""]))
    if not rows:
        raise ValueError("Tableau de probabilités introuvable")
    return rows


def season_centers(seasons: list[str], issued: tuple[int, int]) -> list[date]:
    """Les saisons sont consécutives à partir du mois d'émission (ou juste avant)."""
    year, issue_month = issued
    out = []
    prev = None
    for s in seasons:
        m = SEASONS.index(s) + 1
        if prev is None:
            if m - issue_month > 6:
                year -= 1
            elif issue_month - m > 6:
                year += 1
        elif m < prev:
            year += 1
        out.append(date(year, m, 15))
        prev = m
    return out


def _check_sum(season: str, probs: list[int]) -> None:
    if not 98 <= sum(probs) <= 102:
        raise ValueError(f"Probabilités incohérentes pour {season} : {probs} (somme {sum(probs)})")


def parse_categories(page: str) -> dict:
    issued = parse_issued(page)
    rows = parse_table(page)
    centers = season_centers([s for s, _ in rows], issued)
    data = []
    for (season, probs), c in zip(rows, centers):
        if len(probs) != 3:
            raise ValueError(f"3 colonnes attendues pour {season}, reçu {probs}")
        _check_sum(season, probs)
        data.append({"season": season, "center": c.isoformat(),
                     "la_nina": probs[0], "neutral": probs[1], "el_nino": probs[2]})
    return {"issued": f"{issued[0]}-{issued[1]:02d}", "data": data}


def parse_strengths(page: str) -> dict:
    issued = parse_issued(page)
    rows = parse_table(page)
    centers = season_centers([s for s, _ in rows], issued)
    data = []
    for (season, probs), c in zip(rows, centers):
        if len(probs) != len(STRENGTH_BINS):
            raise ValueError(f"{len(STRENGTH_BINS)} colonnes attendues pour {season}, reçu {probs}")
        _check_sum(season, probs)
        data.append({"season": season, "center": c.isoformat(),
                     "bins": [{"lo": lo, "hi": hi, "p": p} for (lo, hi), p in zip(STRENGTH_BINS, probs)]})
    return {"issued": f"{issued[0]}-{issued[1]:02d}", "data": data}


def parse_discussion(page: str) -> dict:
    text = _strip(_clean(page))
    text = re.sub(r"\s+", " ", text)
    m_date = re.search(r"CLIMATE PREDICTION CENTER/NCEP/NWS\s+(\d{1,2}) ([A-Z][a-z]+) (\d{4})", text)
    m_status = re.search(r"ENSO Alert System Status:\s*(.+?)\s+Synopsis:", text)
    m_syn = re.search(r"Synopsis:\s*(.+?\.)\s", text)
    if not (m_date and m_status):
        raise ValueError("Bulletin CPC : date ou statut introuvable")
    d = date(int(m_date.group(3)), MONTH_NAMES[m_date.group(2)], int(m_date.group(1)))
    return {"date": d.isoformat(), "status": m_status.group(1).strip(),
            "synopsis_en": m_syn.group(1).strip() if m_syn else None}


def archive_urls(start: date, today: date) -> list[str]:
    """Bulletins mensuels archivés du mois de départ au mois courant (format CPC : enso_disc_oct2026)."""
    urls = []
    y, m = start.year, start.month
    while (y, m) <= (today.year, today.month):
        mon = date(y, m, 1).strftime("%b").lower()
        urls.append(f"{config.CPC_ROOT}/enso_disc_{mon}{y}/ensodisc.html")
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    return urls


def status_history(start: date, today: date) -> list[dict]:
    out = []
    for url in archive_urls(start, today):
        try:
            d = parse_discussion(fetch_text(url, retries=1))
        except Exception:  # bulletin du mois pas encore publié
            continue
        out.append({"date": d["date"], "status": d["status"], "url": url})
    return out


def collect() -> dict:
    start = date.fromisoformat(config.START_DATE)
    return {
        "status_history": status_history(start, date.today()),
        "retrieved_at": now_iso(),
        "source": "NOAA Climate Prediction Center, probabilités ENSO officielles (basées sur le RONI)",
        "categories": {**parse_categories(fetch_text(config.CPC_PROBS_URL)), "url": config.CPC_PROBS_URL},
        "strengths": {**parse_strengths(fetch_text(config.CPC_STRENGTHS_URL)), "url": config.CPC_STRENGTHS_URL},
        "discussion": {**parse_discussion(fetch_text(config.CPC_DISCUSSION_URL)), "url": config.CPC_DISCUSSION_URL},
    }
