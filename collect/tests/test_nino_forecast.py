from datetime import date
from pathlib import Path

import pytest

from collect import forecast, nino

FIX = Path(__file__).parent / "fixtures"


def read(name: str) -> str:
    return (FIX / name).read_text(encoding="utf-8", errors="replace")


def test_weekly_parses_glued_negative_columns():
    rows = nino.parse_weekly(" 02SEP1981     20.6-0.1     24.8-0.1     26.5-0.2     28.3-0.3")
    assert rows == [{"week_center": "1981-09-02", "nino34_sst": 26.5, "nino34_anom": -0.2}]


def test_weekly_fixture_values_match_source_file():
    rows = nino.parse_weekly(read("FIXTURE_wksst9120.for"))
    by_date = {r["week_center"]: r for r in rows}
    # Valeurs lues à la main dans le fichier CPC téléchargé le 2026-11-03
    assert by_date["2026-10-28"]["nino34_anom"] == 3.4
    assert by_date["2026-10-28"]["nino34_sst"] == 30.2
    assert by_date["2026-09-23"]["nino34_anom"] == 3.1
    assert all(r["week_center"] < "2026-11-01" for r in rows)


def test_weekly_rejects_malformed_line():
    with pytest.raises(ValueError):
        nino.parse_weekly(" 28OCT2026     26.7 5.4     29.5")


def test_season_center_djf_belongs_to_year():
    assert nino.season_center("DJF", 2026) == date(2026, 1, 15)
    assert nino.season_center("NDJ", 2026) == date(2026, 12, 15)


def test_roni_and_oni_fixture():
    roni = nino.parse_seasonal(read("FIXTURE_RONI.ascii.txt"), 2)
    assert roni[-1] == {"season": "JAS", "year": 2026, "center": "2026-08-15", "value": 1.69}
    oni = nino.parse_seasonal(read("FIXTURE_oni.ascii.txt"), 3)
    assert oni[-1]["value"] == 2.16 and oni[-1]["season"] == "JAS"


def test_week_center_is_cpc_wednesday():
    assert nino.week_center_for(date(2026, 1, 1)) == date(2025, 12, 31)  # jeudi → mercredi précédent
    assert nino.week_center_for(date(2026, 10, 25)) == date(2026, 10, 28)  # dimanche → mercredi suivant
    assert nino.week_center_for(date(2026, 10, 31)) == date(2026, 10, 28)  # samedi


def test_issued_ignores_commented_label():
    assert forecast.parse_issued(read("FIXTURE_cpc_strengths.html")) == (2026, 10)


def test_categories_fixture():
    out = forecast.parse_categories(read("FIXTURE_cpc_probabilities.html"))
    assert out["issued"] == "2026-10"
    first, last = out["data"][0], out["data"][-1]
    assert first == {"season": "SON", "center": "2026-10-15", "la_nina": 0, "neutral": 0, "el_nino": 100}
    assert last == {"season": "MJJ", "center": "2027-06-15", "la_nina": 13, "neutral": 70, "el_nino": 17}
    assert len(out["data"]) == 9


def test_strengths_fixture():
    out = forecast.parse_strengths(read("FIXTURE_cpc_strengths.html"))
    jfm = next(d for d in out["data"] if d["season"] == "JFM")
    assert jfm["center"] == "2027-02-15"
    assert [b["p"] for b in jfm["bins"]] == [0, 0, 0, 0, 0, 2, 15, 37, 46]
    assert jfm["bins"][-1] == {"lo": 2.0, "hi": None, "p": 46}


def test_season_centers_across_year_boundary():
    assert forecast.season_centers(["NDJ", "DJF"], (2027, 1)) == [date(2026, 12, 15), date(2027, 1, 15)]


def test_inconsistent_probabilities_rejected():
    page = "<p>Issued October 2026</p><table><tr><td>SON</td><td>10</td><td>10</td><td>10</td></tr></table>"
    with pytest.raises(ValueError):
        forecast.parse_categories(page)


def test_discussion_fixture():
    d = forecast.parse_discussion(read("FIXTURE_cpc_ensodisc.html"))
    assert d["date"] == "2026-10-08"
    assert d["status"] == "El Niño Advisory"
    assert d["synopsis_en"].startswith("El Niño continues to strengthen")


def test_archive_urls_cover_months():
    urls = forecast.archive_urls(date(2025, 12, 20), date(2026, 2, 3))
    assert [u.rsplit("/", 2)[-2] for u in urls] == ["enso_disc_dec2025", "enso_disc_jan2026", "enso_disc_feb2026"]
