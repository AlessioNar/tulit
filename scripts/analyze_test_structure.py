"""Analyze test structure against the following rules:
1. Tests should all be class-based (no top-level test functions).
2. One test file per python module (test_<module>.py in mirrored path under tests/unittests).
3. Test folder structure should mirror the library (e.g., tulit/parsers/xml -> tests/unittests/parsers/xml)

Outputs a JSON report to reports/test_structure_report.json and a human readable markdown to docs_wip/15-test-structure-analysis.md
"""
from pathlib import Path
import re
import json
import argparse

ROOT = Path('.').resolve()
PACKAGE_DIR = ROOT / 'tulit'
TESTS_DIR = ROOT / 'tests' / 'unittests'

PY_MODULES = list(PACKAGE_DIR.rglob('*.py'))
TEST_FILES = list(TESTS_DIR.rglob('test_*.py')) if TESTS_DIR.exists() else []

# Build a mapping from package-relative module path to module file
modules = {}
for p in PY_MODULES:
    if p.name == '__init__.py':
        continue
    rel = p.relative_to(PACKAGE_DIR)
    modules[str(rel)] = p

# Build a mapping of test files
tests = {}
for t in TEST_FILES:
    rel = t.relative_to(TESTS_DIR)
    tests[str(rel)] = t

# Helper: expected test path for a module
def expected_test_path_for_module(module_rel: str) -> str:
    # module_rel like 'parsers/xml/formex.py'
    parts = Path(module_rel).with_suffix('')
    # test file name
    filename = f"test_{parts.name}.py"
    test_path = parts.parent / filename
    return str(test_path)

# Analysis
missing_tests = []
extra_tests = []
multi_test_modules = []
non_class_based_tests = []
mirror_mismatches = []

# 1. Check modules for expected test files
expected_map = {}
for mod_rel in modules.keys():
    expected = expected_test_path_for_module(mod_rel)
    expected_map[mod_rel] = expected
    if expected not in tests:
        missing_tests.append({'module': mod_rel, 'expected_test': expected})

# 2. Check test files correspond to modules in same mirrored path
module_name_to_tests = {}
for test_rel, test_path in tests.items():
    # derive module path candidate: replace test_<name>.py with <name>.py
    p = Path(test_rel)
    if p.name.startswith('test_'):
        modname = p.name[len('test_'):]
        module_candidate = str(p.parent / (modname + '.py'))
        if module_candidate not in modules:
            # maybe it's organized differently or extra test file
            extra_tests.append({'test': test_rel, 'mapped_module_candidate': module_candidate})
        else:
            module_name_to_tests.setdefault(module_candidate, []).append(test_rel)

# 3. Check for modules with multiple test files (same module name in same package)
for mod, test_list in module_name_to_tests.items():
    if len(test_list) > 1:
        multi_test_modules.append({'module': mod, 'tests': test_list})

# 4. Check tests are class-based: no top-level def test_.* in file
func_test_re = re.compile(r'^def\s+test_\w+', re.MULTILINE)
class_test_re = re.compile(r'class\s+\w*Test\w*\s*\(|class\s+\w*\(unittest.TestCase\)', re.MULTILINE)
for test_rel, test_path in tests.items():
    txt = test_path.read_text(encoding='utf-8')
    top_level_funcs = func_test_re.findall(txt)
    has_class = bool(class_test_re.search(txt))
    if top_level_funcs and not has_class:
        non_class_based_tests.append({'test': test_rel, 'top_level_tests_count': len(top_level_funcs)})

# 5. Mirror structure check: for each package dir under tulit, check tests dir exists
for pkg_dir in PACKAGE_DIR.iterdir():
    if pkg_dir.is_dir():
        rel_pkg = pkg_dir.name
        test_pkg_dir = TESTS_DIR / rel_pkg
        if not test_pkg_dir.exists():
            mirror_mismatches.append({'package': rel_pkg, 'tests_dir_exists': False})

report = {
    'modules_total': len(modules),
    'test_files_total': len(tests),
    'missing_tests': missing_tests,
    'extra_tests': extra_tests,
    'multi_test_modules': multi_test_modules,
    'non_class_based_tests': non_class_based_tests,
    'mirror_mismatches': mirror_mismatches
}

out_json = ROOT / 'reports' / 'test_structure_report.json'
out_json.parent.mkdir(parents=True, exist_ok=True)
out_json.write_text(json.dumps(report, indent=2), encoding='utf-8')

# Also write a summary markdown
out_md = ROOT / 'docs_wip' / '15-test-structure-analysis.md'
out_md.parent.mkdir(parents=True, exist_ok=True)
with out_md.open('w', encoding='utf-8') as f:
    f.write('# Test Structure Analysis\n\n')
    f.write(f'- Modules found: {len(modules)}\n')
    f.write(f'- Test files found: {len(tests)}\n\n')
    f.write('## Missing tests (module -> expected test file)\n')
    if missing_tests:
        for m in missing_tests:
            f.write(f"- {m['module']} -> {m['expected_test']}\n")
    else:
        f.write('- None\n')
    f.write('\n')

    f.write('## Extra tests (test file not mapping to module)\n')
    if extra_tests:
        for e in extra_tests:
            f.write(f"- {e['test']} (candidate module: {e['mapped_module_candidate']})\n")
    else:
        f.write('- None\n')
    f.write('\n')

    f.write('## Modules with multiple tests files\n')
    if multi_test_modules:
        for mm in multi_test_modules:
            f.write(f"- {mm['module']}: {', '.join(mm['tests'])}\n")
    else:
        f.write('- None\n')
    f.write('\n')

    f.write('## Non-class-based tests (top-level test functions)\n')
    if non_class_based_tests:
        for n in non_class_based_tests:
            f.write(f"- {n['test']}: {n['top_level_tests_count']} top-level tests\n")
    else:
        f.write('- None\n')
    f.write('\n')

    f.write('## Packages missing test directories\n')
    if mirror_mismatches:
        for mm in mirror_mismatches:
            f.write(f"- {mm['package']} (tests dir missing)\n")
    else:
        f.write('- None\n')

print('Analysis complete. Reports written to:', out_json, out_md)
