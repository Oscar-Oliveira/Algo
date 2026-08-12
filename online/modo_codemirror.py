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
//
// StreamLanguage do CodeMirror 6 (ver /estatico/vendor/codemirror6/):
// a mesma ideia do antigo defineSimpleMode do CM5 -- token() é chamado
// repetidamente a partir da posição atual, testa cada categoria por
// ordem e devolve um nome de estilo -- mas escrita à mão em vez de
// declarativa, porque o CM6 não tem equivalente ao defineSimpleMode.
window.algoLanguage = CM6.StreamLanguage.define({{
  startState() {{
    return {{dentroComentario: false}};
  }},
  token(stream, state) {{
    if (state.dentroComentario) {{
      if (stream.match(/.*?\\*\\//)) {{
        state.dentroComentario = false;
      }} else {{
        stream.skipToEnd();
      }}
      return "comment";
    }}
    if (stream.match("//")) {{ stream.skipToEnd(); return "comment"; }}
    if (stream.match("/*")) {{ state.dentroComentario = true; return "comment"; }}
    if (stream.match(/"(?:[^"\\\\]|\\\\.)*"/)) return "string";
    if (stream.match(/\\d+\\.\\d+\\b/)) return "number";
    if (stream.match(/\\d+\\b/)) return "number";
    if (stream.match(/({"|".join(_TIPOS)})\\b/)) return "type";
    if (stream.match(/({"|".join(sorted(_LITERAIS_LOGICOS))})\\b/)) return "atom";
    if (stream.match(/({"|".join(sorted(_PALAVRAS_LOGICAS))})\\b/)) return "operator";
    if (stream.match(/({"|".join(todas_acao)})\\b/)) return "keyword";
    if (stream.match(/==|<>|<=|>=|=|<|>|\\+|-|\\*|\\//)) return "operator";
    if (stream.match(/[a-zA-Z_][a-zA-Z0-9_]*/)) return "variableName";
    stream.next();
    return null;
  }},
  languageData: {{
    commentTokens: {{line: "//", block: {{open: "/*", close: "*/"}}}},
  }},
}});
"""


if __name__ == "__main__":  # pragma: no cover -- só para inspeção manual
    print(gerar_js_modo())
