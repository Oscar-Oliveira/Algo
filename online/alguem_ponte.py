# -*- coding: utf-8 -*-
"""Constrói um Alguem por pedido, a partir da credencial que o
estudante guardou (ver credenciais.py), em vez de um config.json local
-- é a única adaptação necessária; todo o resto do pacote alguem/
(política, guardião, escada de ajuda, registador) é reaproveitado tal
e qual, sem alterações."""

from __future__ import annotations

import sys
import os

_RAIZ_PROJETO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _RAIZ_PROJETO not in sys.path:
    sys.path.insert(0, _RAIZ_PROJETO)

from alguem.fornecedores import criar_fornecedor, ErroFornecedorLLM
from alguem.nucleo import Alguem, PoliticaPedagogica, Registador

from credenciais import obter_credencial, CredencialLLM
from autenticacao import obter_id_pseudonimo

# Política por omissão para todas as sessões web -- mesmos valores por
# omissão que o alguem/config.exemplo.json já usa localmente.
POLITICA_POR_OMISSAO = PoliticaPedagogica()


class ErroAlguemIndisponivel(Exception):
    pass


def construir_alguem(
    estudante_id: int,
    ficheiros_visiveis: list[tuple[str, str]] | None = None,
    caminho_bd: str | None = None,
    pasta_logs: str | None = None,
) -> Alguem:
    """Lê a credencial do estudante e constrói um Alguem pronto a
    conversar. Levanta ErroAlguemIndisponivel (com mensagem amigável)
    se o estudante ainda não configurou nenhum fornecedor. Os logs
    usam o id_pseudonimo da conta, nunca o id nem o email diretamente.
    'pasta_logs' existe só para os testes conseguirem isolar os logs
    sem variáveis de ambiente (mesma técnica já usada em alguem/)."""
    from bd import CAMINHO_BD_POR_OMISSAO

    if caminho_bd is None:
        caminho_bd = CAMINHO_BD_POR_OMISSAO

    credencial: CredencialLLM | None = obter_credencial(estudante_id, caminho_bd)
    if credencial is None:
        raise ErroAlguemIndisponivel(
            "Ainda não configuraste nenhum fornecedor de LLM -- "
            "define um em Definições antes de chamares Alguem."
        )

    extras = {}
    if credencial.host:
        extras["host"] = credencial.host

    try:
        fornecedor = criar_fornecedor(
            credencial.fornecedor, credencial.modelo, credencial.api_key, **extras
        )
    except ErroFornecedorLLM as e:
        raise ErroAlguemIndisponivel(str(e)) from e

    kwargs_registador = {"id_estudante": obter_id_pseudonimo(estudante_id, caminho_bd)}
    if pasta_logs is not None:
        kwargs_registador["pasta_logs"] = pasta_logs
    registador = Registador(**kwargs_registador)
    return Alguem(
        fornecedor,
        POLITICA_POR_OMISSAO,
        ficheiros_visiveis=ficheiros_visiveis,
        registador=registador,
    )
