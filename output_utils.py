from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Union


def _fallback_path(path: Path, attempt: int = 0) -> Path:
    """Return a collision-resistant sibling path while keeping a readable name."""
    stamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    suffix = f"_{attempt}" if attempt else ""
    return path.with_name(f"{path.stem}_run_{stamp}{suffix}{path.suffix}")


def safe_write_bytes(path: Union[str, Path], data: bytes) -> Path:
    """Write bytes without letting a stale/locked output file abort a run.

    On Windows, image viewers / Explorer preview handlers can keep a previous
    PNG open.  Rewriting that exact filename can surface as OSError 22 or a
    sharing/permission error.  If the preferred path cannot be written, keep
    the run alive by writing a unique sibling file and return its real path.
    """
    path = Path(path).resolve()
    path.parent.mkdir(parents=True, exist_ok=True)

    try:
        path.write_bytes(data)
        return path
    except OSError as first_error:
        for attempt in range(100):
            alt = _fallback_path(path, attempt)
            try:
                # 'xb' prevents us from accidentally replacing another run.
                with alt.open('xb') as f:
                    f.write(data)
                print(
                    f"warning: could not overwrite '{path.name}' "
                    f"({first_error}). wrote '{alt.name}' instead."
                )
                return alt
            except FileExistsError:
                continue
            except OSError:
                continue
        raise first_error


def safe_write_text(path: Union[str, Path], text: str, encoding: str = 'utf8') -> Path:
    return safe_write_bytes(path, text.encode(encoding))
