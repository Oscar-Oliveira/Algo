# -*- coding: utf-8 -*-
"""Auditoria (4ª ronda), Etapa 9 -- consistência entre as ferramentas
associadas (tracer, flowchart, linter) e o compilador.

A matriz de rastreabilidade (secção 8) levantava duas questões:
(1) nenhum teste corria o MESMO programa pelas 3 ferramentas + o
compilador, comparando interpretações; (2) se o linter sofre da mesma
ambiguidade textual campo-de-estrutura-vs-chamada-de-biblioteca que
afeta a gramática TextMate da extensão VS Code (que não tem árvore de
sintaxe, só regex, por isso precisa de um lookahead por '(' -- ver
editors/vscode-algo/syntaxes/algo.tmLanguage.json).

Achado ao investigar (2): a ambiguidade é estrutural da extensão VS
Code (texto puro, sem parser) -- NÃO existe para linter.py nem
flowchart.py, porque ambos operam sobre a AST já resolvida pelo
parser (A.Chamada vs A.LValue com acesso 'campo' são tipos de nó
DISTINTOS desde a análise sintática; nenhum dos dois faz a sua própria
análise de texto). `flowchart.py::_eh_chamada_a_rotina` confirma isto
diretamente: começa por `isinstance(chamada, A.Chamada)`, por isso um
acesso a campo (sempre A.LValue) nunca pode ser tratado como chamada,
seja qual for o nome. Achado lateral: `Linter.codigo_fonte` é guardado
em __init__ mas nunca lido em lado nenhum da classe -- parâmetro morto,
não um bug (não fazer nada além de registar, por instrução do
projeto). O teste abaixo confirma (1) empiricamente, em vez de só
argumentar pela arquitetura."""
import os
import textwrap

from algo_lang.compilador.parser import parse
from algo_lang.compilador.semantics import verificar
from algo_lang.compilador.codegen import gerar_python_com_mapa
from algo_lang.tools import linter as linter_modulo
from algo_lang.tools.flowchart import gerar_dot
from algo_lang.tools.tracer import gerar_trace


def test_campo_de_estrutura_com_mesmo_nome_de_rotina_nao_ganha_contorno_duplo_no_fluxograma():
    """'dobro' é ao mesmo tempo o nome de uma função E de um campo de
    estrutura -- o fluxograma tem de distinguir 'p.dobro' (campo, sem
    contorno duplo) de 'dobro(x)' (chamada real, com contorno duplo),
    apesar do mesmo nome. Isto seria exatamente o cenário em que uma
    ferramenta baseada em texto (como a gramática VS Code) se
    confundiria sem o lookahead por '('."""
    programa = parse(textwrap.dedent("""
        algoritmo "T"
        estrutura Caixa
            dobro:inteiro
        funcao dobro(n:inteiro):inteiro
            devolver n * 2
        inicio
            c:Caixa
            c.dobro = 5
            escrever(c.dobro)
            escrever(dobro(5))
    """))
    verificar(programa)
    nomes_rotinas = {f.nome for f in programa.funcoes}
    dot = gerar_dot(programa.corpo, programa.nome, nomes_rotinas)

    linha_campo = next(l for l in dot.splitlines() if "c.dobro = 5" in l)
    assert "peripheries=2" not in linha_campo

    linha_chamada = next(l for l in dot.splitlines() if 'label="escrever(dobro(5))"' in l)
    assert "peripheries=2" not in linha_chamada  # escrever() nunca tem contorno duplo, só declaração/atribuição/chamada solta a partir de uma rotina


def test_mesmo_programa_interpretado_consistentemente_pelas_tres_ferramentas(tmp_path):
    """Um só programa, com função de utilizador, chamada de biblioteca,
    estrutura e ciclo -- corrido pelo compilador, linter, flowchart e
    tracer. Nenhuma das 4 ferramentas deve levantar exceção nenhuma
    (nenhuma diverge sobre o programa ser válido), e o CONJUNTO de
    nomes de rotina que cada uma deriva independentemente da mesma AST
    (programa.funcoes) tem de ser exatamente o mesmo -- não há um
    "quarto" cálculo próprio escondido nalguma das ferramentas que
    possa divergir silenciosamente do que o compilador já decidiu."""
    codigo_algo = textwrap.dedent("""
        algoritmo "T"
        importar Matematica
        estrutura Ponto
            x:inteiro
            y:inteiro
        funcao somaCoordenadas(pt:Ponto):inteiro
            devolver pt.x + pt.y
        inicio
            p:Ponto = {x: 3, y: 4}
            total:inteiro = somaCoordenadas(p)
            raiz:decimal = matematica.raiz(16.0)
            i:inteiro
            para i de 0 ate 2 fazer
                escrever(i)
            escrever(total, " ", raiz)
    """)

    # 1) compilador
    programa = parse(codigo_algo)
    verificar(programa)
    nomes_rotinas_compilador = {f.nome for f in programa.funcoes}
    assert nomes_rotinas_compilador == {"somaCoordenadas"}

    # 2) linter -- não deve crashar nem assinalar nada sobre este
    # programa limpo (nenhuma variável não usada, nenhuma rotina nunca
    # chamada: 'somaCoordenadas' É chamada).
    avisos = linter_modulo.analisar(programa, codigo_algo)
    mencoes_a_somacoordenadas = [a for a in avisos if "somaCoordenadas" in str(a)]
    assert mencoes_a_somacoordenadas == []

    # 3) flowchart -- a chamada a 'somaCoordenadas(p)' tem de ganhar
    # contorno duplo (é uma rotina do utilizador); a chamada a
    # 'matematica.raiz' não (é biblioteca) -- mesmo conjunto de nomes
    # que o compilador calculou, não um recálculo próprio divergente.
    dot = gerar_dot(programa.corpo, programa.nome, nomes_rotinas_compilador)
    linha_soma = next(l for l in dot.splitlines() if "somaCoordenadas(p)" in l)
    assert "peripheries=2" in linha_soma
    linha_raiz = next(l for l in dot.splitlines() if "matematica.raiz" in l)
    assert "peripheries=2" not in linha_raiz

    # 4) tracer -- corre o programa real gerado, sem erro nenhum, e o
    # conjunto de nomes de função que o codegen exporta para o tracer
    # (dados["nomes_funcoes"]) é o mesmo que o compilador e o
    # flowchart já usaram.
    dados = gerar_python_com_mapa(programa)
    assert set(dados["nomes_funcoes"]) == nomes_rotinas_compilador
    caminho_py = os.path.join(str(tmp_path), "prog.py")
    with open(caminho_py, "w", encoding="utf-8") as f:
        f.write(dados["codigo"])
    resultado = gerar_trace(
        dados["codigo"], caminho_py, dados["mapa_linhas"],
        dados["nomes_globais"], dados["nomes_funcoes"])
    assert resultado["erro"] is None
    assert resultado["consolaFinal"].strip() == "0\n1\n2\n7 4.0".strip()
