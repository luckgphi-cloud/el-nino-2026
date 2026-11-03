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


def test_magnitude_parsed_from_real_severity_texts():
    assert events.magnitude_from_severity("cyclone", "Hurricane/Typhoon > 74 mph (maximum wind speed of 241 km/h)") == 241.0
    assert events.magnitude_from_severity("fire", "Green impact for forestfire in 7227 ha") == 7227.0
    assert events.magnitude_from_severity("drought", "Minor impact for agricultural drought in 1552123 km2") == 1552123.0
    assert events.magnitude_from_severity("flood", "Magnitude 0 ") is None
    assert events.magnitude_from_severity("fire", None) is None


def test_intensity_classes_use_physical_thresholds():
    assert events.intensity_class("cyclone", 118) == "moderate"
    assert events.intensity_class("cyclone", 119) == "strong"   # catégorie 1 Saffir-Simpson
    assert events.intensity_class("cyclone", 178) == "extreme"  # catégorie 3
    assert events.intensity_class("fire", 39_999) == "moderate"
    assert events.intensity_class("fire", 100_000) == "extreme"
    assert events.intensity_class("drought", 1_000_000) == "extreme"
    assert events.intensity_class("flood", None) is None


def test_intensity_ignores_gdacs_alert_level():
    a = {"type": "cyclone", "severity": "Tropical Storm (maximum wind speed of 222 km/h)", "level": "Green"}
    b = {"type": "cyclone", "severity": "Tropical Storm (maximum wind speed of 222 km/h)", "level": "Red"}
    events.add_intensity([a, b], area_fn=lambda e: None)
    assert a["intensity"] == b["intensity"] == "extreme"


def test_ring_area_one_degree_square_at_equator():
    ring = [[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]
    assert abs(events.ring_area_km2(ring) - 12364) < 50  # 111,2 km × 111,2 km


def test_affected_area_from_real_geometry():
    fc = json.loads((FIX / "FIXTURE_gdacs_flood_geometry.json").read_text())
    area = events.affected_area_km2(fc)
    assert area is not None and area > 0
    assert events.affected_area_km2({"features": []}) is None


def test_split_by_intensity():
    evs = [{"intensity": "moderate"}, {"intensity": "strong"}, {"intensity": None}, {"intensity": "extreme"}]
    main, moderate = events.split_by_intensity(evs)
    assert [e["intensity"] for e in main] == ["strong", None, "extreme"] and moderate == [{"intensity": "moderate"}]


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
