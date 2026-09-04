# -*- coding: utf-8 -*-
"""Histórico de execução/debug de código por estudante -- tabela
'execucao_codigo' (ver docs/interno/PlanoAlguemLLMInvestigacao.md,
secção 9/Fase 4). Separado de alguem/nucleo/registador.py (logs de
conversa com o Alguem, em .jsonl) -- este módulo é sobre CÓDIGO
executado, gravado a partir de main.py:ws_executar/ws_debug.

Histórico completo, sem limite nem substituição (decisão validada,
ponto 5) -- só a eliminação explícita (por período, seleção manual, ou
tudo) o reduz, ver apagar_*."""
from __future__ import annotations

import json

from bd import sessao_bd

TIPOS_VALIDOS = frozenset({"executa", "debug"})


def registar_execucao(estudante_id: int, tipo: str, nome_ficheiro_principal: str,
                       ficheiros: list[dict], resultado: str, dsn: str | None = None) -> None:
    assert tipo in TIPOS_VALIDOS, f"tipo inválido: {tipo!r}"
    with sessao_bd(dsn) as bd:
        bd.execute(
            "INSERT INTO execucao_codigo "
            "(estudante_id, tipo, nome_ficheiro_principal, ficheiros, resultado) "
            "VALUES (%s, %s, %s, %s, %s)",
            (estudante_id, tipo, nome_ficheiro_principal, json.dumps(ficheiros), resultado),
        )


def listar_por_estudante(estudante_id: int, dsn: str | None = None) -> list[dict]:
    """Ver docs/interno/PlanoAlguemLLMInvestigacao.md, secção 10/Fase
    5 -- matéria-prima da vista cronológica por estudante (junta-se às
    sessões do Alguem em online/investigacao.py:vista_estudante)."""
    with sessao_bd(dsn) as bd:
        linhas = bd.execute(
            "SELECT id, tipo, nome_ficheiro_principal, ficheiros, resultado, criado_em "
            "FROM execucao_codigo WHERE estudante_id = %s ORDER BY criado_em DESC",
            (estudante_id,),
        ).fetchall()
    resultado = []
    for linha in linhas:
        item = dict(linha)
        item["ficheiros"] = json.loads(item["ficheiros"])
        resultado.append(item)
    return resultado


def apagar_por_ids(ids: list[int], dsn: str | None = None) -> int:
    """Eliminação física, definitiva -- seleção manual (ver secção 14
    do plano). ids inexistentes são ignorados em silêncio."""
    if not ids:
        return 0
    with sessao_bd(dsn) as bd:
        cursor = bd.execute("DELETE FROM execucao_codigo WHERE id = ANY(%s)", (ids,))
        return cursor.rowcount


def apagar_por_periodo(dias: int, dsn: str | None = None) -> int:
    """Apaga tudo com mais de 'dias' dias -- ex: apagar_por_periodo(90)
    para "tudo com mais de 90 dias" (exemplo da secção 14 do plano)."""
    assert dias >= 0, f"dias tem de ser >= 0, recebido: {dias}"
    with sessao_bd(dsn) as bd:
        cursor = bd.execute(
            "DELETE FROM execucao_codigo WHERE criado_em < now() - (%s || ' days')::interval",
            (dias,),
        )
        return cursor.rowcount


def apagar_tudo(dsn: str | None = None) -> int:
    with sessao_bd(dsn) as bd:
        cursor = bd.execute("DELETE FROM execucao_codigo")
        return cursor.rowcount
