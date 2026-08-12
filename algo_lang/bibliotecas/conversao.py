# -*- coding: utf-8 -*-
"""Biblioteca 'conversao' -- importar com: importar Conversao
(uso: conversao.paraInteiro(x), ...). Converte entre os 5 tipos
primitivos da linguagem (inteiro, decimal, booleano, cadeia, caracter).

Todas as funções levantam sempre ValueError (nunca outra exceção do
Python) quando a conversão falha, para a mensagem de erro mostrada ao
estudante ser sempre a nossa (traduzida por _algo_traduzir_valueerro em
codegen.py), nunca um traceback cru do Python."""

NOME = "conversao"
CABECALHO = ""

# nome_metodo -> (categorias_dos_argumentos, tipo_de_retorno, codigo_python)
# categorias: "numeric" | "inteiro" | "cadeia" | "caracter" | "primitivo"
FUNCOES = {
    "paraTexto": (
        ["primitivo"], "cadeia",
        "def conversao_paraTexto(x):\n    return _algo_fmt(x)\n",
    ),
    "paraInteiro": (
        # bool -> 0/1; decimal -> trunca em direção a zero; cadeia/caracter
        # -> faz parse (ValueError com texto inválido já é traduzido).
        ["primitivo"], "inteiro",
        "def conversao_paraInteiro(x):\n"
        "    try:\n"
        "        return int(x)\n"
        "    except OverflowError as e:\n"
        "        raise ValueError(str(e)) from None\n",
    ),
    "paraDecimal": (
        ["primitivo"], "decimal",
        "def conversao_paraDecimal(x):\n"
        "    try:\n"
        "        return float(x)\n"
        "    except OverflowError as e:\n"
        "        raise ValueError(str(e)) from None\n",
    ),
    "paraBooleano": (
        # 'falso'/'f'/'false' (com espaços/maiúsculas à volta) -> falso;
        # resto segue a truthiness nativa do Python (0/0.0/"" -> falso,
        # tudo o resto -> verdadeiro), que já cobre 'verdadeiro' e
        # qualquer outro texto não vazio.
        ["primitivo"], "booleano",
        "def conversao_paraBooleano(x):\n"
        "    if isinstance(x, str) and x.strip().lower() in (\"falso\", \"f\", \"false\"):\n"
        "        return False\n"
        "    return bool(x)\n",
    ),
    "paraCaracter": (
        ["cadeia"], "caracter",
        "def conversao_paraCaracter(t):\n"
        "    if len(t) != 1:\n"
        "        raise ValueError(\n"
        "            f\"'{t}' não pode ser convertido para caracter "
        "(tem de ter exatamente 1 caracter)\")\n"
        "    return t\n",
    ),
    "paraAscii": (
        ["caracter"], "inteiro",
        "def conversao_paraAscii(c):\n"
        "    if len(c) != 1:\n"
        "        raise ValueError(\n"
        "            f\"'{c}' não é um caracter válido "
        "(esperava-se exatamente 1 caracter)\")\n"
        "    return ord(c)\n",
    ),
    "deAscii": (
        ["inteiro"], "caracter",
        "def conversao_deAscii(i):\n"
        "    try:\n"
        "        return chr(i)\n"
        "    except ValueError:\n"
        "        raise ValueError(\n"
        "            f\"{i} não é um código de caracter válido\") from None\n",
    ),
}
