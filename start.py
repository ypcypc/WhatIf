import os
import platform
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Sequence
from urllib.error import URLError
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parent
BACKEND_PORT = 8000
FRONTEND_PORT = 3030
IS_WINDOWS = platform.system() == "Windows"
BACKEND_HEALTH_URL = f"http://127.0.0.1:{BACKEND_PORT}/api/health"
FRONTEND_URL = f"http://localhost:{FRONTEND_PORT}"


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


def find_pnpm_command() -> list[str]:
    """定位 pnpm 命令，兼容全局安装和 Corepack 托管的 pnpm。"""
    candidates = ["pnpm.cmd", "pnpm.exe", "pnpm"] if IS_WINDOWS else ["pnpm"]
    for candidate in candidates:
        resolved = shutil.which(candidate)
        if resolved:
            return [resolved]

    corepack_candidates = ["corepack.cmd", "corepack.exe", "corepack"] if IS_WINDOWS else ["corepack"]
    for candidate in corepack_candidates:
        resolved = shutil.which(candidate)
        if resolved:
            return [resolved, "pnpm"]

    raise FileNotFoundError("未找到 pnpm 或 corepack，请先安装 pnpm，或启用 Node.js 自带的 Corepack。")


def describe_command(command: Sequence[str]) -> str:
    return " ".join(command)


def find_pnpm() -> str:
    """Backward-compatible string form of the resolved pnpm command."""
    return describe_command(find_pnpm_command())


def start_backend(python: str) -> subprocess.Popen:
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    return subprocess.Popen(
        [python, "-m", "uvicorn", "api.app:app", "--reload", "--port", str(BACKEND_PORT)],
        cwd=ROOT / "backend",
        env=env,
    )


def start_frontend(pnpm_command: Sequence[str]) -> subprocess.Popen:
    return subprocess.Popen(
        [*pnpm_command, "dev", "--port", str(FRONTEND_PORT)],
        cwd=ROOT / "frontend",
    )


def wait_for_http(url: str, timeout_s: float, *, label: str) -> None:
    deadline = time.time() + timeout_s
    last_error: str | None = None
    while time.time() < deadline:
        try:
            with urlopen(url, timeout=2) as response:
                if 200 <= response.status < 500:
                    return
        except URLError as exc:
            last_error = str(exc)
        except Exception as exc:  # pragma: no cover - defensive
            last_error = str(exc)
        time.sleep(0.5)
    raise RuntimeError(f"{label} 启动超时：{last_error or '未收到响应'}")


def stop_process(proc: subprocess.Popen) -> None:
    if proc.poll() is not None:
        return
    try:
        if IS_WINDOWS:
            subprocess.run(
                ["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                capture_output=True,
                check=False,
            )
        else:
            proc.terminate()
            proc.wait(timeout=5)
    except Exception:
        try:
            proc.kill()
        except Exception:
            pass


# ── 主流程 ───────────────────────────────────────────────────


def main() -> None:
    print("=== WhatIf 启动脚本 ===\n")

    # 1) 清理旧进程
    print("[1/3] 清理旧进程...")
    cleanup_port(BACKEND_PORT)
    cleanup_port(FRONTEND_PORT)
    time.sleep(1)

    backend: subprocess.Popen | None = None
    frontend: subprocess.Popen | None = None

    # 2) 启动服务
    python = find_python()
    pnpm_command = find_pnpm_command()
    print(f"\n[2/3] 启动后端 (Python: {python})...")
    backend = start_backend(python)
    wait_for_http(BACKEND_HEALTH_URL, timeout_s=30, label="后端")
    print(f"  后端已就绪: {BACKEND_HEALTH_URL}")

    print(f"\n[3/3] 启动前端 (pnpm: {describe_command(pnpm_command)})...")
    frontend = start_frontend(pnpm_command)
    wait_for_http(FRONTEND_URL, timeout_s=30, label="前端")
    print(f"  前端已就绪: {FRONTEND_URL}")

    print(f"\n后端: {BACKEND_HEALTH_URL}")
    print(f"前端: {FRONTEND_URL}")
    print("\n请在浏览器中打开前端地址。按 Ctrl+C 停止所有服务。\n")

    try:
        while True:
            backend_code = backend.poll()
            frontend_code = frontend.poll()
            if backend_code is not None:
                raise RuntimeError(f"后端已退出，退出码 {backend_code}")
            if frontend_code is not None:
                raise RuntimeError(f"前端已退出，退出码 {frontend_code}")
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n正在停止服务...")
    except RuntimeError as exc:
        print(f"\n服务异常退出：{exc}")
    finally:
        for proc in (frontend, backend):
            if proc is not None:
                stop_process(proc)
        print("已停止。")


if __name__ == "__main__":
    main()
