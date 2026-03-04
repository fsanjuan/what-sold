import io
import os
from datetime import date, datetime

import pandas as pd

CACHE_PATH = os.path.join(os.path.dirname(__file__), "data", "PPR-ALL.csv")
PPR_BASE = "https://www.propertypriceregister.ie"
START_YEAR = 2010



def download_ppr(cache_path: str = CACHE_PATH) -> None:
    from playwright.sync_api import sync_playwright

    os.makedirs(os.path.dirname(cache_path), exist_ok=True)
    current_year = date.today().year
    years = list(range(START_YEAR, current_year + 1))

    print(f"Downloading PPR data for {START_YEAR}–{current_year} (this may take a while)...")

    frames = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        # Load the form once to establish session and solve the bot challenge
        page.goto(f"{PPR_BASE}/website/npsra/pprweb.nsf/PPRDownloads?OpenForm",
                  wait_until="networkidle", timeout=30000)
        page.wait_for_timeout(3000)

        for i, year in enumerate(years):
            print(f"  {year}... ({i + 1}/{len(years)})", end="\r", flush=True)

            try:
                page.select_option("#County", "ALL")
                page.select_option("#Year", str(year))
                page.select_option("#StartMonth", "ALL")
                page.click("input[value='Perform Download']")
                page.wait_for_load_state("networkidle")
                page.wait_for_timeout(1000)

                link = page.query_selector("a[href*='npsra-ppr.nsf/Downloads']")
                if not link:
                    print(f"  {year}: no download link found, skipping.")
                    continue

                href = link.get_attribute("href")
                csv_url = href if href.startswith("http") else f"{PPR_BASE}{href}"

                csv_text = page.evaluate(f"""
                    async () => {{
                        const r = await fetch('{csv_url}');
                        if (!r.ok) throw new Error('HTTP ' + r.status);
                        return await r.text();
                    }}
                """)
                df = pd.read_csv(io.StringIO(csv_text), dtype=str)
                frames.append(df)
            except Exception as e:
                print(f"  {year}: failed ({e}), skipping.")

        browser.close()

    if not frames:
        raise RuntimeError("No PPR data downloaded. Check your internet connection.")

    combined = pd.concat(frames, ignore_index=True)
    combined.to_csv(cache_path, index=False, encoding="utf-8")
    print(f"\nSaved {len(combined):,} records to {cache_path}")


def load_ppr(cache_path: str = CACHE_PATH) -> pd.DataFrame:
    if not os.path.exists(cache_path):
        download_ppr(cache_path)
    else:
        mtime = os.path.getmtime(cache_path)
        age = datetime.now() - datetime.fromtimestamp(mtime)
        print(f"Using cached PPR data (downloaded {age.days} day(s) ago). "
              "Delete data/PPR-ALL.csv to refresh.")

    df = pd.read_csv(cache_path, dtype=str, encoding="utf-8", on_bad_lines="skip")

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
