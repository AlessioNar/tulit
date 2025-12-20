import importlib
import pathlib


class TestLegaljsonSchema:
    def test_schema_file_exists(self):
        pkg = importlib.import_module('tulit.parsers')
        base = pathlib.Path(pkg.__file__).parent / 'legaljson_schema.json'
        assert base.exists(), f"Schema file not found: {base}"
