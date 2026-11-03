import json
from pathlib import Path

from collect import events

FIX = Path(__file__).parent / "fixtures"


def load():
    return json.loads((FIX / "FIXTURE_gdacs_events.json").read_text(encoding="utf-8"))["features"]


def test_normalize_real_gdacs_features():
    out = [events.normalize(f) for f in load()]
    assert all(out)
    assert {e["type"] for e in out} == {"fire", "flood", "cyclone", "drought"}
    tc = next(e for e in out if e["id"] == "TC-1001346")
    assert tc["level"] == "Red" and tc["country"] == "India"
    assert tc["url"].startswith("https://www.gdacs.org/report.aspx")
    assert -180 <= tc["lon"] <= 180 and -90 <= tc["lat"] <= 90


def test_country_list_cleaned():
    f = load()[0]
    f = json.loads(json.dumps(f))
    f["properties"]["country"] = "Aruba, , Brazil, Colombia"
    assert events.normalize(f)["country"] == "Aruba, Brazil, Colombia"


def test_excluded_types_and_bad_geometry():
    f = json.loads(json.dumps(load()[0]))
    f["properties"]["eventtype"] = "EQ"
    assert events.normalize(f) is None
    g = json.loads(json.dumps(load()[0]))
    g["geometry"] = {"type": "Polygon", "coordinates": []}
    assert events.normalize(g) is None


def test_empty_severity_becomes_none():
    f = json.loads(json.dumps(load()[0]))
    f["properties"]["severitydata"] = {"severitytext": "  "}
    assert events.normalize(f)["severity"] is None


def test_dedupe_keeps_latest():
    a = {"id": "X-1", "from": "2026-01-01", "_modified": "2026-01-02", "level": "Green"}
    b = {"id": "X-1", "from": "2026-01-01", "_modified": "2026-01-05", "level": "Orange"}
    out = events.dedupe([a, b])
    assert out == [{"id": "X-1", "from": "2026-01-01", "level": "Orange"}]


def test_search_url_keeps_literal_semicolons():
    u = events.search_url("FL", "2026-01-01", "2026-11-03", 2)
    assert "alertlevel=Green;Orange;Red" in u and "%3B" not in u and u.endswith("pagenumber=2")


def test_user_agent_is_ascii():
    from collect import config
    config.USER_AGENT.encode("ascii")


def test_split_by_level():
    evs = [{"level": "Green"}, {"level": "Orange"}, {"level": "Red"}]
    major, green = events.split_by_level(evs)
    assert [e["level"] for e in major] == ["Orange", "Red"] and green == [{"level": "Green"}]


def test_pagination_stops_on_repeated_page(monkeypatch):
    page = {"features": [{"properties": {"eventid": i}} for i in range(100)]}

    class R:
        content = b"x"

        def json(self):
            return page

    calls = []
    monkeypatch.setattr(events, "fetch", lambda url, timeout: calls.append(url) or R())
    out = events.fetch_type("WF", "2026-01-01", "2026-11-03", max_pages=10)
    assert len(out) == 100 and len(calls) == 2
