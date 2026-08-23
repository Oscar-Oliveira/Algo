# -*- coding: utf-8 -*-
"""Testes para as instruções 'sair' (break) e 'continuar' (continue),
válidas só dentro de um ciclo ('enquanto'/'para'/'fazer...enquanto').

Antes destas instruções, o ALGO não tinha forma de sair de um ciclo a
meio, forçando o idioma da "bandeira" booleana -- estas duas instruções
dão uma alternativa direta e estruturada."""
import textwrap

import pytest

from algo_lang.compilador.lexer import ErroLexico
from algo_lang.compilador.parser import parse, ErroSintatico
from algo_lang.compilador.semantics import verificar, ErroSemantico
from algo_lang.compilador import ast_nodes as A
from apoio import compilar, executar


def _parse(codigo_algo):
    return parse(textwrap.dedent(codigo_algo).lstrip("\n"))


# ---------- parser ----------

def test_sair_dentro_de_enquanto_parseia():
    programa = _parse("""
        algoritmo "T"
        inicio
            enquanto verdadeiro fazer
                sair
    """)
    assert isinstance(programa.corpo[0].corpo[0], A.Sair)


def test_continuar_dentro_de_para_parseia():
    programa = _parse("""
        algoritmo "T"
        inicio
            para i de 1 ate 3 fazer
                continuar
    """)
    assert isinstance(programa.corpo[0].corpo[0], A.Continuar)


def test_sair_nao_aceita_expressao_a_seguir():
    with pytest.raises(ErroSintatico):
        _parse("""
            algoritmo "T"
            inicio
                enquanto verdadeiro fazer
                    sair 1
        """)


# ---------- semantics: contexto (só válido dentro de um ciclo) ----------

def test_sair_dentro_de_enquanto_de_topo_e_aceite():
    verificar(_parse("""
        algoritmo "T"
        inicio
            enquanto verdadeiro fazer
                sair
    """))


def test_continuar_dentro_de_para_de_topo_e_aceite():
    verificar(_parse("""
        algoritmo "T"
        inicio
            i:inteiro
            para i de 1 ate 3 fazer
                continuar
    """))


def test_sair_dentro_de_faz_enquanto_e_aceite():
    verificar(_parse("""
        algoritmo "T"
        inicio
            x:inteiro = 0
            fazer
                x = x + 1
                sair
            enquanto x < 10
    """))


def test_sair_fora_de_qualquer_ciclo_e_rejeitado():
    with pytest.raises(ErroSemantico, match="'sair' só pode ser usado dentro de um ciclo"):
        verificar(_parse("""
            algoritmo "T"
            inicio
                sair
        """))


def test_continuar_dentro_de_funcao_sem_ciclo_e_rejeitado():
    with pytest.raises(ErroSemantico, match="'continuar' só pode ser usado dentro de um ciclo"):
        verificar(_parse("""
            algoritmo "T"
            procedimento p()
                continuar
            inicio
                p()
        """))


def test_sair_dentro_de_escolher_sem_ciclo_exterior_e_rejeitado():
    with pytest.raises(ErroSemantico, match="'sair' só pode ser usado dentro de um ciclo"):
        verificar(_parse("""
            algoritmo "T"
            inicio
                x:inteiro = 1
                escolher x
                    caso 1
                        sair
        """))


def test_sair_dentro_de_escolher_dentro_de_ciclo_exterior_e_aceite():
    """'escolher'/'caso' não reseta o contexto de ciclo -- um 'sair' aí
    visa o ciclo exterior mais próximo (passthrough, tal como ctx_funcao
    já fazia para 'retornar')."""
    verificar(_parse("""
        algoritmo "T"
        inicio
            x:inteiro = 1
            enquanto verdadeiro fazer
                escolher x
                    caso 1
                        sair
    """))


def test_sair_dentro_de_se_dentro_de_ciclo_e_aceite():
    verificar(_parse("""
        algoritmo "T"
        inicio
            enquanto verdadeiro fazer
                se verdadeiro entao
                    sair
    """))


# ---------- semantics: solidez de _todos_caminhos_devolvem com sair/continuar ----------

def test_funcao_com_sair_sem_retornar_apos_o_ciclo_e_rejeitada():
    """AUDITORIA_2026-08-22 (ronda 14): antes da correção a
    _todos_caminhos_devolvem, isto era ACEITE incorretamente -- a leitura
    sequencial via 'retornar 1' como irmão mais à frente na lista,
    ignorando que 'sair' pode desviar o controlo antes de lá chegar
    (repro confirmada por execução: a função cai fora sem retornar
    nada). Tem de ser rejeitado em compilação, não crashar em runtime."""
    with pytest.raises(ErroSemantico, match="nem todos os caminhos terminam"):
        verificar(_parse("""
            algoritmo "T"
            funcao f(): inteiro
                enquanto verdadeiro fazer
                    se verdadeiro entao
                        sair
                    retornar 1
            inicio
                escrever(f())
        """))


def test_funcao_com_continuar_sem_retornar_apos_o_ciclo_e_rejeitada():
    with pytest.raises(ErroSemantico, match="nem todos os caminhos terminam"):
        verificar(_parse("""
            algoritmo "T"
            funcao f(): inteiro
                enquanto verdadeiro fazer
                    se verdadeiro entao
                        continuar
                    retornar 1
            inicio
                escrever(f())
        """))


def test_funcao_com_sair_e_retornar_apos_o_ciclo_e_aceite():
    verificar(_parse("""
        algoritmo "T"
        funcao f(): inteiro
            enquanto verdadeiro fazer
                se verdadeiro entao
                    sair
                retornar 1
            retornar 2
        inicio
            escrever(f())
    """))


def test_funcao_com_sair_dentro_de_para_e_retornar_apos_e_aceite():
    verificar(_parse("""
        algoritmo "T"
        funcao f(): inteiro
            i:inteiro
            para i de 1 ate 10 fazer
                se i == 5 entao
                    sair
            retornar 0
        inicio
            escrever(f())
    """))


def test_funcao_sem_sair_com_retornar_sempre_alcancavel_continua_aceite():
    """Não regressão do comportamento já existente (sem sair/continuar
    envolvidos)."""
    verificar(_parse("""
        algoritmo "T"
        funcao f(): inteiro
            enquanto verdadeiro fazer
                retornar 1
        inicio
            escrever(f())
    """))



# ---------- codegen: execução real ----------

def test_sair_em_enquanto_para_a_iteracao():
    saida = executar("""
        algoritmo "T"
        inicio
            i:inteiro = 0
            enquanto verdadeiro fazer
                i = i + 1
                se i == 3 entao
                    sair
                escrever(i)
    """)
    assert saida.strip().splitlines() == ["1", "2"]


def test_continuar_em_enquanto_salta_a_iteracao():
    saida = executar("""
        algoritmo "T"
        inicio
            i:inteiro = 0
            enquanto i < 5 fazer
                i = i + 1
                se i mod 2 == 0 entao
                    continuar
                escrever(i)
    """)
    assert saida.strip().splitlines() == ["1", "3", "5"]


def test_sair_em_para():
    saida = executar("""
        algoritmo "T"
        inicio
            i:inteiro
            para i de 1 ate 10 fazer
                se i == 4 entao
                    sair
                escrever(i)
    """)
    assert saida.strip().splitlines() == ["1", "2", "3"]


def test_continuar_em_para():
    saida = executar("""
        algoritmo "T"
        inicio
            i:inteiro
            para i de 1 ate 5 fazer
                se i mod 2 == 0 entao
                    continuar
                escrever(i)
    """)
    assert saida.strip().splitlines() == ["1", "3", "5"]


def test_sair_em_faz_enquanto():
    saida = executar("""
        algoritmo "T"
        inicio
            i:inteiro = 0
            fazer
                i = i + 1
                se i == 3 entao
                    sair
                escrever(i)
            enquanto i < 100
    """)
    assert saida.strip().splitlines() == ["1", "2"]


def test_continuar_em_faz_enquanto_respeita_a_condicao_de_saida():
    """AUDITORIA_2026-08-22 (ronda 14): o teste crítico -- antes da
    reestruturação do FazEnquanto ('while True: corpo; if not cond:
    break' -> bandeira '_algo_fazer_primeira_N'), um 'continue' nativo
    do Python saltava por cima do 'if not cond: break', fazendo o ciclo
    ignorar a condição de saída e repetir o corpo indefinidamente.
    Executado de verdade (não só compilado) para provar tanto a saída
    correta como que o ciclo termina."""
    saida = executar("""
        algoritmo "T"
        inicio
            i:inteiro = 0
            contador:inteiro = 0
            fazer
                i = i + 1
                contador = contador + 1
                se i mod 2 == 0 entao
                    continuar
                escrever(i)
            enquanto i < 5
            escrever("contador=", contador)
    """)
    assert saida.strip().splitlines() == ["1", "3", "5", "contador=5"]


def test_faz_enquanto_aninhados_com_continuar_em_ambos_tem_contadores_distintos():
    """Confirma que self._contador_faz_enquanto gera nomes de bandeira
    distintos por ocorrência -- um ciclo interior não interfere com a
    bandeira do exterior."""
    saida = executar("""
        algoritmo "T"
        inicio
            i:inteiro = 0
            fazer
                i = i + 1
                se i mod 2 == 0 entao
                    continuar
                j:inteiro = 0
                fazer
                    j = j + 1
                    se j mod 2 == 0 entao
                        continuar
                    escrever("i=", i, " j=", j)
                enquanto j < 4
            enquanto i < 4
    """)
    assert saida.strip().splitlines() == [
        "i=1 j=1", "i=1 j=3", "i=3 j=1", "i=3 j=3",
    ]


def test_sair_dentro_de_ciclo_aninhado_so_sai_do_interior():
    saida = executar("""
        algoritmo "T"
        inicio
            i:inteiro
            x:inteiro = 0
            enquanto x < 3 fazer
                x = x + 1
                para i de 1 ate 10 fazer
                    se i == 2 entao
                        sair
                    escrever("x=", x, " i=", i)
    """)
    assert saida.strip().splitlines() == ["x=1 i=1", "x=2 i=1", "x=3 i=1"]


def test_sair_num_ciclo_interior_nao_afeta_a_garantia_do_exterior():
    """Um 'sair' dentro de um ciclo INTERIOR só sai desse ciclo -- não
    deve fazer o ciclo EXTERIOR perder a garantia de retornar que já
    tinha antes (confirma que _tem_sair_ou_continuar_alcancavel para
    corretamente em ciclos aninhados, não desce neles)."""
    verificar(_parse("""
        algoritmo "T"
        funcao f(): inteiro
            i:inteiro
            enquanto verdadeiro fazer
                para i de 1 ate 10 fazer
                    se i == 5 entao
                        sair
                retornar 1
        inicio
            escrever(f())
    """))
