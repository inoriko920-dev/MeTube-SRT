from pathlib import Path


def test_step09_materializes_native_main_window_after_step08_foundation() -> None:
    package_root = Path(__file__).resolve().parents[2] / "src" / "metube_srt_desktop"
    main_window = package_root / "presentation" / "shell" / "main_window.py"

    assert main_window.is_file()
