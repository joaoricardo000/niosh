#!/usr/bin/env python3
import re, os, sys, glob, math

def f2c(f):
    return (f - 32.0) * 5.0 / 9.0

def fmt_c(f_val):
    c = f2c(f_val)
    # round to nearest integer degree C
    return f"{round(c)}"

_SUP = str.maketrans("0123456789-", "⁰¹²³⁴⁵⁶⁷⁸⁹⁻")

def _sci(r, sig):
    s = f"{r:.{sig-1}e}"            # e.g. 1.33e-05
    mant, exp = s.split('e')
    mant = mant.rstrip('0').rstrip('.')
    exp_i = int(exp)
    return f"{mant}×10{str(exp_i).translate(_SUP)}"

def sigfig(x, sig=3):
    if x == 0:
        return "0"
    d = math.ceil(math.log10(abs(x)))
    power = sig - d
    factor = 10 ** power
    r = round(x * factor) / factor
    if abs(r) != 0 and (abs(r) < 1e-3 or abs(r) >= 1e5):
        return _sci(r, sig)
    s = f"{r:.10f}".rstrip('0').rstrip('.')
    return s

# ---- Temperature: ranges first, then singles, in one pass via alternation ----
TEMP_RE = re.compile(r'(-?\d+)\s*-\s*(-?\d+)\s*°F|(-?\d+(?:\.\d+)?)\s*°F')

def temp_sub(m):
    if m.group(1) is not None:  # range A-B°F
        a = float(m.group(1)); b = float(m.group(2))
        ca = fmt_c(a); cb = fmt_c(b)
        return f"{ca}–{cb}°C ({m.group(1)}-{m.group(2)}°F)"
    else:  # single
        orig = m.group(3)
        v = float(orig)
        return f"{fmt_c(v)}°C ({orig}°F)"

# ---- Pressure mmHg -> kPa: ranges first then singles ----
MMHG_RE = re.compile(r'(\d+(?:\.\d+)?)\s*-\s*(\d+(?:\.\d+)?)\s*mmHg|(\d+(?:\.\d+)?)\s*mmHg')
KPA = 0.13332237

def mmhg_sub(m):
    if m.group(1) is not None:
        a = float(m.group(1)); b = float(m.group(2))
        return f"{sigfig(a*KPA)}–{sigfig(b*KPA)} kPa ({m.group(1)}-{m.group(2)} mmHg)"
    else:
        orig = m.group(3); v = float(orig)
        return f"{sigfig(v*KPA)} kPa ({orig} mmHg)"

def convert(text):
    text = TEMP_RE.sub(temp_sub, text)
    text = MMHG_RE.sub(mmhg_sub, text)
    text = text.replace('/m3', '/m³')  # mg/m3, g/m3 -> superscript (safe: unit only)
    return text

if __name__ == '__main__':
    mode = sys.argv[1] if len(sys.argv) > 1 else 'run'
    if mode == 'test':
        samples = [
            "BP: 309°F", "FRZ: -148°F [forms glass]", "BP: 5396°F", "MLT: 3632°F",
            "BP: 415-439°F", "Sp.Gr(59°F): 0.93", "VP: 2 mmHg", "VP: 0 mmHg (approx)",
            "VP: 760 mmHg", "VP: 0.0001 mmHg", "TWA 5 mg/m3", "20-55°F", "VP(77°F): 1 mmHg",
            "Conversion: 1 ppm = 4.67 mg/m3", "1220°F", "VP: 1.5-3 mmHg",
        ]
        for s in samples:
            print(repr(s), '->', repr(convert(s)))
    else:
        sp = sys.argv[2]
        src = f"{sp}/pages"; dst = f"{sp}/pages_conv"
        os.makedirs(dst, exist_ok=True)
        files = sorted(glob.glob(f"{src}/page_*.txt"))
        for fp in files:
            with open(fp) as fh:
                t = fh.read()
            with open(os.path.join(dst, os.path.basename(fp)), 'w') as fh:
                fh.write(convert(t))
        print("converted pages:", len(files), "->", dst)
