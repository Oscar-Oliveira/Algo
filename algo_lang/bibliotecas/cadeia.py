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
        # Python. 'ini'/'fim' fora de [0, len(s)] dá erro amigável em vez de
        # cortar silenciosamente.
        "def cadeia_subcadeia(s, ini, fim):\n"
        "    if ini < 0 or ini > len(s) or fim < 0 or fim > len(s):\n"
        "        raise _AlgoIndiceCadeiaInvalido(f'{ini}:{fim}')\n"
        "    if ini > fim:\n"
        # _AlgoErroAmigavel (não ValueError): a mensagem já é português
        # final, não deve ser reembrulhada.
        "        raise _AlgoErroAmigavel(\n"
        "            f'o início ({ini}) não pode ser maior do que o fim ({fim})')\n"
        "    return s[ini:fim]\n",
    ),
    "caracter": (
        ["cadeia", "inteiro"], "caracter",
        # 0-baseado, tal como os vetores e tal como 'subcadeia' (abaixo).
        "def cadeia_caracter(s, i):\n"
        "    if i < 0 or i >= len(s):\n"
        "        raise _AlgoIndiceCadeiaInvalido(i)\n"
        "    return s[i]\n",
    ),
    "procurar": (
        # Devolve o índice (0-baseado) da primeira ocorrência de 'sub' em
        # 's', ou -1 se não encontrado -- convenção comum (ex.: 'indexOf'),
        # não um erro: "não encontrado" é um resultado normal, não uma
        # situação excecional. 'sub' vazio é rejeitado explicitamente --
        # str.find do Python com um texto vazio "encontra-o" em toda a
        # posição (devolve sempre 0), um resultado surpreendente sem
        # valor pedagógico, mesma cautela que 'substituir'/'dividir' já
        # têm para o caso análogo.
        ["cadeia", "cadeia"], "inteiro",
        "def cadeia_procurar(s, sub):\n"
        "    if sub == \"\":\n"
        "        raise _AlgoErroAmigavel(\"o texto a procurar não pode ser vazio\")\n"
        "    return s.find(sub)\n",
    ),
    "substituir": (
        ["cadeia", "cadeia", "cadeia"], "cadeia",
        # Substitui TODAS as ocorrências de 'antigo' por 'novo'. 'antigo'
        # vazio é rejeitado explicitamente -- str.replace do Python com um
        # separador vazio insere 'novo' entre cada caracter de 's' (e antes
        # do primeiro/depois do último), um resultado surpreendente sem
        # valor pedagógico, mesma cautela que 'subcadeia'/'aleatorio' já
        # têm para os seus próprios casos extremos.
        "def cadeia_substituir(s, antigo, novo):\n"
        "    if antigo == \"\":\n"
        "        raise _AlgoErroAmigavel(\"o texto a substituir não pode ser vazio\")\n"
        "    return s.replace(antigo, novo)\n",
    ),
    "dividir": (
        # Divide 's' em partes separadas por 'sep', devolvendo um vetor de
        # cadeia -- 1º uso de uma função de biblioteca a devolver vetor
        # (ver o 4º elemento do tuplo, dims_retorno=1, documentado em
        # bibliotecas/__init__.py). 'sep' vazio é rejeitado explicitamente
        # (mensagem própria em vez do ValueError cru do Python para
        # str.split("")).
        ["cadeia", "cadeia"], "cadeia",
        "def cadeia_dividir(s, sep):\n"
        "    if sep == \"\":\n"
        "        raise _AlgoErroAmigavel(\"o separador não pode ser vazio\")\n"
        "    return s.split(sep)\n",
        1,
    ),
}
