"""migrate_tests.py

Safe, dry-run migration helper to move tests from `tests/unittests` -> `tests/unit`.
It will:
 - enumerate all .py files under the source test folder
 - compute the target path under the destination folder (mirror structure)
 - perform safe textual transforms (replace `tests.unittests` imports, ensure `locate_data_dir` import, replace a few brittle patterns)
 - detect in-function imports and script-like files (flagging them for manual review)
 - produce a JSON report and (when not dry-run) apply changes

Usage:
  python tulit/scripts/migrate_tests.py --src tests/unittests --dest tests/unit [--apply]

By default runs in dry-run mode and writes `reports/test_migration_dryrun.json`.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import re
from typing import List, Dict

ROOT = Path(__file__).resolve().parents[1]
REPORTS_DIR = ROOT / "reports"
REPORTS_DIR.mkdir(exist_ok=True)

RE_SCRIPT_LIKE = re.compile(r"if __name__\W+==\W+[\'\"]__main__[\'\"]|print\(|argparse")
RE_TESTS_UNITT = re.compile(r"\btests\.unittests\b")
RE_LOCATE_DATA = re.compile(r"locate_data_dir\(")
RE_IMPORT_LOCATE = re.compile(r"from\s+tests\.conftest\s+import\s+.*locate_data_dir")
RE_LOCAL_IMPORT = re.compile(r"^\s+(import\s+\w+|from\s+[\w\.]+\s+import\s+\w+)", re.M)

Transform = Dict[str, object]


def scan_and_plan(src: Path, dest: Path) -> Dict[str, object]:
    plans: List[Transform] = []
    src = src.resolve()
    dest = dest.resolve()
    for py in sorted(src.rglob("*.py")):
        rel = py.relative_to(src)
        target = dest / rel
        content = py.read_text(encoding="utf-8")
        transforms = []
        flags = []
        new_content = content

        # Replace references to tests.unittests -> tests
        if RE_TESTS_UNITT.search(new_content):
            transforms.append({
                "op": "replace_tests_unittests",
                "before": "tests.unittests",
                "after": "tests",
            })
            new_content = RE_TESTS_UNITT.sub("tests", new_content)

        # Ensure locate_data_dir import exists if used
        if RE_LOCATE_DATA.search(new_content) and not RE_IMPORT_LOCATE.search(new_content):
            transforms.append({
                "op": "add_import_locate_data_dir",
                "import": "from tests.conftest import locate_data_dir",
            })
            # add import at top after module docstring or at top
            parts = new_content.split("\n")
            insert_at = 0
            # skip shebang and module docstring
            if parts and parts[0].startswith("#!"):
                insert_at = 1
            # skip initial comments and blank lines
            while insert_at < len(parts) and parts[insert_at].strip() == "":
                insert_at += 1
            parts.insert(insert_at, "from tests.conftest import locate_data_dir")
            new_content = "\n".join(parts)

        # Detect in-function imports (simple heuristic: indented import lines)
        local_imports = []
        for m in RE_LOCAL_IMPORT.finditer(content):
            # If the import line has leading whitespace, it's likely in a block
            if m.group(0).startswith(" ") or m.group(0).startswith("\t"):
                local_imports.append(m.group(0).strip())
        if local_imports:
            flags.append({"in_function_imports": local_imports})

        # Detect script-like files
        if RE_SCRIPT_LIKE.search(content) or py.name.startswith("parse_"):
            flags.append({"script_like": True})

        # Detect os.path checks for existence (common OK) — we don't auto-change but flag
        if "os.path" in content and "locate_data_dir" not in content:
            flags.append({"os_path_used": True})

        plans.append({
            "src": str(py),
            "rel": str(rel),
            "dest": str(target),
            "transforms": transforms,
            "flags": flags,
        })

    report = {
        "src": str(src),
        "dest": str(dest),
        "plans": plans,
        "summary": {
            "total_files": len(plans),
            "flagged_files": sum(1 for p in plans if p["flags"]),
            "will_change": sum(1 for p in plans if p["transforms"]),
        },
    }
    return report


def apply_plan(report: Dict[str, object]) -> None:
    # Apply the planned transformations and move files
    for p in report["plans"]:
        src = Path(p["src"])
        dest = Path(p["dest"])
        content = src.read_text(encoding="utf-8")
        new_content = content
        for t in p["transforms"]:
            if t["op"] == "replace_tests_unittests":
                new_content = new_content.replace(t["before"], t["after"])
            if t["op"] == "add_import_locate_data_dir":
                if "from tests.conftest import locate_data_dir" not in new_content:
                    parts = new_content.split("\n")
                    insert_at = 0
                    if parts and parts[0].startswith("#!"):
                        insert_at = 1
                    while insert_at < len(parts) and parts[insert_at].strip() == "":
                        insert_at += 1
                    parts.insert(insert_at, t["import"])
                    new_content = "\n".join(parts)
        # write to destination
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(new_content, encoding="utf-8")
    # After all files are written, remove originals
    for p in report["plans"]:
        src = Path(p["src"])
        try:
            src.unlink()
        except Exception as e:
            print(f"Warning: failed to remove {src}: {e}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--src", default="tests/unittests")
    parser.add_argument("--dest", default="tests/unit")
    parser.add_argument("--apply", action="store_true", help="Apply changes (non-dry-run)")
    args = parser.parse_args()

    src = Path(args.src)
    dest = Path(args.dest)

    report = scan_and_plan(src, dest)
    out = REPORTS_DIR / ("test_migration_dryrun.json" if not args.apply else "test_migration_apply.json")
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(f"Planned {report['summary']['total_files']} files; flagged: {report['summary']['flagged_files']}; will change: {report['summary']['will_change']}")
    print(f"Report written to {out}")

    if args.apply:
        print("Applying changes...")
        apply_plan(report)
        print("Apply complete. Run tests/unit suite under Poetry to validate.")


if __name__ == "__main__":
    main()
