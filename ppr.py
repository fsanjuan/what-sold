import io
import os
from datetime import date, datetime

import pandas as pd

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
PPR_BASE = "https://www.propertypriceregister.ie"
START_YEAR = 2010


def _year_path(year: int) -> str:
    return os.path.join(DATA_DIR, f"PPR-{year}.csv")


def _years_to_download() -> list[int]:
    current_year = date.today().year
    missing = [y for y in range(START_YEAR, current_year) if not os.path.exists(_year_path(y))]
    # Current year is always refreshed
    return missing + [current_year]


def _fetch_year(page, year: int) -> pd.DataFrame | None:
    page.select_option("#County", "ALL")
    page.select_option("#Year", str(year))
    page.select_option("#StartMonth", "ALL")
    page.click("input[value='Perform Download']")
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(1000)

    link = page.query_selector("a[href*='npsra-ppr.nsf/Downloads']")
    if not link:
        return None

    href = link.get_attribute("href")
    csv_url = href if href.startswith("http") else f"{PPR_BASE}{href}"

    csv_text = page.evaluate(f"""
        async () => {{
            const r = await fetch('{csv_url}');
            if (!r.ok) throw new Error('HTTP ' + r.status);
            return await r.text();
        }}
    """)
    return pd.read_csv(io.StringIO(csv_text), dtype=str)


def update_ppr() -> None:
    from playwright.sync_api import sync_playwright

    os.makedirs(DATA_DIR, exist_ok=True)
    years = _years_to_download()

    if not years:
        return

    current_year = date.today().year
    print(f"Fetching {len(years)} year(s): {', '.join(str(y) for y in years)}")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        page.goto(f"{PPR_BASE}/website/npsra/pprweb.nsf/PPRDownloads?OpenForm",
                  wait_until="networkidle", timeout=30000)
        page.wait_for_timeout(3000)

        for i, year in enumerate(years):
            label = f"{year} (current)" if year == current_year else str(year)
            print(f"  Downloading {label}... ({i + 1}/{len(years)})", end="\r", flush=True)
            try:
                df = _fetch_year(page, year)
                if df is None:
                    print(f"  {year}: no download link found, skipping.")
                    continue
                df.to_csv(_year_path(year), index=False, encoding="utf-8")
            except Exception as e:
                print(f"  {year}: failed ({e}), skipping.")

        browser.close()

    print(f"\nDone. Data saved to {DATA_DIR}/")


def load_ppr() -> pd.DataFrame:
    current_year = date.today().year
    current_path = _year_path(current_year)

    # Refresh current year if missing or older than 1 day
    needs_refresh = not os.path.exists(current_path)
    if not needs_refresh:
        age = datetime.now() - datetime.fromtimestamp(os.path.getmtime(current_path))
        needs_refresh = age.days >= 1

    # Also download any missing historical years
    missing_historical = [y for y in range(START_YEAR, current_year) if not os.path.exists(_year_path(y))]

    if needs_refresh or missing_historical:
        update_ppr()

    year_files = sorted(
        f for f in os.listdir(DATA_DIR) if f.startswith("PPR-") and f.endswith(".csv")
    )
    if not year_files:
        raise RuntimeError("No PPR data found in data/. Delete data/ and re-run to re-download.")

    ages = []
    for f in year_files:
        mtime = datetime.fromtimestamp(os.path.getmtime(os.path.join(DATA_DIR, f)))
        ages.append(f"{f}: {(datetime.now() - mtime).days}d old")
    print(f"Loaded {len(year_files)} year file(s). Current year last updated: "
          f"{(datetime.now() - datetime.fromtimestamp(os.path.getmtime(current_path))).days}d ago.")

    frames = [
        pd.read_csv(os.path.join(DATA_DIR, f), dtype=str, encoding="utf-8", on_bad_lines="skip")
        for f in year_files
    ]
    df = pd.concat(frames, ignore_index=True)

    df.columns = [c.strip() for c in df.columns]
    df["_county_norm"] = df["County"].str.strip().str.lower()
    df["Price (€)"] = (
        df["Price (€)"]
        .str.replace("€", "", regex=False)
        .str.replace(",", "", regex=False)
        .str.strip()
        .astype(float, errors="ignore")
    )

    return df
