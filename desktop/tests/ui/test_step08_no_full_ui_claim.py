from pathlib import Path


def test_step08_does_not_ship_final_main_window_yet() -> None:
    package_root = Path(__file__).resolve().parents[2] / "src" / "metube_srt_desktop"
    assert not (package_root / "presentation" / "shell" / "main_window.py").exists()
