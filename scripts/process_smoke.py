import os
import socket
import subprocess
import sys
import time
from pathlib import Path
from typing import TextIO

import httpx


def free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def start_fixture_api(
    tmp_path: Path,
    port: int,
    log_file: TextIO,
) -> subprocess.Popen[str]:
    env = os.environ.copy()
    env["NOESIS_FIXTURE_DB_PATH"] = str(tmp_path / "noesis.db")
    env["NOESIS_FIXTURE_CHROMA_DIR"] = str(tmp_path / "chroma")
    return subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "scripts.fixture_api_app:app",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
            "--log-level",
            "warning",
        ],
        cwd=Path(__file__).resolve().parents[1],
        env=env,
        stdout=log_file,
        stderr=subprocess.STDOUT,
        text=True,
    )


def start_vite_web(
    api: str,
    port: int,
    log_file: TextIO,
) -> subprocess.Popen[str]:
    env = os.environ.copy()
    env["NOESIS_API_PROXY_TARGET"] = api
    return subprocess.Popen(
        [
            "npm",
            "--prefix",
            "web",
            "run",
            "dev",
            "--",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
            "--strictPort",
        ],
        cwd=Path(__file__).resolve().parents[1],
        env=env,
        stdout=log_file,
        stderr=subprocess.STDOUT,
        text=True,
    )


def wait_for_json(url: str, timeout: float) -> None:
    deadline = time.monotonic() + timeout
    last_error = ""
    while time.monotonic() < deadline:
        try:
            response = httpx.get(url, timeout=2.0)
            if response.status_code == 200:
                response.json()
                return
            last_error = f"status={response.status_code}"
        except Exception as exc:
            last_error = str(exc)
        time.sleep(0.25)
    raise RuntimeError(f"timed out waiting for {url}: {last_error}")


def wait_for_text(url: str, text: str, timeout: float) -> None:
    deadline = time.monotonic() + timeout
    last_error = ""
    while time.monotonic() < deadline:
        try:
            response = httpx.get(url, timeout=2.0)
            if response.status_code == 200 and text in response.text:
                return
            last_error = f"status={response.status_code}"
        except Exception as exc:
            last_error = str(exc)
        time.sleep(0.25)
    raise RuntimeError(f"timed out waiting for {url}: {last_error}")


def stop_process(proc: subprocess.Popen[str] | None) -> None:
    if proc is None or proc.poll() is not None:
        return
    proc.terminate()
    try:
        proc.wait(timeout=8.0)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait(timeout=3.0)
