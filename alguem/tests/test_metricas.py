# -*- coding: utf-8 -*-
"""Testes de alguem.scripts.metricas."""
import sys

import pytest

from alguem.nucleo.registador import Registador
from alguem.scripts.metricas import gerar_relatorio, calcular_metricas_da_sessao


def _sessao_com(pasta_logs, id_estudante, eventos_fn):
    registador = Registador(id_estudante=id_estudante, pasta_logs=str(pasta_logs))
    eventos_fn(registador)
    return registador


def test_pasta_vazia_nao_rebenta(tmp_path):
    relatorio = gerar_relatorio(str(tmp_path))
    assert relatorio["globais"]["num_sessoes"] == 0
    assert relatorio["globais"]["num_estudantes"] == 0
    assert relatorio["globais"]["solution_leakage_rate_global"] is None


def test_linhas_vazias_no_jsonl_sao_ignoradas(tmp_path):
    """Um .jsonl com uma linha em branco no meio (ex: editado à mão)
    não deve rebentar nem contar como evento."""
    import json
    from alguem.scripts.metricas import carregar_eventos_por_sessao
    caminho = tmp_path / "sessao.jsonl"
    caminho.write_text(
        json.dumps({"id_sessao": "a", "tipo": "x"}) + "\n"
        "\n"
        + json.dumps({"id_sessao": "a", "tipo": "y"}) + "\n",
        encoding="utf-8")
    resultado = carregar_eventos_por_sessao(str(tmp_path))
    assert len(resultado["a"]) == 2


def test_solution_leakage_rate_de_uma_sessao(tmp_path):
    def eventos(r):
        r.inicio_sessao("openrouter", "x", {}, [])
        r.tentativa_guardiao(1, 1, "p", "codigo", "CODE", 7, False)
        r.tentativa_guardiao(1, 2, "p", "seguro", "SAFE", 1, True)
        r.resposta_final(1, "seguro", 2, False)
        r.fim_sessao()
    _sessao_com(tmp_path, "est-1", eventos)

    relatorio = gerar_relatorio(str(tmp_path))
    sessao = relatorio["por_sessao"][0]
    assert sessao["num_tentativas_totais"] == 2
    assert sessao["num_tentativas_rejeitadas"] == 1
    assert sessao["solution_leakage_rate"] == 0.5


def test_hint_escalation_maxima_e_o_nivel_mais_alto_atingido(tmp_path):
    def eventos(r):
        r.inicio_sessao("openrouter", "x", {}, [])
        r.tentativa_guardiao(1, 1, "p", "r1", "SAFE", 1, True)
        r.resposta_final(1, "r1", 1, False)
        r.tentativa_guardiao(2, 1, "p", "r2", "PARTIAL_SOLUTION", 5, True)
        r.resposta_final(2, "r2", 1, False)
    _sessao_com(tmp_path, "est-1", eventos)

    relatorio = gerar_relatorio(str(tmp_path))
    assert relatorio["por_sessao"][0]["hint_escalation_maxima"] == 5


def test_hint_dependency_e_a_media_de_turnos_por_sessao(tmp_path):
    def sessao_com_n_turnos(id_estudante, n):
        def eventos(r):
            r.inicio_sessao("openrouter", "x", {}, [])
            for i in range(1, n + 1):
                r.tentativa_guardiao(i, 1, f"p{i}", f"r{i}", "SAFE", 1, True)
                r.resposta_final(i, f"r{i}", 1, False)
            r.fim_sessao()
        _sessao_com(tmp_path, id_estudante, eventos)

    sessao_com_n_turnos("est-1", 2)
    sessao_com_n_turnos("est-2", 4)

    relatorio = gerar_relatorio(str(tmp_path))
    assert relatorio["globais"]["hint_dependency_media"] == 3.0  # (2+4)/2


def test_multiplas_sessoes_do_mesmo_estudante_contam_como_1_estudante(tmp_path):
    def eventos_simples(r):
        r.inicio_sessao("openrouter", "x", {}, [])
        r.fim_sessao()
    _sessao_com(tmp_path, "est-1", eventos_simples)
    _sessao_com(tmp_path, "est-1", eventos_simples)
    _sessao_com(tmp_path, "est-2", eventos_simples)

    relatorio = gerar_relatorio(str(tmp_path))
    assert relatorio["globais"]["num_sessoes"] == 3
    assert relatorio["globais"]["num_estudantes"] == 2


def test_sessao_vazia_de_eventos_devolve_dicionario_vazio():
    assert calcular_metricas_da_sessao([]) == {
        "id_sessao": None, "id_estudante": None, "fornecedor": None,
        "modelo": None, "num_turnos": 0, "num_tentativas_totais": 0,
        "num_tentativas_rejeitadas": 0, "solution_leakage_rate": None,
        "hint_escalation_maxima": None, "num_recusas_seguras": 0,
    }


def test_recusas_seguras_sao_contadas(tmp_path):
    def eventos(r):
        r.inicio_sessao("openrouter", "x", {}, [])
        r.resposta_final(1, "recusa", 2, veio_de_recusa_segura=True)
        r.resposta_final(2, "normal", 1, veio_de_recusa_segura=False)
    _sessao_com(tmp_path, "est-1", eventos)

    relatorio = gerar_relatorio(str(tmp_path))
    assert relatorio["por_sessao"][0]["num_recusas_seguras"] == 1


# ---------- main() (linha de comandos) ----------

from alguem.scripts.metricas import main


def test_main_pasta_nao_encontrada_termina_com_erro(monkeypatch, capsys, tmp_path):
    pasta_inexistente = str(tmp_path / "nao_existe")
    monkeypatch.setattr(sys, "argv", ["metricas.py", pasta_inexistente])
    with pytest.raises(SystemExit) as excinfo:
        main()
    assert excinfo.value.code == 1
    saida = capsys.readouterr().out
    assert "não encontrada" in saida


def test_main_pasta_vazia_mostra_mensagem_adequada(monkeypatch, capsys, tmp_path):
    monkeypatch.setattr(sys, "argv", ["metricas.py", str(tmp_path)])
    main()
    saida = capsys.readouterr().out
    assert "Sessões analisadas: 0" in saida
    assert "sem tentativas do guardião" in saida


def test_main_sem_argumentos_usa_a_pasta_por_omissao(monkeypatch, capsys, tmp_path):
    """Sem argumentos na linha de comandos, usa alguem/logs/ (a
    constante PASTA_LOGS_POR_OMISSAO do próprio módulo) -- confirma
    isto substituindo essa constante por uma pasta temporária vazia,
    em vez de mexer na pasta real do pacote."""
    import alguem.scripts.metricas as metricas_mod
    monkeypatch.setattr(metricas_mod, "PASTA_LOGS_POR_OMISSAO", str(tmp_path))
    monkeypatch.setattr(sys, "argv", ["metricas.py"])
    main()
    saida = capsys.readouterr().out
    assert "Sessões analisadas: 0" in saida


def test_main_com_dados_mostra_relatorio_completo(monkeypatch, capsys, tmp_path):
    def eventos(r):
        r.inicio_sessao("openrouter", "gpt-4o-mini", {}, [])
        r.tentativa_guardiao(1, 1, "p", "codigo", "CODE", 7, False)
        r.tentativa_guardiao(1, 2, "p", "seguro", "SAFE", 1, True)
        r.resposta_final(1, "seguro", 2, False)
        r.fim_sessao()
    _sessao_com(tmp_path, "est-1", eventos)

    monkeypatch.setattr(sys, "argv", ["metricas.py", str(tmp_path)])
    main()
    saida = capsys.readouterr().out
    assert "Sessões analisadas: 1" in saida
    assert "Estudantes distintos: 1" in saida
    assert "Solution Leakage Rate (global): 50.0%" in saida
    assert "Hint Dependency" in saida
    assert "Por sessão:" in saida
    assert "openrouter/gpt-4o-mini" in saida
    assert "leakage=50%" in saida
    assert "nível_max=7" in saida
