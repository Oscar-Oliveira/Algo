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
        # esconder um índice errado do estudante. 'ini > fim' (ambos dentro
        # dos limites) tem o mesmo cuidado que matematica.aleatorio já tem
        # para limites invertidos -- sem isto, devolvia "" em silêncio
        # (fatia do Python com início depois do fim), sem indicar ao
        # estudante que os dois argumentos estão trocados.
        "def cadeia_subcadeia(s, ini, fim):\n"
        "    if ini < 0 or ini > len(s) or fim < 0 or fim > len(s):\n"
        "        raise _AlgoIndiceCadeiaInvalido(f'{ini}:{fim}')\n"
        "    if ini > fim:\n"
        "        raise ValueError(\n"
        "            f'o início ({ini}) não pode ser maior do que o fim ({fim})')\n"
        "    return s[ini:fim]\n",
    ),
    "caracter": (
        ["cadeia", "inteiro"], "caracter",
        # 0-baseado, tal como os arrays e tal como 'subcadeia' (abaixo).
        # AL-64/B24: antes, um índice negativo não dava IndexError nenhum
        # -- s[-1] do Python devolve o último caracter em vez de levantar
        # erro, ao contrário de 'subcadeia', que já rejeita limites
        # negativos explicitamente. Guarda explícita, consistente com a
        # documentação da função ("0-baseado"), em vez de confiar no
        # comportamento (inconsistente) do índice nativo do Python.
        "def cadeia_caracter(s, i):\n"
        "    if i < 0 or i >= len(s):\n"
        "        raise _AlgoIndiceCadeiaInvalido(i)\n"
        "    return s[i]\n",
    ),
}
