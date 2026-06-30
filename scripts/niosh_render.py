#!/usr/bin/env python3
"""Renderizador compartilhado: reconstroi as fichas quimicas no layout de grade do NIOSH."""
import re, html, unicodedata

def _norm(s):
    s = unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode().lower()
    return s.strip()

# label (normalizado) -> chave
def _key_for(label):
    n = _norm(label)
    table = [
        ('formula', 'formula'), ('cas#', 'cas'), ('cas', 'cas'), ('rtecs', 'rtecs'),
        ('idlh', 'idlh'), ('conversao', 'conv'), ('dot', 'dot'),
        ('sinonimos', 'syn'), ('limites de exposicao', 'limits'),
        ('descricao fisica', 'phys'), ('metodos de medicao', 'methods'),
        ('propriedades', 'props'), ('protecao', 'ppe'),
        ('recomendacoes de respirador', 'resp'), ('respirador', 'resp'),
        ('incompatibilidades', 'incompat'), ('vias de exposicao', 'routes'),
        ('primeiros socorros', 'firstaid'),
    ]
    for pref, k in table:
        if n.startswith(pref):
            return k
    return None

_LABEL_RE = re.compile(r'^\*\*(.+?):\*\*\s?(.*)$')

def is_ficha(block):
    return ('**CAS#:' in block) or ('**Fórmula:' in block) or ('**Formula:' in block)

def parse_ficha(block):
    lines = block.splitlines()
    name = re.sub(r'^###\s*', '', lines[0]).strip()
    fields = {}
    cur = None
    for ln in lines[1:]:
        if ln.strip() == '---':
            cur = None; continue
        m = _LABEL_RE.match(ln.strip())
        if m:
            k = _key_for(m.group(1))
            if k:
                cur = k
                fields[k] = m.group(2).strip()
                continue
            else:
                cur = None
        if cur is not None and ln.strip():
            fields[cur] = (fields.get(cur, '') + '\n' + ln.strip()).strip()
    return name, fields

def fmt(text):
    if not text:
        return ''
    # artefatos de alinhamento em coluna (NIOSH REL / OSHA PEL) viram espaço simples
    text = re.sub(r'(?:&nbsp;| |&amp;nbsp;)+', ' ', text)
    text = re.sub(r'[ \t]{2,}', ' ', text)
    t = html.escape(text)
    t = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', t)
    t = t.replace('\n', '<br>')
    return t

def tabref(label):
    """Transforma '(ver Tabela N)' / '(ver Tabelas 3 e 4)' em botões que abrem modal."""
    label = re.sub(r'\(ver Tabelas 3 e 4\)',
                   '(<button type="button" class="tabref" data-tab="3-4">ver Tabelas 3 e 4</button>)', label)
    label = re.sub(r'\(ver Tabela (\d)\)',
                   r'(<button type="button" class="tabref" data-tab="\1">ver Tabela \1</button>)', label)
    return label

def ficha_html(name, f, interactive=False):
    g = lambda k: fmt(f.get(k, ''))
    lab = (lambda s: tabref(s)) if interactive else (lambda s: s)
    ids = []
    for k, lbl in [('formula','Fórmula'),('cas','CAS#'),('rtecs','RTECS#'),('idlh','IDLH'),('dot','DOT')]:
        if f.get(k):
            ids.append(f'<div><b>{lbl}:</b> {fmt(f[k])}</div>')
    ids_html = ''.join(ids)
    conv = f'<div class="fconv"><b>Conversão:</b> {g("conv")}</div>' if f.get('conv') else ''
    def cell(label, key, colspan):
        label = lab(label)
        if not f.get(key):
            return f'<td colspan="{colspan}"><div class="flab">{label}</div><div class="fval"></div></td>'
        return f'<td colspan="{colspan}"><div class="flab">{label}</div><div class="fval">{g(key)}</div></td>'
    syn = ''
    if f.get('syn'):
        syn = f'<tr><td colspan="6"><div class="fval"><b>Sinônimos/Nomes Comerciais:</b> {g("syn")}</div></td></tr>'
    rows = f'''<table class="ficha">
<tr class="hdr">
  <td colspan="3"><div class="fc"><div class="fname">{html.escape(name)}</div>{conv}</div></td>
  <td colspan="3"><div class="fc fids">{ids_html}</div></td>
</tr>
{syn}
<tr>
  {cell("Limites de Exposição:", "limits", 3)}
  {cell("Métodos de Medição (ver Tabela 1):", "methods", 3)}
</tr>
<tr>{cell("Descrição Física:", "phys", 6)}</tr>
<tr>
  {cell("Propriedades Químicas e Físicas:", "props", 2)}
  {cell("Proteção Individual/Higiene (ver Tabela 2):", "ppe", 2)}
  {cell("Recomendações de Respirador (ver Tabelas 3 e 4):", "resp", 2)}
</tr>
<tr>{cell("Incompatibilidades e Reatividades:", "incompat", 6)}</tr>
<tr>
  {cell("Vias de Exposição, Sintomas, Órgãos-Alvo (ver Tabela 5):", "routes", 3)}
  {cell("Primeiros Socorros (ver Tabela 6):", "firstaid", 3)}
</tr>
</table>'''
    return rows

_SPLIT_RE = re.compile(r'(?m)^(?=### )')

def render_markdown(text, mdconv, interactive=False):
    """Converte markdown; fichas quimicas viram grade NIOSH, resto via markdown normal."""
    parts = _SPLIT_RE.split(text)
    out = []
    for seg in parts:
        if not seg.strip():
            continue
        if seg.lstrip().startswith('### ') and is_ficha(seg):
            name, f = parse_ficha(seg)
            out.append(ficha_html(name, f, interactive=interactive))
        else:
            mdconv.reset()
            out.append(mdconv.convert(seg))
    return '\n'.join(out)

# CSS das fichas (compartilhado entre tela e impressao via ajustes de tamanho)
def ficha_css(screen=True):
    base = """
table.ficha{border-collapse:collapse;width:100%;margin:14px 0 20px;border:1.5px solid #2a3f55;page-break-inside:avoid}
table.ficha td{border:0.75px solid #9bb0c4;vertical-align:top;padding:0}
table.ficha .fc{padding:4px 6px}
table.ficha .fname{font-weight:700;color:#0d2b45}
table.ficha .fconv{margin-top:3px}
table.ficha .fids div{line-height:1.4}
table.ficha .flab{background:#cfe0ee;font-weight:700;color:#13344f;padding:2px 6px;border-bottom:0.75px solid #9bb0c4}
table.ficha .fval{padding:3px 6px;line-height:1.4}
table.ficha .hdr td{background:#eef4f9}
"""
    if screen:
        sizes = """
table.ficha{font-size:.82rem}
table.ficha .fname{font-size:1.12rem}
table.ficha .fconv,table.ficha .fids div{font-size:.8rem}
table.ficha .flab{font-size:.74rem}
table.ficha .fval{font-size:.8rem}
"""
    else:
        sizes = """
table.ficha{font-size:7.6pt}
table.ficha .fname{font-size:10.5pt}
table.ficha .fconv,table.ficha .fids div{font-size:7.4pt}
table.ficha .flab{font-size:6.8pt}
table.ficha .fval{font-size:7.4pt}
"""
    return base + sizes
