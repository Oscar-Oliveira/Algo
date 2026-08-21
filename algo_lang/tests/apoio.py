# -*- coding: utf-8 -*-
"""Funções auxiliares partilhadas pelos testes do compilador ALGO."""
import subprocess
import sys
import textwrap

from algo_lang.compilador.parser import parse
from algo_lang.compilador.semantics import verificar
from algo_lang.compilador.codegen import gerar_python


def compilar(codigo_algo: str) -> str:
    """Compila uma string de código ALGO e devolve o código Python gerado.
    Lança as exceções do compilador (ErroLexico/ErroSintatico/ErroSemantico)
    se o programa for inválido -- útil para testar deteção de erros."""
    codigo_algo = textwrap.dedent(codigo_algo)
    programa = parse(codigo_algo)
    verificar(programa)
    return gerar_python(programa)


def executar(codigo_algo: str, entrada: str = "") -> str:
    """Compila e executa um programa ALGO, devolvendo o stdout produzido.

    AUDITORIA_2026-08-19 bug #25: 'encoding="utf-8"' explícito -- desde
    que o CABECALHO_RUNTIME gerado força sys.stdout para UTF-8
    (independentemente do ambiente), este processo (o pai, a correr os
    testes) tem de decodificar esse stdout como UTF-8 também, ou
    caracteres fora de ASCII (acentos, emoji) ficam mal decodificados
    quando o 'text=True' sem encoding explícito cai para a codificação
    por omissão do sistema (ex.: cp1252 no Windows)."""
    codigo_py = compilar(codigo_algo)
    resultado = subprocess.run(
        [sys.executable, "-c", codigo_py],
        input=entrada, capture_output=True, text=True, encoding="utf-8", timeout=10,
    )
    if resultado.returncode != 0:
        raise RuntimeError(
            f"O programa Python gerado falhou (código {resultado.returncode}):\n"
            f"{resultado.stderr}\n----- código gerado -----\n{codigo_py}"
        )
    return resultado.stdout
