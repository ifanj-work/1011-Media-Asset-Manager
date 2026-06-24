import os
import sys
from pathlib import Path

# Add project root to path
sys.path.append(os.getcwd())

from catalog import get_catalog

def test_scan():
    db_path = "test_catalog.db"
    if os.path.exists(db_path):
        os.remove(db_path)
    
    catalog = get_catalog(db_path)
    
    # Create a test directory
    test_dir = Path("test_media")
    test_dir.mkdir(exist_ok=True)
    (test_dir / "photo1.jpg").write_text("fake image")
    (test_dir / "video1.mp4").write_text("fake video")
    (test_dir / "sub").mkdir(exist_ok=True)
    (test_dir / "sub" / "design.psd").write_text("fake psd")
    
    print(f"Scanning {test_dir.absolute()}...")
    results = catalog.scan_directory(str(test_dir.absolute()))
    print("Scan Results:", results)
    
    stats = catalog.get_stats()
    print("Stats after scan:", stats)
    
    # Cleanup
    import shutil
    shutil.rmtree(test_dir)
    os.remove(db_path)

if __name__ == "__main__":
    test_scan()
