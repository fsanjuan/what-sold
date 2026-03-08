import os
from datetime import date
from unittest.mock import patch

import pandas as pd
import pytest

import ppr
from ppr import _year_path, _years_to_download, load_ppr


class TestYearPath:
    def test_returns_correct_filename(self):
        path = _year_path(2023)
        assert path.endswith("PPR-2023.csv")

    def test_includes_data_dir(self):
        path = _year_path(2023)
        assert "data" in path


class TestYearsToDownload:
    def test_includes_current_year(self):
        years = _years_to_download()
        assert date.today().year in years

    def test_missing_historical_years_included(self, tmp_path):
        with patch.object(ppr, "DATA_DIR", str(tmp_path)):
            with patch.object(
                ppr, "_year_path", lambda y: str(tmp_path / f"PPR-{y}.csv")
            ):
                # Create only 2022 file, leave others missing
                (tmp_path / "PPR-2022.csv").touch()
                years = _years_to_download()
                assert 2022 not in years
                assert 2021 in years

    def test_current_year_always_included_even_if_file_exists(self, tmp_path):
        current = date.today().year
        with patch.object(ppr, "DATA_DIR", str(tmp_path)):
            with patch.object(
                ppr, "_year_path", lambda y: str(tmp_path / f"PPR-{y}.csv")
            ):
                (tmp_path / f"PPR-{current}.csv").touch()
                years = _years_to_download()
                assert current in years


class TestLoadPpr:
    def _make_year_csv(self, directory, year, rows):
        path = os.path.join(directory, f"PPR-{year}.csv")
        df = pd.DataFrame(rows)
        df.to_csv(path, index=False, encoding="utf-8")
        return path

    def _stub_row(self, year):
        return {
            "Date of Sale (dd/mm/yyyy)": f"01/06/{year}",
            "Address": "1 TEST ST",
            "County": "Dublin",
            "Eircode": "",
            "Price (€)": "€300,000.00",
            "Not Full Market Price": "No",
            "VAT Exclusive": "No",
            "Description of Property": "",
            "Property Size Description": "",
        }

    def test_loads_and_normalises_county(self, tmp_path):
        current_year = date.today().year
        self._make_year_csv(
            str(tmp_path),
            current_year,
            [
                {
                    **self._stub_row(current_year),
                    "Address": "1 TEST ST, DUBLIN 7",
                    "County": "Dublin",
                    "Price (€)": "€350,000.00",
                }
            ],
        )

        with patch.object(ppr, "DATA_DIR", str(tmp_path)):
            with patch.object(
                ppr, "_year_path", lambda y: str(tmp_path / f"PPR-{y}.csv")
            ):
                with patch("ppr.update_ppr"):
                    df = load_ppr()

        assert "_county_norm" in df.columns
        assert df.iloc[0]["_county_norm"] == "dublin"

    def test_price_cleaned_to_float(self, tmp_path):
        current_year = date.today().year
        self._make_year_csv(
            str(tmp_path),
            current_year,
            [
                {
                    **self._stub_row(current_year),
                    "Price (€)": "€350,000.00",
                }
            ],
        )

        with patch.object(ppr, "DATA_DIR", str(tmp_path)):
            with patch.object(
                ppr, "_year_path", lambda y: str(tmp_path / f"PPR-{y}.csv")
            ):
                with patch("ppr.update_ppr"):
                    df = load_ppr()

        assert df.iloc[0]["Price (€)"] == 350000.0

    def test_concatenates_multiple_years(self, tmp_path):
        current_year = date.today().year
        for year, address in [
            (current_year - 1, "1 OLD ST"),
            (current_year, "2 NEW ST"),
        ]:
            self._make_year_csv(
                str(tmp_path),
                year,
                [
                    {
                        **self._stub_row(year),
                        "Address": address,
                    }
                ],
            )

        with patch.object(ppr, "DATA_DIR", str(tmp_path)):
            with patch.object(
                ppr, "_year_path", lambda y: str(tmp_path / f"PPR-{y}.csv")
            ):
                with patch("ppr.update_ppr"):
                    df = load_ppr()

        assert len(df) == 2

    def test_raises_if_no_data_files(self, tmp_path):
        with patch.object(ppr, "DATA_DIR", str(tmp_path)):
            with patch("ppr.update_ppr"):  # skip download
                with pytest.raises(RuntimeError, match="No PPR data found"):
                    load_ppr()
