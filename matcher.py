import pandas as pd
from rapidfuzz import process, fuzz


def find_matches(
    df: pd.DataFrame,
    street_query: str,
    county: str,
    threshold: int = 70,
    limit: int = 200,
) -> pd.DataFrame:
    county_norm = county.strip().lower()

    county_df = df[df["_county_norm"] == county_norm].copy()
    if county_df.empty:
        # Try partial match in case user typed e.g. "Co. Dublin" vs "Dublin"
        county_df = df[df["_county_norm"].str.contains(county_norm, na=False)].copy()

    if county_df.empty:
        print(f"No records found for county '{county}'. "
              "Check spelling (e.g. 'Dublin', 'Cork', 'Galway').")
        return pd.DataFrame()

    addresses = county_df["Address"].fillna("").tolist()

    results = process.extract(
        street_query,
        addresses,
        scorer=fuzz.partial_ratio,
        limit=limit,
        score_cutoff=threshold,
    )

    if not results:
        return pd.DataFrame()

    matched_indices = [county_df.index[idx] for _, _, idx in results]
    scores = [score for _, score, _ in results]

    matches = county_df.loc[matched_indices].copy()
    matches["_score"] = scores

    # Parse dates for sorting
    matches["_date_parsed"] = pd.to_datetime(
        matches["Date of Sale (dd/mm/yyyy)"], format="%d/%m/%Y", errors="coerce"
    )

    matches = matches.sort_values(
        ["_score", "_date_parsed"], ascending=[False, False]
    )

    return matches
