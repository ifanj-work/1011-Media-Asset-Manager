"""
catalog.py — CatalogManager for 1011 Media Asset Manager
Wraps a SQLite database with WAL mode for concurrent reads.

Tables managed here:
  photos          — core file index
  photos_fts      — FTS5 full-text search index (virtual table)
  tags            — per-file tags
  tag_categories  — vocabulary / color for each tag category
  collections     — named virtual albums
  collection_items — collection membership
  activity_log    — JSON-structured event log
"""

import sqlite3
import json
import os
import time
import uuid
from datetime import datetime, timezone
from contextlib import contextmanager
from pathlib import Path

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

                -- FTS5 virtual table for full-text search
                CREATE VIRTUAL TABLE IF NOT EXISTS photos_fts USING fts5(
                    id UNINDEXED,
                    haystack,
                    content=photos,
                    content_rowid=rowid
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

                -- Indexes
                CREATE INDEX IF NOT EXISTS idx_photos_folder  ON photos(folder);
                CREATE INDEX IF NOT EXISTS idx_photos_year    ON photos(year);
                CREATE INDEX IF NOT EXISTS idx_photos_ext     ON photos(ext);
                CREATE INDEX IF NOT EXISTS idx_photos_date    ON photos(date DESC);
                CREATE INDEX IF NOT EXISTS idx_tags_file      ON tags(file_id);
                CREATE INDEX IF NOT EXISTS idx_tags_tag       ON tags(tag);
                CREATE INDEX IF NOT EXISTS idx_ci_collection  ON collection_items(collection_id);
                CREATE INDEX IF NOT EXISTS idx_ci_file        ON collection_items(file_id);
                CREATE INDEX IF NOT EXISTS idx_log_type       ON activity_log(event_type);
                CREATE INDEX IF NOT EXISTS idx_log_created    ON activity_log(created_at);
            """)

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

                # Build FTS haystack
                haystack = " ".join([
                    f["filename"], f["folder"], f["date"], f["year"],
                    " ".join(t for t, _ in f["tags"])
                ])
                conn.execute("""
                    INSERT OR REPLACE INTO photos_fts (id, haystack)
                    VALUES (?, ?)
                """, (f["id"], haystack))

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

    # ── Search ────────────────────────────────────────────────────────────────

    def search(self, query="", file_type=None, sort="newest", page=1,
               per_page=PAGE_SIZE, year=None, date_from=None, date_to=None,
               folder=None):
        """
        Full-text search with optional filters.
        Returns dict with keys: results, total, page, per_page, pages.
        """
        offset = (page - 1) * per_page
        params = []

        if query.strip():
            # FTS join
            base_sql = """
                SELECT p.*, GROUP_CONCAT(t.tag, ',') AS tags_csv
                FROM photos_fts f
                JOIN photos p ON p.id = f.id
                LEFT JOIN tags t ON t.file_id = p.id
                WHERE photos_fts MATCH ?
            """
            params.append(f'"{query.strip()}"*')
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
                SELECT p.*, GROUP_CONCAT(t.tag || ':' || t.category, ',') AS tags_csv
                FROM photos p
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

    def add_tag(self, file_id: str, tag: str, category: str = "custom") -> bool:
        tag = self._normalize_tag(tag)
        if not tag:
            return False
        
        # Auto-detect category from tag_categories if not provided
        if category == "custom":
            category = self._infer_category(tag) or "custom"

        try:
            with get_connection(self.db_path) as conn:
                conn.execute("""
                    INSERT OR IGNORE INTO tags (file_id, tag, category)
                    VALUES (?, ?, ?)
                """, (file_id, tag, category))
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
        with get_connection(self.db_path) as conn:
            for file_id in file_ids:
                for tag in tags:
                    tag_norm = self._normalize_tag(tag)
                    if not tag_norm:
                        continue
                    cat = self._infer_category(tag_norm) or "custom"
                    try:
                        conn.execute("""
                            INSERT OR IGNORE INTO tags (file_id, tag, category)
                            VALUES (?, ?, ?)
                        """, (file_id, tag_norm, cat))
                        success += 1
                    except Exception:
                        pass
                self._update_fts(conn, file_id)
            self._log(conn, "batch_tag", {"file_count": len(file_ids), "tags": tags})
        return {"tagged_files": len(file_ids), "tags_applied": success}

    # ── Tags management ────────────────────────────────────────────────────────

    def get_all_tags(self, category: str = None, sort: str = "count") -> list:
        """Return all distinct tags with usage counts."""
        sql = """
            SELECT t.tag, t.category, COUNT(*) as count
            FROM tags t
            WHERE 1=1
        """
        params = []
        if category and category != "all":
            sql += " AND t.category = ?"
            params.append(category)
        sql += " GROUP BY t.tag, t.category"
        if sort == "az":
            sql += " ORDER BY t.tag ASC"
        elif sort == "newest":
            sql += " ORDER BY MAX(t.created_at) DESC"
        else:
            sql += " ORDER BY count DESC"

        with get_connection(self.db_path) as conn:
            rows = conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]

    def get_tag_categories(self) -> list:
        with get_connection(self.db_path) as conn:
            rows = conn.execute("""
                SELECT tc.name, tc.color, COUNT(t.id) as count
                FROM tag_categories tc
                LEFT JOIN tags t ON t.category = tc.name
                GROUP BY tc.name, tc.color
                ORDER BY count DESC
            """).fetchall()
        return [dict(r) for r in rows]

    def delete_tag_from_vocab(self, tag: str) -> int:
        """Remove a tag from all files. Returns number of files affected."""
        with get_connection(self.db_path) as conn:
            result = conn.execute("DELETE FROM tags WHERE tag = ?", (tag,))
            affected = result.rowcount
            self._log(conn, "tag_delete_vocab", {"tag": tag, "affected": affected})
        return affected

    def merge_tags(self, source: str, target: str) -> int:
        """Reassign all files with source tag → target tag. Returns affected count."""
        source = self._normalize_tag(source)
        target = self._normalize_tag(target)
        cat = self._infer_category(target) or "custom"

        with get_connection(self.db_path) as conn:
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
        return [dict(r) for r in rows]

    def create_collection(self, name: str, description: str = "") -> dict:
        with get_connection(self.db_path) as conn:
            cur = conn.execute("""
                INSERT INTO collections (name, description)
                VALUES (?, ?)
            """, (name, description))
            col_id = cur.lastrowid
            self._log(conn, "collection_create", {"id": col_id, "name": name})
        return {"id": col_id, "name": name, "description": description, "item_count": 0}

    def get_collection(self, col_id: int) -> dict | None:
        with get_connection(self.db_path) as conn:
            row = conn.execute("""
                SELECT c.*, COUNT(ci.id) as item_count
                FROM collections c
                LEFT JOIN collection_items ci ON ci.collection_id = c.id
                WHERE c.id = ?
                GROUP BY c.id
            """, (col_id,)).fetchone()
        return dict(row) if row else None

    def delete_collection(self, col_id: int) -> bool:
        with get_connection(self.db_path) as conn:
            conn.execute("DELETE FROM collections WHERE id = ?", (col_id,))
            self._log(conn, "collection_delete", {"id": col_id})
        return True

    def add_to_collection(self, col_id: int, file_ids: list) -> dict:
        added = 0
        with get_connection(self.db_path) as conn:
            for fid in file_ids:
                try:
                    conn.execute("""
                        INSERT OR IGNORE INTO collection_items (collection_id, file_id)
                        VALUES (?, ?)
                    """, (col_id, fid))
                    added += 1
                except Exception:
                    pass
            # Update updated_at
            conn.execute("""
                UPDATE collections SET updated_at = CURRENT_TIMESTAMP WHERE id = ?
            """, (col_id,))
        return {"added": added}

    def remove_from_collection(self, col_id: int, file_id: str) -> bool:
        with get_connection(self.db_path) as conn:
            conn.execute("""
                DELETE FROM collection_items
                WHERE collection_id = ? AND file_id = ?
            """, (col_id, file_id))
        return True

    def get_collection_files(self, col_id: int, page=1, per_page=PAGE_SIZE) -> dict:
        offset = (page - 1) * per_page
        with get_connection(self.db_path) as conn:
            total = conn.execute("""
                SELECT COUNT(*) FROM collection_items WHERE collection_id = ?
            """, (col_id,)).fetchone()[0]

            rows = conn.execute("""
                SELECT p.*, GROUP_CONCAT(t.tag, ',') AS tags_csv
                FROM collection_items ci
                JOIN photos p ON p.id = ci.file_id
                LEFT JOIN tags t ON t.file_id = p.id
                WHERE ci.collection_id = ?
                GROUP BY p.id
                ORDER BY ci.sort_order, ci.added_at
                LIMIT ? OFFSET ?
            """, (col_id, per_page, offset)).fetchall()

        return {
            "results": [self._row_to_file_dict(r) for r in rows],
            "total": total, "page": page, "per_page": per_page,
            "pages": max(1, -(-total // per_page)),
        }

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

        pct_tagged = round((tagged / total * 100) if total else 0, 1)
        return {
            "total_files": total,
            "tagged_files": tagged,
            "pct_tagged": pct_tagged,
            "collections": col_count,
            "total_size_bytes": total_size,
            "total_size_human": self._human_size(total_size),
            "top_tags": [dict(r) for r in top_tags],
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

    # ── Utility ───────────────────────────────────────────────────────────────

    @staticmethod
    def _normalize_tag(tag: str) -> str:
        import re
        tag = tag.strip().lower()
        tag = re.sub(r'[^a-z0-9\-_]', '-', tag)
        tag = re.sub(r'-+', '-', tag).strip('-')
        return tag[:64]  # max length

    def _infer_category(self, tag: str) -> str | None:
        """Guess category from existing tags table."""
        with get_connection(self.db_path) as conn:
            row = conn.execute("""
                SELECT category FROM tags WHERE tag = ?
                ORDER BY created_at DESC LIMIT 1
            """, (tag,)).fetchone()
        return row["category"] if row else None


# ── Module-level singleton ────────────────────────────────────────────────────
_catalog: CatalogManager | None = None

def get_catalog(db_path: str = DB_PATH) -> CatalogManager:
    global _catalog
    if _catalog is None:
        _catalog = CatalogManager(db_path)
    return _catalog
