import json
from pathlib import Path


def test_ui_manifest_has_twenty_unique_ids() -> None:
    desktop_root = Path(__file__).resolve().parents[2]
    repo_root = desktop_root.parent
    manifest_path = repo_root / "docs" / "desktop" / "UI_REFERENCES" / "manifest.json"
    data = json.loads(manifest_path.read_text(encoding="utf-8"))

    items = data["items"]
    ids = [item["id"] for item in items]

    assert data["expected_count"] == 20
    assert len(items) == 20
    assert len(set(ids)) == 20
    assert ids == [f"UI_{index:02d}" for index in range(1, 21)]
    assert all(item["status"] for item in items)
