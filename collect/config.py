"""Configuration de la collecte. START_DATE est la seule constante à modifier pour changer la période."""
import os
from pathlib import Path

# Date de départ de la visualisation (première semaine incluse : celle qui contient cette date).
START_DATE = "2026-01-01"

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "public" / "data"
CACHE_DIR = ROOT / ".cache"

# ASCII uniquement : le pare-feu de GDACS rejette (403) un User-Agent contenant des accents.
USER_AGENT = "el-nino-2026-viz/0.1" + (
    f" (contact: {os.environ['COLLECT_CONTACT']})" if os.environ.get("COLLECT_CONTACT") else ""
)

CPC_INDICES = "https://www.cpc.ncep.noaa.gov/data/indices"
NINO_WEEKLY_URL = f"{CPC_INDICES}/wksst9120.for"
RONI_URL = f"{CPC_INDICES}/RONI.ascii.txt"
ONI_URL = f"{CPC_INDICES}/oni.ascii.txt"

CPC_ROOT = "https://www.cpc.ncep.noaa.gov/products/analysis_monitoring"
CPC_PROBS_URL = f"{CPC_ROOT}/enso/roni/probabilities/"
CPC_STRENGTHS_URL = f"{CPC_ROOT}/enso/roni/strengths/"
CPC_DISCUSSION_URL = f"{CPC_ROOT}/enso_advisory/ensodisc.shtml"

PSL_NCSS = "https://psl.noaa.gov/thredds/ncss/grid/Datasets/noaa.oisst.v2.highres"
OISST_YEAR_FILE = "sst.day.mean.{year}.nc"
OISST_LTM_FILE = "sst.day.mean.ltm.1991-2020.nc"

GDACS_EVENTS_URL = "https://www.gdacs.org/gdacsapi/api/events/geteventlist/SEARCH"
