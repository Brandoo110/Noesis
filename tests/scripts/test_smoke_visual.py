import importlib.util
import subprocess
import sys
import zlib
from pathlib import Path
from types import ModuleType
from typing import Sequence


def test_smoke_visual_parse_args_defaults() -> None:
    module = _load_visual_module()

    args = module.parse_args(())

    assert args.web == "http://127.0.0.1:5173"
    assert args.out_dir == Path("output/playwright/visual-smoke")
    assert args.baseline_dir == Path("web/visual-baselines")
    assert args.max_diff_ratio == 0.015
    assert args.session == "noesis-visual"


def test_smoke_visual_help_runs_as_script() -> None:
    root = Path(__file__).resolve().parents[2]

    result = subprocess.run(
        [sys.executable, "scripts/smoke_visual.py", "--help"],
        cwd=root,
        capture_output=True,
        check=False,
        text=True,
    )

    assert result.returncode == 0
    assert "--update-baseline" in result.stdout
    assert "--baseline-dir" in result.stdout


def test_png_stats_detects_nonblank_and_blank_images(tmp_path: Path) -> None:
    module = _load_visual_module()
    nonblank = tmp_path / "nonblank.png"
    blank = tmp_path / "blank.png"
    _write_png(nonblank, [(255, 0, 0), (0, 255, 0), (0, 0, 255)])
    _write_png(blank, [(255, 255, 255), (255, 255, 255), (255, 255, 255)])

    nonblank_stats = module.png_stats(nonblank)
    blank_stats = module.png_stats(blank)

    assert nonblank_stats.width == 3
    assert nonblank_stats.height == 1
    assert nonblank_stats.unique_colors == 3
    assert module.is_nonblank(nonblank_stats, min_unique_colors=2)
    assert not module.is_nonblank(blank_stats, min_unique_colors=2)


def test_visual_smoke_updates_and_compares_baseline(tmp_path: Path) -> None:
    module = _load_visual_module()
    runner = FakeRunner(tmp_path)
    args = module.VisualSmokeArgs(
        web="http://web.local",
        out_dir=tmp_path / "out",
        baseline_dir=tmp_path / "baseline",
        timeout=5.0,
        update_baseline=True,
        max_diff_ratio=0.015,
        pixel_tolerance=12,
        min_unique_colors=2,
        pwcli="/tmp/playwright_cli.sh",
        session="test-visual",
    )

    update_checks = module.run_visual_smoke(args, runner=runner)
    compare_checks = module.run_visual_smoke(
        module.VisualSmokeArgs(
            **{
                **args.__dict__,
                "update_baseline": False,
            }
        ),
        runner=runner,
    )

    assert all(check.status == "passed" for check in update_checks)
    assert all(check.status == "passed" for check in compare_checks)
    assert (tmp_path / "baseline" / "desktop.png").exists()
    assert (tmp_path / "baseline" / "mobile.png").exists()
    assert (tmp_path / "baseline" / "manifest.json").exists()
    assert any(_action(command) == "snapshot" for command in runner.commands)


def _load_visual_module() -> ModuleType:
    path = Path(__file__).resolve().parents[2] / "scripts" / "smoke_visual.py"
    spec = importlib.util.spec_from_file_location("smoke_visual", path)
    if spec is None or spec.loader is None:
        raise AssertionError("failed to load smoke_visual.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules["smoke_visual"] = module
    spec.loader.exec_module(module)
    return module


class FakeRunner:
    def __init__(self, tmp_path: Path) -> None:
        self.tmp_path = tmp_path
        self.commands: list[Sequence[str]] = []

    def __call__(self, command: Sequence[str], timeout: float) -> str:
        self.commands.append(command)
        action = _action(command)
        if action == "snapshot":
            return "Noesis\n组合 Brief\nBrief 运行健康\n持仓\n"
        if action == "screenshot":
            output = Path(command[command.index("--filename") + 1])
            _write_png(
                output,
                [(255, 255, 255), (0, 107, 112), (14, 31, 27), (245, 247, 245)],
            )
        return ""


def _action(command: Sequence[str]) -> str:
    return command[2] if len(command) > 2 and command[1].startswith("-s=") else command[1]


def _write_png(path: Path, pixels: list[tuple[int, int, int]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    width = len(pixels)
    height = 1
    raw = bytes([0]) + b"".join(bytes(pixel) for pixel in pixels)
    chunks = [
        _chunk(
            b"IHDR",
            width.to_bytes(4, "big")
            + height.to_bytes(4, "big")
            + bytes([8, 2, 0, 0, 0]),
        ),
        _chunk(b"IDAT", zlib.compress(raw)),
        _chunk(b"IEND", b""),
    ]
    path.write_bytes(b"\x89PNG\r\n\x1a\n" + b"".join(chunks))


def _chunk(kind: bytes, data: bytes) -> bytes:
    return (
        len(data).to_bytes(4, "big")
        + kind
        + data
        + zlib.crc32(kind + data).to_bytes(4, "big")
    )
