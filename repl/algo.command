#!/usr/bin/env bash
# Arranque do ALGO -- não precisas de ativar nenhum ambiente virtual à mão.
# Este script encontra (ou cria, na primeira vez) um venv na raiz do
# projeto (onde está o pyproject.toml), instala o pacote lá dentro se for
# preciso, e depois chama o 'algo' de dentro desse venv diretamente -- o
# mesmo resultado prático de "ativar" o ambiente, sem precisar de o
# ativar na tua shell.

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# Corre tanto daqui (repl/, dentro do repositório -- pyproject.toml
# um nível acima) como da raiz de um pacote distribuído a estudantes
# (empacotar.py copia este script para lá, ao lado do pyproject.toml).
if [ -f "$DIR/pyproject.toml" ]; then
    RAIZ="$DIR"
else
    RAIZ="$(cd "$DIR/.." && pwd)"
fi
VENV="$RAIZ/.venv"

if [ ! -x "$VENV/bin/algo" ]; then
    echo "Primeira utilização: a preparar o ambiente (só demora uns segundos)..."

    PYTHON=""
    for candidato in python3 python; do
        if command -v "$candidato" >/dev/null 2>&1; then
            PYTHON="$candidato"
            break
        fi
    done
    if [ -z "$PYTHON" ]; then
        echo "❌ Não encontrei o Python instalado. Instala o Python 3 (python.org) e tenta outra vez." >&2
        exit 1
    fi

    if ! "$PYTHON" -m venv "$VENV"; then
        echo "❌ Não foi possível criar o ambiente virtual (comando: $PYTHON -m venv)." >&2
        rm -rf "$VENV"
        exit 1
    fi

    if [ ! -x "$VENV/bin/pip" ]; then
        echo "❌ O ambiente virtual foi criado, mas ficou sem o 'pip' lá dentro." >&2
        echo "   Em sistemas Debian/Ubuntu isto costuma acontecer quando falta o" >&2
        echo "   pacote 'python3-venv'. Tenta:" >&2
        echo "     sudo apt install python3-venv" >&2
        echo "   e depois corre este script outra vez." >&2
        rm -rf "$VENV"
        exit 1
    fi

    if ! "$VENV/bin/pip" install --quiet --upgrade pip; then
        echo "❌ Não foi possível atualizar o pip dentro do ambiente virtual." >&2
        rm -rf "$VENV"
        exit 1
    fi

    if ! "$VENV/bin/pip" install --quiet -e "$RAIZ"; then
        echo "❌ Não foi possível instalar o ALGO (pip install -e \"$RAIZ\")." >&2
        echo "   Confirma que esta pasta tem mesmo o ficheiro pyproject.toml." >&2
        rm -rf "$VENV"
        exit 1
    fi

    echo "Ambiente preparado."
    echo
fi

exec "$VENV/bin/algo" "$@"
