"""Layouts of the Diário da República PDF, from lines built by hand (the PDF reader is mocked)."""
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest

from tulit.client.state.portugal import PortugalDREClient
from tulit.parser.exceptions import FileLoadError
from tulit.parser.pdf.layout import Line, _gutter, frames
from tulit.parser.pdf.portugal import DiarioRepublicaParser
from tulit.sources.pt import act_reference


def line(text, x0=60.0, x1=290.0, size=10.0, bold=False, page=0, column=0):
    return Line(page=page, text=text, x0=x0, x1=x1, top=0.0, size=size, bold=bold, width=300.0, column=column)


def body(*texts):
    """Full lines of body text, left-aligned."""
    return [line(text) for text in texts]


def parse(lines):
    with patch('tulit.parser.pdf.portugal.read_lines', return_value=(lines, [], 300.0)):
        return DiarioRepublicaParser().parse('act.pdf')


# A portaria in the layout used since 2021
PORTARIA = [
    line('1/5', 270, 290, 9), line('airatroP', 292, 298, 3.8), line('1.ª série', 250, 290, 9, True),
    line('N.º 1', 270, 290, 8), line('02-01-2025', 250, 290, 8),
    line('FINANÇAS', 60, 150, 11, True),
    line('Portaria n.º 1/2025/1, de 2 de janeiro', 60, 200, 11, True),
    line('Sumário: Primeira alteração à Portaria n.º 123/2014, de 19 de junho, que fixa as', 60, 290),
    line('condições mínimas do seguro.', 90, 200),
    line('A Portaria n.º 123/2014 fixou as condições mínimas do seguro de acidentes', 70, 290),
    *body('pessoais dos bombeiros, que importa agora atualizar com', 'novos limites de capital.'),
    line('Assim, manda o Governo, pelo Ministro das Finanças, o seguinte:', 70, 290),
    line('Artigo 1.º', 155, 185), line('Objeto', 160, 180, bold=True),
    line('A presente portaria altera a Portaria n.º 123/2014, de 19 de junho,', 70, 290),
    *body('que fixa as condições mínimas do seguro de acidentes pessoais.'),
    line('Artigo 2.º', 155, 185), line('Entrada em vigor', 140, 200, bold=True),
    line('A presente portaria entra em vigor no dia seguinte ao da sua publicação e', 72, 280),
    *body('produz efeitos a 1 de janeiro.'),
    line('O Ministro de Estado e das Finanças, Joaquim Sarmento, em 17 de dezembro de 2024.', 70, 290),
]


def test_current_layout_furniture_and_designation():
    parser = parse(PORTARIA)
    assert parser.preface == 'Portaria n.º 1/2025/1, de 2 de janeiro'
    assert parser.recitals[0]['text'] == ('Sumário: Primeira alteração à Portaria n.º 123/2014, de 19 de junho, '
                                          'que fixa as condições mínimas do seguro.')
    assert parser.formula.startswith('Assim, manda o Governo')


def test_article_heading_is_not_a_long_first_line():
    articles = parse(PORTARIA).articles
    assert [a['heading'] for a in articles] == ['Objeto', 'Entrada em vigor']
    assert articles[1]['children'][0]['text'].startswith('A presente portaria entra em vigor')


def test_minister_signature_closes_a_portaria():
    parser = parse(PORTARIA)
    assert 'Joaquim Sarmento' not in parser.articles[-1]['children'][-1]['text']
    assert 'Joaquim Sarmento' in parser.conclusions['signature']


def test_scanned_issue():
    with pytest.raises(FileLoadError, match='no text layer'):
        parse([])


# A constitutional revision in the 1997 layout
REVISION = [
    line('5130 DIÁRIO DA REPÚ', 60, 300), line('BLICA — I SÉRIE-A N.o 218 — 20-9-1997', 0, 240, column=1),
    line('Lei Constitucional n.o 1/97', 110, 240, bold=True), line('de 20 de Setembro', 140, 210, 8, True),
    line('A Assembleia da República decreta o seguinte:', 70, 290),
    line('I — Alterações à Constituição', 120, 250, bold=True),
    line('Artigo 1.o', 155, 185),
    line('No artigo 2.o a expressão «que tem» é substituída por ««visando».', 70, 290),
    line('Artigo 2.o', 155, 185),
    line('O artigo 3.o passa a ter a seguinte redacção:', 70, 290),
    line('«Artigo 3.o', 70, 120),
    line('A soberania reside no povo.»', 70, 200),
    line('II — Disposições finais', 120, 250, bold=True),
    line('Artigo 3.o', 155, 185),
    *body('A presente lei entra em vigor no dia seguinte.'),
    line('Aprovada em 3 de Setembro de 1997.', 90, 250),
    *body('O Presidente da República, JORGE SAMPAIO.'),
    line('CONSTITUIÇÃO DA REPÚBLICA PORTUGUESA', 95, 260, 9, True),
    line('Preâmbulo', 155, 200, bold=True),
    *body('A 25 de Abril de 1974, o Movimento das Forças Armadas.'),
    line('ANEXO I', 150, 200),
    *body('Texto do anexo da Constituição.'),
    line('Depósito legal n.o 8814/85', 130, 220, 8),
    line('AVISO', 160, 200, 13, True),
    *body('Por ordem superior se comunica.'),
    line('MINISTÉRIO DOS NEGÓCIOS ESTRANGEIROS', 70, 290, 12, True, page=1),
    line('Aviso n.o 260/97', 140, 220, bold=True, page=1),
    line('Por ordem superior se torna público.', 60, 290, page=1),
]


def test_revision_layout():
    parser = parse(REVISION)
    assert parser.preface == 'Lei Constitucional n.o 1/97 de 20 de Setembro'
    assert [(c['num'], c['heading']) for c in parser.chapters] == [
        ('I', 'Alterações à Constituição'), ('II', 'Disposições finais')]
    # the misprinted '««' does not swallow the next articles
    assert [a['eId'] for a in parser.articles] == ['art_1', 'art_2', 'art_3']
    assert parser.articles[1]['children'][0]['text'].endswith('A soberania reside no povo.»')


def test_text_republished_after_the_signatures():
    annexes = parse(REVISION).annexes
    assert [(a['num'], a['heading']) for a in annexes] == [('CONSTITUIÇÃO DA REPÚBLICA PORTUGUESA', 'Preâmbulo')]
    text = ' '.join(c['text'] for c in annexes[0]['children'])
    # its own annex stays inside; the back cover and the next act are left out
    assert 'Texto do anexo da Constituição.' in text
    assert 'Por ordem superior' not in text


def test_annex_then_map_is_one_annex():
    lines = PORTARIA[:-1] + [
        line('O Ministro, Joaquim Sarmento, em 17 de dezembro de 2024.', 70, 290),
        line('ANEXO', 160, 190), line('MAPA I', 155, 195, bold=True), *body('Consultor 770 830 900'),
    ]
    annexes = parse(lines).annexes
    assert [(a['num'], a['heading']) for a in annexes] == [('ANEXO', 'MAPA I')]


def test_frame_left_edge_with_many_quoted_lines():
    lines = [line('body', 45, 290) for _ in range(5)] + [line('quoted', 80, 290) for _ in range(8)]
    assert frames(lines)[(0, 0)][0] == 45


def test_gutter_off_the_middle():
    def chars(x0, x1):
        return [{'text': 'a', 'x0': x, 'x1': x + 4} for x in range(int(x0), int(x1), 4) for _ in range(5)]
    # columns at 60-298 and 315-554 on a 592 wide page: the middle (296) is inside the left column
    page = SimpleNamespace(chars=chars(60, 298) + chars(315, 554))
    split = _gutter(page, 592.0)
    assert split is not None and 298 <= split <= 315
    assert _gutter(SimpleNamespace(chars=chars(60, 554)), 592.0) is None


@pytest.mark.parametrize('identifier, expected', [
    ('Portaria n.º 1/2025/1, de 2 de janeiro', ('port', '1', '2025', '01', '02')),
    ('Lei Orgânica n.º 2/2006, de 17 de abril', ('leiorg', '2', '2006', '04', '17')),
    ('Lei Constitucional n.º 1/2005, de 12 de agosto', ('leiconst', '1', '2005', '08', '12')),
    ('Lei n.º 67/98, de 26 de outubro', ('lei', '67', '1998', '10', '26')),
])
def test_citations(identifier, expected):
    parts = act_reference(identifier)
    assert (parts['type'], parts['number'], parts['year'], parts['month'], parts['day']) == expected


def test_unknown_eli_is_not_a_content_type_error(tmp_path):
    response = Mock(status_code=200, url='https://diariodarepublica.pt/dr/error', content=b'<html/>',
                    headers={'Content-Type': 'text/html'})
    response.raise_for_status.return_value = None
    client = PortugalDREClient(download_dir=str(tmp_path))
    with patch.object(client.session, 'get', return_value=response):
        assert client.download('legal_act', act_type='dec-lei', number='400', year='1982', month='09', day='23',
                               region='p') is None
