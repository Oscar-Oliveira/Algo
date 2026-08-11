# -*- coding: utf-8 -*-
"""Gera o "modo" do CodeMirror (destaque de sintaxe) para o ALGO,
diretamente a partir das palavras-chave reais do compilador -- em vez
de manter uma lista escrita à mão que poderia desatualizar-se, o mesmo
princípio já usado em alguem/nucleo/conhecimento_algo.py."""
from __future__ import annotations

import json
import sys
import os
import warnings

_RAIZ_PROJETO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _RAIZ_PROJETO not in sys.path:
    sys.path.insert(0, _RAIZ_PROJETO)

from algo_lang.compilador.lexer import PALAVRAS_CHAVE
from algo_lang.compilador.semantics import NUMERICOS, TEXTUAIS

_PALAVRAS_ACAO = {
    "escrever", "ler", "devolver", "fazer", "escolher", "importar",
    "incluir", "afirmar", "para", "de", "ate", "passo", "enquanto",
    "se", "entao", "senao", "caso", "contrario", "funcao", "procedimento",
    "ref", "constante", "estrutura", "algoritmo", "inicio",
}
_PALAVRAS_LOGICAS = {"e", "ou", "nao", "div", "mod"}
_TIPOS = sorted(NUMERICOS | TEXTUAIS | {"booleano"})
_LITERAIS_LOGICOS = {"verdadeiro", "falso"}

_PALAVRAS_NAO_CLASSIFICADAS = PALAVRAS_CHAVE - _PALAVRAS_ACAO - _PALAVRAS_LOGICAS - _LITERAIS_LOGICOS
# Se o compilador ganhar uma palavra-chave nova que este ficheiro ainda
# não sabe classificar, cai para "acao" por omissão -- feio mas
# inofensivo (destaque a mais, não código a menos). ON-37: antes disto
# era só "imediatamente visível ao rever o ficheiro" -- na prática,
# ninguém revê este ficheiro sempre que o lexer muda. Agora avisa
# explicitamente, para o fallback silencioso não passar despercebido.
if _PALAVRAS_NAO_CLASSIFICADAS:
    warnings.warn(
        f"modo_codemirror: {len(_PALAVRAS_NAO_CLASSIFICADAS)} palavra(s)-chave "
        f"não classificada(s) ({', '.join(sorted(_PALAVRAS_NAO_CLASSIFICADAS))}) -- "
        f"a cair para a categoria 'acao' por omissão. Classifica-a(s) "
        f"explicitamente em _PALAVRAS_ACAO ou _PALAVRAS_LOGICAS.", stacklevel=2)


def gerar_js_modo() -> str:
    todas_acao = sorted((_PALAVRAS_ACAO | _PALAVRAS_NAO_CLASSIFICADAS))
    return f"""\
// Gerado a partir das palavras-chave reais do compilador do ALGO --
// ver online/modo_codemirror.py. Não editar à mão.
CodeMirror.defineSimpleMode("algo", {{
  start: [
    {{regex: /\\/\\/.*/, token: "comment"}},
    {{regex: /\\/\\*/, token: "comment", next: "comentario"}},
    {{regex: /"(?:[^"\\\\]|\\\\.)*"/, token: "string"}},
    {{regex: /\\b\\d+\\.\\d+\\b/, token: "number"}},
    {{regex: /\\b\\d+\\b/, token: "number"}},
    {{regex: /\\b({"|".join(_TIPOS)})\\b/, token: "type"}},
    {{regex: /\\b({"|".join(sorted(_LITERAIS_LOGICOS))})\\b/, token: "atom"}},
    {{regex: /\\b({"|".join(sorted(_PALAVRAS_LOGICAS))})\\b/, token: "operator"}},
    {{regex: /\\b({"|".join(todas_acao)})\\b/, token: "keyword"}},
    {{regex: /==|<>|<=|>=|=|<|>|\\+|-|\\*|\\//, token: "operator"}},
    {{regex: /[a-zA-Z_][a-zA-Z0-9_]*/, token: "variable"}},
  ],
  comentario: [
    {{regex: /.*?\\*\\//, token: "comment", next: "start"}},
    {{regex: /.*/, token: "comment"}},
  ],
  meta: {{lineComment: "//"}},
}});
"""


if __name__ == "__main__":  # pragma: no cover -- só para inspeção manual
    print(gerar_js_modo())
