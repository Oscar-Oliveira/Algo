# -*- coding: utf-8 -*-
"""Biblioteca 'matematica' -- importar com: importar Matematica  (uso: matematica.raiz(x), ...)"""

NOME = "matematica"
CABECALHO = "import math as _math\nimport random as _random\n"

# nome_metodo -> (categorias_dos_argumentos, tipo_de_retorno, codigo_python)
# categorias: "numeric" | "inteiro" | "cadeia"
FUNCOES = {
    "raiz": (
        ["numeric"], "decimal",
        "def matematica_raiz(x):\n    return _math.sqrt(x)\n",
    ),
    "potencia": (
        ["numeric", "numeric"], "decimal",
        # potencia() declara sempre retorno 'decimal', mas base**exp do
        # Python fica 'int' quando base e exp são ambos inteiros -- float()
        # garante que o valor devolvido corresponde ao tipo declarado.
        "def matematica_potencia(base, exp):\n    return float(base ** exp)\n",
    ),
    "absoluto": (
        # AL-19: "numeric" como tipo de retorno é um marcador especial --
        # devolve o mesmo tipo do argumento (ver semantics.py:
        # _verificar_chamada), não sempre 'decimal'.
        ["numeric"], "numeric",
        "def matematica_absoluto(x):\n    return abs(x)\n",
    ),
    "piso": (
        ["numeric"], "inteiro",
        "def matematica_piso(x):\n    return _math.floor(x)\n",
    ),
    "teto": (
        ["numeric"], "inteiro",
        "def matematica_teto(x):\n    return _math.ceil(x)\n",
    ),
    "aleatorio": (
        ["inteiro", "inteiro"], "inteiro",
        "def matematica_aleatorio(a, b):\n    return _random.randint(a, b)\n",
    ),
}
