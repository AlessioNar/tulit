"""
Command-line interface for tulit.

Examples
--------
Download an EU act and write it as legalJSON::

    tulit get 32024R0903 -o 32024R0903.json
    tulit get 32016R0679 --format xhtml --language FRA

Parse a local file::

    tulit parse --format akn 32014L0092.akn -o 32014L0092.json

List the available parser formats::

    tulit formats
"""
import argparse
import json
import logging
import sys
from typing import Optional, Sequence

from tulit import __version__
from tulit.api import CELLAR_FORMATS, _validate, fetch
from tulit.parser.exceptions import ParserError
from tulit.parser.registry import get_parser, get_parser_registry


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog='tulit',
        description='Retrieve legislation from official sources and convert it to legalJSON.',
    )
    parser.add_argument('--version', action='version', version=f'tulit {__version__}')
    parser.add_argument('-v', '--verbose', action='store_true', help='log progress to stderr')
    commands = parser.add_subparsers(dest='command', required=True)

    get = commands.add_parser('get', help='download an EU act from Cellar as legalJSON')
    get.add_argument('celex', help='CELEX number, e.g. 32024R0903')
    get.add_argument('-f', '--format', choices=sorted(CELLAR_FORMATS), default='fmx4',
                     help='Cellar format to download and parse (default: fmx4)')
    get.add_argument('-l', '--language', default='ENG',
                     help='three-letter language code (default: ENG)')
    get.add_argument('--download-dir',
                     help='keep the downloaded source files in this directory')
    get.add_argument('--no-meta', action='store_true', help='do not attach Cellar metadata')
    _add_output_arguments(get)

    parse = commands.add_parser('parse', help='convert a local file or folder to legalJSON')
    parse.add_argument('path', help='file, or folder for multi-file Formex acts')
    parse.add_argument('-f', '--format', required=True,
                       help='parser format id or alias (see "tulit formats")')
    _add_output_arguments(parse)

    commands.add_parser('formats', help='list the parser formats and their aliases')
    return parser


def _add_output_arguments(command: argparse.ArgumentParser) -> None:
    command.add_argument('-o', '--output', help='write to this file instead of stdout')
    command.add_argument('--indent', type=int, default=2, help='JSON indentation (default: 2)')
    command.add_argument('--no-validate', action='store_true',
                         help='skip validation against the legalJSON schema')


def _parse_local(path: str, format_id: str) -> dict:
    registry = get_parser_registry()
    aliases = registry.list_aliases()
    if aliases.get(format_id, format_id) == 'akn':
        parser = get_parser(format_id, file_path=path)
    else:
        parser = get_parser(format_id)
    parser.parse(path)
    return parser.to_dict()


def _write(doc: dict, output: Optional[str], indent: int) -> None:
    text = json.dumps(doc, ensure_ascii=False, indent=indent)
    if output:
        with open(output, 'w', encoding='utf-8') as f:
            f.write(text + '\n')
    else:
        sys.stdout.write(text + '\n')


def _list_formats() -> None:
    registry = get_parser_registry()
    aliases: dict = {}
    for alias, format_id in registry.list_aliases().items():
        aliases.setdefault(format_id, []).append(alias)
    for format_id in registry.list_formats():
        extra = ', '.join(sorted(aliases.get(format_id, [])))
        sys.stdout.write(f"{format_id}{'  (' + extra + ')' if extra else ''}\n")


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    if args.verbose:
        logging.basicConfig(level=logging.INFO, format='%(levelname)s %(name)s %(message)s')

    try:
        if args.command == 'formats':
            _list_formats()
            return 0
        if args.command == 'get':
            doc = fetch(
                args.celex,
                format=args.format,
                language=args.language,
                download_dir=args.download_dir,
                metadata=not args.no_meta,
                validate=not args.no_validate,
            )
        else:
            doc = _parse_local(args.path, args.format)
            if not args.no_validate:
                _validate(doc)
        _write(doc, args.output, args.indent)
        return 0
    except (ParserError, ValueError, OSError) as e:
        sys.stderr.write(f"tulit: error: {e}\n")
        return 1


if __name__ == '__main__':
    sys.exit(main())
