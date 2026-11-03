"""Anomalies hebdomadaires de SST (NOAA OISST v2.1) → PNG Web Mercator + grille de lecture 1°.

Anomalie = moyenne sur la semaine CPC (dim.–sam.) de (SST quotidienne − climatologie quotidienne 1991-2020).
Les deux fichiers sont lus via le service de sous-ensembles THREDDS de NOAA PSL, à 0,5° (une maille sur deux).
"""
import io
import json
import re
import time
import uuid
import warnings
from datetime import date, datetime, timedelta, timezone

import netCDF4
import numpy as np
from PIL import Image

from . import config
from .common import fetch, now_iso, write_json
from .nino import week_center_for

STRIDE = 2  # 0,25° → 0,5°
RES = 0.25 * STRIDE
MERC_SIZE = 720
MERC_MAX_LAT = 85.0511287798066
PAUSE_S = 2  # pause entre requêtes PSL (le serveur renvoie 429 si on insiste)
PROVISIONAL_DAYS = 15  # PSL : « Data less than 15 days old may be subject to revision »
NINO34_BOX = (-5.0, 5.0, 190.0, 240.0)  # lat min, lat max, lon min, lon max (0-360)

# Classes de 0,5 °C de −4 à +4, plus deux classes ouvertes. Palette ColorBrewer RdBu (sûre pour les daltonismes
# rouge-vert), interpolée de 11 à 18 couleurs, du froid (bleu) au chaud (rouge).
EDGES = [round(-4.0 + 0.5 * i, 1) for i in range(17)]
_RDBU = ["#053061", "#2166ac", "#4393c3", "#92c5de", "#d1e5f0", "#f7f7f7",
         "#fddbc7", "#f4a582", "#d6604d", "#b2182b", "#67001f"]


def palette(n: int = len(EDGES) + 1) -> list[str]:
    anchors = np.array([[int(h[i:i + 2], 16) for i in (1, 3, 5)] for h in _RDBU], dtype=float)
    pos = np.linspace(0, len(anchors) - 1, n)
    out = []
    for p in pos:
        i = min(int(p), len(anchors) - 2)
        c = anchors[i] + (anchors[i + 1] - anchors[i]) * (p - i)
        out.append("#" + "".join(f"{int(round(v)):02x}" for v in c))
    return out


COLORS = palette()


def classify(anom: np.ndarray) -> np.ndarray:
    """Indice de classe (0..17) ; 255 pour les terres / glaces (NaN)."""
    idx = np.digitize(anom, EDGES).astype(np.uint8)
    idx[np.isnan(anom)] = 255
    return idx


def cpc_weeks(start: date, last_day: date) -> list[tuple[date, date, date]]:
    """Semaines (dimanche, mercredi, samedi) complètes entre start et last_day."""
    center = week_center_for(start)
    out = []
    while center + timedelta(days=3) <= last_day:
        out.append((center - timedelta(days=3), center, center + timedelta(days=3)))
        center += timedelta(days=7)
    return out


def ltm_day(d: date) -> date:
    """Date dans la climatologie (an 0001, 365 jours) : le 29 février prend la valeur du 28."""
    if d.month == 2 and d.day == 29:
        return date(1, 2, 28)
    return date(1, d.month, d.day)


def _ncss(file: str, t0: str, t1: str) -> np.ndarray:
    params = {"var": "sst", "horizStride": STRIDE, "time_start": t0, "time_end": t1, "accept": "netcdf"}
    r = fetch(f"{config.PSL_NCSS}/{file}", params=params, timeout=300)
    time.sleep(PAUSE_S)
    ds = netCDF4.Dataset(f"mem-{uuid.uuid4().hex}.nc", memory=r.content)
    v = ds["sst"]
    v.set_auto_mask(False)
    arr = np.array(v[:], dtype=np.float32)
    miss = getattr(v, "missing_value", None)
    if miss is not None:
        arr[arr == miss] = np.nan
    arr[(arr < -5) | (arr > 45)] = np.nan
    lat = np.array(ds["lat"][:])
    lon = np.array(ds["lon"][:])
    ds.close()
    if not (lat[0] < lat[-1] and abs(lat[1] - lat[0] - RES) < 1e-6 and abs(lon[0] - 0.125) < 1e-6):
        raise ValueError("Grille OISST inattendue")
    return arr


def _cached(key: str, loader, cache: bool) -> np.ndarray:
    path = config.CACHE_DIR / "sst" / f"{key}.npy"
    if cache and path.exists():
        return np.load(path)
    arr = loader()
    if cache:
        path.parent.mkdir(parents=True, exist_ok=True)
        np.save(path, arr)
    return arr


def _days(sun: date, sat: date, provisional: bool) -> np.ndarray:
    parts = []
    d = sun
    while d <= sat:  # une semaine peut chevaucher deux fichiers annuels
        end = min(sat, date(d.year, 12, 31))
        f = config.OISST_YEAR_FILE.format(year=d.year)
        parts.append(_cached(f"obs_{d}_{end}", lambda f=f, d=d, end=end: _ncss(f, f"{d}T00:00:00Z", f"{end}T00:00:00Z"),
                             cache=not provisional))
        d = end + timedelta(days=1)
    return np.concatenate(parts)


def _clim(sun: date, sat: date) -> np.ndarray:
    """Climatologie des jours de la semaine, en une requête par bloc de jours consécutifs dans l'an 0001."""
    days = [ltm_day(sun + timedelta(days=i)) for i in range((sat - sun).days + 1)]
    blocks: list[list[date]] = []
    for d in days:
        if blocks and (d - blocks[-1][-1]).days == 1:
            blocks[-1].append(d)
        else:
            blocks.append([d])  # nouveau bloc au passage 31 déc. → 1er janv. (ou doublon du 28 fév.)
    out = []
    for b in blocks:
        key = f"ltm_{b[0]:%m-%d}_{b[-1]:%m-%d}"
        arr = _cached(key, lambda b=b: _ncss(config.OISST_LTM_FILE, f"0001-{b[0]:%m-%d}T00:00:00Z",
                                             f"0001-{b[-1]:%m-%d}T00:00:00Z"), cache=True)
        out.extend(arr)
    return np.stack(out)


def weekly_anomaly(obs: np.ndarray, clim: np.ndarray) -> np.ndarray:
    if obs.shape != clim.shape or obs.shape[0] != 7:
        raise ValueError(f"Semaine incomplète : {obs.shape} vs {clim.shape}")
    with np.errstate(invalid="ignore"):
        anom = obs - clim
        # Une maille n'est valide que si les 7 jours le sont (évite les bords de banquise changeants).
        return np.where(np.isnan(anom).any(axis=0), np.nan, anom.mean(axis=0)).astype(np.float32)


def grid_lats(n: int) -> np.ndarray:
    return -89.875 + RES * np.arange(n)


def grid_lons(n: int) -> np.ndarray:
    return 0.125 + RES * np.arange(n)


def box_mean(anom: np.ndarray, box=NINO34_BOX) -> float:
    lats, lons = grid_lats(anom.shape[0]), grid_lons(anom.shape[1])
    li = (lats >= box[0]) & (lats <= box[1])
    lj = (lons >= box[2]) & (lons <= box[3])
    sub = anom[np.ix_(li, lj)]
    w = np.cos(np.deg2rad(lats[li]))[:, None] * np.ones_like(sub)
    ok = ~np.isnan(sub)
    return float((sub[ok] * w[ok]).sum() / w[ok].sum())


def to_mercator(grid: np.ndarray, size: int = MERC_SIZE) -> np.ndarray:
    """Reprojette une grille lat/lon régulière (lat croissante, lon 0..360) en carré Web Mercator,
    lon −180..180, nord en haut (plus proche voisin)."""
    nlat, nlon = grid.shape
    shifted = np.roll(grid, nlon // 2, axis=1)  # colonne 0 → lon −180
    y = (np.arange(size) + 0.5) / size
    lat = np.degrees(np.arctan(np.sinh(np.pi * (1 - 2 * y))))
    rows = np.clip(np.round((lat - (-89.875)) / RES).astype(int), 0, nlat - 1)
    x = (np.arange(size) + 0.5) / size * 360 - 180
    cols = np.clip(np.floor((x + 180) / 360 * nlon).astype(int), 0, nlon - 1)
    return shifted[np.ix_(rows, cols)]


def png_bytes(classes: np.ndarray) -> bytes:
    img = Image.fromarray(classes, mode="P")
    pal = []
    for c in COLORS:
        pal += [int(c[1:3], 16), int(c[3:5], 16), int(c[5:7], 16)]
    pal += [0, 0, 0] * (256 - len(COLORS))
    img.putpalette(pal)
    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True, transparency=255)
    return buf.getvalue()


def readout_grid(anom: np.ndarray) -> bytes:
    """Grille 1° (180×360, nord-ouest en premier), int8 = anomalie × 10, −128 = pas de donnée."""
    nlat, nlon = anom.shape
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)  # blocs entièrement terrestres → NaN attendu
        coarse = np.nanmean(anom.reshape(nlat // 2, 2, nlon // 2, 2), axis=(1, 3))
    coarse = np.roll(coarse, (nlon // 2) // 2, axis=1)[::-1]
    out = np.full(coarse.shape, -128, dtype=np.int8)
    ok = ~np.isnan(coarse)
    out[ok] = np.clip(np.round(coarse[ok] * 10), -127, 127).astype(np.int8)
    return out.tobytes()


def _latest_obs_day() -> date:
    year = datetime.now(timezone.utc).year
    for y in (year, year - 1):  # en tout début d'année, le fichier de l'année peut ne pas exister encore
        try:
            r = fetch(f"{config.PSL_NCSS}/{config.OISST_YEAR_FILE.format(year=y)}/dataset.xml", retries=1)
        except RuntimeError:
            continue
        m = re.search(r"<end>(\d{4}-\d{2}-\d{2})", r.text)
        if m:
            return date.fromisoformat(m.group(1))
    raise ValueError("Fin de couverture OISST introuvable")


def collect() -> None:
    out_dir = config.DATA_DIR / "sst"
    out_dir.mkdir(parents=True, exist_ok=True)
    start = date.fromisoformat(config.START_DATE)
    today = datetime.now(timezone.utc).date()
    last = _latest_obs_day()
    weeks = cpc_weeks(start, last)
    nino_path = config.DATA_DIR / "nino.json"
    cpc = {}
    if nino_path.exists():
        cpc = {r["week_center"]: r["nino34_anom"] for r in json.loads(nino_path.read_text())["weekly"]["data"]}

    def one(week):
        sun, center, sat = week
        provisional = (today - sat).days < PROVISIONAL_DAYS
        anom = weekly_anomaly(_days(sun, sat, provisional), _clim(sun, sat))
        (out_dir / f"{center}.png").write_bytes(png_bytes(classify(to_mercator(anom))))
        (out_dir / f"{center}.bin").write_bytes(readout_grid(anom))
        mine = round(box_mean(anom), 2)
        ref = cpc.get(center.isoformat())
        print(f"  {center} Niño-3.4 calculé {mine:+.2f} / CPC {ref}")
        return {"week_center": center.isoformat(), "start": sun.isoformat(), "end": sat.isoformat(),
                "provisional": provisional, "nino34_box_mean": mine, "cpc_nino34": ref,
                "diff": None if ref is None else round(mine - ref, 2)}

    rows = [one(w) for w in weeks]  # séquentiel : le serveur PSL limite le débit
    diffs = [abs(r["diff"]) for r in rows if r["diff"] is not None]
    write_json(out_dir / "index.json", {
        "retrieved_at": now_iso(),
        "source": "NOAA/NCEI OISST v2.1 (AVHRR), via NOAA PSL ; anomalies calculées par rapport à la climatologie 1991-2020",
        "url": "https://psl.noaa.gov/data/gridded/data.noaa.oisst.v2.highres.html",
        "last_obs_day": last.isoformat(),
        "palette": {"edges": EDGES, "colors": COLORS, "unit": "°C"},
        "image": {"projection": "web-mercator", "width": MERC_SIZE, "height": MERC_SIZE,
                  "bounds": [-180, -MERC_MAX_LAT, 180, MERC_MAX_LAT]},
        "readout": {"resolution_deg": 1.0, "rows": 180, "cols": 360, "scale": 0.1, "nodata": -128,
                    "origin": "nord-ouest (89,5°N, 179,5°O), lignes vers le sud"},
        "validation": {
            "description": "Moyenne pondérée (cos lat) de nos anomalies sur 5°S-5°N, 170°O-120°O comparée à l'indice hebdomadaire CPC",
            "weeks_compared": len(diffs),
            "max_abs_diff": max(diffs) if diffs else None,
            "mean_abs_diff": round(sum(diffs) / len(diffs), 3) if diffs else None,
        },
        "weeks": rows,
    })
