from pathlib import Path


def test_desktop_project_isolated_from_legacy_web_source() -> None:
    desktop_root = Path(__file__).resolve().parents[2]

    assert (desktop_root / "src" / "metube_srt_desktop").is_dir()
    assert not (desktop_root / "app").exists()
    assert not (desktop_root / "ui").exists()
    assert not (desktop_root / "src" / "metube_srt_desktop" / "web").exists()
