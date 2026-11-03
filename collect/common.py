"""Outils partagés : HTTP avec reprises, écriture JSON horodatée."""
import json
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

from .config import USER_AGENT

_session = requests.Session()
_session.headers["User-Agent"] = USER_AGENT


def fetch(url: str, params: dict | None = None, timeout: int = 120, retries: int = 4) -> requests.Response:
    last: Exception | None = None
    for attempt in range(retries):
        try:
            r = _session.get(url, params=params, timeout=timeout)
            if r.status_code == 429:  # limitation de débit : on respecte Retry-After
                wait = int(r.headers.get("Retry-After", "0") or 0) or 30 * (attempt + 1)
                last = RuntimeError(f"429 Too Many Requests (attente {wait} s)")
                time.sleep(min(wait, 300))
                continue
            r.raise_for_status()
            return r
        except requests.RequestException as e:
            last = e
            time.sleep(2 ** attempt * 3)
    raise RuntimeError(f"Échec de téléchargement {url} : {last}")


def fetch_text(url: str, **kw) -> str:
    r = fetch(url, **kw)
    r.encoding = r.encoding or "utf-8"
    return r.text


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    tmp.replace(path)
