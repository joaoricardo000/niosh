#!/usr/bin/env python3
"""Concatena os 114 blocos -> Markdown unico, e gera site/ (index.html + livro.html)."""
import re, os, sys, glob, json, html, datetime
import markdown
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import niosh_render

# caminhos relativos ao repositório (scripts/ -> raiz)
ROOT = os.environ.get('NIOSH_ROOT') or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHUNKS = os.path.join(ROOT, 'translation', 'chunks')
OUTDIR = os.path.join(ROOT, 'translation')   # Niosh-pt-BR.md
SITE = os.path.join(ROOT, 'docs')            # site (GitHub Pages)
os.makedirs(SITE, exist_ok=True)
os.makedirs(OUTDIR, exist_ok=True)

# 1) concatenar blocos em ordem
parts = []
missing = []
for i in range(1, 115):
    f = f"{CHUNKS}/chunk_{i:03d}.md"
    if not os.path.exists(f) or os.path.getsize(f) < 50:
        missing.append(i); continue
    with open(f) as fh:
        parts.append(fh.read().strip())
if missing:
    print("FALTANDO/VAZIO:", missing); sys.exit(2)

TITLE = "NIOSH — Guia de bolso de riscos químicos"
SUBTITLE = "NIOSH Pocket Guide to Chemical Hazards — DHHS (NIOSH) Publicação Nº 2005-149 — Tradução PT-BR"
full_md = "\n\n".join(parts)
# colapsa "líderes de pontos" do sumário (....) que quebram o layout no mobile
full_md = re.sub(r' *\.{4,} *', ' … ', full_md)

md_path = os.path.join(OUTDIR, "Niosh-pt-BR.md")
with open(md_path, "w") as fh:
    fh.write(f"# {TITLE}\n\n*{SUBTITLE}*\n\n---\n\n" + full_md + "\n")
print("Markdown unico:", md_path, os.path.getsize(md_path), "bytes")

# âncoras (#tabela-N) nas Tabelas 1-6
for _n in '123456':
    full_md = re.sub(r'(^## Tabela ' + _n + r'\b[^\n]*)$', r'\1 {#tabela-' + _n + '}', full_md, count=1, flags=re.M)

marker = re.compile(r'<!--\s*p[áa]g\.\s*orig\.\s*(\d+)\s*-->', re.I)
_SEP = re.compile(r'^\|[\s:\-|]+\|\s*$')

def merge_continuation_tables(md):
    """Remove cabeçalhos 'Tabela N (Continuação)' e funde tabelas consecutivas de mesmo
    cabeçalho numa só tabela contínua."""
    md = re.sub(r'(?m)^## Tabela \d+ \(Continua[çc][ãa]o\)[^\n]*\n(?:### [^\n]*\n)?', '', md)
    lines = md.split('\n')
    out, cur_header = [], None
    i, n = 0, len(lines)
    while i < n:
        l = lines[i]
        if l.startswith('|') and i + 1 < n and _SEP.match(lines[i + 1]):
            j = len(out) - 1
            while j >= 0 and out[j].strip() == '':
                j -= 1
            prev_is_row = j >= 0 and out[j].startswith('|')
            if cur_header == l and prev_is_row:           # mesma tabela -> funde
                while out and out[-1].strip() == '':
                    out.pop()
                i += 2
                continue
            cur_header = l
            out.append(lines[i]); out.append(lines[i + 1])
            i += 2
            continue
        if l.strip() != '' and not l.startswith('|'):
            cur_header = None                              # saiu do contexto da tabela
        out.append(l)
        i += 1
    text = '\n'.join(out)
    # remove linhas-subcabeçalho redundantes do tipo "| **Pele (continuação):** | |"
    text = re.sub(r'(?m)^\|\s*\*\*[^|]*\(continua[çc][ãa]o\)[^|]*\*\*\s*\|\s*\|\s*$\n?', '', text)
    return text

def _extract_tabelas(md):
    lines = md.split('\n')
    heads = [i for i, l in enumerate(lines) if l.startswith('## ')]
    out = {}
    for hi, idx in enumerate(heads):
        m = re.match(r'## Tabela (\d)', lines[idx])
        if not m:
            continue
        n = m.group(1)
        end = heads[hi + 1] if hi + 1 < len(heads) else len(lines)
        blk = re.sub(r'\s*\{#tabela-\d\}', '', '\n'.join(lines[idx:end]))
        mdc = markdown.Markdown(extensions=['tables', 'sane_lists', 'attr_list'])
        out[n] = mdc.convert(blk)
    return out

mdconv = markdown.Markdown(extensions=['tables', 'fenced_code', 'sane_lists', 'attr_list'])

# 2) front matter (contínuo, tabelas fundidas) | listagem+apêndices+índices (paginado)
# divide no título "LISTAGEM DE SUBSTÂNCIAS QUÍMICAS" (que passa a encabeçar a listagem),
# senão na 1ª ficha.
mlist = re.search(r'(?m)^# LISTAGEM DE SUBST[^\n]*\n', full_md)
if mlist:
    bidx = mlist.start()
    rest_md = marker.sub('', full_md[bidx:], count=1)   # tira o 1º marcador p/ o título encabeçar a 1ª página
else:
    mb = re.search(r'(?m)^### [^\n]+\n+\*\*Fórmula:\*\*', full_md)
    bidx = mb.start() if mb else len(full_md)
    rest_md = full_md[bidx:]
front_md = merge_continuation_tables(marker.sub('', full_md[:bidx]))

fm_html = niosh_render.render_markdown(front_md, mdconv, interactive=True)
TABELAS = _extract_tabelas(front_md)
print("tabelas (modal):", sorted(TABELAS))

pieces = marker.split(rest_md)
rest_pages = []
if pieces[0].strip():
    rest_pages.append((None, pieces[0]))
for k in range(1, len(pieces), 2):
    num = int(pieces[k]); body = pieces[k + 1] if k + 1 < len(pieces) else ""
    rest_pages.append((num, body))
rest_html = [(num, niosh_render.render_markdown(body.strip(), mdconv, interactive=True)) for num, body in rest_pages]
print("paginas listagem:", len(rest_html))

# 3) seções: 0 = front matter contínuo; 1.. = paginado
sect = [f'<section class="pg fm active" data-idx="0">{fm_html}</section>']
for j, (num, h) in enumerate(rest_html):
    sect.append(f'<section class="pg" data-idx="{j+1}" data-orig="{num if num is not None else ""}">{h}</section>')
sections_html = "\n".join(sect)
total = len(rest_html) + 1
origs = [None] + [(num if num is not None else None) for num, _ in rest_html]

# indice de substancias (autocomplete)
subs = []
for j, (num, h) in enumerate(rest_html):
    for m in re.finditer(r'<div class="fname">(.*?)</div>', h):
        subs.append({"n": html.unescape(m.group(1)), "p": j + 1})
subs.sort(key=lambda x: x["n"].lower())
print("substancias indexadas:", len(subs))

# secoes de Apendices e Indices (por cabecalho h1/h2)
def find_head(pat):
    rx = re.compile(pat, re.I)
    for j, (num, h) in enumerate(rest_html):
        for m in re.finditer(r'<h[12][^>]*>(.*?)</h[12]>', h, re.S):
            if rx.search(m.group(1)):
                return j + 1
    return None
app_idx = find_head(r'ap[êe]ndice')
idx_idx = find_head(r'índices|índice (por )?(número|nome)|cas number index|number index')
gen_date = datetime.date(2026, 6, 29).isoformat()

REPO_URL = "https://github.com/joaoricardo000/niosh"

ANALYTICS = ('<script defer src="https://atabela.com.br/a/s.js" '
             'data-website-id="da03b5b1-c78f-4444-b06f-52fb2ee65efa"></script>')

LOGO = ('<svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" '
        'stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">'
        '<path d="M9 2h6"/><path d="M10 2v6L4.5 18.5A2 2 0 0 0 6.3 21.5h11.4a2 2 0 0 0 1.8-3L14 8V2"/>'
        '<path d="M7 14h10"/></svg>')

linkbtns = ['<button class="mbtn mfull" data-go="LIST">Listagem</button>', '<button class="mbtn mfull" data-go="TAB">Tabelas</button>']
links_html = "\n".join(linkbtns)

CSS = """
*{box-sizing:border-box}
body{margin:0;font-family:-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;color:#1a1a1a;background:#f4f5f7;line-height:1.5}
header.bar{position:sticky;top:0;z-index:30;background:#0d2b45;color:#fff;display:flex;gap:.4rem;align-items:center;padding:.4rem .6rem;min-height:50px;transition:transform .25s ease}
header.bar.hide{transform:translateY(-100%)}
.bar .brand{display:flex;align-items:center;gap:.35rem;color:#fff;text-decoration:none;font-weight:700;font-size:.85rem;white-space:nowrap}
.bar .brand:hover{color:#cde}
.bar .ico{background:#1769aa;color:#fff;border:0;border-radius:8px;padding:.4rem .55rem;cursor:pointer;font-size:1rem;line-height:1}
.bar .ico:hover{background:#2a86d6}
#installbtn{margin-left:auto}
#installbtn svg{display:block}
.pagebox{display:flex;align-items:center}
.pagebtn{background:transparent;color:#cfe0ee;border:0;font:inherit;font-size:.85rem;cursor:pointer;padding:.35rem .45rem;border-radius:6px;white-space:nowrap;min-width:2.4rem;text-align:center}
.pagebtn:hover{background:rgba(255,255,255,.14);color:#fff}
.pagebox input{width:4.6rem;padding:.4rem;border:0;border-radius:6px;font:inherit}
.bar .ac{position:relative;flex:1;min-width:130px;max-width:460px}
.bar .ac input{width:100%;padding:.42rem .6rem;border-radius:8px;border:0;font:inherit}
.aclist{position:absolute;top:112%;left:0;right:0;background:#fff;color:#1a1a1a;border-radius:8px;box-shadow:0 8px 24px rgba(0,0,0,.25);list-style:none;margin:0;padding:.25rem;max-height:64vh;overflow:auto;display:none;z-index:40}
.aclist.open{display:block}
.aclist li{padding:.4rem .55rem;border-radius:6px;cursor:pointer;font-size:.9rem;display:flex;justify-content:space-between;gap:.5rem}
.aclist li.sel,.aclist li:hover{background:#e3eefb}
.aclist li small{color:#888;white-space:nowrap}
.ind{font-size:.78rem;color:#cde;white-space:nowrap;max-width:30vw;overflow:hidden;text-overflow:ellipsis}
.menu{position:absolute;top:100%;right:.5rem;margin-top:.3rem;background:#fff;color:#1a1a1a;border-radius:12px;box-shadow:0 12px 32px rgba(0,0,0,.32);padding:.6rem;width:270px;display:none;z-index:50}
.menu.open{display:block}
.menu .mi{display:block;padding:.55rem .6rem;border-radius:8px;text-decoration:none;color:#0d2b45;font-size:.9rem}
.menu a.mi:hover{background:#eef3f7}
.menu label.mi input{display:block;width:100%;margin-top:.35rem}
.menu input{font:inherit;padding:.5rem;border:1px solid #ccc;border-radius:8px;width:100%}
.menu .mrow{display:flex;gap:.4rem;margin:.4rem 0}
.menu .mrow>*{flex:1;min-width:0}
.menu .mbtn{background:#0d2b45;color:#fff;border:0;border-radius:8px;padding:.6rem;cursor:pointer;font-size:.85rem}
.menu .mbtn:hover{background:#1769aa}
.menu .mfull{display:block;width:100%;margin-top:.45rem}
.wrap{max-width:940px;margin:1rem auto;padding:0 1rem;overflow-x:clip}
.pg{display:none;background:#fff;padding:1.4rem 1.7rem;border:1px solid #e2e2e2;border-radius:10px;box-shadow:0 1px 3px rgba(0,0,0,.06);overflow-wrap:break-word}
.pg.active{display:block}
.pgtag{font-size:.7rem;color:#bbb;text-align:right;margin:.6rem 0 -.2rem}
.pgsep{border:0;border-top:1px dashed #d4d4d4;margin:1.6rem 0}
.pg h1{font-size:1.5rem;border-bottom:2px solid #0d2b45;padding-bottom:.3rem}
.pg h2{font-size:1.25rem;color:#0d2b45;margin-top:1.4rem}
.pg h3{font-size:1.05rem;color:#0a3d62;margin-top:1.2rem;border-left:4px solid #0b5;padding-left:.5rem}
.pg table:not(.ficha){border-collapse:collapse;width:100%;margin:.8rem 0;font-size:.88rem}
.pg table:not(.ficha) th,.pg table:not(.ficha) td{border:1px solid #ccc;padding:.35rem .5rem;text-align:left;vertical-align:top}
.pg table:not(.ficha) th{background:#eef3f7}
.pg code{background:#f0f0f0;padding:.1rem .3rem;border-radius:4px;font-size:.88em}
mark{background:#ffec99}
/* botão de referência a tabela dentro das fichas */
.tabref{display:inline;background:#e3eefb;color:#1769aa;border:1px solid #bcd6f0;border-radius:6px;padding:0 .35rem;margin:0 .05rem;font:inherit;font-size:.92em;font-weight:600;cursor:pointer;line-height:1.25;white-space:nowrap}
.tabref:hover{background:#1769aa;color:#fff;border-color:#1769aa}
/* modal de tabelas */
.modal{position:fixed;inset:0;background:rgba(6,17,33,.55);display:none;z-index:100;padding:3vh 3vw}
.modal.open{display:flex;align-items:flex-start;justify-content:center}
.modal-box{background:#fff;border-radius:12px;max-width:920px;width:100%;max-height:94vh;overflow:auto;box-shadow:0 24px 70px rgba(0,0,0,.45);position:relative;padding:1rem 1.3rem 1.5rem}
.modal-close{position:sticky;top:0;float:right;background:#0d2b45;color:#fff;border:0;border-radius:8px;width:36px;height:36px;font-size:1.05rem;cursor:pointer;z-index:2}
.modal-box h2{font-size:1.15rem;color:#0d2b45;margin:.3rem 0 .2rem;clear:both}
.modal-box table{border-collapse:collapse;width:100%;margin:.6rem 0;font-size:.85rem}
.modal-box th,.modal-box td{border:1px solid #ccc;padding:.35rem .5rem;text-align:left;vertical-align:top}
.modal-box th{background:#eef3f7}
.modal-box code{background:#f0f0f0;padding:.1rem .3rem;border-radius:4px}
@media(max-width:600px){.modal{padding:0}.modal-box{border-radius:0;max-height:100vh;min-height:100vh;padding:.8rem .9rem 1.4rem}.modal-box table{display:block;overflow-x:auto;font-size:.8rem}}
.foot{max-width:940px;margin:1rem auto 3rem;color:#666;font-size:.8rem;padding:0 1rem;text-align:center}
@media print{header.bar{display:none}.pg{display:block!important}}
/* ---------- responsivo / mobile (alvos de toque >=48px, fontes >=16px) ---------- */
@media (max-width:600px){
  /* cabeçalho em 2 linhas: (título + hambúrguer) / busca em largura total */
  .bar{flex-wrap:wrap;gap:.5rem;padding:.6rem .7rem}
  .bar .brand{order:1;gap:.4rem}
  .bar .brand span{display:none}
  .bar .brand svg{width:30px;height:30px}
  #prev{order:2}
  .pagebox{order:3}
  #next{order:4}
  #installbtn{order:5;margin-left:auto;min-width:46px;min-height:46px;padding:.3rem;display:inline-flex;align-items:center;justify-content:center;border-radius:10px}
  .bar .nav{font-size:1.35rem;min-width:44px;min-height:44px;padding:.3rem;display:inline-flex;align-items:center;justify-content:center;border-radius:10px}
  .pagebtn{font-size:1rem;min-height:44px}
  .pagebox input{font-size:16px}
  .bar .ac{order:6;flex-basis:100%;max-width:100%}
  .bar .ac input{font-size:16px;padding:.7rem .85rem}
  .aclist{max-height:70vh}
  .aclist li{padding:.75rem .65rem;font-size:1rem;min-height:48px;align-items:center}
  .aclist li small{font-size:.85rem}
  /* menu maior e mais tocável */
  .menu{left:.5rem;right:.5rem;width:auto;padding:.7rem}
  .menu .mi{font-size:1rem;padding:.75rem .6rem}
  .menu input{font-size:16px;padding:.65rem}
  .menu .mbtn{font-size:1rem;padding:.8rem;min-height:50px}
  .menu .mlinks{gap:.5rem}
  .menu .mlinks button{font-size:.95rem;padding:.8rem;min-height:48px}
  /* corpo com fonte maior */
  .wrap{margin:.6rem auto;padding:0 .55rem}
  .pg{padding:1.1rem .95rem;border-radius:8px;font-size:1.05rem;line-height:1.55}
  .pg h1{font-size:1.4rem}.pg h2{font-size:1.2rem}.pg h3{font-size:1.08rem}
  /* botões de referência de tabela: maiores p/ toque */
  .tabref{font-size:.98em;padding:.2rem .55rem;border-radius:8px}
  /* modal: botão fechar maior */
  .modal-close{width:46px;height:46px;font-size:1.25rem}
  /* tabelas comuns rolam na horizontal */
  .pg table:not(.ficha){display:block;overflow-x:auto;-webkit-overflow-scrolling:touch}
  /* fichas químicas empilham em coluna única, com fonte maior */
  table.ficha,table.ficha tbody,table.ficha tr,table.ficha td{display:block;width:100%!important}
  table.ficha tr{border:0}
  table.ficha td{border:0;border-top:1px solid #9bb0c4}
  table.ficha tr.hdr td:first-child{border-top:0}
  table.ficha{font-size:.98rem}
  table.ficha .fname{font-size:1.25rem}
  table.ficha .fconv,table.ficha .fids div{font-size:.95rem}
  table.ficha .flab{font-size:.9rem;border-top:1px solid #9bb0c4;padding:.4rem .5rem}
  table.ficha .fval{font-size:.98rem;padding:.45rem .55rem}
}
""" + niosh_render.ficha_css(screen=True)

JS = r"""
const origs=__ORIGS__, subs=__SUBS__, total=__TOTAL__, APP=__APP__, IDX=__IDX__, LIST=1;
const TABELAS=__TABELAS__;
const norm=s=>(s||'').normalize('NFD').replace(/[̀-ͯ]/g,'').toLowerCase();
subs.forEach(s=>s.k=norm(s.n));
const pages=[...document.querySelectorAll('.pg')];
let cur=0;
const pagenum=document.getElementById('pagenum');
const jin=document.getElementById('jump');
function show(i,keepHash){
  i=parseInt(i,10); if(isNaN(i))i=0;
  if(i!==0){ i=Math.max(1,Math.min(total-1,i)); }
  pages[cur].classList.remove('active');
  cur=i; pages[i].classList.add('active');
  if(i===0){ pagenum.textContent='início'; }
  else { pagenum.textContent=i+' / '+(total-1); }
  if(jin) jin.value=(i===0?1:i);
  window.scrollTo(0,0); if(!keepHash) location.hash='p'+(i+1);
}
document.getElementById('prev').onclick=()=>show(cur-1);
document.getElementById('next').onclick=()=>show(cur+1);
document.addEventListener('keydown',e=>{
  if(e.target.tagName==='INPUT')return;
  if(modal&&modal.classList.contains('open'))return;
  if(e.key==='ArrowLeft')show(cur-1);
  if(e.key==='ArrowRight')show(cur+1);
});

/* ---- autocomplete de substancias ---- */
const si=document.getElementById('subsearch'), al=document.getElementById('aclist');
let acItems=[], acSel=-1;
function renderAC(){
  const q=norm(si.value.trim());
  al.innerHTML=''; acSel=-1;
  if(!q){al.classList.remove('open');return;}
  const starts=[], has=[];
  for(const s of subs){const l=s.k; if(l.startsWith(q))starts.push(s); else if(l.includes(q))has.push(s);}
  acItems=starts.concat(has).slice(0,14);
  if(!acItems.length){al.classList.remove('open');return;}
  acItems.forEach(s=>{
    const li=document.createElement('li');
    const name=document.createElement('span'); name.textContent=s.n;
    const pg=document.createElement('small'); pg.textContent='pág. '+s.p;
    li.appendChild(name); li.appendChild(pg);
    li.onmousedown=e=>{e.preventDefault(); si.value=''; al.classList.remove('open'); si.blur(); show(s.p);};
    al.appendChild(li);
  });
  al.classList.add('open');
}
si.addEventListener('input',renderAC);
si.addEventListener('focus',renderAC);
si.addEventListener('keydown',e=>{
  if(!al.classList.contains('open'))return;
  const lis=[...al.children];
  if(e.key==='ArrowDown'){e.preventDefault();acSel=Math.min(lis.length-1,acSel+1);}
  else if(e.key==='ArrowUp'){e.preventDefault();acSel=Math.max(0,acSel-1);}
  else if(e.key==='Enter'){e.preventDefault();const s=acItems[acSel>=0?acSel:0];if(s){si.value='';al.classList.remove('open');si.blur();show(s.p);}return;}
  else if(e.key==='Escape'){al.classList.remove('open');return;}
  else return;
  lis.forEach((li,k)=>li.classList.toggle('sel',k===acSel));
  if(lis[acSel])lis[acSel].scrollIntoView({block:'nearest'});
});

/* ---- número da página no header: clicar abre input para digitar ---- */
function closeJump(){ if(jin)jin.style.display='none'; if(pagenum)pagenum.style.display=''; }
function doJump(){ show(parseInt(jin.value,10)||1); closeJump(); }
if(pagenum) pagenum.onclick=()=>{ pagenum.style.display='none'; jin.style.display=''; jin.value=(cur===0?1:cur); jin.focus(); try{jin.select();}catch(_){} };
if(jin){ jin.addEventListener('change',doJump); jin.addEventListener('blur',closeJump);
  jin.addEventListener('keydown',e=>{ if(e.key==='Enter'){e.preventDefault();doJump();} else if(e.key==='Escape')closeJump(); }); }
document.addEventListener('click',e=>{ if(!e.target.closest('.ac')) al.classList.remove('open'); });

/* ---- modal de tabelas ---- */
const modal=document.getElementById('modal'), modalBody=document.getElementById('modal-body');
function openTabela(key){
  let html=(key==='3-4') ? ((TABELAS['3']||'')+(TABELAS['4']||'')) : (TABELAS[key]||'');
  modalBody.innerHTML=html||'<p>Tabela não disponível.</p>';
  modal.classList.add('open'); document.body.style.overflow='hidden'; modal.scrollTop=0;
}
function closeModal(){modal.classList.remove('open'); document.body.style.overflow='';}
document.addEventListener('click',e=>{
  const b=e.target.closest('.tabref');
  if(b){e.preventDefault(); openTabela(b.dataset.tab); return;}
  if(e.target===modal || e.target.closest('.modal-close')) closeModal();
});
document.addEventListener('keydown',e=>{ if(e.key==='Escape') closeModal(); });

/* ---- barra auto-oculta no mobile (reaparece ao rolar para cima) ---- */
const bar=document.querySelector('header.bar');
let lastY=window.scrollY||0, ticking=false;
function onScroll(){
  const y=window.scrollY||0;
  if(window.matchMedia('(max-width:600px)').matches){
    if(y>lastY+4 && y>90) bar.classList.add('hide');
    else if(y<lastY-4) bar.classList.remove('hide');
  } else bar.classList.remove('hide');
  lastY=y; ticking=false;
}
window.addEventListener('scroll',()=>{ if(!ticking){requestAnimationFrame(onScroll); ticking=true;} },{passive:true});

/* ---- PWA: instalar como app ---- */
let deferredPrompt=null;
const installbtn=document.getElementById('installbtn');
if(window.matchMedia('(display-mode: standalone)').matches && installbtn) installbtn.style.display='none';
window.addEventListener('beforeinstallprompt',e=>{e.preventDefault(); deferredPrompt=e;});
if(installbtn) installbtn.onclick=async()=>{
  if(deferredPrompt){ deferredPrompt.prompt(); await deferredPrompt.userChoice; deferredPrompt=null; }
  else { alert('Para instalar este guia como app:\n\n• Android (Chrome): menu ⋮ → "Adicionar à tela inicial".\n• iPhone (Safari): botão Compartilhar → "Adicionar à Tela de Início".'); }
};
window.addEventListener('appinstalled',()=>{ if(installbtn) installbtn.style.display='none'; });
if('serviceWorker' in navigator){ navigator.serviceWorker.register('sw.js').then(reg=>{ reg.addEventListener('updatefound',()=>{const nw=reg.installing; if(nw) nw.addEventListener('statechange',()=>{ if(nw.state==='installed' && navigator.serviceWorker.controller){ nw.postMessage('skipWaiting'); } }); }); }).catch(()=>{}); let _rl=false; navigator.serviceWorker.addEventListener('controllerchange',()=>{ if(_rl)return; _rl=true; location.reload(); }); }

/* ---- roteamento por hash (#p N e #tabela-N) ---- */
function goHash(){
  const h=location.hash; let m;
  if(m=h.match(/^#tabela-(\d)/)){ show(0,true); const el=document.getElementById('tabela-'+m[1]); if(el) setTimeout(()=>el.scrollIntoView({block:'start',behavior:'smooth'}),40); return true; }
  if(m=h.match(/^#p(\d+)/)){ show(parseInt(m[1],10)-1,true); return true; }
  return false;
}
window.addEventListener('hashchange',goHash);
if(!goHash()) show(0);
"""
JS = (JS.replace("__ORIGS__", json.dumps(origs))
        .replace("__SUBS__", json.dumps(subs, ensure_ascii=False))
        .replace("__TOTAL__", str(total))
        .replace("__APP__", json.dumps(app_idx))
        .replace("__IDX__", json.dumps(idx_idx))
        .replace("__TABELAS__", json.dumps(TABELAS, ensure_ascii=False)))

livro = f"""<!doctype html><html lang="pt-BR"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(TITLE)} — Livro</title>
{ANALYTICS}
<link rel="manifest" href="manifest.json"><meta name="theme-color" content="#0d2b45">
<link rel="apple-touch-icon" href="icon-192.png">
<style>{CSS}</style></head>
<body>
<header class="bar">
  <a class="brand" href="index.html" title="Início (home)">{LOGO}<span>NIOSH·PT-BR</span></a>
  <button id="prev" class="ico nav" title="Anterior (←)">◀</button>
  <span class="pagebox"><button id="pagenum" type="button" class="pagebtn" title="Ir para página">—</button><input id="jump" type="number" min="1" max="{total-1}" style="display:none"></span>
  <button id="next" class="ico nav" title="Próxima (→)">▶</button>
  <div class="ac">
    <input id="subsearch" type="search" placeholder="🔍 Buscar substância…" autocomplete="off" spellcheck="false">
    <ul id="aclist" class="aclist"></ul>
  </div>
  <button id="installbtn" class="ico" title="Instalar como app" aria-label="Instalar como app"><svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="#fff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 3v12"/><path d="M7 11l5 5 5-5"/><path d="M5 21h14"/></svg></button>
</header>
<div class="wrap">
{sections_html}
</div>
<div class="foot">{html.escape(SUBTITLE)}<br>Domínio público (CC0 1.0). Tradução automática para PT-BR — revisão recomendada para uso crítico. Gerado em {gen_date}.<br><a href="{REPO_URL}" target="_blank" rel="noopener" style="color:#789">github.com/joaoricardo000/niosh</a></div>
<div id="modal" class="modal" aria-hidden="true">
  <div class="modal-box"><button class="modal-close" type="button" title="Fechar" aria-label="Fechar">✕</button><div id="modal-body"></div></div>
</div>
<script>{JS}</script>
</body></html>"""
with open(os.path.join(SITE, "livro.html"), "w") as fh:
    fh.write(livro)
print("livro.html:", os.path.getsize(os.path.join(SITE, "livro.html")), "bytes")

# 4) index.html (capa + downloads) — design consistente com o app
def kb(b): return f"{b/1024:.0f} KB" if b < 1024*1024 else f"{b/1024/1024:.1f} MB"
pdf_path = os.path.join(SITE, "Niosh-pt-BR.pdf")
en_path = os.path.join(SITE, "Niosh-EN.pdf")
pdf_size = os.path.getsize(pdf_path) if os.path.exists(pdf_path) else 0
en_size = os.path.getsize(en_path) if os.path.exists(en_path) else 0
pdf_pages = en_pages = ""
try:
    import fitz
    if pdf_size: pdf_pages = f" · {fitz.open(pdf_path).page_count} páginas"
    if en_size: en_pages = f" · {fitz.open(en_path).page_count} páginas"
except Exception:
    pass

READ_ICON = ('<svg viewBox="0 0 48 48" fill="none" stroke="#fff" stroke-width="2.3" '
             'stroke-linecap="round" stroke-linejoin="round">'
             '<path d="M24 13c-3.2-2.4-7.3-3.4-12-3.4-2 0-3.2.4-3.2.4v26.6s1.2-.5 3.2-.5c4.7 0 8.8 1 12 3.4"/>'
             '<path d="M24 13c3.2-2.4 7.3-3.4 12-3.4 2 0 3.2.4 3.2.4v26.6s-1.2-.5-3.2-.5c-4.7 0-8.8 1-12 3.4z"/>'
             '<path d="M24 13v26.5"/></svg>')
# ícone clássico de arquivo PDF (documento branco com canto dobrado + faixa vermelha "PDF")
PDF_ICON = ('<svg viewBox="0 0 48 48" xmlns="http://www.w3.org/2000/svg">'
            '<path d="M11 3h17l9 9v30a3 3 0 0 1-3 3H11a3 3 0 0 1-3-3V6a3 3 0 0 1 3-3z" fill="#fff"/>'
            '<path d="M28 3l9 9h-6.2A2.8 2.8 0 0 1 28 9.2V3z" fill="#cdd9e5"/>'
            '<rect x="5" y="25" width="33" height="13" rx="2" fill="#e03131"/>'
            '<text x="21.5" y="34.3" font-family="Arial,Helvetica,sans-serif" font-size="8.5" '
            'font-weight="700" fill="#fff" text-anchor="middle">PDF</text></svg>')

INDEX_CSS = """
*{box-sizing:border-box}
body{margin:0;font-family:-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;background:#f4f5f7;color:#1a1a1a;line-height:1.55}
.topbar{position:sticky;top:0;z-index:10;background:#0d2b45;color:#fff;display:flex;gap:.4rem;align-items:center;justify-content:space-between;padding:.4rem .6rem;min-height:50px}
.topbar .ac{position:relative;flex:1;min-width:120px;max-width:420px}
.topbar .ac input{width:100%;padding:.42rem .6rem;border-radius:8px;border:0;font:inherit}
.topbar .aclist{position:absolute;top:112%;left:0;right:0;background:#fff;color:#1a1a1a;border-radius:8px;box-shadow:0 8px 24px rgba(0,0,0,.25);list-style:none;margin:0;padding:.25rem;max-height:64vh;overflow:auto;display:none;z-index:40}
.topbar .aclist.open{display:block}
.topbar .aclist li{padding:.45rem .55rem;border-radius:6px;cursor:pointer;font-size:.9rem;display:flex;justify-content:space-between;gap:.5rem}
.topbar .aclist li.sel,.topbar .aclist li:hover{background:#e3eefb}
.topbar .aclist li small{color:#888;white-space:nowrap}
@media(max-width:560px){.topbar .brand span{display:none}}
.topbar .brand{display:flex;align-items:center;gap:.35rem;color:#fff;text-decoration:none;font-weight:700;font-size:.85rem;white-space:nowrap}
.topbar .brand svg{width:22px;height:22px}
.topbar .toplink{color:#fff;text-decoration:none;font-size:1rem;line-height:1;background:#1769aa;padding:.4rem .7rem;border-radius:8px;white-space:nowrap}
.topbar .toplink:hover{background:#2a86d6}
.hero{background:linear-gradient(160deg,#0d2b45,#15436b);color:#fff;padding:2.6rem 1.2rem 2.4rem;text-align:center}
.hero .badge{display:inline-block;background:rgba(255,255,255,.14);color:#dce8f3;font-size:.72rem;letter-spacing:.05em;text-transform:uppercase;padding:.3rem .75rem;border-radius:999px;margin-bottom:.85rem}
.hero h1{font-size:2.5rem;margin:.2rem auto;max-width:760px;line-height:1.1;letter-spacing:.06em}
.hero h1 span{display:block;font-size:.46em;font-weight:600;letter-spacing:.01em;color:#cfe0ee;margin-top:.5rem}
.hero .sub{color:#bcd3e6;font-size:1rem;max-width:680px;margin:.55rem auto 0}
.container{max-width:780px;margin:-1.5rem auto 0;padding:0 1rem 2rem}
.actions{display:flex;gap:1rem;flex-wrap:wrap}
.action{flex:1;min-width:250px;display:flex;align-items:center;gap:1rem;text-align:left;text-decoration:none;border-radius:14px;padding:1.1rem 1.3rem;color:#fff;box-shadow:0 8px 24px rgba(13,43,69,.18);transition:.15s}
.action:hover{transform:translateY(-2px);box-shadow:0 12px 30px rgba(13,43,69,.26)}
.action .ico{flex:0 0 auto;width:58px;height:58px;display:flex;align-items:center;justify-content:center}
.action .ico svg{width:100%;height:100%;display:block}
.action .txt{display:flex;flex-direction:column;min-width:0}
.action .txt .t{font-weight:700;font-size:1.08rem}
.action .txt small{font-weight:400;opacity:.92;font-size:.8rem;margin-top:.3rem}
.action.read{background:linear-gradient(135deg,#0b9c5a,#0a7d49)}
.action.dl{background:linear-gradient(135deg,#1769aa,#125a93)}
.minrow{margin-top:1rem}
.action-min{display:flex;align-items:baseline;gap:.5rem;width:100%;color:#34506a;text-decoration:none;font-size:.9rem;font-weight:600;border:1px solid #cdd8e2;background:#fff;padding:.85rem 1.3rem;border-radius:14px}
.action-min:hover{border-color:#1769aa;color:#0d2b45;box-shadow:0 4px 14px rgba(13,43,69,.1)}
.action-min small{color:#8895a3;font-size:.78rem;font-weight:400;margin-left:auto}
.card{background:#fff;border:1px solid #e6e9ee;border-radius:14px;padding:1.3rem 1.5rem;margin-top:1.6rem;box-shadow:0 2px 8px rgba(0,0,0,.05)}
.card h3{margin:.1rem 0 .6rem;color:#0d2b45}
.card ul{padding-left:1.1rem;margin:.4rem 0}.card li{margin:.28rem 0}
.meta{color:#5a6b7b;font-size:.85rem;margin-top:.85rem}.meta a{color:#1769aa}
.foot{color:#8595a4;font-size:.8rem;text-align:center;padding:1rem 1rem 2.6rem}
@media(max-width:560px){.hero h1{font-size:2rem}.hero{padding:2rem 1rem 1.9rem}.action{min-width:100%}}
"""

HOME_JS = r"""
const subs=__SUBS__;
const norm=s=>(s||'').normalize('NFD').replace(/[̀-ͯ]/g,'').toLowerCase();
subs.forEach(s=>s.k=norm(s.n));
const si=document.getElementById('subsearch'), al=document.getElementById('aclist');
let acItems=[], acSel=-1;
function go(p){location.href='livro.html#p'+(p+1);}
function renderAC(){
  const q=norm(si.value.trim()); al.innerHTML=''; acSel=-1;
  if(!q){al.classList.remove('open');return;}
  const starts=[],has=[];
  for(const s of subs){ if(s.k.startsWith(q))starts.push(s); else if(s.k.includes(q))has.push(s); }
  acItems=starts.concat(has).slice(0,14);
  if(!acItems.length){al.classList.remove('open');return;}
  acItems.forEach(s=>{const li=document.createElement('li');
    const a=document.createElement('span'); a.textContent=s.n;
    const b=document.createElement('small'); b.textContent='pág. '+s.p;
    li.appendChild(a); li.appendChild(b);
    li.onmousedown=e=>{e.preventDefault(); si.blur(); go(s.p);};
    al.appendChild(li); });
  al.classList.add('open');
}
si.addEventListener('input',renderAC);
si.addEventListener('focus',renderAC);
si.addEventListener('keydown',e=>{
  if(!al.classList.contains('open'))return;
  const lis=[...al.children];
  if(e.key==='ArrowDown'){e.preventDefault();acSel=Math.min(lis.length-1,acSel+1);}
  else if(e.key==='ArrowUp'){e.preventDefault();acSel=Math.max(0,acSel-1);}
  else if(e.key==='Enter'){e.preventDefault();const s=acItems[acSel>=0?acSel:0];if(s){si.blur();go(s.p);}return;}
  else if(e.key==='Escape'){al.classList.remove('open');return;}
  else return;
  lis.forEach((li,k)=>li.classList.toggle('sel',k===acSel));
});
document.addEventListener('click',e=>{if(!e.target.closest('.ac'))al.classList.remove('open');});
if('serviceWorker' in navigator){ navigator.serviceWorker.register('sw.js').then(reg=>{ reg.addEventListener('updatefound',()=>{const nw=reg.installing; if(nw) nw.addEventListener('statechange',()=>{ if(nw.state==='installed' && navigator.serviceWorker.controller){ nw.postMessage('skipWaiting'); } }); }); }).catch(()=>{}); let _rl=false; navigator.serviceWorker.addEventListener('controllerchange',()=>{ if(_rl)return; _rl=true; location.reload(); }); }
"""
HOME_JS = HOME_JS.replace("__SUBS__", json.dumps(subs, ensure_ascii=False))

index = f"""<!doctype html><html lang="pt-BR"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(TITLE)}</title>
{ANALYTICS}
<link rel="manifest" href="manifest.json"><meta name="theme-color" content="#0d2b45">
<link rel="apple-touch-icon" href="icon-192.png">
<style>{INDEX_CSS}</style></head>
<body>
<header class="topbar">
  <a class="brand" href="index.html" title="Início">{LOGO}<span>NIOSH·PT-BR</span></a>
  <div class="ac"><input id="subsearch" type="search" placeholder="🔍 Buscar substância…" autocomplete="off" spellcheck="false"><ul id="aclist" class="aclist"></ul></div>
  <a class="toplink" href="livro.html">Abrir leitor →</a>
</header>
<section class="hero">
  <div class="badge">Tradução PT-BR · CBMSC</div>
  <h1>NIOSH<span>Guia de bolso de riscos químicos</span></h1>
  <p class="sub">{html.escape(SUBTITLE)}</p>
</section>
<main class="container">
  <div class="actions">
    <a class="action read" href="livro.html"><span class="ico">{READ_ICON}</span><span class="txt"><span class="t">Ler o livro online</span><small>{len(subs)} substâncias · busca com autocomplete · layout responsivo</small></span></a>
    <a class="action dl" href="Niosh-pt-BR.pdf" download><span class="ico">{PDF_ICON}</span><span class="txt"><span class="t">Baixar PDF (🇧🇷 PT-BR)</span><small>{kb(pdf_size)}{pdf_pages}</small></span></a>
  </div>
  <div class="minrow">
    <a class="action-min" href="Niosh-EN.pdf" download>🇺🇸 Baixar PDF original (em inglês) <small>{kb(en_size)}{en_pages}</small></a>
  </div>
  <div class="card">
    <h3>Sobre esta tradução</h3>
    <ul>
      <li>Tradução para <b>português do Brasil</b> do <i>NIOSH Pocket Guide to Chemical Hazards</i> (2005-149, 3ª impressão).</li>
      <li><b>Medidas convertidas para o sistema métrico</b> (°F→°C, mmHg→kPa, atm→kPa), com o valor original entre parênteses.</li>
      <li>Nomes químicos traduzidos para PT-BR (original em inglês entre parênteses). Fórmulas, CAS#, RTECS#, DOT# e códigos de respirador/medição mantidos no original.</li>
      <li>Os índices finais (CAS/DOT/sinônimos) foram mantidos no original para preservar a função de busca alfabética.</li>
    </ul>
    <p class="meta">Documento original de <b>domínio público</b> do NIOSH. Esta é uma <b>tradução automática</b>; para uso crítico (resposta a emergência, decisões de segurança), confirme as informações na fonte oficial em
    <a href="https://www.cdc.gov/niosh/npg/" target="_blank" rel="noopener">cdc.gov/niosh/npg</a>. Gerado em {gen_date}.</p>
  </div>
  <div class="card">
    <h3>Código-fonte e licença</h3>
    <p class="meta">Projeto de código aberto. Código, dados da tradução e instruções de reprodução estão no GitHub:<br>
    <a href="{REPO_URL}" target="_blank" rel="noopener">{REPO_URL.replace('https://','')}</a></p>
    <p class="meta">Esta tradução e o site são liberados em <b>domínio público</b> sob <a href="https://creativecommons.org/publicdomain/zero/1.0/deed.pt_BR" target="_blank" rel="noopener">CC0 1.0</a> — uso, cópia e adaptação livres, sem necessidade de atribuição. O guia NIOSH original é domínio público do governo dos EUA.</p>
  </div>
</main>
<footer class="foot">CBMSC · <a href="{REPO_URL}" target="_blank" rel="noopener" style="color:#9ab">github.com/joaoricardo000/niosh</a> · CC0 1.0 (domínio público)</footer>
<script>{HOME_JS}</script>
</body></html>"""
with open(os.path.join(SITE, "index.html"), "w") as fh:
    fh.write(index)
print("index.html:", os.path.getsize(os.path.join(SITE, "index.html")), "bytes")

# 5) PWA — manifest + service worker
manifest = {
    "name": TITLE, "short_name": "NIOSH",
    "description": "Guia de Bolso de Riscos Químicos do NIOSH — tradução PT-BR (CBMSC)",
    "lang": "pt-BR", "start_url": "index.html", "scope": "./",
    "display": "standalone", "orientation": "portrait-primary",
    "background_color": "#0d2b45", "theme_color": "#0d2b45",
    "icons": [
        {"src": "icon-192.png", "sizes": "192x192", "type": "image/png", "purpose": "any"},
        {"src": "icon-512.png", "sizes": "512x512", "type": "image/png", "purpose": "any"},
        {"src": "icon-512.png", "sizes": "512x512", "type": "image/png", "purpose": "maskable"},
    ],
}
with open(os.path.join(SITE, "manifest.json"), "w") as fh:
    json.dump(manifest, fh, ensure_ascii=False, indent=2)

# versão derivada do conteúdo: muda só quando index/livro/manifest mudam -> auto-invalida cache do SW
import hashlib
_ver_src = (open(os.path.join(SITE, "index.html"), "rb").read()
            + open(os.path.join(SITE, "livro.html"), "rb").read()
            + json.dumps(manifest, ensure_ascii=False).encode())
SW_VER = hashlib.sha1(_ver_src).hexdigest()[:10]

SW = """const C='niosh-cbmsc-__VER__';
const ASSETS=['icon-192.png','icon-512.png','manifest.json'];
self.addEventListener('install',e=>{e.waitUntil(caches.open(C).then(c=>c.addAll(ASSETS)).catch(()=>{})); self.skipWaiting();});
self.addEventListener('activate',e=>{e.waitUntil(caches.keys().then(ks=>Promise.all(ks.filter(k=>k!==C).map(k=>caches.delete(k)))).then(()=>self.clients.claim()));});
function isHTML(r){return r.mode==='navigate' || (r.headers.get('accept')||'').includes('text/html') || /\\.html($|\\?)/.test(r.url);}
self.addEventListener('fetch',e=>{
  const r=e.request; if(r.method!=='GET' || !r.url.startsWith(self.location.origin)) return;
  if(isHTML(r)){
    // network-first: sempre tenta a versão mais nova; cai pro cache só offline
    e.respondWith(fetch(r).then(resp=>{const cp=resp.clone(); caches.open(C).then(c=>c.put(r,cp)); return resp;})
      .catch(()=>caches.match(r).then(h=>h||caches.match('livro.html')||caches.match('index.html'))));
  } else {
    // estáticos (ícones, pdf): cache-first com atualização em segundo plano
    e.respondWith(caches.match(r).then(hit=>hit || fetch(r).then(resp=>{const cp=resp.clone(); caches.open(C).then(c=>c.put(r,cp)); return resp;})));
  }
});
self.addEventListener('message',e=>{ if(e.data==='skipWaiting') self.skipWaiting(); });
""".replace('__VER__', SW_VER)
with open(os.path.join(SITE, "sw.js"), "w") as fh:
    fh.write(SW)
print("manifest.json + sw.js OK (sw ver", SW_VER + ")")
print("OK")
