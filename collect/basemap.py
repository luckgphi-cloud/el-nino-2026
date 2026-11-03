"""Fond de carte Natural Earth (domaine public), allégé : propriétés retirées, coordonnées à 0,01°.
Étape ponctuelle : `python -m collect basemap` (pas incluse dans la collecte par défaut)."""
from . import config
from .common import fetch, write_json

NE = "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson"
LAYERS = {"land": "ne_50m_land", "borders": "ne_110m_admin_0_boundary_lines_land"}


def _round(coords):
    if isinstance(coords[0], (int, float)):
        return [round(coords[0], 2), round(coords[1], 2)]
    return [_round(c) for c in coords]


def simplify(fc: dict) -> dict:
    return {"type": "FeatureCollection", "features": [
        {"type": "Feature", "properties": {},
         "geometry": {"type": f["geometry"]["type"], "coordinates": _round(f["geometry"]["coordinates"])}}
        for f in fc["features"] if f.get("geometry")]}


def collect() -> None:
    for name, src in LAYERS.items():
        write_json(config.ROOT / "public" / "basemap" / f"{name}.geojson", simplify(fetch(f"{NE}/{src}.geojson").json()))
