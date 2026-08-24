# -*- coding: utf-8 -*-
"""Biblioteca 'conversao' -- importar com: importar Conversao
(uso: conversao.paraInteiro(x), ...). Converte entre os 5 tipos
primitivos da linguagem (inteiro, decimal, booleano, cadeia, caracter).

Todas as funções levantam sempre ValueError ou _AlgoErroAmigavel (nunca
outra exceção do Python) quando a conversão falha, para a mensagem de
erro mostrada ao estudante ser sempre a nossa, nunca um traceback cru
do Python. Os pontos que reaproveitam o texto nativo de um OverflowError
do Python usam ValueError puro para caírem na tabela de
_algo_traduzir_valueerro em codegen.py; o resto usa _AlgoErroAmigavel."""

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
        # -> faz parse (ValueError com texto inválido já é traduzido). Se
        # 'x' é texto e int() falha, cai para um parse manual da parte
        # inteira -- extraída e convertida diretamente com int(), nunca
        # passando por float() (que perdia precisão para números grandes).
        # Só reconhece o formato simples sinal?+dígitos*+.+dígitos* --
        # notação científica ("1e10") não é aceite.
        ["primitivo"], "inteiro",
        "def conversao_paraInteiro(x):\n"
        "    if isinstance(x, str) and \"_\" in x:\n"
        "        raise _AlgoErroAmigavel(f\"'{x}' não é um número inteiro válido\")\n"
        "    try:\n"
        "        return int(x)\n"
        "    except OverflowError as e:\n"
        "        raise ValueError(str(e)) from None\n"
        "    except ValueError as e:\n"
        "        if isinstance(x, str):\n"
        "            s = x.strip()\n"
        "            sinal = \"\"\n"
        "            if s[:1] in (\"+\", \"-\"):\n"
        "                sinal, s = s[0], s[1:]\n"
        "            if \".\" in s:\n"
        "                parte_inteira, parte_decimal = s.split(\".\", 1)\n"
        "                inteira_ok = parte_inteira == \"\" or parte_inteira.isdigit()\n"
        "                decimal_ok = parte_decimal == \"\" or parte_decimal.isdigit()\n"
        "                if inteira_ok and decimal_ok and (parte_inteira or parte_decimal):\n"
        "                    return int(sinal + (parte_inteira or \"0\"))\n"
        "        raise e\n",
    ),
    "paraDecimal": (
        # Ao contrário de 'ler()', esta função aceita nan/inf/-inf/
        # Infinity de propósito -- é o único ponto do ALGO por onde um
        # programa pode construir esses valores.
        ["primitivo"], "decimal",
        "def conversao_paraDecimal(x):\n"
        "    if isinstance(x, str) and \"_\" in x:\n"
        "        raise _AlgoErroAmigavel(f\"'{x}' não é um número decimal válido\")\n"
        "    try:\n"
        "        return float(x)\n"
        "    except OverflowError as e:\n"
        "        raise ValueError(str(e)) from None\n",
    ),
    "paraBooleano": (
        # 'falso'/'f'/'false'/'não'/'nao'/'n'/'0' (com espaços/maiúsculas
        # à volta) -> falso; resto segue a truthiness nativa do Python
        # (0.0/"" -> falso, tudo o resto -> verdadeiro), que já cobre
        # 'verdadeiro' e qualquer outro texto não vazio. 'não'/'nao' têm
        # de estar na lista explicitamente: numa linguagem cujo
        # código-fonte é todo em português, a própria palavra "não" a
        # converter para 'verdadeiro' (por ser texto não vazio) era uma
        # armadilha, não só uma limitação da truthiness genérica. '0'
        # também está explícito: texto "0" é não-vazio (truthy nativo do
        # Python), mas é a forma mais comum doutros formatos (JSON,
        # variáveis de ambiente, CSV) de representar falso.
        ["primitivo"], "booleano",
        "def conversao_paraBooleano(x):\n"
        "    if isinstance(x, str) and x.strip().lower() in (\"falso\", \"f\", \"false\", \"não\", \"nao\", \"n\", \"0\"):\n"
        "        return False\n"
        "    return bool(x)\n",
    ),
    "paraCaracter": (
        ["cadeia"], "caracter",
        "def conversao_paraCaracter(t):\n"
        "    if len(t) != 1:\n"
        "        raise _AlgoErroAmigavel(\n"
        "            f\"'{t}' não pode ser convertido para caracter "
        "(tem de ter exatamente 1 caracter)\")\n"
        "    return t\n",
    ),
    "paraAscii": (
        ["caracter"], "inteiro",
        "def conversao_paraAscii(c):\n"
        "    if len(c) != 1:\n"
        "        raise _AlgoErroAmigavel(\n"
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
        "        raise _AlgoErroAmigavel(\n"
        "            f\"{i} não é um código de caracter válido\") from None\n",
    ),
}
