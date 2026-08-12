# -*- coding: utf-8 -*-
"""Testes de regressão para as funcionalidades base da linguagem (não
estruturas/fluxogramas/transpilação, mas o essencial que as sustenta)."""
import pytest

from algo_lang.compilador.semantics import ErroSemantico
from apoio import executar, compilar


def test_tipos_e_operadores_aritmeticos():
    saida = executar("""
        algoritmo "T"
        inicio
            escrever(7 div 2, " ", 7 mod 2, " ", 2 ^ 10, " ", 7 / 2)
    """)
    assert saida.strip() == "3 1 1024 3.5"


def test_concatenacao_com_mais():
    saida = executar("""
        algoritmo "T"
        inicio
            nome:cadeia = "Ana"
            escrever("Olá, " + nome + "!")
    """)
    assert saida.strip() == "Olá, Ana!"


def test_ciclos_para_enquanto_faz_enquanto():
    saida = executar("""
        algoritmo "T"
        inicio
            i:inteiro = 0
            para i de 1 ate 3 fazer
                escrever(i)
            c:inteiro = 0
            enquanto c < 2 fazer
                escrever("e", c)
                c = c + 1
            d:inteiro = 0
            fazer
                escrever("f", d)
                d = d + 1
            enquanto d < 2
    """)
    assert saida.split() == ["1", "2", "3", "e0", "e1", "f0", "f1"]


def test_recursividade():
    saida = executar("""
        algoritmo "T"
        funcao fatorial(n:inteiro):inteiro
            se n <= 1 entao
                devolver 1
            senao
                devolver n * fatorial(n - 1)
        inicio
            escrever(fatorial(5))
    """)
    assert saida.strip() == "120"


def test_variavel_global_visivel_em_funcao():
    saida = executar("""
        algoritmo "T"
        procedimento mostra()
            escrever(contador)
        inicio
            contador:inteiro = 42
            mostra()
    """)
    assert saida.strip() == "42"


def test_parametro_sombreia_global():
    saida = executar("""
        algoritmo "T"
        total:inteiro = 0
        funcao dobro(total:inteiro):inteiro
            devolver total * 2
        inicio
            escrever(dobro(5))
    """)
    assert saida.strip() == "10"


def test_funcao_nao_ve_variavel_local_de_outra_funcao():
    with pytest.raises(ErroSemantico, match="não foi declarada"):
        compilar("""
            algoritmo "T"
            procedimento a()
                x:inteiro = 5
            procedimento b()
                escrever(x)
            inicio
                a()
                b()
        """)


def test_atribuicao_de_tipo_incompativel_da_erro():
    with pytest.raises(ErroSemantico):
        compilar("""
            algoritmo "T"
            inicio
                x:inteiro = 5
                x = "texto"
        """)


def test_condicao_nao_booleana_da_erro():
    with pytest.raises(ErroSemantico, match="booleana"):
        compilar("""
            algoritmo "T"
            inicio
                se 5 entao
                    escrever("nunca")
        """)


def test_biblioteca_nao_importada_da_erro():
    with pytest.raises(ErroSemantico, match="não foi importada"):
        compilar("""
            algoritmo "T"
            inicio
                escrever(matematica.raiz(4))
        """)


def test_ref_so_em_procedimento_ja_nao_se_aplica_funciona_em_funcao():
    """Desde a última revisão, 'ref' passou a ser permitido em funções."""
    saida = executar("""
        algoritmo "T"
        funcao incrementa(ref x:inteiro):inteiro
            x = x + 1
            devolver x
        inicio
            n:inteiro = 5
            r:inteiro = incrementa(n)
            escrever(n, " ", r)
    """)
    assert saida.strip() == "6 6"
