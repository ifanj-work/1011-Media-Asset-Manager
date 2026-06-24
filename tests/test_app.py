import importlib
import os
import shutil
import tempfile
import unittest
import zipfile
from pathlib import Path
from PIL import Image


class MediaAssetManagerTestCase(unittest.TestCase):
    def setUp(self):
        workspace_tmp = Path(".tmp") / "test-dbs"
        workspace_tmp.mkdir(parents=True, exist_ok=True)
        self.tempdir_path = Path(tempfile.mkdtemp(prefix="catalog-", dir=workspace_tmp))
        self.db_path = self.tempdir_path / "test_catalog.db"
        self.previous_db_path = os.environ.get("DB_PATH")
        os.environ["DB_PATH"] = str(self.db_path)

        import catalog as catalog_module
        import app as app_module

        self.catalog_module = importlib.reload(catalog_module)
        self.app_module = importlib.reload(app_module)
        self.app = self.app_module.app
        self.app.config["TESTING"] = True
        self.client = self.app.test_client()

    def tearDown(self):
        if self.previous_db_path is None:
            os.environ.pop("DB_PATH", None)
        else:
            os.environ["DB_PATH"] = self.previous_db_path
        shutil.rmtree(self.tempdir_path, ignore_errors=True)

    def get_json(self, path, **kwargs):
        response = self.client.get(path, **kwargs)
        self.assertEqual(response.status_code, 200, msg=path)
        return response.get_json()

    def post_json(self, path, payload, expected_status=200):
        response = self.client.post(path, json=payload)
        self.assertEqual(response.status_code, expected_status, msg=path)
        return response.get_json()

    def delete_json(self, path, expected_status=200):
        response = self.client.delete(path)
        self.assertEqual(response.status_code, expected_status, msg=path)
        return response.get_json()

    def patch_json(self, path, payload, expected_status=200):
        response = self.client.patch(path, json=payload)
        self.assertEqual(response.status_code, expected_status, msg=path)
        return response.get_json()

    def test_page_routes_smoke(self):
        for path in ["/", "/search", "/tags", "/collections", "/collections/1"]:
            response = self.client.get(path)
            self.assertEqual(response.status_code, 200, msg=path)

        search_page = self.client.get("/search")
        body = search_page.get_data(as_text=True)
        self.assertNotIn('href="/settings"', body)
        self.assertIn("Copy File Path", body)

    def test_api_smoke_endpoints(self):
        stats = self.get_json("/api/stats")
        self.assertEqual(stats["total_files"], 10)

        tags = self.get_json("/api/tags")
        self.assertTrue(tags["tags"])

        collections = self.get_json("/api/collections")
        self.assertTrue(collections["collections"])

        search = self.get_json("/api/search?per_page=3")
        self.assertEqual(len(search["results"]), 3)

        collection_items = self.get_json("/api/collections/1/items")
        self.assertIn("results", collection_items)

        folders = self.get_json("/api/folders")
        self.assertIn("folders", folders)

        saved_searches = self.get_json("/api/saved-searches")
        self.assertIn("saved_searches", saved_searches)

    def test_search_regressions_and_filtering(self):
        for term in ["persija", "match", "liga-1", "Persija 2024"]:
            data = self.get_json(f"/api/search?q={term}")
            self.assertGreater(data["total"], 0, msg=term)

        filtered = self.get_json("/api/search?q=Persija 2024&type=videos")
        self.assertGreater(filtered["total"], 0)
        self.assertTrue(all(item["ext"] == "mp4" for item in filtered["results"]))

    def test_batch_tag_counts_reflect_new_inserts(self):
        first = self.post_json(
            "/api/batch/tags",
            {"file_ids": ["f001", "f002"], "tags": ["stabilization-pass"]},
        )
        self.assertEqual(first["tagged_files"], 2)
        self.assertEqual(first["tags_applied"], 2)

        second = self.post_json(
            "/api/batch/tags",
            {"file_ids": ["f001", "f002"], "tags": ["stabilization-pass"]},
        )
        self.assertEqual(second["tagged_files"], 0)
        self.assertEqual(second["tags_applied"], 0)

    def test_tag_vocabulary_create_infer_merge_and_delete(self):
        before_categories = {
            row["name"]: row["count"]
            for row in self.get_json("/api/tags/categories")["categories"]
        }

        created = self.post_json(
            "/api/tags",
            {"tag": "press kit", "category": "event"},
            expected_status=201,
        )
        self.assertTrue(created["created"])
        self.assertEqual(created["tag"], "press-kit")
        self.assertEqual(created["count"], 0)

        repeated = self.post_json(
            "/api/tags",
            {"tag": "press kit", "category": "event"},
        )
        self.assertFalse(repeated["created"])

        after_categories = {
            row["name"]: row["count"]
            for row in self.get_json("/api/tags/categories")["categories"]
        }
        self.assertEqual(after_categories["event"], before_categories["event"] + 1)

        event_tags = self.get_json("/api/tags?category=event&sort=az")["tags"]
        press_kit = next(tag for tag in event_tags if tag["tag"] == "press-kit")
        self.assertEqual(press_kit["count"], 0)

        tag_added = self.post_json(
            "/api/file/f001/tags",
            {"tag": "press-kit"},
            expected_status=201,
        )
        self.assertEqual(tag_added["tag"], "press-kit")

        file_tags = self.get_json("/api/file/f001/tags")["tags"]
        press_kit_assignment = next(tag for tag in file_tags if tag["tag"] == "press-kit")
        self.assertEqual(press_kit_assignment["category"], "event")

        self.post_json(
            "/api/file/f002/tags",
            {"tag": "liga1", "category": "event"},
            expected_status=201,
        )
        merged = self.post_json("/api/tags/merge", {"source": "liga1", "target": "liga-1"})
        self.assertEqual(merged["files_affected"], 1)

        f002_tags = self.get_json("/api/file/f002/tags")["tags"]
        tag_names = {tag["tag"] for tag in f002_tags}
        self.assertIn("liga-1", tag_names)
        self.assertNotIn("liga1", tag_names)

        deleted = self.delete_json("/api/tags/press-kit")
        self.assertEqual(deleted["files_affected"], 1)

        updated_f001_tags = self.get_json("/api/file/f001/tags")["tags"]
        self.assertNotIn("press-kit", {tag["tag"] for tag in updated_f001_tags})

        all_tags = self.get_json("/api/tags?sort=az")["tags"]
        self.assertNotIn("press-kit", {tag["tag"] for tag in all_tags})

    def test_collection_flows_and_results_payload(self):
        collection = self.post_json(
            "/api/collections",
            {"name": "Regression Set", "description": "Collection flow test"},
            expected_status=201,
        )
        collection_id = collection["id"]

        first_add = self.post_json(
            f"/api/collections/{collection_id}/items",
            {"file_ids": ["f001", "f002"]},
        )
        self.assertEqual(first_add["added"], 2)

        duplicate_add = self.post_json(
            f"/api/collections/{collection_id}/items",
            {"file_ids": ["f001", "f002"]},
        )
        self.assertEqual(duplicate_add["added"], 0)

        items = self.get_json(f"/api/collections/{collection_id}/items?sort=oldest")
        self.assertEqual(items["total"], 2)
        self.assertEqual(len(items["results"]), 2)
        self.assertEqual([item["id"] for item in items["results"]], ["f001", "f002"])

        removed = self.delete_json(f"/api/collections/{collection_id}/items/f001")
        self.assertTrue(removed["ok"])

        after_remove = self.get_json(f"/api/collections/{collection_id}/items")
        self.assertEqual(after_remove["total"], 1)
        self.assertEqual(after_remove["results"][0]["id"], "f002")

    def test_scan_supports_multiple_semicolon_delimited_paths(self):
        library_a = self.tempdir_path / "library-a"
        library_b = self.tempdir_path / "library-b"
        library_a.mkdir()
        library_b.mkdir()

        (library_a / "alpha-match.jpg").write_bytes(b"fake-jpg-a")
        (library_b / "beta-training.png").write_bytes(b"fake-png-b")

        invalid_path = self.tempdir_path / "missing-library"
        multi_path = f"{library_a}; {library_b}; {invalid_path}"

        saved = self.post_json("/api/config", {"library_path": multi_path})
        self.assertTrue(saved["ok"])

        config = self.get_json("/api/config")
        self.assertEqual(config["library_path"], f"{library_a}; {library_b}; {invalid_path}")

        report = self.post_json("/api/scan", {})
        self.assertEqual(report["new"], 2)
        self.assertEqual(report["found"], 2)
        self.assertEqual(len(report["scanned_paths"]), 2)
        self.assertEqual(report["invalid_paths"], [str(invalid_path)])

        updated_config = self.get_json("/api/config")
        self.assertEqual(updated_config["library_path"], f"{library_a}; {library_b}")

        alpha_results = self.get_json("/api/search?q=alpha")
        beta_results = self.get_json("/api/search?q=beta")
        self.assertGreaterEqual(alpha_results["total"], 1)
        self.assertGreaterEqual(beta_results["total"], 1)

    def test_folder_prefix_and_saved_search_crud(self):
        library_root = self.tempdir_path / "library"
        nested = library_root / "matchday" / "gallery"
        nested.mkdir(parents=True)
        Image.new("RGB", (320, 240), "#22c55e").save(library_root / "root-alpha.jpg", format="JPEG")
        Image.new("RGB", (320, 240), "#3b82f6").save(nested / "nested-beta.jpg", format="JPEG")

        report = self.post_json("/api/scan", {"path": str(library_root)})
        self.assertEqual(report["new"], 2)

        folders = self.get_json("/api/folders")["folders"]
        self.assertTrue(folders)
        root_name = library_root.name
        self.assertIn(root_name, {folder["name"] for folder in folders})

        root_results = self.get_json(f"/api/search?folder_prefix={root_name}")
        self.assertEqual(root_results["total"], 2)

        nested_prefix = f"{root_name}\\matchday"
        nested_results = self.get_json(f"/api/search?folder_prefix={nested_prefix}")
        self.assertEqual(nested_results["total"], 1)
        self.assertEqual(nested_results["results"][0]["filename"], "nested-beta.jpg")

        created = self.post_json(
            "/api/saved-searches",
            {
                "name": "Nested Beta",
                "query": "beta",
                "file_type": "images",
                "sort": "name-az",
                "folder_prefix": nested_prefix,
            },
            expected_status=201,
        )
        saved_id = created["id"]

        updated = self.patch_json(
            f"/api/saved-searches/{saved_id}",
            {"name": "Nested Beta Updated"},
        )
        self.assertEqual(updated["name"], "Nested Beta Updated")

        search = self.get_json(f"/api/search?q=beta&saved_search_id={saved_id}")
        self.assertEqual(search["total"], 1)

        activity = self.get_json("/api/activity?limit=20")["activity"]
        self.assertTrue(any(item["event_type"] == "saved_search_apply" for item in activity))

        deleted = self.delete_json(f"/api/saved-searches/{saved_id}")
        self.assertTrue(deleted["ok"])

    def test_scan_extracts_metadata_for_supported_images(self):
        image_dir = self.tempdir_path / "metadata-library"
        image_dir.mkdir()
        image_path = image_dir / "meta-sample.jpg"

        exif = Image.Exif()
        exif[271] = "Canon"
        exif[272] = "EOS R6"
        exif[42036] = "RF24-70mm"
        exif[34855] = 640
        exif[33437] = (28, 10)
        exif[37386] = (70, 1)
        exif[33434] = (1, 250)
        exif[36867] = "2026:04:09 10:30:00"
        Image.new("RGB", (640, 480), "#f97316").save(image_path, format="JPEG", exif=exif)

        self.post_json("/api/scan", {"path": str(image_dir)})
        search = self.get_json("/api/search?q=meta-sample")
        file_id = search["results"][0]["id"]
        file_details = self.get_json(f"/api/file/{file_id}")

        self.assertEqual(file_details["width"], 640)
        self.assertEqual(file_details["height"], 480)
        if self.catalog_module.exifread:
            self.assertEqual(file_details["metadata"]["make"], "Canon")
            self.assertEqual(file_details["metadata"]["model"], "EOS R6")

    def test_batch_download_reports_missing_files_and_includes_manifest(self):
        real_file = self.tempdir_path / "real-download.jpg"
        Image.new("RGB", (200, 120), "#eab308").save(real_file, format="JPEG")

        with self.catalog_module.get_connection(str(self.db_path)) as conn:
            conn.execute(
                """
                INSERT INTO photos
                (id, path, filename, folder, size, mtime, date, year, month, ext, width, height, duration)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "download-real",
                    str(real_file),
                    real_file.name,
                    "tests",
                    real_file.stat().st_size,
                    real_file.stat().st_mtime,
                    "2026-04-09",
                    "2026",
                    "04",
                    "jpg",
                    200,
                    120,
                    0,
                ),
            )

        response = self.client.post("/api/batch/download", json={"file_ids": ["download-real", "f001"]})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers.get("X-Archive-Included"), "1")
        self.assertEqual(response.headers.get("X-Archive-Missing"), "1")

        batch_path = self.tempdir_path / "batch-download.zip"
        batch_path.write_bytes(response.data)
        with zipfile.ZipFile(batch_path) as zf:
            names = set(zf.namelist())
            self.assertIn("real-download.jpg", names)
            self.assertIn("missing-files.txt", names)
            manifest = zf.read("missing-files.txt").decode("utf-8")
            self.assertIn("Match_Action_001.jpg", manifest)

        activity = self.get_json("/api/activity?limit=20")["activity"]
        self.assertTrue(any(item["event_type"] == "download_batch" for item in activity))

    def test_thumbnail_route_generates_image_thumbnails_and_keeps_fallback(self):
        source_path = self.tempdir_path / "thumb-source.png"
        Image.new("RGB", (640, 360), "#0ea5e9").save(source_path, format="PNG")

        with self.catalog_module.get_connection(str(self.db_path)) as conn:
            conn.execute(
                """
                INSERT INTO photos
                (id, path, filename, folder, size, mtime, date, year, month, ext, width, height, duration)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "local-thumb",
                    str(source_path),
                    source_path.name,
                    "tests",
                    source_path.stat().st_size,
                    source_path.stat().st_mtime,
                    "2026-04-09",
                    "2026",
                    "04",
                    "png",
                    640,
                    360,
                    0,
                ),
            )

        thumb_response = self.client.get("/api/thumb/local-thumb")
        self.assertEqual(thumb_response.status_code, 200)
        self.assertEqual(thumb_response.mimetype, "image/jpeg")
        self.assertGreater(len(thumb_response.data), 0)
        thumb_response.close()

        fallback_response = self.client.get("/api/thumb/f001")
        self.assertEqual(fallback_response.status_code, 200)
        self.assertEqual(fallback_response.mimetype, "image/svg+xml")
        fallback_response.close()

    def test_thumbnail_route_generates_video_thumbnails(self):
        try:
            import imageio.v2 as imageio
        except ImportError:
            self.skipTest("imageio is not installed")

        try:
            import numpy as np
            frame = np.full((120, 160, 3), (10, 80, 180), dtype=np.uint8)
        except ImportError:
            frame = [[(10, 80, 180) for _ in range(160)] for _ in range(120)]

        source_path = self.tempdir_path / "thumb-video.mp4"
        with imageio.get_writer(str(source_path), fps=1, codec="libx264", quality=10) as writer:
            writer.append_data(frame)

        with self.catalog_module.get_connection(str(self.db_path)) as conn:
            conn.execute(
                """
                INSERT INTO photos
                (id, path, filename, folder, size, mtime, date, year, month, ext, width, height, duration)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "local-video-thumb",
                    str(source_path),
                    source_path.name,
                    "tests",
                    source_path.stat().st_size,
                    source_path.stat().st_mtime,
                    "2026-04-09",
                    "2026",
                    "04",
                    "mp4",
                    160,
                    120,
                    1,
                ),
            )

        thumb_response = self.client.get("/api/thumb/local-video-thumb")
        self.assertEqual(thumb_response.status_code, 200)
        self.assertEqual(thumb_response.mimetype, "image/jpeg")
        self.assertGreater(len(thumb_response.data), 0)
        thumb_response.close()

    def test_batch_remove_tags(self):
        # First add tags to files
        self.post_json("/api/batch/tags", {"file_ids": ["f001", "f002"], "tags": ["remove-me"]})
        # Verify tags added
        f001_tags = {t["tag"] for t in self.get_json("/api/file/f001/tags")["tags"]}
        self.assertIn("remove-me", f001_tags)
        
        # Now remove
        result = self.post_json("/api/batch/tags/remove", {"file_ids": ["f001", "f002"], "tags": ["remove-me"]})
        self.assertEqual(result["updated_files"], 2)
        self.assertEqual(result["tags_removed"], 2)
        
        # Verify gone
        f001_tags_after = {t["tag"] for t in self.get_json("/api/file/f001/tags")["tags"]}
        self.assertNotIn("remove-me", f001_tags_after)

    def test_fts_updates_after_batch_tag(self):
        # Add unique tag via batch
        self.post_json("/api/batch/tags", {"file_ids": ["f001"], "tags": ["unique-fts-test-tag"]})
        # Search should find the file
        results = self.get_json("/api/search?q=unique-fts-test-tag")
        self.assertGreater(results["total"], 0)
        self.assertTrue(any(r["id"] == "f001" for r in results["results"]))

    def test_tag_normalization_edge_cases(self):
        # Spaces become hyphens. We use a tag that doesn't already exist to avoid conflict
        r = self.post_json("/api/file/f001/tags", {"tag": "new space tag"}, expected_status=201)
        self.assertEqual(r["tag"], "new-space-tag")
        # Uppercase becomes lowercase
        r2 = self.post_json("/api/file/f003/tags", {"tag": "NEWUPPER"}, expected_status=201)
        self.assertEqual(r2["tag"], "newupper")
        # Special chars stripped (only alphanumeric+hyphen kept)
        r3 = self.post_json("/api/file/f003/tags", {"tag": "test@tag!"}, expected_status=201)
        self.assertEqual(r3["tag"], "test-tag")

    def test_no_destructive_delete_file_route(self):
        # Ensure DELETE /api/file/<id> does not exist (would delete from disk)
        response = self.client.delete("/api/file/f001")
        # Should 405 (method not allowed) or 404 (no such route), NOT 200/204
        self.assertIn(response.status_code, [404, 405])
        # File record should still exist
        f = self.get_json("/api/file/f001")
        self.assertEqual(f["id"], "f001")

    def test_batch_tag_remove_endpoint_requires_fields(self):
        r = self.client.post("/api/batch/tags/remove", json={})
        self.assertEqual(r.status_code, 400)
        r2 = self.client.post("/api/batch/tags/remove", json={"file_ids": ["f001"]})
        self.assertEqual(r2.status_code, 400)


if __name__ == "__main__":
    unittest.main()
