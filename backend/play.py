import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from runtime.game import GameEngine
from runtime.cli import GameCLI
import config


def _resolve_worldpkg_path(arg: str | None) -> Path:
    if arg is None:
        return config.OUTPUT_BASE

    path = Path(arg)
    if path.exists():
        return path

    path = config.OUTPUT_DIR / arg
    if path.exists():
        return path

    return Path(arg)


def main():
    arg = sys.argv[1] if len(sys.argv) > 1 else None
    worldpkg_path = _resolve_worldpkg_path(arg)
    saves_dir = config.SAVES_DIR

    if not worldpkg_path.exists():
        print(f"[错误] WorldPkg 不存在: {worldpkg_path}")
        print()
        if config.OUTPUT_DIR.exists():
            available = [d.name for d in config.OUTPUT_DIR.iterdir() if d.is_dir()]
            if available:
                print("可用的 WorldPkg:")
                for name in available:
                    print(f"  python play.py {name}")
        print()
        print("或运行 Phase 1 数据提取:")
        print("  python extract.py ../data/novels/小说.txt")
        sys.exit(1)

    required_files = [
        "metadata.json",
        "events/events.json",
        "lorebook/characters.json",
    ]
    for rel_path in required_files:
        if not (worldpkg_path / rel_path).exists():
            print(f"[错误] 缺少文件：{rel_path}")
            print("请确保 WorldPkg 数据完整")
            sys.exit(1)

    print(f"[加载] {worldpkg_path.name}")

    try:
        engine = GameEngine(worldpkg_path, saves_dir)

        cli = GameCLI(engine)
        cli.run()

    except Exception as e:
        print(f"\n[致命错误] {e}")
        raise


if __name__ == "__main__":
    main()
