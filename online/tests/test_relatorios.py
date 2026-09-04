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


def test_novo_relatorio_comeca_nao_visto():
    id_estudante = autenticacao.registar("estudante@exemplo.com", "password123")
    relatorios.criar_relatorio(id_estudante, "primeiro")

    assert relatorios.listar_relatorios()[0]["visto"] is False
    assert relatorios.contar_nao_vistos() == 1


def test_marcar_todos_vistos_zera_a_contagem():
    id_estudante = autenticacao.registar("estudante@exemplo.com", "password123")
    relatorios.criar_relatorio(id_estudante, "primeiro")
    relatorios.criar_relatorio(id_estudante, "segundo")

    relatorios.marcar_todos_vistos()

    assert relatorios.contar_nao_vistos() == 0
    assert all(r["visto"] for r in relatorios.listar_relatorios())


def test_marcar_todos_vistos_e_idempotente_para_relatorios_ja_vistos():
    id_estudante = autenticacao.registar("estudante@exemplo.com", "password123")
    relatorios.criar_relatorio(id_estudante, "primeiro")
    relatorios.marcar_todos_vistos()

    relatorios.criar_relatorio(id_estudante, "segundo")
    relatorios.marcar_todos_vistos()

    assert relatorios.contar_nao_vistos() == 0
    assert all(r["visto"] for r in relatorios.listar_relatorios())
