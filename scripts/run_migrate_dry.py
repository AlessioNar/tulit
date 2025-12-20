import json
from pathlib import Path
from scripts import migrate_tests

report = migrate_tests.scan_and_plan(Path('tests/unittests'), Path('tests/unit'))
out = Path('reports/test_migration_dryrun.json')
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps(report, indent=2), encoding='utf-8')
print(f"Planned {report['summary']['total_files']} files; flagged: {report['summary']['flagged_files']}; will change: {report['summary']['will_change']}")
print(f"Wrote report to {out}")
