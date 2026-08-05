# -*- coding: utf-8 -*-
"""Testes de alguem.nucleo.registador -- o ficheiro JSON Lines por
sessão que suporta as métricas da investigação."""
import json
import os

from alguem.nucleo.registador import Registador


def _ler_eventos(caminho):
    with open(caminho, encoding="utf-8") as f:
        return [json.loads(linha) for linha in f if linha.strip()]


def test_cria_um_ficheiro_por_sessao(tmp_path):
    registador = Registador(id_estudante="est-1", pasta_logs=str(tmp_path))
    assert os.path.isfile(registador.caminho)
    assert registador.caminho.endswith(".jsonl")


def test_duas_sessoes_criam_dois_ficheiros_diferentes(tmp_path):
    r1 = Registador(id_estudante="est-1", pasta_logs=str(tmp_path))
    r2 = Registador(id_estudante="est-1", pasta_logs=str(tmp_path))
    assert r1.caminho != r2.caminho
    assert r1.id_sessao != r2.id_sessao


def test_inicio_sessao_regista_fornecedor_modelo_e_politica(tmp_path):
    registador = Registador(id_estudante="est-1", pasta_logs=str(tmp_path))
    registador.inicio_sessao(
        fornecedor="openrouter", modelo="gpt-4o-mini",
        politica={"modo": "socratic", "nivel_maximo_ajuda": 5},
        nomes_ficheiros_iniciais=["exercicio.algo"])
    eventos = _ler_eventos(registador.caminho)
    assert len(eventos) == 1
    assert eventos[0]["tipo"] == "inicio_sessao"
    assert eventos[0]["fornecedor"] == "openrouter"
    assert eventos[0]["modelo"] == "gpt-4o-mini"
    assert eventos[0]["politica"]["nivel_maximo_ajuda"] == 5
    assert eventos[0]["ficheiros_iniciais"] == ["exercicio.algo"]


def test_todos_os_eventos_tem_timestamp_id_sessao_e_id_estudante(tmp_path):
    registador = Registador(id_estudante="est-xyz", pasta_logs=str(tmp_path))
    registador.inicio_sessao("openrouter", "x", {}, [])
    registador.ficheiros_atualizados(["a.algo"])
    registador.fim_sessao()
    eventos = _ler_eventos(registador.caminho)
    assert len(eventos) == 3
    for evento in eventos:
        assert "timestamp" in evento
        assert evento["id_sessao"] == registador.id_sessao
        assert evento["id_estudante"] == "est-xyz"


def test_tentativa_guardiao_regista_todos_os_campos(tmp_path):
    registador = Registador(id_estudante="est-1", pasta_logs=str(tmp_path))
    registador.tentativa_guardiao(
        turno=1, tentativa=1, mensagem_estudante="como faço isto?",
        resposta_proposta="```algo\nescrever(1)\n```",
        classificacao="CODE", nivel_aproximado=7, aceitavel=False)
    eventos = _ler_eventos(registador.caminho)
    evento = eventos[0]
    assert evento["tipo"] == "tentativa_guardiao"
    assert evento["turno"] == 1
    assert evento["mensagem_estudante"] == "como faço isto?"
    assert evento["resposta_proposta"] == "```algo\nescrever(1)\n```"
    assert evento["classificacao"] == "CODE"
    assert evento["nivel_aproximado"] == 7
    assert evento["aceitavel"] is False


def test_resposta_rejeitada_fica_no_log_mesmo_nao_tendo_sido_mostrada(tmp_path):
    """Pedido explícito: as tentativas rejeitadas pelo guardião ficam
    registadas, mesmo nunca chegando ao estudante -- para investigar
    leakage (RQ5)."""
    registador = Registador(id_estudante="est-1", pasta_logs=str(tmp_path))
    registador.tentativa_guardiao(1, 1, "pergunta", "conteúdo perigoso revelado",
                                   "FULL_SOLUTION", 6, False)
    registador.resposta_final(1, "resposta segura final", num_tentativas=2,
                               veio_de_recusa_segura=True)
    eventos = _ler_eventos(registador.caminho)
    textos = [str(v) for e in eventos for v in e.values()]
    assert any("conteúdo perigoso revelado" in t for t in textos)


def test_novo_turno_incrementa_e_devolve_o_numero(tmp_path):
    registador = Registador(id_estudante="est-1", pasta_logs=str(tmp_path))
    assert registador.novo_turno() == 1
    assert registador.novo_turno() == 2
    assert registador.novo_turno() == 3


def test_fim_sessao_regista_o_numero_total_de_turnos(tmp_path):
    registador = Registador(id_estudante="est-1", pasta_logs=str(tmp_path))
    registador.novo_turno()
    registador.novo_turno()
    registador.fim_sessao()
    eventos = _ler_eventos(registador.caminho)
    evento_fim = eventos[-1]
    assert evento_fim["tipo"] == "fim_sessao"
    assert evento_fim["num_turnos"] == 2


def test_eventos_sao_persistidos_imediatamente_linha_a_linha(tmp_path):
    """Cada evento tem de ficar em disco assim que é escrito (flush),
    não só quando a sessão fecha -- para não se perder nada se o
    processo for interrompido a meio."""
    registador = Registador(id_estudante="est-1", pasta_logs=str(tmp_path))
    registador.ficheiros_atualizados(["a.algo"])
    # lê o ficheiro sem fechar o registador -- confirma que já lá está
    eventos = _ler_eventos(registador.caminho)
    assert len(eventos) == 1


def test_ficheiro_e_valido_json_lines_uma_linha_por_evento(tmp_path):
    registador = Registador(id_estudante="est-1", pasta_logs=str(tmp_path))
    registador.inicio_sessao("openrouter", "x", {}, [])
    registador.ficheiros_atualizados(["a.algo"])
    registador.fim_sessao()
    with open(registador.caminho, encoding="utf-8") as f:
        linhas = [l for l in f.readlines() if l.strip()]
    assert len(linhas) == 3
    for linha in linhas:
        json.loads(linha)  # não levanta exceção -- é JSON válido
