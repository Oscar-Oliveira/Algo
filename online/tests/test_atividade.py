# -*- coding: utf-8 -*-
import atividade
import autenticacao
import grupos


def test_registar_e_listar_evento():
    id_est = autenticacao.registar("a@b.com", "password123")
    atividade.registar_evento("login", id_est, id_est)
    resultado = atividade.listar_eventos()
    assert resultado["total"] == 1
    assert resultado["eventos"][0]["tipo"] == "login"
    assert resultado["eventos"][0]["ator_email"] == "a@b.com"


def test_registar_evento_com_detalhes():
    atividade.registar_evento("login_falhado", detalhes={"email": "x@y.com"})
    evento = atividade.listar_eventos()["eventos"][0]
    assert evento["detalhes"] == {"email": "x@y.com"}


def test_listar_eventos_filtra_por_utilizador():
    id1 = autenticacao.registar("a@b.com", "password123")
    id2 = autenticacao.registar("c@d.com", "password123")
    atividade.registar_evento("login", id1, id1)
    atividade.registar_evento("login", id2, id2)

    resultado = atividade.listar_eventos(estudante_id=id1)
    assert resultado["total"] == 1
    assert resultado["eventos"][0]["ator_id"] == id1


def test_listar_eventos_filtra_por_grupo():
    grupo = grupos.criar_grupo("Grupo A")
    id_est = autenticacao.registar("a@b.com", "password123", codigo_grupo=grupo["codigo"])
    atividade.registar_evento("registo", id_est, id_est, grupo["id"])
    atividade.registar_evento("login", id_est, id_est)  # sem grupo

    resultado = atividade.listar_eventos(grupo_id=grupo["id"])
    assert resultado["total"] == 1
    assert resultado["eventos"][0]["tipo"] == "registo"


def test_listar_eventos_filtra_por_tipo():
    id_est = autenticacao.registar("a@b.com", "password123")
    atividade.registar_evento("login", id_est, id_est)
    atividade.registar_evento("login_falhado", detalhes={"email": "a@b.com"})

    resultado = atividade.listar_eventos(tipo="login_falhado")
    assert resultado["total"] == 1
    assert resultado["eventos"][0]["tipo"] == "login_falhado"


def test_listar_eventos_paginado():
    id_est = autenticacao.registar("a@b.com", "password123")
    for _ in range(5):
        atividade.registar_evento("login", id_est, id_est)

    pagina1 = atividade.listar_eventos(pagina=1, por_pagina=2)
    assert len(pagina1["eventos"]) == 2
    assert pagina1["total"] == 5
    pagina3 = atividade.listar_eventos(pagina=3, por_pagina=2)
    assert len(pagina3["eventos"]) == 1


def test_apagar_eventos_remove_definitivamente():
    id_est = autenticacao.registar("a@b.com", "password123")
    atividade.registar_evento("login", id_est, id_est)
    atividade.registar_evento("login", id_est, id_est)
    ids = [e["id"] for e in atividade.listar_eventos()["eventos"]]

    apagados = atividade.apagar_eventos([ids[0]])
    assert apagados == 1
    assert atividade.listar_eventos()["total"] == 1


def test_apagar_eventos_ids_inexistentes_nao_da_erro():
    assert atividade.apagar_eventos([999, 1000]) == 0


def test_apagar_eventos_lista_vazia_nao_faz_nada():
    id_est = autenticacao.registar("a@b.com", "password123")
    atividade.registar_evento("login", id_est, id_est)
    assert atividade.apagar_eventos([]) == 0
    assert atividade.listar_eventos()["total"] == 1


def test_exportar_csv_inclui_cabecalho_e_eventos():
    id_est = autenticacao.registar("a@b.com", "password123")
    atividade.registar_evento("login", id_est, id_est)
    csv_texto = atividade.exportar_csv()
    linhas = csv_texto.splitlines()
    assert linhas[0].startswith("id,tipo,criado_em")
    assert "a@b.com" in csv_texto
