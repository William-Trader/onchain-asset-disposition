#!/usr/bin/env python3
"""Typeset the manuscript in A4 Word format using python-docx."""
import argparse
import re
from pathlib import Path

from docx import Document
from docx.enum.style import WD_STYLE_TYPE
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.opc.constants import RELATIONSHIP_TYPE
from docx.shared import Cm, Pt, RGBColor

ROOT = Path(__file__).resolve().parent
SERIF = 'Noto Serif CJK SC'
SANS = 'Noto Sans CJK SC'
EN = 'Liberation Serif'
INK = '151E26'
DARK = '214957'


def attr(element, key, value):
    element.set(qn('w:' + key), str(value))


def child(element, name, **attributes):
    obj = OxmlElement('w:' + name)
    for key, value in attributes.items():
        attr(obj, key, value)
    element.append(obj)
    return obj


def font(style, size, latin=EN, cjk=SERIF, bold=False, color=INK):
    style.font.name = latin
    style.font.size = Pt(size)
    style.font.bold = bold
    style.font.color.rgb = RGBColor.from_string(color)
    prop = style.element.get_or_add_rPr()
    attr(prop.rFonts, 'eastAsia', cjk)


def para_style(doc, name, size=10.5, before=0, after=0, line=15, *,
               bold=False, align=WD_ALIGN_PARAGRAPH.LEFT, color=INK,
               cjk=SERIF, latin=EN, next_p=False, together=True):
    st = doc.styles[name] if name in doc.styles else doc.styles.add_style(name, WD_STYLE_TYPE.PARAGRAPH)
    font(st, size, latin=latin, cjk=cjk, bold=bold, color=color)
    fmt = st.paragraph_format
    fmt.space_before = Pt(before)
    fmt.space_after = Pt(after)
    fmt.line_spacing = Pt(line)
    fmt.alignment = align
    fmt.keep_with_next = next_p
    fmt.keep_together = together
    fmt.widow_control = True
    return st


def setup(doc):
    section = doc.sections[0]
    section.page_width, section.page_height = Cm(21), Cm(29.7)
    section.top_margin, section.bottom_margin = Cm(2.05), Cm(2)
    section.left_margin, section.right_margin = Cm(2.35), Cm(2.35)
    section.header_distance, section.footer_distance = Cm(.95), Cm(.95)
    left, center, justify = WD_ALIGN_PARAGRAPH.LEFT, WD_ALIGN_PARAGRAPH.CENTER, WD_ALIGN_PARAGRAPH.JUSTIFY
    st = para_style(doc, 'Normal', size=11, after=4.5, line=17, align=justify, together=False)
    st.paragraph_format.first_line_indent = Pt(22)
    para_style(doc, 'Title', size=21, before=10, after=6, line=30,
               align=center, cjk=SANS, bold=True, next_p=True)
    para_style(doc, 'Subtitle', size=13, after=8, line=21, align=center, cjk=SANS, color=DARK, next_p=True)
    para_style(doc, 'Paper Author', size=12, after=10, line=17, align=center, cjk=SANS, next_p=True)
    para_style(doc, 'Paper English Author', size=10.5, after=8, line=15, align=center, next_p=True)
    para_style(doc, 'Paper English', size=13, before=6, after=4, line=17, align=center, bold=True, next_p=True)
    para_style(doc, 'Paper Abstract', size=10.4, after=5, line=15.8, align=justify)
    para_style(doc, 'Paper Keywords', size=10.3, after=11, line=15.4, color=DARK)
    for lvl, size, before, after, line in [(1, 15, 13, 6, 22), (2, 12.4, 9, 5, 19)]:
        para_style(doc, 'Heading ' + str(lvl), size=size, before=before, after=after,
                   line=line, cjk=SANS, bold=True, color=DARK, next_p=True)
    para_style(doc, 'Paper Caption', size=10.1, before=8, after=5, line=15,
               align=center, cjk=SANS, bold=True, color=DARK, next_p=True)
    para_style(doc, 'Paper Figure Caption', size=10.1, before=5, after=4, line=15,
               align=center, cjk=SANS, bold=True, color=DARK, next_p=True)
    para_style(doc, 'Paper Note', size=9.0, before=3, after=6, line=13.6, color='47515A')
    para_style(doc, 'Paper Table', size=9.1, line=13.6, align=left)
    para_style(doc, 'Paper Table Header', size=9.1, line=13.6, cjk=SANS, bold=True, color=DARK)
    para_style(doc, 'Paper Identifier', size=9.0, before=0, after=3, line=14, latin='Liberation Mono', cjk=SANS)
    st = para_style(doc, 'Paper Reference', size=9.5, after=3, line=13.3)
    st.paragraph_format.left_indent = Pt(24)
    st.paragraph_format.first_line_indent = Pt(-24)
    para_style(doc, 'Paper Picture', before=7, after=0, line=15, align=center, next_p=True)
    doc.styles['Paper Picture'].paragraph_format.line_spacing = 1.0
    para_style(doc, 'Paper Availability', size=9.8, before=5, after=6, line=15, color=DARK)
    para_style(doc, 'Paper Footer', size=9, line=13, align=center, color='4B5960')
    footer = section.footer.paragraphs[0]
    footer.style = 'Paper Footer'
    field = child(footer._p, 'fldSimple', instr='PAGE')
    child(child(field, 'r'), 't').text = '1'
    return section


def text_runs(p, value):
    for idx, segment in enumerate(value.split('**')):
        run = p.add_run(segment)
        if idx % 2:
            run.bold = True


def labeled(doc, style, value):
    p = doc.add_paragraph(style=style)
    title, rest = value.split('｜', 1)
    p.add_run(title + '  ').bold = True
    text_runs(p, rest)


def add_link(p, display, url):
    link = child(p._p, 'hyperlink')
    link.set(qn('r:id'), p.part.relate_to(url, RELATIONSHIP_TYPE.HYPERLINK, is_external=True))
    link.set(qn('w:history'), '1')
    run = child(link, 'r')
    prop = child(run, 'rPr')
    child(prop, 'color', val=DARK)
    child(prop, 'u', val='single')
    child(run, 't').text = display


def reference(doc, text):
    paragraph = doc.add_paragraph(style='Paper Reference')
    match = re.search(r'https://\S+\.$', text)
    if not match:
        paragraph.add_run(text)
        return
    paragraph.add_run(text[:match.start()])
    url = match.group()[:-1]
    display = re.sub(r"([/_?=-])", lambda m: m.group() + "\u200b", url)
    add_link(paragraph, display, url)
    paragraph.add_run('.')


def add_table(doc, rows, width_cm, keep_note=False):
    table = doc.add_table(rows=len(rows), cols=len(rows[0]))
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False
    ratios_by_title = {
        '层级': (.18, .36, .46),
        '时间': (.22, .34, .44),
        '观察窗（UTC）': (.18, .16, .13, .13, .22, .18),
        '样本与 UTC 时间': (.24, .15, .16, .25, .20)
    }
    if rows[0][0] == '样本':
        ratios = (.11,.15,.21,.23,.15,.15) if len(rows[0])==6 else (.15,.32,.32,.21)
    else:
        ratios = ratios_by_title[rows[0][0]]
    for col, frac in zip(table.columns, ratios):
        col.width = Cm(width_cm * frac)
    pol = table._tbl.tblPr
    borders = child(pol, 'tblBorders')
    for name, size, color in [('top', 12, DARK), ('bottom', 9, DARK), ('insideH', 4, 'D4DCE0')]:
        child(borders, name, val='single', sz=size, color=color)
    margins = child(pol, 'tblCellMar')
    for edge, amount in [('top', 85), ('bottom', 85), ('start', 82), ('end', 82)]:
        child(margins, edge, w=amount, type='dxa')
    for i, (values, row) in enumerate(zip(rows, table.rows)):
        tr_props = row._tr.get_or_add_trPr()
        child(tr_props, 'cantSplit')
        if i == 0:
            child(tr_props, 'tblHeader', val='1')
        for j, (text, cell) in enumerate(zip(values, row.cells)):
            cell.width = Cm(width_cm * ratios[j])
            cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
            if i == 0:
                child(cell._tc.get_or_add_tcPr(), 'shd', fill='EDF3F4')
            paragraph = cell.paragraphs[0]
            paragraph.style = 'Paper Table Header' if i == 0 else 'Paper Table'
            paragraph.paragraph_format.keep_with_next = i < len(rows) - 1 or keep_note
            if j and rows[0][0] not in ('层级','时间'):
                paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
            paragraph.add_run(text)
    return table


def build(source, output):
    doc = Document()
    setup(doc)
    doc.core_properties.title = '数字资产交易服务受限下的用户资产处置能力'
    doc.core_properties.subject = 'Mt.Gox；Uniswap v3；链上复核'
    doc.core_properties.author = '周家乐'
    doc.core_properties.last_modified_by = ''
    lines = [line.strip() for line in source.read_text(encoding='utf-8').splitlines()]
    i = 0
    while i < len(lines):
        line = lines[i]
        if not line:
            i += 1
            continue
        if i == 0:
            doc.add_paragraph(line.removeprefix('# '), 'Title')
        elif i == 1:
            doc.add_paragraph(line.removeprefix('## '), 'Subtitle')
        elif line.startswith('# '):
            doc.add_heading(line[2:], level=1)
        elif line.startswith('## '):
            doc.add_heading(line[3:], level=2)
        elif line.startswith('|'):
            rows = []
            while i < len(lines) and lines[i].startswith('|'):
                values = [s.strip() for s in lines[i].strip('|').split('|')]
                if not all(re.fullmatch(r'[:\-]+', val) for val in values):
                    rows.append(values)
                i += 1
            following = next((part for part in lines[i:] if part),'')
            add_table(doc, rows, 16.3, keep_note=following.startswith('@note '))
            continue
        elif line.startswith('@'):
            tag, value = line[1:].split(' ', 1)
            if tag == 'figure':
                p = doc.add_paragraph(style='Paper Picture')
                frame = p.add_run().add_picture(str(source.parent / value), width=Cm(16.3))
                alt = {'mechanism.png':'两案控制点与操作路径。Mt.Gox 提现暂停。Uniswap Labs 官方网页受限，另有 0x 经 v3 池卖出并返回 ETH。','costs.png':'两个条形展示池费、其余成交偏离和本笔 Gas 的统一基准成本。'}
                frame._inline.docPr.set('descr', alt[value])
            elif tag in ('lead', 'key', 'availability'):
                labeled(doc, {'lead':'Paper Abstract','key':'Paper Keywords','availability':'Paper Availability'}[tag], value)
            else:
                style = {'caption': ('Paper Figure Caption' if value.startswith('图') else 'Paper Caption'),
                         'note':'Paper Note','mono':'Paper Identifier','en':'Paper English','author':'Paper Author','enauthor':'Paper English Author'}[tag]
                doc.add_paragraph(value, style)
        elif re.match(r'^\[\d+\]', line):
            reference(doc, line)
        else:
            paragraph = doc.add_paragraph()
            text_runs(paragraph, line)
        i += 1
    output.parent.mkdir(parents=True, exist_ok=True)
    doc.save(output)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=ROOT / 'paper.md')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    build(args.source, args.output)
