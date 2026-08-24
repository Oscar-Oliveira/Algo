# -*- coding: utf-8 -*-
"""Testes para a funcionalidade 'estrutura' (registos/structs)."""
import subprocess

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


def test_vetor_de_estruturas_tem_instancias_independentes():
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
            retornar p.x + p.y
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


# ---------- 'nulo' e estruturas auto-referenciadas (listas ligadas, árvores) ----------

def test_estrutura_auto_referenciada_nao_recursa_infinitamente():
    """Antes, declarar 'n:No' com um campo 'seguinte:No' rebentava com
    RecursionError -- o valor por omissão de um campo do próprio tipo
    era sempre construído eagerly. Agora o campo fica 'nulo'."""
    saida = executar("""
        algoritmo "T"
        estrutura No
            valor:inteiro
            seguinte:No
        inicio
            n:No
            escrever(n.valor, "|", n.seguinte == nulo)
    """)
    assert saida.strip() == "0|verdadeiro"


def test_lista_ligada_construida_e_percorrida_com_nulo():
    """Atribuição de estrutura copia por valor -- por isso 'b' tem de
    estar com os seus campos finais ANTES de 'a.seguinte = b', senão
    'a.seguinte' fica com a cópia de 'b' como estava nesse momento
    (valor=0), não com o valor atribuído depois. Constrói-se sempre de
    trás para a frente, tal como não há alocação dinâmica em ALGO."""
    saida = executar("""
        algoritmo "T"
        estrutura No
            valor:inteiro
            seguinte:No
        inicio
            b:No
            b.valor = 2
            b.seguinte = nulo

            a:No
            a.valor = 1
            a.seguinte = b

            atual:No = a
            enquanto atual <> nulo fazer
                escrever(atual.valor)
                atual = atual.seguinte
    """)
    assert saida.split() == ["1", "2"]


def test_aceder_a_campo_de_nulo_da_erro_amigavel_nao_traceback(tmp_path):
    algo_path = tmp_path / "prog.algo"
    algo_path.write_text(
        'algoritmo "T"\n'
        'estrutura No\n'
        '    valor:inteiro\n'
        '    seguinte:No\n'
        'inicio\n'
        '    n:No\n'
        '    escrever(n.seguinte.valor)\n',
        encoding="utf-8")
    resultado = subprocess.run(
        ["algo", "executa", str(algo_path)], capture_output=True, text=True)
    assert "Traceback" not in resultado.stdout
    assert "campo 'valor' de um valor nulo" in resultado.stdout


def test_nulo_incompativel_com_tipo_primitivo_da_erro():
    with pytest.raises(ErroSemantico, match="nulo"):
        compilar("""
            algoritmo "T"
            inicio
                x:inteiro = nulo
                escrever(x)
        """)


def test_nulo_nao_pode_ser_usado_como_identificador():
    with pytest.raises(ErroSintatico):
        compilar("""
            algoritmo "T"
            inicio
                nulo:inteiro = 5
                escrever(nulo)
        """)


def test_mutuamente_recursivas_tambem_nao_recursam_infinitamente():
    saida = executar("""
        algoritmo "T"
        estrutura A
            b:B
        estrutura B
            a:A
        inicio
            x:A
            escrever(x.b == nulo)
    """)
    assert saida.strip() == "verdadeiro"


def test_campo_vetor_do_proprio_tipo_nao_recursa_infinitamente():
    """Ronda 15: 'estrutura No: filhos:No[2]' (uma árvore, campo-vetor do
    PRÓPRIO tipo) compilava, mas construir a instância por omissão
    tentava eagerly popular os 2 elementos de 'filhos', cada um dos quais
    tentava construir os seus próprios 2 elementos, ad infinitum --
    RecursionError em runtime, sem workaround nenhum. Um campo-vetor
    recursivo agora fica vazio por omissão, tal como um campo escalar
    recursivo (ex.: 'seguinte:No') já ficava 'nulo'."""
    saida = executar("""
        algoritmo "T"
        estrutura No
            valor:inteiro
            filhos:No[2]
        inicio
            x:No
            escrever(x.valor)
    """)
    assert saida.strip() == "0"


def test_campo_vetor_mutuamente_recursivo_tambem_nao_recursa_infinitamente():
    saida = executar("""
        algoritmo "T"
        estrutura A
            filhosB:B[1]
        estrutura B
            filhosA:A[1]
        inicio
            x:A
            escrever("ok")
    """)
    assert saida.strip() == "ok"


def test_aceder_a_campo_vetor_recursivo_vazio_da_erro_amigavel_nao_traceback(tmp_path):
    algo_path = tmp_path / "prog.algo"
    algo_path.write_text(
        'algoritmo "T"\n'
        'estrutura No\n'
        '    valor:inteiro\n'
        '    filhos:No[2]\n'
        'inicio\n'
        '    x:No\n'
        '    escrever(x.filhos[0].valor)\n',
        encoding="utf-8")
    import os
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    resultado = subprocess.run(
        ["algo", "executa", str(algo_path)], capture_output=True, encoding="utf-8", env=env)
    assert "Traceback" not in resultado.stdout
    assert "posição de vetor" in resultado.stdout


# ---------- campo 'ref' (aliasing em vez de cópia por valor) ----------

def test_campo_ref_compila_e_fica_nulo_por_omissao():
    saida = executar("""
        algoritmo "T"
        estrutura No
            valor:inteiro
            seguinte:ref No
        inicio
            n:No
            escrever(n.seguinte == nulo)
    """)
    assert saida.strip() == "verdadeiro"


def test_ref_em_declaracao_local_continua_erro_sintatico():
    with pytest.raises(ErroSintatico):
        compilar("""
            algoritmo "T"
            inicio
                x:ref inteiro
        """)


def test_ref_em_declaracao_global_continua_erro_sintatico():
    with pytest.raises(ErroSintatico):
        compilar("""
            algoritmo "T"
            x:ref inteiro
            inicio
                escrever(1)
        """)


def test_campo_ref_de_tipo_primitivo_da_erro_semantico():
    with pytest.raises(ErroSemantico, match="ref"):
        compilar("""
            algoritmo "T"
            estrutura No
                valor:ref inteiro
            inicio
                n:No
        """)


def test_campo_ref_vetor_da_erro_semantico():
    with pytest.raises(ErroSemantico, match="ref"):
        compilar("""
            algoritmo "T"
            estrutura No
                valor:inteiro
                seguinte:ref No[3]
            inicio
                n:No
        """)


def test_lista_ligada_com_ref_permite_ligar_e_mutar_depois():
    """Ao contrário de test_lista_ligada_construida_e_percorrida_com_nulo
    (campo simples, cópia por valor, tem de se construir de trás para a
    frente), um campo 'ref' é um alias -- ligar 'a.seguinte = b' e só
    depois mutar 'b.valor' propaga através de 'a.seguinte'."""
    saida = executar("""
        algoritmo "T"
        estrutura No
            valor:inteiro
            seguinte:ref No
        inicio
            b:No
            b.valor = 2

            a:No
            a.valor = 1
            a.seguinte = b

            b.valor = 99
            escrever(a.seguinte.valor)
    """)
    assert saida.strip() == "99"


def test_copia_por_valor_de_estrutura_preserva_identidade_de_campo_ref():
    """Copiar 'a' por valor (declaração a partir doutra variável) não deve
    quebrar o aliasing do seu campo 'ref' -- prova o __deepcopy__ gerado
    (codegen.py:_gerar_estrutura), não só a atribuição direta ao campo."""
    saida = executar("""
        algoritmo "T"
        estrutura No
            valor:inteiro
            seguinte:ref No
        inicio
            b:No
            b.valor = 2

            a:No
            a.seguinte = b

            c:No = a
            b.valor = 77
            escrever(c.seguinte.valor)
    """)
    assert saida.strip() == "77"


def test_campo_normal_continua_copiado_por_valor_mesmo_com_irmao_ref():
    """Regressão: um campo simples ao lado de um campo 'ref' na mesma
    estrutura continua a copiar por valor -- só o campo 'ref' faz alias."""
    saida = executar("""
        algoritmo "T"
        estrutura Par
            a:inteiro
            seguinte:ref Par
        inicio
            x:Par
            x.a = 1

            y:Par = x
            x.a = 999
            escrever(y.a)
    """)
    assert saida.strip() == "1"


def test_ciclo_de_dois_nos_via_ref_sobrevive_a_copia_por_valor():
    """Um ciclo de referências real só é possível através de campos 'ref'
    (cópia por valor sozinha cortava sempre qualquer ciclo antes desta
    funcionalidade) -- passar um nó do ciclo por valor a um procedimento
    tem de terminar sem RecursionError, graças ao 'memo' do __deepcopy__
    gerado."""
    saida = executar("""
        algoritmo "T"
        estrutura No
            valor:inteiro
            seguinte:ref No

        procedimento imprimir(n:No)
            escrever(n.valor)

        inicio
            a:No
            a.valor = 1
            b:No
            b.valor = 2
            a.seguinte = b
            b.seguinte = a
            imprimir(a)
    """)
    assert saida.strip() == "1"


def test_comparar_dois_ciclos_de_dois_nos_via_ref_nao_rebenta_e_da_igual():
    """Mesmo cenário do teste acima, mas para '==' em vez de cópia: sem
    deteção de ciclo no '__eq__' gerado, comparar dois nós que formam um
    ciclo via 'ref' entrava em RecursionError (o 'memo' do __deepcopy__
    não protegia '__eq__')."""
    saida = executar("""
        algoritmo "T"
        estrutura No
            valor:inteiro
            seguinte:ref No

        inicio
            a1:No
            a1.valor = 1
            b1:No
            b1.valor = 2
            a1.seguinte = b1
            b1.seguinte = a1

            a2:No
            a2.valor = 1
            b2:No
            b2.valor = 2
            a2.seguinte = b2
            b2.seguinte = a2

            escrever(a1 == a1)
            escrever(a1 == a2)
            b2.valor = 99
            escrever(a1 == a2)
    """)
    assert saida.strip() == "verdadeiro\nverdadeiro\nfalso"
