# -*- coding: utf-8 -*-
"""Lê o config.json (fornecedor/modelo/credenciais + política
pedagógica) e constrói um Alguem pronto a usar. É o único sítio do
projeto que sabe o nome do ficheiro de configuração -- todo o resto
(fornecedores, política, tutor) recebe os dados já prontos, sem saber
de onde vieram."""
from __future__ import annotations

import json
import os

from .fornecedores import criar_fornecedor, ErroFornecedorLLM
from .nucleo.politica_pedagogica import PoliticaPedagogica
from .nucleo.tutor import Alguem

CAMINHO_CONFIG_POR_OMISSAO = os.path.join(os.path.dirname(__file__), "config.json")


class ErroConfiguracao(Exception):
    pass


def carregar_config(caminho: str = CAMINHO_CONFIG_POR_OMISSAO) -> dict:
    if not os.path.isfile(caminho):
        exemplo = os.path.join(os.path.dirname(caminho), "config.exemplo.json")
        raise ErroConfiguracao(
            f"Não encontrei '{caminho}'.\n"
            f"Copia '{exemplo}' para '{caminho}' e preenche o fornecedor, "
            f"o modelo e a tua chave de API antes de chamares o Alguem."
        )
    with open(caminho, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError as e:
            raise ErroConfiguracao(f"'{caminho}' não é um JSON válido: {e}") from e


def criar_alguem(caminho_config: str = CAMINHO_CONFIG_POR_OMISSAO,
                  ficheiros_visiveis: list[tuple[str, str]] | None = None) -> Alguem:
    dados = carregar_config(caminho_config)

    nome_fornecedor = dados.get("fornecedor")
    modelo = dados.get("modelo")
    if not nome_fornecedor or not modelo:
        raise ErroConfiguracao(
            "O config.json precisa de indicar 'fornecedor' e 'modelo'."
        )

    credenciais = dados.get("credenciais", {})
    if not isinstance(credenciais, dict):
        raise ErroConfiguracao(
            "'credenciais' no config.json tem de ser um objeto (ex: "
            '{"openai": {"api_key": "..."}}), não uma lista nem um valor solto.'
        )
    dados_credenciais = credenciais.get(nome_fornecedor, {})
    if not isinstance(dados_credenciais, dict):
        raise ErroConfiguracao(
            f"'credenciais.{nome_fornecedor}' no config.json tem de ser um "
            f'objeto (ex: {{"api_key": "..."}}), não um valor solto.'
        )
    dados_credenciais = dict(dados_credenciais)
    api_key = dados_credenciais.pop("api_key", "") or ""
    # o que sobrar (ex: 'host' da Ollama) passa por diante ao
    # construtor do fornecedor -- se a chave for mesmo obrigatória e
    # estiver em falta, é o próprio fornecedor que recusa (ver
    # AgenteLLM.REQUER_API_KEY em fornecedores/base.py); a Ollama, por
    # exemplo, não precisa de nenhuma.
    try:
        fornecedor = criar_fornecedor(nome_fornecedor, modelo, api_key, **dados_credenciais)
    except ErroFornecedorLLM as e:
        raise ErroConfiguracao(str(e)) from e

    dados_politica = dados.get("politica_pedagogica", {})
    try:
        politica = PoliticaPedagogica.a_partir_de_dict(dados_politica)
    except ValueError as e:
        raise ErroConfiguracao(str(e)) from e

    return Alguem(fornecedor, politica, ficheiros_visiveis=ficheiros_visiveis)
