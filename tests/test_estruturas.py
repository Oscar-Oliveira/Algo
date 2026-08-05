# -*- coding: utf-8 -*-
"""Testes para a funcionalidade 'estrutura' (registos/structs)."""
import pytest

from algo_lang.compilador.lexer import ErroLexico
from algo_lang.compilador.parser import ErroSintatico
from algo_lang.compilador.semantics import ErroSemantico

from apoio import executar, compilar


def test_declaracao_e_acesso_a_campos():
    saida = executar("""
        algoritmo "T"
        estrutura Ponto
            x:inteiro
            y:inteiro
        inicio
            p:Ponto
            p.x = 3
            p.y = 4
            escrever(p.x, ",", p.y)
    """)
    assert saida.strip() == "3,4"


def test_campos_tem_valor_por_omissao():
    saida = executar("""
        algoritmo "T"
        estrutura Conta
            saldo:decimal
            nome:cadeia
            ativa:booleano
        inicio
            c:Conta
            escrever(c.saldo, "|", c.nome, "|", c.ativa)
    """)
    assert saida.strip() == "0.0||falso"


def test_estrutura_aninhada():
    saida = executar("""
        algoritmo "T"
        estrutura Ponto
            x:inteiro
            y:inteiro
        estrutura Retangulo
            canto:Ponto
            largura:inteiro
        inicio
            r:Retangulo
            r.canto.x = 10
            r.canto.y = 20
            escrever(r.canto.x, ",", r.canto.y)
    """)
    assert saida.strip() == "10,20"


def test_ref_com_estrutura_altera_o_original():
    saida = executar("""
        algoritmo "T"
        estrutura Ponto
            x:inteiro
            y:inteiro
        procedimento deslocar(ref p:Ponto, dx:inteiro)
            p.x = p.x + dx
        inicio
            p:Ponto
            p.x = 5
            deslocar(p, 100)
            escrever(p.x)
    """)
    assert saida.strip() == "105"


def test_array_de_estruturas_tem_instancias_independentes():
    saida = executar("""
        algoritmo "T"
        estrutura Ponto
            x:inteiro
        inicio
            pontos:Ponto[3]
            pontos[0].x = 100
            escrever(pontos[0].x, ",", pontos[1].x, ",", pontos[2].x)
    """)
    assert saida.strip() == "100,0,0"


def test_estrutura_como_parametro_e_retorno_de_funcao():
    saida = executar("""
        algoritmo "T"
        estrutura Ponto
            x:inteiro
            y:inteiro
        funcao somaCoordenadas(p:Ponto):inteiro
            devolver p.x + p.y
        inicio
            p:Ponto
            p.x = 3
            p.y = 4
            escrever(somaCoordenadas(p))
    """)
    assert saida.strip() == "7"


def test_campo_inexistente_da_erro_semantico():
    with pytest.raises(ErroSemantico, match="não tem nenhum campo"):
        compilar("""
            algoritmo "T"
            estrutura Ponto
                x:inteiro
            inicio
                p:Ponto
                escrever(p.z)
        """)


def test_tipo_de_estrutura_desconhecido_da_erro():
    with pytest.raises(ErroSemantico, match="desconhecido"):
        compilar("""
            algoritmo "T"
            inicio
                p:NaoExiste
                escrever(p)
        """)


def test_atribuicao_de_tipo_incompativel_a_campo_da_erro():
    with pytest.raises(ErroSemantico):
        compilar("""
            algoritmo "T"
            estrutura Ponto
                x:inteiro
            inicio
                p:Ponto
                p.x = "texto"
        """)


def test_estrutura_duplicada_da_erro():
    with pytest.raises(ErroSemantico, match="já foi definida"):
        compilar("""
            algoritmo "T"
            estrutura Ponto
                x:inteiro
            estrutura Ponto
                y:inteiro
            inicio
                escrever(1)
        """)


def test_campo_duplicado_da_erro():
    with pytest.raises(ErroSemantico, match="duplicado"):
        compilar("""
            algoritmo "T"
            estrutura Ponto
                x:inteiro
                x:decimal
            inicio
                escrever(1)
        """)
