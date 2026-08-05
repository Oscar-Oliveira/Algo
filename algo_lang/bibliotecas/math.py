# -*- coding: utf-8 -*-
"""Biblioteca 'math' -- importar com: importar Math  (uso: math.raiz(x), ...)"""

NOME = "math"
CABECALHO = "import math as _math\nimport random as _random\n"

# nome_metodo -> (categorias_dos_argumentos, tipo_de_retorno, codigo_python)
# categorias: "numeric" | "inteiro" | "cadeia"
FUNCOES = {
    "raiz": (
        ["numeric"], "decimal",
        "def math_raiz(x):\n    return _math.sqrt(x)\n",
    ),
    "potencia": (
        ["numeric", "numeric"], "decimal",
        "def math_potencia(base, exp):\n    return base ** exp\n",
    ),
    "absoluto": (
        ["numeric"], "decimal",
        "def math_absoluto(x):\n    return abs(x)\n",
    ),
    "piso": (
        ["numeric"], "inteiro",
        "def math_piso(x):\n    return _math.floor(x)\n",
    ),
    "teto": (
        ["numeric"], "inteiro",
        "def math_teto(x):\n    return _math.ceil(x)\n",
    ),
    "aleatorio": (
        ["inteiro", "inteiro"], "inteiro",
        "def math_aleatorio(a, b):\n    return _random.randint(a, b)\n",
    ),
}
