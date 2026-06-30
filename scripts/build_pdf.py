#!/usr/bin/env python3
"""Gera Niosh-pt-BR.pdf a partir do Markdown unico, com layout de impressao."""
import sys, os, re, html, datetime
import markdown
from weasyprint import HTML
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import niosh_render

MD = sys.argv[1]          # /home/ubuntu/git/niosh/Niosh-pt-BR.md
PDF = sys.argv[2]         # /home/ubuntu/git/niosh/Niosh-pt-BR.pdf

raw = open(MD).read()
# remove o cabecalho de titulo que o build_html ja colocou (vamos recriar a capa)
raw = re.sub(r'^#\s.*?\n\n\*.*?\*\n\n---\n\n', '', raw, count=1, flags=re.S)
# tira os marcadores de pagina (comentarios)
raw = re.sub(r'<!--\s*p[áa]g\.\s*orig\.\s*\d+\s*-->', '', raw, flags=re.I)

mdconv = markdown.Markdown(extensions=['tables', 'fenced_code', 'sane_lists', 'attr_list'])
body = niosh_render.render_markdown(raw, mdconv)

TITLE = "NIOSH — Guia de bolso de riscos químicos"
SUB = "NIOSH Pocket Guide to Chemical Hazards — DHHS (NIOSH) Publicacao No 2005-149 — Traducao PT-BR"
gen = datetime.date(2026,6,29).strftime('%d/%m/%Y')

CSS = """
@page {
  size: A4; margin: 18mm 15mm 16mm 15mm;
  @bottom-center { content: counter(page) " / " counter(pages); font-size: 8pt; color:#888; }
  @top-right { content: "Guia NIOSH — PT-BR"; font-size: 7.5pt; color:#aaa; }
}
@page :first { @top-right{content:none} @bottom-center{content:none} }
html{font-size:9.5pt}
body{font-family:'DejaVu Sans',sans-serif;color:#1a1a1a;line-height:1.4}
h1{font-size:18pt;color:#0d2b45;border-bottom:2px solid #0d2b45;padding-bottom:3pt}
h2{font-size:13pt;color:#0d2b45;page-break-before:always;border-bottom:1px solid #ccc;padding-bottom:2pt;margin-top:0}
h3{font-size:10.5pt;color:#0a3d62;border-left:3px solid #0b5;padding-left:5pt;page-break-after:avoid;margin-top:10pt}
h3, h3 + p, table{page-break-inside:avoid}
p{margin:2pt 0}
table{border-collapse:collapse;width:100%;margin:4pt 0;font-size:8.2pt}
th,td{border:1px solid #bbb;padding:2pt 4pt;text-align:left;vertical-align:top}
th{background:#eef3f7}
code{background:#f0f0f0;padding:0 2pt;font-family:'DejaVu Sans Mono',monospace;font-size:8.5pt}
strong{color:#222}
hr{border:0;border-top:1px solid #ddd}
.cover{page-break-after:always;text-align:center;padding-top:60mm}
.cover h1{border:0;font-size:26pt}
.cover .s{font-size:12pt;color:#345;margin-top:8pt;max-width:140mm;margin-left:auto;margin-right:auto}
.cover .n{margin-top:30mm;font-size:8.5pt;color:#777;max-width:150mm;margin-left:auto;margin-right:auto;text-align:left;border:1px solid #ddd;padding:8pt;border-radius:4pt}
""" + niosh_render.ficha_css(screen=False)

cover = f"""<div class="cover">
  <h1>{html.escape(TITLE)}</h1>
  <div class="s">{html.escape(SUB)}</div>
  <div class="n"><b>Sobre esta traducao:</b> traducao automatica para portugues do Brasil.
  Medidas convertidas para o sistema metrico (&deg;F&rarr;&deg;C, mmHg&rarr;kPa, atm&rarr;kPa) com o valor original entre parenteses.
  Nomes quimicos em PT-BR com o original em ingles entre parenteses; formulas, CAS#, RTECS#, DOT# e codigos de respirador/medicao mantidos no original.
  Indices finais mantidos no original como chaves de busca.
  Documento original de dominio publico do NIOSH. Para uso critico, confirme na fonte oficial (cdc.gov/niosh/npg). Gerado em {gen}.</div>
</div>"""

doc = f"<!doctype html><html lang='pt-BR'><head><meta charset='utf-8'><style>{CSS}</style></head><body>{cover}{body}</body></html>"
HTML(string=doc).write_pdf(PDF)
print("PDF gerado:", PDF)
