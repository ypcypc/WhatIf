import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from runtime.game import GameEngine
from runtime.cli import GameCLI
import config


def _resolve_wpkg_path(arg: str | None) -> Path:
    if arg is None:
        return config.OUTPUT_WPKG

    path = Path(arg)
    if path.exists():
        return path

    if not path.suffix:
        wpkg_path = config.OUTPUT_DIR / f"{arg}.wpkg"
        if wpkg_path.exists():
            return wpkg_path

    path = config.OUTPUT_DIR / arg
    if path.exists():
        return path

    return Path(arg)


def main():
    arg = sys.argv[1] if len(sys.argv) > 1 else None
    wpkg_path = _resolve_wpkg_path(arg)
    saves_dir = config.SAVES_DIR

    if not wpkg_path.exists():
        print(f"[错误] WorldPkg 不存在: {wpkg_path}")
        print()
        if config.OUTPUT_DIR.exists():
            available = [f.stem for f in config.OUTPUT_DIR.iterdir() if f.suffix == ".wpkg"]
            if available:
                print("可用的 WorldPkg:")
                for name in available:
                    print(f"  python play.py {name}")
        print()
        print("或运行数据提取:")
        print("  python extract.py ../data/novels/小说.txt")
        sys.exit(1)

    print(f"[加载] {wpkg_path.name}")

    try:
        engine = GameEngine(wpkg_path, saves_dir)

        cli = GameCLI(engine)
        cli.run()

    except Exception as e:
        print(f"\n[致命错误] {e}")
        raise


if __name__ == "__main__":
    main()
