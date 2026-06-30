# NIOSH — Guia de bolso de riscos químicos (tradução PT-BR)

Tradução para português do Brasil do *NIOSH Pocket Guide to Chemical Hazards*
(DHHS/NIOSH, publicação nº 2005-149, 3ª impressão).

**Site:** https://joaoricardo000.github.io/niosh/

## Sobre
- Tradução das ~677 fichas de substâncias + tabelas, apêndices e índices.
- Medidas convertidas para o sistema métrico (°F→°C, mmHg→kPa, atm→kPa), com o original entre parênteses.
- Nomes químicos em PT-BR com o nome em inglês entre parênteses; fórmulas, CAS#, RTECS#, DOT# e códigos de respirador/medição mantidos no original.
- Leitor web (busca com autocomplete, tabelas em modal, PWA instalável) + PDF.

> ⚠️ Tradução automática — revisão recomendada para uso crítico (resposta a
> emergência, decisões de segurança). Confira a fonte oficial:
> https://www.cdc.gov/niosh/npg/

## Estrutura
- `docs/` — site publicado (GitHub Pages): `index.html`, `livro.html`, PWA, PDFs.
- `translation/` — `Niosh-pt-BR.md` (markdown único), `chunks/` (fonte da tradução), `glossary.md`.
- `scripts/` — geração do site/PDF (`build_html.py`, `build_pdf.py`, `niosh_render.py`) e pipeline (`convert_units.py`, `fix_review.py`).
- `source/` — PDF original em inglês (domínio público).

## Reproduzir
```bash
python3 -m venv venv && ./venv/bin/pip install markdown pymupdf weasyprint
./venv/bin/python scripts/build_html.py                 # gera docs/ a partir de translation/chunks
./venv/bin/python scripts/build_pdf.py translation/Niosh-pt-BR.md docs/Niosh-pt-BR.pdf
```

## Licença
- Tradução, site e código: **CC0 1.0** (domínio público) — ver `LICENSE`.
- *NIOSH Pocket Guide* original: domínio público do governo dos EUA.
