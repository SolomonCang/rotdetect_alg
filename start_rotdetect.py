#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BACKEND = ROOT / "backend"
FRONTEND = ROOT / "frontend"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Start the RotDetect backend and frontend dev servers.")
    parser.add_argument("--backend-port",
                        type=int,
                        default=8000,
                        help="FastAPI backend port.")
    parser.add_argument("--frontend-port",
                        type=int,
                        default=5173,
                        help="Vite frontend port.")
    parser.add_argument("--host",
                        default="0.0.0.0",
                        help="Frontend host passed to Vite.")
    args = parser.parse_args()

    ensure_project_layout()
    ensure_ports_available(args.backend_port, args.frontend_port)

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
    shutdown_requested = False

    def stop_processes(*_: object) -> None:
        nonlocal stopping, shutdown_requested
        shutdown_requested = True
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
            if shutdown_requested:
                return 0
            for process in processes:
                if process.poll() is not None:
                    stop_processes()
                    if shutdown_requested:
                        return 0
                    return process.returncode or 1
            time.sleep(0.5)
    finally:
        stop_processes()


def is_port_in_use(port: int, host: str = "127.0.0.1") -> bool:
    """Check if a port has an active listener by attempting a connection."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(1)
        try:
            sock.connect((host, port))
            return True  # connection succeeded → something is listening
        except (ConnectionRefusedError, OSError):
            return False  # connection refused → port is free


def get_process_using_port(port: int) -> int | None:
    """Get PID of process using the given port on macOS/Linux."""
    try:
        result = subprocess.run(
            ["lsof", "-i", f":{port}", "-t"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.stdout.strip():
            return int(result.stdout.strip().split()[0])
    except (subprocess.TimeoutExpired, ValueError, IndexError,
            FileNotFoundError):
        pass
    return None


def free_port(port: int, force: bool = False) -> bool:
    """
    Try to free a port by killing the process using it.
    
    Args:
        port: Port number to free
        force: If True, use SIGKILL instead of SIGTERM
        
    Returns:
        True if port is now free, False if failed
    """
    if not is_port_in_use(port):
        return True

    pid = get_process_using_port(port)
    if pid is None:
        print(
            f"⚠️  Port {port} is in use but could not identify process. Try: lsof -i :{port}"
        )
        return False

    signal_type = signal.SIGKILL if force else signal.SIGTERM
    signal_name = "SIGKILL" if force else "SIGTERM"

    try:
        print(f"🔓 Freeing port {port} (PID {pid}) with {signal_name}...")
        os.kill(pid, signal_type)
        time.sleep(0.5)

        if not is_port_in_use(port):
            print(f"✅ Port {port} freed successfully")
            return True
        elif not force:
            print(
                f"⚠️  Process {pid} still holding port {port}, trying SIGKILL..."
            )
            return free_port(port, force=True)
        else:
            print(f"❌ Failed to free port {port}")
            return False
    except ProcessLookupError:
        # Process already terminated
        time.sleep(0.5)
        if not is_port_in_use(port):
            print(f"✅ Port {port} freed successfully")
            return True
        return False
    except PermissionError:
        print(f"❌ Permission denied: cannot kill process {pid} on port {port}")
        return False


def ensure_ports_available(backend_port: int, frontend_port: int) -> None:
    """Check and free ports if needed."""
    print("\n🔍 Checking port availability...\n")

    ports_to_check = [
        ("Backend", backend_port),
        ("Frontend", frontend_port),
    ]

    for service_name, port in ports_to_check:
        max_retries = 3
        for attempt in range(max_retries):
            if not is_port_in_use(port):
                print(f"✅ {service_name} port {port} is available")
                break

            print(
                f"⚠️  {service_name} port {port} is in use (attempt {attempt+1}/{max_retries})"
            )

            if free_port(port):
                print()
                break
            elif attempt < max_retries - 1:
                # Wait and retry
                print(f"⏳ Waiting 2 seconds before retry...")
                time.sleep(2)
                print()
            else:
                print(
                    f"❌ Could not free port {port}. Please free it manually or use a different port.\n"
                )
                raise SystemExit(1)
    print()


def ensure_project_layout() -> None:
    missing = [
        str(path.relative_to(ROOT)) for path in (BACKEND, FRONTEND)
        if not path.exists()
    ]
    if missing:
        joined = ", ".join(missing)
        raise SystemExit(f"Missing required project directories: {joined}")


def start_process(name: str, command: list[str],
                  cwd: Path) -> subprocess.Popen[bytes]:
    env = os.environ.copy()
    print(f"[{name}] {' '.join(command)}")
    try:
        return subprocess.Popen(command, cwd=cwd, env=env,
                                stdin=subprocess.DEVNULL)
    except FileNotFoundError as exc:
        binary = command[0]
        raise SystemExit(
            f"Could not find '{binary}'. Install it before running this script."
        ) from exc


if __name__ == "__main__":
    raise SystemExit(main())
