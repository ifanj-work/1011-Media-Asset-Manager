"""
app.py — 1011 Media Asset Manager
Flask application: page routes + JSON API
"""

import os
import re
from pathlib import Path
from flask import (
    Flask, render_template, jsonify, request,
    abort, send_file, Response
)
import io
import zipfile
from PIL import Image, ImageOps, UnidentifiedImageError
try:
    import imageio.v2 as imageio
except ImportError:  # pragma: no cover
    imageio = None
from catalog import get_catalog

app = Flask(__name__)
app.config["JSON_SORT_KEYS"] = False

THUMB_CACHE_DIR = Path(os.environ.get("THUMB_CACHE_DIR", ".tmp/thumb-cache"))
THUMB_MAX_SIZE = (1600, 1600)
VIDEO_EXTENSIONS = {"mp4", "mov", "avi", "mkv", "mxf", "r3d", "braw"}

# ── Jinja Filters ──────────────────────────────────────────────────────────
@app.template_filter('format_number')
def format_number(value):
    try:
        return f"{int(value):,}"
    except (ValueError, TypeError):
        return value

@app.template_filter('format_bytes')
def format_bytes(size):
    try:
        size = float(size)
    except (ValueError, TypeError):
        return "0 B"
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size < 1024.0:
            return f"{size:.1f} {unit}"
        size /= 1024.0
    return f"{size:.1f} PB"

# ── Catalog singleton ──────────────────────────────────────────────────────
DB_PATH = os.environ.get("DB_PATH", "photo_catalog.db")
catalog  = get_catalog(DB_PATH)

# ═══════════════════════════════════════════════════════════════════════════
#  Page Routes
# ═══════════════════════════════════════════════════════════════════════════

@app.route("/")
def index():
    stats = catalog.get_stats()
    activity = catalog.get_activity_log(limit=10)
    return render_template("dashboard.html", stats=stats, activity=activity)

@app.route("/search")
def search():
    return render_template("search.html")

@app.route("/tags")
def tags():
    categories = catalog.get_tag_categories()
    return render_template("tags.html", categories=categories)

@app.route("/collections")
def collections():
    cols = catalog.get_collections()
    return render_template("collections.html", collections=cols)

@app.route("/collections/<int:col_id>")
def collection_detail(col_id):
    col = catalog.get_collection(col_id)
    if not col:
        abort(404, description="Collection not found")
    return render_template("collection_detail.html", collection=col)

# ═══════════════════════════════════════════════════════════════════════════
#  API — Search
# ═══════════════════════════════════════════════════════════════════════════

@app.route("/api/search")
def api_search():
    """
    GET /api/search
    Query params:
      q          — full-text query string
      type       — all | images | videos | psd
      sort       — newest | oldest | name-az | name-za | size-desc
      page       — int (default 1)
      per_page   — int (default 50, max 200)
      year       — e.g. "2026"
      date_from  — "YYYY-MM-DD"
      date_to    — "YYYY-MM-DD"
      folder     — folder slug
    """
    q         = request.args.get("q", "").strip()
    file_type = request.args.get("type", "all")
    sort      = request.args.get("sort", "newest")
    year      = request.args.get("year")
    date_from = request.args.get("date_from")
    date_to   = request.args.get("date_to")
    folder    = request.args.get("folder")
    folder_prefix = request.args.get("folder_prefix")
    saved_search_id = request.args.get("saved_search_id")

    try:
        page     = max(1, int(request.args.get("page", 1)))
        per_page = min(200, max(1, int(request.args.get("per_page", 50))))
    except ValueError:
        page, per_page = 1, 50

    result = catalog.search(
        query=q, file_type=file_type, sort=sort,
        page=page, per_page=per_page,
        year=year, date_from=date_from, date_to=date_to,
        folder=folder, folder_prefix=folder_prefix,
    )
    if saved_search_id:
        try:
            catalog.log_saved_search_apply(int(saved_search_id))
        except ValueError:
            pass
    return jsonify(result)

@app.route("/api/folders")
def api_folders():
    return jsonify({"folders": catalog.get_folder_tree()})

@app.route("/api/saved-searches", methods=["GET"])
def api_get_saved_searches():
    return jsonify({"saved_searches": catalog.get_saved_searches()})

@app.route("/api/saved-searches", methods=["POST"])
def api_create_saved_search():
    data = request.get_json(force=True) or {}
    try:
        saved_search = catalog.create_saved_search(data)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:
        return jsonify({"error": str(exc)}), 409
    return jsonify(saved_search), 201

@app.route("/api/saved-searches/<int:saved_id>", methods=["GET"])
def api_get_saved_search(saved_id):
    saved_search = catalog.get_saved_search(saved_id)
    if not saved_search:
        abort(404, description="Saved search not found")
    return jsonify(saved_search)

@app.route("/api/saved-searches/<int:saved_id>", methods=["PATCH"])
def api_update_saved_search(saved_id):
    data = request.get_json(force=True) or {}
    try:
        saved_search = catalog.update_saved_search(saved_id, data)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:
        return jsonify({"error": str(exc)}), 409
    if not saved_search:
        abort(404, description="Saved search not found")
    return jsonify(saved_search)

@app.route("/api/saved-searches/<int:saved_id>", methods=["DELETE"])
def api_delete_saved_search(saved_id):
    existing = catalog.get_saved_search(saved_id)
    if not existing:
        abort(404, description="Saved search not found")
    catalog.delete_saved_search(saved_id)
    return jsonify({"ok": True})

# ═══════════════════════════════════════════════════════════════════════════
#  API — Files
# ═══════════════════════════════════════════════════════════════════════════

@app.route("/api/file/<file_id>")
def api_get_file(file_id):
    f = catalog.get_file(file_id)
    if not f:
        abort(404, description="File not found")
    return jsonify(f)

@app.route("/api/file/<file_id>/tags", methods=["GET"])
def api_get_file_tags(file_id):
    tags = catalog.get_file_tags(file_id)
    return jsonify({"tags": tags})

@app.route("/api/file/<file_id>/tags", methods=["POST"])
def api_add_tag(file_id):
    data     = request.get_json(force=True) or {}
    tag      = (data.get("tag") or "").strip()
    category = data.get("category", "custom")

    if not tag:
        return jsonify({"error": "tag is required"}), 400

    ok = catalog.add_tag(file_id, tag, category)
    if not ok:
        return jsonify({"error": "Failed to add tag (duplicate or invalid)"}), 409
    return jsonify({"ok": True, "tag": catalog._normalize_tag(tag)}), 201

@app.route("/api/file/<file_id>/tags/<tag>", methods=["DELETE"])
def api_remove_tag(file_id, tag):
    catalog.remove_tag(file_id, tag)
    return jsonify({"ok": True})

@app.route("/api/batch/tags", methods=["POST"])
def api_batch_tag():
    """
    POST /api/batch/tags
    Body: { "file_ids": [...], "tags": [...] }
    """
    data     = request.get_json(force=True) or {}
    file_ids = data.get("file_ids", [])
    tags     = data.get("tags", [])

    if not file_ids or not tags:
        return jsonify({"error": "file_ids and tags are required"}), 400

    result = catalog.batch_add_tags(file_ids, tags)
    return jsonify(result)

@app.route("/api/batch/tags/remove", methods=["POST"])
def api_batch_tag_remove():
    """
    POST /api/batch/tags/remove
    Body: { "file_ids": [...], "tags": [...] }
    """
    data     = request.get_json(force=True) or {}
    file_ids = data.get("file_ids", [])
    tags     = data.get("tags", [])

    if not file_ids or not tags:
        return jsonify({"error": "file_ids and tags are required"}), 400

    result = catalog.batch_remove_tags(file_ids, tags)
    return jsonify(result)

# ═══════════════════════════════════════════════════════════════════════════
#  API — Tag Vocabulary
# ═══════════════════════════════════════════════════════════════════════════

@app.route("/api/tags")
def api_get_tags():
    """
    GET /api/tags
    Query params:
      category — filter by category name
      sort     — count (default) | az | newest
      q        — prefix search
    """
    category = request.args.get("category", "all")
    sort     = request.args.get("sort", "count")
    q        = request.args.get("q", "").strip().lower()

    tags = catalog.get_all_tags(
        category=category if category != "all" else None,
        sort=sort
    )

    # JS autocomplete prefix search
    if q:
        tags = [t for t in tags if t["tag"].startswith(q)]

    return jsonify({"tags": tags})

@app.route("/api/tags", methods=["POST"])
def api_create_tag():
    data = request.get_json(force=True) or {}
    tag = (data.get("tag") or "").strip()
    category = (data.get("category") or "custom").strip()

    if not tag:
        return jsonify({"error": "tag is required"}), 400

    result = catalog.create_tag_vocabulary(tag, category)
    if not result.get("ok"):
        return jsonify({"error": result.get("error", "Failed to create tag")}), 400

    status_code = 201 if result.get("created") else 200
    return jsonify(result), status_code

@app.route("/api/tags/categories")
def api_tag_categories():
    cats = catalog.get_tag_categories()
    return jsonify({"categories": cats})

@app.route("/api/tags/analytics")
def api_tag_analytics():
    return jsonify(catalog.get_tag_analytics())

@app.route("/api/tags/<tag>", methods=["DELETE"])
def api_delete_tag(tag):
    affected = catalog.delete_tag_from_vocab(tag)
    return jsonify({"ok": True, "files_affected": affected})

@app.route("/api/tags/merge", methods=["POST"])
def api_merge_tags():
    data   = request.get_json(force=True) or {}
    source = data.get("source", "").strip()
    target = data.get("target", "").strip()
    if not source or not target:
        return jsonify({"error": "source and target are required"}), 400
    affected = catalog.merge_tags(source, target)
    return jsonify({"ok": True, "files_affected": affected})

# ═══════════════════════════════════════════════════════════════════════════
#  API — Collections
# ═══════════════════════════════════════════════════════════════════════════

@app.route("/api/collections")
def api_get_collections():
    return jsonify({"collections": catalog.get_collections()})

@app.route("/api/collections", methods=["POST"])
def api_create_collection():
    data = request.get_json(force=True) or {}
    name = (data.get("name") or "").strip()
    desc = (data.get("description") or "").strip()
    if not name:
        return jsonify({"error": "name is required"}), 400
    col = catalog.create_collection(name, desc)
    return jsonify(col), 201

@app.route("/api/collections/<int:col_id>")
def api_get_collection(col_id):
    col = catalog.get_collection(col_id)
    if not col:
        abort(404)
    return jsonify(col)

@app.route("/api/collections/<int:col_id>", methods=["DELETE"])
def api_delete_collection(col_id):
    catalog.delete_collection(col_id)
    return jsonify({"ok": True})

@app.route("/api/collections/<int:col_id>/items", methods=["GET"])
def api_collection_items(col_id):
    try:
        page     = max(1, int(request.args.get("page", 1)))
        per_page = min(200, int(request.args.get("per_page", 50)))
    except ValueError:
        page, per_page = 1, 50
    sort = request.args.get("sort", "newest")
    return jsonify(catalog.get_collection_files(col_id, page, per_page, sort=sort))

@app.route("/api/collections/<int:col_id>/items", methods=["POST"])
def api_add_to_collection(col_id):
    data     = request.get_json(force=True) or {}
    file_ids = data.get("file_ids", [])
    if not file_ids:
        return jsonify({"error": "file_ids required"}), 400
    result = catalog.add_to_collection(col_id, file_ids)
    return jsonify(result)

@app.route("/api/collections/<int:col_id>/items/<file_id>", methods=["DELETE"])
def api_remove_from_collection(col_id, file_id):
    catalog.remove_from_collection(col_id, file_id)
    return jsonify({"ok": True})

# ═══════════════════════════════════════════════════════════════════════════
#  API — Downloads
# ═══════════════════════════════════════════════════════════════════════════

@app.route("/api/file/<file_id>/raw")
def api_serve_file(file_id):
    """Serve file inline (for video playback and preview)."""
    f = catalog.get_file(file_id)
    if not f:
        abort(404, description="File not found")
    
    path = Path(f["path"])
    if not path.exists():
        abort(404, description="File missing from disk")
    
    return send_file(path, as_attachment=False, conditional=True, max_age=86400)

@app.route("/api/download/<file_id>")
def api_download(file_id):
    f = catalog.get_file(file_id)
    if not f:
        abort(404, description="File not found")
    
    path = Path(f["path"])
    if not path.exists():
        # Fallback to stub for prototype mode if file is missing from disk
        return jsonify({"error": f"File missing from disk: {path}"}), 404
    catalog.log_event("download_single", {
        "file_id": file_id,
        "filename": path.name,
    })
    return send_file(path, as_attachment=True, download_name=path.name)

@app.route("/api/batch/download", methods=["POST"])
def api_batch_download():
    data = request.get_json(force=True) or {}
    file_ids = data.get("file_ids", [])
    if not file_ids:
        return jsonify({"error": "file_ids required"}), 400
        
    requested_files = [catalog.get_file(fid) for fid in file_ids]
    available_files = []
    missing_files = []
    for file_record in requested_files:
        if not file_record:
            continue
        path = Path(file_record["path"])
        if path.exists():
            available_files.append(file_record)
        else:
            missing_files.append(file_record)

    if not available_files:
        return jsonify({
            "error": "No valid files found for download",
            "requested": len(file_ids),
            "missing": len(missing_files),
        }), 404

    memory_file = io.BytesIO()
    with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zf:
        for f in available_files:
            p = Path(f["path"])
            zf.write(p, p.name)
        if missing_files:
            manifest_lines = [
                "Some requested files were unavailable and were not included in this archive.",
                "",
            ]
            manifest_lines.extend(
                f"- {item.get('filename', item.get('id'))}: {item.get('path', '')}"
                for item in missing_files
            )
            zf.writestr("missing-files.txt", "\n".join(manifest_lines))

    memory_file.seek(0)
    response = send_file(
        memory_file,
        mimetype="application/zip",
        as_attachment=True,
        download_name="1011_Media_Batch.zip"
    )
    response.headers["X-Archive-Requested"] = str(len(file_ids))
    response.headers["X-Archive-Included"] = str(len(available_files))
    response.headers["X-Archive-Missing"] = str(len(missing_files))
    catalog.log_event("download_batch", {
        "requested_file_count": len(file_ids),
        "included_file_count": len(available_files),
        "missing_file_count": len(missing_files),
    })
    return response

# ═══════════════════════════════════════════════════════════════════════════
#  API — Stats & Activity
# ═══════════════════════════════════════════════════════════════════════════

@app.route("/api/stats")
def api_stats():
    return jsonify(catalog.get_stats())

@app.route("/api/activity")
def api_activity():
    try:
        limit = min(100, int(request.args.get("limit", 20)))
    except ValueError:
        limit = 20
    return jsonify({"activity": catalog.get_activity_log(limit)})

# ═══════════════════════════════════════════════════════════════════════════
#  API — Configuration & Maintenance
# ═══════════════════════════════════════════════════════════════════════════

@app.route("/api/config", methods=["GET"])
def api_get_config():
    return jsonify(catalog.get_config())

@app.route("/api/config", methods=["POST"])
def api_update_config():
    data = request.get_json(force=True) or {}
    for key, value in data.items():
        catalog.update_config(key, value)
    return jsonify({"ok": True})

@app.route("/api/scan", methods=["POST"])
def api_scan():
    """
    Trigger a directory scan.
    Body: { "path": "z:/path/to/media;\\\\server\\share\\media" }
    """
    data = request.get_json(force=True) or {}
    path = data.get("path")
    
    if not path:
        # Try to get from config
        config = catalog.get_config()
        path = config.get("library_path")

    if not path:
        return jsonify({"error": "No scan path provided or configured"}), 400

    # For safety/simplicity in this prototype, we block while scanning.
    # In a real app, this should be a background task (e.g. Celery).
    results = catalog.scan_directories(path)
    
    if "error" in results:
        return jsonify(results), 400
        
    return jsonify(results)

# ═══════════════════════════════════════════════════════════════════════════
#  API — Thumbnail stub (serves icon until Phase 3 indexer)
# ═══════════════════════════════════════════════════════════════════════════

def _placeholder_thumbnail_svg(ext: str) -> str:
    ext = (ext or "jpg").lower()
    if ext in VIDEO_EXTENSIONS:
        color = "#06B6D4"
    elif ext in {"psd", "psb", "ai", "eps"}:
        color = "#A855F7"
    else:
        color = "#6366F1"

    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="400" height="300"
      viewBox="0 0 400 300" style="background:#18181b;">
  <rect width="400" height="300" fill="#18181b"/>
  <rect x="1" y="1" width="398" height="298" fill="none" stroke="#3f3f46" stroke-width="1"/>
  <text x="200" y="130" font-family="sans-serif" font-size="64"
        text-anchor="middle" fill="{color}" opacity="0.3">&#9670;</text>
  <text x="200" y="175" font-family="monospace" font-size="13"
        text-anchor="middle" fill="#52525b">{ext.upper()}</text>
</svg>"""


def _safe_thumb_stem(file_id: str) -> str:
    return re.sub(r"[^A-Za-z0-9_-]+", "-", file_id).strip("-") or "thumb"


def _build_thumb_cache_path(file_id: str, source_path: Path) -> Path:
    stat = source_path.stat()
    THUMB_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    stem = _safe_thumb_stem(file_id)
    return THUMB_CACHE_DIR / f"{stem}-{stat.st_mtime_ns}-{stat.st_size}.jpg"


def _render_pil_thumbnail(source_path: Path, thumb_path: Path) -> Path | None:
    try:
        with Image.open(source_path) as img:
            img = ImageOps.exif_transpose(img)
            if getattr(img, "n_frames", 1) > 1:
                img.seek(0)

            if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
                rgba = img.convert("RGBA")
                background = Image.new("RGBA", rgba.size, "#18181B")
                img = Image.alpha_composite(background, rgba).convert("RGB")
            elif img.mode != "RGB":
                img = img.convert("RGB")

            img.thumbnail(THUMB_MAX_SIZE, Image.Resampling.LANCZOS)
            img.save(thumb_path, format="JPEG", quality=88, optimize=True)
        return thumb_path
    except (UnidentifiedImageError, OSError, ValueError):
        return None


def _get_thumbnail_path(file_record: dict) -> Path | None:
    source_path = Path(file_record["path"])
    if not source_path.exists():
        return None

    ext = (file_record.get("ext") or source_path.suffix.lstrip(".")).lower()
    thumb_path = _build_thumb_cache_path(file_record["id"], source_path)
    if thumb_path.exists():
        return thumb_path

    stale_pattern = f"{_safe_thumb_stem(file_record['id'])}-*.jpg"
    for stale_path in THUMB_CACHE_DIR.glob(stale_pattern):
        if stale_path != thumb_path:
            stale_path.unlink(missing_ok=True)

    if ext in VIDEO_EXTENSIONS:
        return _render_video_thumbnail(source_path, thumb_path)

    return _render_pil_thumbnail(source_path, thumb_path)


def _render_video_thumbnail(source_path: Path, thumb_path: Path) -> Path | None:
    if imageio is None:
        return None

    try:
        with imageio.get_reader(str(source_path), format="ffmpeg") as reader:
            try:
                frame = reader.get_data(0)
            except Exception:
                frame = next(iter(reader), None)

        if frame is None:
            return None

        img = Image.fromarray(frame)
        if img.mode != "RGB":
            img = img.convert("RGB")
        img.thumbnail(THUMB_MAX_SIZE, Image.Resampling.LANCZOS)
        img.save(thumb_path, format="JPEG", quality=88, optimize=True)
        return thumb_path
    except Exception:
        return None


@app.route("/api/thumb/<file_id>")
def api_thumbnail(file_id):
    """
    Serves a placeholder SVG thumbnail until the background indexer
    generates real JPEG thumbs in Phase 3.
    """
    f = catalog.get_file(file_id)
    if not f:
        abort(404, description="File not found")

    thumb_path = _get_thumbnail_path(f)
    if thumb_path and thumb_path.exists():
        return send_file(
            thumb_path,
            mimetype="image/jpeg",
            conditional=True,
            max_age=86400,
        )

    ext = (f.get("ext", "jpg")).lower()
    svg = _placeholder_thumbnail_svg(ext)
    return Response(
        svg,
        mimetype="image/svg+xml",
        headers={"Cache-Control": "public, max-age=86400"},
    )

# ═══════════════════════════════════════════════════════════════════════════
#  Error handlers
# ═══════════════════════════════════════════════════════════════════════════

@app.errorhandler(404)
def not_found(e):
    if request.path.startswith("/api/"):
        return jsonify({"error": str(e)}), 404
    return render_template("layout.html"), 404

@app.errorhandler(500)
def server_error(e):
    if request.path.startswith("/api/"):
        return jsonify({"error": "Internal server error"}), 500
    return render_template("layout.html"), 500

# ═══════════════════════════════════════════════════════════════════════════
#  Run
# ═══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("1011 Media Asset Manager — http://localhost:5000")
    app.run(debug=True, host="0.0.0.0", port=5000, use_reloader=True)
