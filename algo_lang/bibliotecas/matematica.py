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
        # AL-85/B13: mesma proteção que _algo_pot (codegen.py, AL-57/B16)
        # para o operador '^' -- sem isto, base negativa com expoente
        # fracionário faz 'base ** exp' devolver um 'complex', e
        # float(complex) levanta TypeError cru (não traduzido por
        # _algo_traduzir_valueerro, que só trata ValueError).
        "def matematica_potencia(base, exp):\n"
        "    if base < 0 and not float(exp).is_integer():\n"
        "        raise ValueError(\"negative number cannot be raised to a fractional power\")\n"
        "    return float(base ** exp)\n",
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
        # AL-86/B22: sem esta verificação, 'a > b' fazia _random.randint
        # levantar ValueError com o texto interno do Python ("empty range
        # in randrange(...)"), incluindo um número que não corresponde a
        # nenhum argumento escrito pelo estudante (é 'b+1', artefacto
        # interno do randrange) -- mensagem própria e clara em vez disso.
        "def matematica_aleatorio(a, b):\n"
        "    if a > b:\n"
        "        raise ValueError(\n"
        "            f\"o limite inferior ({a}) não pode ser maior do que o limite \"\n"
        "            f\"superior ({b})\")\n"
        "    return _random.randint(a, b)\n",
    ),
}
