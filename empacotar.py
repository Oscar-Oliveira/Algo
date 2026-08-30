#!/usr/bin/env python3
"""Empacota o ALGO (compilador, ferramentas, instalação, manual e exemplos)
num .zip autónomo, pronto a distribuir a estudantes -- sem alguem/, online/,
nem testes.

Uso: python3 empacotar.py
Produz: dist/algo-<versao>.zip
"""
import os
import re
import shutil
import subprocess
import zipfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
PASTA_EXTENSAO = RAIZ / "editores" / "vscode-algo"

# (origem relativa à raiz, destino relativo à raiz do pacote) -- os
# scripts de arranque vivem em instaladores/ no repositório, mas saem
# soltos na raiz do pacote, para o estudante continuar a fazer
# duplo-clique sem abrir subpastas.
FICHEIROS = [
    ("instaladores/algo.sh", "algo.sh"),
    ("instaladores/algo.bat", "algo.bat"),
    ("instaladores/algo.command", "algo.command"),
    ("docs/manuais/ManualCLI.md", "docs/manuais/ManualCLI.md"),
]
PASTAS = [
    ("algo_lang", {"tests", "__pycache__"}),
    ("docs/exemplos", {"__pycache__"}),
]

README_PACOTE = """\
# ALGO

Linguagem algorítmica em português (pseudocódigo estruturado,
executável), para aprender programação.

## Instalar e abrir a consola

```bash
./algo.sh        # Linux/macOS -- ./algo.command também funciona no macOS
algo.bat         # Windows
```

Na primeira utilização, o script cria um ambiente virtual Python ao
lado dele próprio e instala o ALGO lá dentro -- não precisas de nada
instalado à mão, além do próprio Python 3. Depois disso, abre
diretamente a consola interativa.

## A seguir

- `docs/manuais/ManualCLI.md` -- manual do estudante: a consola interativa,
  todos os comandos (`algo executa`, `algo fluxograma`, `algo
  verifica`, ...), a extensão de realce de sintaxe para VS Code
  (`algo-language-*.vsix`, na raiz deste pacote), e instalação do
  Python à mão se o script de arranque não funcionar.
- `docs/exemplos/` -- programas ALGO de exemplo, organizados por assunto.
"""

# pyproject.toml mínimo para o pacote distribuído -- só o necessário para
# o "pip install -e" que instaladores/algo.sh faz. O pyproject.toml do
# repositório tem secções de desenvolvimento (dev deps, pytest, mutmut)
# que não fazem sentido no pacote do estudante.
PYPROJECT_PACOTE = """\
[build-system]
requires = ["setuptools>=61.0"]
build-backend = "setuptools.build_meta"

[project]
name = "algo-lang"
version = "{versao}"
description = "Compilador de uma linguagem algorítmica (em português) para Python, para ensino de programação"
requires-python = ">=3.8"

[project.scripts]
algo = "algo_lang.cli:main"

[tool.setuptools]
packages = ["algo_lang", "algo_lang.compilador", "algo_lang.tools", "algo_lang.bibliotecas"]
"""


def obter_versao() -> str:
    texto = (RAIZ / "pyproject.toml").read_text(encoding="utf-8")
    m = re.search(r'^version\s*=\s*"([^"]+)"', texto, re.MULTILINE)
    if not m:
        raise SystemExit("Não encontrei 'version' em pyproject.toml.")
    return m.group(1)


def copiar_pasta(origem: Path, destino: Path, excluir: set[str]) -> None:
    def ignorar(_dir: str, nomes: list[str]) -> set[str]:
        return {n for n in nomes if n in excluir or n.endswith(".pyc")}

    shutil.copytree(origem, destino, ignore=ignorar)


def gerar_vsix(destino: Path) -> None:
    vsce = shutil.which("vsce")
    if not vsce:
        raise SystemExit(
            "'vsce' não encontrado no PATH -- instala com 'npm install -g "
            "@vscode/vsce' para poder empacotar a extensão VS Code."
        )
    subprocess.run(
        [vsce, "package", "--out", f"{destino}{os.sep}"],
        cwd=PASTA_EXTENSAO,
        check=True,
    )


def main() -> None:
    versao = obter_versao()
    nome_pacote = f"algo-{versao}"

    dist = RAIZ / "dist"
    pasta_pacote = dist / nome_pacote
    if pasta_pacote.exists():
        shutil.rmtree(pasta_pacote)
    pasta_pacote.mkdir(parents=True)

    for origem_rel, destino_rel in FICHEIROS:
        origem = RAIZ / origem_rel
        if not origem.exists():
            raise SystemExit(f"Falta o ficheiro esperado: {origem_rel}")
        destino = pasta_pacote / destino_rel
        destino.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(origem, destino)

    (pasta_pacote / "pyproject.toml").write_text(
        PYPROJECT_PACOTE.format(versao=versao), encoding="utf-8"
    )

    for rel, excluir in PASTAS:
        origem = RAIZ / rel
        if not origem.exists():
            raise SystemExit(f"Falta a pasta esperada: {rel}")
        copiar_pasta(origem, pasta_pacote / rel, excluir)

    gerar_vsix(pasta_pacote)

    (pasta_pacote / "README.md").write_text(README_PACOTE, encoding="utf-8")

    caminho_zip = dist / f"{nome_pacote}.zip"
    if caminho_zip.exists():
        caminho_zip.unlink()
    with zipfile.ZipFile(caminho_zip, "w", zipfile.ZIP_DEFLATED) as zf:
        for caminho in sorted(pasta_pacote.rglob("*")):
            if caminho.is_file():
                zf.write(caminho, caminho.relative_to(dist))

    print(f"Pacote criado: {caminho_zip.relative_to(RAIZ)}")


if __name__ == "__main__":
    main()
