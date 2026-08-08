# -*- coding: utf-8 -*-
"""Testes para a geração de fluxogramas (formato DOT / Graphviz)."""
import shutil
import subprocess
import tempfile
import os

import pytest

from algo_lang.compilador.parser import parse
from algo_lang.compilador.semantics import verificar
from algo_lang.tools.flowchart import gerar_dot

GRAPHVIZ_DISPONIVEL = shutil.which("dot") is not None


def _dot_para(codigo_algo, nome_funcao=None):
    import textwrap
    programa = parse(textwrap.dedent(codigo_algo))
    verificar(programa)
    corpo = programa.corpo
    if nome_funcao:
        alvo = next(f for f in programa.funcoes if f.nome == nome_funcao)
        corpo = alvo.corpo
    return gerar_dot(corpo, programa.nome)


def test_estrutura_basica_do_dot():
    dot = _dot_para("""
        algoritmo "T"
        inicio
            x:inteiro = 1
    """)
    assert dot.startswith("digraph Fluxograma {")
    assert dot.rstrip().endswith("}")
    assert 'shape=oval' in dot          # Início / Fim
    assert dot.count("shape=oval") == 2  # exatamente um Início e um Fim


def test_se_gera_um_diamante_e_dois_ramos():
    dot = _dot_para("""
        algoritmo "T"
        inicio
            x:inteiro = 1
            se x > 0 entao
                escrever("positivo")
            senao
                escrever("nao positivo")
    """)
    assert dot.count("shape=diamond") == 1
    assert '[label="sim"]' in dot
    assert '[label="não"]' in dot
    assert dot.count("shape=parallelogram") == 2   # os dois escrever()


def test_senao_se_gera_diamantes_encadeados():
    dot = _dot_para("""
        algoritmo "T"
        inicio
            nota:inteiro = 15
            se nota >= 18 entao
                escrever("Excelente")
            senao se nota >= 10 entao
                escrever("Aprovado")
            senao
                escrever("Reprovado")
    """)
    assert dot.count("shape=diamond") == 2


def test_ciclo_para_tem_aresta_de_retorno():
    dot = _dot_para("""
        algoritmo "T"
        inicio
            total:inteiro = 0
            i:inteiro = 0
            para i de 1 ate 10 fazer
                total = total + i
    """)
    linhas = dot.splitlines()
    assert dot.count("shape=diamond") == 1
    diamante_id = next(l.strip().split(" ")[0] for l in linhas if "shape=diamond" in l)
    # o nó de decisão do ciclo tem de ter pelo menos 2 arestas a apontar para ele:
    # uma de entrada no ciclo e uma de retorno depois do corpo (loop back)
    arestas_entrada = [l for l in linhas if f"-> {diamante_id}" in l]
    assert len(arestas_entrada) >= 2


def test_escolha_gera_um_ramo_por_caso_mais_contrario():
    dot = _dot_para("""
        algoritmo "T"
        inicio
            n:inteiro = 2
            escolher n
                caso 1
                    escrever("um")
                caso 2, 3
                    escrever("dois ou tres")
                contrario
                    escrever("outro")
    """)
    assert dot.count("shape=hexagon") == 1
    assert '[label="1"]' in dot
    assert '[label="2, 3"]' in dot
    assert '[label="contrario"]' in dot


def test_fluxograma_de_funcao_especifica():
    dot = _dot_para("""
        algoritmo "T"
        funcao dobro(x:inteiro):inteiro
            devolver x * 2
        inicio
            escrever(dobro(5))
    """, nome_funcao="dobro")
    assert "devolver" in dot
    assert dot.count("shape=oval") == 2


def test_dot_gerado_nao_tem_ids_de_no_duplicados():
    dot = _dot_para("""
        algoritmo "T"
        inicio
            i:inteiro = 0
            j:inteiro = 0
            para i de 1 ate 3 fazer
                para j de 1 ate 3 fazer
                    escrever(i, j)
    """)
    ids = []
    for linha in dot.splitlines():
        linha = linha.strip()
        if linha.startswith("n") and "[label=" in linha and "->" not in linha:
            ids.append(linha.split(" ")[0])
    assert len(ids) == len(set(ids)), "há nós com o mesmo identificador"


@pytest.mark.skipif(not GRAPHVIZ_DISPONIVEL, reason="Graphviz ('dot') não está instalado")
def test_graphviz_consegue_renderizar_o_dot_gerado():
    dot = _dot_para("""
        algoritmo "T"
        funcao classificar(nota:inteiro):cadeia
            se nota >= 10 entao
                devolver "Aprovado"
            senao
                devolver "Reprovado"
        inicio
            i:inteiro = 0
            para i de 1 ate 3 fazer
                escrever(i)
            enquanto falso fazer
                escrever("nunca")
            escrever(classificar(15))
    """)
    with tempfile.TemporaryDirectory() as pasta:
        caminho_dot = os.path.join(pasta, "grafo.dot")
        caminho_png = os.path.join(pasta, "grafo.png")
        with open(caminho_dot, "w", encoding="utf-8") as f:
            f.write(dot)
        resultado = subprocess.run(["dot", "-Tpng", caminho_dot, "-o", caminho_png],
                                    capture_output=True, text=True)
        assert resultado.returncode == 0, resultado.stderr
        assert os.path.getsize(caminho_png) > 0


def test_cli_gera_ficheiro_dot(tmp_path):
    import textwrap
    algo_path = tmp_path / "prog.algo"
    algo_path.write_text(textwrap.dedent("""
        algoritmo "T"
        inicio
            se verdadeiro entao
                escrever("ok")
    """), encoding="utf-8")
    resultado = subprocess.run(
        ["algo", "fluxograma", str(algo_path)], capture_output=True, text=True)
    assert resultado.returncode == 0, resultado.stderr
    assert (tmp_path / "prog" / "prog.dot").exists()


def test_cli_gera_um_fluxograma_por_rotina_alem_do_principal(tmp_path):
    import textwrap
    algo_path = tmp_path / "prog.algo"
    algo_path.write_text(textwrap.dedent("""
        algoritmo "T"
        funcao dobro(x:inteiro):inteiro
            devolver x * 2
        procedimento mostrar(msg:cadeia)
            escrever(msg)
        inicio
            escrever(dobro(5))
            mostrar("oi")
    """), encoding="utf-8")
    resultado = subprocess.run(
        ["algo", "fluxograma", str(algo_path)], capture_output=True, text=True)
    assert resultado.returncode == 0, resultado.stderr
    pasta = tmp_path / "prog"
    assert (pasta / "prog.dot").exists()
    assert (pasta / "prog_dobro.dot").exists()
    assert (pasta / "prog_mostrar.dot").exists()


def test_cli_com_funcao_gera_so_essa(tmp_path):
    import textwrap
    algo_path = tmp_path / "prog.algo"
    algo_path.write_text(textwrap.dedent("""
        algoritmo "T"
        funcao dobro(x:inteiro):inteiro
            devolver x * 2
        procedimento mostrar(msg:cadeia)
            escrever(msg)
        inicio
            escrever(dobro(5))
            mostrar("oi")
    """), encoding="utf-8")
    resultado = subprocess.run(
        ["algo", "fluxograma", str(algo_path), "--funcao", "dobro"],
        capture_output=True, text=True)
    assert resultado.returncode == 0, resultado.stderr
    pasta = tmp_path / "prog"
    assert (pasta / "prog_dobro.dot").exists()
    assert not (pasta / "prog.dot").exists()
    assert not (pasta / "prog_mostrar.dot").exists()


def test_chamada_a_funcao_definida_tem_contorno_duplo():
    """Chamadas a funções/procedimentos do próprio programa ficam com
    'peripheries=2' (símbolo de sub-rotina), para se distinguirem no
    fluxograma de instruções simples."""
    import textwrap
    programa = parse(textwrap.dedent("""
        algoritmo "T"
        funcao dobro(x:inteiro):inteiro
            devolver x * 2
        procedimento mostrar(msg:cadeia)
            escrever(msg)
        inicio
            total:inteiro = 0
            total = dobro(5)
            mostrar("oi")
    """))
    verificar(programa)
    nomes_rotinas = {f.nome for f in programa.funcoes}
    dot = gerar_dot(programa.corpo, programa.nome, nomes_rotinas)
    linhas = dot.splitlines()
    linha_total0 = next(l for l in linhas if '"total = 0"' in l)
    linha_dobro = next(l for l in linhas if "dobro(5)" in l)
    linha_mostrar = next(l for l in linhas if "mostrar(" in l)
    assert "peripheries=2" not in linha_total0
    assert "peripheries=2" in linha_dobro
    assert "peripheries=2" in linha_mostrar


def test_chamada_a_biblioteca_nao_tem_contorno_duplo():
    """math.raiz(...) não é uma rotina do utilizador -- não deve ganhar o
    contorno duplo (isso é só para chamar funções/procedimentos próprios)."""
    import textwrap
    programa = parse(textwrap.dedent("""
        algoritmo "T"
        importar Math
        inicio
            x:decimal = math.raiz(4.0)
    """))
    verificar(programa)
    nomes_rotinas = {f.nome for f in programa.funcoes}
    dot = gerar_dot(programa.corpo, programa.nome, nomes_rotinas)
    linha_x = next(l for l in dot.splitlines() if "math.raiz" in l)
    assert "peripheries=2" not in linha_x


def test_declaracao_a_partir_de_chamada_a_rotina_tem_contorno_duplo():
    import textwrap
    from algo_lang.compilador.parser import parse as _parse
    from algo_lang.compilador.semantics import verificar as _verificar
    programa = _parse(textwrap.dedent("""
        algoritmo "T"
        funcao dobro(n:inteiro):inteiro
            devolver n * 2
        inicio
            y:inteiro = dobro(5)
    """))
    _verificar(programa)
    nomes_rotinas = {f.nome for f in programa.funcoes}
    dot = gerar_dot(programa.corpo, programa.nome, nomes_rotinas)
    assert "y = dobro(5)" in dot
    assert dot.count("peripheries=2") == 1


def test_ler_gera_paralelogramo():
    dot = _dot_para("""
        algoritmo "T"
        inicio
            x:inteiro
            ler(x)
    """)
    assert 'label="ler(x)"' in dot
    assert "parallelogram" in dot


def test_chamada_solta_a_biblioteca_nao_tem_contorno_duplo():
    """Só chamadas a funções/procedimentos DO PRÓPRIO PROGRAMA ficam com
    contorno duplo -- uma chamada a biblioteca (tem '.') não conta como
    'rotina' para este efeito."""
    dot = _dot_para("""
        algoritmo "T"
        importar Cadeia
        inicio
            cadeia.maiusculas("ola")
    """)
    assert 'cadeia.maiusculas' in dot
    assert "peripheries=2" not in dot
