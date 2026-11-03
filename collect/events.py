"""Événements extrêmes GDACS : inondations (FL), cyclones tropicaux (TC), sécheresses (DR), feux de forêt (WF).
Séismes, tsunamis et volcans sont exclus (pas de lien climatique).

Intensité : classée sur une mesure PHYSIQUE (vent, surface brûlée, surface touchée), avec les mêmes seuils
partout dans le monde. L'alerte GDACS (qui intègre la population exposée et la capacité du pays à faire face)
est conservée comme information secondaire, mais ne sert pas au classement.
"""
import json
import math
import re
import time
from datetime import datetime, timezone

from . import config
from .common import fetch, now_iso, write_json

TYPES = {"WF": "fire", "FL": "flood", "TC": "cyclone", "DR": "drought"}
LEVELS = ("Green", "Orange", "Red")
PAGE_SIZE = 100  # taille de page imposée par l'API
EARTH_R_KM = 6371.0

# Seuils d'intensité : (borne « forte », borne « extrême »), dans l'unité de la mesure.
# Cyclones : échelle de Saffir-Simpson (catégorie 1 dès 119 km/h, catégorie 3 « majeur » dès 178 km/h).
# Feux, sécheresses, inondations : seuils ronds choisis d'après la répartition 2026 (voir METHODOLOGIE.md).
THRESHOLDS = {
    "cyclone": (119.0, 178.0),
    "fire": (40_000.0, 100_000.0),  # GDACS ne recense déjà que de grands feux (médiane ≈ 7 500 ha)
    "drought": (200_000.0, 1_000_000.0),
    "flood": (10_000.0, 100_000.0),  # 2026 : médiane ≈ 190 km², ~1/5 au-dessus de 10 000, ~7 % au-dessus de 100 000
}
UNITS = {"cyclone": "km/h", "fire": "ha", "drought": "km²", "flood": "km²"}
MEASURES = {"cyclone": "vent maximal", "fire": "surface brûlée", "drought": "surface touchée", "flood": "surface de la zone touchée (estimation)"}
_PATTERNS = {
    "cyclone": re.compile(r"wind speed of ([0-9.]+) km/h"),
    "fire": re.compile(r"in ([0-9.]+) ha"),
    "drought": re.compile(r"in ([0-9.]+) km2"),
}


def magnitude_from_severity(etype: str, severity: str | None) -> float | None:
    """Mesure physique lue dans le texte de sévérité GDACS (None si absente)."""
    pat = _PATTERNS.get(etype)
    m = pat.search(severity or "") if pat else None
    return float(m.group(1)) if m else None


def intensity_class(etype: str, magnitude: float | None) -> str | None:
    if magnitude is None:
        return None
    strong, extreme = THRESHOLDS[etype]
    return "extreme" if magnitude >= extreme else "strong" if magnitude >= strong else "moderate"


def ring_area_km2(ring: list) -> float:
    """Aire d'un anneau lon/lat (projection sinusoïdale, à surface égale), en km²."""
    if len(ring) < 4:
        return 0.0
    pts = [(math.radians(x) * EARTH_R_KM * math.cos(math.radians(y)), math.radians(y) * EARTH_R_KM) for x, y in ring]
    s = sum(x1 * y2 - x2 * y1 for (x1, y1), (x2, y2) in zip(pts, pts[1:] + pts[:1]))
    return abs(s) / 2


def geometry_area_km2(geom: dict) -> float:
    polys = [geom["coordinates"]] if geom["type"] == "Polygon" else geom["coordinates"] if geom["type"] == "MultiPolygon" else []
    return sum(ring_area_km2(p[0]) - sum(ring_area_km2(h) for h in p[1:]) for p in polys)


def affected_area_km2(fc: dict) -> float | None:
    """Surface des polygones « Affected area » d'une réponse getgeometry GDACS (None s'il n'y en a pas)."""
    polys = [f["geometry"] for f in fc.get("features", [])
             if (f.get("properties") or {}).get("Class") == "Poly_Affected" and f.get("geometry")]
    if not polys:
        return None
    area = round(sum(geometry_area_km2(g) for g in polys), 1)
    return area if area > 0 else None  # polygone dégénéré : pas de mesure


def flood_area(e: dict) -> float | None:
    """Surface inondée estimée d'un événement, avec cache par (événement, épisode)."""
    url = e.get("_geom_url")
    if not url:
        return None
    key = re.sub(r"[^0-9A-Za-z]+", "_", url.split("?")[-1])
    path = config.CACHE_DIR / "gdacs_fl" / f"{key}.json"
    if path.exists():
        return json.loads(path.read_text())["area_km2"]
    try:
        area = affected_area_km2(fetch(url, timeout=120, retries=2).json())
    except Exception:
        return None  # pas mis en cache : nouvel essai à la prochaine collecte
    time.sleep(0.5)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"area_km2": area}))
    return area


def normalize(feature: dict) -> dict | None:
    p = feature.get("properties") or {}
    g = feature.get("geometry") or {}
    etype = TYPES.get(p.get("eventtype"))
    if etype is None or g.get("type") != "Point" or p.get("alertlevel") not in LEVELS:
        return None
    lon, lat = g["coordinates"][:2]
    sev = (p.get("severitydata") or {}).get("severitytext")
    country = (p.get("country") or "").strip(" ,") or None
    if country:
        country = ", ".join(c.strip() for c in country.split(",") if c.strip())
    return {
        "id": f"{p['eventtype']}-{p['eventid']}",
        "type": etype,
        "name": p.get("name") or p.get("eventname") or "Sans nom",
        "from": p["fromdate"],
        "to": p.get("todate") or p["fromdate"],
        "lon": round(float(lon), 3),
        "lat": round(float(lat), 3),
        "level": p["alertlevel"],
        "severity": sev.strip() if sev and sev.strip() else None,
        "country": country,
        "url": (p.get("url") or {}).get("report"),
        "_geom_url": (p.get("url") or {}).get("geometry"),
        "_modified": p.get("datemodified") or "",
    }


def dedupe(events: list[dict]) -> list[dict]:
    """Un événement peut revenir sur plusieurs pages / épisodes : on garde la version la plus récente."""
    best: dict[str, dict] = {}
    for e in events:
        if e["id"] not in best or e["_modified"] > best[e["id"]]["_modified"]:
            best[e["id"]] = e
    out = sorted(best.values(), key=lambda e: (e["from"], e["id"]))
    for e in out:
        e.pop("_modified", None)
    return out


def add_intensity(events: list[dict], area_fn=flood_area) -> list[dict]:
    for e in events:
        mag = area_fn(e) if e["type"] == "flood" else magnitude_from_severity(e["type"], e["severity"])
        e["magnitude"] = mag
        e["magnitude_unit"] = UNITS[e["type"]]
        e["intensity"] = intensity_class(e["type"], mag)
        e.pop("_geom_url", None)
    return events


def search_url(code: str, date_from: str, date_to: str, page: int) -> str:
    # Les « ; » doivent rester littéraux : encodés (%3B), l'API répond 400.
    return (f"{config.GDACS_EVENTS_URL}?eventlist={code}&fromdate={date_from}&todate={date_to}"
            f"&alertlevel={';'.join(LEVELS)}&pagenumber={page}")


def fetch_type(code: str, date_from: str, date_to: str, max_pages: int = 300) -> list[dict]:
    """Pagine jusqu'à une page incomplète, ou une page sans événement nouveau (garde-fou)."""
    feats, seen = [], set()
    for page in range(1, max_pages + 1):
        r = fetch(search_url(code, date_from, date_to, page), timeout=180)
        batch = r.json().get("features", []) if r.content else []
        ids = {(f.get("properties") or {}).get("eventid") for f in batch}
        if batch and ids <= seen:
            break
        seen |= ids
        feats += batch
        if len(batch) < PAGE_SIZE:
            break
    else:
        raise RuntimeError(f"GDACS {code} : plus de {max_pages} pages")
    return feats


def split_by_intensity(events: list[dict]) -> tuple[list[dict], list[dict]]:
    """Fortes, extrêmes et non mesurées (chargées à l'ouverture) ; modérées (chargées à la demande : surtout des
    milliers de petits feux)."""
    main = [e for e in events if e["intensity"] != "moderate"]
    moderate = [e for e in events if e["intensity"] == "moderate"]
    return main, moderate


def collect() -> None:
    today = datetime.now(timezone.utc).date().isoformat()
    events = []
    for code in TYPES:
        raw = fetch_type(code, config.START_DATE, today)
        norm = [e for e in (normalize(f) for f in raw) if e]
        print(f"  GDACS {code} : {len(raw)} reçus, {len(norm)} retenus")
        events += norm
    events = add_intensity(dedupe(events))
    missing = sum(1 for e in events if e["intensity"] is None)
    print(f"  intensité non mesurée : {missing} événement(s)")
    main, moderate = split_by_intensity(events)
    meta = {
        "retrieved_at": now_iso(),
        "source": "GDACS — Global Disaster Alert and Coordination System (ONU OCHA, UNOSAT, Commission européenne JRC/ECHO)",
        "url": "https://www.gdacs.org/",
        "terms_url": "https://www.gdacs.org/About/termofuse.aspx",
        "period": {"from": config.START_DATE, "to": today},
        "intensity": {"thresholds": {k: list(v) for k, v in THRESHOLDS.items()}, "units": UNITS, "measures": MEASURES},
    }
    write_json(config.DATA_DIR / "events.json", {**meta, "intensities": ["strong", "extreme", None], "events": main})
    write_json(config.DATA_DIR / "events_moderate.json", {**meta, "intensities": ["moderate"], "events": moderate})
    old = config.DATA_DIR / "events_green.json"
    if old.exists():
        old.unlink()  # ancien découpage par niveau d'alerte
