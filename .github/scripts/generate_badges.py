"""Generate badge JSON for coverage from coverage.xml."""
import json
import xml.etree.ElementTree as ET
from pathlib import Path

cov_file = Path("coverage.xml")
badges_dir = Path(".github/badges")
badges_dir.mkdir(parents=True, exist_ok=True)

coverage_msg = "unknown"
coverage_color = "yellow"

if cov_file.exists():
    try:
        tree = ET.parse(str(cov_file))
        root = tree.getroot()
        # Get line-rate from root
        lr = root.get("line-rate")
        if lr:
            pct = round(float(lr) * 100, 1)
            coverage_msg = f"{pct}%"
            coverage_color = "brightgreen" if pct >= 90 else "yellow"
    except Exception as e:
        print(f"Error parsing coverage.xml: {e}")

badge = {
    "schemaVersion": 1,
    "label": "coverage",
    "message": coverage_msg,
    "color": coverage_color
}

with open(badges_dir / "coverage.json", "w") as f:
    json.dump(badge, f)

print(f"Generated coverage badge: {coverage_msg}")
