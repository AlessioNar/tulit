import importlib

import pytest

from tulit.parser.exceptions import ParserError
from tulit.parser.registry import (
    ParserRegistry, get_parser, get_parser_registry, register_parser
)


class TestRegistryModule:
    def test_import(self):
        importlib.import_module('tulit.parser.registry')


class TestParserRegistry:
    def test_register_and_create(self):
        registry = ParserRegistry()
        registry.register('dummy', dict, aliases=['dmy'])
        assert isinstance(registry.create('dmy'), dict)
        assert registry.list_formats() == ['dummy']

    def test_duplicate_alias_rejected(self):
        registry = ParserRegistry()
        registry.register('one', dict, aliases=['x'])
        with pytest.raises(ParserError):
            registry.register('two', list, aliases=['x'])

    def test_unknown_format(self):
        with pytest.raises(ParserError):
            ParserRegistry().create('missing')


class TestGlobalRegistry:
    @pytest.mark.parametrize('format_id, class_name', [
        ('formex', 'Formex4Parser'),
        ('fmx4', 'Formex4Parser'),
        ('akomantoso', 'AkomaNtosoParser'),
        ('akn4eu', 'AKN4EUParser'),
        ('legaldocml-de', 'GermanLegalDocMLParser'),
        ('akn-lu', 'LuxembourgAKNParser'),
        ('xhtml', 'CellarHTMLParser'),
        ('html', 'CellarStandardHTMLParser'),
        ('proposal', 'ProposalHTMLParser'),
        ('boe', 'BOEXMLParser'),
        ('veneto', 'VenetoHTMLParser'),
    ])
    def test_builtin_parsers_registered(self, format_id, class_name):
        assert type(get_parser(format_id)).__name__ == class_name

    def test_akn_factory_detects_variant(self, data_root):
        akn_file = data_root / 'sources' / 'eu' / 'eurlex' / 'akn' / '32014L0092.akn'
        parser = get_parser('akn', file_path=str(akn_file))
        assert type(parser).__name__ == 'AkomaNtosoParser'

    def test_register_parser_with_class_and_factory(self):
        register_parser('test-class-format', parser_class=dict)
        register_parser('test-factory-format', factory=lambda: [])
        assert get_parser('test-class-format') == {}
        assert get_parser('test-factory-format') == []

    def test_register_parser_requires_exactly_one_source(self):
        with pytest.raises(ParserError):
            register_parser('test-invalid-format')
        with pytest.raises(ParserError):
            register_parser('test-invalid-format', parser_class=dict, factory=dict)

    def test_global_registry_is_shared(self):
        assert get_parser_registry() is get_parser_registry()
