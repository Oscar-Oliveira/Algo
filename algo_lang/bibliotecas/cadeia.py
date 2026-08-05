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
        # 0-baseado; 'fim' é exclusivo, tal como as fatias (slices) do Python\n"
        "def cadeia_subcadeia(s, ini, fim):\n    return s[ini:fim]\n",
    ),
    "caracter": (
        ["cadeia", "inteiro"], "caracter",
        # 0-baseado, tal como os arrays. Um índice fora dos limites dá
        # IndexError, apanhado pelo mesmo tratamento amigável que já existe
        # para os arrays ("índice fora dos limites").
        "def cadeia_caracter(s, i):\n    return s[i]\n",
    ),
}
