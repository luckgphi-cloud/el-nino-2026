from collect import trends


def test_trend_zones_are_valid_closed_polygons():
    fc = trends.build()
    assert fc["features"], "aucune zone"
    for f in fc["features"]:
        ring = f["geometry"]["coordinates"][0]
        assert ring[0] == ring[-1] and len(ring) >= 4
        assert all(-180 <= x <= 360 and -90 <= y <= 90 for x, y in ring)
        p = f["properties"]
        assert p["season"] in trends.SEASONS and p["kind"] in trends.KINDS
        assert "El Niño" in p["label_fr"]


def test_no_causal_wording():
    fc = trends.build()
    for f in fc["features"]:
        assert "caus" not in f["properties"]["label_fr"].lower()
