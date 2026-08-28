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
            p:Ponto = {}
            p.x = 3
            p.y = 4
            escrever(p.x, ",", p.y)
    """)
    assert saida.strip() == "3,4"


def test_campos_tem_valor_por_omissao():
    """'{}' constrói uma instância real, com cada campo no seu próprio
    valor por omissão -- ao contrário de uma declaração 'c:Conta' sem
    literal nenhum, que fica 'nulo' (ver test_declaracao_sem_literal_
    fica_nula, mais abaixo)."""
    saida = executar("""
        algoritmo "T"
        estrutura Conta
            saldo:decimal
            nome:cadeia
            ativa:booleano
        inicio
            c:Conta = {}
            escrever(c.saldo, "|", c.nome, "|", c.ativa)
    """)
    assert saida.strip() == "0.0||falso"


def test_declaracao_sem_literal_fica_nula():
    saida = executar("""
        algoritmo "T"
        estrutura Conta
            saldo:decimal
        inicio
            c:Conta
            escrever(c == nulo)
    """)
    assert saida.strip() == "verdadeiro"


def test_estrutura_aninhada():
    """Um campo do tipo 'estrutura' segue a mesma regra que a variável
    top-level: fica 'nulo' por omissão, mesmo dentro de um '{}' -- por
    isso 'r.canto' também precisa do seu próprio '{}' explícito antes de
    se lhe poder aceder a campos."""
    saida = executar("""
        algoritmo "T"
        estrutura Ponto
            x:inteiro
            y:inteiro
        estrutura Retangulo
            canto:Ponto
            largura:inteiro
        inicio
            r:Retangulo = {canto: {}, largura: 0}
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
            p:Ponto = {}
            p.x = 5
            deslocar(p, 100)
            escrever(p.x)
    """)
    assert saida.strip() == "105"


def test_vetor_de_estruturas_bare_fica_com_elementos_nulos():
    """Ponto 5: o valor por omissão de um vetor continua a ser preenchido
    eagerly (ao contrário de uma 'estrutura' sozinha), mas cada elemento
    de tipo 'estrutura' é, ele próprio, 'nulo' -- não uma instância nova."""
    saida = executar("""
        algoritmo "T"
        estrutura Ponto
            x:inteiro
        inicio
            pontos:Ponto[3]
            escrever(pontos[0] == nulo, ",", pontos[1] == nulo, ",", pontos[2] == nulo)
    """)
    assert saida.strip() == "verdadeiro,verdadeiro,verdadeiro"


def test_vetor_de_estruturas_tem_instancias_independentes():
    saida = executar("""
        algoritmo "T"
        estrutura Ponto
            x:inteiro
        inicio
            pontos:Ponto[3] = {{}, {}, {}}
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
            p:Ponto = {}
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
    """'{}' preenche cada campo com o SEU PRÓPRIO valor por omissão --
    para um campo de tipo 'estrutura' isso é sempre 'nulo' (ponto 5),
    recursivo ou não, por isso não há recursão nenhuma a evitar aqui:
    'seguinte' fica 'nulo' tal e qual um campo escalar ficaria 0."""
    saida = executar("""
        algoritmo "T"
        estrutura No
            valor:inteiro
            seguinte:No
        inicio
            n:No = {}
            escrever(n.valor, "|", n.seguinte == nulo)
    """)
    assert saida.strip() == "0|verdadeiro"


def test_lista_ligada_construida_e_percorrida_com_nulo():
    """Ao contrário de uma cópia por valor, aliasing permite ligar
    'a.seguinte = b' e só DEPOIS mutar 'b.valor' -- a mutação aparece
    através de 'a.seguinte', porque é o MESMO objeto (ponto 1)."""
    saida = executar("""
        algoritmo "T"
        estrutura No
            valor:inteiro
            seguinte:No
        inicio
            a:No = {}
            a.valor = 1

            b:No = {}
            a.seguinte = b
            b.valor = 2

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
        '    n:No = {}\n'
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
            x:A = {}
            escrever(x.b == nulo)
    """)
    assert saida.strip() == "verdadeiro"


def test_campo_vetor_do_proprio_tipo_nao_recursa_infinitamente():
    """Ronda 15: 'estrutura No: filhos:No[2]' (uma árvore, campo-vetor do
    PRÓPRIO tipo) compilava, mas construir a instância por omissão
    tentava eagerly popular os 2 elementos de 'filhos', cada um dos quais
    tentava construir os seus próprios 2 elementos, ad infinitum --
    RecursionError em runtime, sem workaround nenhum. Hoje um campo-vetor
    NUNCA recursa, mesmo do próprio tipo: cada elemento é preenchido
    eagerly, mas um elemento de tipo 'estrutura' é sempre 'nulo' (ponto
    5), nunca uma instância nova."""
    saida = executar("""
        algoritmo "T"
        estrutura No
            valor:inteiro
            filhos:No[2]
        inicio
            x:No = {}
            escrever(x.valor, "|", x.filhos[0] == nulo, ",", x.filhos[1] == nulo)
    """)
    assert saida.strip() == "0|verdadeiro,verdadeiro"


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
    """'filhos' fica preenchido (2 elementos), mas cada elemento é 'nulo'
    -- '.valor' sobre o elemento é que dá o erro amigável (ver
    test_campo_vetor_do_proprio_tipo_nao_recursa_infinitamente)."""
    algo_path = tmp_path / "prog.algo"
    algo_path.write_text(
        'algoritmo "T"\n'
        'estrutura No\n'
        '    valor:inteiro\n'
        '    filhos:No[2]\n'
        'inicio\n'
        '    x:No = {}\n'
        '    escrever(x.filhos[0].valor)\n',
        encoding="utf-8")
    import os
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    resultado = subprocess.run(
        ["algo", "executa", str(algo_path)], capture_output=True, encoding="utf-8", env=env)
    assert "Traceback" not in resultado.stdout
    assert "campo 'valor' de um valor nulo" in resultado.stdout


def test_aceder_a_posicao_de_vetor_nulo_da_erro_amigavel_nao_traceback(tmp_path):
    """Um 'vetor' pode ficar 'nulo' tal como uma 'estrutura' (declaração
    sem literal, ou 'nulo' explícito) -- indexá-lo dá um erro amigável
    dedicado, não o traceback cru do Python."""
    algo_path = tmp_path / "prog.algo"
    algo_path.write_text(
        'algoritmo "T"\n'
        'inicio\n'
        '    v:inteiro[3] = nulo\n'
        '    escrever(v[0])\n',
        encoding="utf-8")
    import os
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    resultado = subprocess.run(
        ["algo", "executa", str(algo_path)], capture_output=True, encoding="utf-8", env=env)
    assert "Traceback" not in resultado.stdout
    assert "posição de um vetor nulo" in resultado.stdout


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


def test_ref_em_campo_de_estrutura_e_erro_sintatico():
    """'ref' num campo de 'estrutura' já não existe como funcionalidade
    (aliasing é agora o comportamento normal de QUALQUER campo, ver
    test_lista_ligada_construida_e_percorrida_com_nulo) -- volta a ser
    exatamente o mesmo erro sintático que uma declaração local/global."""
    with pytest.raises(ErroSintatico):
        compilar("""
            algoritmo "T"
            estrutura No
                valor:inteiro
                seguinte:ref No
            inicio
                escrever(1)
        """)
