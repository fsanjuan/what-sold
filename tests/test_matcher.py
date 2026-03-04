import re
from datetime import date

import pandas as pd
import pytest
from dateutil.relativedelta import relativedelta

from matcher import find_matches


def make_df(records):
    """Build a minimal PPR-like DataFrame from a list of dicts."""
    df = pd.DataFrame(records)
    df["_county_norm"] = df["County"].str.strip().str.lower()
    return df


def recent(months_ago=1):
    """Return a date string (dd/mm/yyyy) N months in the past."""
    d = date.today() - relativedelta(months=months_ago)
    return d.strftime("%d/%m/%Y")


def old():
    """Return a date string 5 years in the past (outside any reasonable window)."""
    d = date.today() - relativedelta(years=5)
    return d.strftime("%d/%m/%Y")


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def smithfield_df():
    return make_df([
        {"Address": "APT 10, BLOCK A, SMITHFIELD MARKET, DUBLIN 7", "County": "Dublin",
         "Date of Sale (dd/mm/yyyy)": recent(3), "Price (€)": 350000.0,
         "Description of Property": "Second-Hand Dwelling house /Apartment"},
        {"Address": "22 SMITHFIELD VILLAGE, BOW ST, DUBLIN 7", "County": "Dublin",
         "Date of Sale (dd/mm/yyyy)": recent(6), "Price (€)": 420000.0,
         "Description of Property": "Second-Hand Dwelling house /Apartment"},
        {"Address": "5 GRIFFITH AVENUE, DUBLIN 9", "County": "Dublin",
         "Date of Sale (dd/mm/yyyy)": recent(1), "Price (€)": 550000.0,
         "Description of Property": "Second-Hand Dwelling house /Apartment"},
        {"Address": "14 SPRINGFIELD PARK, CORK", "County": "Cork",
         "Date of Sale (dd/mm/yyyy)": recent(1), "Price (€)": 300000.0,
         "Description of Property": "Second-Hand Dwelling house /Apartment"},
        {"Address": "APT 5, ASHFIELD COURT, DUBLIN 15", "County": "Dublin",
         "Date of Sale (dd/mm/yyyy)": recent(1), "Price (€)": 280000.0,
         "Description of Property": "Second-Hand Dwelling house /Apartment"},
    ])


# ---------------------------------------------------------------------------
# County filtering
# ---------------------------------------------------------------------------

class TestCountyFilter:
    def test_filters_to_correct_county(self, smithfield_df):
        results = find_matches(smithfield_df, "Smithfield", "Dublin", months=0)
        assert all(results["County"] == "Dublin")

    def test_excludes_other_county(self, smithfield_df):
        results = find_matches(smithfield_df, "Springfield", "Cork", months=0)
        assert all(results["County"] == "Cork")

    def test_unknown_county_returns_empty(self, smithfield_df):
        results = find_matches(smithfield_df, "Smithfield", "Atlantis", months=0)
        assert results.empty

    def test_partial_county_match(self, smithfield_df):
        # county input "ublin" is a substring of "dublin" — partial fallback kicks in
        results = find_matches(smithfield_df, "Smithfield", "ublin", months=0)
        assert not results.empty


# ---------------------------------------------------------------------------
# Address matching — exact matches
# ---------------------------------------------------------------------------

class TestExactMatching:
    def test_matches_uppercase_address(self, smithfield_df):
        results = find_matches(smithfield_df, "Smithfield", "Dublin", months=0)
        addresses = results["Address"].tolist()
        assert any("SMITHFIELD" in a for a in addresses)

    def test_case_insensitive(self, smithfield_df):
        lower = find_matches(smithfield_df, "smithfield", "Dublin", months=0)
        upper = find_matches(smithfield_df, "SMITHFIELD", "Dublin", months=0)
        assert set(lower["Address"]) == set(upper["Address"])

    def test_no_false_positives(self, smithfield_df):
        # "Ashfield" and "Springfield" should NOT appear when searching "Smithfield"
        results = find_matches(smithfield_df, "Smithfield", "Dublin", months=0)
        addresses = results["Address"].tolist()
        assert not any("ASHFIELD" in a for a in addresses)
        assert not any("SPRINGFIELD" in a for a in addresses)

    def test_multi_word_query(self, smithfield_df):
        results = find_matches(smithfield_df, "Griffith Avenue", "Dublin", months=0)
        assert len(results) == 1
        assert "GRIFFITH AVENUE" in results.iloc[0]["Address"]

    def test_no_match_returns_empty(self, smithfield_df):
        results = find_matches(smithfield_df, "Merrion Square", "Dublin", months=0)
        assert results.empty


# ---------------------------------------------------------------------------
# Date filtering
# ---------------------------------------------------------------------------

class TestDateFilter:
    def test_excludes_old_records(self):
        df = make_df([
            {"Address": "1 SMITHFIELD, DUBLIN 7", "County": "Dublin",
             "Date of Sale (dd/mm/yyyy)": old(), "Price (€)": 300000.0,
             "Description of Property": ""},
            {"Address": "2 SMITHFIELD, DUBLIN 7", "County": "Dublin",
             "Date of Sale (dd/mm/yyyy)": recent(6), "Price (€)": 310000.0,
             "Description of Property": ""},
        ])
        results = find_matches(df, "Smithfield", "Dublin", months=24)
        assert len(results) == 1
        assert "2 SMITHFIELD" in results.iloc[0]["Address"]

    def test_months_zero_returns_all(self):
        df = make_df([
            {"Address": "1 SMITHFIELD, DUBLIN 7", "County": "Dublin",
             "Date of Sale (dd/mm/yyyy)": old(), "Price (€)": 300000.0,
             "Description of Property": ""},
            {"Address": "2 SMITHFIELD, DUBLIN 7", "County": "Dublin",
             "Date of Sale (dd/mm/yyyy)": recent(6), "Price (€)": 310000.0,
             "Description of Property": ""},
        ])
        results = find_matches(df, "Smithfield", "Dublin", months=0)
        assert len(results) == 2

    def test_all_old_records_returns_empty(self):
        df = make_df([
            {"Address": "1 SMITHFIELD, DUBLIN 7", "County": "Dublin",
             "Date of Sale (dd/mm/yyyy)": old(), "Price (€)": 300000.0,
             "Description of Property": ""},
        ])
        results = find_matches(df, "Smithfield", "Dublin", months=24)
        assert results.empty


# ---------------------------------------------------------------------------
# Sorting
# ---------------------------------------------------------------------------

class TestSorting:
    def test_sorted_by_date_descending(self):
        df = make_df([
            {"Address": "1 SMITHFIELD, DUBLIN 7", "County": "Dublin",
             "Date of Sale (dd/mm/yyyy)": recent(12), "Price (€)": 300000.0,
             "Description of Property": ""},
            {"Address": "2 SMITHFIELD, DUBLIN 7", "County": "Dublin",
             "Date of Sale (dd/mm/yyyy)": recent(3), "Price (€)": 320000.0,
             "Description of Property": ""},
            {"Address": "3 SMITHFIELD, DUBLIN 7", "County": "Dublin",
             "Date of Sale (dd/mm/yyyy)": recent(6), "Price (€)": 310000.0,
             "Description of Property": ""},
        ])
        results = find_matches(df, "Smithfield", "Dublin", months=24)
        dates = pd.to_datetime(results["Date of Sale (dd/mm/yyyy)"], format="%d/%m/%Y")
        assert dates.is_monotonic_decreasing
