#!/usr/bin/env python3
"""Gera PDFs do manual, dos slides das aulas e das fichas de trabalho, a
partir do Markdown em docs/, usando o Chrome/Edge instalado em modo headless.

Uso: py gerar_pdfs.py
Requer: markdown-it-py (pip install markdown-it-py) e Chrome ou Edge instalados.
Produz: dist/docs/manual.pdf, dist/docs/aulas/*.pdf, dist/docs/fichas/*.pdf
"""
from __future__ import annotations

import re
import shutil
import subprocess
import tempfile
from pathlib import Path

from markdown_it import MarkdownIt

RAIZ = Path(__file__).resolve().parent
PASTA_AULAS = RAIZ / "docs" / "aulas"
PASTA_FICHAS = PASTA_AULAS / "fichas"
PASTA_MANUAL = RAIZ / "docs" / "manuais" / "manual"
DESTINO = RAIZ / "dist" / "docs"
PADRAO_NUMERADO = "[0-9][0-9]-*.md"

md = MarkdownIt("gfm-like")

CSS_BASE = """
body { font-family: "Segoe UI", Arial, sans-serif; color: #1c1c1c; margin: 0; }
h1, h2, h3 { color: #1c1c1c; }
h1 { font-size: 1.8em; } h2 { font-size: 1.4em; } h3 { font-size: 1.15em; }
code { font-family: Consolas, "Courier New", monospace; }
pre { background: #1e1e1e; color: #f2f2f2; padding: 0.6em 0.8em; border-radius: 4px;
      overflow-wrap: break-word; white-space: pre-wrap; }
pre code { background: none; padding: 0; }
img, svg { max-width: 100%; height: auto; }
table { border-collapse: collapse; width: 100%; }
th, td { border: 1px solid #ccc; padding: 0.3em 0.6em; text-align: left; }
"""

CSS_MANUAL = CSS_BASE + """
@page { size: A4; margin: 20mm 18mm; }
.capitulo:not(:first-child) { page-break-before: always; }
"""

CSS_FICHA = CSS_BASE + """
@page { size: A4; margin: 20mm 18mm; }
"""

# Tamanho 16:9 em A4 (297x167mm) para aproximar o rácio dos slides reveal.js.
CSS_SLIDES = CSS_BASE + """
@page { size: 297mm 167mm; margin: 14mm 18mm; }
.slide {
    page-break-before: always;
    min-height: calc(167mm - 28mm);
    display: flex;
    flex-direction: column;
    justify-content: center;
}
.slide:first-child { page-break-before: avoid; }
.slide img, .slide svg { max-height: 55vh; display: block; margin: 0 auto; }
"""


def encontrar_navegador() -> str:
    candidatos = [
        shutil.which("chrome"),
        shutil.which("google-chrome"),
        shutil.which("msedge"),
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        "/usr/bin/google-chrome",
        "/usr/bin/chromium-browser",
        "/usr/bin/microsoft-edge",
    ]
    for candidato in candidatos:
        if candidato and Path(candidato).exists():
            return candidato
    raise SystemExit("Não encontrei Chrome nem Edge instalados -- necessários para gerar PDF.")


def html_para_pdf(navegador: str, html_path: Path, pdf_path: Path) -> None:
    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    resultado = subprocess.run(
        [
            navegador, "--headless=new", "--disable-gpu", "--no-pdf-header-footer",
            f"--print-to-pdf={pdf_path}", html_path.as_uri(),
        ],
        capture_output=True, text=True,
    )
    if resultado.returncode != 0:
        raise SystemExit(f"Falha ao gerar {pdf_path}:\n{resultado.stderr}")


def envolver_html(titulo: str, corpo: str, css: str, base_dir: Path) -> str:
    return (
        '<!doctype html><html lang="pt"><head><meta charset="utf-8">'
        f'<base href="{base_dir.as_uri()}/">'
        f"<title>{titulo}</title><style>{css}</style></head>"
        f"<body>{corpo}</body></html>"
    )


def inserir_svgs_inline(html: str, base_dir: Path) -> str:
    """Substitui <img src="...svg"> pelo conteúdo <svg> inline: o Chrome
    headless, em modo --print-to-pdf, falha silenciosamente a incorporar
    imagens SVG carregadas via <img src>, mas desenha SVG inline sem
    problemas (fica como vetor no PDF, em vez de rasterizado)."""

    def substituir(correspondencia: re.Match) -> str:
        origem = correspondencia.group(1)
        if not origem.lower().endswith(".svg"):
            return correspondencia.group(0)
        caminho = base_dir / origem
        if not caminho.exists():
            return correspondencia.group(0)
        conteudo = caminho.read_text(encoding="utf-8")
        conteudo = re.sub(r"<\?xml[^>]*\?>", "", conteudo)
        conteudo = re.sub(r"<!DOCTYPE[^>]*>", "", conteudo, flags=re.S)
        return conteudo

    return re.sub(r'<img[^>]*\bsrc="([^"]+)"[^>]*/?>', substituir, html)


def dividir_slides(texto: str) -> list[str]:
    """Remove o front matter YAML (theme/customTheme) e devolve os blocos
    entre separadores '---', que no reveal.js marcam cada slide horizontal."""
    linhas = texto.splitlines()
    fim_cabecalho = next(i for i in range(1, len(linhas)) if linhas[i].strip() == "---")
    resto = "\n".join(linhas[fim_cabecalho + 1:])
    return [bloco.strip() for bloco in re.split(r"(?m)^---$", resto) if bloco.strip()]


def gerar_manual(navegador: str, tmp: Path) -> None:
    ficheiros = sorted(PASTA_MANUAL.glob(PADRAO_NUMERADO))
    corpo = "".join(
        f'<section class="capitulo">{md.render(f.read_text(encoding="utf-8"))}</section>'
        for f in ficheiros
    )
    corpo = inserir_svgs_inline(corpo, PASTA_MANUAL)
    html_path = tmp / "manual.html"
    html_path.write_text(envolver_html("Manual ALGO", corpo, CSS_MANUAL, PASTA_MANUAL), encoding="utf-8")
    html_para_pdf(navegador, html_path, DESTINO / "manual.pdf")
    print(f"  manual.pdf ({len(ficheiros)} capítulos)")


def gerar_aulas(navegador: str, tmp: Path) -> None:
    for f in sorted(PASTA_AULAS.glob(PADRAO_NUMERADO)):
        slides = dividir_slides(f.read_text(encoding="utf-8"))
        corpo = "".join(f'<section class="slide">{md.render(s)}</section>' for s in slides)
        corpo = inserir_svgs_inline(corpo, PASTA_AULAS)
        html_path = tmp / f"aula-{f.stem}.html"
        html_path.write_text(envolver_html(f.stem, corpo, CSS_SLIDES, PASTA_AULAS), encoding="utf-8")
        html_para_pdf(navegador, html_path, DESTINO / "aulas" / f"{f.stem}.pdf")
        print(f"  aulas/{f.stem}.pdf ({len(slides)} slides)")


def gerar_fichas(navegador: str, tmp: Path) -> None:
    for f in sorted(PASTA_FICHAS.glob(PADRAO_NUMERADO)):
        corpo = md.render(f.read_text(encoding="utf-8"))
        corpo = inserir_svgs_inline(corpo, PASTA_FICHAS)
        html_path = tmp / f"ficha-{f.stem}.html"
        html_path.write_text(envolver_html(f.stem, corpo, CSS_FICHA, PASTA_FICHAS), encoding="utf-8")
        html_para_pdf(navegador, html_path, DESTINO / "fichas" / f"{f.stem}.pdf")
        print(f"  fichas/{f.stem}.pdf")


def main() -> None:
    navegador = encontrar_navegador()
    DESTINO.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp_str:
        tmp = Path(tmp_str)
        print("A gerar manual...")
        gerar_manual(navegador, tmp)
        print("A gerar slides das aulas...")
        gerar_aulas(navegador, tmp)
        print("A gerar fichas de trabalho...")
        gerar_fichas(navegador, tmp)
    print(f"\nPDFs gerados em {DESTINO}")


if __name__ == "__main__":
    main()
