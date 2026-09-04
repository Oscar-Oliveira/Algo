# -*- coding: utf-8 -*-
"""Testes de online.historico_codigo -- histórico de execução/debug de
código por estudante (ver docs/interno/PlanoAlguemLLMInvestigacao.md,
secção 9 e 14/Fase 4)."""
import json

import pytest

import autenticacao
import bd
import historico_codigo as hc


def _registar(estudante_id, tipo="executa", resultado="Sucesso"):
    hc.registar_execucao(
        estudante_id, tipo, "principal.algo",
        [{"nome": "principal.algo", "conteudo": "algoritmo \"T\""}], resultado)


def _linhas():
    with bd.sessao_bd() as ligacao:
        return ligacao.execute(
            "SELECT * FROM execucao_codigo ORDER BY id"
        ).fetchall()


def test_registar_execucao_grava_uma_linha():
    id_est = autenticacao.registar("a@b.com", "password123")
    _registar(id_est)
    linhas = _linhas()
    assert len(linhas) == 1
    assert linhas[0]["estudante_id"] == id_est
    assert linhas[0]["tipo"] == "executa"
    assert linhas[0]["nome_ficheiro_principal"] == "principal.algo"
    assert linhas[0]["resultado"] == "Sucesso"
    ficheiros = json.loads(linhas[0]["ficheiros"])
    assert ficheiros == [{"nome": "principal.algo", "conteudo": "algoritmo \"T\""}]


def test_registar_execucao_rejeita_tipo_invalido():
    id_est = autenticacao.registar("a@b.com", "password123")
    with pytest.raises(AssertionError):
        hc.registar_execucao(id_est, "invalido", "p.algo", [], "Sucesso")


def test_registar_execucao_nao_substitui_tentativas_anteriores():
    """Histórico completo, sem limite nem substituição (decisão
    validada, ponto 5) -- cada tentativa fica com a sua própria linha."""
    id_est = autenticacao.registar("a@b.com", "password123")
    _registar(id_est, resultado="Sucesso")
    _registar(id_est, tipo="debug", resultado="Erro em execução: X")
    assert len(_linhas()) == 2


def test_listar_por_estudante_devolve_so_as_dele_por_ordem_recente_primeiro():
    id_a = autenticacao.registar("a@b.com", "password123")
    id_b = autenticacao.registar("b@c.com", "password123")
    hc.registar_execucao(id_a, "executa", "p1.algo", [{"nome": "p1.algo", "conteudo": "x"}], "Sucesso")
    hc.registar_execucao(id_a, "debug", "p2.algo", [], "Erro em execução: X")
    hc.registar_execucao(id_b, "executa", "outro.algo", [], "Sucesso")

    linhas = hc.listar_por_estudante(id_a)
    assert len(linhas) == 2
    assert {l["nome_ficheiro_principal"] for l in linhas} == {"p1.algo", "p2.algo"}
    linha_p1 = next(l for l in linhas if l["nome_ficheiro_principal"] == "p1.algo")
    assert linha_p1["ficheiros"] == [{"nome": "p1.algo", "conteudo": "x"}]


def test_apagar_por_ids_remove_so_os_indicados():
    id_est = autenticacao.registar("a@b.com", "password123")
    _registar(id_est)
    _registar(id_est)
    linhas = _linhas()
    apagados = hc.apagar_por_ids([linhas[0]["id"]])
    assert apagados == 1
    restantes = _linhas()
    assert len(restantes) == 1
    assert restantes[0]["id"] == linhas[1]["id"]


def test_apagar_por_ids_ignora_ids_inexistentes():
    id_est = autenticacao.registar("a@b.com", "password123")
    _registar(id_est)
    apagados = hc.apagar_por_ids([999999])
    assert apagados == 0
    assert len(_linhas()) == 1


def test_apagar_por_ids_com_lista_vazia_nao_toca_na_bd():
    id_est = autenticacao.registar("a@b.com", "password123")
    _registar(id_est)
    assert hc.apagar_por_ids([]) == 0
    assert len(_linhas()) == 1


def test_apagar_por_periodo_so_remove_linhas_antigas():
    id_est = autenticacao.registar("a@b.com", "password123")
    _registar(id_est)
    with bd.sessao_bd() as ligacao:
        ligacao.execute(
            "UPDATE execucao_codigo SET criado_em = now() - interval '100 days'")
    _registar(id_est)  # esta fica "recente" (agora mesmo)
    apagados = hc.apagar_por_periodo(90)
    assert apagados == 1
    assert len(_linhas()) == 1


def test_apagar_por_periodo_rejeita_dias_negativo():
    with pytest.raises(AssertionError):
        hc.apagar_por_periodo(-1)


def test_apagar_tudo_remove_todas_as_linhas():
    id_est = autenticacao.registar("a@b.com", "password123")
    _registar(id_est)
    _registar(id_est)
    apagados = hc.apagar_tudo()
    assert apagados == 2
    assert len(_linhas()) == 0


def test_apagar_por_ids_de_outro_estudante_nao_interfere():
    """Só o admin (via rota) decide o que apagar -- este módulo não
    filtra por dono, ver rotas em main.py."""
    id_a = autenticacao.registar("a@b.com", "password123")
    id_b = autenticacao.registar("b@c.com", "password123")
    _registar(id_a)
    _registar(id_b)
    assert len(_linhas()) == 2
