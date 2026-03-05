"""WhatIf 启动脚本 — 清理旧进程 + 启动后端 API 和前端开发服务器

跨平台（Windows / Linux / macOS），用法:
    python start.py
"""

import os
import platform
import signal
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BACKEND_PORT = 8000
FRONTEND_PORT = 5173
IS_WINDOWS = platform.system() == "Windows"


# ── 清理旧进程 ──────────────────────────────────────────────


def _kill_pids(pids: set[int]) -> None:
    for pid in pids:
        try:
            if IS_WINDOWS:
                subprocess.run(
                    ["taskkill", "/F", "/PID", str(pid)],
                    capture_output=True,
                )
            else:
                os.kill(pid, signal.SIGKILL)
        except (ProcessLookupError, PermissionError, OSError):
            pass


def _pids_on_port_windows(port: int) -> set[int]:
    """netstat 解析 Windows 上占用指定端口的 PID"""
    try:
        out = subprocess.check_output(
            ["netstat", "-ano"], text=True, stderr=subprocess.DEVNULL,
        )
    except Exception:
        return set()

    pids: set[int] = set()
    target = f":{port}"
    for line in out.splitlines():
        parts = line.split()
        if len(parts) >= 5 and target in parts[1]:
            try:
                pids.add(int(parts[-1]))
            except ValueError:
                pass
    pids.discard(0)
    return pids


def _pids_on_port_unix(port: int) -> set[int]:
    """lsof 解析 Unix 上占用指定端口的 PID"""
    try:
        out = subprocess.check_output(
            ["lsof", "-ti", f":{port}"], text=True, stderr=subprocess.DEVNULL,
        )
    except Exception:
        return set()
    pids: set[int] = set()
    for token in out.split():
        try:
            pids.add(int(token))
        except ValueError:
            pass
    return pids


def cleanup_port(port: int) -> None:
    pids = _pids_on_port_windows(port) if IS_WINDOWS else _pids_on_port_unix(port)
    if pids:
        print(f"  端口 {port}: 杀掉进程 {pids}")
        _kill_pids(pids)
    else:
        print(f"  端口 {port}: 无残留进程")


# ── 启动服务 ─────────────────────────────────────────────────


def find_python() -> str:
    """定位 .venv 中的 Python"""
    if IS_WINDOWS:
        venv_python = ROOT / ".venv" / "Scripts" / "python.exe"
    else:
        venv_python = ROOT / ".venv" / "bin" / "python"
    if venv_python.exists():
        return str(venv_python)
    return sys.executable


def start_backend(python: str) -> subprocess.Popen:
    return subprocess.Popen(
        [python, "-m", "uvicorn", "api.app:app", "--reload", "--port", str(BACKEND_PORT)],
        cwd=ROOT / "backend",
    )


def start_frontend() -> subprocess.Popen:
    cmd = ["pnpm", "dev", "--port", str(FRONTEND_PORT)]
    # Windows 下 pnpm 是 .cmd，需要 shell=True
    return subprocess.Popen(
        cmd,
        cwd=ROOT / "frontend",
        shell=IS_WINDOWS,
    )


# ── 主流程 ───────────────────────────────────────────────────


def main() -> None:
    print("=== WhatIf 启动脚本 ===\n")

    # 1) 清理旧进程
    print("[1/3] 清理旧进程...")
    cleanup_port(BACKEND_PORT)
    cleanup_port(FRONTEND_PORT)
    time.sleep(1)

    # 2) 启动服务
    python = find_python()
    print(f"\n[2/3] 启动后端 (Python: {python})...")
    backend = start_backend(python)

    print(f"[3/3] 启动前端...")
    frontend = start_frontend()

    print(f"\n后端: http://localhost:{BACKEND_PORT}")
    print(f"前端: http://localhost:{FRONTEND_PORT}")
    print("\n请在浏览器中打开前端地址。按 Ctrl+C 停止所有服务。\n")

    # 3) 等待 Ctrl+C，然后优雅退出
    try:
        backend.wait()
    except KeyboardInterrupt:
        print("\n正在停止服务...")
    finally:
        for proc in (backend, frontend):
            try:
                proc.terminate()
                proc.wait(timeout=5)
            except Exception:
                proc.kill()
        print("已停止。")


if __name__ == "__main__":
    main()
