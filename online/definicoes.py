# -*- coding: utf-8 -*-
"""Definições globais da aplicação, editáveis pelo admin no painel --
tabela chave/valor simples (ver 'definicao' em bd.py), pensada para
crescer para lá do único interruptor atual (ativar/desativar o
Alguem). Sem linha para uma chave, assume-se o valor por omissão."""
from __future__ import annotations

from bd import sessao_bd

_CHAVE_ALGUEM_ATIVO = "alguem_ativo"


def alguem_ativo(dsn: str | None = None) -> bool:
    with sessao_bd(dsn) as bd:
        linha = bd.execute(
            "SELECT valor FROM definicao WHERE chave = %s", (_CHAVE_ALGUEM_ATIVO,)
        ).fetchone()
    return linha["valor"] == "true" if linha else False


def definir_alguem_ativo(ativo: bool, dsn: str | None = None) -> None:
    with sessao_bd(dsn) as bd:
        bd.execute(
            "INSERT INTO definicao (chave, valor) VALUES (%s, %s) "
            "ON CONFLICT (chave) DO UPDATE SET valor = EXCLUDED.valor",
            (_CHAVE_ALGUEM_ATIVO, "true" if ativo else "false"),
        )
