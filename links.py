import re
import time
from urllib.parse import urlencode, unquote

import requests

TARGET_DOMAINS = ("daft.ie", "myhome.ie")


def _extract_search_terms(address: str) -> str:
    """Strip apartment/block prefixes and return the meaningful part of a PPR address."""
    cleaned = re.sub(
        r'^\s*(APT|APARTMENT|UNIT|FLAT|NO\.?)\s+[\w-]+\s*,?\s*',
        '', address.strip(), flags=re.IGNORECASE
    )
    # Strip a leading dash/hyphen that may remain after APT stripping (e.g. "APT 116 - BLK A1")
    cleaned = re.sub(r'^\s*-\s*', '', cleaned)
    cleaned = re.sub(
        r'^\s*(BLOCK|BLK)\s+[\w-]+\s*,?\s*',
        '', cleaned, flags=re.IGNORECASE
    )

    parts = [p.strip() for p in cleaned.split(',')]
    meaningful = [
        p for p in parts
        if p
        and not re.match(r'^(Dublin|Cork|Galway|Limerick|Waterford|D\d)', p, re.IGNORECASE)
        and not re.match(r'^Co\.?\s+', p, re.IGNORECASE)
    ]

    return ' '.join(meaningful[:2])


def build_search_url(address: str) -> str:
    """Return a Google search URL to find the property on Daft or MyHome."""
    terms = _extract_search_terms(address)
    query = f'site:daft.ie OR site:myhome.ie "{terms}"'
    return "https://www.google.com/search?" + urlencode({"q": query})


def resolve_listing_urls(
    addresses: list[str],
    api_key: str,
    progress_callback=None,
    delay: float = 0.2,
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
            query = f'site:daft.ie OR site:myhome.ie "{terms}"'
            try:
                resp = requests.post(
                    "https://google.serper.dev/search",
                    headers={"X-API-KEY": api_key, "Content-Type": "application/json"},
                    json={"q": query, "gl": "ie", "hl": "en", "num": 3},
                    timeout=10,
                )
                resp.raise_for_status()
                for result in resp.json().get("organic", []):
                    candidate = result.get("link", "")
                    if any(domain in candidate for domain in TARGET_DOMAINS):
                        url = candidate
                        break
            except requests.RequestException:
                pass

        results.append(url)
        if progress_callback:
            progress_callback(i, address, url)

        if i < len(addresses) - 1:
            time.sleep(delay)

    return results
