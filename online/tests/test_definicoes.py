# -*- coding: utf-8 -*-
"""Testes de online.definicoes -- tabela chave/valor 'definicao',
incluindo os campos novos da Fase 3 (nivel_maximo_ajuda, usar_guardiao)."""
import pytest

import definicoes


def test_nivel_maximo_ajuda_usa_valor_por_omissao_sem_linha_guardada():
    assert definicoes.nivel_maximo_ajuda() == 5


def test_definir_nivel_maximo_ajuda_e_ler_de_volta():
    definicoes.definir_nivel_maximo_ajuda(2)
    assert definicoes.nivel_maximo_ajuda() == 2


@pytest.mark.parametrize("nivel", [-1, 7, 8])
def test_definir_nivel_maximo_ajuda_rejeita_fora_do_intervalo(nivel):
    """0-6, não 0-7 -- o nível 7 (Código) fica sempre bloqueado à parte
    (permite_gerar_codigo, fora de âmbito nesta fase), por isso não é
    uma opção válida aqui (ver definicoes.definir_nivel_maximo_ajuda)."""
    with pytest.raises(ValueError):
        definicoes.definir_nivel_maximo_ajuda(nivel)


def test_usar_guardiao_ativo_por_omissao_sem_linha_guardada():
    assert definicoes.usar_guardiao() is True


def test_definir_usar_guardiao_e_ler_de_volta():
    definicoes.definir_usar_guardiao(False)
    assert definicoes.usar_guardiao() is False
    definicoes.definir_usar_guardiao(True)
    assert definicoes.usar_guardiao() is True
