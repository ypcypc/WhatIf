from runtime.game import GameEngine
import config

_engine: GameEngine | None = None


def get_engine() -> GameEngine:
    global _engine
    if _engine is None:
        if not config.OUTPUT_BASE.exists():
            raise RuntimeError(
                "WorldPkg 不存在，请先运行 Phase 1 数据提取: python extract.py ../data/novels/xxx.txt"
            )
        _engine = GameEngine(config.OUTPUT_BASE, config.SAVES_DIR)
    return _engine
