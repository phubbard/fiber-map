# fiber-map

A one-page, self-hosted watch on fiber internet buildout around a ZIP code: a map of
telecom construction permits, headline numbers, news, and links to the coverage
checkers. Think "Yahoo Finance, but the ticker is your neighborhood's fiber".

Pure Python 3 standard library, no pip installs. The page it produces makes **no
third-party requests at runtime**: Leaflet is vendored and the map tiles are cached
locally at build time.

## What it shows

| Panel | Source | Freshness |
|---|---|---|
| Banner | Companies that pulled their first permit here or city-wide, and new right-of-way permits in the box, over the last `new_window_days`. Items that appeared since your last visit on this browser are highlighted. A red warning appears when the page was built more than two days ago, which is how a dead cron job shows itself. | Each build |
| Permit pins and table | City of San Diego Development Services approvals (DataSD, daily CSV). Right-of-way construction permits and traffic-control permits held by telecom companies, with the job named in the scope line, e.g. `AT&T FIBER (A05EE9V)`. | Daily |
| Headline tiles | Counts from the permits: fiber jobs in the box in the last 12 months vs the prior 12, active permits, what is new since the last build, and the same fiber count city-wide. | Each build |
| News | Google News RSS, one query per topic in `config.json`. | Each build |
| Links | FCC National Broadband Map centred on the area, AT&T / T-Mobile / Google Fiber availability checkers, the City Project Finder. | Static |
| Watchlist | Frequent right-of-way permit holders city-wide that matched no telecom rule, so a newcomer with an unfamiliar name can be spotted and given a rule. | Each build |

Permits are a leading indicator: a company pulls a right-of-way permit weeks to
months before the crews show up, and the FCC map only updates twice a year.

## Run it

```bash
python3 -m fibermap build          # fetch permits, news, tiles; write site/data.js + site/areas/*.js
python3 -m fibermap serve          # http://127.0.0.1:8765/
python3 -m unittest discover -s tests -t .
```

After a build you can also just open `site/index.html` in a browser: the page reads
`data.js`, so no server is needed.

The first build downloads ~22 MB per year of permits (cached, conditional GET after
that), the Census ZCTA gazetteer if your config has no `center`, and a few hundred
OpenStreetMap tiles for the box. Later builds are small.

Nightly, on the host that serves it, `deploy.sh` pulls the repo, builds, and rsyncs
`site/` to `~/html/fiber-map` (override with `FIBERMAP_DEST`; set `FIBERMAP_NTFY` to a
ntfy.sh topic to hear about failures):

```cron
15 6 * * * $HOME/code/fiber-map/deploy.sh >> $HOME/logs/fiber-map.log 2>&1
```

Or serve `site/` directly with anything static (Caddy `file_server`,
`python3 -m http.server`).

## Several ZIPs on one page

`config.json` takes a list of areas; the page gets a dropdown, each ZIP has its own
URL (`…/#92126`) that friends can bookmark, and the dropdown shows how many new items
each ZIP has:

```json
"areas": [
  {"zip": "92122", "label": "University City (92122)", "radius_km": 2.5},
  {"zip": "92126", "label": "Mira Mesa (92126)"},
  {"zip": "92129", "label": "Rancho Peñasquitos (92129)", "zoom_offset": 0,
   "news": {"queries": [{"label": "PQ", "q": "\"Rancho Penasquitos\" fiber"}]}}
]
```

Per-area keys: `zip`, `label`, `center`, `radius_km`, `bbox`, `zoom_offset`, extra
`news.queries` and `links`. Permits are fetched once for the whole city; the build
writes `site/data.js` (the shared index, news and watchlist) plus `site/areas/<zip>.js`
per area, loaded on demand. A config with a single top-level `zip` still works.

## Point it at another ZIP

Copy `config.example.json` to `config.json` and edit:

- `zip`: the centre and a sensible radius are looked up from the Census ZCTA
  gazetteer. Override with `center: [lat, lng]` and `radius_km`, or give an explicit
  `bbox: [south, west, north, east]`.
- `zoom_offset`: how many levels to zoom in after the map fits the box (default 1, so
  the view is the ZIP rather than the box plus margin; 0 shows the whole box).
- `label`: the page title.
- `news.queries`: Google News searches. Provider-name queries work well
  (`"AT&T Fiber" "Austin"`); ZIP codes and neighborhood names return noise.
- `permits.source`: `sandiego` for addresses inside the City of San Diego, `none`
  elsewhere (you still get the map, the news and the links). See below for adding a city.
- `permits.extra_companies`: extra `{"name", "pattern"}` regex rules for local ISPs.
- `tiles.zooms`: zoom levels to cache. 13 to 16 is about 200 tiles for a 5 km box.

`python3 -m fibermap resolve-zip 78704` prints what the gazetteer knows about a ZIP.

## Adding a permit source for another city

Each source is a module in `fibermap/permits/` exposing
`fetch(cfg, cache_dir) -> (list[Permit], info)` and registered in
`fibermap/permits/__init__.py`. `Permit` is in `permits/base.py`; `classify.py` turns
holder and scope text into a company name and is shared. Most cities publish permits
through Socrata, ArcGIS Hub or a CSV export; the only hard requirements are a stable
permit id, a lat/long, a status and some free text naming the applicant.

## Layout

```
fibermap/            the package (python3 -m fibermap)
  config.py          load config.json, normalise the list of areas, resolve a ZIP to a box
  zcta.py            Census ZCTA gazetteer lookup
  geo.py             bbox and tile maths
  permits/           source adapters (sandiego.py) + classifier
  news.py            Google News RSS
  tiles.py           OSM tile cache for the box
  history.py         first-seen dates for "new" badges
  build.py           writes site/data.json
site/                static page: index.html, app.js, style.css, vendor/leaflet
data/                caches and state (git-ignored)
tests/               unittest
```

## Data notes

- FCC National Broadband Map data has twice-yearly as-of dates (June 30, December 31)
  published about four months later; the page links to it rather than mirroring it.
  Bulk downloads need a free BDC API account; a future version could draw the fiber
  footprint from those files.
- Permit holders are sometimes people (the contractor's PM), so classification reads
  the scope text too. A holder whose name says telecom (Communications, Networks,
  Broadband, Wireless, ...) is kept under that name even when the scope never says
  "fiber", so a newcomer appears before anyone writes a rule for it. SDG&E and
  water/sewer work are excluded even when they mention fiber.
- Many AT&T "fiber" permits are a single drop from a street cabinet to one property
  ("... to property owner's demarcation point"). Those are tagged `drop` so a street of
  business hookups does not read as a neighborhood build.
- Permits still in "Opened" status often have no coordinates yet, so the most
  forward-looking filings can be missing from the map until they are issued.
- "New" means first seen by this tool within `new_window_days`; on the very first build
  items are dated by their own permit or publication date instead.
