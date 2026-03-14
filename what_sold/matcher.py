from datetime import date

import pandas as pd
from dateutil.relativedelta import relativedelta
from rapidfuzz import fuzz, process


def find_matches(
    df: pd.DataFrame,
    street_query: str,
    county: str,
    months: int = 24,
    threshold: int = 70,
    limit: int = 200,
) -> pd.DataFrame:
    county_norm = county.strip().lower()

    county_df = df[df["_county_norm"] == county_norm].copy()
    if county_df.empty:
        # Try partial match in case user typed e.g. "Co. Dublin" vs "Dublin"
        county_df = df[df["_county_norm"].str.contains(county_norm, na=False)].copy()

    if county_df.empty:
        print(
            f"No records found for county '{county}'. "
            "Check spelling (e.g. 'Dublin', 'Cork', 'Galway')."
        )
        return pd.DataFrame()

    # Parse dates and filter by recency
    county_df["_date_parsed"] = pd.to_datetime(
        county_df["Date of Sale (dd/mm/yyyy)"], format="%d/%m/%Y", errors="coerce"
    )
    if months > 0:
        cutoff = date.today() - relativedelta(months=months)
        county_df = county_df[county_df["_date_parsed"] >= pd.Timestamp(cutoff)]

    if county_df.empty:
        print(f"No records found in the past {months} months. Try increasing the time window.")
        return pd.DataFrame()

    addresses = county_df["Address"].fillna("").tolist()
    addresses_lower = [a.lower() for a in addresses]
    query_lower = street_query.lower()

    # Pass 1: exact substring matches (case-insensitive) — always correct
    exact = [(i, 100) for i, a in enumerate(addresses_lower) if query_lower in a]

    if exact:
        matched_indices = [county_df.index[i] for i, _ in exact[:limit]]
        scores = [s for _, s in exact[:limit]]
    else:
        # Pass 2: fuzzy fallback for typos — higher threshold to reduce false positives
        results = process.extract(
            query_lower,
            addresses_lower,
            scorer=fuzz.partial_ratio,
            limit=limit,
            score_cutoff=max(threshold, 85),
        )
        if not results:
            return pd.DataFrame()
        matched_indices = [county_df.index[idx] for _, _, idx in results]
        scores = [score for _, score, _ in results]

    matches = county_df.loc[matched_indices].copy()
    matches["_score"] = scores

    matches = matches.sort_values(["_score", "_date_parsed"], ascending=[False, False])

    return matches
