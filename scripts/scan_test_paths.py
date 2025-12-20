"""Scan tests for brittle path patterns and conftest import issues.

Usage: python scripts/scan_test_paths.py [--root tests/unittests] [--out reports/test_path_issues.json]
"""
from pathlib import Path
import re
import json
import argparse

DEFAULT_ROOT = Path("tests/unittests")
PATTERNS = [
    (r"\.\.\\\.\\data", "parent-relative data reference '..\\..\\data'"),
    (r"\.\\/tests\\/data", "relative './tests/data'"),
    (r"tests\.unittests\.conftest", "import from tests.unittests.conftest (prefer tests.conftest)")
]


def scan(root: Path):
    results = []
    for p in root.rglob("*.py"):
        try:
            txt = p.read_text(encoding='utf-8')
        except Exception:
            continue
        file_issues = []
        for pattern, desc in PATTERNS:
            if re.search(pattern, txt):
                file_issues.append({'pattern': pattern, 'description': desc})
        if "os.path.join(os.path.dirname(__file__)" in txt and "data" in txt:
            file_issues.append({'pattern': 'os.path.join(os.path.dirname(__file__), ... data)', 'description': 'dirname-based data path detected'})
        if "locate_data_dir(__file__)" not in txt and ("/data/" in txt or "\\\data\\" in txt):
            # heuristic: file references data but not the locate_data_dir helper
            file_issues.append({'pattern': 'data-reference-without-locate', 'description': 'File references tests/data but does not use locate_data_dir()'})
        if file_issues:
            results.append({'path': str(p), 'issues': file_issues})
    return results


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', default=str(DEFAULT_ROOT), help='Root tests dir to scan')
    parser.add_argument('--out', default='reports/test_path_issues.json', help='Output JSON path')
    args = parser.parse_args()

    root = Path(args.root)
    results = scan(root)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding='utf-8')
    print(f"Scanned {root}, found {len(results)} files with potential issues. Report written to {out}")

if __name__ == '__main__':
    main()
