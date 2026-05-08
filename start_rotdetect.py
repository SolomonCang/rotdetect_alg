#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import signal
import subprocess
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parent
BACKEND = ROOT / "backend"
FRONTEND = ROOT / "frontend"


def main() -> int:
    parser = argparse.ArgumentParser(description="Start the RotDetect backend and frontend dev servers.")
    parser.add_argument("--backend-port", type=int, default=8000, help="FastAPI backend port.")
    parser.add_argument("--frontend-port", type=int, default=5173, help="Vite frontend port.")
    parser.add_argument("--host", default="0.0.0.0", help="Frontend host passed to Vite.")
    args = parser.parse_args()

    ensure_project_layout()

    backend_cmd = [
        "uv",
        "run",
        "uvicorn",
        "rotdetect.api:app",
        "--reload",
        "--port",
        str(args.backend_port),
    ]
    frontend_cmd = [
        "npm",
        "run",
        "dev",
        "--",
        "--host",
        args.host,
        "--port",
        str(args.frontend_port),
    ]

    processes: list[subprocess.Popen[bytes]] = []

    stopping = False

    def stop_processes(*_: object) -> None:
        nonlocal stopping
        if stopping:
            return
        stopping = True
        print("\nStopping RotDetect services...")
        for process in processes:
            if process.poll() is None:
                process.send_signal(signal.SIGINT)
        for process in processes:
            try:
                process.wait(timeout=8)
            except subprocess.TimeoutExpired:
                process.terminate()

    signal.signal(signal.SIGINT, stop_processes)
    signal.signal(signal.SIGTERM, stop_processes)

    print("Starting RotDetect...")
    print(f"Backend:  http://localhost:{args.backend_port}/docs")
    print(f"Frontend: http://localhost:{args.frontend_port}")
    print("Press Ctrl+C to stop both services.\n")

    try:
        processes.append(start_process("backend", backend_cmd, BACKEND))
        processes.append(start_process("frontend", frontend_cmd, FRONTEND))

        while True:
            for process in processes:
                if process.poll() is not None:
                    stop_processes()
                    return process.returncode or 1
            time.sleep(0.5)
    finally:
        stop_processes()


def ensure_project_layout() -> None:
    missing = [str(path.relative_to(ROOT)) for path in (BACKEND, FRONTEND) if not path.exists()]
    if missing:
        joined = ", ".join(missing)
        raise SystemExit(f"Missing required project directories: {joined}")


def start_process(name: str, command: list[str], cwd: Path) -> subprocess.Popen[bytes]:
    env = os.environ.copy()
    print(f"[{name}] {' '.join(command)}")
    try:
        return subprocess.Popen(command, cwd=cwd, env=env)
    except FileNotFoundError as exc:
        binary = command[0]
        raise SystemExit(f"Could not find '{binary}'. Install it before running this script.") from exc


if __name__ == "__main__":
    raise SystemExit(main())
