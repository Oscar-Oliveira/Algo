# -*- coding: utf-8 -*-
"""Painel de admin -- Investigação (ver
docs/interno/PlanoAlguemLLMInvestigacao.md, secção 6/10, Fase 5):
dashboard, relatório e exportação sobre as sessões do Alguem
(alguem/logs/*.jsonl, via alguem.scripts.metricas), e a vista
cronológica por estudante (sessões + execuções de código).

Controlo de acesso (secção 15): um admin GLOBAL vê tudo; um admin de
GRUPO só vê estudantes cuja pertença ATUAL (estudante_grupo, não o
campo 'grupo' denormalizado nas sessões) aponte para um dos grupos que
gere -- um estudante sem grupo nenhum nunca é visível a um admin de
grupo. O campo 'grupo' de cada sessão (secção 4) é só para exibição/
filtro de relatório -- denormalizado de propósito, para não mudar
quando o estudante muda de turma; o controlo de acesso usa sempre a
pertença ATUAL."""
from __future__ import annotations

import csv
import io
import json
from collections import defaultdict

import grupos
import historico_codigo
from alguem.nucleo import registador
from alguem.scripts import metricas
from bd import sessao_bd

PAPEIS_ESCOPO = frozenset({"global", "pessoal", "indisponivel"})


class ErroInvestigacao(Exception):
    pass


class ErroAcessoNegado(ErroInvestigacao):
    """Pedido direto (vista por estudante) fora do âmbito de um admin
    de grupo -- ver secção 15: devolve 403, não um 404 nem uma lista
    silenciosamente vazia (main.py mapeia isto para 403)."""
    pass


def _mapa_email_para_conta(dsn: str | None = None) -> dict[str, dict]:
    """email -> {"id": estudante_id, "grupos": conjunto de grupo_ids
    ATUAIS} -- uma só query serve tanto o controlo de acesso (secção
    15) como a resolução email->id que a UI precisa (o relatório só
    tem o email, vindo dos logs; "ver este estudante" precisa do id)."""
    with sessao_bd(dsn) as bd:
        linhas = bd.execute(
            "SELECT estudante.id, estudante.email, eg.grupo_id FROM estudante "
            "LEFT JOIN estudante_grupo eg ON eg.estudante_id = estudante.id"
        ).fetchall()
    mapa: dict[str, dict] = {}
    for linha in linhas:
        conta = mapa.setdefault(linha["email"], {"id": linha["id"], "grupos": set()})
        if linha["grupo_id"] is not None:
            conta["grupos"].add(linha["grupo_id"])
    return mapa


def _grupos_permitidos(admin_id: int, admin_global: bool, dsn: str | None = None) -> set[int] | None:
    """None = sem restrição (admin global)."""
    if admin_global:
        return None
    return set(grupos.listar_grupos_geridos(admin_id, dsn))


def _pode_ver(grupos_do_estudante: set[int], permitidos: set[int] | None) -> bool:
    if permitidos is None:
        return True
    # estudante sem grupo nenhum -> nunca visível a um admin de grupo,
    # mesmo que 'permitidos' não esteja vazio (ver secção 15).
    return bool(grupos_do_estudante & permitidos)


def listar_sessoes_no_ambito(admin_id: int, admin_global: bool, pasta_logs: str | None = None,
                              dsn: str | None = None) -> list[dict]:
    """Todas as sessões que este admin tem permissão para ver (secção
    15), sem nenhum filtro de relatório aplicado ainda -- é a partir
    desta lista que a UI deriva as opções disponíveis para os filtros
    (grupo, fornecedor), para nunca oferecer uma opção que depois
    devolveria sempre vazio."""
    pasta_logs = pasta_logs or registador.PASTA_LOGS_POR_OMISSAO
    eventos_por_sessao = metricas.carregar_eventos_por_sessao(pasta_logs)
    sessoes = [metricas.calcular_metricas_da_sessao(e) for e in eventos_por_sessao.values()]

    mapa_contas = _mapa_email_para_conta(dsn)
    permitidos = _grupos_permitidos(admin_id, admin_global, dsn)
    resultado = []
    for s in sessoes:
        conta = mapa_contas.get(s.get("id_estudante"))
        if not _pode_ver(conta["grupos"] if conta else set(), permitidos):
            continue
        # 'estudante_id' não vem dos logs (que só têm o email) -- é
        # anexado aqui para a UI poder abrir a vista por estudante
        # (secção 10) diretamente a partir de uma linha do relatório.
        # None se a conta já não existir (email só no histórico antigo).
        s["estudante_id"] = conta["id"] if conta else None
        resultado.append(s)
    return resultado


def filtrar_sessoes(sessoes: list[dict], *, grupo: str | None = None,
                     data_inicio: str | None = None, data_fim: str | None = None,
                     fornecedor: str | None = None, apoio_escopo: str | None = None,
                     guardiao_escopo: str | None = None) -> list[dict]:
    """Filtros de relatório sobre uma lista já dentro do âmbito do
    admin (ver listar_sessoes_no_ambito) -- 'grupo' filtra pelo campo
    denormalizado da sessão (nome, tal como era nessa altura), distinto
    do controlo de acesso."""
    resultado = []
    for s in sessoes:
        if grupo and s.get("grupo") != grupo:
            continue
        if fornecedor and s.get("fornecedor") != fornecedor:
            continue
        if apoio_escopo and s.get("apoio_escopo") != apoio_escopo:
            continue
        if guardiao_escopo and s.get("guardiao_escopo") != guardiao_escopo:
            continue
        # timestamp_inicio é ISO-8601 (UTC) -- comparação lexicográfica
        # de string já é cronológica, sem precisar de parse.
        if data_inicio and (not s.get("timestamp_inicio") or s["timestamp_inicio"] < data_inicio):
            continue
        if data_fim and (not s.get("timestamp_inicio") or s["timestamp_inicio"] > data_fim):
            continue
        resultado.append(s)
    resultado.sort(key=lambda s: s.get("timestamp_inicio") or "", reverse=True)
    return resultado


def opcoes_de_filtro(sessoes_no_ambito: list[dict]) -> dict:
    return {
        "grupos": sorted({s["grupo"] for s in sessoes_no_ambito if s.get("grupo")}),
        "fornecedores": sorted({s["fornecedor"] for s in sessoes_no_ambito if s.get("fornecedor")}),
    }


def listar_sessoes(admin_id: int, admin_global: bool, *, grupo: str | None = None,
                    data_inicio: str | None = None, data_fim: str | None = None,
                    fornecedor: str | None = None, apoio_escopo: str | None = None,
                    guardiao_escopo: str | None = None, pasta_logs: str | None = None,
                    dsn: str | None = None) -> list[dict]:
    """Atalho: listar_sessoes_no_ambito + filtrar_sessoes numa só
    chamada, para quem só precisa do resultado final (ex: exportação) e
    não das opções de filtro disponíveis (ver opcoes_de_filtro)."""
    no_ambito = listar_sessoes_no_ambito(admin_id, admin_global, pasta_logs, dsn)
    return filtrar_sessoes(
        no_ambito, grupo=grupo, data_inicio=data_inicio, data_fim=data_fim,
        fornecedor=fornecedor, apoio_escopo=apoio_escopo, guardiao_escopo=guardiao_escopo)


def gerar_dashboard(sessoes: list[dict]) -> dict:
    """Agregados para os gráficos da secção 6, a partir de uma lista já
    filtrada (ver listar_sessoes) -- este módulo não sabe nada de
    HTTP/filtros, só agrega o que recebe."""
    por_dia: dict[str, int] = defaultdict(int)
    tentativas_por_grupo: dict[str, list[int]] = defaultdict(lambda: [0, 0])  # [tentativas, rejeitadas]
    distribuicao_nivel: dict[int, int] = defaultdict(int)
    distribuicao_turnos: dict[int, int] = defaultdict(int)
    sessoes_por_fornecedor_escopo: dict[tuple[str, str], int] = defaultdict(int)

    for s in sessoes:
        if s.get("timestamp_inicio"):
            por_dia[s["timestamp_inicio"][:10]] += 1

        nome_grupo = s.get("grupo") or "(sem grupo)"
        entrada = tentativas_por_grupo[nome_grupo]
        entrada[0] += s.get("num_tentativas_totais") or 0
        entrada[1] += s.get("num_tentativas_rejeitadas") or 0

        if s.get("hint_escalation_maxima") is not None:
            distribuicao_nivel[s["hint_escalation_maxima"]] += 1
        distribuicao_turnos[s.get("num_turnos") or 0] += 1

        if s.get("fornecedor"):
            chave = f"{s['fornecedor']}/{s.get('modelo') or '?'}"
            escopo = s.get("apoio_escopo") or "desconhecido"
            sessoes_por_fornecedor_escopo[(chave, escopo)] += 1

    return {
        "sessoes_por_dia": [
            {"dia": dia, "sessoes": n} for dia, n in sorted(por_dia.items())
        ],
        "leakage_por_grupo": [
            {"grupo": nome, "solution_leakage_rate": (rejeitadas / tentativas) if tentativas else None,
             "num_tentativas": tentativas}
            for nome, (tentativas, rejeitadas) in sorted(tentativas_por_grupo.items())
        ],
        "distribuicao_nivel_maximo": [
            {"nivel": nivel, "sessoes": distribuicao_nivel.get(nivel, 0)} for nivel in range(0, 8)
        ],
        "distribuicao_turnos": [
            {"turnos": turnos, "sessoes": n} for turnos, n in sorted(distribuicao_turnos.items())
        ],
        "sessoes_por_fornecedor_e_escopo": [
            {"fornecedor_modelo": chave, "escopo": escopo, "sessoes": n}
            for (chave, escopo), n in sorted(sessoes_por_fornecedor_escopo.items())
        ],
    }


_COLUNAS_EXPORTACAO = [
    "id_sessao", "id_estudante", "estudante_id", "grupo", "fornecedor", "modelo",
    "apoio_escopo", "guardiao_escopo", "guardiao_fornecedor", "guardiao_modelo",
    "num_turnos", "num_tentativas_totais", "num_tentativas_rejeitadas",
    "solution_leakage_rate", "hint_escalation_maxima", "num_recusas_seguras",
    "timestamp_inicio",
]


def exportar_csv(sessoes: list[dict]) -> str:
    saida = io.StringIO()
    escritor = csv.writer(saida)
    escritor.writerow(_COLUNAS_EXPORTACAO)
    for s in sessoes:
        escritor.writerow([s.get(coluna) for coluna in _COLUNAS_EXPORTACAO])
    return saida.getvalue()


def exportar_json(sessoes: list[dict]) -> str:
    return json.dumps(
        [{coluna: s.get(coluna) for coluna in _COLUNAS_EXPORTACAO} for s in sessoes],
        ensure_ascii=False, indent=2)


def vista_estudante(admin_id: int, admin_global: bool, estudante_id: int,
                     pasta_logs: str | None = None, dsn: str | None = None) -> dict:
    """Linha temporal única (secção 10): sessões do Alguem dessa pessoa
    + execuções de código, por ordem cronológica. Levanta
    ErroAcessoNegado se o estudante estiver fora do âmbito de um admin
    de grupo (secção 15) -- nunca uma lista vazia silenciosa."""
    with sessao_bd(dsn) as bd:
        linha = bd.execute("SELECT email FROM estudante WHERE id = %s", (estudante_id,)).fetchone()
    if linha is None:
        raise ErroAcessoNegado("Estudante não encontrado.")
    email = linha["email"]

    if not admin_global:
        permitidos = _grupos_permitidos(admin_id, admin_global, dsn)
        conta = _mapa_email_para_conta(dsn).get(email)
        if not _pode_ver(conta["grupos"] if conta else set(), permitidos):
            raise ErroAcessoNegado("Este estudante não está num dos grupos que geres.")

    pasta_logs = pasta_logs or registador.PASTA_LOGS_POR_OMISSAO
    eventos_por_sessao = metricas.carregar_eventos_por_sessao(pasta_logs)
    sessoes = [
        metricas.calcular_metricas_da_sessao(eventos)
        for eventos in eventos_por_sessao.values()
        if eventos and eventos[0].get("id_estudante") == email
    ]

    execucoes = historico_codigo.listar_por_estudante(estudante_id, dsn)

    linha_do_tempo = (
        [{"tipo": "sessao_alguem", "timestamp": s.get("timestamp_inicio"), "dados": s} for s in sessoes]
        + [{"tipo": "execucao_codigo", "timestamp": e["criado_em"].isoformat(), "dados": e}
           for e in execucoes]
    )
    linha_do_tempo.sort(key=lambda item: item["timestamp"] or "", reverse=True)

    return {"email": email, "estudante_id": estudante_id, "linha_do_tempo": linha_do_tempo}
