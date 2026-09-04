# -*- coding: utf-8 -*-
"""Testes de online.investigacao -- dashboard/relatório/exportação e
vista por estudante (ver docs/interno/PlanoAlguemLLMInvestigacao.md,
secção 6/10, Fase 5), com foco no controlo de acesso por grupo
(secção 15)."""
import json

import pytest

import autenticacao
import grupos
import historico_codigo
import investigacao as inv
from alguem.nucleo.registador import Registador


def _sessao(pasta_logs, email, **kwargs_inicio):
    r = Registador(id_estudante=email, pasta_logs=str(pasta_logs))
    r.inicio_sessao("openrouter", "gpt-4o-mini", {}, [], **kwargs_inicio)
    r.fim_sessao()


# ---------- controlo de acesso (secção 15) ----------

def test_admin_global_ve_sessoes_de_todos_os_grupos(tmp_path):
    admin_id = autenticacao.registar("admin@escola.pt", "password123")
    autenticacao.registar("a@b.com", "password123")
    _sessao(tmp_path, "a@b.com", grupo="Turma A")
    _sessao(tmp_path, "b@c.com", grupo="Turma B")
    sessoes = inv.listar_sessoes(admin_id, admin_global=True, pasta_logs=str(tmp_path))
    assert len(sessoes) == 2


def test_admin_de_grupo_so_ve_estudantes_dos_seus_grupos(tmp_path):
    admin_id = autenticacao.registar("prof@escola.pt", "password123")
    id_a = autenticacao.registar("a@b.com", "password123")
    autenticacao.registar("b@c.com", "password123")
    turma_a = grupos.criar_grupo("Turma A", criado_por=admin_id)
    grupos.reatribuir_grupo(id_a, turma_a["id"])
    grupos.definir_grupos_geridos(admin_id, [turma_a["id"]])

    _sessao(tmp_path, "a@b.com")
    _sessao(tmp_path, "b@c.com")

    sessoes = inv.listar_sessoes(admin_id, admin_global=False, pasta_logs=str(tmp_path))
    assert [s["id_estudante"] for s in sessoes] == ["a@b.com"]


def test_admin_de_grupo_nao_ve_estudante_sem_grupo_nenhum(tmp_path):
    """Mesmo que o admin de grupo gira pelo menos um grupo, um
    estudante sem NENHUM grupo nunca lhe aparece (só a admins globais)."""
    admin_id = autenticacao.registar("prof@escola.pt", "password123")
    turma_a = grupos.criar_grupo("Turma A", criado_por=admin_id)
    grupos.definir_grupos_geridos(admin_id, [turma_a["id"]])
    autenticacao.registar("solo@escola.pt", "password123")
    _sessao(tmp_path, "solo@escola.pt")

    sessoes = inv.listar_sessoes(admin_id, admin_global=False, pasta_logs=str(tmp_path))
    assert sessoes == []


def test_acesso_usa_pertenca_atual_nao_o_grupo_denormalizado_da_sessao(tmp_path):
    """A sessão guarda 'grupo' como estava NA ALTURA (denormalizado) --
    mas o controlo de acesso usa a pertença ATUAL. Um estudante que
    mudou de turma depois da sessão passa a ser visto pelo admin da
    turma NOVA, não pelo da antiga, mesmo que a sessão continue a
    mostrar o nome da turma antiga."""
    admin_antigo = autenticacao.registar("prof_antigo@escola.pt", "password123")
    admin_novo = autenticacao.registar("prof_novo@escola.pt", "password123")
    id_est = autenticacao.registar("a@b.com", "password123")
    turma_antiga = grupos.criar_grupo("Turma Antiga", criado_por=admin_antigo)
    turma_nova = grupos.criar_grupo("Turma Nova", criado_por=admin_novo)
    grupos.definir_grupos_geridos(admin_antigo, [turma_antiga["id"]])
    grupos.definir_grupos_geridos(admin_novo, [turma_nova["id"]])

    _sessao(tmp_path, "a@b.com", grupo="Turma Antiga")
    grupos.reatribuir_grupo(id_est, turma_nova["id"])  # muda de turma DEPOIS da sessão

    sessoes_antigo = inv.listar_sessoes(admin_antigo, admin_global=False, pasta_logs=str(tmp_path))
    sessoes_novo = inv.listar_sessoes(admin_novo, admin_global=False, pasta_logs=str(tmp_path))
    assert sessoes_antigo == []
    assert len(sessoes_novo) == 1
    assert sessoes_novo[0]["grupo"] == "Turma Antiga"  # exibição continua a mostrar a turma da altura


# ---------- filtros de relatório ----------

def test_filtro_por_grupo_denormalizado(tmp_path):
    admin_id = autenticacao.registar("admin@escola.pt", "password123")
    autenticacao.registar("a@b.com", "password123")
    _sessao(tmp_path, "a@b.com", grupo="Turma A")
    _sessao(tmp_path, "a@b.com", grupo="Turma B")
    sessoes = inv.listar_sessoes(admin_id, admin_global=True, grupo="Turma A", pasta_logs=str(tmp_path))
    assert len(sessoes) == 1
    assert sessoes[0]["grupo"] == "Turma A"


def test_filtro_por_apoio_escopo_e_guardiao_escopo(tmp_path):
    admin_id = autenticacao.registar("admin@escola.pt", "password123")
    autenticacao.registar("a@b.com", "password123")
    _sessao(tmp_path, "a@b.com", apoio_escopo="global", guardiao_escopo="global")
    _sessao(tmp_path, "a@b.com", apoio_escopo="pessoal", guardiao_escopo="indisponivel")

    so_globais = inv.listar_sessoes(
        admin_id, admin_global=True, apoio_escopo="global", pasta_logs=str(tmp_path))
    assert len(so_globais) == 1

    so_sem_guardiao = inv.listar_sessoes(
        admin_id, admin_global=True, guardiao_escopo="indisponivel", pasta_logs=str(tmp_path))
    assert len(so_sem_guardiao) == 1


def test_filtro_por_periodo(tmp_path):
    admin_id = autenticacao.registar("admin@escola.pt", "password123")
    autenticacao.registar("a@b.com", "password123")
    _sessao(tmp_path, "a@b.com")
    sessoes = inv.listar_sessoes(
        admin_id, admin_global=True, data_inicio="2999-01-01", pasta_logs=str(tmp_path))
    assert sessoes == []  # nenhuma sessão é "do futuro"


# ---------- opções de filtro derivadas do âmbito ----------

def test_opcoes_de_filtro_so_reflete_o_que_o_admin_pode_ver(tmp_path):
    admin_id = autenticacao.registar("prof@escola.pt", "password123")
    id_a = autenticacao.registar("a@b.com", "password123")
    autenticacao.registar("b@c.com", "password123")
    turma_a = grupos.criar_grupo("Turma A", criado_por=admin_id)
    grupos.reatribuir_grupo(id_a, turma_a["id"])
    grupos.definir_grupos_geridos(admin_id, [turma_a["id"]])

    _sessao(tmp_path, "a@b.com", grupo="Turma A")
    _sessao(tmp_path, "b@c.com", grupo="Turma B")

    no_ambito = inv.listar_sessoes_no_ambito(admin_id, admin_global=False, pasta_logs=str(tmp_path))
    opcoes = inv.opcoes_de_filtro(no_ambito)
    assert opcoes["grupos"] == ["Turma A"]  # nunca "Turma B" -- fora do âmbito


# ---------- dashboard ----------

def test_gerar_dashboard_agrega_por_grupo_e_por_dia():
    sessoes = [
        {"id_estudante": "a@b.com", "grupo": "Turma A", "timestamp_inicio": "2026-01-01T10:00:00+00:00",
         "num_tentativas_totais": 2, "num_tentativas_rejeitadas": 1,
         "hint_escalation_maxima": 3, "num_turnos": 4, "fornecedor": "openai",
         "modelo": "gpt-4o-mini", "apoio_escopo": "global"},
        {"id_estudante": "b@c.com", "grupo": "Turma A", "timestamp_inicio": "2026-01-01T11:00:00+00:00",
         "num_tentativas_totais": 0, "num_tentativas_rejeitadas": 0,
         "hint_escalation_maxima": None, "num_turnos": 1, "fornecedor": None,
         "modelo": None, "apoio_escopo": None},
    ]
    dashboard = inv.gerar_dashboard(sessoes)
    assert dashboard["sessoes_por_dia"] == [{"dia": "2026-01-01", "sessoes": 2}]
    assert dashboard["leakage_por_grupo"] == [
        {"grupo": "Turma A", "solution_leakage_rate": 0.5, "num_tentativas": 2}]
    assert {"nivel": 3, "sessoes": 1} in dashboard["distribuicao_nivel_maximo"]
    assert len(dashboard["distribuicao_nivel_maximo"]) == 8  # níveis 0-7
    assert {"turnos": 4, "sessoes": 1} in dashboard["distribuicao_turnos"]
    assert {"fornecedor_modelo": "openai/gpt-4o-mini", "escopo": "global", "sessoes": 1} \
        in dashboard["sessoes_por_fornecedor_e_escopo"]


def test_gerar_dashboard_com_lista_vazia_nao_rebenta():
    dashboard = inv.gerar_dashboard([])
    assert dashboard["sessoes_por_dia"] == []
    assert dashboard["leakage_por_grupo"] == []
    assert len(dashboard["distribuicao_nivel_maximo"]) == 8


# ---------- exportação ----------

def test_exportar_csv_tem_cabecalho_e_uma_linha_por_sessao():
    sessoes = [{"id_sessao": "s1", "id_estudante": "a@b.com", "grupo": "Turma A"}]
    csv_texto = inv.exportar_csv(sessoes)
    linhas = csv_texto.strip().splitlines()
    assert len(linhas) == 2
    assert "id_sessao" in linhas[0]
    assert "s1" in linhas[1]


def test_exportar_json_e_uma_lista_valida():
    sessoes = [{"id_sessao": "s1", "id_estudante": "a@b.com", "grupo": "Turma A"}]
    dados = json.loads(inv.exportar_json(sessoes))
    assert len(dados) == 1
    assert dados[0]["id_sessao"] == "s1"
    assert dados[0]["id_estudante"] == "a@b.com"
    assert dados[0]["grupo"] == "Turma A"
    assert set(dados[0]) == set(inv._COLUNAS_EXPORTACAO)


# ---------- vista por estudante (secção 10) ----------

def test_vista_estudante_junta_sessoes_e_execucoes_por_ordem_cronologica(tmp_path):
    admin_id = autenticacao.registar("admin@escola.pt", "password123")
    id_est = autenticacao.registar("a@b.com", "password123")
    _sessao(tmp_path, "a@b.com")
    historico_codigo.registar_execucao(id_est, "executa", "p.algo", [], "Sucesso")

    vista = inv.vista_estudante(admin_id, admin_global=True, estudante_id=id_est, pasta_logs=str(tmp_path))
    assert vista["email"] == "a@b.com"
    tipos = [item["tipo"] for item in vista["linha_do_tempo"]]
    assert set(tipos) == {"sessao_alguem", "execucao_codigo"}
    timestamps = [item["timestamp"] for item in vista["linha_do_tempo"]]
    assert timestamps == sorted(timestamps, reverse=True)


def test_vista_estudante_fora_do_ambito_de_admin_de_grupo_levanta_erro(tmp_path):
    admin_id = autenticacao.registar("prof@escola.pt", "password123")
    id_est = autenticacao.registar("a@b.com", "password123")
    turma_a = grupos.criar_grupo("Turma A", criado_por=admin_id)
    grupos.definir_grupos_geridos(admin_id, [turma_a["id"]])
    # id_est não pertence a nenhum grupo -- fora do âmbito
    with pytest.raises(inv.ErroAcessoNegado):
        inv.vista_estudante(admin_id, admin_global=False, estudante_id=id_est, pasta_logs=str(tmp_path))


def test_vista_estudante_dentro_do_ambito_de_admin_de_grupo_funciona(tmp_path):
    admin_id = autenticacao.registar("prof@escola.pt", "password123")
    id_est = autenticacao.registar("a@b.com", "password123")
    turma_a = grupos.criar_grupo("Turma A", criado_por=admin_id)
    grupos.reatribuir_grupo(id_est, turma_a["id"])
    grupos.definir_grupos_geridos(admin_id, [turma_a["id"]])
    _sessao(tmp_path, "a@b.com")

    vista = inv.vista_estudante(admin_id, admin_global=False, estudante_id=id_est, pasta_logs=str(tmp_path))
    assert vista["email"] == "a@b.com"


# ---------- listar_estudantes_no_ambito_admin / verificar_acesso_estudante (Fase 6) ----------

def test_listar_estudantes_no_ambito_admin_inclui_conta_sem_sessao_nenhuma():
    """Ao contrário de listar_sessoes_no_ambito, esta lista é sobre
    CONTAS -- um estudante que nunca falou com o Alguem (só executou
    código, ou nem isso) tem de aparecer na mesma, para o seletor do
    Apoio Pedagógico (secção 11) conseguir apontar para ele."""
    admin_id = autenticacao.registar("admin@escola.pt", "password123")
    autenticacao.registar("a@b.com", "password123")
    estudantes = inv.listar_estudantes_no_ambito_admin(admin_id, admin_global=True)
    assert [e["email"] for e in estudantes] == ["a@b.com"]


def test_listar_estudantes_no_ambito_admin_filtra_por_grupo_para_admin_de_grupo():
    admin_id = autenticacao.registar("prof@escola.pt", "password123")
    id_a = autenticacao.registar("a@b.com", "password123")
    autenticacao.registar("b@c.com", "password123")
    turma_a = grupos.criar_grupo("Turma A", criado_por=admin_id)
    grupos.reatribuir_grupo(id_a, turma_a["id"])
    grupos.definir_grupos_geridos(admin_id, [turma_a["id"]])

    estudantes = inv.listar_estudantes_no_ambito_admin(admin_id, admin_global=False)
    assert [e["email"] for e in estudantes] == ["a@b.com"]


def test_verificar_acesso_estudante_devolve_email_quando_permitido():
    admin_id = autenticacao.registar("admin@escola.pt", "password123")
    id_est = autenticacao.registar("a@b.com", "password123")
    assert inv.verificar_acesso_estudante(admin_id, admin_global=True, estudante_id=id_est) == "a@b.com"


def test_verificar_acesso_estudante_levanta_erro_fora_do_ambito():
    admin_id = autenticacao.registar("prof@escola.pt", "password123")
    id_est = autenticacao.registar("a@b.com", "password123")
    turma_a = grupos.criar_grupo("Turma A", criado_por=admin_id)
    grupos.definir_grupos_geridos(admin_id, [turma_a["id"]])
    with pytest.raises(inv.ErroAcessoNegado):
        inv.verificar_acesso_estudante(admin_id, admin_global=False, estudante_id=id_est)


# ---------- listar_grupos_no_ambito_admin / verificar_acesso_grupo (Apoio por Grupo) ----------

def test_listar_grupos_no_ambito_admin_global_ve_todos():
    admin_id = autenticacao.registar("admin@escola.pt", "password123")
    grupos.criar_grupo("Turma A", criado_por=admin_id)
    grupos.criar_grupo("Turma B", criado_por=admin_id)
    nomes = [g["nome"] for g in inv.listar_grupos_no_ambito_admin(admin_id, admin_global=True)]
    assert nomes == ["Turma A", "Turma B"]


def test_listar_grupos_no_ambito_admin_de_grupo_so_ve_os_que_gere():
    admin_id = autenticacao.registar("prof@escola.pt", "password123")
    turma_a = grupos.criar_grupo("Turma A", criado_por=admin_id)
    grupos.criar_grupo("Turma B", criado_por=admin_id)
    grupos.definir_grupos_geridos(admin_id, [turma_a["id"]])
    nomes = [g["nome"] for g in inv.listar_grupos_no_ambito_admin(admin_id, admin_global=False)]
    assert nomes == ["Turma A"]


def test_verificar_acesso_grupo_admin_global_sempre_permitido():
    admin_id = autenticacao.registar("admin@escola.pt", "password123")
    turma = grupos.criar_grupo("Turma A", criado_por=admin_id)
    inv.verificar_acesso_grupo(admin_id, admin_global=True, grupo_id=turma["id"])  # não levanta


def test_verificar_acesso_grupo_levanta_erro_fora_do_ambito():
    admin_id = autenticacao.registar("prof@escola.pt", "password123")
    turma_a = grupos.criar_grupo("Turma A", criado_por=admin_id)
    turma_b = grupos.criar_grupo("Turma B", criado_por=admin_id)
    grupos.definir_grupos_geridos(admin_id, [turma_a["id"]])
    inv.verificar_acesso_grupo(admin_id, admin_global=False, grupo_id=turma_a["id"])  # não levanta
    with pytest.raises(inv.ErroAcessoNegado):
        inv.verificar_acesso_grupo(admin_id, admin_global=False, grupo_id=turma_b["id"])
