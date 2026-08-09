# -*- coding: utf-8 -*-
"""Biblioteca 'cadeia' -- importar com: importar Cadeia  (uso: cadeia.comprimento(s), ...)"""

NOME = "cadeia"
CABECALHO = ""

FUNCOES = {
    "comprimento": (
        ["cadeia"], "inteiro",
        "def cadeia_comprimento(s):\n    return len(s)\n",
    ),
    "maiusculas": (
        ["cadeia"], "cadeia",
        "def cadeia_maiusculas(s):\n    return s.upper()\n",
    ),
    "minusculas": (
        ["cadeia"], "cadeia",
        "def cadeia_minusculas(s):\n    return s.lower()\n",
    ),
    "inverter": (
        ["cadeia"], "cadeia",
        "def cadeia_inverter(s):\n    return s[::-1]\n",
    ),
    "subcadeia": (
        ["cadeia", "inteiro", "inteiro"], "cadeia",
        # 0-baseado; 'fim' é exclusivo, tal como as fatias (slices) do
        # Python. AL-21: ao contrário de uma slice normal do Python, 'ini'
        # /'fim' fora de [0, len(s)] dá erro amigável (_AlgoIndiceCadeiaInvalido,
        # a mesma mensagem que cadeia.caracter já usa), em vez de cortar
        # silenciosamente -- consistência entre as duas funções, e não
        # esconder um índice errado do estudante.
        "def cadeia_subcadeia(s, ini, fim):\n"
        "    if ini < 0 or ini > len(s) or fim < 0 or fim > len(s):\n"
        "        raise _AlgoIndiceCadeiaInvalido(f'{ini}:{fim}')\n"
        "    return s[ini:fim]\n",
    ),
    "caracter": (
        ["cadeia", "inteiro"], "caracter",
        # 0-baseado, tal como os arrays. Um índice fora dos limites dá
        # IndexError -- reencaminhado como _AlgoIndiceCadeiaInvalido (AL-09,
        # definida no cabeçalho de codegen.py) para a mensagem amigável
        # distinguir "posição de texto" de "posição de array".
        "def cadeia_caracter(s, i):\n"
        "    try:\n"
        "        return s[i]\n"
        "    except IndexError:\n"
        "        raise _AlgoIndiceCadeiaInvalido(i) from None\n",
    ),
}
