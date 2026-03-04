import re
from urllib.parse import urlencode


def _extract_search_terms(address: str) -> str:
    """Strip apartment/block prefixes and return the meaningful part of a PPR address."""
    # Remove leading unit designators: APT 10, APARTMENT 5B, BLOCK A, UNIT 3, FLAT 2, NO. 5
    cleaned = re.sub(
        r'^\s*(APT|APARTMENT|UNIT|FLAT|NO\.?)\s+[\w-]+\s*,?\s*',
        '', address.strip(), flags=re.IGNORECASE
    )
    cleaned = re.sub(
        r'^\s*(BLOCK|BLK)\s+[\w-]+\s*,?\s*',
        '', cleaned, flags=re.IGNORECASE
    )

    # Split by comma, drop parts that look like Dublin postcodes or county names
    parts = [p.strip() for p in cleaned.split(',')]
    meaningful = [
        p for p in parts
        if p
        and not re.match(r'^(Dublin|Cork|Galway|Limerick|Waterford|D\d)', p, re.IGNORECASE)
        and not re.match(r'^Co\.?\s+', p, re.IGNORECASE)
    ]

    # Take the first two meaningful parts
    return ' '.join(meaningful[:2])


def build_search_url(address: str) -> str:
    """Return a Google search URL to find the property on Daft or MyHome."""
    terms = _extract_search_terms(address)
    query = f'site:daft.ie OR site:myhome.ie "{terms}"'
    return "https://www.google.com/search?" + urlencode({"q": query})
