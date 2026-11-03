"""Tests du traitement SST sur des grilles synthétiques construites dans le test (aucune donnée réelle simulée)."""
from datetime import date

import numpy as np
import pytest

from collect import sst

NLAT, NLON = 360, 720  # grille 0,5° telle que livrée par PSL avec horizStride=2


def test_classes_edges_and_nan():
    a = np.array([-9.0, -4.0, -0.01, 0.0, 0.49, 3.99, 4.0, np.nan])
    assert sst.classify(a).tolist() == [0, 1, 8, 9, 9, 16, 17, 255]
    assert len(sst.COLORS) == len(sst.EDGES) + 1


def test_palette_is_blue_to_red():
    first, last = sst.COLORS[0], sst.COLORS[-1]
    assert int(first[5:7], 16) > int(first[1:3], 16)  # bleu dominant
    assert int(last[1:3], 16) > int(last[5:7], 16)    # rouge dominant


def test_cpc_weeks_complete_only():
    weeks = sst.cpc_weeks(date(2026, 1, 1), date(2026, 1, 16))
    # la semaine centrée le 14 se termine le 17 : absente si le dernier jour observé est le 16
    assert [w[1] for w in weeks] == [date(2025, 12, 31), date(2026, 1, 7)]
    assert weeks[0] == (date(2025, 12, 28), date(2025, 12, 31), date(2026, 1, 3))


def test_ltm_day_leap():
    assert sst.ltm_day(date(2028, 2, 29)) == date(1, 2, 28)
    assert sst.ltm_day(date(2026, 10, 28)) == date(1, 10, 28)


def test_weekly_anomaly_requires_seven_valid_days():
    obs = np.full((7, 2, 2), 20.0, dtype=np.float32)
    clim = np.full((7, 2, 2), 19.0, dtype=np.float32)
    obs[3, 0, 0] = np.nan
    a = sst.weekly_anomaly(obs, clim)
    assert np.isnan(a[0, 0]) and a[1, 1] == pytest.approx(1.0)
    with pytest.raises(ValueError):
        sst.weekly_anomaly(obs[:6], clim[:6])


def test_box_mean_selects_nino34_region():
    g = np.zeros((NLAT, NLON), dtype=np.float32)
    lats, lons = sst.grid_lats(NLAT), sst.grid_lons(NLON)
    inside = (np.abs(lats) <= 5)[:, None] & ((lons >= 190) & (lons <= 240))[None, :]
    g[inside] = 2.0
    g[0, 0] = np.nan
    assert sst.box_mean(g) == pytest.approx(2.0)


def test_mercator_orientation():
    g = np.zeros((NLAT, NLON), dtype=np.float32)
    g[sst.grid_lats(NLAT) > 60, :] = 1.0                 # nord
    g[:, (sst.grid_lons(NLON) > 0) & (sst.grid_lons(NLON) < 10)] = 2.0  # juste à l'est de Greenwich
    m = sst.to_mercator(g, size=360)
    assert m[0, 50] == 1.0 and m[-1, 50] == 0.0           # nord en haut
    assert m[180, 181] == 2.0 and m[180, 170] == 0.0      # lon 0..10 au centre-droit


def test_readout_orientation_and_encoding():
    g = np.full((NLAT, NLON), np.nan, dtype=np.float32)
    g[-2:, 360:362] = 1.23   # 89,4-89,6°N, lon 180,1-180,6 → (après bascule) ouest extrême, nord
    out = np.frombuffer(sst.readout_grid(g), dtype=np.int8).reshape(180, 360)
    assert out[0, 0] == 12
    assert out[90, 90] == -128


def test_png_has_transparent_land():
    png = sst.png_bytes(np.array([[0, 255]], dtype=np.uint8))
    assert png[:8] == b"\x89PNG\r\n\x1a\n" and b"tRNS" in png
