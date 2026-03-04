import os
import re
from datetime import date

from ppr import load_ppr
from matcher import find_matches
from spreadsheet import generate_spreadsheet


def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"\s+", "_", text)
    return text


def main():
    print("House Price Helper")
    print("------------------")
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

    slug = slugify(f"{street}_{county}")
    filename = f"{slug}_{date.today()}.xlsx"
    output_path = os.path.join(os.path.dirname(__file__), filename)

    generate_spreadsheet(matches, output_path)
    print(f"\nSaved to: {filename}")


if __name__ == "__main__":
    main()
