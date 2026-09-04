# -*- coding: utf-8 -*-
"""Definições globais da aplicação, editáveis pelo admin no painel --
tabela chave/valor simples (ver 'definicao' em bd.py), pensada para
crescer para lá do único interruptor atual (ativar/desativar o
Alguem). Sem linha para uma chave, assume-se o valor por omissão."""
from __future__ import annotations

from bd import sessao_bd

_CHAVE_ALGUEM_ATIVO = "alguem_ativo"
_CHAVE_NIVEL_MAXIMO_AJUDA = "nivel_maximo_ajuda"
_CHAVE_USAR_GUARDIAO = "usar_guardiao"

# Mesmos valores por omissão que alguem.nucleo.politica_pedagogica.
# PoliticaPedagogica usa quando não há linha em 'definicao' (ver
# docs/interno/PlanoAlguemLLMInvestigacao.md, secção 8/Fase 3).
_NIVEL_MAXIMO_AJUDA_POR_OMISSAO = 5
_USAR_GUARDIAO_POR_OMISSAO = True


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


def nivel_maximo_ajuda(dsn: str | None = None) -> int:
    with sessao_bd(dsn) as bd:
        linha = bd.execute(
            "SELECT valor FROM definicao WHERE chave = %s", (_CHAVE_NIVEL_MAXIMO_AJUDA,)
        ).fetchone()
    return int(linha["valor"]) if linha else _NIVEL_MAXIMO_AJUDA_POR_OMISSAO


def definir_nivel_maximo_ajuda(nivel: int, dsn: str | None = None) -> None:
    # 0-6, não 0-7 (o teto que PoliticaPedagogica.__post_init__ aceita):
    # o nível 7 (Código) fica sempre bloqueado à parte, por
    # permite_gerar_codigo -- fixo a False nesta fase (secção 8 do
    # plano, "fora de âmbito") e não exposto ao admin -- por isso
    # oferecer 7 aqui seria uma opção sem efeito nenhum.
    if not (0 <= nivel <= 6):
        raise ValueError(
            f"nivel_maximo_ajuda tem de estar entre 0 e 6, recebido: {nivel}")
    with sessao_bd(dsn) as bd:
        bd.execute(
            "INSERT INTO definicao (chave, valor) VALUES (%s, %s) "
            "ON CONFLICT (chave) DO UPDATE SET valor = EXCLUDED.valor",
            (_CHAVE_NIVEL_MAXIMO_AJUDA, str(nivel)),
        )


def usar_guardiao(dsn: str | None = None) -> bool:
    with sessao_bd(dsn) as bd:
        linha = bd.execute(
            "SELECT valor FROM definicao WHERE chave = %s", (_CHAVE_USAR_GUARDIAO,)
        ).fetchone()
    return linha["valor"] == "true" if linha else _USAR_GUARDIAO_POR_OMISSAO


def definir_usar_guardiao(ativo: bool, dsn: str | None = None) -> None:
    with sessao_bd(dsn) as bd:
        bd.execute(
            "INSERT INTO definicao (chave, valor) VALUES (%s, %s) "
            "ON CONFLICT (chave) DO UPDATE SET valor = EXCLUDED.valor",
            (_CHAVE_USAR_GUARDIAO, "true" if ativo else "false"),
        )
