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


def locate_tests_dir(start: Path | str | None = None) -> Path:
    p = Path(start) if start else Path(__file__).resolve()
    p = p.resolve()
    for parent in [p] + list(p.parents):
        candidate = parent / "tests"
        if candidate.exists() and candidate.is_dir():
            return candidate
    raise RuntimeError("Could not locate 'tests' directory starting from %s" % p)


@pytest.fixture(scope="session")
def data_root() -> Path:
    return locate_data_dir()


def pytest_sessionfinish(session, exitstatus):
    """Generate coverage badge after tests complete."""
    try:
        import json
        import xml.etree.ElementTree as ET
        
        coverage_file = Path("coverage.xml")
        if coverage_file.exists():
            tree = ET.parse(str(coverage_file))
            root = tree.getroot()
            pct = round(float(root.get("line-rate")) * 100, 1)
            badge = {
                "schemaVersion": 1,
                "label": "coverage",
                "message": f"{pct}%",
                "color": "brightgreen" if pct >= 90 else "yellow"
            }
            badges_dir = Path(".github/badges")
            badges_dir.mkdir(parents=True, exist_ok=True)
            with open(badges_dir / "coverage.json", "w") as f:
                json.dump(badge, f)
    except Exception as e:
        print(f"Warning: Could not generate coverage badge: {e}")