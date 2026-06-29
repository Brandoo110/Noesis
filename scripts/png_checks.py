import hashlib
import zlib
from dataclasses import dataclass
from pathlib import Path

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


@dataclass(frozen=True)
class PngStats:
    width: int
    height: int
    unique_colors: int
    digest: str
    pixels: tuple[tuple[int, int, int], ...]


def png_stats(path: Path) -> PngStats:
    data = path.read_bytes()
    if not data.startswith(PNG_SIGNATURE):
        raise ValueError(f"{path} is not a PNG file")
    width, height, bit_depth, color_type, compressed = _read_png(data)
    if bit_depth != 8 or color_type not in (2, 6):
        raise ValueError(
            f"unsupported PNG format bit_depth={bit_depth} color_type={color_type}"
        )
    channels = 4 if color_type == 6 else 3
    row_size = width * channels
    raw = zlib.decompress(compressed)
    rows: list[bytes] = []
    offset = 0
    previous = bytes(row_size)
    for _ in range(height):
        filter_type = raw[offset]
        offset += 1
        row = bytearray(raw[offset : offset + row_size])
        offset += row_size
        _unfilter(row, previous, filter_type, channels)
        rows.append(bytes(row))
        previous = bytes(row)
    pixels: list[tuple[int, int, int]] = []
    for row in rows:
        for index in range(0, len(row), channels):
            pixels.append((row[index], row[index + 1], row[index + 2]))
    return PngStats(
        width=width,
        height=height,
        unique_colors=len(set(pixels)),
        digest=hashlib.sha256(data).hexdigest(),
        pixels=tuple(pixels),
    )


def is_nonblank(stats: PngStats, *, min_unique_colors: int) -> bool:
    return stats.width > 0 and stats.height > 0 and stats.unique_colors >= min_unique_colors


def diff_ratio(current: PngStats, baseline: PngStats, *, tolerance: int) -> float:
    if current.width != baseline.width or current.height != baseline.height:
        return 1.0
    changed = 0
    total = len(current.pixels)
    for left, right in zip(current.pixels, baseline.pixels):
        if any(abs(a - b) > tolerance for a, b in zip(left, right)):
            changed += 1
    return changed / total if total else 1.0


def _read_png(data: bytes) -> tuple[int, int, int, int, bytes]:
    offset = len(PNG_SIGNATURE)
    width = height = bit_depth = color_type = 0
    idat_parts: list[bytes] = []
    while offset < len(data):
        length = int.from_bytes(data[offset : offset + 4], "big")
        offset += 4
        chunk_type = data[offset : offset + 4]
        offset += 4
        chunk_data = data[offset : offset + length]
        offset += length + 4
        if chunk_type == b"IHDR":
            width = int.from_bytes(chunk_data[0:4], "big")
            height = int.from_bytes(chunk_data[4:8], "big")
            bit_depth = chunk_data[8]
            color_type = chunk_data[9]
        elif chunk_type == b"IDAT":
            idat_parts.append(chunk_data)
        elif chunk_type == b"IEND":
            break
    return width, height, bit_depth, color_type, b"".join(idat_parts)


def _unfilter(row: bytearray, previous: bytes, filter_type: int, bpp: int) -> None:
    for index, value in enumerate(row):
        left = row[index - bpp] if index >= bpp else 0
        up = previous[index]
        up_left = previous[index - bpp] if index >= bpp else 0
        if filter_type == 0:
            continue
        if filter_type == 1:
            row[index] = (value + left) & 0xFF
        elif filter_type == 2:
            row[index] = (value + up) & 0xFF
        elif filter_type == 3:
            row[index] = (value + ((left + up) // 2)) & 0xFF
        elif filter_type == 4:
            row[index] = (value + _paeth(left, up, up_left)) & 0xFF
        else:
            raise ValueError(f"unsupported PNG filter type {filter_type}")


def _paeth(left: int, up: int, up_left: int) -> int:
    estimate = left + up - up_left
    distance_left = abs(estimate - left)
    distance_up = abs(estimate - up)
    distance_up_left = abs(estimate - up_left)
    if distance_left <= distance_up and distance_left <= distance_up_left:
        return left
    if distance_up <= distance_up_left:
        return up
    return up_left
