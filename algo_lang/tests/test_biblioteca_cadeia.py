# -*- coding: utf-8 -*-
"""Testes da biblioteca 'cadeia' -- funções 'procurar'/'substituir'/
'dividir', acrescentadas na ronda 14 de auditoria (2026-08-22): a
biblioteca era minimalista de propósito (comprimento/maiusculas/
minusculas/inverter/subcadeia/caracter), sem estas três, o que force
o estudante a implementar pesquisa/substituição/divisão como
exercício -- mantido deliberadamente como escolha pedagógica noutros
pontos, mas adicionadas aqui a pedido do maintainer."""
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


# ---------- procurar ----------

def test_procurar_encontra_a_primeira_ocorrencia():
    saida = executar("""
        algoritmo "T"
        importar Cadeia
        inicio
            escrever(cadeia.procurar("ola mundo mundo", "mundo"))
    """)
    assert saida.strip() == "4"


def test_procurar_nao_encontrado_devolve_menos_um():
    saida = executar("""
        algoritmo "T"
        importar Cadeia
        inicio
            escrever(cadeia.procurar("ola mundo", "zzz"))
    """)
    assert saida.strip() == "-1"


def test_procurar_texto_vazio_da_erro_amigavel():
    """Ronda 15: 'sub' vazio não tinha guarda nenhuma -- str.find do
    Python com um texto vazio "encontra-o" em toda a posição (devolve
    sempre 0), inconsistente com 'substituir'/'dividir', que já rejeitam
    o caso análogo (texto/separador vazio) explicitamente."""
    resultado = _correr_esperando_erro("""\
algoritmo "T"
importar Cadeia
inicio
    escrever(cadeia.procurar("banana", ""))
""")
    assert resultado.returncode == 1
    assert "Traceback" not in resultado.stdout
    assert "não pode ser vazio" in resultado.stdout


# ---------- substituir ----------

def test_substituir_troca_todas_as_ocorrencias():
    saida = executar("""
        algoritmo "T"
        importar Cadeia
        inicio
            escrever(cadeia.substituir("banana", "a", "o"))
    """)
    assert saida.strip() == "bonono"


def test_substituir_texto_antigo_vazio_da_erro_amigavel():
    resultado = _correr_esperando_erro("""\
algoritmo "T"
importar Cadeia
inicio
    escrever(cadeia.substituir("banana", "", "o"))
""")
    assert resultado.returncode == 1
    assert "Traceback" not in resultado.stdout
    assert "não pode ser vazio" in resultado.stdout


# ---------- dividir ----------

def test_dividir_separa_pelo_separador():
    saida = executar("""
        algoritmo "T"
        importar Cadeia
        inicio
            partes:cadeia[3] = cadeia.dividir("um,dois,tres", ",")
            escrever(partes[0], "-", partes[1], "-", partes[2])
    """)
    assert saida.strip() == "um-dois-tres"


def test_dividir_separador_vazio_da_erro_amigavel():
    resultado = _correr_esperando_erro("""\
algoritmo "T"
importar Cadeia
inicio
    partes:cadeia[1] = cadeia.dividir("abc", "")
    escrever(partes[0])
""")
    assert resultado.returncode == 1
    assert "Traceback" not in resultado.stdout
    assert "separador" in resultado.stdout


def test_dividir_com_mais_partes_do_que_o_tamanho_declarado_da_erro_amigavel():
    """Ronda 15: o tamanho declarado ('partes:cadeia[N]') nunca era
    validado contra o tamanho REAL devolvido em runtime -- um resultado
    com MAIS elementos do que o declarado ficava silenciosamente legível
    além do tamanho declarado (ex.: 'partes[3]' com N=2)."""
    resultado = _correr_esperando_erro("""\
algoritmo "T"
importar Cadeia
inicio
    partes:cadeia[2] = cadeia.dividir("um,dois,tres,quatro", ",")
    escrever(partes[0])
""")
    assert resultado.returncode == 1
    assert "Traceback" not in resultado.stdout
    assert "4 elemento" in resultado.stdout
    assert "espera 2" in resultado.stdout


def test_dividir_com_menos_partes_do_que_o_tamanho_declarado_da_erro_amigavel():
    resultado = _correr_esperando_erro("""\
algoritmo "T"
importar Cadeia
inicio
    partes:cadeia[5] = cadeia.dividir("um,dois,tres,quatro", ",")
    escrever(partes[0])
""")
    assert resultado.returncode == 1
    assert "Traceback" not in resultado.stdout
    assert "4 elemento" in resultado.stdout
    assert "espera 5" in resultado.stdout


def test_dividir_usado_como_valor_escalar_da_erro_semantico():
    """'cadeia.dividir' devolve um vetor -- primeira função de biblioteca
    a fazê-lo (ver dims_retorno em bibliotecas/cadeia.py) -- por isso tem
    de ser indexado, tal como um vetor devolvido por uma função normal."""
    with pytest.raises(ErroSemantico, match="devolve um vetor"):
        compilar("""
            algoritmo "T"
            importar Cadeia
            inicio
                escrever(cadeia.dividir("a,b", ","))
        """)


def test_dividir_pode_ser_indexado_inline_sem_variavel_intermedia():
    """Ronda 15: até aqui, o resultado de 'cadeia.dividir' só podia ser
    consumido através de uma variável intermédia -- 'A.Chamada' não
    tinha campo 'acessos'. Agora suporta indexação/acesso a campo
    diretamente sobre o resultado da chamada."""
    saida = executar("""
        algoritmo "T"
        importar Cadeia
        inicio
            escrever(cadeia.dividir("um,dois,tres", ",")[1])
    """)
    assert saida.strip() == "dois"
