"""Collecte : `python -m collect [étapes...]`. Sans argument, exécute toutes les étapes.

Chaque étape écrit son fichier dans public/data/. Une étape en échec n'efface pas les données
précédentes : l'erreur est consignée dans manifest.json, et le front affiche « indisponible ».
"""
import json
import sys
import traceback

from . import basemap, config, events, forecast, nino, sst, trends
from .common import now_iso, write_json

STEPS = {
    "nino": lambda: write_json(config.DATA_DIR / "nino.json", nino.collect()),
    "forecast": lambda: write_json(config.DATA_DIR / "forecast.json", forecast.collect()),
    "sst": sst.collect,
    "events": events.collect,
    "trends": trends.collect,
    "basemap": basemap.collect,
}
DEFAULT_STEPS = ["nino", "forecast", "sst", "events", "trends"]


def main(argv: list[str]) -> int:
    wanted = argv or DEFAULT_STEPS
    unknown = [s for s in wanted if s not in STEPS]
    if unknown:
        print(f"Étapes inconnues : {unknown}. Disponibles : {list(STEPS)}")
        return 2
    manifest_path = config.DATA_DIR / "manifest.json"
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {"steps": {}}
    failed = False
    for name in wanted:
        print(f"→ {name}")
        try:
            STEPS[name]()
            manifest["steps"][name] = {"ok": True, "at": now_iso()}
        except Exception as e:  # on continue les autres étapes
            failed = True
            traceback.print_exc()
            manifest["steps"][name] = {**manifest["steps"].get(name, {}), "ok": False,
                                       "error": str(e)[:300], "failed_at": now_iso()}
    manifest["start_date"] = config.START_DATE
    manifest["updated_at"] = now_iso()
    write_json(manifest_path, manifest)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
