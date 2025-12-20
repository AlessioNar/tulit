import importlib
import pathlib


class TestAssets:
    def test_xml_xsd_exists(self):
        pkg = importlib.import_module('tulit.parser')
        assets_dir = pathlib.Path(pkg.__file__).parent / 'xml' / 'assets'
        assert assets_dir.exists(), f"Assets directory missing: {assets_dir}"
        # check a representative file
        sample = assets_dir / 'xml.xsd'
        assert sample.exists(), f"Expected asset xml.xsd not found: {sample}"
