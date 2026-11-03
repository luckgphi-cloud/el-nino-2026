"""Indices Niño-3.4 : hebdomadaire (CPC, OISST, base 1991-2020), RONI et ONI (moyennes 3 mois, ERSSTv6)."""
import re
from datetime import date, datetime, timedelta

from . import config
from .common import fetch_text, now_iso

MONTHS = {m: i + 1 for i, m in enumerate("JAN FEB MAR APR MAY JUN JUL AUG SEP OCT NOV DEC".split())}
SEASONS = ["DJF", "JFM", "FMA", "MAM", "AMJ", "MJJ", "JJA", "JAS", "ASO", "SON", "OND", "NDJ"]
_NUM = re.compile(r"-?\d+\.\d")
_WEEK = re.compile(r"^\s*(\d{2})([A-Z]{3})(\d{4})\s+(.*)$")


def parse_weekly(text: str) -> list[dict]:
    """Lit wksst9120.for. Les colonnes peuvent être collées ("20.6-0.1") : on extrait les nombres par regex."""
    rows = []
    for line in text.splitlines():
        m = _WEEK.match(line)
        if not m:
            continue
        nums = [float(x) for x in _NUM.findall(m.group(4))]
        if len(nums) != 8:
            raise ValueError(f"Ligne hebdo inattendue : {line!r}")
        d = date(int(m.group(3)), MONTHS[m.group(2)], int(m.group(1)))
        rows.append({"week_center": d.isoformat(), "nino34_sst": nums[4], "nino34_anom": nums[5]})
    return rows


def season_center(season: str, year: int) -> date:
    """Milieu de la saison de 3 mois. Dans les fichiers CPC, « DJF 2026 » = déc. 2025–fév. 2026 : le mois
    central appartient toujours à l'année indiquée."""
    return date(year, SEASONS.index(season) + 1, 15)


def parse_seasonal(text: str, value_col: int) -> list[dict]:
    rows = []
    for line in text.splitlines():
        parts = line.split()
        if len(parts) < 3 or parts[0] not in SEASONS:
            continue
        season, year = parts[0], int(parts[1])
        rows.append({
            "season": season,
            "year": year,
            "center": season_center(season, year).isoformat(),
            "value": float(parts[value_col]),
        })
    return rows


def week_center_for(d: date) -> date:
    """Mercredi (centre de semaine CPC) de la semaine dim.–sam. qui contient d."""
    sunday = d - timedelta(days=(d.weekday() + 1) % 7)
    return sunday + timedelta(days=3)


def collect() -> dict:
    start = datetime.strptime(config.START_DATE, "%Y-%m-%d").date()
    first_week = week_center_for(start)
    weekly = [r for r in parse_weekly(fetch_text(config.NINO_WEEKLY_URL)) if r["week_center"] >= first_week.isoformat()]
    # Saisons : on garde aussi celles centrées un mois avant le départ, pour que la courbe ne démarre pas à vide.
    season_min = (start - timedelta(days=45)).isoformat()
    roni = [r for r in parse_seasonal(fetch_text(config.RONI_URL), 2) if r["center"] >= season_min]
    oni = [r for r in parse_seasonal(fetch_text(config.ONI_URL), 3) if r["center"] >= season_min]
    # Le CPC indique que les deux dernières valeurs RONI peuvent encore être révisées.
    for r in roni[-2:]:
        r["provisional"] = True
    return {
        "retrieved_at": now_iso(),
        "weekly": {
            "source": "NOAA CPC, indice Niño-3.4 hebdomadaire (OISST v2.1, base 1991-2020)",
            "url": config.NINO_WEEKLY_URL,
            "data": weekly,
        },
        "roni": {
            "source": "NOAA CPC, Relative Oceanic Niño Index (ERSSTv6, base 1991-2020)",
            "url": config.RONI_URL,
            "threshold_el_nino": 0.5,
            "threshold_la_nina": -0.5,
            "threshold_source": "https://www.cpc.ncep.noaa.gov/products/analysis_monitoring/enso/roni/",
            "data": roni,
        },
        "oni": {
            "source": "NOAA CPC, Oceanic Niño Index (ERSST)",
            "url": config.ONI_URL,
            "data": oni,
        },
    }
