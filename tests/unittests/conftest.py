from pathlib import Path
import pytest


def locate_data_dir(start: Path | str | None = None) -> Path:
    p = Path(start) if start else Path(__file__).resolve()
    p = p.resolve()
    for parent in [p] + list(p.parents):
        candidate = parent / "data"
        if candidate.exists() and candidate.is_dir():
            return candidate
    raise RuntimeError("Could not locate 'data' directory starting from %s" % p)


@pytest.fixture(scope="session")
def data_root() -> Path:
    return locate_data_dir()
