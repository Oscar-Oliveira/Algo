# -*- coding: utf-8 -*-
"""Registo geral de atividade da aplicação -- separado dos logs de
conversa com o Alguem (ver alguem/nucleo/registador.py), que ficam
intocados por este módulo. Cada linha é um evento administrativo ou de
conta (login, registo, aprovação, mudanças de grupo/admin, etc.),
gravado por quem chama (normalmente main.py, depois de uma ação já ter
sido concluída com sucesso). Eliminação de eventos é sempre física e
definitiva -- ver notes.md."""
from __future__ import annotations

import csv
import io
import json

from bd import sessao_bd

POR_PAGINA_POR_OMISSAO = 50


def registar_evento(tipo: str, ator_id: int | None = None, alvo_id: int | None = None,
                     grupo_id: int | None = None, detalhes: dict | None = None,
                     dsn: str | None = None) -> None:
    with sessao_bd(dsn) as bd:
        bd.execute(
            "INSERT INTO log_atividade (tipo, ator_id, alvo_id, grupo_id, detalhes) "
            "VALUES (%s, %s, %s, %s, %s)",
            (tipo, ator_id, alvo_id, grupo_id, json.dumps(detalhes) if detalhes else None),
        )


def _construir_filtros(estudante_id: int | None, grupo_id: int | None, tipo: str | None,
                        data_inicio: str | None, data_fim: str | None) -> tuple[str, list]:
    condicoes = []
    parametros: list = []
    if estudante_id is not None:
        condicoes.append("(log_atividade.ator_id = %s OR log_atividade.alvo_id = %s)")
        parametros.extend([estudante_id, estudante_id])
    if grupo_id is not None:
        condicoes.append("log_atividade.grupo_id = %s")
        parametros.append(grupo_id)
    if tipo:
        condicoes.append("log_atividade.tipo = %s")
        parametros.append(tipo)
    if data_inicio:
        condicoes.append("log_atividade.criado_em >= %s")
        parametros.append(data_inicio)
    if data_fim:
        condicoes.append("log_atividade.criado_em <= %s")
        parametros.append(data_fim)
    clausula = f"WHERE {' AND '.join(condicoes)}" if condicoes else ""
    return clausula, parametros


_SELECT_BASE = """
    SELECT log_atividade.id, log_atividade.tipo, log_atividade.criado_em, log_atividade.detalhes,
           log_atividade.ator_id, ator.email AS ator_email,
           log_atividade.alvo_id, alvo.email AS alvo_email,
           log_atividade.grupo_id, grupo.nome AS grupo_nome
    FROM log_atividade
    LEFT JOIN estudante AS ator ON ator.id = log_atividade.ator_id
    LEFT JOIN estudante AS alvo ON alvo.id = log_atividade.alvo_id
    LEFT JOIN grupo ON grupo.id = log_atividade.grupo_id
"""


def listar_eventos(estudante_id: int | None = None, grupo_id: int | None = None,
                    tipo: str | None = None, data_inicio: str | None = None,
                    data_fim: str | None = None, pagina: int = 1,
                    por_pagina: int = POR_PAGINA_POR_OMISSAO,
                    dsn: str | None = None) -> dict:
    clausula, parametros = _construir_filtros(estudante_id, grupo_id, tipo, data_inicio, data_fim)
    pagina = max(1, pagina)
    deslocamento = (pagina - 1) * por_pagina

    with sessao_bd(dsn) as bd:
        total = bd.execute(
            f"SELECT COUNT(*) AS total FROM log_atividade {clausula}", parametros
        ).fetchone()["total"]
        linhas = bd.execute(
            f"{_SELECT_BASE} {clausula} "
            f"ORDER BY log_atividade.criado_em DESC, log_atividade.id DESC "
            f"LIMIT %s OFFSET %s",
            parametros + [por_pagina, deslocamento],
        ).fetchall()

    eventos = []
    for linha in linhas:
        evento = dict(linha)
        if evento["detalhes"]:
            evento["detalhes"] = json.loads(evento["detalhes"])
        eventos.append(evento)
    return {"eventos": eventos, "total": total, "pagina": pagina, "por_pagina": por_pagina}


def apagar_eventos(ids: list[int], dsn: str | None = None) -> int:
    """Elimina fisicamente os eventos indicados -- definitivo, sem
    recuperação possível. Devolve quantas linhas foram mesmo apagadas
    (ids inexistentes são ignorados em silêncio)."""
    if not ids:
        return 0
    with sessao_bd(dsn) as bd:
        cursor = bd.execute("DELETE FROM log_atividade WHERE id = ANY(%s)", (ids,))
        return cursor.rowcount


def exportar_csv(estudante_id: int | None = None, grupo_id: int | None = None,
                  tipo: str | None = None, data_inicio: str | None = None,
                  data_fim: str | None = None, dsn: str | None = None) -> str:
    clausula, parametros = _construir_filtros(estudante_id, grupo_id, tipo, data_inicio, data_fim)
    with sessao_bd(dsn) as bd:
        linhas = bd.execute(
            f"{_SELECT_BASE} {clausula} ORDER BY log_atividade.criado_em DESC, log_atividade.id DESC",
            parametros,
        ).fetchall()

    saida = io.StringIO()
    escritor = csv.writer(saida)
    escritor.writerow(["id", "tipo", "criado_em", "ator_email", "alvo_email", "grupo_nome", "detalhes"])
    for linha in linhas:
        escritor.writerow([
            linha["id"], linha["tipo"], linha["criado_em"].isoformat(),
            linha["ator_email"] or "", linha["alvo_email"] or "", linha["grupo_nome"] or "",
            linha["detalhes"] or "",
        ])
    return saida.getvalue()
