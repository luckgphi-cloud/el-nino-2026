"""Événements extrêmes GDACS : inondations (FL), cyclones tropicaux (TC), sécheresses (DR), feux de forêt (WF).
Séismes, tsunamis et volcans sont exclus (pas de lien climatique). Même critère pour le monde entier."""
from datetime import datetime, timezone

from . import config
from .common import fetch, now_iso, write_json

TYPES = {"WF": "fire", "FL": "flood", "TC": "cyclone", "DR": "drought"}
LEVELS = ("Green", "Orange", "Red")
PAGE_SIZE = 100  # taille de page imposée par l'API


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


def split_by_level(events: list[dict]) -> tuple[list[dict], list[dict]]:
    """Orange/rouge (chargés à l'ouverture) et vert (chargés à la demande : plusieurs milliers de petits feux)."""
    major = [e for e in events if e["level"] in ("Orange", "Red")]
    green = [e for e in events if e["level"] == "Green"]
    return major, green


def collect() -> None:
    today = datetime.now(timezone.utc).date().isoformat()
    events = []
    for code in TYPES:
        raw = fetch_type(code, config.START_DATE, today)
        norm = [e for e in (normalize(f) for f in raw) if e]
        print(f"  GDACS {code} : {len(raw)} reçus, {len(norm)} retenus")
        events += norm
    major, green = split_by_level(dedupe(events))
    meta = {
        "retrieved_at": now_iso(),
        "source": "GDACS — Global Disaster Alert and Coordination System (ONU OCHA, UNOSAT, Commission européenne JRC/ECHO)",
        "url": "https://www.gdacs.org/",
        "terms_url": "https://www.gdacs.org/About/termofuse.aspx",
        "period": {"from": config.START_DATE, "to": today},
    }
    write_json(config.DATA_DIR / "events.json", {**meta, "levels": ["Orange", "Red"], "events": major})
    write_json(config.DATA_DIR / "events_green.json", {**meta, "levels": ["Green"], "events": green})
