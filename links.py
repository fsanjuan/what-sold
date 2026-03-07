import re
import time
from urllib.parse import urlencode

import requests

TARGET_DOMAINS = ("daft.ie", "myhome.ie")

# URL path patterns that indicate a real listing page worth linking to
_VALID_URL_PATTERNS = (
    "myhome.ie/residential/brochure/",
    "daft.ie/for-sale/",
    "daft.ie/new-homes/",
)


def _extract_search_terms(address: str) -> str:
    """
    Extract meaningful search terms from a PPR address.
    Keeps the unit number (e.g. "116" from "APT 116") so searches are apartment-specific.
    """
    address = address.strip()

    # Capture the unit number from "APT XX" / "APARTMENT XX" style prefixes
    apt_match = re.match(
        r'^\s*(?:APT|APARTMENT|UNIT|FLAT|NO\.?)\s+([\w-]+)',
        address, flags=re.IGNORECASE
    )
    unit_id = apt_match.group(1) if apt_match else None

    # Strip the full apartment prefix, including an optional dash-separated block label
    # e.g. "APT 116 - BLK A1, " or "APT 58 BLOCK B, " or "APT 66, "
    cleaned = re.sub(
        r'^\s*(?:APT|APARTMENT|UNIT|FLAT|NO\.?)\s+[\w-]+(?:\s*[-,/]\s*(?:BLK|BLOCK)\s+[\w-]+)?\s*[,]?\s*',
        '', address, flags=re.IGNORECASE
    )
    # Strip a standalone BLOCK/BLK prefix that may remain after the apt strip
    cleaned = re.sub(
        r'^\s*(?:BLOCK|BLK)\s+[\w-]+\s*[,]?\s*',
        '', cleaned, flags=re.IGNORECASE
    )

    parts = [p.strip() for p in cleaned.split(',')]
    meaningful = [
        p for p in parts
        if p
        and not re.match(r'^(Dublin|Cork|Galway|Limerick|Waterford|D\d)', p, re.IGNORECASE)
        and not re.match(r'^Co\.?\s+', p, re.IGNORECASE)
    ]

    if unit_id:
        # Skip any remaining block-code fragments (e.g. "BLOCKA") to find the street name
        street_parts = [p for p in meaningful if not re.match(r'^(BLOCK|BLK)\w*', p, re.IGNORECASE)]
        street = street_parts[0] if street_parts else (meaningful[0] if meaningful else '')
        return f"{unit_id} {street}".strip() if street else unit_id

    return ' '.join(meaningful[:2])


def build_search_url(address: str) -> str:
    """Return a Google search URL to find the property listing on Daft or MyHome."""
    terms = _extract_search_terms(address)
    query = f'site:myhome.ie/residential/brochure OR site:daft.ie/for-sale {terms}'
    return "https://www.google.com/search?" + urlencode({"q": query})


def _first_valid_url(candidates: list[str]) -> str | None:
    return next((c for c in candidates if any(p in c for p in _VALID_URL_PATTERNS)), None)


def resolve_listing_urls(
    addresses: list[str],
    api_key: str,
    progress_callback=None,
    delay: float = 0.2,
    debug: bool = False,
) -> list[str | None]:
    """
    Use Serper.dev (Google Search API) to find a daft.ie/myhome.ie listing for each address.
    Returns a list in the same order as input, None where not found.
    progress_callback(i, address, url_or_None) is called after each result.

    Requires a Serper API key (set SERPER_API_KEY env var).
    Free tier: 2500 queries/month — https://serper.dev
    """
    results: list[str | None] = []

    for i, address in enumerate(addresses):
        terms = _extract_search_terms(address)
        url: str | None = None

        if terms:
            query = f'site:myhome.ie/residential/brochure OR site:daft.ie/for-sale {terms}'
            try:
                resp = requests.post(
                    "https://google.serper.dev/search",
                    headers={"X-API-KEY": api_key, "Content-Type": "application/json"},
                    json={"q": query, "gl": "ie", "hl": "en", "num": 5},
                    timeout=10,
                )
                resp.raise_for_status()
                candidates = [r.get("link", "") for r in resp.json().get("organic", [])]
                if debug:
                    print(f"    [debug] query: {query}")
                    print(f"    [debug] results: {candidates}")
                url = _first_valid_url(candidates)
            except requests.RequestException:
                pass

        results.append(url)
        if progress_callback:
            progress_callback(i, address, url)

        if i < len(addresses) - 1:
            time.sleep(delay)

    return results
