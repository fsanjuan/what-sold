# what-sold

When looking for a property to buy in Ireland, one of the first things worth doing is checking what has actually sold nearby — and for how much. The [Property Price Register](https://www.propertypriceregister.ie/) (PPR) has all of that data, but browsing it manually and copy-pasting results into a spreadsheet is tedious. This tool automates exactly that: give it a street or development name and it produces a ready-to-use Excel spreadsheet in under a minute.

## What it does

1. Downloads PPR data (full register, 2010–present) and caches it locally
2. Asks you for a street/area, county, and how far back to search
3. Fuzzy-matches addresses in the register against your query
4. Writes an Excel spreadsheet with matching sales — address, date, price, property type, and a Google search link to find the listing on Daft or MyHome
5. Optionally resolves those Google links to direct Daft/MyHome listing URLs using the [Serper API](https://serper.dev)

## Requirements

- Python 3.12+
- A Chromium browser (installed via Playwright on first run)
- _(Optional)_ A [Serper API key](https://serper.dev) for direct link resolution (free tier: 2 500 queries/month)

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
playwright install chromium
```

## Usage

```bash
source .venv/bin/activate
python3 main.py
```

You'll be prompted for:

| Prompt | Example |
|--------|---------|
| Street/area | `Main Street` or a development name |
| County | `Dublin`, `Cork`, `Galway`, … |
| Months back to search | `24` |
| Resolve Daft/MyHome links? | `y` / `N` / `debug` |

The last prompt only appears if `SERPER_API_KEY` is set in your environment (see below). Enter `debug` to print the exact search queries and raw API results.

Output is saved to `output/`, e.g. `output/main_street_dublin_2026-03-08.xlsx`.

## Link resolution (optional)

Each row in the spreadsheet includes a Google search link you can open manually. If you want the script to resolve these to direct listing URLs automatically, sign up at [serper.dev](https://serper.dev) and set your key:

```bash
export SERPER_API_KEY=your_key_here
```

Then answer `y` when prompted.

### Why link resolution isn't 100% reliable

The PPR records the address as it was registered at the time of sale. Listing sites (Daft, MyHome) use their own address formats, which often differ — abbreviated development names, different block labelling, missing unit numbers, etc. The script works around this by:

- Expanding common PPR abbreviations before searching (e.g. `RD` → `ROAD`, `AVE` → `AVENUE`)
- Quoting the development name as a phrase in the search query to avoid results from nearby developments
- Including the block identifier in the query
- Validating that the house/unit number, block letter, and a distinctive word from the street name all appear in the returned URL slug
- Distinguishing lettered house suffixes (e.g. `116B`) from block indicators (e.g. `89C` in a development) when validating URLs
- Skipping link resolution entirely for dual-property sales (e.g. `6 & 6A`), which have no single listing to link to

Despite these heuristics, some listings won't be found because:

- The listing has since been removed or archived
- The address format on the listing site is too different from the PPR record to match reliably
- The property never had a public listing (e.g. new-build purchased off-plan directly from a developer)
- Multiple units share a very similar address, leading to ambiguous results

For unresolved addresses, the spreadsheet still includes a Google search link so you can look them up manually.

## PPR data cache

Data is stored in `data/PPR-{year}.csv`. Historical years (2010 to last year) are downloaded once and kept. The current year's file is refreshed automatically if it is more than 1 day old. To force a full re-download, delete the `data/` directory.

## Running tests

```bash
source .venv/bin/activate
pytest
```

## Docker

**Run the tool:**
```bash
docker build -t what-sold .
docker run -it -v $(pwd)/output:/app/output what-sold
```

Pass a Serper API key to enable link resolution:
```bash
docker run -it -e SERPER_API_KEY=your_key_here -v $(pwd)/output:/app/output what-sold
```

The `-v` flag mounts your local `output/` directory into the container so generated spreadsheets are saved to your machine.

**Run the tests:**
```bash
docker build --target test -t what-sold-test .
docker run what-sold-test
```
