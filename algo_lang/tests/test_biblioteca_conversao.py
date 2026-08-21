# -*- coding: utf-8 -*-
"""Testes da biblioteca 'conversao' -- converte entre os 5 tipos
primitivos (inteiro, decimal, booleano, cadeia, caracter)."""
import os
import subprocess
import sys

import pytest

from apoio import compilar, executar
from algo_lang.compilador.semantics import ErroSemantico


def _correr_esperando_erro(codigo_algo):
    codigo_py = compilar(codigo_algo)
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    return subprocess.run(
        [sys.executable, "-c", codigo_py], capture_output=True,
        encoding="utf-8", timeout=10, env=env)


# ---------- paraTexto ----------

def test_para_texto_de_inteiro_decimal_e_booleano():
    saida = executar("""
        algoritmo "T"
        importar Conversao
        inicio
            escrever(conversao.paraTexto(10))
            escrever(conversao.paraTexto(3.5))
            escrever(conversao.paraTexto(verdadeiro))
            escrever(conversao.paraTexto(falso))
    """)
    assert saida.strip().splitlines() == ["10", "3.5", "verdadeiro", "falso"]


def test_para_texto_permite_concatenar_numero_em_cadeia():
    """O problema original que motivou a biblioteca: '+' entre cadeia e
    número é um erro semântico, mas paraTexto(x) resolve-o."""
    saida = executar("""
        algoritmo "T"
        importar Conversao
        inicio
            idade:inteiro = 20
            escrever("idade: " + conversao.paraTexto(idade))
    """)
    assert saida.strip() == "idade: 20"


# ---------- paraInteiro ----------

@pytest.mark.parametrize("expr,esperado", [
    ("3.9", "3"), ("-3.9", "-3"), ("verdadeiro", "1"), ("falso", "0"),
])
def test_para_inteiro_de_decimal_e_booleano(expr, esperado):
    saida = executar(f"""
        algoritmo "T"
        importar Conversao
        inicio
            escrever(conversao.paraInteiro({expr}))
    """)
    assert saida.strip() == esperado


def test_para_inteiro_de_cadeia_valida():
    saida = executar("""
        algoritmo "T"
        importar Conversao
        inicio
            escrever(conversao.paraInteiro("123"))
    """)
    assert saida.strip() == "123"


def test_para_inteiro_de_cadeia_invalida_da_erro_nosso_nao_traceback():
    resultado = _correr_esperando_erro("""\
algoritmo "T"
importar Conversao
inicio
    escrever(conversao.paraInteiro("1A3"))
""")
    assert resultado.returncode == 1
    assert "Traceback" not in resultado.stdout
    assert "Traceback" not in resultado.stderr
    assert "não pode ser convertido para um número inteiro" in resultado.stdout


def test_para_inteiro_de_decimal_infinito_da_erro_nosso_nao_traceback():
    """AL: '*' pode fazer overflow silencioso para infinito (ao contrário
    de '^'/matematica.potencia, que já dá OverflowError antes disto);
    int(inf) é OverflowError, não ValueError -- tem de ser apanhado
    dentro da própria função de conversão."""
    resultado = _correr_esperando_erro("""\
algoritmo "T"
importar Conversao
inicio
    x:decimal = """ + "9" * 300 + """.0
    y:decimal = x * x
    escrever(conversao.paraInteiro(y))
""")
    assert resultado.returncode == 1
    assert "Traceback" not in resultado.stdout
    assert "Traceback" not in resultado.stderr
    # AUDITORIA_2026-08-19 bug #8: passou a ter uma tradução dedicada
    # (antes caía no genérico "valor inválido (...)", com o texto do
    # Python "cannot convert float infinity to integer" à mistura).
    assert "infinito" in resultado.stdout
    assert "infinity" not in resultado.stdout.lower()


# ---------- paraDecimal ----------

def test_para_decimal_de_cadeia_inteiro_e_booleano():
    saida = executar("""
        algoritmo "T"
        importar Conversao
        inicio
            escrever(conversao.paraDecimal("3.14"))
            escrever(conversao.paraDecimal(4))
            escrever(conversao.paraDecimal(verdadeiro))
    """)
    assert saida.strip().splitlines() == ["3.14", "4.0", "1.0"]


def test_para_decimal_de_cadeia_invalida_da_erro_nosso():
    resultado = _correr_esperando_erro("""\
algoritmo "T"
importar Conversao
inicio
    escrever(conversao.paraDecimal("abc"))
""")
    assert resultado.returncode == 1
    assert "Traceback" not in resultado.stdout
    assert "não pode ser convertido para um número decimal" in resultado.stdout


# ---------- paraBooleano ----------

@pytest.mark.parametrize("expr,esperado", [
    ("0", "falso"), ("5", "verdadeiro"), ("0.0", "falso"), ("1.5", "verdadeiro"),
    ('""', "falso"), ('"falso"', "falso"), ('"Falso"', "falso"), ('"F"', "falso"),
    ('"qualquer coisa"', "verdadeiro"), ('"verdadeiro"', "verdadeiro"),
    ("verdadeiro", "verdadeiro"), ("falso", "falso"),
])
def test_para_booleano(expr, esperado):
    saida = executar(f"""
        algoritmo "T"
        importar Conversao
        inicio
            escrever(conversao.paraBooleano({expr}))
    """)
    assert saida.strip() == esperado


def test_para_booleano_nunca_da_erro():
    """bool(x) do Python nunca levanta exceção -- confirma que não há
    nenhum caminho de erro nesta função."""
    saida = executar("""
        algoritmo "T"
        importar Conversao
        inicio
            escrever(conversao.paraBooleano("qualquer texto estranho !@#"))
    """)
    assert saida.strip() == "verdadeiro"


# ---------- paraCaracter ----------

def test_para_caracter_de_cadeia_com_1_caracter():
    saida = executar("""
        algoritmo "T"
        importar Conversao
        inicio
            escrever(conversao.paraCaracter("z"))
    """)
    assert saida.strip() == "z"


def test_para_caracter_de_cadeia_com_mais_de_1_caracter_da_erro_nosso():
    resultado = _correr_esperando_erro("""\
algoritmo "T"
importar Conversao
inicio
    escrever(conversao.paraCaracter("abc"))
""")
    assert resultado.returncode == 1
    assert "Traceback" not in resultado.stdout
    assert "exatamente 1 caracter" in resultado.stdout


# ---------- paraAscii / deAscii ----------

def test_para_ascii_e_de_ascii_sao_inversas():
    saida = executar("""
        algoritmo "T"
        importar Conversao
        inicio
            escrever(conversao.paraAscii('A'))
            escrever(conversao.deAscii(65))
    """)
    assert saida.strip().splitlines() == ["65", "A"]


def test_para_ascii_de_caracter_por_omissao_vazio_da_erro_nosso_nao_traceback():
    """O valor por omissão de 'caracter' não inicializado é "" (0
    caracteres) -- ord("") é TypeError no Python puro, não ValueError;
    tem de ser apanhado dentro da própria função de conversão."""
    resultado = _correr_esperando_erro("""\
algoritmo "T"
importar Conversao
inicio
    c:caracter
    escrever(conversao.paraAscii(c))
""")
    assert resultado.returncode == 1
    assert "Traceback" not in resultado.stdout
    assert "Traceback" not in resultado.stderr
    assert "não é um caracter válido" in resultado.stdout


def test_de_ascii_fora_do_intervalo_valido_da_erro_nosso():
    resultado = _correr_esperando_erro("""\
algoritmo "T"
importar Conversao
inicio
    escrever(conversao.deAscii(-5))
""")
    assert resultado.returncode == 1
    assert "Traceback" not in resultado.stdout
    assert "não é um código de caracter válido" in resultado.stdout


# ---------- verificação de tipos em compilação ----------

def test_para_ascii_nao_aceita_cadeia_generica_so_caracter():
    with pytest.raises(ErroSemantico, match="espera um caracter"):
        compilar("""
            algoritmo "T"
            importar Conversao
            inicio
                escrever(conversao.paraAscii("abc"))
        """)


def test_para_inteiro_nao_aceita_estrutura():
    with pytest.raises(ErroSemantico, match="espera um valor de tipo primitivo"):
        compilar("""
            algoritmo "T"
            importar Conversao
            estrutura Ponto
                x:inteiro
                y:inteiro
            inicio
                p:Ponto
                escrever(conversao.paraInteiro(p))
        """)
