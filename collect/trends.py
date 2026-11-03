"""Zones de tendance El Niño : tracé SCHÉMATIQUE, à la main, d'après la carte NOAA CPC
« Warm Episode Relationships » (déc.–févr. et juin–août) et le texte qui l'accompagne.

Ce ne sont pas des données mesurées : les contours sont approximatifs (à quelques degrés près) et ne
doivent pas être lus finement. Ils indiquent où les épisodes El Niño passés se sont statistiquement
accompagnés de conditions plus humides, plus sèches, plus chaudes ou plus fraîches. Tendance ≠ causalité.
Longitudes en degrés est, éventuellement > 180 pour les zones qui traversent l'antiméridien.
"""
import math

from . import config
from .common import now_iso, write_json

SOURCE_URL = "https://www.cpc.ncep.noaa.gov/products/analysis_monitoring/ensocycle/elninosfc.shtml"
MAP_URL = "https://www.cpc.ncep.noaa.gov/products/analysis_monitoring/impacts/warm.gif"

KINDS = {
    "wet": ("Plus humide que la normale", "hatch-wet", "#4fc3f7"),
    "wet_warm": ("Plus humide et plus chaud", "hatch-wet", "#4fc3f7"),
    "wet_cool": ("Plus humide et plus frais", "hatch-wet", "#4fc3f7"),
    "dry": ("Plus sec que la normale", "hatch-dry", "#d7b98e"),
    "dry_warm": ("Plus sec et plus chaud", "hatch-dry", "#d7b98e"),
    "dry_cool": ("Plus sec et plus frais", "hatch-dry", "#d7b98e"),
    "warm": ("Plus chaud que la normale", "hatch-warm", "#ff8a65"),
}
SEASONS = {"DJF": "déc.–févr.", "JJA": "juin–août"}


def ellipse(cx: float, cy: float, rx: float, ry: float, n: int = 28) -> list[list[float]]:
    pts = [[round(cx + rx * math.cos(2 * math.pi * i / n), 2), round(cy + ry * math.sin(2 * math.pi * i / n), 2)]
           for i in range(n)]
    return pts + [pts[0]]


def poly(*pts: tuple[float, float]) -> list[list[float]]:
    ring = [list(p) for p in pts]
    return ring + [ring[0]]


# (saison, type, région, contour)
ZONES = [
    ("DJF", "wet_warm", "Pacifique équatorial central et est, côte de l'Équateur et du nord du Pérou",
     poly((160, -6), (200, -8), (250, -8), (279, -7), (281, 0), (279, 5), (250, 6), (200, 6), (160, 5))),
    ("DJF", "dry", "Philippines et Pacifique nord-ouest tropical",
     poly((112, 8), (125, 17), (150, 20), (185, 23), (205, 22), (205, 15), (180, 13), (150, 10), (125, 6))),
    ("DJF", "dry", "Indonésie orientale, nord de l'Australie et Pacifique sud-ouest",
     poly((118, -2), (135, -4), (155, -10), (180, -17), (198, -24), (190, -28), (170, -24), (145, -20), (128, -16), (115, -10))),
    ("DJF", "dry_warm", "Indonésie et Malaisie", ellipse(110, -3, 13, 8)),
    ("DJF", "warm", "Asie du Sud-Est et sud de la Chine", poly((84, 26), (100, 30), (118, 28), (120, 18), (110, 8), (96, 2), (86, 12))),
    ("DJF", "wet", "Sud-est de la Chine et Taïwan", ellipse(119, 24, 5, 3)),
    ("DJF", "warm", "Japon et Corée", ellipse(134, 37, 8, 5)),
    ("DJF", "wet", "Afrique de l'Est équatoriale", ellipse(38, -1, 4, 6)),
    ("DJF", "dry_warm", "Afrique australe (sud-est)", ellipse(31, -20, 8, 9)),
    ("DJF", "warm", "Sud-est de l'Australie", ellipse(146, -36, 6, 4)),
    ("DJF", "warm", "Sud de l'Alaska et ouest/centre du Canada",
     poly((-168, 58), (-150, 63), (-125, 61), (-103, 56), (-92, 50), (-100, 46), (-118, 49), (-140, 54), (-160, 53))),
    ("DJF", "wet", "Sud-ouest des États-Unis et nord-ouest du Mexique", ellipse(-114, 31, 6, 4)),
    ("DJF", "wet_cool", "Côte du golfe du Mexique (États-Unis)", ellipse(-89, 30, 11, 4)),
    ("DJF", "dry", "Nord de l'Amérique du Sud", ellipse(-57, 2, 11, 6)),
    ("DJF", "warm", "Sud-est du Brésil", ellipse(-44, -19, 6, 7)),
    ("DJF", "wet", "Sud du Brésil, Uruguay, nord-est de l'Argentine", ellipse(-56, -30, 7, 6)),
    ("JJA", "dry", "Inde", ellipse(79, 21, 7, 7)),
    ("JJA", "dry", "Indonésie, Philippines et nord de l'Australie",
     poly((96, 4), (113, 16), (128, 12), (140, 0), (150, -10), (142, -20), (125, -18), (110, -12), (100, -5))),
    ("JJA", "dry_cool", "Est de l'Australie et mer de Tasman",
     poly((135, -18), (160, -17), (178, -22), (180, -35), (168, -45), (150, -42), (140, -32))),
    ("JJA", "wet", "Pacifique équatorial central", poly((165, 2), (180, -6), (195, -12), (210, 0), (218, 10), (195, 16), (172, 12))),
    ("JJA", "dry_warm", "Amérique centrale et Caraïbes", ellipse(-75, 13, 15, 5)),
    ("JJA", "warm", "Côte ouest de l'Amérique du Sud", poly((-82, 3), (-76, 4), (-70, -10), (-68, -28), (-73, -30), (-80, -10))),
    ("JJA", "wet", "Centre du Chili", ellipse(-72, -35, 2.5, 4)),
    ("JJA", "warm", "Sud-est du Brésil", ellipse(-45, -23, 8, 8)),
]


def build() -> dict:
    feats = []
    for season, kind, region, ring in ZONES:
        label, pattern, stroke = KINDS[kind]
        feats.append({
            "type": "Feature",
            "properties": {"season": season, "kind": kind, "region": region, "pattern": pattern, "stroke": stroke,
                           "label_fr": f"{label} en {SEASONS[season]} lors des épisodes El Niño passés — {region}"},
            "geometry": {"type": "Polygon", "coordinates": [ring]},
        })
    return {"type": "FeatureCollection", "features": feats}


def collect() -> None:
    write_json(config.DATA_DIR / "trends.json", {
        "generated_at": now_iso(),
        "source": "Tracé schématique d'après NOAA Climate Prediction Center, « Warm Episode Relationships » (déc.–févr., juin–août)",
        "note": "Contours approximatifs tracés à la main ; tendance statistique, pas causalité ni prévision.",
        "url": SOURCE_URL,
        "map_url": MAP_URL,
        "features": build(),
    })
