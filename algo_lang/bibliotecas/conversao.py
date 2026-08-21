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
        # AL-65/B25: uma cadeia com ponto decimal (ex.: "3.5") caía direto
        # no ValueError de int() -- assimetria com um valor 'decimal'
        # (que já trunca sem erro nenhum). Cai para int(float(x)) só
        # quando 'x' é texto E o parse direto de int() falhou; se também
        # não for um número decimal válido, o ValueError original (e a
        # sua tradução) é preservado tal-e-qual.
        # AL-91/B21: 'x="inf"'/'"Infinity"' é um float válido (float(x) não
        # falha), mas int(float("inf")) levanta OverflowError -- sem o
        # apanhar aqui também, escapava deste 'except ValueError' (que só
        # trata ValueError) e propagava até ao wrapper genérico de
        # OverflowError em codegen.py, dando "overflow numérico", uma
        # mensagem enganadora para um texto que não é sequer um número.
        # AUDITORIA_2026-08-19 bug #43: int()/float() do Python aceitam
        # separadores '_' de milhar (ex.: "1_000") que o lexer de ALGO
        # não suporta -- rejeitado explicitamente antes de tentar
        # qualquer conversão.
        ["primitivo"], "inteiro",
        "def conversao_paraInteiro(x):\n"
        "    if isinstance(x, str) and \"_\" in x:\n"
        "        raise ValueError(f\"'{x}' não é um número inteiro válido\")\n"
        "    try:\n"
        "        return int(x)\n"
        "    except OverflowError as e:\n"
        "        raise ValueError(str(e)) from None\n"
        "    except ValueError as e:\n"
        "        if isinstance(x, str):\n"
        "            try:\n"
        "                return int(float(x))\n"
        "            except (ValueError, OverflowError):\n"
        "                pass\n"
        "        raise e\n",
    ),
    "paraDecimal": (
        # AUDITORIA_2026-08-19 bug #40 (investigado, não é bug): ao
        # contrário de 'ler()' (entrada interativa de um estudante, onde
        # 'nan'/'inf' é quase sempre um erro de digitação), esta função é
        # o ÚNICO ponto do próprio LEGO -- ALGO não tem literal nenhum
        # para infinito/nan no código-fonte -- por onde um programa pode
        # construir esses valores deliberadamente (ver
        # test_matematica_piso_de_infinito_da_overflow_amigavel e
        # test_conversao_parainteiro_de_infinito_da_erro_amigavel, que
        # dependem exatamente disto). matematica.piso/teto e
        # conversao.paraInteiro já traduzem o OverflowError resultante
        # para uma mensagem amigável -- por isso aceitar aqui não deixa
        # nenhum valor "perigoso" escapar sem aviso. Continua a rejeitar
        # separadores '_' de milhar (bug #43), que nunca têm uso
        # legítimo.
        ["primitivo"], "decimal",
        "def conversao_paraDecimal(x):\n"
        "    if isinstance(x, str) and \"_\" in x:\n"
        "        raise ValueError(f\"'{x}' não é um número decimal válido\")\n"
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
