# -*- coding: utf-8 -*-
import pytest

import autenticacao
import grupos


def test_criar_grupo_devolve_codigo_em_claro():
    resultado = grupos.criar_grupo("Grupo A")
    assert resultado["nome"] == "Grupo A"
    assert len(resultado["codigo"]) == grupos._TAMANHO_CODIGO


def test_criar_grupo_com_nome_duplicado_da_erro():
    grupos.criar_grupo("Grupo A")
    with pytest.raises(grupos.ErroGrupo, match="Já existe"):
        grupos.criar_grupo("Grupo A")


def test_verificar_codigo_correto_devolve_id_do_grupo():
    resultado = grupos.criar_grupo("Grupo A")
    assert grupos.verificar_codigo(resultado["codigo"]) == resultado["id"]


def test_verificar_codigo_errado_devolve_none():
    grupos.criar_grupo("Grupo A")
    assert grupos.verificar_codigo("codigo-que-nao-existe") is None


def test_verificar_codigo_de_grupo_desativado_devolve_none():
    resultado = grupos.criar_grupo("Grupo A")
    grupos.desativar_grupo(resultado["id"])
    assert grupos.verificar_codigo(resultado["codigo"]) is None


def test_ver_codigo_devolve_o_codigo_em_claro():
    resultado = grupos.criar_grupo("Grupo A")
    assert grupos.ver_codigo(resultado["id"]) == resultado["codigo"]


def test_ver_codigo_de_grupo_inexistente_da_erro():
    with pytest.raises(grupos.ErroGrupo, match="não encontrado"):
        grupos.ver_codigo(999)


def test_regenerar_codigo_invalida_o_antigo():
    resultado = grupos.criar_grupo("Grupo A")
    codigo_antigo = resultado["codigo"]
    codigo_novo = grupos.regenerar_codigo(resultado["id"])

    assert codigo_novo != codigo_antigo
    assert grupos.verificar_codigo(codigo_antigo) is None
    assert grupos.verificar_codigo(codigo_novo) == resultado["id"]
    assert grupos.ver_codigo(resultado["id"]) == codigo_novo


def test_editar_grupo_muda_o_nome():
    resultado = grupos.criar_grupo("Grupo A")
    grupos.editar_grupo(resultado["id"], "Grupo A (renomeada)")
    lista = grupos.listar_grupos()
    assert lista[0]["nome"] == "Grupo A (renomeada)"


def test_ativar_e_desativar_grupo():
    resultado = grupos.criar_grupo("Grupo A")
    grupos.desativar_grupo(resultado["id"])
    assert grupos.listar_grupos()[0]["ativo"] is False
    grupos.ativar_grupo(resultado["id"])
    assert grupos.listar_grupos()[0]["ativo"] is True


def test_apagar_grupo_sem_membros():
    resultado = grupos.criar_grupo("Grupo A")
    grupos.apagar_grupo(resultado["id"])
    assert grupos.listar_grupos() == []


def test_apagar_grupo_com_membros_da_erro():
    resultado = grupos.criar_grupo("Grupo A")
    autenticacao.registar("aluno@escola.pt", "password123", codigo_grupo=resultado["codigo"])
    with pytest.raises(grupos.ErroGrupo, match="membros associados"):
        grupos.apagar_grupo(resultado["id"])
    assert len(grupos.listar_grupos()) == 1


def test_apagar_grupo_inexistente_da_erro():
    with pytest.raises(grupos.ErroGrupo, match="não encontrado"):
        grupos.apagar_grupo(999)


def test_listar_grupos_inclui_contagem_de_membros():
    resultado = grupos.criar_grupo("Grupo A")
    autenticacao.registar("a@escola.pt", "password123", codigo_grupo=resultado["codigo"])
    autenticacao.registar("b@escola.pt", "password123", codigo_grupo=resultado["codigo"])
    lista = grupos.listar_grupos()
    assert lista[0]["num_membros"] == 2


def test_reatribuir_grupo_move_o_estudante():
    grupo1 = grupos.criar_grupo("Grupo A")
    grupo2 = grupos.criar_grupo("Grupo B")
    id_est = autenticacao.registar("aluno@escola.pt", "password123", codigo_grupo=grupo1["codigo"])

    anterior = grupos.reatribuir_grupo(id_est, grupo2["id"])
    assert anterior == grupo1["id"]
    assert grupos.listar_grupos()[1]["num_membros"] == 1  # Grupo B (ordenado por nome)


def test_reatribuir_grupo_para_sem_grupo():
    grupo1 = grupos.criar_grupo("Grupo A")
    id_est = autenticacao.registar("aluno@escola.pt", "password123", codigo_grupo=grupo1["codigo"])
    grupos.reatribuir_grupo(id_est, None)
    assert grupos.listar_grupos()[0]["num_membros"] == 0


def test_reatribuir_grupo_para_grupo_inativo_da_erro():
    grupo1 = grupos.criar_grupo("Grupo A")
    grupo2 = grupos.criar_grupo("Grupo B")
    grupos.desativar_grupo(grupo2["id"])
    id_est = autenticacao.registar("aluno@escola.pt", "password123", codigo_grupo=grupo1["codigo"])
    with pytest.raises(grupos.ErroGrupo, match="inválido ou inativo"):
        grupos.reatribuir_grupo(id_est, grupo2["id"])


def test_reatribuir_grupo_de_estudante_inexistente_da_erro():
    with pytest.raises(grupos.ErroGrupo, match="não encontrado"):
        grupos.reatribuir_grupo(999, None)


def test_exportar_membros_csv():
    resultado = grupos.criar_grupo("Grupo A")
    autenticacao.registar("aluno@escola.pt", "password123", codigo_grupo=resultado["codigo"])
    csv_texto = grupos.exportar_membros_csv(resultado["id"])
    assert "aluno@escola.pt" in csv_texto
    assert "email" in csv_texto.splitlines()[0]


def test_exportar_membros_csv_grupo_inexistente_da_erro():
    with pytest.raises(grupos.ErroGrupo, match="não encontrado"):
        grupos.exportar_membros_csv(999)
