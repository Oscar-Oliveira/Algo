# -*- coding: utf-8 -*-
"""Reportes de problemas/erros que os estudantes enviam aos admins a
partir do editor -- consulta paginada e apagar no painel de admin, sem
nenhum estado intermédio (não há "marcar como resolvido")."""
from __future__ import annotations

from bd import sessao_bd


def criar_relatorio(estudante_id: int, descricao: str, dsn: str | None = None) -> None:
    descricao = descricao.strip()
    if not descricao:
        raise ValueError("Descrição não pode estar vazia.")
    with sessao_bd(dsn) as bd:
        bd.execute(
            "INSERT INTO relatorio_problema (estudante_id, descricao) VALUES (%s, %s)",
            (estudante_id, descricao),
        )


def listar_relatorios(dsn: str | None = None) -> list[dict]:
    """Todos os reportes, mais recentes primeiro -- para a tabela de
    relatórios do painel de admin."""
    with sessao_bd(dsn) as bd:
        linhas = bd.execute(
            """SELECT relatorio_problema.id, relatorio_problema.descricao,
                      relatorio_problema.criado_em, estudante.email
               FROM relatorio_problema
               JOIN estudante ON estudante.id = relatorio_problema.estudante_id
               ORDER BY relatorio_problema.criado_em DESC, relatorio_problema.id DESC"""
        ).fetchall()
    return [dict(linha) for linha in linhas]


def apagar_relatorio(relatorio_id: int, dsn: str | None = None) -> None:
    with sessao_bd(dsn) as bd:
        bd.execute("DELETE FROM relatorio_problema WHERE id = %s", (relatorio_id,))
