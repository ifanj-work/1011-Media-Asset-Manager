# 1011 Media Asset Manager

Internal demo-first media asset manager for the 1011 creative team.

The app is built with Flask, SQLite, and vanilla JavaScript. Phase 1 focuses on a stable searchable catalog, controlled tags, collections, and predictable API behavior against seeded demo data.

## Current Scope

- Library search with filters, sorting, date range, keyboard navigation, and detail modal
- On-demand cached thumbnails for image files Pillow can decode
- Controlled tag vocabulary with create, merge, delete, and per-file tagging
- Collections with create, add/remove items, and collection detail browsing
- Dashboard stats and recent activity
- Demo-safe downloads and file actions when originals are missing from disk

## Deferred

These are intentionally out of scope for the current milestone:

- Real LAN ingestion and background indexing
- Upload/import UI
- Settings workflow
- EXIF extraction beyond the current placeholder metadata
- Video thumbnail extraction and broader design-file thumbnail support
- Saved searches, sharing, auth, and AI tagging

## Local Run

Requirements:

- Python 3.11+
- Flask installed in your environment

Start the app:

```bash
python app.py
```

The server runs at `http://localhost:5000`.

## Tests

Run the Flask regression suite:

```bash
python -B -m unittest discover -s tests -v
```

The tests create a fresh temporary SQLite database per test case and do not touch your working `photo_catalog.db`.

## Database Behavior

By default the app uses:

```text
photo_catalog.db
```

You can override it with:

```text
DB_PATH=/path/to/another.db
```

The saved library path in the dashboard supports multiple scan roots separated by `;`, for example:

```text
\\172.16.0.25\data; \\172.16.0.25\data xxv
```

On startup the catalog manager will:

1. Create missing schema objects
2. Seed the demo dataset when the database is empty
3. Migrate older FTS layouts to the standalone `photos_fts(id, haystack)` index
4. Backfill the tag vocabulary from existing assignments
5. Rebuild the FTS index when counts are out of sync

This keeps older prototype databases usable without a separate migration command.

## Main Routes

Pages:

- `/`
- `/search`
- `/tags`
- `/collections`
- `/collections/<id>`

JSON APIs:

- `GET /api/search`
- `GET /api/file/<id>`
- `POST /api/file/<id>/tags`
- `POST /api/batch/tags`
- `GET /api/tags`
- `POST /api/tags`
- `POST /api/tags/merge`
- `DELETE /api/tags/<tag>`
- `GET /api/collections`
- `POST /api/collections`
- `GET /api/collections/<id>/items`
- `POST /api/collections/<id>/items`

## Project Structure

```text
app.py                 Flask routes and API surface
catalog.py             SQLite catalog manager and seed/migration logic
templates/             Server-rendered HTML templates
static/js/             Page scripts and UI components
static/css/            Design system and component styles
PRD/                   Product requirements
SKILLS/                Local skills bundled with the project
tests/                 Flask regression tests
```

## Notes

- The seeded catalog is the primary Phase 1 dataset.
- Missing original files are expected in demo mode; the UI stays in-app and reports that the asset is unavailable.
- `/api/thumb/<id>` now generates cached JPEG thumbnails for decodable image files and falls back to placeholder artwork for missing or unsupported originals.
- `/api/scan` accepts one or more library roots separated by `;` and will scan valid paths even if some entries are invalid.
- `directives/` and `execution/` remain reserved for future deterministic workflows. This milestone does not force a refactor into that architecture.
