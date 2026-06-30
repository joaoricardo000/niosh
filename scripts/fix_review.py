#!/usr/bin/env python3
"""Aplica as correções da revisão independente aos chunks PT-BR.
Uso: fix_review.py dry   (mostra o que mudaria)
     fix_review.py apply (grava)"""
import re, glob, sys, math

SP = '/tmp/claude-1000/-home-ubuntu-git-niosh/e2a5d2e8-67bf-45db-9ecf-58c4ddf9481e/scratchpad'
files = sorted(glob.glob(f"{SP}/out/chunk_*.md"))
mode = sys.argv[1] if len(sys.argv) > 1 else 'dry'

DEC = re.compile(r"(?<![\d,])(\d{1,3}),(\d+)(?![\d,'’]|-[^\d]|[A-Za-z])")

def sigfig(x, sig=3):
    if x == 0: return "0"
    d = math.ceil(math.log10(abs(x)))
    f = 10 ** (sig - d)
    r = round(x * f) / f
    s = f"{r:.10f}".rstrip('0').rstrip('.')
    return s

ATM = re.compile(r"([<>≥≤]?)\s*(\d+(?:\.\d+)?)\s*atm(?![A-Za-zÀ-ÿ])")
def conv_atm(text):
    out = []
    last = 0
    for m in ATM.finditer(text):
        pre = text[max(0, m.start()-12):m.start()]
        if 'kPa (' in pre:                      # já convertido — não mexer
            continue
        op, val = m.group(1), m.group(2)
        kpa = sigfig(float(val) * 101.325)
        out.append(text[last:m.start()])
        out.append(f"{op}{kpa} kPa ({op}{val} atm)")
        last = m.end()
    out.append(text[last:])
    return ''.join(out)

stats = {'aldrin':0,'hema':0,'carbo':0,'lpe':0,'lpe_pl':0,'header':0,'dec':0,'atm':0}
atm_samples = []

for f in files:
    s = open(f).read()
    o = s
    # 1) Aldrim -> Aldrin
    n=s.count('Aldrim'); s=s.replace('Aldrim','Aldrin'); stats['aldrin']+=n
    # 2) hemoglobinúria -> hematúria (Arsina; única ocorrência no doc)
    n=s.count('hemoglobinúria'); s=s.replace('hemoglobinúria','hematúria'); stats['hema']+=n
    # 6) carbeto -> carboneto (Carbeto/carbeto)
    n=len(re.findall('arbeto',s)); s=s.replace('arbeto','arboneto'); stats['carbo']+=n
    # 5) Apêndice G: LPEs->PELs, LPE->PEL (palavra), cabeçalho de coluna
    n=len(re.findall(r'\bLPEs\b',s)); s=re.sub(r'\bLPEs\b','PELs',s); stats['lpe_pl']+=n
    n=len(re.findall(r'\bLPE\b',s)); s=re.sub(r'\bLPE\b','PEL',s); stats['lpe']+=n
    n=s.count('| Produto Químico |'); s=s.replace('| Produto Químico |','| Substância Química |'); stats['header']+=n
    # 7) atm -> kPa (antes do decimal, p/ casar valores com ponto; valores com vírgula tratados depois)
    #    fazemos decimal primeiro para uniformizar, depois atm:
    # 3) decimal vírgula -> ponto (locant-safe)
    stats['dec'] += len(DEC.findall(s)); s = DEC.sub(lambda m:m.group(1)+'.'+m.group(2), s)
    # atm
    before_atm = s
    s = conv_atm(s)
    # contar atm convertidos
    stats['atm'] += len(re.findall(r'kPa \([<>≥≤]?\d', s)) - len(re.findall(r'kPa \([<>≥≤]?\d', before_atm))
    if mode=='apply' and s!=o:
        open(f,'w').write(s)

print("MODO:", mode)
for k,v in stats.items(): print(f"  {k}: {v}")
# amostra de atm convertidos
print("\n=== amostra atm convertidos ===")
shown=0
for f in files:
    for ln in open(f):
        if shown>=12: break
        ln2=conv_atm(DEC.sub(lambda m:m.group(1)+'.'+m.group(2),ln))
        for m in re.finditer(r"[<>≥≤]?\d[\d.]* kPa \([<>≥≤]?\d[\d.]* atm\)", ln2):
            print("  ",m.group(0)); shown+=1
            if shown>=12: break
