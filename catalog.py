"""
catalog.py — CatalogManager for 1011 Media Asset Manager
Wraps a SQLite database with WAL mode for concurrent reads.

Tables managed here:
  photos          — core file index
  photos_fts      — FTS5 full-text search index (virtual table)
  tags            — per-file tags
  tag_vocabulary  — controlled vocabulary for reusable tags
  tag_categories  — vocabulary / color for each tag category
  collections     — named virtual albums
  collection_items — collection membership
  activity_log    — JSON-structured event log
"""

import sqlite3
import json
import os
import re
import time
import uuid
from datetime import datetime, timezone
from contextlib import contextmanager
from pathlib import Path
from PIL import Image, ImageOps, UnidentifiedImageError

try:
    import exifread
except ImportError:  # pragma: no cover - optional dependency for metadata extraction
    exifread = None

DB_PATH = os.environ.get("DB_PATH", "photo_catalog.db")
PAGE_SIZE = 50  # default results per page


# ─────────────────────────────────────────────────────────────────────────────
#  Connection helper
# ─────────────────────────────────────────────────────────────────────────────

@contextmanager
def get_connection(db_path: str = DB_PATH):
    """Yield a WAL-mode SQLite connection that returns Row objects."""
    conn = sqlite3.connect(db_path, timeout=10, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA cache_size=-32000")   # 32 MB page cache
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# ─────────────────────────────────────────────────────────────────────────────
#  CatalogManager
# ─────────────────────────────────────────────────────────────────────────────

class CatalogManager:
    """High-level interface for all database operations."""

    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self._init_schema()
        self._seed_demo_data()
        self._post_init_maintenance()

    def _post_init_maintenance(self):
        """Run light schema/data maintenance needed for older prototypes."""
        with get_connection(self.db_path) as conn:
            recreated_fts = self._ensure_fts_table(conn)
            self._sync_tag_vocabulary(conn)
            self._sync_collection_covers(conn)
            if recreated_fts or self._fts_needs_rebuild(conn):
                self._rebuild_fts(conn)

    # ── Schema ────────────────────────────────────────────────────────────────

    def _init_schema(self):
        """Create all tables if they don't exist. Idempotent."""
        with get_connection(self.db_path) as conn:
            conn.executescript("""
                -- Core file index
                CREATE TABLE IF NOT EXISTS photos (
                    id       TEXT PRIMARY KEY,
                    path     TEXT NOT NULL UNIQUE,
                    filename TEXT NOT NULL,
                    folder   TEXT NOT NULL,
                    size     INTEGER DEFAULT 0,
                    mtime    REAL DEFAULT 0,
                    date     TEXT,
                    year     TEXT,
                    month    TEXT,
                    ext      TEXT,
                    width    INTEGER DEFAULT 0,
                    height   INTEGER DEFAULT 0,
                    duration REAL DEFAULT 0,
                    indexed_at TEXT DEFAULT CURRENT_TIMESTAMP
                );

                -- Standalone FTS5 virtual table for full-text search
                CREATE VIRTUAL TABLE IF NOT EXISTS photos_fts USING fts5(
                    id UNINDEXED,
                    haystack
                );

                -- Per-file tags
                CREATE TABLE IF NOT EXISTS tags (
                    id         INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_id    TEXT NOT NULL,
                    tag        TEXT NOT NULL,
                    category   TEXT DEFAULT 'custom',
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(file_id, tag),
                    FOREIGN KEY (file_id) REFERENCES photos(id) ON DELETE CASCADE
                );

                -- Tag controlled vocabulary
                CREATE TABLE IF NOT EXISTS tag_vocabulary (
                    id         INTEGER PRIMARY KEY AUTOINCREMENT,
                    tag        TEXT NOT NULL UNIQUE,
                    category   TEXT DEFAULT 'custom',
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                );

                -- Tag controlled vocabulary
                CREATE TABLE IF NOT EXISTS tag_categories (
                    id         INTEGER PRIMARY KEY AUTOINCREMENT,
                    name       TEXT NOT NULL UNIQUE,
                    color      TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                );

                -- Collections (virtual albums)
                CREATE TABLE IF NOT EXISTS collections (
                    id            INTEGER PRIMARY KEY AUTOINCREMENT,
                    name          TEXT NOT NULL,
                    description   TEXT,
                    cover_file_id TEXT,
                    created_at    TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at    TEXT DEFAULT CURRENT_TIMESTAMP
                );

                -- Collection membership
                CREATE TABLE IF NOT EXISTS collection_items (
                    id            INTEGER PRIMARY KEY AUTOINCREMENT,
                    collection_id INTEGER NOT NULL,
                    file_id       TEXT NOT NULL,
                    added_at      TEXT DEFAULT CURRENT_TIMESTAMP,
                    sort_order    INTEGER DEFAULT 0,
                    UNIQUE(collection_id, file_id),
                    FOREIGN KEY (collection_id) REFERENCES collections(id) ON DELETE CASCADE,
                    FOREIGN KEY (file_id)       REFERENCES photos(id)      ON DELETE CASCADE
                );

                -- Activity log
                CREATE TABLE IF NOT EXISTS activity_log (
                    id         INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_type TEXT NOT NULL,
                    details    TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                );

                -- Extracted media metadata
                CREATE TABLE IF NOT EXISTS photo_metadata (
                    file_id        TEXT PRIMARY KEY,
                    make           TEXT,
                    model          TEXT,
                    lens           TEXT,
                    iso            INTEGER,
                    focal_length   REAL,
                    aperture       REAL,
                    shutter_speed  TEXT,
                    captured_at    TEXT,
                    gps_latitude   REAL,
                    gps_longitude  REAL,
                    raw_json       TEXT,
                    created_at     TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at     TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (file_id) REFERENCES photos(id) ON DELETE CASCADE
                );

                -- Shared saved searches
                CREATE TABLE IF NOT EXISTS saved_searches (
                    id            INTEGER PRIMARY KEY AUTOINCREMENT,
                    name          TEXT NOT NULL UNIQUE,
                    query         TEXT DEFAULT '',
                    file_type     TEXT DEFAULT 'all',
                    sort          TEXT DEFAULT 'newest',
                    date_from     TEXT,
                    date_to       TEXT,
                    folder_prefix TEXT,
                    created_at    TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at    TEXT DEFAULT CURRENT_TIMESTAMP
                );

                -- App Settings
                CREATE TABLE IF NOT EXISTS settings (
                    key   TEXT PRIMARY KEY,
                    value TEXT
                );

                -- Indexes
                CREATE INDEX IF NOT EXISTS idx_photos_folder  ON photos(folder);
                CREATE INDEX IF NOT EXISTS idx_photos_year    ON photos(year);
                CREATE INDEX IF NOT EXISTS idx_photos_ext     ON photos(ext);
                CREATE INDEX IF NOT EXISTS idx_photos_date    ON photos(date DESC);
                CREATE INDEX IF NOT EXISTS idx_tags_file      ON tags(file_id);
                CREATE INDEX IF NOT EXISTS idx_tags_tag       ON tags(tag);
                CREATE INDEX IF NOT EXISTS idx_tag_vocab_tag  ON tag_vocabulary(tag);
                CREATE INDEX IF NOT EXISTS idx_tag_vocab_cat  ON tag_vocabulary(category);
                CREATE INDEX IF NOT EXISTS idx_ci_collection  ON collection_items(collection_id);
                CREATE INDEX IF NOT EXISTS idx_ci_file        ON collection_items(file_id);
                CREATE INDEX IF NOT EXISTS idx_log_type       ON activity_log(event_type);
                CREATE INDEX IF NOT EXISTS idx_log_created    ON activity_log(created_at);
                CREATE INDEX IF NOT EXISTS idx_metadata_capture ON photo_metadata(captured_at);
                CREATE INDEX IF NOT EXISTS idx_saved_search_name ON saved_searches(name);
            """)

    def _ensure_fts_table(self, conn) -> bool:
        """
        Replace the older external-content FTS table with a standalone table.
        Returns True when the table was recreated and must be repopulated.
        """
        row = conn.execute("""
            SELECT sql
            FROM sqlite_master
            WHERE type = 'table' AND name = 'photos_fts'
        """).fetchone()

        if not row:
            conn.execute("CREATE VIRTUAL TABLE photos_fts USING fts5(id UNINDEXED, haystack)")
            return True

        sql = (row["sql"] or "").lower()
        if "content=photos" in sql:
            conn.execute("DROP TABLE IF EXISTS photos_fts")
            conn.execute("CREATE VIRTUAL TABLE photos_fts USING fts5(id UNINDEXED, haystack)")
            return True

        return False

    def _fts_needs_rebuild(self, conn) -> bool:
        photo_count = conn.execute("SELECT COUNT(*) FROM photos").fetchone()[0]
        fts_count = conn.execute("SELECT COUNT(*) FROM photos_fts").fetchone()[0]
        return photo_count != fts_count

    def _rebuild_fts(self, conn):
        """Rebuild the full-text index from current photos and tag assignments."""
        rows = conn.execute("""
            SELECT p.id,
                   p.filename,
                   p.folder,
                   p.date,
                   p.year,
                   GROUP_CONCAT(t.tag, ' ') AS tag_str
            FROM photos p
            LEFT JOIN tags t ON t.file_id = p.id
            GROUP BY p.id
        """).fetchall()

        conn.execute("DELETE FROM photos_fts")
        payload = []
        for row in rows:
            haystack = " ".join(filter(None, [
                row["filename"],
                row["folder"],
                row["date"],
                row["year"],
                row["tag_str"],
            ]))
            payload.append((row["id"], haystack))

        conn.executemany("""
            INSERT INTO photos_fts (id, haystack)
            VALUES (?, ?)
        """, payload)

    def _sync_tag_vocabulary(self, conn):
        """Backfill vocabulary rows from existing tag assignments."""
        rows = conn.execute("""
            SELECT t.tag, t.category
            FROM tags t
            JOIN (
                SELECT tag, MAX(created_at) AS max_created_at
                FROM tags
                GROUP BY tag
            ) latest
              ON latest.tag = t.tag
             AND latest.max_created_at = t.created_at
            GROUP BY t.tag
        """).fetchall()

        for row in rows:
            self._ensure_tag_vocabulary(conn, row["tag"], row["category"])

    def _sync_collection_covers(self, conn):
        rows = conn.execute("""
            SELECT id FROM collections
        """).fetchall()
        for row in rows:
            self._refresh_collection_cover(conn, row["id"])

    # ── Demo seed data ─────────────────────────────────────────────────────────

    def _seed_demo_data(self):
        """Populate the DB with realistic demo data if it's empty."""
        with get_connection(self.db_path) as conn:
            count = conn.execute("SELECT COUNT(*) FROM photos").fetchone()[0]
            if count > 0:
                return  # already seeded

            DEMO_FILES = [
                {
                    "id": "f001", "path": "\\\\172.16.0.25\\data\\2026\\Match\\Match_Action_001.jpg",
                    "filename": "Match_Action_001.jpg", "folder": "2026/Match",
                    "size": 4404019, "date": "2026-04-06", "year": "2026", "month": "04", "ext": "jpg",
                    "width": 4000, "height": 3000, "duration": 0,
                    "tags": [("match", "event"), ("persija", "team"), ("2026", "year")],
                },
                {
                    "id": "f002", "path": "\\\\172.16.0.25\\data\\2026\\Match\\Goal_Celebration.mp4",
                    "filename": "Goal_Celebration.mp4", "folder": "2026/Match",
                    "size": 13107200, "date": "2026-04-05", "year": "2026", "month": "04", "ext": "mp4",
                    "width": 1920, "height": 1080, "duration": 15.0,
                    "tags": [("highlight", "event"), ("liga-1", "event")],
                },
                {
                    "id": "f003", "path": "\\\\172.16.0.25\\data\\2026\\Design\\Jersey_Design_Kit.psd",
                    "filename": "Jersey_Design_Kit.psd", "folder": "2026/Design",
                    "size": 190840832, "date": "2026-04-03", "year": "2026", "month": "04", "ext": "psd",
                    "width": 4096, "height": 4096, "duration": 0,
                    "tags": [("persija", "team"), ("design", "custom")],
                },
                {
                    "id": "f004", "path": "\\\\172.16.0.25\\data\\2026\\Players\\Player_Headshot_RR23.jpg",
                    "filename": "Player_Headshot_RR23.jpg", "folder": "2026/Players",
                    "size": 6081126, "date": "2026-04-02", "year": "2026", "month": "04", "ext": "jpg",
                    "width": 3000, "height": 4500, "duration": 0,
                    "tags": [("rizky-ridho", "player"), ("portrait", "event")],
                },
                {
                    "id": "f005", "path": "\\\\172.16.0.25\\data\\2026\\Match\\Training_Reel.mp4",
                    "filename": "Training_Reel.mp4", "folder": "2026/Match",
                    "size": 52428800, "date": "2026-04-01", "year": "2026", "month": "04", "ext": "mp4",
                    "width": 1920, "height": 1080, "duration": 45.0,
                    "tags": [("training", "event"), ("persija", "team"), ("2026", "year")],
                },
                {
                    "id": "f006", "path": "\\\\172.16.0.25\\data\\2025\\Match\\Persija_vs_Persib_001.jpg",
                    "filename": "Persija_vs_Persib_001.jpg", "folder": "2025/Match",
                    "size": 5242880, "date": "2025-10-15", "year": "2025", "month": "10", "ext": "jpg",
                    "width": 4000, "height": 2667, "duration": 0,
                    "tags": [("persija", "team"), ("persib", "team"), ("match", "event"), ("2025", "year"), ("liga-1", "event")],
                },
                {
                    "id": "f007", "path": "\\\\172.16.0.25\\data\\2025\\Match\\Jay_Idzes_Tackle.jpg",
                    "filename": "Jay_Idzes_Tackle.jpg", "folder": "2025/Match",
                    "size": 4718592, "date": "2025-09-28", "year": "2025", "month": "09", "ext": "jpg",
                    "width": 4000, "height": 3000, "duration": 0,
                    "tags": [("jay-idzes", "player"), ("match", "event"), ("2025", "year")],
                },
                {
                    "id": "f008", "path": "\\\\172.16.0.25\\data\\2025\\Events\\Media_Day_2025.jpg",
                    "filename": "Media_Day_2025.jpg", "folder": "2025/Events",
                    "size": 3145728, "date": "2025-07-10", "year": "2025", "month": "07", "ext": "jpg",
                    "width": 3000, "height": 2000, "duration": 0,
                    "tags": [("media-day", "event"), ("official", "custom"), ("2025", "year")],
                },
                {
                    "id": "f009", "path": "\\\\172.16.0.25\\data\\2024\\Match\\Liga1_Final_Highlights.mp4",
                    "filename": "Liga1_Final_Highlights.mp4", "folder": "2024/Match",
                    "size": 104857600, "date": "2024-12-05", "year": "2024", "month": "12", "ext": "mp4",
                    "width": 1920, "height": 1080, "duration": 120.0,
                    "tags": [("liga-1", "event"), ("highlight", "event"), ("2024", "year"), ("persija", "team")],
                },
                {
                    "id": "f010", "path": "\\\\172.16.0.25\\data\\2024\\Design\\Social_Template.psd",
                    "filename": "Social_Template.psd", "folder": "2024/Design",
                    "size": 25165824, "date": "2024-11-20", "year": "2024", "month": "11", "ext": "psd",
                    "width": 1080, "height": 1080, "duration": 0,
                    "tags": [("social-media", "custom"), ("design", "custom"), ("2024", "year")],
                },
            ]

            # Insert files
            for f in DEMO_FILES:
                conn.execute("""
                    INSERT OR IGNORE INTO photos
                    (id, path, filename, folder, size, date, year, month, ext, width, height, duration)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (f["id"], f["path"], f["filename"], f["folder"],
                      f["size"], f["date"], f["year"], f["month"], f["ext"],
                      f["width"], f["height"], f["duration"]))

                # Insert tags
                for tag, category in f["tags"]:
                    conn.execute("""
                        INSERT OR IGNORE INTO tags (file_id, tag, category)
                        VALUES (?, ?, ?)
                    """, (f["id"], tag, category))

            # Seed tag categories
            CATEGORIES = [
                ("event",  "#818CF8"),
                ("team",   "#F472B6"),
                ("player", "#A78BFA"),
                ("league", "#FBBF24"),
                ("year",   "#38BDF8"),
                ("custom", "#71717A"),
            ]
            for name, color in CATEGORIES:
                conn.execute("""
                    INSERT OR IGNORE INTO tag_categories (name, color)
                    VALUES (?, ?)
                """, (name, color))

            # Seed sample collections
            DEMO_COLLECTIONS = [
                (1, "Pre-Season Training 2026", "Official coverage of the first team pre-season training camp.", "f005"),
                (2, "Media Day Highlights",     "Selected clips and photos for social media team.",              "f008"),
                (3, "Liga 1 — Best of 2026",    "Top match photos from Liga 1 season 2026.",                    "f006"),
            ]
            for col_id, name, desc, cover in DEMO_COLLECTIONS:
                conn.execute("""
                    INSERT OR IGNORE INTO collections (id, name, description, cover_file_id)
                    VALUES (?, ?, ?, ?)
                """, (col_id, name, desc, cover))

            # Add some items to collection 1
            for file_id in ["f001", "f005"]:
                conn.execute("""
                    INSERT OR IGNORE INTO collection_items (collection_id, file_id)
                    VALUES (1, ?)
                """, (file_id,))

            self._sync_tag_vocabulary(conn)
            self._rebuild_fts(conn)

    # ── Search ────────────────────────────────────────────────────────────────

    def search(self, query="", file_type=None, sort="newest", page=1,
               per_page=PAGE_SIZE, year=None, date_from=None, date_to=None,
               folder=None, folder_prefix=None):
        """
        Full-text search with optional filters.
        Returns dict with keys: results, total, page, per_page, pages.
        """
        offset = (page - 1) * per_page
        params = []

        if query.strip():
            fts_query = self._build_fts_query(query)
        else:
            fts_query = ""

        if fts_query:
            # FTS join
            base_sql = """
                SELECT p.*, GROUP_CONCAT(t.tag, ',') AS tags_csv
                FROM photos_fts f
                JOIN photos p ON p.id = f.id
                LEFT JOIN tags t ON t.file_id = p.id
                WHERE photos_fts MATCH ?
            """
            params.append(fts_query)
        else:
            base_sql = """
                SELECT p.*, GROUP_CONCAT(t.tag, ',') AS tags_csv
                FROM photos p
                LEFT JOIN tags t ON t.file_id = p.id
                WHERE 1=1
            """

        # File type filter
        if file_type and file_type != "all":
            if file_type == "images":
                base_sql += " AND p.ext IN ('jpg','jpeg','png','gif','webp','heic','tiff','raw','cr2','nef')"
            elif file_type == "videos":
                base_sql += " AND p.ext IN ('mp4','mov','avi','mkv','mxf','r3d','braw')"
            elif file_type == "psd":
                base_sql += " AND p.ext IN ('psd','psb','ai','eps')"

        # Date filters
        if year:
            base_sql += " AND p.year = ?"
            params.append(year)
        if date_from:
            base_sql += " AND p.date >= ?"
            params.append(date_from)
        if date_to:
            base_sql += " AND p.date <= ?"
            params.append(date_to)
        if folder:
            base_sql += " AND p.folder = ?"
            params.append(folder)
        if folder_prefix:
            normalized_prefix = self._normalize_folder_prefix(folder_prefix)
            if normalized_prefix:
                base_sql += " AND (p.folder = ? OR p.folder LIKE ?)"
                params.extend([normalized_prefix, f"{normalized_prefix}\\%"])

        base_sql += " GROUP BY p.id"

        # Sort
        sort_map = {
            "newest": "p.date DESC, p.indexed_at DESC",
            "oldest": "p.date ASC",
            "name-az": "p.filename ASC",
            "name-za": "p.filename DESC",
            "size-desc": "p.size DESC",
        }
        base_sql += f" ORDER BY {sort_map.get(sort, 'p.date DESC')}"

        with get_connection(self.db_path) as conn:
            # Count total (without pagination)
            count_sql = f"SELECT COUNT(*) FROM ({base_sql})"
            total = conn.execute(count_sql, params).fetchone()[0]

            # Paginated results
            rows = conn.execute(
                base_sql + " LIMIT ? OFFSET ?",
                params + [per_page, offset]
            ).fetchall()

        results = [self._row_to_file_dict(r) for r in rows]
        return {
            "results": results,
            "total": total,
            "page": page,
            "per_page": per_page,
            "pages": max(1, -(-total // per_page)),  # ceiling division
        }

    def _row_to_file_dict(self, row):
        """Convert a DB Row to a clean dict for JSON serialization."""
        d = dict(row)
        tags_csv = d.pop("tags_csv", "") or ""
        d["tags"] = [t.strip() for t in tags_csv.split(",") if t.strip()]
        d["size_human"] = self._human_size(d.get("size", 0))
        d["type_label"] = d.get("ext", "").upper()
        d["thumbnail_url"] = f"/api/thumb/{d['id']}"
        return d

    @staticmethod
    def _human_size(size_bytes: int) -> str:
        for unit in ("B", "KB", "MB", "GB"):
            if size_bytes < 1024:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024
        return f"{size_bytes:.1f} TB"

    # ── File detail ───────────────────────────────────────────────────────────

    def get_file(self, file_id: str) -> dict | None:
        with get_connection(self.db_path) as conn:
            row = conn.execute("""
                SELECT p.*,
                       pm.make,
                       pm.model,
                       pm.lens,
                       pm.iso,
                       pm.focal_length,
                       pm.aperture,
                       pm.shutter_speed,
                       pm.captured_at,
                       pm.gps_latitude,
                       pm.gps_longitude,
                       pm.raw_json,
                       GROUP_CONCAT(t.tag || ':' || t.category, ',') AS tags_csv
                FROM photos p
                LEFT JOIN photo_metadata pm ON pm.file_id = p.id
                LEFT JOIN tags t ON t.file_id = p.id
                WHERE p.id = ?
                GROUP BY p.id
            """, (file_id,)).fetchone()

        if not row:
            return None

        d = dict(row)
        tags_csv = d.pop("tags_csv", "") or ""
        d["tags"] = []
        for entry in tags_csv.split(","):
            if ":" in entry:
                tag, cat = entry.split(":", 1)
                d["tags"].append({"tag": tag.strip(), "category": cat.strip()})
        d["size_human"] = self._human_size(d.get("size", 0))
        d["available"] = Path(d.get("path", "")).exists()
        metadata = {
            "make": d.pop("make", None),
            "model": d.pop("model", None),
            "lens": d.pop("lens", None),
            "iso": d.pop("iso", None),
            "focal_length": d.pop("focal_length", None),
            "aperture": d.pop("aperture", None),
            "shutter_speed": d.pop("shutter_speed", None),
            "captured_at": d.pop("captured_at", None),
            "gps_latitude": d.pop("gps_latitude", None),
            "gps_longitude": d.pop("gps_longitude", None),
        }
        raw_json = d.pop("raw_json", None)
        if raw_json:
            try:
                metadata["raw"] = json.loads(raw_json)
            except (TypeError, ValueError):
                metadata["raw"] = {}
        else:
            metadata["raw"] = {}
        d["metadata"] = metadata if any(value not in (None, "", {}) for value in metadata.values()) else {}
        return d

    # ── Tag operations ─────────────────────────────────────────────────────────

    def get_file_tags(self, file_id: str) -> list:
        with get_connection(self.db_path) as conn:
            rows = conn.execute("""
                SELECT tag, category FROM tags
                WHERE file_id = ?
                ORDER BY created_at
            """, (file_id,)).fetchall()
        return [dict(r) for r in rows]

    def create_tag_vocabulary(self, tag: str, category: str = "custom") -> dict:
        tag = self._normalize_tag(tag)
        if not tag:
            return {"ok": False, "error": "invalid tag"}

        with get_connection(self.db_path) as conn:
            category = self._normalize_category(category, conn)
            created = self._ensure_tag_vocabulary(conn, tag, category)
            row = conn.execute("""
                SELECT tv.tag,
                       tv.category,
                       tv.created_at,
                       COUNT(t.id) AS count
                FROM tag_vocabulary tv
                LEFT JOIN tags t ON t.tag = tv.tag
                WHERE tv.tag = ?
                GROUP BY tv.tag, tv.category, tv.created_at
            """, (tag,)).fetchone()

        result = dict(row) if row else {"tag": tag, "category": category}
        result.update({"ok": True, "created": created})
        return result

    def add_tag(self, file_id: str, tag: str, category: str = "custom") -> bool:
        tag = self._normalize_tag(tag)
        if not tag:
            return False

        try:
            with get_connection(self.db_path) as conn:
                if category == "custom":
                    category = self._infer_category(tag, conn) or "custom"
                category = self._normalize_category(category, conn)
                self._ensure_tag_vocabulary(conn, tag, category)

                before = conn.total_changes
                conn.execute("""
                    INSERT OR IGNORE INTO tags (file_id, tag, category)
                    VALUES (?, ?, ?)
                """, (file_id, tag, category))
                inserted = conn.total_changes > before
                if not inserted:
                    return False
                self._update_fts(conn, file_id)
                self._log(conn, "tag_add", {"file_id": file_id, "tag": tag})
            return True
        except Exception:
            return False

    def remove_tag(self, file_id: str, tag: str) -> bool:
        try:
            with get_connection(self.db_path) as conn:
                conn.execute("""
                    DELETE FROM tags WHERE file_id = ? AND tag = ?
                """, (file_id, tag))
                self._update_fts(conn, file_id)
                self._log(conn, "tag_remove", {"file_id": file_id, "tag": tag})
            return True
        except Exception:
            return False

    def batch_add_tags(self, file_ids: list, tags: list) -> dict:
        """Apply multiple tags to multiple files. Returns counts."""
        success = 0
        tagged_files = 0
        with get_connection(self.db_path) as conn:
            for file_id in file_ids:
                file_updated = False
                for tag in tags:
                    tag_norm = self._normalize_tag(tag)
                    if not tag_norm:
                        continue
                    cat = self._infer_category(tag_norm, conn) or "custom"
                    cat = self._normalize_category(cat, conn)
                    self._ensure_tag_vocabulary(conn, tag_norm, cat)
                    try:
                        before = conn.total_changes
                        conn.execute("""
                            INSERT OR IGNORE INTO tags (file_id, tag, category)
                            VALUES (?, ?, ?)
                        """, (file_id, tag_norm, cat))
                        if conn.total_changes > before:
                            success += 1
                            file_updated = True
                    except Exception:
                        pass
                self._update_fts(conn, file_id)
                if file_updated:
                    tagged_files += 1
            self._log(conn, "batch_tag", {
                "requested_file_count": len(file_ids),
                "updated_file_count": tagged_files,
                "tags": tags,
                "tags_applied": success,
            })
        return {"tagged_files": tagged_files, "tags_applied": success}

    def batch_remove_tags(self, file_ids: list, tags: list) -> dict:
        """Remove multiple tags from multiple files. Returns counts."""
        success = 0
        updated_files = 0
        with get_connection(self.db_path) as conn:
            for file_id in file_ids:
                file_updated = False
                for tag in tags:
                    tag_norm = self._normalize_tag(tag)
                    if not tag_norm:
                        continue
                    try:
                        before = conn.total_changes
                        conn.execute("""
                            DELETE FROM tags WHERE file_id = ? AND tag = ?
                        """, (file_id, tag_norm))
                        if conn.total_changes > before:
                            success += 1
                            file_updated = True
                    except Exception:
                        pass
                if file_updated:
                    self._update_fts(conn, file_id)
                    updated_files += 1
            self._log(conn, "batch_tag_remove", {
                "requested_file_count": len(file_ids),
                "updated_file_count": updated_files,
                "tags": tags,
                "tags_removed": success,
            })
        return {"updated_files": updated_files, "tags_removed": success}

    # ── Tags management ────────────────────────────────────────────────────────

    def get_all_tags(self, category: str = None, sort: str = "count") -> list:
        """Return all vocabulary tags with usage counts, including unused tags."""
        sql = """
            SELECT tv.tag,
                   tv.category,
                   tv.created_at,
                   COUNT(t.id) AS count
            FROM tag_vocabulary tv
            LEFT JOIN tags t ON t.tag = tv.tag
            WHERE 1=1
        """
        params = []
        if category and category != "all":
            sql += " AND tv.category = ?"
            params.append(category)
        sql += " GROUP BY tv.tag, tv.category, tv.created_at"
        if sort == "az":
            sql += " ORDER BY tv.tag ASC"
        elif sort == "newest":
            sql += " ORDER BY tv.created_at DESC"
        else:
            sql += " ORDER BY count DESC, tv.tag ASC"

        with get_connection(self.db_path) as conn:
            rows = conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]

    def get_tag_categories(self) -> list:
        with get_connection(self.db_path) as conn:
            rows = conn.execute("""
                SELECT tc.name, tc.color, COUNT(t.id) as count
                FROM tag_categories tc
                LEFT JOIN tag_vocabulary t ON t.category = tc.name
                GROUP BY tc.name, tc.color
                ORDER BY tc.name ASC
            """).fetchall()
        return [dict(r) for r in rows]

    def get_tag_analytics(self) -> dict:
        with get_connection(self.db_path) as conn:
            most_used = conn.execute("""
                SELECT tv.tag, tv.category, COUNT(t.id) AS count
                FROM tag_vocabulary tv
                LEFT JOIN tags t ON t.tag = tv.tag
                GROUP BY tv.tag, tv.category
                ORDER BY count DESC, tv.tag ASC
                LIMIT 10
            """).fetchall()
            unused = conn.execute("""
                SELECT tv.tag, tv.category, tv.created_at
                FROM tag_vocabulary tv
                LEFT JOIN tags t ON t.tag = tv.tag
                WHERE t.id IS NULL
                ORDER BY tv.created_at DESC, tv.tag ASC
                LIMIT 10
            """).fetchall()
        return {
            "most_used": [dict(row) for row in most_used],
            "unused": [dict(row) for row in unused],
            "categories": self.get_tag_categories(),
        }

    def get_folder_tree(self) -> list:
        with get_connection(self.db_path) as conn:
            rows = conn.execute("""
                SELECT folder, COUNT(*) AS count
                FROM photos
                WHERE folder IS NOT NULL AND folder != ''
                GROUP BY folder
                ORDER BY folder ASC
            """).fetchall()

        root: dict[str, dict] = {}
        for row in rows:
            folder = self._normalize_folder_prefix(row["folder"])
            if not folder:
                continue
            segments = [part for part in re.split(r"[\\/]+", folder) if part]
            node_map = root
            current_path = ""
            for segment in segments:
                current_path = segment if not current_path else f"{current_path}\\{segment}"
                node = node_map.setdefault(segment, {
                    "name": segment,
                    "path": current_path,
                    "count": 0,
                    "_children": {},
                })
                node["count"] += row["count"]
                node_map = node["_children"]

        def serialize(nodes: dict[str, dict]) -> list:
            items = []
            for key in sorted(nodes.keys(), key=str.lower):
                node = nodes[key]
                items.append({
                    "name": node["name"],
                    "path": node["path"],
                    "count": node["count"],
                    "children": serialize(node["_children"]),
                })
            return items

        return serialize(root)

    def get_saved_searches(self) -> list:
        with get_connection(self.db_path) as conn:
            rows = conn.execute("""
                SELECT *
                FROM saved_searches
                ORDER BY updated_at DESC, name ASC
            """).fetchall()
        return [dict(row) for row in rows]

    def create_saved_search(self, payload: dict) -> dict:
        record = self._normalize_saved_search_payload(payload, require_name=True)
        with get_connection(self.db_path) as conn:
            cur = conn.execute("""
                INSERT INTO saved_searches
                (name, query, file_type, sort, date_from, date_to, folder_prefix)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                record["name"],
                record["query"],
                record["file_type"],
                record["sort"],
                record["date_from"],
                record["date_to"],
                record["folder_prefix"],
            ))
            saved_id = cur.lastrowid
            saved = conn.execute("""
                SELECT * FROM saved_searches WHERE id = ?
            """, (saved_id,)).fetchone()
            self._log(conn, "saved_search_create", {
                "saved_search_id": saved_id,
                "name": record["name"],
            })
        return dict(saved)

    def update_saved_search(self, saved_id: int, payload: dict) -> dict | None:
        if not payload:
            return self.get_saved_search(saved_id)

        allowed = {
            "name", "query", "file_type", "sort",
            "date_from", "date_to", "folder_prefix",
        }
        raw_update = {key: value for key, value in payload.items() if key in allowed}
        if not raw_update:
            return self.get_saved_search(saved_id)

        normalized = self._normalize_saved_search_payload(raw_update, require_name=False)
        assignments = ", ".join(f"{key} = ?" for key in normalized.keys())
        params = list(normalized.values()) + [saved_id]

        with get_connection(self.db_path) as conn:
            conn.execute(f"""
                UPDATE saved_searches
                SET {assignments},
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, params)
            row = conn.execute("""
                SELECT * FROM saved_searches WHERE id = ?
            """, (saved_id,)).fetchone()
            if row:
                self._log(conn, "saved_search_update", {
                    "saved_search_id": saved_id,
                    "fields": sorted(normalized.keys()),
                })
        return dict(row) if row else None

    def get_saved_search(self, saved_id: int) -> dict | None:
        with get_connection(self.db_path) as conn:
            row = conn.execute("""
                SELECT * FROM saved_searches WHERE id = ?
            """, (saved_id,)).fetchone()
        return dict(row) if row else None

    def delete_saved_search(self, saved_id: int) -> bool:
        with get_connection(self.db_path) as conn:
            row = conn.execute("""
                SELECT name FROM saved_searches WHERE id = ?
            """, (saved_id,)).fetchone()
            conn.execute("DELETE FROM saved_searches WHERE id = ?", (saved_id,))
            self._log(conn, "saved_search_delete", {
                "saved_search_id": saved_id,
                "name": row["name"] if row else None,
            })
        return True

    def log_saved_search_apply(self, saved_id: int) -> None:
        with get_connection(self.db_path) as conn:
            row = conn.execute("""
                SELECT name FROM saved_searches WHERE id = ?
            """, (saved_id,)).fetchone()
            if row:
                self._log(conn, "saved_search_apply", {
                    "saved_search_id": saved_id,
                    "name": row["name"],
                })

    def delete_tag_from_vocab(self, tag: str) -> int:
        """Remove a tag from all files. Returns number of files affected."""
        with get_connection(self.db_path) as conn:
            file_ids = [row[0] for row in conn.execute("""
                SELECT DISTINCT file_id FROM tags WHERE tag = ?
            """, (tag,)).fetchall()]
            conn.execute("DELETE FROM tags WHERE tag = ?", (tag,))
            conn.execute("DELETE FROM tag_vocabulary WHERE tag = ?", (tag,))
            for file_id in file_ids:
                self._update_fts(conn, file_id)
            affected = len(file_ids)
            self._log(conn, "tag_delete", {"tag": tag, "affected": affected})
        return affected

    def merge_tags(self, source: str, target: str) -> int:
        """Reassign all files with source tag → target tag. Returns affected count."""
        source = self._normalize_tag(source)
        target = self._normalize_tag(target)
        if not source or not target or source == target:
            return 0

        with get_connection(self.db_path) as conn:
            cat = self._infer_category(target, conn) or self._infer_category(source, conn) or "custom"
            cat = self._normalize_category(cat, conn)
            self._ensure_tag_vocabulary(conn, target, cat)

            # Get files with source tag
            file_ids = [r[0] for r in conn.execute(
                "SELECT DISTINCT file_id FROM tags WHERE tag = ?", (source,)
            ).fetchall()]

            # For each file, add target tag (ignore if exists), remove source
            for fid in file_ids:
                conn.execute("""
                    INSERT OR IGNORE INTO tags (file_id, tag, category)
                    VALUES (?, ?, ?)
                """, (fid, target, cat))
            conn.execute("DELETE FROM tags WHERE tag = ?", (source,))
            conn.execute("DELETE FROM tag_vocabulary WHERE tag = ?", (source,))
            for fid in file_ids:
                self._update_fts(conn, fid)
            self._log(conn, "tag_merge", {"source": source, "target": target, "files": len(file_ids)})
        return len(file_ids)

    # ── Collections ────────────────────────────────────────────────────────────

    def get_collections(self) -> list:
        with get_connection(self.db_path) as conn:
            rows = conn.execute("""
                SELECT c.id, c.name, c.description, c.cover_file_id,
                       c.created_at, c.updated_at,
                       COUNT(ci.id) as item_count
                FROM collections c
                LEFT JOIN collection_items ci ON ci.collection_id = c.id
                GROUP BY c.id
                ORDER BY c.updated_at DESC
            """).fetchall()
        collections = []
        for row in rows:
            item = dict(row)
            item["cover_thumbnail_url"] = (
                f"/api/thumb/{item['cover_file_id']}" if item.get("cover_file_id") else None
            )
            collections.append(item)
        return collections

    def create_collection(self, name: str, description: str = "") -> dict:
        with get_connection(self.db_path) as conn:
            cur = conn.execute("""
                INSERT INTO collections (name, description)
                VALUES (?, ?)
            """, (name, description))
            col_id = cur.lastrowid
            self._log(conn, "collection_create", {"collection_id": col_id, "name": name})
        return {
            "id": col_id,
            "name": name,
            "description": description,
            "item_count": 0,
            "cover_file_id": None,
            "cover_thumbnail_url": None,
        }

    def get_collection(self, col_id: int) -> dict | None:
        with get_connection(self.db_path) as conn:
            row = conn.execute("""
                SELECT c.*, COUNT(ci.id) as item_count
                FROM collections c
                LEFT JOIN collection_items ci ON ci.collection_id = c.id
                WHERE c.id = ?
                GROUP BY c.id
            """, (col_id,)).fetchone()
        if not row:
            return None
        result = dict(row)
        result["cover_thumbnail_url"] = (
            f"/api/thumb/{result['cover_file_id']}" if result.get("cover_file_id") else None
        )
        return result

    def delete_collection(self, col_id: int) -> bool:
        with get_connection(self.db_path) as conn:
            conn.execute("DELETE FROM collections WHERE id = ?", (col_id,))
            self._log(conn, "collection_delete", {"collection_id": col_id})
        return True

    def add_to_collection(self, col_id: int, file_ids: list) -> dict:
        added = 0
        with get_connection(self.db_path) as conn:
            for fid in file_ids:
                try:
                    before = conn.total_changes
                    conn.execute("""
                        INSERT OR IGNORE INTO collection_items (collection_id, file_id)
                        VALUES (?, ?)
                    """, (col_id, fid))
                    if conn.total_changes > before:
                        added += 1
                except Exception:
                    pass
            conn.execute("""
                UPDATE collections SET updated_at = CURRENT_TIMESTAMP WHERE id = ?
            """, (col_id,))
            self._refresh_collection_cover(conn, col_id)
            self._log(conn, "collection_add_items", {
                "collection_id": col_id,
                "requested_file_count": len(file_ids),
                "added_file_count": added,
            })
        return {"added": added}

    def remove_from_collection(self, col_id: int, file_id: str) -> bool:
        with get_connection(self.db_path) as conn:
            conn.execute("""
                DELETE FROM collection_items
                WHERE collection_id = ? AND file_id = ?
            """, (col_id, file_id))
            conn.execute("""
                UPDATE collections SET updated_at = CURRENT_TIMESTAMP WHERE id = ?
            """, (col_id,))
            self._refresh_collection_cover(conn, col_id)
            self._log(conn, "collection_remove_item", {
                "collection_id": col_id,
                "file_id": file_id,
            })
        return True

    def get_collection_files(self, col_id: int, page=1, per_page=PAGE_SIZE, sort: str = "newest") -> dict:
        offset = (page - 1) * per_page
        order_map = {
            "newest": "ci.added_at DESC, ci.id DESC",
            "oldest": "ci.added_at ASC, ci.id ASC",
            "name-az": "p.filename ASC",
            "name-za": "p.filename DESC",
        }
        order_by = order_map.get(sort, order_map["newest"])

        with get_connection(self.db_path) as conn:
            total = conn.execute("""
                SELECT COUNT(*) FROM collection_items WHERE collection_id = ?
            """, (col_id,)).fetchone()[0]

            rows = conn.execute(f"""
                SELECT p.*, ci.added_at AS added_at, GROUP_CONCAT(t.tag, ',') AS tags_csv
                FROM collection_items ci
                JOIN photos p ON p.id = ci.file_id
                LEFT JOIN tags t ON t.file_id = p.id
                WHERE ci.collection_id = ?
                GROUP BY p.id
                ORDER BY {order_by}
                LIMIT ? OFFSET ?
            """, (col_id, per_page, offset)).fetchall()

        return {
            "results": [self._row_to_file_dict(r) for r in rows],
            "total": total, "page": page, "per_page": per_page,
            "pages": max(1, -(-total // per_page)),
        }

    # ── Config & Settings ─────────────────────────────────────────────────────

    def get_config(self) -> dict:
        """Retrieve application settings."""
        with get_connection(self.db_path) as conn:
            rows = conn.execute("SELECT key, value FROM settings").fetchall()

        config = {r["key"]: r["value"] for r in rows}
        defaults = {
            "library_path": "",
            "last_scan": None,
            "last_scan_duration_s": "0",
            "last_scan_invalid_paths": "[]",
            "last_scan_paths": "[]",
        }
        for key, value in defaults.items():
            config.setdefault(key, value)

        return config

    def update_config(self, key: str, value: str):
        """Update or insert an application setting."""
        if key == "library_path":
            value = "; ".join(self._parse_library_paths(value))
        with get_connection(self.db_path) as conn:
            self._set_setting(conn, key, value)

    # ── Scanner ───────────────────────────────────────────────────────────────

    @staticmethod
    def _parse_library_paths(raw_paths) -> list[str]:
        """Parse semicolon-delimited library paths, trimming empties and duplicates."""
        if raw_paths is None:
            return []

        if isinstance(raw_paths, str):
            candidates = raw_paths.split(";")
        elif isinstance(raw_paths, (list, tuple, set)):
            candidates = []
            for value in raw_paths:
                if isinstance(value, str):
                    candidates.extend(value.split(";"))
        else:
            return []

        paths = []
        seen = set()
        for candidate in candidates:
            path = candidate.strip()
            if not path:
                continue
            key = os.path.normcase(os.path.normpath(path))
            if key in seen:
                continue
            seen.add(key)
            paths.append(path)
        return paths

    @staticmethod
    def _empty_scan_stats() -> dict:
        return {
            "found": 0,
            "new": 0,
            "updated": 0,
            "skipped": 0,
            "errors": 0,
            "metadata_updated": 0,
        }

    def _scan_directory_with_connection(self, conn, root_path: str) -> dict:
        """Scan a single root path using an existing DB connection."""
        stats = self._empty_scan_stats()

        # Supported extensions
        EXT_IMAGES = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.heic', '.tiff'}
        EXT_VIDEO  = {'.mp4', '.mov', '.avi', '.mkv', '.mxf', '.r3d', '.braw'}
        EXT_DESIGN = {'.psd', '.psb', '.ai', '.eps'}
        SUPPORTED  = EXT_IMAGES | EXT_VIDEO | EXT_DESIGN
        root_label = os.path.basename(os.path.normpath(root_path)) or root_path

        for root, _, files in os.walk(root_path):
            for filename in files:
                ext = os.path.splitext(filename)[1].lower()
                if ext not in SUPPORTED:
                    continue

                stats["found"] += 1
                file_path = os.path.join(root, filename)

                try:
                    p = Path(file_path)
                    f_stat = p.stat()
                    mtime = f_stat.st_mtime
                    size = f_stat.st_size

                    rel_folder = os.path.relpath(root, root_path)
                    if rel_folder == ".":
                        rel_folder = root_label
                    else:
                        rel_folder = os.path.join(root_label, rel_folder)

                    existing = conn.execute("""
                        SELECT p.id,
                               p.mtime,
                               p.width,
                               p.height,
                               p.duration,
                               pm.file_id AS metadata_file_id
                        FROM photos p
                        LEFT JOIN photo_metadata pm ON pm.file_id = p.id
                        WHERE p.path = ?
                    """, (file_path,)).fetchone()
                    ext_key = ext[1:]

                    if existing and abs(existing["mtime"] - mtime) < 1.0 and not self._media_details_missing(existing, ext_key):
                        stats["skipped"] += 1
                        continue

                    details = self._inspect_media_file(p, ext_key)
                    dt = datetime.fromtimestamp(mtime, tz=timezone.utc)
                    date_str = dt.strftime("%Y-%m-%d")
                    year_str = dt.strftime("%Y")
                    month_str = dt.strftime("%m")

                    if existing:
                        file_id = existing["id"]
                        conn.execute("""
                            UPDATE photos
                            SET filename = ?,
                                folder = ?,
                                size = ?,
                                mtime = ?,
                                date = ?,
                                year = ?,
                                month = ?,
                                ext = ?,
                                width = ?,
                                height = ?,
                                duration = ?,
                                indexed_at = CURRENT_TIMESTAMP
                            WHERE id = ?
                        """, (
                            filename,
                            rel_folder,
                            size,
                            mtime,
                            date_str,
                            year_str,
                            month_str,
                            ext_key,
                            details["width"],
                            details["height"],
                            details["duration"],
                            file_id,
                        ))
                        stats["updated"] += 1
                    else:
                        file_id = str(uuid.uuid4())
                        conn.execute("""
                            INSERT INTO photos
                            (id, path, filename, folder, size, mtime, date, year, month, ext, width, height, duration)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            file_id,
                            file_path,
                            filename,
                            rel_folder,
                            size,
                            mtime,
                            date_str,
                            year_str,
                            month_str,
                            ext_key,
                            details["width"],
                            details["height"],
                            details["duration"],
                        ))
                        stats["new"] += 1

                    if self._upsert_photo_metadata(conn, file_id, details.get("metadata")):
                        stats["metadata_updated"] += 1
                    self._update_fts(conn, file_id)

                except Exception as e:
                    print(f"Error scanning {file_path}: {e}")
                    stats["errors"] += 1

        return stats

    def scan_directories(self, raw_paths) -> dict:
        """Scan one or more directories. Paths may be semicolon-delimited."""
        requested_paths = self._parse_library_paths(raw_paths)
        if not requested_paths:
            return {"error": "No scan paths provided"}

        valid_paths = [path for path in requested_paths if os.path.isdir(path)]
        invalid_paths = [path for path in requested_paths if not os.path.isdir(path)]

        if not valid_paths:
            return {"error": f"Invalid directory path(s): {'; '.join(invalid_paths)}"}

        start_time = time.time()
        stats = self._empty_scan_stats()

        with get_connection(self.db_path) as conn:
            for root_path in valid_paths:
                path_stats = self._scan_directory_with_connection(conn, root_path)
                for key, value in path_stats.items():
                    stats[key] += value

            normalized_paths = "; ".join(valid_paths)
            duration_s = round(time.time() - start_time, 2)
            self._set_setting(conn, "last_scan", datetime.now().isoformat())
            self._set_setting(conn, "last_scan_duration_s", str(duration_s))
            self._set_setting(conn, "last_scan_invalid_paths", json.dumps(invalid_paths))
            self._set_setting(conn, "last_scan_paths", json.dumps(valid_paths))
            self._set_setting(conn, "library_path", normalized_paths)

            self._log(conn, "scan_complete", {
                "paths": valid_paths,
                "invalid_paths": invalid_paths,
                "duration_s": duration_s,
                **stats
            })
            if stats["metadata_updated"]:
                self._log(conn, "metadata_extract", {
                    "paths": valid_paths,
                    "metadata_updated": stats["metadata_updated"],
                })

        return {
            "duration_s": duration_s,
            "scanned_paths": valid_paths,
            "invalid_paths": invalid_paths,
            **stats
        }

    def scan_directory(self, root_path: str) -> dict:
        """
        Recursively scan a directory for media files and update the catalog.
        Returns a summary of the scan results.
        """
        return self.scan_directories(root_path)

    # ── Stats ─────────────────────────────────────────────────────────────────

    def get_stats(self) -> dict:
        with get_connection(self.db_path) as conn:
            total = conn.execute("SELECT COUNT(*) FROM photos").fetchone()[0]
            tagged = conn.execute("""
                SELECT COUNT(DISTINCT file_id) FROM tags
            """).fetchone()[0]
            col_count = conn.execute("SELECT COUNT(*) FROM collections").fetchone()[0]
            total_size = conn.execute("SELECT SUM(size) FROM photos").fetchone()[0] or 0
            top_tags = conn.execute("""
                SELECT tag, COUNT(*) as count FROM tags
                GROUP BY tag ORDER BY count DESC LIMIT 10
            """).fetchall()
            folder_count = conn.execute("""
                SELECT COUNT(DISTINCT folder) FROM photos
            """).fetchone()[0]
            saved_search_count = conn.execute("""
                SELECT COUNT(*) FROM saved_searches
            """).fetchone()[0]
            settings = {
                row["key"]: row["value"]
                for row in conn.execute("""
                    SELECT key, value
                    FROM settings
                    WHERE key IN ('library_path', 'last_scan', 'last_scan_duration_s', 'last_scan_invalid_paths')
                """).fetchall()
            }

        pct_tagged = round((tagged / total * 100) if total else 0, 1)
        configured_paths = self._parse_library_paths(settings.get("library_path", ""))
        try:
            invalid_paths = json.loads(settings.get("last_scan_invalid_paths") or "[]")
        except (TypeError, ValueError):
            invalid_paths = []
        return {
            "total_files": total,
            "tagged_files": tagged,
            "pct_tagged": pct_tagged,
            "collections": col_count,
            "total_size_bytes": total_size,
            "total_size_human": self._human_size(total_size),
            "top_tags": [dict(r) for r in top_tags],
            "folders_indexed": folder_count,
            "saved_searches": saved_search_count,
            "health": {
                "last_scan": settings.get("last_scan"),
                "last_scan_duration_s": float(settings.get("last_scan_duration_s") or 0),
                "configured_path_count": len(configured_paths),
                "invalid_path_count": len(invalid_paths),
                "invalid_paths": invalid_paths,
            },
        }

    # ── FTS helpers ───────────────────────────────────────────────────────────

    def _update_fts(self, conn, file_id: str):
        """Rebuild FTS haystack for a single file after tag change."""
        row = conn.execute("""
            SELECT p.filename, p.folder, p.date, p.year,
                   GROUP_CONCAT(t.tag, ' ') AS tag_str
            FROM photos p
            LEFT JOIN tags t ON t.file_id = p.id
            WHERE p.id = ?
            GROUP BY p.id
        """, (file_id,)).fetchone()
        if row:
            haystack = " ".join(filter(None, [
                row["filename"], row["folder"], row["date"],
                row["year"], row["tag_str"]
            ]))
            conn.execute("""
                INSERT OR REPLACE INTO photos_fts (id, haystack)
                VALUES (?, ?)
            """, (file_id, haystack))

    def _upsert_photo_metadata(self, conn, file_id: str, metadata: dict | None) -> bool:
        if metadata and any(value not in (None, "", {}) for value in metadata.values()):
            conn.execute("""
                INSERT INTO photo_metadata
                (file_id, make, model, lens, iso, focal_length, aperture,
                 shutter_speed, captured_at, gps_latitude, gps_longitude,
                 raw_json, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(file_id) DO UPDATE SET
                    make = excluded.make,
                    model = excluded.model,
                    lens = excluded.lens,
                    iso = excluded.iso,
                    focal_length = excluded.focal_length,
                    aperture = excluded.aperture,
                    shutter_speed = excluded.shutter_speed,
                    captured_at = excluded.captured_at,
                    gps_latitude = excluded.gps_latitude,
                    gps_longitude = excluded.gps_longitude,
                    raw_json = excluded.raw_json,
                    updated_at = CURRENT_TIMESTAMP
            """, (
                file_id,
                metadata.get("make"),
                metadata.get("model"),
                metadata.get("lens"),
                metadata.get("iso"),
                metadata.get("focal_length"),
                metadata.get("aperture"),
                metadata.get("shutter_speed"),
                metadata.get("captured_at"),
                metadata.get("gps_latitude"),
                metadata.get("gps_longitude"),
                json.dumps(metadata.get("raw") or {}),
            ))
            return True

        conn.execute("DELETE FROM photo_metadata WHERE file_id = ?", (file_id,))
        return False

    # ── Activity log ──────────────────────────────────────────────────────────

    def _log(self, conn, event_type: str, details: dict):
        conn.execute("""
            INSERT INTO activity_log (event_type, details)
            VALUES (?, ?)
        """, (event_type, json.dumps(details)))

    def get_activity_log(self, limit=50) -> list:
        with get_connection(self.db_path) as conn:
            rows = conn.execute("""
                SELECT * FROM activity_log ORDER BY created_at DESC LIMIT ?
            """, (limit,)).fetchall()
        result = []
        for r in rows:
            d = dict(r)
            try:
                d["details"] = json.loads(d["details"] or "{}")
            except Exception:
                d["details"] = {}
            result.append(d)
        return result

    def log_event(self, event_type: str, details: dict) -> None:
        with get_connection(self.db_path) as conn:
            self._log(conn, event_type, details)

    # ── Utility ───────────────────────────────────────────────────────────────

    @staticmethod
    def _normalize_tag(tag: str) -> str:
        tag = tag.strip().lower()
        tag = re.sub(r'[^a-z0-9\-_]', '-', tag)
        tag = re.sub(r'-+', '-', tag).strip('-')
        return tag[:64]  # max length

    @staticmethod
    def _build_fts_query(query: str) -> str:
        terms = re.findall(r"[a-z0-9]+", query.lower())
        return " AND ".join(f"{term}*" for term in terms[:8])

    @staticmethod
    def _normalize_folder_prefix(folder_prefix: str | None) -> str:
        if not folder_prefix:
            return ""
        cleaned = re.sub(r"[\\/]+", "\\\\", str(folder_prefix).strip())
        return cleaned.rstrip("\\")

    def _normalize_category(self, category: str | None, conn=None) -> str:
        category = (category or "custom").strip().lower()
        owns_connection = conn is None
        if owns_connection:
            with get_connection(self.db_path) as local_conn:
                return self._normalize_category(category, local_conn)

        row = conn.execute("""
            SELECT name FROM tag_categories WHERE name = ?
        """, (category,)).fetchone()
        return category if row else "custom"

    def _ensure_tag_vocabulary(self, conn, tag: str, category: str) -> bool:
        category = self._normalize_category(category, conn)
        before = conn.total_changes
        conn.execute("""
            INSERT OR IGNORE INTO tag_vocabulary (tag, category)
            VALUES (?, ?)
        """, (tag, category))
        return conn.total_changes > before

    def _infer_category(self, tag: str, conn=None) -> str | None:
        """Guess category from vocabulary first, then historical assignments."""
        owns_connection = conn is None
        if owns_connection:
            with get_connection(self.db_path) as local_conn:
                return self._infer_category(tag, local_conn)

        row = conn.execute("""
            SELECT category
            FROM tag_vocabulary
            WHERE tag = ?
        """, (tag,)).fetchone()
        if row:
            return row["category"]

        row = conn.execute("""
            SELECT category FROM tags WHERE tag = ?
            ORDER BY created_at DESC LIMIT 1
        """, (tag,)).fetchone()
        return row["category"] if row else None

    def _normalize_saved_search_payload(self, payload: dict, require_name: bool) -> dict:
        normalized = {}
        if require_name or "name" in payload:
            name = (payload.get("name") or "").strip()
            if not name:
                raise ValueError("name is required")
            normalized["name"] = name[:120]

        if "query" in payload or require_name:
            normalized["query"] = (payload.get("query") or "").strip()
        if "file_type" in payload or require_name:
            normalized["file_type"] = (payload.get("file_type") or "all").strip() or "all"
        if "sort" in payload or require_name:
            normalized["sort"] = (payload.get("sort") or "newest").strip() or "newest"
        if "date_from" in payload or require_name:
            normalized["date_from"] = (payload.get("date_from") or None) or None
        if "date_to" in payload or require_name:
            normalized["date_to"] = (payload.get("date_to") or None) or None
        if "folder_prefix" in payload or require_name:
            folder_prefix = self._normalize_folder_prefix(payload.get("folder_prefix"))
            normalized["folder_prefix"] = folder_prefix or None
        return normalized

    def _refresh_collection_cover(self, conn, col_id: int) -> None:
        row = conn.execute("""
            SELECT file_id
            FROM collection_items
            WHERE collection_id = ?
            ORDER BY sort_order ASC, added_at ASC, id ASC
            LIMIT 1
        """, (col_id,)).fetchone()
        conn.execute("""
            UPDATE collections
            SET cover_file_id = ?
            WHERE id = ?
        """, (row["file_id"] if row else None, col_id))

    @staticmethod
    def _set_setting(conn, key: str, value: str | None) -> None:
        conn.execute("""
            INSERT OR REPLACE INTO settings (key, value)
            VALUES (?, ?)
        """, (key, value))

    @staticmethod
    def _supports_metadata_extraction(ext: str) -> bool:
        return ext.lower() in {"jpg", "jpeg", "tif", "tiff", "png", "webp", "heic"}

    def _media_details_missing(self, existing, ext: str) -> bool:
        if not existing:
            return True
        if self._supports_metadata_extraction(ext):
            if not existing["width"] or not existing["height"]:
                return True
            if exifread and ext.lower() in {"jpg", "jpeg", "tif", "tiff"} and not existing["metadata_file_id"]:
                return True
        return False

    def _inspect_media_file(self, file_path: Path, ext: str) -> dict:
        details = {"width": 0, "height": 0, "duration": 0.0, "metadata": None}
        if self._supports_metadata_extraction(ext):
            opened = False
            try:
                with Image.open(file_path) as img:
                    img = ImageOps.exif_transpose(img)
                    details["width"], details["height"] = img.size
                    opened = True
            except (UnidentifiedImageError, OSError, ValueError):
                pass
            if opened:
                details["metadata"] = self._extract_image_metadata(file_path, ext)
        return details

    def _extract_image_metadata(self, file_path: Path, ext: str) -> dict | None:
        if not exifread or ext.lower() not in {"jpg", "jpeg", "tif", "tiff"}:
            return None
        try:
            with file_path.open("rb") as handle:
                tags = exifread.process_file(handle, details=False)
        except OSError:
            return None

        raw_map = {}
        for key in (
            "Image Make",
            "Image Model",
            "EXIF LensModel",
            "EXIF ISOSpeedRatings",
            "EXIF PhotographicSensitivity",
            "EXIF FocalLength",
            "EXIF FNumber",
            "EXIF ExposureTime",
            "EXIF DateTimeOriginal",
            "Image DateTime",
            "GPS GPSLatitude",
            "GPS GPSLatitudeRef",
            "GPS GPSLongitude",
            "GPS GPSLongitudeRef",
        ):
            if key in tags:
                raw_map[key] = str(tags[key])

        metadata = {
            "make": self._tag_string(tags.get("Image Make")),
            "model": self._tag_string(tags.get("Image Model")),
            "lens": self._tag_string(tags.get("EXIF LensModel") or tags.get("EXIF LensSpecification")),
            "iso": self._safe_int(tags.get("EXIF ISOSpeedRatings") or tags.get("EXIF PhotographicSensitivity")),
            "focal_length": self._ratio_to_float(tags.get("EXIF FocalLength")),
            "aperture": self._ratio_to_float(tags.get("EXIF FNumber")),
            "shutter_speed": self._tag_string(tags.get("EXIF ExposureTime")),
            "captured_at": self._normalize_exif_datetime(
                self._tag_string(tags.get("EXIF DateTimeOriginal") or tags.get("Image DateTime"))
            ),
            "gps_latitude": self._parse_gps_coordinate(tags.get("GPS GPSLatitude"), tags.get("GPS GPSLatitudeRef")),
            "gps_longitude": self._parse_gps_coordinate(tags.get("GPS GPSLongitude"), tags.get("GPS GPSLongitudeRef")),
            "raw": raw_map,
        }
        if any(value not in (None, "", {}) for value in metadata.values()):
            return metadata
        return None

    @staticmethod
    def _tag_string(tag) -> str | None:
        if tag is None:
            return None
        text = str(tag).strip()
        return text or None

    @staticmethod
    def _safe_int(value) -> int | None:
        if value is None:
            return None
        text = str(value).strip()
        if not text:
            return None
        try:
            return int(float(text.split("/")[0])) if "/" in text else int(float(text))
        except ValueError:
            return None

    @staticmethod
    def _ratio_to_float(value) -> float | None:
        if value is None:
            return None
        if hasattr(value, "values") and value.values:
            value = value.values[0]
        if hasattr(value, "num") and hasattr(value, "den"):
            if not value.den:
                return None
            return round(value.num / value.den, 4)
        text = str(value).strip()
        if not text:
            return None
        try:
            if "/" in text:
                numerator, denominator = text.split("/", 1)
                denominator = float(denominator)
                if not denominator:
                    return None
                return round(float(numerator) / denominator, 4)
            return round(float(text), 4)
        except ValueError:
            return None

    def _parse_gps_coordinate(self, value, ref) -> float | None:
        if value is None:
            return None
        items = getattr(value, "values", None)
        if not items:
            text = str(value)
            parts = [part.strip() for part in text.strip("[]").split(",") if part.strip()]
        else:
            parts = items
        if len(parts) < 3:
            return None
        degrees = self._ratio_to_float(parts[0]) or 0.0
        minutes = self._ratio_to_float(parts[1]) or 0.0
        seconds = self._ratio_to_float(parts[2]) or 0.0
        decimal = degrees + (minutes / 60.0) + (seconds / 3600.0)
        ref_value = str(ref).strip().upper() if ref else ""
        if ref_value in {"S", "W"}:
            decimal *= -1
        return round(decimal, 6)

    @staticmethod
    def _normalize_exif_datetime(value: str | None) -> str | None:
        if not value:
            return None
        text = value.strip()
        for fmt in ("%Y:%m:%d %H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y:%m:%d %H:%M:%S%z"):
            try:
                return datetime.strptime(text, fmt).isoformat(sep=" ")
            except ValueError:
                continue
        return text


# ── Module-level singleton ────────────────────────────────────────────────────
_catalog: CatalogManager | None = None

def get_catalog(db_path: str = DB_PATH) -> CatalogManager:
    global _catalog
    if _catalog is None:
        _catalog = CatalogManager(db_path)
    return _catalog
