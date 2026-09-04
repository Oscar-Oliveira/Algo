# -*- coding: utf-8 -*-
"""Prompts do tutor e do Guardião, editáveis pelo admin -- tabela
'prompt_configuravel' (chave/texto, mesmo espírito de 'definicao' em
definicoes.py). Sem linha para uma chave, usa-se o texto por omissão
já definido no código (ver docs/interno/PlanoAlguemLLMInvestigacao.md,
secção 13/Fase 3).

Aviso de segurança (ver a mesma secção do plano): 'tutor' e 'guardiao'
incluem a rede de segurança pedagógica -- um admin que edite mal este
texto pode enfraquecer, sem querer, a proteção contra o Alguem revelar
soluções. É uma decisão explícita, não um efeito colateral ignorado."""
from __future__ import annotations

from alguem.nucleo.guardiao import PROMPT_CLASSIFICACAO
from alguem.nucleo.system_prompt import IDENTIDADE
from bd import sessao_bd

# 'apoio_pedagogico' (terceiro prompt do plano) só existe a partir da
# Fase 6 -- não há texto por omissão para ele ainda, por isso fica de
# fora daqui até essa fase precisar dele.
PROMPTS_OMISSAO = {
    "tutor": IDENTIDADE,
    "guardiao": PROMPT_CLASSIFICACAO,
}


class ErroPromptConfiguravel(Exception):
    pass


def _validar_chave(chave: str) -> None:
    if chave not in PROMPTS_OMISSAO:
        disponiveis = ", ".join(sorted(PROMPTS_OMISSAO))
        raise ErroPromptConfiguravel(f"Prompt '{chave}' desconhecido. Válidos: {disponiveis}.")


def obter_prompt_personalizado(chave: str, dsn: str | None = None) -> str | None:
    """Devolve o texto guardado na BD para 'chave', ou None se ainda
    não foi personalizado (a usar o valor por omissão)."""
    _validar_chave(chave)
    with sessao_bd(dsn) as bd:
        linha = bd.execute(
            "SELECT texto FROM prompt_configuravel WHERE chave = %s", (chave,)
        ).fetchone()
    return linha["texto"] if linha else None


def obter_prompt(chave: str, dsn: str | None = None) -> str:
    """O texto realmente em uso: o personalizado, se existir, senão o
    valor por omissão do código."""
    return obter_prompt_personalizado(chave, dsn) or PROMPTS_OMISSAO[chave]


def definir_prompt(chave: str, texto: str, atualizado_por: int, dsn: str | None = None) -> None:
    _validar_chave(chave)
    if not texto.strip():
        raise ErroPromptConfiguravel("O prompt não pode ficar vazio.")
    with sessao_bd(dsn) as bd:
        bd.execute(
            "INSERT INTO prompt_configuravel (chave, texto, atualizado_em, atualizado_por) "
            "VALUES (%s, %s, now(), %s) "
            "ON CONFLICT (chave) DO UPDATE SET "
            "texto = EXCLUDED.texto, atualizado_em = now(), atualizado_por = EXCLUDED.atualizado_por",
            (chave, texto, atualizado_por),
        )


def repor_omissao(chave: str, dsn: str | None = None) -> None:
    _validar_chave(chave)
    with sessao_bd(dsn) as bd:
        bd.execute("DELETE FROM prompt_configuravel WHERE chave = %s", (chave,))
