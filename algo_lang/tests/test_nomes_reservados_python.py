# -*- coding: utf-8 -*-
"""Testes para a validação de nomes contra palavras reservadas do PYTHON
(não do ALGO) -- bug real encontrado na auditoria: um identificador como
'class' é válido em ALGO mas gera Python sintaticamente inválido."""
import textwrap
import pytest

from apoio import compilar
from algo_lang.compilador.semantics import ErroSemantico


@pytest.mark.parametrize("codigo,palavra", [
    ('algoritmo "T"\ninicio\n    class:inteiro = 5\n    escrever(class)\n', "class"),
    ('algoritmo "T"\nfuncao f(return:inteiro):inteiro\n    devolver return\ninicio\n    escrever(f(1))\n', "return"),
    ('algoritmo "T"\nestrutura P\n    import:inteiro\ninicio\n    escrever(1)\n', "import"),
    ('algoritmo "T"\nfuncao def():inteiro\n    devolver 1\ninicio\n    escrever(def())\n', "def"),
    ('algoritmo "T"\ninicio\n    para for de 1 ate 3 fazer\n        escrever(for)\n', "for"),
    ('algoritmo "T"\nestrutura class\n    x:inteiro\ninicio\n    escrever(1)\n', "class"),
])
def test_nome_colide_com_palavra_reservada_do_python_da_erro(codigo, palavra):
    with pytest.raises(ErroSemantico, match="palavra reservada do Python"):
        compilar(codigo)


def test_nome_parecido_mas_nao_reservado_nao_e_bloqueado():
    """'matched', 'typed', etc. não são palavras reservadas -- só
    PARECEM. Não podem ser rejeitados por engano."""
    codigo_py = compilar("""
        algoritmo "T"
        inicio
            matched:inteiro = 5
            escrever(matched)
    """)
    assert "matched = 5" in codigo_py


def test_soft_keyword_e_permitido_como_identificador():
    """'match'/'type'/'case' só são especiais em contextos muito
    específicos do Python -- como identificadores normais continuam a
    ser Python válido, por isso o ALGO não os deve bloquear."""
    codigo_py = compilar("""
        algoritmo "T"
        inicio
            match:inteiro = 5
            escrever(match)
    """)
    assert "match = 5" in codigo_py


