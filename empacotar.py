#!/usr/bin/env python3
"""Empacota o ALGO (compilador, ferramentas, instalação, manual e exemplos)
num .zip autónomo, pronto a distribuir a estudantes -- sem alguem/, online/,
nem testes.

Uso: python3 empacotar.py
Produz: dist/algo-<versao>.zip
"""
import re
import shutil
import zipfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parent

# (origem relativa à raiz, destino relativo à raiz do pacote)
FICHEIROS = [
    "algo.sh",
    "algo.bat",
    "algo.command",
    "pyproject.toml",
    "docs/ManualCLI.md",
]
PASTAS = [
    ("algo_lang", {"tests", "__pycache__"}),
    ("docs/manual", {"__pycache__"}),
    ("exemplos", {"__pycache__"}),
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

- `docs/ManualCLI.md` -- manual do estudante: a consola interativa,
  todos os comandos (`algo executa`, `algo fluxograma`, `algo
  verifica`, ...), a extensão de realce de sintaxe para VS Code
  (`algo_lang/editors/vscode-algo/`), e instalação do Python à mão se
  o script de arranque não funcionar.
- `docs/manual/` -- manual da linguagem em si (tipos, condicionais,
  ciclos, vetores, funções, estruturas, bibliotecas, ...).
- `exemplos/` -- programas ALGO de exemplo, organizados por assunto.
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


def main() -> None:
    versao = obter_versao()
    nome_pacote = f"algo-{versao}"

    dist = RAIZ / "dist"
    pasta_pacote = dist / nome_pacote
    if pasta_pacote.exists():
        shutil.rmtree(pasta_pacote)
    pasta_pacote.mkdir(parents=True)

    for rel in FICHEIROS:
        origem = RAIZ / rel
        if not origem.exists():
            raise SystemExit(f"Falta o ficheiro esperado: {rel}")
        destino = pasta_pacote / rel
        destino.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(origem, destino)

    for rel, excluir in PASTAS:
        origem = RAIZ / rel
        if not origem.exists():
            raise SystemExit(f"Falta a pasta esperada: {rel}")
        copiar_pasta(origem, pasta_pacote / rel, excluir)

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
