"""
app.py — 1011 Media Asset Manager
Flask application: page routes + JSON API
"""

import os
import mimetypes
from pathlib import Path
from flask import (
    Flask, render_template, jsonify, request,
    abort, send_file, Response, send_from_directory
)
import io
import zipfile
from catalog import get_catalog

app = Flask(__name__)
app.config["JSON_SORT_KEYS"] = False

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

    try:
        page     = max(1, int(request.args.get("page", 1)))
        per_page = min(200, max(1, int(request.args.get("per_page", 50))))
    except ValueError:
        page, per_page = 1, 50

    result = catalog.search(
        query=q, file_type=file_type, sort=sort,
        page=page, per_page=per_page,
        year=year, date_from=date_from, date_to=date_to,
        folder=folder,
    )
    return jsonify(result)

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

@app.route("/api/tags/categories")
def api_tag_categories():
    cats = catalog.get_tag_categories()
    return jsonify({"categories": cats})

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
    return jsonify(catalog.get_collection_files(col_id, page, per_page))

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

@app.route("/api/download/<file_id>")
def api_download(file_id):
    f = catalog.get_file(file_id)
    if not f:
        abort(404, description="File not found")
    
    path = Path(f["path"])
    if not path.exists():
        # Fallback to stub for prototype mode if file is missing from disk
        return jsonify({"error": f"File missing from disk: {path}"}), 404
        
    return send_file(path, as_attachment=True, download_name=path.name)

@app.route("/api/batch/download", methods=["POST"])
def api_batch_download():
    data = request.get_json(force=True) or {}
    file_ids = data.get("file_ids", [])
    if not file_ids:
        return jsonify({"error": "file_ids required"}), 400
        
    files = [catalog.get_file(fid) for fid in file_ids]
    files = [f for f in files if f and Path(f["path"]).exists()]
    
    if not files:
        return jsonify({"error": "No valid files found for download"}), 404
        
    # In a real app, this should be an async job. For the prototype, build ZIP in memory.
    memory_file = io.BytesIO()
    with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zf:
        for f in files:
            p = Path(f["path"])
            # In a real app, handle name collisions inside the ZIP
            zf.write(p, p.name)
            
    memory_file.seek(0)
    return send_file(
        memory_file,
        mimetype="application/zip",
        as_attachment=True,
        download_name="1011_Media_Batch.zip"
    )

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
#  API — Thumbnail stub (serves icon until Phase 3 indexer)
# ═══════════════════════════════════════════════════════════════════════════

@app.route("/api/thumb/<file_id>")
def api_thumbnail(file_id):
    """
    Serves a placeholder SVG thumbnail until the background indexer
    generates real JPEG thumbs in Phase 3.
    """
    f = catalog.get_file(file_id)
    ext = (f.get("ext", "jpg") if f else "jpg").lower()

    if ext in ("mp4", "mov", "avi", "mkv", "mxf"):
        icon, color = "video", "#06B6D4"
    elif ext in ("psd", "psb", "ai"):
        icon, color = "layers", "#A855F7"
    else:
        icon, color = "image", "#6366F1"

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="400" height="300"
      viewBox="0 0 400 300" style="background:#18181b;">
  <rect width="400" height="300" fill="#18181b"/>
  <rect x="1" y="1" width="398" height="298" fill="none" stroke="#3f3f46" stroke-width="1"/>
  <text x="200" y="130" font-family="sans-serif" font-size="64"
        text-anchor="middle" fill="{color}" opacity="0.3">◼</text>
  <text x="200" y="175" font-family="monospace" font-size="13"
        text-anchor="middle" fill="#52525b">{ext.upper()}</text>
</svg>"""

    return Response(svg, mimetype="image/svg+xml",
                    headers={"Cache-Control": "public, max-age=86400"})

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
