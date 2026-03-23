import zipfile
from pathlib import Path

from runtime.game import GameEngine
import config

_engine: GameEngine | None = None
_current_wpkg: Path | None = None


def list_worldpkgs() -> list[dict]:
    """List all .wpkg files in the output directory."""
    if not config.OUTPUT_DIR.exists():
        return []
    results = []
    for f in sorted(config.OUTPUT_DIR.iterdir()):
        if f.suffix == ".wpkg" and f.is_file():
            has_cover = False
            try:
                with zipfile.ZipFile(f, "r") as zf:
                    names = zf.namelist()
                    has_cover = any(n in names for n in ("cover.png", "cover.jpg", "cover.jpeg", "cover.webp"))
            except zipfile.BadZipFile:
                pass
            results.append({
                "name": f.stem,
                "filename": f.name,
                "size": f.stat().st_size,
                "hasCover": has_cover,
            })
    return results


def load_worldpkg(filename: str) -> None:
    """Load a specific .wpkg file, replacing the current engine."""
    global _engine, _current_wpkg
    wpkg_path = config.OUTPUT_DIR / filename
    if not wpkg_path.exists() or wpkg_path.suffix != ".wpkg":
        raise FileNotFoundError(f".wpkg 文件不存在: {filename}")
    _engine = GameEngine(wpkg_path, config.SAVES_DIR)
    _current_wpkg = wpkg_path


def get_current_wpkg_name() -> str | None:
    """Return the name of the currently loaded worldpkg."""
    return _current_wpkg.stem if _current_wpkg else None


def get_engine() -> GameEngine:
    global _engine
    if _engine is None:
        raise RuntimeError("未加载数据包，请先选择一个 .wpkg 文件")
    return _engine
