import os
import re
from datetime import date

from ppr import load_ppr
from matcher import find_matches
from spreadsheet import generate_spreadsheet
from links import build_search_url, resolve_listing_urls, _build_query


def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"\s+", "_", text)
    return text


def main():
    print("what-sold")
    print("---------")
    print("Searches the Irish Property Price Register for similar nearby sales.\n")

    street = input("Street/area (e.g. Griffith Avenue, Dublin): ").strip()
    if not street:
        print("No address entered. Exiting.")
        return

    county = input("County (e.g. Dublin, Cork, Galway): ").strip()
    if not county:
        print("No county entered. Exiting.")
        return

    months_input = input("How many months back to search? [24]: ").strip()
    months = int(months_input) if months_input.isdigit() else 24

    print("\nLoading PPR data...")
    df = load_ppr()

    print(f"Searching for '{street}' in {county} (past {months} months)...")
    matches = find_matches(df, street, county, months=months)

    if matches.empty:
        print("No matches found. Try a broader street name or check the county spelling.")
        return

    print(f"Found {len(matches)} match(es).")

    serper_key = os.environ.get("SERPER_API_KEY", "").strip()
    resolve = input("Resolve Daft/MyHome links? [y/N/debug]: ").strip().lower() if serper_key else "n"
    if resolve in ("y", "debug") and serper_key:
        debug = resolve == "debug"
        print("Searching for listings...")
        address_list = [str(row.get("Address", "")).strip() for _, row in matches.iterrows()]
        idx_list = list(matches.index)
        total = len(address_list)

        def on_result(i, address, url):
            prefix = f"  [{i + 1}/{total}] {address[:55]:<55}"
            suffix = url or f'not found  (searched: {_build_query(address)})'
            print(f"{prefix} → {suffix}")

        url_list = resolve_listing_urls(
            address_list, api_key=serper_key,
            progress_callback=on_result, debug=debug,
        )
        urls = dict(zip(idx_list, url_list))
        matches = matches.copy()
        matches["_listing_url"] = matches.index.map(urls)
        found = sum(1 for v in urls.values() if v)
        print(f"  {found}/{len(matches)} listing(s) found.")
    elif resolve == "y" and not serper_key:
        print("  Skipping — set SERPER_API_KEY environment variable to enable link resolution.")

    slug = slugify(f"{street}_{county}")
    filename = f"{slug}_{date.today()}.xlsx"
    output_dir = os.path.join(os.path.dirname(__file__), "output")
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, filename)

    generate_spreadsheet(matches, output_path)
    print(f"\nSaved to: output/{filename}")


if __name__ == "__main__":
    main()
