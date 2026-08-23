# -*- coding: utf-8 -*-
"""Testes para as funcionalidades adicionadas na última revisão: constante,
comentários multi-linha, literais de vetor, afirmar e erros de execução
amigáveis (traduzidos para português em vez do traceback Python cru)."""
import subprocess
import sys
import textwrap

import pytest

from algo_lang.compilador.lexer import tokenizar
from algo_lang.compilador.parser import ErroSintatico
from algo_lang.compilador.semantics import ErroSemantico
from apoio import compilar, executar


# ---------- constante ----------

def test_constante_pode_ser_lida():
    saida = executar("""
        algoritmo "T"
        constante PI:decimal = 3.14
        inicio
            escrever(PI)
    """)
    assert saida.strip() == "3.14"


def test_constante_local_a_funcao():
    saida = executar("""
        algoritmo "T"
        funcao circulo(raio:decimal):decimal
            constante PI:decimal = 3.14159
            retornar PI * raio * raio
        inicio
            escrever(circulo(2.0))
    """)
    assert saida.strip() == "12.56636"


def test_constante_nao_pode_ser_reatribuida():
    with pytest.raises(ErroSemantico, match="é uma constante"):
        compilar("""
            algoritmo "T"
            constante MAX:inteiro = 10
            inicio
                MAX = 20
        """)


def test_constante_nao_pode_ser_alvo_de_ler():
    with pytest.raises(ErroSemantico, match="é uma constante"):
        compilar("""
            algoritmo "T"
            constante MAX:inteiro = 10
            inicio
                ler(MAX)
        """)


def test_constante_nao_pode_ser_passada_por_referencia():
    with pytest.raises(ErroSemantico, match="constante"):
        compilar("""
            algoritmo "T"
            constante MAX:inteiro = 10
            procedimento inc(ref x:inteiro)
                x = x + 1
            inicio
                inc(MAX)
        """)


def test_constante_tem_de_ter_valor_inicial():
    with pytest.raises(ErroSintatico):
        compilar("""
            algoritmo "T"
            inicio
                constante SEM_VALOR:inteiro
        """)


def test_constante_nao_pode_ser_vetor():
    with pytest.raises(ErroSintatico):
        compilar("""
            algoritmo "T"
            inicio
                constante V:inteiro[3] = {1, 2, 3}
        """)


def test_parametro_pode_sombrear_constante_global():
    """Uma função pode ter um parâmetro com o mesmo nome de uma constante
    global -- dentro da função, o parâmetro (não constante) é que conta."""
    saida = executar("""
        algoritmo "T"
        constante X:inteiro = 1
        funcao dobro(x:inteiro):inteiro
            retornar x * 2
        inicio
            escrever(dobro(21))
    """)
    assert saida.strip() == "42"


# ---------- comentários multi-linha ----------

def test_comentario_bloco_e_ignorado():
    saida = executar("""
        algoritmo "T"
        /* isto é
           um comentário
           de várias linhas */
        inicio
            escrever("depois do comentário")
    """)
    assert saida.strip() == "depois do comentário"


def test_comentario_bloco_preserva_numero_de_linhas():
    codigo = textwrap.dedent("""\
        algoritmo "T"
        /* linha 2
           linha 3
           linha 4 */
        inicio
            x:inteiro = "erro"
    """)
    tokens = tokenizar(codigo)
    # a atribuição inválida está na linha 6 do texto original
    with pytest.raises(ErroSemantico, match="linha 6"):
        compilar(codigo)


def test_comentario_bloco_no_meio_de_uma_linha():
    saida = executar("""
        algoritmo "T"
        inicio
            x:inteiro = 1 /* comentário */ + 2
            escrever(x)
    """)
    assert saida.strip() == "3"


def test_comentario_linha_simples_continua_a_funcionar():
    saida = executar("""
        algoritmo "T"
        inicio
            escrever("ok") // comentário de uma linha
    """)
    assert saida.strip() == "ok"


def test_comentario_linha_com_barra_asterisco_nao_e_lido_como_bloco():
    """Um '/*' que apareça DEPOIS de um '//' na mesma linha é só texto do
    comentário de linha -- não deve abrir um comentário de bloco real e
    engolir o código a seguir."""
    saida = executar("""
        algoritmo "T"
        inicio
            // nota: 2 / 4 * 3 nao e um bloco, mas parece um /* aqui
            x:inteiro = 5
            escrever(x)
    """)
    assert saida.strip() == "5"


# ---------- literais de vetor ----------

def test_vetor_literal_1d():
    saida = executar("""
        algoritmo "T"
        inicio
            v:inteiro[3] = {10, 20, 30}
            escrever(v[0], ",", v[1], ",", v[2])
    """)
    assert saida.strip() == "10,20,30"


def test_vetor_literal_2d():
    saida = executar("""
        algoritmo "T"
        inicio
            m:inteiro[2][2] = {{1, 2}, {3, 4}}
            escrever(m[0][0], ",", m[0][1], ",", m[1][0], ",", m[1][1])
    """)
    assert saida.strip() == "1,2,3,4"


def test_vetor_literal_tipo_incompativel_da_erro():
    with pytest.raises(ErroSemantico):
        compilar("""
            algoritmo "T"
            inicio
                v:inteiro[3] = {1, "dois", 3}
        """)


def test_vetor_literal_aninhamento_errado_da_erro():
    """AL-16: esta verificação de forma passou do parser (ErroSintatico)
    para semantics.py (ErroSemantico) -- o parser deixou de saber de
    antemão quantas dimensões esperar, para poder aceitar '{...}' como
    expressão geral (ex.: argumento de uma chamada), não só como valor
    inicial de uma declaração."""
    with pytest.raises(ErroSemantico, match="dimensões"):
        compilar("""
            algoritmo "T"
            inicio
                v:inteiro[3] = {1, {2, 3}, 4}
        """)


def test_vetor_literal_em_variavel_nao_vetor_da_erro():
    with pytest.raises(ErroSemantico, match="vetor"):
        compilar("""
            algoritmo "T"
            inicio
                x:inteiro = {1, 2, 3}
        """)


# ---------- afirmar ----------

def test_afirmar_verdadeiro_nao_produz_saida():
    saida = executar("""
        algoritmo "T"
        inicio
            afirmar 1 + 1 == 2
            escrever("depois")
    """)
    assert saida.strip() == "depois"


def test_afirmar_falso_termina_o_programa():
    codigo = """
        algoritmo "T"
        inicio
            afirmar 1 == 2, "um não é dois"
            escrever("nunca chega aqui")
    """
    codigo_py = compilar(codigo)
    resultado = subprocess.run(
        [sys.executable, "-c", codigo_py], capture_output=True, text=True,
        encoding="utf-8", timeout=10)
    assert resultado.returncode == 1
    assert "um não é dois" in resultado.stdout
    assert "nunca chega aqui" not in resultado.stdout


def test_afirmar_condicao_nao_booleana_da_erro():
    with pytest.raises(ErroSemantico, match="booleana"):
        compilar("""
            algoritmo "T"
            inicio
                afirmar 5
        """)


def test_afirmar_mensagem_nao_textual_da_erro():
    with pytest.raises(ErroSemantico, match="texto"):
        compilar("""
            algoritmo "T"
            inicio
                afirmar verdadeiro, 123
        """)


# ---------- erros de execução amigáveis ----------

def _executar_sem_levantar(codigo_algo):
    codigo_py = compilar(codigo_algo)
    return subprocess.run(
        [sys.executable, "-c", codigo_py], capture_output=True, text=True,
        encoding="utf-8", timeout=10)


def test_indice_fora_dos_limites_da_mensagem_amigavel():
    resultado = _executar_sem_levantar("""
        algoritmo "T"
        inicio
            v:inteiro[3] = {1, 2, 3}
            escrever(v[10])
    """)
    assert resultado.returncode == 1
    assert "índice fora dos limites" in resultado.stdout
    assert "Traceback" not in resultado.stdout


def test_divisao_por_zero_da_mensagem_amigavel():
    resultado = _executar_sem_levantar("""
        algoritmo "T"
        inicio
            x:inteiro = 5
            y:inteiro = 0
            escrever(x / y)
    """)
    assert resultado.returncode == 1
    assert "divisão por zero" in resultado.stdout
    assert "Traceback" not in resultado.stdout


def test_recursao_infinita_da_mensagem_amigavel():
    resultado = _executar_sem_levantar("""
        algoritmo "T"
        funcao f(n:inteiro):inteiro
            retornar f(n + 1)
        inicio
            escrever(f(1))
    """)
    assert resultado.returncode == 1
    assert "recursão infinita" in resultado.stdout
    assert "Traceback" not in resultado.stdout


def test_variavel_global_continua_visivel_apos_wrapper_de_erros():
    """Regressão: envolver o corpo principal em _algo_programa() não pode
    quebrar a visibilidade de variáveis globais dentro de funções."""
    saida = executar("""
        algoritmo "T"
        contador:inteiro = 42
        procedimento mostra()
            escrever(contador)
        inicio
            mostra()
    """)
    assert saida.strip() == "42"


# ---------- debug: variável declarada depois do ciclo não pode aparecer ----------

# nota: os testes de debug (variável só aparece depois de atribuída,
# globais+locais dentro de função) migraram para test_tracer.py, porque
# essa é agora a responsabilidade de algo_lang.tools.tracer, não do
# compilador -- ver test_debug_nao_mostra_variavel_antes_de_atribuida e
# test_debug_mostra_globais_e_locais_dentro_de_funcao nesse ficheiro.


# ---------- vetores com mais de 2 dimensões ----------

def test_vetor_3d():
    saida = executar("""
        algoritmo "T"
        inicio
            cubo:inteiro[2][2][2]
            cubo[0][0][0] = 111
            cubo[1][1][1] = 222
            escrever(cubo[0][0][0], ",", cubo[1][1][1], ",", cubo[0][1][0])
    """)
    assert saida.strip() == "111,222,0"


def test_vetor_literal_3d():
    saida = executar("""
        algoritmo "T"
        inicio
            c:inteiro[2][2][2] = {{{1,2},{3,4}},{{5,6},{7,8}}}
            escrever(c[0][0][0], ",", c[1][1][1])
    """)
    assert saida.strip() == "1,8"


# ---------- literal de estrutura ----------

def test_estrutura_literal_completo():
    saida = executar("""
        algoritmo "T"
        estrutura Ponto
            x:inteiro
            y:inteiro
        inicio
            p:Ponto = {x: 3, y: 4}
            escrever(p.x, ",", p.y)
    """)
    assert saida.strip() == "3,4"


def test_estrutura_literal_parcial_usa_omissao_nos_restantes():
    saida = executar("""
        algoritmo "T"
        estrutura Ponto
            x:inteiro
            y:inteiro
        inicio
            p:Ponto = {x: 10}
            escrever(p.x, ",", p.y)
    """)
    assert saida.strip() == "10,0"


def test_estrutura_literal_campo_inexistente_da_erro():
    with pytest.raises(ErroSemantico, match="não tem nenhum campo"):
        compilar("""
            algoritmo "T"
            estrutura Ponto
                x:inteiro
            inicio
                p:Ponto = {x: 1, z: 2}
        """)


def test_estrutura_literal_em_tipo_nao_estrutura_da_erro():
    with pytest.raises(ErroSemantico, match="não é uma estrutura"):
        compilar("""
            algoritmo "T"
            inicio
                x:inteiro = {y: 1}
        """)


def test_estrutura_literal_tipo_de_campo_incompativel_da_erro():
    with pytest.raises(ErroSemantico):
        compilar("""
            algoritmo "T"
            estrutura Ponto
                x:inteiro
            inicio
                p:Ponto = {x: "texto"}
        """)
