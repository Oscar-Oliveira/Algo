# -*- coding: utf-8 -*-
import pytest

import autenticacao
import relatorios


def test_criar_e_listar_relatorio():
    id_estudante = autenticacao.registar("estudante@exemplo.com", "password123")
    relatorios.criar_relatorio(id_estudante, "Botão de guardar não funciona.")

    lista = relatorios.listar_relatorios()
    assert len(lista) == 1
    assert lista[0]["email"] == "estudante@exemplo.com"
    assert lista[0]["descricao"] == "Botão de guardar não funciona."


def test_listar_relatorios_mais_recente_primeiro():
    id_estudante = autenticacao.registar("estudante@exemplo.com", "password123")
    relatorios.criar_relatorio(id_estudante, "primeiro")
    relatorios.criar_relatorio(id_estudante, "segundo")

    lista = relatorios.listar_relatorios()
    assert [r["descricao"] for r in lista] == ["segundo", "primeiro"]


def test_criar_relatorio_com_descricao_vazia_da_erro():
    id_estudante = autenticacao.registar("estudante@exemplo.com", "password123")
    with pytest.raises(ValueError):
        relatorios.criar_relatorio(id_estudante, "   ")


def test_apagar_relatorio():
    id_estudante = autenticacao.registar("estudante@exemplo.com", "password123")
    relatorios.criar_relatorio(id_estudante, "primeiro")
    relatorios.criar_relatorio(id_estudante, "segundo")
    id_a_apagar = relatorios.listar_relatorios()[0]["id"]

    relatorios.apagar_relatorio(id_a_apagar)

    lista = relatorios.listar_relatorios()
    assert len(lista) == 1
    assert lista[0]["descricao"] == "primeiro"


def test_apagar_relatorio_inexistente_nao_da_erro():
    relatorios.apagar_relatorio(999)
